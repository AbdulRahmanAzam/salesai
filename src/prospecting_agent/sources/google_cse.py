from __future__ import annotations

import re
from typing import Any

from prospecting_agent.http_client import HttpClient
from prospecting_agent.models import Company, ICP
from prospecting_agent.sources.base import CompanySource

GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"


class GoogleCSECompanySource(CompanySource):
    """Uses Google Custom Search to discover companies from ICP search queries."""

    name = "google_cse"

    def __init__(self, http: HttpClient, api_key: str | None, cx: str | None):
        self.http = http
        self.api_key = api_key
        self.cx = cx

    def _enabled(self) -> bool:
        return bool(self.api_key and self.cx)

    def find_companies(self, icp: ICP) -> list[Company]:
        if not self._enabled():
            return []

        queries = icp.search_queries[:5]
        if not queries:
            queries = [f"{icp.product_name} {' '.join(icp.keywords[:3])} companies"]

        companies: list[Company] = []
        seen_domains: set[str] = set()

        for query in queries:
            results = self._search(query)
            for item in results:
                link = item.get("link", "")
                domain = _extract_domain(link)
                if not domain or domain in seen_domains:
                    continue
                if _is_aggregator(domain):
                    continue
                seen_domains.add(domain)

                title = item.get("title", "")
                snippet = item.get("snippet", "")
                company_name = _infer_company_name(title, domain)

                companies.append(
                    Company(
                        name=company_name,
                        domain=domain,
                        description=snippet[:300] if snippet else None,
                        source=self.name,
                        source_url=link,
                        notes=[f"Found via search: {query[:80]}"],
                    )
                )
                if len(companies) >= icp.max_companies:
                    return companies

        return companies

    def _search(self, query: str, num: int = 10) -> list[dict[str, Any]]:
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": min(num, 10),
        }
        try:
            data = self.http.get(GOOGLE_CSE_URL, params=params)
            return data.get("items", [])
        except Exception as exc:
            print(f"[warn] google_cse search failed for '{query}': {exc}")
            return []


def _extract_domain(url: str) -> str | None:
    match = re.search(r"https?://([^/]+)", url)
    if not match:
        return None
    domain = match.group(1).lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def _is_aggregator(domain: str) -> bool:
    aggregators = {
        "linkedin.com", "twitter.com", "x.com", "facebook.com", "instagram.com",
        "youtube.com", "reddit.com", "wikipedia.org", "crunchbase.com",
        "glassdoor.com", "indeed.com", "yelp.com", "bbb.org",
        "google.com", "bing.com", "yahoo.com", "amazon.com",
        "medium.com", "substack.com", "github.com",
    }
    return domain in aggregators or any(domain.endswith(f".{a}") for a in aggregators)


def _infer_company_name(title: str, domain: str) -> str:
    if " - " in title:
        return title.split(" - ")[0].strip()
    if " | " in title:
        return title.split(" | ")[0].strip()
    return domain.split(".")[0].replace("-", " ").title()
