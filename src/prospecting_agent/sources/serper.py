"""Serper.dev Google Search source for company and contact discovery.

Serper.dev provides Google Search results via API.
Free tier: 2,500 searches/month (no credit card required).
Sign up at: https://serper.dev

Set SERPER_API_KEY in your .env file.
"""
from __future__ import annotations

import re

from prospecting_agent.http_client import HttpClient
from prospecting_agent.models import Company, Contact, ICP
from prospecting_agent.sources.base import CompanySource, ContactSource

_SERPER_URL = "https://google.serper.dev/search"

# Domains that are not B2B target companies
_SKIP_DOMAINS = {
    "linkedin.com", "twitter.com", "x.com", "facebook.com", "instagram.com",
    "youtube.com", "medium.com", "reddit.com", "substack.com",
    "google.com", "microsoft.com", "amazon.com", "apple.com", "meta.com",
    "techcrunch.com", "theverge.com", "wired.com", "zdnet.com", "venturebeat.com",
    "wikipedia.org", "stackoverflow.com", "github.com", "gitlab.com",
    "glassdoor.com", "indeed.com", "crunchbase.com", "g2.com", "gartner.com",
    "producthunt.com", "ycombinator.com", "angellist.com", "wellfound.com",
    "aws.amazon.com", "cloud.google.com", "azure.microsoft.com",
    "digitalocean.com", "vercel.com", "netlify.com",
    "businesswire.com", "prnewswire.com", "globenewswire.com",
}


def _extract_domain(url: str) -> str | None:
    m = re.search(r"https?://(?:www\.)?([^/]+)", url)
    if not m:
        return None
    return m.group(1).lower().split(":")[0]


def _clean_company_name(title: str, domain: str) -> str:
    for sep in [" - ", " | ", " · ", " — ", " :: "]:
        if sep in title:
            return title.split(sep)[0].strip()
    return domain.split(".")[0].replace("-", " ").title()


class SerperCompanySource(CompanySource):
    """Finds B2B companies using Google Search via Serper.dev."""

    name = "serper"

    def __init__(self, http: HttpClient, api_key: str):
        self.http = http
        self.api_key = api_key

    def find_companies(self, icp: ICP) -> list[Company]:
        companies: list[Company] = []
        seen_domains: set[str] = set()

        queries = _build_company_queries(icp)

        for query in queries:
            if len(companies) >= icp.max_companies:
                break
            try:
                resp = self.http.session.post(
                    _SERPER_URL,
                    json={"q": query, "num": 10, "gl": "us", "hl": "en"},
                    headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                    timeout=10,
                )
                if resp.status_code != 200:
                    print(f"  [warn] Serper returned {resp.status_code} for '{query[:60]}'")
                    continue
                data = resp.json()
            except Exception as exc:
                print(f"  [warn] Serper search failed for '{query[:60]}': {exc}")
                continue

            organic = data.get("organic", [])
            for r in organic:
                if len(companies) >= icp.max_companies:
                    break
                url = r.get("link", "")
                domain = _extract_domain(url)
                if not domain or domain in seen_domains or domain in _SKIP_DOMAINS:
                    continue
                if any(domain.endswith(f".{s}") for s in _SKIP_DOMAINS):
                    continue
                seen_domains.add(domain)

                title = r.get("title", "")
                snippet = r.get("snippet", "")
                company_name = _clean_company_name(title, domain)

                companies.append(
                    Company(
                        name=company_name,
                        domain=domain,
                        description=snippet[:400] if snippet else None,
                        source=self.name,
                        source_url=url,
                        notes=[f"Serper/Google search: {query[:80]}"],
                    )
                )

        print(f"  [serper] Found {len(companies)} companies via Google Search")
        return companies


class SerperPersonSource(ContactSource):
    """Finds LinkedIn profiles via Google Search (Serper.dev)."""

    name = "serper_people"

    def __init__(self, http: HttpClient, api_key: str):
        self.http = http
        self.api_key = api_key

    def find_contacts(self, icp: ICP, companies: list[Company]) -> list[Contact]:
        contacts: list[Contact] = []
        seen: set[str] = set()

        # Build batch LinkedIn queries
        titles = " OR ".join(f'"{t}"' for t in icp.persona_titles[:4])
        for company in companies[:15]:
            if not company.name and not company.domain:
                continue

            # Search Google for LinkedIn profiles at this company
            name_q = company.name or company.domain
            query = f'site:linkedin.com/in ({titles}) "{name_q}"'

            try:
                resp = self.http.session.post(
                    _SERPER_URL,
                    json={"q": query, "num": 5, "gl": "us", "hl": "en"},
                    headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                    timeout=10,
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
            except Exception as exc:
                print(f"  [warn] Serper people search failed for '{company.name}': {exc}")
                continue

            for r in data.get("organic", []):
                contact = _parse_linkedin_result(r, company, icp)
                if contact:
                    key = contact.key()
                    if key not in seen:
                        seen.add(key)
                        contacts.append(contact)

        print(f"  [serper_people] Found {len(contacts)} LinkedIn contacts via Google Search")
        return contacts


def _parse_linkedin_result(r: dict, company: Company, icp: ICP) -> Contact | None:
    """Parse a LinkedIn search result into a Contact."""
    title_str = r.get("title", "")
    snippet = r.get("snippet", "")
    link = r.get("link", "")

    # LinkedIn title format: "First Last - Title at Company | LinkedIn"
    m = re.match(r"^([A-Za-z][\w\s'-]{2,40})\s*[-–]\s*(.+?)(?:\s*[|·]\s*LinkedIn)?$", title_str)
    if not m:
        return None

    name = m.group(1).strip()
    raw_title = m.group(2).strip()

    # Clean up "Title at Company" format
    title = re.split(r"\s+at\s+", raw_title, maxsplit=1)[0].strip()

    # Check if title matches ICP persona titles
    title_lower = title.lower()
    matched = any(pt.lower() in title_lower or title_lower in pt.lower()
                  for pt in icp.persona_titles)
    if not matched:
        return None

    return Contact(
        full_name=name,
        title=title[:100],
        company_name=company.name,
        company_domain=company.domain,
        linkedin_url=link if "linkedin.com/in/" in link else None,
        source="serper_people",
        confidence=0.75,
        signals=["Google/LinkedIn search"],
    )


def _build_company_queries(icp: ICP) -> list[str]:
    """Build targeted Google search queries to find B2B companies."""
    queries: list[str] = []

    kw = " ".join(icp.keywords[:3]) if icp.keywords else ""
    industries = icp.industries[:2]

    for industry in industries:
        if kw:
            queries.append(f'"{kw}" {industry} B2B software startup company')
        else:
            queries.append(f'{industry} software startup company "Series A" OR "Series B"')

    if kw:
        queries.append(f'{kw} startup "engineering team" site:.io OR site:.ai')

    # Tech stack based queries
    if icp.tech_stack:
        ts = " ".join(icp.tech_stack[:2])
        ind = industries[0] if industries else "SaaS"
        queries.append(f'{ind} company uses {ts} platform engineering')

    # Explicit search queries from ICP
    if icp.search_queries:
        queries.extend(icp.search_queries[:2])

    # Deduplicate
    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        ql = q.lower().strip()
        if ql not in seen and q.strip():
            seen.add(ql)
            unique.append(q)

    return unique[:6]
