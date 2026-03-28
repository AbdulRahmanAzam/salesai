from __future__ import annotations

import csv
import json
import signal as _signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from threading import Thread
from typing import Any

from prospecting_agent.config import Settings
from prospecting_agent.enrichment import ContactEnricher
from prospecting_agent.http_client import HttpClient
from prospecting_agent.icp_interpreter import ICPInterpreter
from prospecting_agent.models import Company, Contact, ICP, ProspectDraft
from prospecting_agent.scoring import LLMScorer, score_contact
from prospecting_agent.sources import (
    ApolloSource,
    CrunchbaseSource,
    DuckDuckGoCompanySource,
    GitHubOrgSource,
    GoogleCSECompanySource,
    HackerNewsSource,
    HunterSource,
    LLMContactSource,
    MockCompanySource,
    MockContactSource,
    OpenCorporatesSource,
    ProductHuntSource,
    RedditCompanySource,
    SerperCompanySource,
    SerperPersonSource,
    WebScraperContactSource,
    YCombinatorSource,
)

from event_emitter import emit_step, emit_item, emit_summary, ProgressCallback


def run_prospecting(
    icp: ICP,
    settings: Settings,
    output_dir: Path,
    max_leads: int | None = None,
    use_llm_scoring: bool = True,
    progress: ProgressCallback | None = None,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    http = HttpClient(timeout_seconds=settings.http_timeout_seconds)

    def _step(idx: int, status: str, label: str, **kw: Any) -> None:
        print(f"[info] {label}")
        if progress:
            emit_step(idx, status, label, **kw)

    # Phase 1: Collect companies from all sources
    _step(0, "running", "Searching companies across Apollo, Google, GitHub, HN, ProductHunt...")
    company_sources = _build_company_sources(http, settings, icp)
    companies = _collect_companies(icp, company_sources)

    # Mock fallback — if real sources returned 0 companies (API credits exhausted)
    if not companies and settings.enable_mock_fallback:
        print("  [warn] All company sources returned 0 results — activating mock fallback")
        mock_companies = MockCompanySource().find_companies(icp)
        companies = mock_companies

    # Enrich companies via Apollo organizations/enrich (free-plan friendly)
    if settings.apollo_api_key:
        import time
        apollo_enricher = ApolloSource(http, settings.apollo_base_url, settings.apollo_api_key)
        enriched_count = 0
        apollo_credits_exhausted = False
        for i, company in enumerate(companies):
            if apollo_credits_exhausted:
                break
            try:
                companies[i] = apollo_enricher.enrich_company(company)
                enriched_count += 1
            except Exception as exc:
                exc_str = str(exc).lower()
                if "insufficient credits" in exc_str or "422" in exc_str or "402" in exc_str:
                    print(f"  [warn] Apollo credits exhausted — skipping remaining enrichment")
                    apollo_credits_exhausted = True
                else:
                    print(f"  [warn] Apollo enrich skipped for {company.domain}: {exc}")
            # Rate limit: Apollo free plan has per-minute caps
            if (i + 1) % 10 == 0:
                time.sleep(2)
        print(f"  [info] Apollo enriched {enriched_count}/{len(companies)} companies")

    _step(0, "done", f"Found {len(companies)} unique companies", count=len(companies))

    # Phase 2: Collect contacts from contact sources
    _step(1, "running", f"Searching contacts at {len(companies)} companies...")
    contact_sources = _build_contact_sources(http, settings, max_leads=max_leads)
    contacts = _collect_contacts(icp, companies, contact_sources)

    # Mock fallback — if real sources returned 0 contacts (API credits exhausted)
    if not contacts and settings.enable_mock_fallback:
        print("  [warn] All contact sources returned 0 results — activating mock fallback")
        mock_contacts = MockContactSource().find_contacts(icp, companies)
        contacts = mock_contacts

    _step(1, "done", f"Found {len(contacts)} unique contacts", count=len(contacts))

    # Phase 3: Enrich contacts (email discovery, LinkedIn, verification)
    _step(2, "running", f"Enriching {len(contacts)} contacts (emails, LinkedIn, verification)...")
    enricher = ContactEnricher(
        http=http,
        hunter_api_key=settings.hunter_api_key,
        google_cse_api_key=settings.google_cse_api_key,
        google_cse_cx=settings.google_cse_cx,
    )
    contacts = _enrich_contacts(contacts, enricher)
    with_email = sum(1 for c in contacts if c.email)
    with_linkedin = sum(1 for c in contacts if c.linkedin_url)
    _step(2, "done", f"Enriched: {with_email} emails, {with_linkedin} LinkedIn profiles")

    # Phase 4: Score + rank contacts
    _step(3, "running", f"Scoring {len(contacts)} leads with LLM + rules...")
    company_index = {c.key(): c for c in companies}
    llm_scorer = None
    if use_llm_scoring and settings.llm_api_key:
        llm_scorer = LLMScorer(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
        )

    drafts = _build_drafts(icp, contacts, company_index, llm_scorer)
    if max_leads is not None and max_leads > 0:
        drafts = drafts[:max_leads]
    _step(3, "done", f"Scored and ranked {len(drafts)} prospects")

    # Emit individual lead items for progressive rendering
    if progress:
        for draft in drafts:
            emit_item(draft)

    # Phase 5: Output
    _step(4, "running", "Writing output files...")
    queue_json_path = output_dir / "prospect_queue.json"
    queue_csv_path = output_dir / "prospect_queue.csv"
    companies_path = output_dir / "companies.json"
    icp_path = output_dir / "icp_resolved.json"

    _write_json(queue_json_path, [d.to_record() for d in drafts])
    _write_csv(queue_csv_path, drafts)
    _write_json(companies_path, [asdict(c) for c in companies])
    _write_json(icp_path, asdict(icp))

    summary = {
        "companies": len(companies),
        "contacts": len(contacts),
        "contacts_with_email": with_email,
        "contacts_with_linkedin": with_linkedin,
        "drafts": len(drafts),
        "max_leads": max_leads,
        "llm_scoring": llm_scorer is not None,
        "queue_json": str(queue_json_path),
        "queue_csv": str(queue_csv_path),
        "companies_json": str(companies_path),
        "icp_resolved_json": str(icp_path),
        "icp": asdict(icp),
    }
    _step(4, "done", f"Pipeline complete — {len(drafts)} leads ready for review")

    if progress:
        emit_summary(summary)

    return summary


def interpret_and_run(
    natural_language_input: str,
    settings: Settings,
    output_dir: Path,
    max_leads: int | None = None,
    progress: ProgressCallback | None = None,
) -> dict:
    """Full pipeline: natural language -> ICP interpretation -> prospecting."""
    if not settings.llm_api_key:
        raise ValueError(
            "PROSPECTING_LLM_API_KEY is required for natural language ICP interpretation."
        )

    interpreter = ICPInterpreter(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
    )

    print(f"[info] Interpreting ICP from: '{natural_language_input[:100]}...'")
    icp_dict = interpreter.interpret(natural_language_input)

    interpretation = icp_dict.pop("interpretation", "")
    if interpretation:
        print(f"[info] LLM interpretation: {interpretation}")

    icp = ICP(**{k: v for k, v in icp_dict.items() if k in ICP.__dataclass_fields__})

    print(f"[info] Resolved ICP: {icp.product_name}")
    print(f"[info] Target industries: {', '.join(icp.industries)}")
    print(f"[info] Persona titles: {', '.join(icp.persona_titles)}")
    print(f"[info] Keywords: {', '.join(icp.keywords[:5])}")

    result = run_prospecting(icp, settings, output_dir, max_leads=max_leads, progress=progress)
    result["interpretation"] = interpretation
    result["product_name"] = icp.product_name
    result["product_pitch"] = icp.product_pitch
    # Merge interpretation into the ICP dict for frontend display
    if "icp" in result:
        result["icp"]["interpretation"] = interpretation
    return result


def _build_company_sources(
    http: HttpClient, settings: Settings, icp: ICP
) -> list:
    sources = []

    # Apollo (may be 403 on free plan — handled gracefully)
    apollo = ApolloSource(http, settings.apollo_base_url, settings.apollo_api_key)
    if settings.apollo_api_key:
        sources.append(apollo)

    # Serper.dev — Google Search results (best quality, free 2500/month)
    if settings.serper_api_key:
        sources.append(SerperCompanySource(http, settings.serper_api_key))

    # Google CSE (requires CX ID to be configured)
    if settings.google_cse_api_key and settings.google_cse_cx:
        sources.append(
            GoogleCSECompanySource(http, settings.google_cse_api_key, settings.google_cse_cx)
        )

    # DuckDuckGo — free web search fallback
    sources.append(DuckDuckGoCompanySource(http))

    sources.append(OpenCorporatesSource(http, settings.opencorporates_api_token))
    sources.append(GitHubOrgSource(http, settings.github_token))
    sources.append(HackerNewsSource(http))

    if settings.producthunt_token:
        sources.append(ProductHuntSource(http, settings.producthunt_token))

    # Free sources — no API key required
    sources.append(RedditCompanySource(http))
    sources.append(YCombinatorSource(http))
    sources.append(CrunchbaseSource(http))

    # Mock fallback — last resort when all real APIs exhaust credits
    if settings.enable_mock_fallback:
        sources.append(MockCompanySource())

    return sources


def _build_contact_sources(http: HttpClient, settings: Settings, max_leads: int | None = None) -> list:
    sources = []

    # Apollo people search (may be 403 on free plan)
    if settings.apollo_api_key:
        sources.append(
            ApolloSource(http, settings.apollo_base_url, settings.apollo_api_key)
        )

    # Hunter email finder (may be quota-exhausted)
    if settings.hunter_api_key:
        max_domains = min(10, (max_leads or 10) * 2)
        sources.append(
            HunterSource(
                http,
                settings.hunter_api_key,
                per_domain_limit=max(10, min(100, settings.max_source_results)),
                max_domains=max_domains,
            )
        )

    # Serper.dev LinkedIn people search — Google quality, fast
    if settings.serper_api_key:
        sources.append(SerperPersonSource(http, settings.serper_api_key))

    # Web scraper — scrapes company team/about pages (fast: 3 paths, 5 domains)
    max_scrape = min(5, (max_leads or 10))
    sources.append(WebScraperContactSource(http, max_domains=max_scrape))

    # LLM contact discovery — always available as fallback when paid APIs run out
    if settings.llm_api_key:
        max_domains = min(15, (max_leads or 10) * 2)
        sources.append(
            LLMContactSource(
                http,
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                model=settings.llm_model,
                max_domains=max_domains,
            )
        )

    # Mock fallback — last resort when all real APIs exhaust credits
    if settings.enable_mock_fallback:
        sources.append(MockContactSource())

    return sources


def _run_with_timeout(fn, timeout: int, label: str = "source"):
    """Run *fn* in a thread with a hard timeout.  Returns [] on timeout."""
    result = []
    error = [None]

    def _worker():
        nonlocal result
        try:
            result = fn()
        except Exception as exc:
            error[0] = exc

    t = Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=timeout)

    if t.is_alive():
        print(f"  [warn] {label} timed out after {timeout}s — skipping")
        return []
    if error[0]:
        raise error[0]
    return result


