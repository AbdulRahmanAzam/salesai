"""Reddit company source — searches Reddit for companies matching ICP.

Uses Reddit's public JSON API (no authentication required).
Searches relevant subreddits like r/startups, r/SaaS, r/Entrepreneur, etc.
"""
from __future__ import annotations

import re
from typing import Any

from prospecting_agent.http_client import HttpClient
from prospecting_agent.models import Company, ICP
from prospecting_agent.sources.base import CompanySource

_DOMAIN_RE = re.compile(r"https?://(?:www\.)?([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,})")

_SKIP_DOMAINS = {
    "reddit.com", "redd.it", "imgur.com", "i.redd.it",
    "github.com", "gitlab.com", "bitbucket.org",
    "youtube.com", "youtu.be", "medium.com", "twitter.com", "x.com",
    "linkedin.com", "facebook.com", "instagram.com",
    "wikipedia.org", "google.com", "docs.google.com",
    "stackoverflow.com", "stackexchange.com",
    "news.ycombinator.com", "ycombinator.com",
    "techcrunch.com", "theverge.com", "wired.com",
    "pastebin.com", "gist.github.com",
}

_SUBREDDITS = [
    "startups", "SaaS", "Entrepreneur", "smallbusiness",
    "webdev", "devops", "machinelearning", "artificial",
    "selfhosted", "sideproject", "indiehackers",
]


class RedditCompanySource(CompanySource):
    """Discovers companies from Reddit posts and comments."""

    name = "reddit"

    def __init__(self, http: HttpClient):
        self.http = http

    def find_companies(self, icp: ICP) -> list[Company]:
        queries = self._build_queries(icp)
        companies: list[Company] = []
        seen_domains: set[str] = set()

        for query in queries[:4]:  # Limit queries to avoid rate limiting
            try:
                data = self.http.session.get(
                    "https://www.reddit.com/search.json",
                    params={
                        "q": query,
                        "sort": "relevance",
                        "t": "year",
                        "limit": 25,
                        "restrict_sr": False,
                    },
                    headers={"User-Agent": "SalesIntelligenceBot/1.0"},
                    timeout=self.http.timeout_seconds,
                )
                if data.status_code != 200:
                    continue

                result = data.json()
                posts = result.get("data", {}).get("children", [])

                for post in posts:
                    post_data = post.get("data", {})
                    url = post_data.get("url", "")
                    selftext = post_data.get("selftext", "")
                    title = post_data.get("title", "")

                    # Extract domains from post URL and body
                    domains = set()
                    for text in [url, selftext]:
                        for match in _DOMAIN_RE.finditer(text):
                            d = match.group(1).lower()
                            if d not in _SKIP_DOMAINS and d not in seen_domains:
                                domains.add(d)

                    for domain in domains:
                        seen_domains.add(domain)
                        name = domain.split(".")[0].capitalize()
                        companies.append(
                            Company(
                                name=name,
                                domain=domain,
                                source=self.name,
                                source_url=f"https://reddit.com{post_data.get('permalink', '')}",
                                notes=[f"Found via Reddit: '{title[:80]}'"],
                            )
                        )
                        if len(companies) >= icp.max_companies:
                            return companies

            except Exception as exc:
                print(f"  [warn] Reddit search failed for '{query}': {exc}")
                continue

        return companies

    def _build_queries(self, icp: ICP) -> list[str]:
        queries: list[str] = []
        if icp.keywords:
            queries.append(" ".join(icp.keywords[:3]))
        if icp.industries:
            for ind in icp.industries[:2]:
                queries.append(f"{ind} startup")
        if icp.search_queries:
            queries.extend(icp.search_queries[:2])
        if icp.product_name:
            queries.append(f"{icp.product_name} alternative")
        if not queries:
            queries.append(icp.product_name or "startup")
        return queries
