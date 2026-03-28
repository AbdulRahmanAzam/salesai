from __future__ import annotations

from typing import Any

from prospecting_agent.http_client import HttpClient
from prospecting_agent.models import Company, Contact, ICP
from prospecting_agent.sources.base import CompanySource, ContactSource


class ApolloSource(CompanySource, ContactSource):
    name = "apollo"

    def __init__(self, http: HttpClient, base_url: str, api_key: str | None):
        self.http = http
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        h = {
            "Content-Type": "application/json",
            "accept": "application/json",
        }
        if self.api_key:
            h["X-Api-Key"] = self.api_key
        return h

    def _enabled(self) -> bool:
        return bool(self.api_key)

    def find_companies(self, icp: ICP) -> list[Company]:
        if not self._enabled():
            return []

        body: dict[str, Any] = {
            "page": 1,
            "per_page": min(100, max(25, icp.max_companies)),
        }
        if icp.locations:
            body["organization_locations"] = icp.locations
        if icp.employee_ranges:
            body["organization_num_employees_ranges"] = _normalize_employee_ranges(
                icp.employee_ranges
            )
        if icp.keywords:
            body["q_organization_name"] = " ".join(icp.keywords[:5])
        if icp.industries:
            body["organization_industry_tag_ids"] = icp.industries

        url = f"{self.base_url}/api/v1/mixed_companies/search"
        try:
            data = self.http.post(url, json_body=body, headers=self._headers())
        except Exception as exc:
            print(f"[warn] Apollo company search failed: {exc}")
            # Retry with minimal filters
            minimal_body: dict[str, Any] = {
                "page": 1,
                "per_page": min(100, max(25, icp.max_companies)),
            }
            if icp.locations:
                minimal_body["organization_locations"] = icp.locations
            if icp.employee_ranges:
                minimal_body["organization_num_employees_ranges"] = _normalize_employee_ranges(
                    icp.employee_ranges
                )
            try:
                data = self.http.post(url, json_body=minimal_body, headers=self._headers())
                print(f"[info] Apollo retry with minimal filters succeeded")
            except Exception as exc2:
                print(f"[warn] Apollo retry also failed: {exc2}")
                return []

        companies: list[Company] = []
        for org in data.get("organizations", []):
            domain = org.get("primary_domain") or org.get("website_url")
            companies.append(
                Company(
                    name=org.get("name") or "Unknown",
                    domain=_normalize_domain(domain),
                    linkedin_url=org.get("linkedin_url"),
                    location=org.get("primary_location") or org.get("raw_address"),
                    industry=org.get("industry"),
                    source=self.name,
                    source_url=org.get("website_url") or org.get("linkedin_url"),
                    notes=["Apollo organization search match"],
                )
            )
        return companies

    def find_contacts(self, icp: ICP, companies: list[Company]) -> list[Contact]:
        if not self._enabled() or not companies:
            return []

        org_domains = [c.domain for c in companies if c.domain]
        if not org_domains:
            return []

        body: dict[str, Any] = {
            "page": 1,
            "per_page": min(100, max(25, icp.max_contacts)),
            "q_organization_domains_list": org_domains[:1000],
        }
        if icp.persona_titles:
            body["person_titles"] = icp.persona_titles

        url = f"{self.base_url}/api/v1/mixed_people/search"
        try:
            data = self.http.post(url, json_body=body, headers=self._headers())
        except Exception as exc:
            print(f"[warn] Apollo people search failed: {exc}")
            # Retry without title filters
            retry_body: dict[str, Any] = {
                "page": 1,
                "per_page": min(100, max(25, icp.max_contacts)),
                "q_organization_domains_list": org_domains[:1000],
            }
            try:
                data = self.http.post(url, json_body=retry_body, headers=self._headers())
            except Exception as exc2:
                print(f"[warn] Apollo people retry also failed: {exc2}")
                return []

        people = data.get("people", []) or data.get("contacts", [])
        contacts: list[Contact] = []
        for person in people:
            company = person.get("organization") or {}
            domain = company.get("primary_domain") or person.get("organization_website_url")
            contacts.append(
                Contact(
                    full_name=_join_name(person),
                    title=person.get("title"),
                    company_name=company.get("name") or person.get("organization_name") or "Unknown",
                    company_domain=_normalize_domain(domain),
                    email=person.get("email"),
                    linkedin_url=person.get("linkedin_url"),
                    source=self.name,
                    source_url=person.get("linkedin_url"),
                    confidence=0.75,
                    signals=["Apollo people search"],
                    research_notes=[
                        "Matched by Apollo using ICP filters and company domain list."
                    ],
                )
            )
        return contacts

    def enrich_company(self, company: Company) -> Company:
        """Use Apollo organizations/enrich (free-plan friendly) to add metadata."""
        if not self._enabled() or not company.domain:
            return company
        url = f"{self.base_url}/api/v1/organizations/enrich"
        try:
            import requests as _requests
            resp = self.http.session.get(
                url,
                params={"domain": company.domain},
                headers=self._headers(),
                timeout=self.http.timeout_seconds,
            )
            if resp.status_code in (402, 422, 429):
                body_text = resp.text[:200]
                raise RuntimeError(f"Apollo {resp.status_code}: {body_text}")
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise exc

        org = data.get("organization") or {}
        if not org:
            return company

        if not company.industry and org.get("industry"):
            company.industry = org["industry"]
        if not company.location:
            loc_parts = [org.get("city"), org.get("state"), org.get("country")]
            loc = ", ".join(p for p in loc_parts if p)
            if loc:
                company.location = loc
        if not company.linkedin_url and org.get("linkedin_url"):
            company.linkedin_url = org["linkedin_url"]
        if org.get("estimated_num_employees"):
            company.notes.append(f"~{org['estimated_num_employees']} employees (Apollo)")
        if org.get("short_description"):
            company.notes.append(f"Apollo: {org['short_description']}")
        company.notes.append("Enriched via Apollo organizations/enrich")
        return company


def _join_name(person: dict[str, Any]) -> str:
    full_name = person.get("name")
    if full_name:
        return full_name
    first = (person.get("first_name") or "").strip()
    last = (person.get("last_name") or "").strip()
    combined = " ".join(p for p in [first, last] if p)
    return combined or "Unknown"


def _normalize_domain(domain_or_url: str | None) -> str | None:
    if not domain_or_url:
        return None
    value = domain_or_url.strip().lower()
    value = value.replace("https://", "").replace("http://", "")
    if value.startswith("www."):
        value = value[4:]
    return value.split("/")[0]


# Apollo predefined employee-count ranges
_APOLLO_RANGES = [
    (1, 10), (11, 20), (21, 50), (51, 100), (101, 200),
    (201, 500), (501, 1000), (1001, 2000), (2001, 5000),
    (5001, 10000),
]


def _normalize_employee_ranges(raw_ranges: list[str]) -> list[str]:
    """Map ICP employee ranges (e.g. '10,200') to Apollo's standard buckets."""
    result: set[str] = set()
    for r in raw_ranges:
        parts = r.replace("-", ",").split(",")
        try:
            lo = int(parts[0].strip())
            hi = int(parts[1].strip()) if len(parts) > 1 else lo
        except (ValueError, IndexError):
            continue
        for a_lo, a_hi in _APOLLO_RANGES:
            if a_hi >= lo and a_lo <= hi:
                result.add(f"{a_lo},{a_hi}")
    return sorted(result) if result else ["1,10", "11,20", "21,50", "51,100", "101,200"]