def _collect_companies(icp: ICP, sources: list) -> list[Company]:
    merged: dict[str, Company] = {}
    for source in sources:
        try:
            print(f"  [source] {source.name}: searching companies...")
            rows = _run_with_timeout(
                lambda s=source: s.find_companies(icp),
                timeout=30,
                label=source.name,
            )
            print(f"  [source] {source.name}: found {len(rows)} companies")
        except Exception as exc:
            rows = []
            print(f"  [warn] {source.name} failed for companies: {exc}")
        for row in rows:
            if row.domain and row.domain in {d.lower() for d in icp.exclude_domains}:
                continue
            key = row.key()
            if key in merged:
                merged[key] = _merge_company(merged[key], row)
            else:
                merged[key] = row
            if len(merged) >= icp.max_companies:
                break
        if len(merged) >= icp.max_companies:
            break
    return list(merged.values())


def _collect_contacts(
    icp: ICP, companies: list[Company], contact_sources: list
) -> list[Contact]:
    merged: dict[str, Contact] = {}
    email_index: dict[str, str] = {}

    for source in contact_sources:
        try:
            print(f"  [source] {source.name}: searching contacts...")
            rows = _run_with_timeout(
                lambda s=source: s.find_contacts(icp, companies),
                timeout=45,
                label=source.name,
            )
            print(f"  [source] {source.name}: found {len(rows)} contacts")
        except Exception as exc:
            rows = []
            print(f"  [warn] {source.name} failed for contacts: {exc}")
        for row in rows:
            primary_key = row.key()
            match_key = _find_match_key(row, merged, email_index)

            if match_key:
                merged[match_key] = _merge_contact(merged[match_key], row)
                if row.email:
                    email_index[row.email.lower()] = match_key
            else:
                merged[primary_key] = row
                if row.email:
                    email_index[row.email.lower()] = primary_key
            if len(merged) >= icp.max_contacts:
                break
        if len(merged) >= icp.max_contacts:
            break
    return list(merged.values())


