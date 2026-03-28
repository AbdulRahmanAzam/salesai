from __future__ import annotations

import re
from typing import Any

from prospecting_agent.http_client import HttpClient
from prospecting_agent.models import Contact


class ContactEnricher:
    """Enriches contacts with email, LinkedIn, and additional signals.

    Uses Hunter email-finder, Hunter email-verifier, and Google CSE
    to discover missing contact details.
    """

    def __init__(
        self,
        http: HttpClient,
        hunter_api_key: str | None = None,
        google_cse_api_key: str | None = None,
        google_cse_cx: str | None = None,
    ):
        self.http = http
        self.hunter_key = hunter_api_key
        self.cse_key = google_cse_api_key
        self.cse_cx = google_cse_cx
        self._hunter_quota_exhausted = False

    def enrich(self, contact: Contact) -> Contact:
        if not contact.email and self.hunter_key and not self._hunter_quota_exhausted:
            contact = self._find_email_hunter(contact)

        if not contact.linkedin_url:
            contact = self._find_linkedin(contact)

        if contact.email and self.hunter_key and not self._hunter_quota_exhausted:
            contact = self._verify_email(contact)

        return contact

    def _find_email_hunter(self, contact: Contact) -> Contact:
        if not contact.company_domain:
            return contact

        params: dict[str, Any] = {
            "api_key": self.hunter_key,
            "domain": contact.company_domain,
            "full_name": contact.full_name,
        }
        try:
            data = self.http.get(
                "https://api.hunter.io/v2/email-finder", params=params
            )
            result = data.get("data", {})
            email = result.get("email")
            if email:
                contact.email = email
                score = result.get("score", 0)
                contact.confidence = max(contact.confidence, score / 100.0)
                contact.signals.append("Email found via Hunter email-finder")
                sources = result.get("sources", [])
                if sources:
                    contact.signals.append(
                        f"Email seen on {len(sources)} public source(s)"
                    )
        except Exception as exc:
            if "429" in str(exc) or "Too Many Requests" in str(exc):
                self._hunter_quota_exhausted = True
                print(f"[warn] Hunter quota exhausted — skipping remaining email lookups")
            else:
                print(f"[warn] Hunter email-finder failed for {contact.full_name}: {exc}")

        return contact

    def _verify_email(self, contact: Contact) -> Contact:
        if not contact.email:
            return contact

        params: dict[str, Any] = {
            "api_key": self.hunter_key,
            "email": contact.email,
        }
        try:
            data = self.http.get(
                "https://api.hunter.io/v2/email-verifier", params=params
            )
            result = data.get("data", {})
            status = result.get("status", "")
            score = result.get("score", 0)

            if status == "valid":
                contact.confidence = max(contact.confidence, score / 100.0)
                contact.signals.append("Email verified (valid)")
            elif status == "accept_all":
                contact.confidence = max(contact.confidence, 0.6)
                contact.signals.append("Email domain accepts all (verify manually)")
            elif status in ("invalid", "disposable"):
                contact.signals.append(f"Email flagged as {status}")
                contact.confidence = min(contact.confidence, 0.2)
        except Exception as exc:
            if "429" in str(exc) or "Too Many Requests" in str(exc):
                self._hunter_quota_exhausted = True
                print(f"[warn] Hunter verification quota exhausted — skipping remaining")
            else:
                print(f"[warn] Hunter email-verifier failed for {contact.email}: {exc}")

        return contact

    def _find_linkedin(self, contact: Contact) -> Contact:
        if not self.cse_key or not self.cse_cx:
            contact = self._guess_linkedin_url(contact)
            return contact

        query = f'site:linkedin.com/in/ "{contact.full_name}"'
        if contact.company_name:
            query += f' "{contact.company_name}"'

        params: dict[str, Any] = {
            "key": self.cse_key,
            "cx": self.cse_cx,
            "q": query,
            "num": 3,
        }
        try:
            data = self.http.get(
                "https://www.googleapis.com/customsearch/v1", params=params
            )
            items = data.get("items", [])
            for item in items:
                link = item.get("link", "")
                if "linkedin.com/in/" in link.lower():
                    contact.linkedin_url = link
                    contact.signals.append("LinkedIn found via Google search")
                    break
        except Exception as exc:
            print(f"[warn] LinkedIn search failed for {contact.full_name}: {exc}")
            contact = self._guess_linkedin_url(contact)

        return contact

    def _guess_linkedin_url(self, contact: Contact) -> Contact:
        if contact.linkedin_url:
            return contact

        name = contact.full_name.lower().strip()
        parts = re.sub(r"[^a-z\s]", "", name).split()
        if len(parts) >= 2:
            slug = "-".join(parts)
            contact.linkedin_url = f"https://linkedin.com/in/{slug}"
            contact.signals.append("LinkedIn URL guessed from name (unverified)")

        return contact
