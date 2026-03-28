from __future__ import annotations

import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from typing import Any

from prospecting_agent.http_client import HttpClient
from prospecting_agent.models import ICP
from research_agent.config import ResearchSettings
from research_agent.models import (
    ActivityItem,
    CompanyProfile,
    NewsItem,
    PersonProfile,
    ResearchDossier,
)
from research_agent.sources.base import ResearchSource
from research_agent.sources.blog_feeds import BlogFeedSource
from research_agent.sources.builtwith import BuiltWithSource
from research_agent.sources.github import GitHubResearchSource
from research_agent.sources.google_news import GoogleNewsSource
from research_agent.sources.google_search import GoogleSearchSource
from research_agent.sources.hn_search import HNSearchSource
from research_agent.synthesizer import LLMSynthesizer

from event_emitter import emit_step, emit_item, emit_summary, ProgressCallback


def run_research(
    prospect_queue_path: Path,
    icp: ICP,
    settings: ResearchSettings,
    output_dir: Path,
    max_research: int | None = None,
    min_prospect_score: float = 30.0,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    def _step(idx: int, status: str, label: str, **kw: Any) -> None:
        print(f"[info] {label}")
        if progress:
            emit_step(idx, status, label, **kw)

    _step(0, "running", "Loading and filtering prospect queue...")
    prospects = _load_prospects(prospect_queue_path, min_prospect_score)
    if max_research and max_research > 0:
        prospects = prospects[:max_research]

    if not prospects:
        print("[info] No prospects above minimum score threshold.")
        return {"researched": 0, "skipped": 0}

    _step(0, "done", f"Loaded {len(prospects)} prospects (min_score={min_prospect_score})")

    _step(1, "running", f"Researching {len(prospects)} prospects across news, GitHub, HN...")
    http = HttpClient(timeout_seconds=settings.http_timeout_seconds)
    sources = _build_sources(http, settings)
    synthesizer = _build_synthesizer(settings)

    dossiers: list[ResearchDossier] = []
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=settings.max_concurrent_research) as pool:
        futures = {
            pool.submit(
                _research_one_prospect, prospect, icp, sources, synthesizer
            ): prospect
            for prospect in prospects
        }
        for future in as_completed(futures):
            prospect = futures[future]
            name = prospect.get("contact", {}).get("full_name", "Unknown")
            try:
                dossier = future.result()
                dossiers.append(dossier)
                conf = dossier.research_confidence
                print(f"  [ok] {name} (confidence={conf:.2f})")
                if progress:
                    emit_item(dossier)
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                print(f"  [fail] {name}: {exc}")

    _step(1, "done", f"Researched {len(dossiers)} prospects ({len(errors)} errors)")

    _step(2, "running", "Writing dossiers and summary...")
    dossiers.sort(key=lambda d: d.research_confidence, reverse=True)

    dossiers_path = output_dir / "research_dossiers.json"
    summary_path = output_dir / "research_summary.csv"
    _write_json(dossiers_path, [d.to_dict() for d in dossiers])
    _write_summary_csv(summary_path, dossiers)

    result = {
        "researched": len(dossiers),
        "errors": len(errors),
        "dossiers_json": str(dossiers_path),
        "summary_csv": str(summary_path),
    }
    if errors:
        result["error_details"] = errors
    _step(2, "done", f"Research complete — {len(dossiers)} dossiers ready")

    if progress:
        emit_summary(result)

    return result


def _load_prospects(
    path: Path, min_score: float
) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    filtered = [p for p in raw if p.get("score", 0) >= min_score]
    filtered.sort(key=lambda p: p.get("score", 0), reverse=True)
    return filtered


def _build_sources(
    http: HttpClient, settings: ResearchSettings
) -> list[ResearchSource]:
    sources: list[ResearchSource] = [
        GoogleNewsSource(http),
        HNSearchSource(http),
        GitHubResearchSource(http, settings.github_token),
        BlogFeedSource(http),
        BuiltWithSource(http, settings.builtwith_api_key),
    ]
    if settings.google_cse_api_key and settings.google_cse_cx:
        sources.insert(
            0, GoogleSearchSource(http, settings.google_cse_api_key, settings.google_cse_cx)
        )
    return sources


def _build_synthesizer(settings: ResearchSettings) -> LLMSynthesizer | None:
    if not settings.openai_api_key:
        print("[warn] RESEARCH_LLM_API_KEY not set -- dossiers will use fallback synthesis.")
        return None
    return LLMSynthesizer(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_model,
    )


