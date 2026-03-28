"""DuckDuckGo-powered company and contact discovery.

Uses the duckduckgo_search Python package (free, no API key required).
Provides real web search results for company discovery.
"""
from __future__ import annotations

import re
import time
from typing import Any

from prospecting_agent.http_client import HttpClient
from prospecting_agent.models import Company, Contact, ICP
from prospecting_agent.sources.base import CompanySource, ContactSource

# Domains to skip as not being real B2B companies
_SKIP_DOMAINS = {
    # Social / content platforms
    "linkedin.com", "twitter.com", "x.com", "facebook.com", "instagram.com",
    "youtube.com", "medium.com", "reddit.com", "substack.com", "pinterest.com",
    "threads.net", "tiktok.com", "discord.com", "slack.com",
    # Tech giants
    "google.com", "microsoft.com", "amazon.com", "apple.com", "meta.com",
    "netflix.com", "airbnb.com", "uber.com", "lyft.com", "stripe.com",
    # News / aggregators
    "techcrunch.com", "theverge.com", "wired.com", "zdnet.com", "venturebeat.com",
    "arstechnica.com", "thenewstack.io", "infoworld.com", "devops.com",
    "theregister.co.uk", "businesswire.com", "prnewswire.com", "globenewswire.com",
    # Reference
    "wikipedia.org", "stackoverflow.com", "stackexchange.com",
    "github.com", "gitlab.com", "bitbucket.org",
    # Job boards
    "glassdoor.com", "indeed.com", "monster.com", "ziprecruiter.com",
    "angellist.com", "wellfound.com", "ycombinator.com",
    # Hosting / infrastructure (not companies we sell TO)
    "aws.amazon.com", "cloud.google.com", "azure.microsoft.com",
    "digitalocean.com", "heroku.com", "vercel.com", "netlify.com",
    # Analyst / directories
    "crunchbase.com", "g2.com", "capterra.com", "gartner.com",
    "producthunt.com", "alternativeto.net",
    # Docs / learning
    "docs.microsoft.com", "developer.mozilla.org", "readthedocs.io",
    "learn.microsoft.com",
}


def _extract_domain(url: str) -> str | None:
    m = re.search(r"https?://(?:www\.)?([^/]+)", url)
    if not m:
        return None
    return m.group(1).lower().split(":")[0]


def _clean_company_name(title: str, domain: str) -> str:
    """Extract a clean company name from a page title."""
    for sep in [" - ", " | ", " · ", " — ", " :: "]:
        if sep in title:
            return title.split(sep)[0].strip()
    return domain.split(".")[0].replace("-", " ").title()


class DuckDuckGoCompanySource(CompanySource):
    """Finds B2B companies using DuckDuckGo web search."""

    name = "duckduckgo"

    def __init__(self, http: HttpClient):
        self.http = http

    def find_companies(self, icp: ICP) -> list[Company]:
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                print("  [warn] ddgs package not installed. Run: pip install ddgs")
                return []

        companies: list[Company] = []
        seen_domains: set[str] = set()

        # Build targeted search queries
        queries = _build_company_queries(icp)

        for query in queries:
            if len(companies) >= icp.max_companies:
                break
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=15, region="us-en"))
                time.sleep(0.8)  # Polite delay
            except Exception as exc:
                print(f"  [warn] DDG search failed for '{query[:60]}': {exc}")
                time.sleep(2)
                continue

            for r in results:
                if len(companies) >= icp.max_companies:
                    break

                url = r.get("href", "")
                domain = _extract_domain(url)
                if not domain or domain in seen_domains or domain in _SKIP_DOMAINS:
                    continue
                # Skip subdomains of skip domains
                if any(domain.endswith(f".{s}") for s in _SKIP_DOMAINS):
                    continue
                seen_domains.add(domain)

                title = r.get("title", "")
                snippet = r.get("body", "")
                company_name = _clean_company_name(title, domain)

                companies.append(
                    Company(
                        name=company_name,
                        domain=domain,
                        description=snippet[:400] if snippet else None,
                        source=self.name,
                        source_url=url,
                        notes=[f"DDG search: {query[:80]}"],
                    )
                )

        print(f"  [ddg] Found {len(companies)} companies via DuckDuckGo")
        return companies


