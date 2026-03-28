from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from prospecting_agent.http_client import HttpClient
from research_agent.sources.base import ResearchSource

HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1"


class HNSearchSource(ResearchSource):
    """Uses the Hacker News Algolia API (free, no key) to find mentions and activity."""

    name = "hn_algolia"

    def __init__(self, http: HttpClient):
        self.http = http

    def _search(self, query: str, tags: str | None = None, hits: int = 10) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "query": query,
            "hitsPerPage": min(hits, 20),
        }
        if tags:
            params["tags"] = tags
        try:
            data = self.http.get(f"{HN_ALGOLIA_URL}/search", params=params)
            return data.get("hits", [])
        except Exception as exc:
            print(f"[warn] hn_algolia search failed for '{query}': {exc}")
            return []

    def _search_recent(self, query: str, tags: str | None = None, hits: int = 10) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "query": query,
            "hitsPerPage": min(hits, 20),
        }
        if tags:
            params["tags"] = tags
        try:
            data = self.http.get(f"{HN_ALGOLIA_URL}/search_by_date", params=params)
            return data.get("hits", [])
        except Exception as exc:
            print(f"[warn] hn_algolia date search failed for '{query}': {exc}")
            return []

    def research_company(self, company_name: str, domain: str | None) -> dict[str, Any]:
        query = company_name
        if domain:
            query = f"{company_name} OR {domain}"

        stories = self._search(query, tags="story", hits=8)
        recent = self._search_recent(query, tags="story", hits=5)

        all_hits = {h.get("objectID"): h for h in stories + recent}

        news: list[dict[str, str | None]] = []
        for hit in all_hits.values():
            news.append({
                "title": hit.get("title") or hit.get("story_title", ""),
                "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                "source": "hacker_news",
                "published_date": _format_ts(hit.get("created_at_i")),
                "snippet": hit.get("story_text", "")[:300] if hit.get("story_text") else None,
            })

        return {
            "recent_news": news,
            "_raw": {"hn_hits": list(all_hits.values())},
        }

    def research_person(
        self,
        full_name: str,
        company_name: str | None,
        domain: str | None,
    ) -> dict[str, Any]:
        query = f'"{full_name}"'

        stories = self._search(query, tags="story", hits=5)
        comments = self._search(query, tags="comment", hits=5)

        activities: list[dict[str, str | None]] = []
        topics: set[str] = set()

        for hit in stories:
            title = hit.get("title") or ""
            activities.append({
                "activity_type": "hn_story",
                "title": title,
                "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                "date": _format_ts(hit.get("created_at_i")),
                "snippet": hit.get("story_text", "")[:300] if hit.get("story_text") else None,
            })
            if title:
                topics.update(_extract_topics(title))

        for hit in comments:
            text = hit.get("comment_text", "") or ""
            activities.append({
                "activity_type": "hn_comment",
                "title": hit.get("story_title") or "HN Comment",
                "url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                "date": _format_ts(hit.get("created_at_i")),
                "snippet": _strip_html(text)[:300],
            })

        author_hits = self._search(full_name.split()[0] if full_name else "", tags="story", hits=3)
        for hit in author_hits:
            if hit.get("author") and full_name.lower().split()[0] in (hit.get("author") or "").lower():
                activities.append({
                    "activity_type": "hn_submission",
                    "title": hit.get("title", ""),
                    "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                    "date": _format_ts(hit.get("created_at_i")),
                    "snippet": None,
                })

        return {
            "recent_activity": activities,
            "mutual_interests": sorted(topics)[:10],
            "_raw": {"hn_stories": stories, "hn_comments": comments},
        }


def _format_ts(ts: int | None) -> str | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    except (OSError, ValueError):
        return None


def _strip_html(text: str) -> str:
    import re
    return re.sub(r"<[^>]+>", " ", text).strip()


def _extract_topics(title: str) -> list[str]:
    keywords = [
        "ai", "ml", "saas", "devops", "kubernetes", "cloud", "security",
        "startup", "fundraising", "open source", "api", "database",
        "frontend", "backend", "infrastructure", "observability",
        "analytics", "fintech", "crypto", "blockchain",
    ]
    title_lower = title.lower()
    return [k for k in keywords if k in title_lower]
