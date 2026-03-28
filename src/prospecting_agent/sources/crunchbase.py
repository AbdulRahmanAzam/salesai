"""Crunchbase company source — searches Crunchbase for companies matching ICP.

Uses Crunchbase's public autocomplete/search endpoints (no API key required).
The autocomplete endpoint returns basic company info for free.
"""
from __future__ import annotations

import re
from typing import Any

from prospecting_agent.http_client import HttpClient
from prospecting_agent.models import Company, ICP
from prospecting_agent.sources.base import CompanySource


class CrunchbaseSource(CompanySource):
    """Discovers companies from Crunchbase's public autocomplete API."""

    name = "crunchbase"

    _AUTOCOMPLETE_URL = "https://www.crunchbase.com/v4/data/autocompletes"

    def __init__(self, http: HttpClient):
        self.http = http

    def find_companies(self, icp: ICP) -> list[Company]:
        queries = self._build_queries(icp)
        companies: list[Company] = []
        seen_domains: set[str] = set()

        for query in queries[:5]:
            try:
                resp = self.http.session.get(
                    self._AUTOCOMPLETE_URL,
                    params={
                        "query": query,
                        "collection_ids": "organizations",
                        "limit": 10,
                    },
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    },
                    timeout=self.http.timeout_seconds,
                )
                if resp.status_code != 200:
                    print(f"  [warn] Crunchbase returned {resp.status_code} for '{query}'")
                    continue

                data = resp.json()
                entities = data.get("entities", [])

                for entity in entities:
                    props = entity.get("identifier", {})
                    name = props.get("value", "")
                    permalink = props.get("permalink", "")
                    entity_id = props.get("entity_def_id", "")

                    if entity_id != "organization" or not name:
                        continue

                    # Try to get domain from short description or use permalink
                    short_desc = entity.get("short_description", "")
                    facet_ids = entity.get("facet_ids", [])

                    # Derive domain from permalink (best guess)
                    # e.g. permalink "stripe" → stripe.com
                    domain_guess = f"{permalink}.com" if permalink else ""

                    if domain_guess in seen_domains:
                        continue
                    if domain_guess:
                        seen_domains.add(domain_guess)

                    industry = ", ".join(facet_ids[:3]) if facet_ids else ""

                    companies.append(
                        Company(
                            name=name,
                            domain=domain_guess,
                            industry=industry,
                            description=short_desc[:200] if short_desc else "",
                            source=self.name,
                            source_url=f"https://www.crunchbase.com/organization/{permalink}" if permalink else "",
                            notes=[f"Crunchbase match for '{query}'"],
                        )
                    )
                    if len(companies) >= icp.max_companies:
                        return companies

            except Exception as exc:
                print(f"  [warn] Crunchbase search failed for '{query}': {exc}")
                continue

        return companies

    def _build_queries(self, icp: ICP) -> list[str]:
        queries: list[str] = []
        if icp.keywords:
            for kw in icp.keywords[:3]:
                queries.append(kw)
        if icp.industries:
            queries.extend(icp.industries[:2])
        if icp.search_queries:
            queries.extend(icp.search_queries[:2])
        if not queries:
            queries.append(icp.product_name or "startup")
        # Deduplicate
        seen: set[str] = set()
        unique: list[str] = []
        for q in queries:
            ql = q.lower().strip()
            if ql and ql not in seen:
                seen.add(ql)
                unique.append(q)
        return unique
