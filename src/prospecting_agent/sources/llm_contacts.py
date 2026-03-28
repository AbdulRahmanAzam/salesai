"""LLM-powered contact discovery source.

When paid API quotas (Hunter, Apollo) are exhausted, this source uses:
1. Web scraping of company pages (team/about) to find real names + titles
2. LLM to infer likely contacts based on company profile + ICP
3. Standard email pattern generation (first@domain, first.last@domain, etc.)
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from openai import OpenAI

from prospecting_agent.http_client import HttpClient
from prospecting_agent.models import Company, Contact, ICP
from prospecting_agent.sources.base import ContactSource

# Common email patterns ranked by likelihood
_EMAIL_PATTERNS = [
    "{first}@{domain}",
    "{first}.{last}@{domain}",
    "{first}{last_initial}@{domain}",
    "{first_initial}{last}@{domain}",
    "{first}_{last}@{domain}",
]


class LLMContactSource(ContactSource):
    """Discovers contacts using LLM analysis + web scraping when paid APIs are unavailable."""

    name = "llm_discovery"

    def __init__(
        self,
        http: HttpClient,
        api_key: str,
        base_url: str = "https://inference.do-ai.run/v1",
        model: str = "openai-gpt-oss-120b",
        max_domains: int = 15,
    ):
        self.http = http
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.max_domains = max_domains

    def find_contacts(self, icp: ICP, companies: list[Company]) -> list[Contact]:
        if not companies:
            return []

        contacts: list[Contact] = []
        domains_searched = 0

        for company in companies:
            if domains_searched >= self.max_domains:
                break
            if not company.domain:
                continue

            domains_searched += 1

            # Step 1: Try to scrape team/about page for real contacts
            scraped = self._scrape_team_page(company)

            # Step 2: Use LLM to generate contacts from company info + ICP
            llm_contacts = self._llm_discover(company, icp, scraped)

            for c in llm_contacts:
                contacts.append(c)
                if len(contacts) >= icp.max_contacts:
                    return contacts

            # Small delay to avoid hammering
            time.sleep(0.5)

        return contacts

    def _scrape_team_page(self, company: Company) -> list[dict[str, str]]:
        """Try to scrape the company website for team/about page data."""
        found: list[dict[str, str]] = []
        domain = company.domain
        if not domain:
            return found

        # Try common team page paths
        paths = [
            f"https://{domain}/about",
            f"https://{domain}/team",
            f"https://{domain}/about-us",
            f"https://{domain}/company",
            f"https://www.{domain}/about",
            f"https://www.{domain}/team",
        ]

        for url in paths[:3]:  # Only try first 3 to save time
            try:
                import requests
                resp = requests.get(
                    url,
                    timeout=8,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "text/html,application/xhtml+xml",
                    },
                    allow_redirects=True,
                )
                if resp.status_code != 200:
                    continue

                text = resp.text[:15000]  # Cap at 15k chars
                # Extract names + titles from page using simple patterns
                found.extend(_extract_people_from_html(text))
                if found:
                    break  # Found people, stop trying other paths
            except Exception:
                continue

        return found[:10]  # Cap at 10 people

    def _llm_discover(
        self,
        company: Company,
        icp: ICP,
        scraped_people: list[dict[str, str]],
    ) -> list[Contact]:
        """Ask the LLM to identify the most likely contacts at this company."""

        # Build context about the company
        company_info = f"Company: {company.name}\nDomain: {company.domain}"
        if company.industry:
            company_info += f"\nIndustry: {company.industry}"
        if company.location:
            company_info += f"\nLocation: {company.location}"
        if company.description:
            company_info += f"\nDescription: {company.description}"
        for note in company.notes[:3]:
            company_info += f"\nNote: {note}"

        scraped_section = ""
        if scraped_people:
            scraped_section = "\n\nPeople found on company website:\n"
            for p in scraped_people:
                scraped_section += f"- {p.get('name', 'Unknown')}"
                if p.get("title"):
                    scraped_section += f" ({p['title']})"
                scraped_section += "\n"

        target_titles = ", ".join(icp.persona_titles[:5])

        prompt = f"""You are a B2B sales research assistant. Based on the company information below, identify the most likely real contacts who match the target personas.

{company_info}{scraped_section}

Target personas: {target_titles}
Product being sold: {icp.product_name} - {icp.product_pitch}

