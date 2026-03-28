from __future__ import annotations

import re

from prospecting_agent.http_client import HttpClient
from prospecting_agent.models import Company, ICP
from prospecting_agent.sources.base import CompanySource

_DOMAIN_RE = re.compile(r"https?://([^/]+)")
_SKIP_DOMAINS = {"github.com", "github.io", "githubusercontent.com"}


class GitHubOrgSource(CompanySource):
    name = "github"

    def __init__(self, http: HttpClient, token: str | None):
        self.http = http
        self.token = token

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/vnd.github+json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
            h["X-GitHub-Api-Version"] = "2022-11-28"
        return h

    def find_companies(self, icp: ICP) -> list[Company]:
        query_terms = icp.keywords or icp.tech_stack or icp.industries
        if not query_terms:
            return []

        query = "+".join(query_terms[:3]) + "+type:org"

        try:
            data = self.http.get(
                "https://api.github.com/search/users",
                params={"q": query, "per_page": min(30, max(10, icp.max_companies))},
                headers=self._headers(),
            )
        except Exception as exc:
            print(f"  [warn] GitHub org search failed: {exc}")
            return []

        companies: list[Company] = []
        seen_domains: set[str] = set()

        for item in data.get("items", []):
            login = item.get("login")
            if not login:
                continue

            # Fetch full org profile to get blog/website URL
            domain = self._fetch_org_domain(login)
            if domain and domain in seen_domains:
                continue
            if domain:
                seen_domains.add(domain)

            companies.append(
                Company(
                    name=login,
                    domain=domain,
                    source=self.name,
                    source_url=item.get("html_url"),
                    notes=["GitHub organization matched ICP keyword query."],
                )
            )
            if len(companies) >= icp.max_companies:
                break

        return companies

    def _fetch_org_domain(self, login: str) -> str | None:
        """Fetch the org profile and extract the blog/website domain."""
        try:
            data = self.http.get(
                f"https://api.github.com/orgs/{login}",
                headers=self._headers(),
            )
        except Exception:
            return None

        # Try blog first (usually the company website), then html_url
        for field in ("blog", "html_url"):
            url = data.get(field, "")
            if not url:
                continue
            match = _DOMAIN_RE.search(url)
            if not match:
                # blog might be bare domain like "example.com"
                if "." in url and "/" not in url:
                    return url.lower().strip()
                continue
            domain = match.group(1).lower()
            if domain.startswith("www."):
                domain = domain[4:]
            # Skip GitHub-hosted domains
            if any(domain.endswith(s) for s in _SKIP_DOMAINS):
                continue
            return domain

        return None
