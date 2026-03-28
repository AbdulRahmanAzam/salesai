from __future__ import annotations

import argparse
import csv
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


BASE_URL = "https://api.hunter.io/v2/domain-search"


@dataclass
class LeadRecord:
    domain: str
    company: str | None
    company_type: str | None
    company_industry: str | None
    company_description: str | None
    company_country: str | None
    company_city: str | None
    company_state: str | None
    company_postal_code: str | None
    company_linkedin: str | None
    company_twitter: str | None
    company_facebook: str | None
    company_phone: str | None
    company_pattern: str | None
    company_disposable: bool | None
    company_webmail: bool | None
    company_accept_all: bool | None
    full_name: str | None
    first_name: str | None
    last_name: str | None
    position: str | None
    seniority: str | None
    department: str | None
    email: str
    confidence: int | None
    verification_status: str | None
    verification_date: str | None
    verification_method: str | None
    verification_mode: str | None
    email_type: str | None
    linkedin: str | None
    twitter: str | None
    phone_number: str | None
    sources_count: int
    sources_domains: str | None
    sources_uris: str | None
    source: str


class HunterClient:
    def __init__(self, api_key: str, timeout_seconds: int = 30):
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "prospecting-agent-hunter/1.0",
                "Accept": "application/json",
            }
        )

    def domain_search(
        self,
        domain: str,
        *,
        company: str | None = None,
        limit: int = 100,
        offset: int = 0,
        department: str | None = None,
        seniority: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "api_key": self.api_key,
            "domain": domain,
            "limit": limit,
            "offset": offset,
        }
        if company:
            params["company"] = company
        if department:
            params["department"] = department
        if seniority:
            params["seniority"] = seniority

        resp = self.session.get(BASE_URL, params=params, timeout=self.timeout_seconds)

        if resp.status_code == 429:
            raise RuntimeError(
                "Hunter API rate limit reached. Wait and retry, or reduce request volume."
            )

        if resp.status_code >= 400:
            try:
                body = resp.json()
            except ValueError:
                body = {"errors": [{"details": resp.text}]}
            raise RuntimeError(
                f"Hunter API error for domain '{domain}': {json.dumps(body, ensure_ascii=True)}"
            )

        payload = resp.json()
        if payload.get("errors"):
            raise RuntimeError(
                f"Hunter API returned errors for domain '{domain}': "
                f"{json.dumps(payload.get('errors'), ensure_ascii=True)}"
            )
        return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect publicly available business contacts from Hunter domain-search "
            "and export to JSON/CSV."
        )
    )
    parser.add_argument(
        "--domain",
        action="append",
        default=[],
        help="Single domain to query. Repeat the flag for multiple domains.",
    )
    parser.add_argument(
        "--domains-file",
        type=Path,
        default=None,
        help="Optional text file with one domain per line.",
    )
    parser.add_argument(
        "--company",
        default=None,
        help="Optional company name hint to improve matching.",
    )
    parser.add_argument(
        "--department",
        default=None,
        help="Optional filter (for example: executive, engineering, marketing, sales).",
    )
    parser.add_argument(
        "--seniority",
        default=None,
        help="Optional filter (for example: junior, senior, executive).",
    )
    parser.add_argument(
        "--per-domain-limit",
        type=int,
        default=100,
        help="Max emails to request per domain (Hunter max is 100).",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Hunter API key. If omitted, HUNTER_API_KEY env var is used.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("output") / "hunter",
        help="Directory for exported JSON and CSV files.",
    )
    parser.add_argument(
        "--request-delay-seconds",
        type=float,
        default=0.3,
        help="Delay between domain requests to reduce rate-limit pressure.",
    )
    return parser.parse_args()


def _normalize_domain(value: str) -> str:
    domain = value.strip().lower()
    domain = domain.replace("https://", "").replace("http://", "")
    if domain.startswith("www."):
        domain = domain[4:]
    return domain.split("/")[0]


def _load_domains(args: argparse.Namespace) -> list[str]:
    domains = [_normalize_domain(d) for d in args.domain if d.strip()]

    if args.domains_file:
        lines = args.domains_file.read_text(encoding="utf-8").splitlines()
        file_domains = [_normalize_domain(line) for line in lines if line.strip()]
        domains.extend(file_domains)

    deduped: list[str] = []
    seen = set()
    for domain in domains:
        if domain and domain not in seen:
            deduped.append(domain)
            seen.add(domain)

    return deduped