def _enrich_contacts(
    contacts: list[Contact], enricher: ContactEnricher
) -> list[Contact]:
    enriched: list[Contact] = []
    for i, contact in enumerate(contacts):
        try:
            enriched.append(enricher.enrich(contact))
            if (i + 1) % 10 == 0:
                print(f"  [enrich] {i + 1}/{len(contacts)} contacts enriched...")
        except Exception as exc:
            print(f"  [warn] enrichment failed for {contact.full_name}: {exc}")
            enriched.append(contact)
    return enriched


def _build_drafts(
    icp: ICP,
    contacts: list[Contact],
    company_index: dict[str, Company],
    llm_scorer: LLMScorer | None = None,
) -> list[ProspectDraft]:
    drafts: list[ProspectDraft] = []

    for contact in contacts:
        company = company_index.get((contact.company_domain or "").lower().strip())

        rule_score, rule_reasons = score_contact(contact, icp, company)

        if llm_scorer and rule_score >= 25:
            try:
                llm_score, llm_reasons, explanation = llm_scorer.score(
                    contact, company, icp
                )
                final_score = (rule_score * 0.4) + (llm_score * 0.6)
                reasons = llm_reasons + [
                    r for r in rule_reasons if r not in llm_reasons
                ]
            except Exception:
                final_score = rule_score
                reasons = rule_reasons
                explanation = ""
        else:
            final_score = rule_score
            reasons = rule_reasons
            explanation = ""

        drafts.append(
            ProspectDraft(
                contact=contact,
                company=company,
                score=round(final_score, 1),
                reasons=reasons,
                relevance_explanation=explanation,
                status="review_required",
            )
        )

    drafts.sort(key=lambda d: d.score, reverse=True)
    return drafts