def _research_one_prospect(
    prospect: dict[str, Any],
    icp: ICP,
    sources: list[ResearchSource],
    synthesizer: LLMSynthesizer | None,
) -> ResearchDossier:
    contact = prospect.get("contact", {})
    full_name = contact.get("full_name", "Unknown")
    company_name = contact.get("company_name", "Unknown")
    domain = contact.get("company_domain")

    company_data = _collect_company_data(sources, company_name, domain)
    person_data = _collect_person_data(sources, full_name, company_name, domain)

    company_profile = _build_company_profile(company_name, domain, company_data)
    person_profile = _build_person_profile(
        full_name, contact.get("title"), company_name, person_data
    )

    if synthesizer:
        synthesis = synthesizer.synthesize(
            product_name=icp.product_name,
            product_pitch=icp.product_pitch,
            person_name=full_name,
            person_title=contact.get("title"),
            company_name=company_name,
            company_domain=domain,
            company_data=company_data,
            person_data=person_data,
        )
    else:
        from research_agent.synthesizer import _fallback_synthesis
        synthesis = _fallback_synthesis(company_data, person_data)

    return ResearchDossier(
        prospect_score=prospect.get("score", 0),
        prospect_reasons=prospect.get("reasons", []),
        contact_name=full_name,
        contact_title=contact.get("title"),
        contact_company=company_name,
        contact_email=contact.get("email"),
        contact_linkedin=contact.get("linkedin_url"),
        company_profile=company_profile,
        person_profile=person_profile,
        talking_points=synthesis.get("talking_points", []),
        pain_points=synthesis.get("pain_points", []),
        relevance_summary=synthesis.get("relevance_summary", ""),
        research_confidence=synthesis.get("research_confidence", 0.0),
    )


def _collect_company_data(
    sources: list[ResearchSource], company_name: str, domain: str | None
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for source in sources:
        try:
            data = source.research_company(company_name, domain)
            _merge_data(merged, data)
        except Exception as exc:
            print(f"  [warn] {source.name} company research failed: {exc}")
    return merged


def _collect_person_data(
    sources: list[ResearchSource],
    full_name: str,
    company_name: str | None,
    domain: str | None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for source in sources:
        try:
            data = source.research_person(full_name, company_name, domain)
            _merge_data(merged, data)
        except Exception as exc:
            print(f"  [warn] {source.name} person research failed: {exc}")
    return merged


def _merge_data(target: dict[str, Any], new: dict[str, Any]) -> None:
    for key, value in new.items():
        if not value:
            continue
        if key == "_raw":
            target.setdefault("_raw", {}).update(value)
        elif isinstance(value, list):
            existing = target.get(key, [])
            if isinstance(existing, list):
                target[key] = existing + value
            else:
                target[key] = value
        elif isinstance(value, dict):
            existing = target.get(key, {})
            if isinstance(existing, dict):
                existing.update(value)
                target[key] = existing
            else:
                target[key] = value
        elif key not in target:
            target[key] = value


def _build_company_profile(
    name: str, domain: str | None, data: dict[str, Any]
) -> CompanyProfile:
    news_raw = data.get("recent_news", [])
    news = []
    for item in news_raw:
        if isinstance(item, dict):
            news.append(NewsItem(
                title=item.get("title", ""),
                url=item.get("url", ""),
                source=item.get("source", "unknown"),
                published_date=item.get("published_date"),
                snippet=item.get("snippet"),
            ))

    return CompanyProfile(
        name=name,
        domain=domain,
        description=data.get("description"),
        industry=data.get("industry"),
        employee_count=data.get("employee_count"),
        founded_year=data.get("founded_year"),
        funding_stage=data.get("funding_stage"),
        total_funding=data.get("total_funding"),
        headquarters=data.get("headquarters"),
        technologies=_dedup_list(data.get("technologies", [])),
        competitors=_dedup_list(data.get("competitors", [])),
        recent_news=news[:15],
        social_profiles=data.get("social_profiles", {}),
        key_metrics=data.get("key_metrics", {}),
    )


def _build_person_profile(
    full_name: str,
    title: str | None,
    company_name: str | None,
    data: dict[str, Any],
) -> PersonProfile:
    activities_raw = data.get("recent_activity", [])
    activities = []
    for item in activities_raw:
        if isinstance(item, dict):
            activities.append(ActivityItem(
                activity_type=item.get("activity_type", "unknown"),
                title=item.get("title", ""),
                url=item.get("url"),
                date=item.get("date"),
                snippet=item.get("snippet"),
            ))

    return PersonProfile(
        full_name=full_name,
        current_title=title,
        current_company=company_name,
        bio=data.get("bio"),
        skills=_dedup_list(data.get("skills", [])),
        publications=_dedup_list(data.get("publications", [])),
        social_profiles=data.get("social_profiles", {}),
        recent_activity=activities[:20],
        mutual_interests=_dedup_list(data.get("mutual_interests", [])),
    )


def _dedup_list(items: list) -> list:
    seen: set[str] = set()
    result = []
    for item in items:
        key = str(item).lower().strip()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _write_json(path: Path, payload: list | dict) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _write_summary_csv(path: Path, dossiers: list[ResearchDossier]) -> None:
    fields = [
        "contact_name",
        "contact_title",
        "contact_company",
        "contact_email",
        "prospect_score",
        "research_confidence",
        "talking_points_count",
        "pain_points_count",
        "news_count",
        "activities_count",
        "technologies",
        "relevance_summary",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for d in dossiers:
            writer.writerow({
                "contact_name": d.contact_name,
                "contact_title": d.contact_title,
                "contact_company": d.contact_company,
                "contact_email": d.contact_email,
                "prospect_score": d.prospect_score,
                "research_confidence": d.research_confidence,
                "talking_points_count": len(d.talking_points),
                "pain_points_count": len(d.pain_points),
                "news_count": len(d.company_profile.recent_news),
                "activities_count": len(d.person_profile.recent_activity),
                "technologies": " | ".join(d.company_profile.technologies[:5]),
                "relevance_summary": d.relevance_summary[:200],
            })