def _to_lead_records(domain: str, payload: dict[str, Any]) -> list[LeadRecord]:
    data = payload.get("data", {})
    company = data.get("organization")
    emails = data.get("emails", [])

    records: list[LeadRecord] = []
    for item in emails:
        first_name = item.get("first_name")
        last_name = item.get("last_name")
        full_name = item.get("value")
        verification = item.get("verification") or {}
        sources = item.get("sources") or []
        source_domains = sorted(
            {str(s.get("domain")).strip() for s in sources if s.get("domain")}
        )
        source_uris = [str(s.get("uri")).strip() for s in sources if s.get("uri")]
        records.append(
            LeadRecord(
                domain=domain,
                company=company,
                company_type=data.get("type"),
                company_industry=data.get("industry"),
                company_description=data.get("description"),
                company_country=data.get("country"),
                company_city=data.get("city"),
                company_state=data.get("state"),
                company_postal_code=data.get("postal_code"),
                company_linkedin=data.get("linkedin"),
                company_twitter=data.get("twitter"),
                company_facebook=data.get("facebook"),
                company_phone=data.get("phone_number"),
                company_pattern=data.get("pattern"),
                company_disposable=data.get("disposable"),
                company_webmail=data.get("webmail"),
                company_accept_all=data.get("accept_all"),
                full_name=full_name,
                first_name=first_name,
                last_name=last_name,
                position=item.get("position"),
                seniority=item.get("seniority"),
                department=item.get("department"),
                email=item.get("value") or "",
                confidence=item.get("confidence"),
                verification_status=verification.get("status"),
                verification_date=verification.get("date"),
                verification_method=verification.get("method"),
                verification_mode=verification.get("mode"),
                email_type=item.get("type"),
                linkedin=item.get("linkedin"),
                twitter=item.get("twitter"),
                phone_number=item.get("phone_number"),
                sources_count=len(sources),
                sources_domains=" | ".join(source_domains) if source_domains else None,
                sources_uris=" | ".join(source_uris) if source_uris else None,
                source="hunter_domain_search",
            )
        )

    return [r for r in records if r.email]


def _write_json(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    load_dotenv()
    args = parse_args()

    api_key = args.api_key or os.getenv("HUNTER_API_KEY")
    if not api_key:
        raise SystemExit(
            "Missing API key. Provide --api-key or set HUNTER_API_KEY in your environment."
        )

    domains = _load_domains(args)
    if not domains:
        raise SystemExit("No domains provided. Use --domain and/or --domains-file.")

    limit = max(1, min(100, args.per_domain_limit))
    delay = max(0.0, args.request_delay_seconds)

    client = HunterClient(api_key=api_key)

    all_rows: list[dict[str, Any]] = []
    domain_summaries: list[dict[str, Any]] = []
    raw_domain_responses: list[dict[str, Any]] = []
    failed_domains: list[str] = []

    for idx, domain in enumerate(domains, start=1):
        try:
            payload = client.domain_search(
                domain,
                company=args.company,
                limit=limit,
                offset=0,
                department=args.department,
                seniority=args.seniority,
            )
            data = payload.get("data", {})
            records = _to_lead_records(domain, payload)
            all_rows.extend([r.__dict__ for r in records])
            domain_summaries.append(
                {
                    "domain": domain,
                    "organization": data.get("organization"),
                    "type": data.get("type"),
                    "industry": data.get("industry"),
                    "description": data.get("description"),
                    "country": data.get("country"),
                    "city": data.get("city"),
                    "state": data.get("state"),
                    "postal_code": data.get("postal_code"),
                    "pattern": data.get("pattern"),
                    "accept_all": data.get("accept_all"),
                    "webmail": data.get("webmail"),
                    "disposable": data.get("disposable"),
                    "linkedin": data.get("linkedin"),
                    "twitter": data.get("twitter"),
                    "facebook": data.get("facebook"),
                    "phone_number": data.get("phone_number"),
                    "emails_count": len(data.get("emails", []) or []),
                    "emails_available": bool(data.get("emails", [])),
                }
            )
            raw_domain_responses.append({"domain": domain, "payload": payload})
            print(
                f"[{idx}/{len(domains)}] {domain}: {len(records)} contact(s) collected"
            )
        except Exception as exc:
            failed_domains.append(domain)
            print(f"[{idx}/{len(domains)}] {domain}: FAILED - {exc}")

        if idx < len(domains) and delay > 0:
            time.sleep(delay)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "hunter_leads.json"
    csv_path = args.out_dir / "hunter_leads.csv"
    domains_path = args.out_dir / "hunter_domains.json"
    raw_path = args.out_dir / "hunter_raw_responses.json"

    _write_json(json_path, all_rows)
    _write_csv(csv_path, all_rows)
    _write_json(domains_path, domain_summaries)
    _write_json(raw_path, raw_domain_responses)

    print("\nDone")
    print(f"Total domains processed: {len(domains)}")
    print(f"Total contacts exported: {len(all_rows)}")
    print(f"JSON output: {json_path}")
    print(f"CSV output:  {csv_path}")
    print(f"Domains output: {domains_path}")
    print(f"Raw API output: {raw_path}")
    if failed_domains:
        print(f"Domains failed: {', '.join(failed_domains)}")


if __name__ == "__main__":
    main()
