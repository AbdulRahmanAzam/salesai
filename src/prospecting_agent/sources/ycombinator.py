"""Y Combinator company source — searches the YC company directory.

Uses the public YC Algolia index (same API that ycombinator.com/companies uses).
No authentication required.
"""
from __future__ import annotations

import re
from typing import Any

from prospecting_agent.http_client import HttpClient
from prospecting_agent.models import Company, ICP
from prospecting_agent.sources.base import CompanySource


class YCombinatorSource(CompanySource):
    """Discovers companies from Y Combinator's public company directory."""

    name = "ycombinator"

    _ALGOLIA_URL = "https://45bwzj1sgc-dsn.algolia.net/1/indexes/YCCompany_production/query"
    _ALGOLIA_APP_ID = "45BWZJ1SGC"
    _ALGOLIA_API_KEY = "MjBjYjRiMzY0NzdhZWY0NjExY2NhZjYxMGIxYjc2MTAwNWFkNTkwNTc4NjgxYjU0YzFhYTY2ZGQ5OGY5NDMzZnJlc3RyaWN0SW5kaWNlcz0lNUIlMjJZQ0NvbXBhbnlfcHJvZHVjdGlvbiUyMiU1RCZ0YWdGaWx0ZXJzPSU1QiUyMnN0YXR1c19zdHJpbmclM0FBY3RpdmUlMjIlNUQmYW5hbHl0aWNzVGFncz0lNUIlMjJ5Y2RjJTIyJTVE"

    def __init__(self, http: HttpClient):
        self.http = http

    def find_companies(self, icp: ICP) -> list[Company]:
        queries = self._build_queries(icp)
        companies: list[Company] = []
        seen_domains: set[str] = set()

        for query in queries[:5]:
            try:
                resp = self.http.session.post(
                    self._ALGOLIA_URL,
                    json={
                        "query": query,
                        "hitsPerPage": min(20, icp.max_companies),
                        "page": 0,
                    },
                    headers={
                        "X-Algolia-Application-Id": self._ALGOLIA_APP_ID,
                        "X-Algolia-API-Key": self._ALGOLIA_API_KEY,
                        "Content-Type": "application/json",
                    },
                    timeout=self.http.timeout_seconds,
                )
                if resp.status_code != 200:
                    print(f"  [warn] YC Algolia returned {resp.status_code} for '{query}'")
                    continue

                data = resp.json()
                hits = data.get("hits", [])

                for hit in hits:
                    name = hit.get("name", "")
                    url = hit.get("website") or hit.get("url") or ""
                    domain = self._extract_domain(url)

                    if not domain or domain in seen_domains:
                        continue
                    seen_domains.add(domain)

                    one_liner = hit.get("one_liner", "")
                    batch = hit.get("batch", "")
                    team_size_str = hit.get("team_size", "")
                    industry = hit.get("industry", "") or ", ".join(hit.get("tags", [])[:3])
                    yc_slug = hit.get("slug", "")

                    employee_range = ""
                    if isinstance(team_size_str, (int, float)):
                        employee_range = f"{int(team_size_str)}"
                    elif isinstance(team_size_str, str) and team_size_str:
                        employee_range = team_size_str

                    companies.append(
                        Company(
                            name=name,
                            domain=domain,
                            industry=industry,
                            description=one_liner,
                            employee_range=employee_range,
                            source=self.name,
                            source_url=f"https://www.ycombinator.com/companies/{yc_slug}" if yc_slug else url,
                            notes=[f"YC Batch: {batch}"] if batch else [],
                        )
                    )
                    if len(companies) >= icp.max_companies:
                        return companies

            except Exception as exc:
                print(f"  [warn] YC search failed for '{query}': {exc}")
                continue

        return companies

    def _build_queries(self, icp: ICP) -> list[str]:
        queries: list[str] = []
        if icp.keywords:
            queries.append(" ".join(icp.keywords[:3]))
            for kw in icp.keywords[:2]:
                queries.append(kw)
        if icp.industries:
            queries.extend(icp.industries[:2])
        if icp.search_queries:
            queries.extend(icp.search_queries[:2])
        if not queries:
            queries.append(icp.product_name or "AI")
        # Deduplicate
        seen: set[str] = set()
        unique: list[str] = []
        for q in queries:
            ql = q.lower().strip()
            if ql and ql not in seen:
                seen.add(ql)
                unique.append(q)
        return unique

    @staticmethod
    def _extract_domain(url: str) -> str | None:
        if not url:
            return None
        m = re.search(r"https?://(?:www\.)?([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,})", url)
        return m.group(1).lower() if m else None
