from __future__ import annotations

from typing import Any

from prospecting_agent.http_client import HttpClient
from prospecting_agent.models import Company, ICP
from prospecting_agent.sources.base import CompanySource

PH_GRAPHQL_URL = "https://api.producthunt.com/v2/api/graphql"

POSTS_QUERY = """\
query SearchPosts($query: String!) {
  posts(order: RANKING, first: 20, query: $query) {
    edges {
      node {
        name
        tagline
        website
        url
        votesCount
        topics {
          edges {
            node {
              name
            }
          }
        }
        makers {
          name
          headline
        }
      }
    }
  }
}"""


class ProductHuntSource(CompanySource):
    """Discovers companies from Product Hunt matching ICP keywords."""

    name = "producthunt"

    def __init__(self, http: HttpClient, token: str | None):
        self.http = http
        self.token = token

    def _enabled(self) -> bool:
        return bool(self.token)

    def find_companies(self, icp: ICP) -> list[Company]:
        if not self._enabled():
            return []

        query_terms = icp.keywords[:3] + icp.industries[:2]
        if not query_terms:
            query_terms = [icp.product_name]

        query = " ".join(query_terms)
        posts = self._search_posts(query)

        companies: list[Company] = []
        seen_domains: set[str] = set()

        for post in posts:
            domain = _extract_domain(post.get("website"))
            if not domain or domain in seen_domains:
                continue
            seen_domains.add(domain)

            topics = [
                e["node"]["name"]
                for e in (post.get("topics", {}).get("edges", []))
                if e.get("node", {}).get("name")
            ]

            notes = [f"Product Hunt: {post.get('tagline', '')}"]
            if post.get("votesCount"):
                notes.append(f"PH votes: {post['votesCount']}")

            companies.append(
                Company(
                    name=post.get("name", "Unknown"),
                    domain=domain,
                    source=self.name,
                    source_url=post.get("url"),
                    notes=notes,
                    technologies=topics,
                )
            )
            if len(companies) >= icp.max_companies:
                break

        return companies

    def _search_posts(self, query: str) -> list[dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        body = {
            "query": POSTS_QUERY,
            "variables": {"query": query},
        }
        try:
            data = self.http.post(PH_GRAPHQL_URL, json_body=body, headers=headers)
            edges = data.get("data", {}).get("posts", {}).get("edges", [])
            return [e["node"] for e in edges if e.get("node")]
        except Exception as exc:
            print(f"[warn] producthunt search failed: {exc}")
            return []


def _extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    value = url.strip().lower()
    value = value.replace("https://", "").replace("http://", "")
    if value.startswith("www."):
        value = value[4:]
    return value.split("/")[0] or None