def _find_match_key(
    contact: Contact,
    merged: dict[str, Contact],
    email_index: dict[str, str],
) -> str | None:
    primary_key = contact.key()
    if primary_key in merged:
        return primary_key

    if contact.email:
        email_key = email_index.get(contact.email.lower())
        if email_key and email_key in merged:
            return email_key

    name = (contact.full_name or "").lower().strip()
    domain = (contact.company_domain or contact.company_name or "").lower().strip()
    if name and len(name) > 3:
        for existing_key, existing in merged.items():
            if _fuzzy_name_match(name, (existing.full_name or "").lower().strip()):
                existing_domain = (
                    existing.company_domain or existing.company_name or ""
                ).lower().strip()
                if domain and existing_domain and (
                    domain in existing_domain or existing_domain in domain
                ):
                    return existing_key
    return None


def _fuzzy_name_match(a: str, b: str) -> bool:
    if a == b:
        return True
    parts_a = a.split()
    parts_b = b.split()
    if not parts_a or not parts_b:
        return False
    if parts_a[-1] != parts_b[-1]:
        return False
    first_a = parts_a[0].rstrip(".")
    first_b = parts_b[0].rstrip(".")
    if first_a == first_b:
        return True
    if len(first_a) == 1 and first_b.startswith(first_a):
        return True
    if len(first_b) == 1 and first_a.startswith(first_b):
        return True
    return False


def _merge_company(a: Company, b: Company) -> Company:
    return Company(
        name=a.name if len(a.name) >= len(b.name) else b.name,
        domain=a.domain or b.domain,
        linkedin_url=a.linkedin_url or b.linkedin_url,
        location=a.location or b.location,
        employee_range=a.employee_range or b.employee_range,
        industry=a.industry or b.industry,
        description=a.description or b.description,
        source=f"{a.source}+{b.source}",
        source_url=a.source_url or b.source_url,
        technologies=sorted(set(a.technologies + b.technologies)),
        notes=sorted(set(a.notes + b.notes)),
    )


def _merge_contact(a: Contact, b: Contact) -> Contact:
    return Contact(
        full_name=a.full_name if len(a.full_name) >= len(b.full_name) else b.full_name,
        title=a.title or b.title,
        company_name=a.company_name or b.company_name,
        company_domain=a.company_domain or b.company_domain,
        email=a.email or b.email,
        linkedin_url=a.linkedin_url or b.linkedin_url,
        phone=a.phone or b.phone,
        location=a.location or b.location,
        source=f"{a.source}+{b.source}",
        source_url=a.source_url or b.source_url,
        confidence=max(a.confidence, b.confidence),
        signals=sorted(set(a.signals + b.signals)),
        research_notes=sorted(set(a.research_notes + b.research_notes)),
    )


def _write_json(path: Path, payload: list | dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_csv(path: Path, drafts: list[ProspectDraft]) -> None:
    fields = [
        "score",
        "status",
        "full_name",
        "title",
        "company_name",
        "company_domain",
        "email",
        "linkedin_url",
        "phone",
        "location",
        "source",
        "signals",
        "reasons",
        "relevance_explanation",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for d in drafts:
            writer.writerow(
                {
                    "score": d.score,
                    "status": d.status,
                    "full_name": d.contact.full_name,
                    "title": d.contact.title,
                    "company_name": d.contact.company_name,
                    "company_domain": d.contact.company_domain,
                    "email": d.contact.email,
                    "linkedin_url": d.contact.linkedin_url,
                    "phone": d.contact.phone,
                    "location": d.contact.location,
                    "source": d.contact.source,
                    "signals": " | ".join(d.contact.signals),
                    "reasons": " | ".join(d.reasons),
                    "relevance_explanation": d.relevance_explanation,
                }
            )
