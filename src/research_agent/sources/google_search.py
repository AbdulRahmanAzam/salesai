from __future__ import annotations

from typing import Any

from prospecting_agent.http_client import HttpClient
from research_agent.sources.base import ResearchSource

GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"


class GoogleSearchSource(ResearchSource):
    """Uses Google Custom Search Engine JSON API to find public mentions."""

    name = "google_cse"

    def __init__(self, http: HttpClient, api_key: str | None, cx: str | None):
        self.http = http
        self.api_key = api_key
        self.cx = cx

    def _enabled(self) -> bool:
        return bool(self.api_key and self.cx)

    def _search(self, query: str, num: int = 5) -> list[dict[str, Any]]:
        if not self._enabled():
            return []
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

    def research_company(self, company_name: str, domain: str | None) -> dict[str, Any]:
        query = f'"{company_name}"'
        if domain:
            query += f" OR site:{domain}"

        items = self._search(query, num=8)
        news: list[dict[str, str | None]] = []
        description_candidates: list[str] = []

        for item in items:
            snippet = item.get("snippet", "")
            news.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "source": "google_cse",
                "published_date": item.get("pagemap", {}).get("metatags", [{}])[0].get("article:published_time") if item.get("pagemap") else None,
                "snippet": snippet,
            })
            if snippet and len(snippet) > 40:
                description_candidates.append(snippet)

        return {
            "recent_news": news,
            "description": description_candidates[0] if description_candidates else None,
            "_raw": {"google_cse_results": items},
        }

    def research_person(
        self,
        full_name: str,
        company_name: str | None,
        domain: str | None,
    ) -> dict[str, Any]:
        query = f'"{full_name}"'
        if company_name:
            query += f' "{company_name}"'

        items = self._search(query, num=8)
        activities: list[dict[str, str | None]] = []
        bio_candidates: list[str] = []

        for item in items:
            snippet = item.get("snippet", "")
            link = item.get("link", "")
            activities.append({
                "activity_type": _classify_result(link),
                "title": item.get("title", ""),
                "url": link,
                "snippet": snippet,
            })
            if snippet and len(snippet) > 40:
                bio_candidates.append(snippet)

        return {
            "recent_activity": activities,
            "bio": bio_candidates[0] if bio_candidates else None,
            "_raw": {"google_cse_results": items},
        }


def _classify_result(url: str) -> str:
    url_lower = url.lower()
    if "linkedin.com" in url_lower:
        return "linkedin_mention"
    if "github.com" in url_lower:
        return "github_mention"
    if "twitter.com" in url_lower or "x.com" in url_lower:
        return "twitter_mention"
    if "youtube.com" in url_lower:
        return "talk_or_interview"
    if any(s in url_lower for s in ["medium.com", "dev.to", "substack.com", "hashnode"]):
        return "blog_post"
    if any(s in url_lower for s in ["techcrunch", "reuters", "bloomberg", "forbes"]):
        return "press_mention"
    return "web_mention"
