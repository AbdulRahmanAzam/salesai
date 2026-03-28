from __future__ import annotations

import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from prospecting_agent.models import ICP
from personalisation_agent.config import PersonalisationSettings
from personalisation_agent.drafting import DraftWriter
from personalisation_agent.models import OutreachDraft, PersonalisationResult

from event_emitter import emit_step, emit_item, emit_summary, ProgressCallback


def run_personalisation(
    dossiers_path: Path,
    icp: ICP,
    settings: PersonalisationSettings,
    output_dir: Path,
    max_drafts: int | None = None,
    min_confidence: float | None = None,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    def _step(idx: int, status: str, label: str, **kw: Any) -> None:
        print(f"[info] {label}")
        if progress:
            emit_step(idx, status, label, **kw)

    min_conf = min_confidence if min_confidence is not None else settings.min_research_confidence

    _step(0, "running", "Loading research dossiers...")
    dossiers = _load_dossiers(dossiers_path, min_conf)
    if max_drafts is not None and max_drafts > 0:
        dossiers = dossiers[:max_drafts]

    if not dossiers:
        print("[info] No dossiers above confidence threshold. Nothing to personalise.")
        return {"drafts": 0, "skipped": 0}

    if not settings.llm_api_key:
        print("[error] PERSONALISATION_LLM_API_KEY is not set. Cannot generate drafts.")
        return {"drafts": 0, "error": "missing_api_key"}

    _step(0, "done", f"Loaded {len(dossiers)} dossiers")

    _step(1, "running", f"Writing personalised outreach for {len(dossiers)} prospects...")
    writer = DraftWriter(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )

    results: list[PersonalisationResult] = []
    failed = 0

    print(f"[info] Personalising {len(dossiers)} dossiers with {settings.llm_model}...")
    print(f"[info] Using endpoint: {settings.llm_base_url}")

    with ThreadPoolExecutor(max_workers=settings.max_concurrent_drafts) as pool:
        futures = {
            pool.submit(
                _personalise_one, writer, icp.product_name, icp.product_pitch, dossier
            ): dossier
            for dossier in dossiers
        }
        for future in as_completed(futures):
            dossier = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(
                    f"  [ok] {result.draft.contact_name} "
                    f"(score: {result.draft.personalization_score})"
                )
                if progress:
                    emit_item(result.draft)
            except Exception as exc:
                failed += 1
                name = dossier.get("contact_name", "?")
                print(f"  [fail] {name}: {exc}")

    _step(1, "done", f"Generated {len(results)} drafts ({failed} failed)")

    _step(2, "running", "Finalising and writing output...")
    results.sort(key=lambda r: r.draft.personalization_score, reverse=True)

    drafts_path = output_dir / "outreach_drafts.json"
    summary_path = output_dir / "outreach_summary.csv"

    _write_json(drafts_path, [r.draft.to_dict() for r in results])
    _write_summary_csv(summary_path, results)

    avg_score = (
        sum(r.draft.personalization_score for r in results) / len(results)
        if results
        else 0
    )

    summary = {
        "drafts": len(results),
        "failed": failed,
        "avg_personalization_score": round(avg_score, 1),
        "model": settings.llm_model,
        "endpoint": settings.llm_base_url,
        "drafts_json": str(drafts_path),
        "summary_csv": str(summary_path),
    }
    _step(2, "done", f"Personalisation complete — {len(results)} drafts ready")

    if progress:
        emit_summary(summary)

    return summary


def _load_dossiers(path: Path, min_confidence: float) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Expected a JSON array in {path}")

    filtered = [
        d for d in raw if d.get("research_confidence", 0) >= min_confidence
    ]
    filtered.sort(key=lambda d: d.get("prospect_score", 0), reverse=True)
    return filtered


def _personalise_one(
    writer: DraftWriter,
    product_name: str,
    product_pitch: str,
    dossier: dict[str, Any],
) -> PersonalisationResult:
    llm_output = writer.write_draft(product_name, product_pitch, dossier)

    draft = OutreachDraft(
        contact_name=dossier.get("contact_name", "Unknown"),
        contact_title=dossier.get("contact_title"),
        contact_company=dossier.get("contact_company", "Unknown"),
        contact_email=dossier.get("contact_email"),
        contact_linkedin=dossier.get("contact_linkedin"),
        subject=llm_output["subject"],
        body=llm_output["body"],
        personalization_score=llm_output["personalization_score"],
        personalization_signals=llm_output["personalization_signals"],
        status="draft",
        prospect_score=dossier.get("prospect_score", 0),
        research_confidence=dossier.get("research_confidence", 0),
    )

    return PersonalisationResult(
        draft=draft,
        dossier_used=dossier,
        icp_product=product_name,
        icp_pitch=product_pitch,
    )


def _write_json(path: Path, payload: list | dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_summary_csv(path: Path, results: list[PersonalisationResult]) -> None:
    fields = [
        "contact_name",
        "contact_title",
        "contact_company",
        "contact_email",
        "subject",
        "personalization_score",
        "prospect_score",
        "research_confidence",
        "signals_count",
        "status",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            d = r.draft
            w.writerow(
                {
                    "contact_name": d.contact_name,
                    "contact_title": d.contact_title,
                    "contact_company": d.contact_company,
                    "contact_email": d.contact_email,
                    "subject": d.subject,
                    "personalization_score": d.personalization_score,
                    "prospect_score": d.prospect_score,
                    "research_confidence": d.research_confidence,
                    "signals_count": len(d.personalization_signals),
                    "status": d.status,
                }
            )
