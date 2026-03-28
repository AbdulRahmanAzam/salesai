from __future__ import annotations

from typing import Any

from prospecting_agent.http_client import HttpClient
from research_agent.sources.base import ResearchSource

GITHUB_API = "https://api.github.com"


class GitHubResearchSource(ResearchSource):
    """Uses the GitHub REST API to gather person/company open-source signals."""

    name = "github"

    def __init__(self, http: HttpClient, token: str | None):
        self.http = http
        self.token = token

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            return self.http.get(f"{GITHUB_API}{path}", params=params, headers=self._headers())
        except Exception as exc:
            print(f"[warn] github request failed for {path}: {exc}")
            return {}

    def research_company(self, company_name: str, domain: str | None) -> dict[str, Any]:
        query = company_name
        if domain:
            short_name = domain.split(".")[0]
            query = f"{company_name} OR {short_name}"

        data = self._get("/search/users", params={"q": f"{query} type:org", "per_page": 3})
        orgs = data.get("items", []) if isinstance(data, dict) else []

        technologies: list[str] = []
        social_profiles: dict[str, str] = {}
        description: str | None = None
        key_metrics: dict[str, str] = {}

        if orgs:
            org = orgs[0]
            login = org.get("login", "")
            social_profiles["github"] = org.get("html_url", f"https://github.com/{login}")

            org_detail = self._get(f"/orgs/{login}")
            if isinstance(org_detail, dict):
                description = org_detail.get("description") or org_detail.get("bio")
                key_metrics["github_public_repos"] = str(org_detail.get("public_repos", 0))
                key_metrics["github_followers"] = str(org_detail.get("followers", 0))

                if org_detail.get("blog"):
                    social_profiles["blog"] = org_detail["blog"]
                if org_detail.get("twitter_username"):
                    social_profiles["twitter"] = f"https://twitter.com/{org_detail['twitter_username']}"

            repos = self._get(f"/orgs/{login}/repos", params={"sort": "updated", "per_page": 10})
            if isinstance(repos, list):
                for repo in repos:
                    lang = repo.get("language")
                    if lang and lang not in technologies:
                        technologies.append(lang)
                    for topic in repo.get("topics", []):
                        if topic not in technologies:
                            technologies.append(topic)

        return {
            "technologies": technologies[:20],
            "social_profiles": social_profiles,
            "description": description,
            "key_metrics": key_metrics,
            "_raw": {"github_orgs": orgs},
        }

    def research_person(
        self,
        full_name: str,
        company_name: str | None,
        domain: str | None,
    ) -> dict[str, Any]:
        query = f'"{full_name}" in:name'
        if company_name:
            query = f'"{full_name}" in:name "{company_name}" in:bio'

        data = self._get("/search/users", params={"q": query, "per_page": 3})
        users = data.get("items", []) if isinstance(data, dict) else []

        if not users and full_name:
            parts = full_name.lower().split()
            simple_query = "+".join(parts) + " in:name"
            data = self._get("/search/users", params={"q": simple_query, "per_page": 3})
            users = data.get("items", []) if isinstance(data, dict) else []

        bio: str | None = None
        skills: list[str] = []
        social_profiles: dict[str, str] = {}
        activities: list[dict[str, str | None]] = []

        if users:
            user = users[0]
            login = user.get("login", "")
            social_profiles["github"] = user.get("html_url", f"https://github.com/{login}")

            profile = self._get(f"/users/{login}")
            if isinstance(profile, dict):
                bio = profile.get("bio")
                if profile.get("blog"):
                    social_profiles["blog"] = profile["blog"]
                if profile.get("twitter_username"):
                    social_profiles["twitter"] = f"https://twitter.com/{profile['twitter_username']}"
                if profile.get("company"):
                    social_profiles["company"] = profile["company"]

            repos = self._get(f"/users/{login}/repos", params={"sort": "updated", "per_page": 10})
            if isinstance(repos, list):
                for repo in repos:
                    lang = repo.get("language")
                    if lang and lang not in skills:
                        skills.append(lang)

                    activities.append({
                        "activity_type": "github_repo",
                        "title": repo.get("full_name", ""),
                        "url": repo.get("html_url", ""),
                        "date": (repo.get("pushed_at") or "")[:10] or None,
                        "snippet": repo.get("description"),
                    })

        return {
            "bio": bio,
            "skills": skills[:15],
            "social_profiles": social_profiles,
            "recent_activity": activities,
            "_raw": {"github_users": users},
        }
