from __future__ import annotations

from typing import Any

from prospecting_agent.http_client import HttpClient
from research_agent.sources.base import ResearchSource

BUILTWITH_FREE_URL = "https://api.builtwith.com/free1/api.json"


class BuiltWithSource(ResearchSource):
    """Uses the BuiltWith free-tier API to detect tech stack from a domain."""

    name = "builtwith"

    def __init__(self, http: HttpClient, api_key: str | None = None):
        self.http = http
        self.api_key = api_key

    def research_company(self, company_name: str, domain: str | None) -> dict[str, Any]:
        if not domain:
            return {}

        technologies: list[str] = []
        raw_groups: list[dict[str, Any]] = []

        if self.api_key:
            techs, raw = self._fetch_paid(domain)
            technologies = techs
            raw_groups = raw
        else:
            techs, raw = self._fetch_free(domain)
            technologies = techs
            raw_groups = raw

        return {
            "technologies": technologies[:30],
            "_raw": {"builtwith_groups": raw_groups},
        }

    def research_person(
        self,
        full_name: str,
        company_name: str | None,
        domain: str | None,
    ) -> dict[str, Any]:
        return {}

    def _fetch_free(self, domain: str) -> tuple[list[str], list[dict[str, Any]]]:
        params = {"KEY": self.api_key or "free", "LOOKUP": domain}
        try:
            data = self.http.get(BUILTWITH_FREE_URL, params=params)
        except Exception as exc:
            print(f"[warn] builtwith free lookup failed for {domain}: {exc}")
            return [], []

        technologies: list[str] = []
        groups = data.get("groups", []) or []
        for group in groups:
            for cat in group.get("categories", []):
                for tech in cat.get("live", []):
                    name = tech.get("Name")
                    if name and name not in technologies:
                        technologies.append(name)
        return technologies, groups

    def _fetch_paid(self, domain: str) -> tuple[list[str], list[dict[str, Any]]]:
        url = f"https://api.builtwith.com/v21/api.json"
        params = {"KEY": self.api_key, "LOOKUP": domain}
        try:
            data = self.http.get(url, params=params)
        except Exception as exc:
            print(f"[warn] builtwith paid lookup failed for {domain}: {exc}")
            return self._fetch_free(domain)

        technologies: list[str] = []
        results = data.get("Results", []) or []
        for result in results:
            for path_entry in result.get("Result", {}).get("Paths", []):
                for tech in path_entry.get("Technologies", []):
                    name = tech.get("Name")
                    if name and name not in technologies:
                        technologies.append(name)
        return technologies, results