Return a JSON array of 1-3 contacts. Each contact should have:
- "name": Full name (realistic for the company's likely location/culture)
- "title": Job title (must match one of the target personas)
- "confidence": How confident you are this person exists (0.0-1.0)
- "reasoning": Brief note on why this contact is likely

IMPORTANT RULES:
- If you found real people from the website scrape, use those exact names and titles.
- If no scraped data, infer likely contacts based on the company size and industry.
- For small companies (< 50 employees), the CTO is often a cofounder.
- Use culturally appropriate names for the company's location.
- Be honest about confidence. Scraped = 0.7-0.9, inferred = 0.3-0.5.
- Return ONLY the JSON array. No markdown, no explanation."""

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1200,
            )
            raw = (resp.choices[0].message.content or "").strip()
            # Strip markdown fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            people = _parse_json_lenient(raw)
            if not isinstance(people, list):
                return []
        except Exception as exc:
            print(f"  [warn] LLM contact discovery failed for {company.domain}: {exc}")
            return []

        contacts: list[Contact] = []
        for person in people:
            name = person.get("name", "").strip()
            title = person.get("title", "").strip()
            conf = float(person.get("confidence", 0.3))
            reasoning = person.get("reasoning", "")

            if not name or not title:
                continue

            # Generate email guesses
            emails = _generate_emails(name, company.domain)
            primary_email = emails[0] if emails else None

            signals = ["LLM-inferred contact"]
            if scraped_people and any(
                name.lower() in p.get("name", "").lower() for p in scraped_people
            ):
                signals = ["Found on company website", "LLM-matched to ICP persona"]
                conf = max(conf, 0.7)

            contacts.append(
                Contact(
                    full_name=name,
                    title=title,
                    company_name=company.name,
                    company_domain=company.domain,
                    email=primary_email,
                    linkedin_url=_guess_linkedin(name),
                    source=self.name,
                    source_url=f"https://{company.domain}",
                    confidence=conf,
                    signals=signals,
                    research_notes=[
                        reasoning,
                        f"Email pattern: {primary_email} (common pattern, verify before sending)",
                        *(
                            [f"Alternative emails: {', '.join(emails[1:3])}"]
                            if len(emails) > 1
                            else []
                        ),
                    ],
                )
            )

        return contacts


def _extract_people_from_html(html: str) -> list[dict[str, str]]:
    """Extract names and titles from HTML using common patterns."""
    people: list[dict[str, str]] = []
    seen: set[str] = set()

    # Pattern 1: Look for structured team members (common in team pages)
    # e.g., <h3>John Smith</h3><p>CTO</p> or similar structures
    patterns = [
        # Name in heading followed by title
        r'<h[2-4][^>]*>([A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)?)</h[2-4]>\s*(?:<[^>]+>)*\s*([A-Z][^<]{3,50})',
        # Name with title in same element
        r'"name"\s*:\s*"([^"]+)".*?"(?:title|role|position)"\s*:\s*"([^"]+)"',
        # Data attributes
        r'data-name="([^"]+)"[^>]*data-(?:title|role)="([^"]+)"',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, html, re.IGNORECASE | re.DOTALL):
            name = match.group(1).strip()
            title = match.group(2).strip()
            # Basic validation
            if (
                2 <= len(name.split()) <= 4
                and len(name) < 50
                and name.lower() not in seen
                and not any(w in name.lower() for w in ["lorem", "ipsum", "test", "example"])
            ):
                seen.add(name.lower())
                people.append({"name": name, "title": _clean_title(title)})

    return people


def _clean_title(title: str) -> str:
    """Clean up a scraped title string."""
    title = re.sub(r"<[^>]+>", "", title).strip()
    title = re.sub(r"\s+", " ", title)
    return title[:80] if title else ""


def _generate_emails(full_name: str, domain: str | None) -> list[str]:
    """Generate likely email addresses from a name and domain."""
    if not domain or not full_name:
        return []

    parts = re.sub(r"[^a-z\s]", "", full_name.lower()).split()
    if len(parts) < 2:
        return []

    first = parts[0]
    last = parts[-1]
    first_initial = first[0] if first else ""
    last_initial = last[0] if last else ""

    emails = []
    for pattern in _EMAIL_PATTERNS:
        email = (
            pattern.replace("{first}", first)
            .replace("{last}", last)
            .replace("{first_initial}", first_initial)
            .replace("{last_initial}", last_initial)
            .replace("{domain}", domain)
        )
        emails.append(email)

    return emails


def _guess_linkedin(name: str) -> str | None:
    """Generate a likely LinkedIn URL from a name."""
    clean = re.sub(r"[^a-z\s]", "", name.lower()).split()
    if len(clean) >= 2:
        slug = "-".join(clean)
        return f"https://linkedin.com/in/{slug}"
    return None


def _parse_json_lenient(raw: str) -> Any:
    """Try to parse JSON, with fallback repairs for common LLM output issues."""
    # First try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Fix 1: Trailing commas before } or ]
    fixed = re.sub(r",\s*([}\]])", r"\1", raw)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Fix 2: Truncated JSON — try to close open structures
    # Find the last complete object in an array
    bracket_pos = fixed.rfind("}")
    if bracket_pos > 0:
        # Try closing the array after the last complete object
        candidate = fixed[:bracket_pos + 1]
        # Count open brackets to close them
        open_brackets = candidate.count("[") - candidate.count("]")
        candidate += "]" * max(0, open_brackets)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Fix 3: Extract individual JSON objects with regex
    objects = []
    for m in re.finditer(r"\{[^{}]*\}", raw, re.DOTALL):
        try:
            obj = json.loads(m.group())
            if "name" in obj:
                objects.append(obj)
        except json.JSONDecodeError:
            continue
    if objects:
        return objects

    raise json.JSONDecodeError("Could not parse LLM output", raw, 0)
