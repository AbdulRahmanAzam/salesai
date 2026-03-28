"""Web scraper contact source using BeautifulSoup.

Scrapes company websites (team, about, leadership pages) to extract
real names, titles, and LinkedIn profile URLs.
"""
from __future__ import annotations

import re
import time
from typing import Any

from prospecting_agent.http_client import HttpClient
from prospecting_agent.models import Company, Contact, ICP
from prospecting_agent.sources.base import ContactSource

# Common paths that contain team/leadership info (ordered by likelihood)
_TEAM_PATHS = [
    "/team",
    "/about",
    "/about-us",
]

# Patterns that match "Name - Title" type structures in HTML
_NAME_RE = re.compile(
    r"\b((?:[A-Z][a-z' -]+\s+){1,2}[A-Z][a-z' -]+)\b"
)
_TITLE_KEYWORDS = [
    "chief technology", "cto", "vp engineering", "vice president engineering",
    "head of engineering", "head of platform", "vp of engineering",
    "director of engineering", "chief engineer", "devops manager",
    "platform engineer", "site reliability", "vp infrastructure",
    "engineering manager", "chief architect", "co-founder",
    "founder", "principal engineer",
]

_LINKEDIN_RE = re.compile(
    r'href=["\']?(https?://(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?)["\']?'
)


class WebScraperContactSource(ContactSource):
    """Scrapes company websites for team member names and LinkedIn URLs."""

    name = "web_scraper"

    def __init__(self, http: HttpClient, max_domains: int = 15):
        self.http = http
        self.max_domains = max_domains

    def find_contacts(self, icp: ICP, companies: list[Company]) -> list[Contact]:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            print("  [warn] BeautifulSoup not installed. Run: pip install beautifulsoup4")
            return []

        contacts: list[Contact] = []
        seen: set[str] = set()

        for company in companies[:self.max_domains]:
            if not company.domain:
                continue

            found = self._scrape_company(company, icp)
            for contact in found:
                key = contact.key()
                if key not in seen:
                    seen.add(key)
                    contacts.append(contact)

            time.sleep(0.3)  # polite delay

        print(f"  [web_scraper] Found {len(contacts)} contacts via web scraping")
        return contacts

    def _scrape_company(self, company: Company, icp: ICP) -> list[Contact]:
        """Try several paths to find team contact information."""
        from bs4 import BeautifulSoup

        base = f"https://{company.domain}"
        contacts: list[Contact] = []

        for path in _TEAM_PATHS:
            url = base + path
            try:
                resp = self.http.session.get(url, timeout=5, allow_redirects=True)
                if resp.status_code != 200:
                    continue
                content_type = resp.headers.get("content-type", "")
                if "html" not in content_type:
                    continue
                if len(resp.content) < 500:
                    continue
            except Exception:
                continue

            html = resp.text
            soup = BeautifulSoup(html, "lxml")

            # Remove script and style elements
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()

            page_text = soup.get_text(separator=" ", strip=True)

            # Extract LinkedIn URLs from the page
            linkedin_urls = set(_LINKEDIN_RE.findall(html))

            # Try to find person cards/sections
            found = _extract_contacts_from_page(
                page_text, linkedin_urls, company, icp
            )
            if found:
                contacts.extend(found)
                break  # Found something, no need to try more paths

        return contacts


def _extract_contacts_from_page(
    text: str,
    linkedin_urls: set[str],
    company: Company,
    icp: ICP,
) -> list[Contact]:
    """Parse contact info from scraped page text."""
    contacts: list[Contact] = []
    seen_names: set[str] = set()

    # Look for patterns like "John Smith, CTO" or "Jane Doe\nVP Engineering"
    # Split text into chunks around linebreaks
    chunks = re.split(r'[\n\r]{1,3}', text)

    for i, chunk in enumerate(chunks):
        chunk = chunk.strip()
        if len(chunk) > 200 or len(chunk) < 3:
            continue

        # Check if this chunk contains a relevant title
        chunk_lower = chunk.lower()
        matched_title = next(
            (t for t in _TITLE_KEYWORDS if t in chunk_lower), None
        )
        if not matched_title:
            continue

        # Look for a name in adjacent chunks
        window = chunks[max(0, i-2):i+3]
        name = _find_best_name(window)
        if not name or name in seen_names:
            continue

        seen_names.add(name)

        # Try to find a clean title
        title = _extract_title(chunk)

        # Find a LinkedIn URL that might match
        li_url = _find_matching_linkedin(name, linkedin_urls)

        contacts.append(Contact(
            full_name=name,
            title=title or matched_title.title(),
            company_name=company.name,
            company_domain=company.domain,
            linkedin_url=li_url,
            source="web_scraper",
            confidence=0.6 if li_url else 0.4,
            signals=["team page scrape"],
        ))

    return contacts


def _find_best_name(chunks: list[str]) -> str | None:
    """Find the most likely person's name from a list of text chunks."""
    candidate: str | None = None
    for chunk in chunks:
        chunk = chunk.strip()
        if len(chunk) > 60:  # Likely not just a name
            continue
        m = _NAME_RE.search(chunk)
        if m:
            name = m.group(0).strip()
            # Reject if it looks like a company name or generic phrase
            if name.lower() in {"the platform", "our team", "meet our", "learn more"}:
                continue
            if len(name.split()) in (2, 3):
                candidate = name
                break
    return candidate


def _extract_title(text: str) -> str | None:
    """Extract a job title from text."""
    text = text.strip()
    # Common pattern: "Name - Title" or "Title\nName"
    for sep in [" - ", " | ", " — ", ", ", "\n"]:
        parts = text.split(sep)
        if len(parts) >= 2:
            # The shorter non-name part is likely the title
            for part in parts:
                part = part.strip()
                if 3 < len(part) < 80:
                    part_lower = part.lower()
                    if any(kw in part_lower for kw in _TITLE_KEYWORDS):
                        return part
    # If the whole chunk is a title
    if len(text) < 80 and any(kw in text.lower() for kw in _TITLE_KEYWORDS):
        return text
    return None


def _find_matching_linkedin(name: str, linkedin_urls: set[str]) -> str | None:
    """Try to match a person's name to a LinkedIn URL."""
    if not linkedin_urls:
        return None
    name_lower = name.lower().replace(" ", "").replace(".", "").replace("-", "")
    for url in linkedin_urls:
        url_slug = url.rstrip("/").split("/")[-1].lower().replace("-", "")
        if name_lower[:6] in url_slug or url_slug[:6] in name_lower:
            return url
    return None
