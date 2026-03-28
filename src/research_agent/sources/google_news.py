from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote_plus

from prospecting_agent.http_client import HttpClient
from research_agent.sources.base import ResearchSource

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"


class GoogleNewsSource(ResearchSource):
    """Pulls recent news via Google News RSS feed (free, no API key)."""

    name = "google_news_rss"

    def __init__(self, http: HttpClient):
        self.http = http

    def _fetch_rss(self, query: str, max_items: int = 8) -> list[dict[str, str | None]]:
        url = f"{GOOGLE_NEWS_RSS}?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
        try:
            resp = self.http.session.get(url, timeout=self.http.timeout_seconds)
            resp.raise_for_status()
            return _parse_rss(resp.text, max_items)
        except Exception as exc:
            print(f"[warn] google_news_rss fetch failed for '{query}': {exc}")
            return []

    def research_company(self, company_name: str, domain: str | None) -> dict[str, Any]:
        query = f'"{company_name}"'
        items = self._fetch_rss(query, max_items=10)

        if domain and len(items) < 3:
            domain_items = self._fetch_rss(domain.split(".")[0], max_items=5)
            seen_titles = {i["title"] for i in items}
            for di in domain_items:
                if di["title"] not in seen_titles:
                    items.append(di)

        news = [
            {
                "title": i["title"],
                "url": i["url"],
                "source": i.get("source", "google_news"),
                "published_date": i.get("pub_date"),
                "snippet": i.get("description"),
            }
            for i in items
        ]
        return {
            "recent_news": news,
            "_raw": {"google_news_items": items},
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

        items = self._fetch_rss(query, max_items=8)

        activities = [
            {
                "activity_type": "news_mention",
                "title": i["title"],
                "url": i["url"],
                "date": i.get("pub_date"),
                "snippet": i.get("description"),
            }
            for i in items
        ]
        return {
            "recent_activity": activities,
            "_raw": {"google_news_items": items},
        }


def _parse_rss(xml_text: str, max_items: int) -> list[dict[str, str | None]]:
    items: list[dict[str, str | None]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    ns = ""
    channel = root.find(f"{ns}channel")
    if channel is None:
        channel = root

    for item_el in channel.findall(f"{ns}item"):
        if len(items) >= max_items:
            break
        title = (item_el.findtext(f"{ns}title") or "").strip()
        link = (item_el.findtext(f"{ns}link") or "").strip()
        pub_date = (item_el.findtext(f"{ns}pubDate") or "").strip() or None
        description_raw = (item_el.findtext(f"{ns}description") or "").strip()
        description = _strip_html(description_raw)[:500] if description_raw else None
        source_el = item_el.findtext(f"{ns}source")
        source = source_el.strip() if source_el else "google_news"

        if title or link:
            items.append({
                "title": title,
                "url": link,
                "pub_date": pub_date,
                "description": description,
                "source": source,
            })
    return items


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()