class DuckDuckGoPersonSource(ContactSource):
    """Finds named contacts via DuckDuckGo person/linkedin searches."""

    name = "ddg_people"

    def __init__(self, http: HttpClient):
        self.http = http

    def find_contacts(self, icp: ICP, companies: list[Company]) -> list[Contact]:
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                return []

        contacts: list[Contact] = []
        seen: set[str] = set()

        for company in companies[:12]:  # cap to avoid rate limits
            if not company.domain:
                continue

            queries = _build_person_queries(icp, company)
            for query in queries[:2]:  # 2 queries per company
                try:
                    with DDGS() as ddgs:
                        results = list(ddgs.text(query, max_results=8, region="us-en"))
                    time.sleep(0.6)
                except Exception as exc:
                    print(f"  [warn] DDG people search failed for '{company.domain}': {exc}")
                    time.sleep(2)
                    continue

                for r in results:
                    contact = _parse_contact_from_result(r, company, icp)
                    if contact:
                        key = contact.key()
                        if key not in seen:
                            seen.add(key)
                            contacts.append(contact)

        print(f"  [ddg_people] Found {len(contacts)} person snippets via DuckDuckGo")
        return contacts


def _build_company_queries(icp: ICP) -> list[str]:
    """Build targeted DDG search queries to find B2B companies."""
    queries: list[str] = []

    kw = " ".join(icp.keywords[:3]) if icp.keywords else ""
    ind = icp.industries[0] if icp.industries else "software"

    if kw:
        queries.append(f'{kw} {ind} company startup "VP Engineering" OR "CTO"')
        queries.append(f'{kw} {ind} startup B2B software company team')

    for industry in icp.industries[:2]:
        queries.append(f'{industry} software startup "{kw}" platform company')

    # Use explicit search queries if provided in ICP
    if icp.search_queries:
        queries.extend(icp.search_queries[:3])

    # Tech-stack based queries
    if icp.tech_stack:
        ts = " ".join(icp.tech_stack[:3])
        queries.append(f'{ts} startup engineering platform company')

    # Deduplicate preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        ql = q.lower().strip()
        if ql not in seen:
            seen.add(ql)
            unique.append(q)

    return unique[:6]  # max 6 queries


def _build_person_queries(icp: ICP, company: Company) -> list[str]:
    """Build DDG queries to find contacts at a specific company."""
    queries: list[str] = []
    titles = " OR ".join(f'"{t}"' for t in icp.persona_titles[:3])
    domain = company.domain or company.name

    queries.append(f'site:linkedin.com {titles} "{company.name}" engineering')
    queries.append(f'"{company.name}" ({titles}) engineering team site:linkedin.com/in')

    return queries


def _parse_contact_from_result(
    result: dict[str, Any], company: Company, icp: ICP
) -> Contact | None:
    """Try to extract a person's name and title from a DDG result snippet."""
    title_str = result.get("title", "")
    body = result.get("body", "")
    url = result.get("href", "")

    # Must look like a LinkedIn profile page
    if "linkedin.com/in/" not in url:
        return None

    # Extract name from LinkedIn URL or title
    # LinkedIn title format: "John Smith - CTO at Company | LinkedIn"
    name = None
    job_title = None

    # Pattern: "FirstName LastName - Title at Company"
    m = re.match(r"^([A-Z][a-z]+(?: [A-Z][a-z.'-]+)+)\s*[-–]\s*(.+?)\s*(?:\||at |$)", title_str)
    if m:
        name = m.group(1).strip()
        job_title = m.group(2).strip().split(" at ")[0].split(" | ")[0].strip()

    if not name or len(name.split()) < 2:
        return None

    # Check if title matches our ICP personas
    target_titles_lower = [t.lower() for t in icp.persona_titles]
    job_lower = (job_title or "").lower()
    if not any(t in job_lower for t in target_titles_lower):
        return None

    return Contact(
        full_name=name,
        title=job_title,
        company_name=company.name,
        company_domain=company.domain,
        linkedin_url=url if "linkedin.com/in/" in url else None,
        source="ddg_people",
        source_url=url,
        confidence=0.5,
        signals=["DDG LinkedIn search"],
    )
