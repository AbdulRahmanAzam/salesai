from __future__ import annotations

import time
from typing import Any

from prospecting_agent.http_client import HttpClient
from prospecting_agent.models import Company, Contact, ICP
from prospecting_agent.sources.base import ContactSource


class HunterSource(ContactSource):
    name = "hunter"

    def __init__(
        self,
        http: HttpClient,
        api_key: str | None,
        per_domain_limit: int = 25,
        max_domains: int = 15,
    ):
        self.http = http
        self.api_key = api_key
        self.per_domain_limit = max(1, min(10, per_domain_limit))  # Hunter free plan caps at 10
        self.max_domains = max_domains  # Cap total domains to conserve monthly quota
        self._quota_exhausted = False  # Set True on 429 to stop all further requests

    def _enabled(self) -> bool:
        return bool(self.api_key)

    def _check_quota(self) -> int:
        """Return remaining searches, or -1 if check fails."""
        try:
            data = self.http.get(
                "https://api.hunter.io/v2/account",
                params={"api_key": self.api_key},
            )
            searches = data.get("data", {}).get("requests", {}).get("searches", {})
            used = searches.get("used", 0)
            available = searches.get("available", 0)
            remaining = available - used
            print(f"  [hunter] quota: {used}/{available} searches used, {remaining} remaining")
            return remaining
        except Exception:
            return -1  # Can't check, proceed cautiously

    def find_contacts(self, icp: ICP, companies: list[Company]) -> list[Contact]:
        if not self._enabled() or not companies:
            return []

        # Pre-flight quota check
        remaining = self._check_quota()
        if remaining == 0:
            print("  [hunter] monthly search quota exhausted — skipping all domains")
            return []
        if remaining > 0:
            # Each domain can cost 1-2 searches (filtered + unfiltered retry)
            safe_domains = max(1, remaining // 2)
            effective_max = min(self.max_domains, safe_domains)
            print(f"  [hunter] will search up to {effective_max} domains (quota-aware)")
        else:
            effective_max = self.max_domains

        departments = _infer_departments(icp.persona_titles)
        seniorities = _infer_seniorities(icp.persona_titles)

        contacts: list[Contact] = []
        seen_domains: set[str] = set()
        domains_searched = 0

        for company in companies:
            if self._quota_exhausted:
                print("  [hunter] stopping — rate limited (429)")
                break
            if domains_searched >= effective_max:
                print(f"  [hunter] reached domain cap ({effective_max}), stopping")
                break

            domain = _normalize_domain(company.domain)
            if not domain or domain in seen_domains:
                continue

            seen_domains.add(domain)
            domains_searched += 1
            rows = self._fetch_domain_contacts(
                domain,
                company_name=company.name,
                departments=departments,
                seniorities=seniorities,
            )
            for row in rows:
                contacts.append(
                    Contact(
                        full_name=_full_name(row),
                        title=row.get("position"),
                        company_name=(
                            row.get("organization")
                            or company.name
                            or domain.split(".")[0].capitalize()
                        ),
                        company_domain=domain,
                        email=row.get("value"),
                        linkedin_url=row.get("linkedin"),
                        source=self.name,
                        source_url=(
                            f"https://hunter.io/domain/{domain}"
                            if row.get("value")
                            else None
                        ),
                        confidence=_confidence(row),
                        signals=[
                            "Hunter domain-search match",
                            *(
                                [
                                    "Hunter department/seniority filter match"
                                ]
                                if departments or seniorities
                                else []
                            ),
                        ],
                        research_notes=[
                            "Publicly discoverable contact from Hunter domain search."
                        ],
                    )
                )
                if len(contacts) >= icp.max_contacts:
                    return contacts

        return contacts

    def _fetch_domain_contacts(
        self,
        domain: str,
        company_name: str | None,
        departments: list[str] | None = None,
        seniorities: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "api_key": self.api_key,
            "domain": domain,
            "limit": self.per_domain_limit,
            "offset": 0,
        }
        if company_name:
            params["company"] = company_name
        if departments:
            params["department"] = ",".join(departments)
        if seniorities:
            params["seniority"] = ",".join(seniorities)

        data = self._request_domain_search(domain, params)
        if self._quota_exhausted:
            return []
        rows = data.get("data", {}).get("emails", []) or []

        # Filters can be too strict for small domains. Retry once without filters.
        # Skip retry if quota is exhausted.
        if not rows and (departments or seniorities) and not self._quota_exhausted:
            retry_params = {
                "api_key": self.api_key,
                "domain": domain,
                "limit": self.per_domain_limit,
                "offset": 0,
            }
            if company_name:
                retry_params["company"] = company_name
            retry_data = self._request_domain_search(domain, retry_params)
            return retry_data.get("data", {}).get("emails", []) or []

        return rows

    def _request_domain_search(self, domain: str, params: dict[str, Any]) -> dict[str, Any]:
        if self._quota_exhausted:
            return {}
        # Rate-limit: Hunter free plan has strict per-second limits
        time.sleep(2)
        try:
            data = self.http.get("https://api.hunter.io/v2/domain-search", params=params)
        except Exception as exc:
            exc_str = str(exc)
            if "429" in exc_str:
                print(f"[warn] hunter 429 rate-limited on {domain} — stopping all requests")
                self._quota_exhausted = True
                return {}
            print(f"[warn] hunter failed for domain {domain}: {exc}")
            return {}

        if data.get("errors"):
            print(f"[warn] hunter returned API errors for domain {domain}: {data.get('errors')}")
            return {}

        return data


def _normalize_domain(domain_or_url: str | None) -> str | None:
    if not domain_or_url:
        return None
    value = domain_or_url.strip().lower()
    value = value.replace("https://", "").replace("http://", "")
    if value.startswith("www."):
        value = value[4:]
    return value.split("/")[0]


def _full_name(row: dict[str, Any]) -> str:
    first = (row.get("first_name") or "").strip()
    last = (row.get("last_name") or "").strip()
    combined = " ".join([x for x in [first, last] if x]).strip()
    if combined:
        return combined

    email = (row.get("value") or "").strip()
    if email and "@" in email:
        return email.split("@", 1)[0]
    return "Unknown"


def _confidence(row: dict[str, Any]) -> float:
    value = row.get("confidence")
    if value is None:
        return 0.65
    try:
        # Hunter confidence is typically 0-100; normalize to 0-1.
        return max(0.0, min(1.0, float(value) / 100.0))
    except (TypeError, ValueError):
        return 0.65


# Hunter valid department values (https://hunter.io/api-documentation/v2#domain-search)
_VALID_DEPARTMENTS = {
    "executive", "it", "finance", "management", "communication",
    "education", "design", "hr", "legal", "marketing",
    "operations", "sales", "support",
}


def _infer_departments(persona_titles: list[str]) -> list[str]:
    blob = " ".join([t.lower() for t in persona_titles])
    mapped: list[str] = []

    if any(k in blob for k in ["cto", "engineering", "platform", "devops", "sre", "it"]):
        mapped.append("it")
    if any(k in blob for k in ["operations", "ops"]):
        mapped.append("operations")
    if any(k in blob for k in ["founder", "co-founder", "ceo", "owner", "president"]):
        mapped.append("executive")
    if any(k in blob for k in ["marketing", "growth"]):
        mapped.append("marketing")
    if any(k in blob for k in ["sales", "revenue", "bizdev", "business development"]):
        mapped.append("sales")
    if any(k in blob for k in ["manager", "director", "head of", "vp"]):
        mapped.append("management")

    # Safety: only return values Hunter actually accepts
    return sorted(set(mapped) & _VALID_DEPARTMENTS)


# Hunter valid seniority values: junior, senior, executive
_VALID_SENIORITIES = {"junior", "senior", "executive"}


def _infer_seniorities(persona_titles: list[str]) -> list[str]:
    blob = " ".join([t.lower() for t in persona_titles])
    mapped: list[str] = []

    if any(k in blob for k in ["founder", "co-founder", "ceo", "cto", "cfo", "coo", "chief",
                                "vp", "vice president", "head", "director", "president"]):
        mapped.append("executive")
    if any(k in blob for k in ["lead", "principal", "staff", "manager"]):
        mapped.append("senior")

    # Safety: only return values Hunter actually accepts
    return sorted(set(mapped) & _VALID_SENIORITIES)
