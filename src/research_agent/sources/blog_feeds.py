from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote_plus

from prospecting_agent.http_client import HttpClient
from research_agent.sources.base import ResearchSource


class BlogFeedSource(ResearchSource):
    """Checks DEV.to and Medium RSS feeds for a person's blog activity."""

    name = "blog_feeds"

    def __init__(self, http: HttpClient):
        self.http = http

    def research_company(self, company_name: str, domain: str | None) -> dict[str, Any]:
        return {}

    def research_person(
        self,
        full_name: str,
        company_name: str | None,
        domain: str | None,
    ) -> dict[str, Any]:
        activities: list[dict[str, str | None]] = []
        skills: list[str] = []

        devto_posts = self._search_devto(full_name)
        for post in devto_posts:
            activities.append({
                "activity_type": "blog_post",
                "title": post.get("title", ""),
                "url": post.get("url", ""),
                "date": (post.get("published_at") or "")[:10] or None,
                "snippet": post.get("description"),
            })
            for tag in post.get("tag_list", []):
                if tag and tag not in skills:
                    skills.append(tag)

        username_guess = _guess_username(full_name)
        if username_guess:
            medium_posts = self._fetch_medium_rss(username_guess)
            for mp in medium_posts:
                activities.append({
                    "activity_type": "blog_post",
                    "title": mp.get("title", ""),
                    "url": mp.get("url", ""),
                    "date": mp.get("pub_date"),
                    "snippet": mp.get("description"),
                })

        return {
            "recent_activity": activities,
            "skills": skills[:10],
            "_raw": {"devto_posts": devto_posts},
        }

    def _search_devto(self, name: str) -> list[dict[str, Any]]:
        # First try searching articles by username guess
        username = _guess_username(name)
        if username:
            url = "https://dev.to/api/articles"
            params = {"username": username, "per_page": 5}
            try:
                data = self.http.get(url, params=params)
                if isinstance(data, list) and data:
                    return data
            except Exception:
                pass

        # Fallback: use the DEV.to search API with the full name
        try:
            search_url = f"https://dev.to/api/articles?per_page=5&tag=&top=365"
            resp = self.http.session.get(
                "https://dev.to/api/articles/search",
                params={"q": name, "per_page": 5},
                timeout=self.http.timeout_seconds,
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    return data
        except Exception:
            pass

        # Last resort: scrape the search page
        try:
            resp = self.http.session.get(
                f"https://dev.to/search/feed_content",
                params={"per_page": 5, "page": 0, "search_fields": name, "class_name": "Article"},
                timeout=self.http.timeout_seconds,
            )
            if resp.status_code == 200:
                data = resp.json()
                result = data.get("result", [])
                if isinstance(result, list) and result:
                    return result
        except Exception:
            pass

        return []

    def _fetch_medium_rss(self, username: str) -> list[dict[str, str | None]]:
        url = f"https://medium.com/feed/@{username}"
        try:
            resp = self.http.session.get(url, timeout=self.http.timeout_seconds)
            resp.raise_for_status()
            return _parse_rss_items(resp.text, max_items=5)
        except Exception:
            return []


def _guess_username(full_name: str) -> str:
    parts = full_name.lower().strip().split()
    if len(parts) >= 2:
        return parts[0] + parts[-1]
    return parts[0] if parts else ""


def _parse_rss_items(xml_text: str, max_items: int) -> list[dict[str, str | None]]:
    items: list[dict[str, str | None]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    channel = root.find("channel")
    if channel is None:
        channel = root

    for item_el in channel.findall("item"):
        if len(items) >= max_items:
            break
        title = (item_el.findtext("title") or "").strip()
        link = (item_el.findtext("link") or "").strip()
        pub_date = (item_el.findtext("pubDate") or "").strip() or None
        desc_raw = (item_el.findtext("description") or "").strip()
        description = re.sub(r"<[^>]+>", " ", desc_raw)[:300] if desc_raw else None

        if title or link:
            items.append({
                "title": title,
                "url": link,
                "pub_date": pub_date,
                "description": description,
            })
    return items
