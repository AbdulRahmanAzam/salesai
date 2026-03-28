from __future__ import annotations

from prospecting_agent.http_client import HttpClient
from prospecting_agent.models import Company, ICP
from prospecting_agent.sources.base import CompanySource


class OpenCorporatesSource(CompanySource):
    name = "opencorporates"

    def __init__(self, http: HttpClient, api_token: str | None):
        self.http = http
        self.api_token = api_token

    def find_companies(self, icp: ICP) -> list[Company]:
        terms = icp.keywords or icp.industries or [icp.product_name]
        query = " ".join(terms[:3]).strip()
        if not query:
            return []

        params: dict = {
            "q": query,
            "page": 1,
            "per_page": min(100, max(25, icp.max_companies)),
            "inactive": "false",
        }
        if self.api_token:
            params["api_token"] = self.api_token

        data = self.http.get("https://api.opencorporates.com/v0.4/companies/search", params=params)
        rows = data.get("results", {}).get("companies", [])

        companies: list[Company] = []
        for row in rows:
            item = row.get("company", {})
            name = item.get("name")
            if not name:
                continue
            companies.append(
                Company(
                    name=name,
                    domain=None,
                    location=item.get("registered_address_in_full"),
                    industry=_extract_first_industry(item),
                    source=self.name,
                    source_url=item.get("opencorporates_url"),
                    notes=[
                        "Open legal entity match (good for firmographic verification)."
                    ],
                )
            )
        return companies


def _extract_first_industry(item: dict) -> str | None:
    industry_codes = item.get("industry_codes") or []
    if not industry_codes:
        return None
    first = industry_codes[0].get("industry_code", {})
    return first.get("description")
