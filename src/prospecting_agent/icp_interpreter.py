from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

SYSTEM_PROMPT = """\
You are an expert B2B sales strategist. Given a natural-language description of someone's \
product, service, or skill set, you produce a structured Ideal Customer Profile (ICP) \
that a lead-generation system can use to find potential customers.

You must INFER what is not stated:
- If someone says "I do full stack development", understand they build websites/web apps, \
  and their ideal leads are businesses NEEDING websites — startups, agencies, small businesses, \
  e-commerce stores, etc.
- If someone says "AI invoice tool for freelancers", the leads are freelancers and small \
  businesses who struggle with invoicing.
- Think about WHO WOULD BUY this product/service and WHERE to find them.

Rules:
- industries: real industry verticals where buyers live
- persona_titles: job titles of the DECISION MAKER who would buy/hire
- tech_stack: technologies the target companies likely use (helps find them via APIs)
- keywords: search terms to find these companies on the web, HN, GitHub, ProductHunt
- search_queries: 3-5 Google/web search queries to find companies needing this
- employee_ranges: company size ranges in "min,max" format (e.g. "1,10" or "51,200")
- locations: if not specified, default to ["United States"]
- Output valid JSON only, no markdown fences."""

USER_PROMPT = """\
User's input:
---
{user_input}
---

Convert this into a structured ICP. Output JSON with exactly these keys:

{{
  "product_name": "A concise name for their product/service (infer if not given)",
  "product_pitch": "A 1-2 sentence pitch describing what they offer and to whom",
  "industries": ["3-6 target industry verticals"],
  "employee_ranges": ["size ranges like '1,10' or '51,200'"],
  "locations": ["target locations, default ['United States'] if unspecified"],
  "persona_titles": ["4-8 job titles of decision makers who would buy this"],
  "tech_stack": ["5-10 technologies target companies likely use"],
  "keywords": ["8-15 search keywords to find these companies"],
  "search_queries": ["3-5 specific Google search queries to find target companies"],
  "exclude_domains": [],
  "max_companies": 75,
  "max_contacts": 200,
  "interpretation": "2-3 sentences explaining your reasoning about what leads they need"
}}"""


class ICPInterpreter:
    """Uses an LLM to convert natural language into a structured ICP."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://inference.do-ai.run/v1",
        model: str = "openai-gpt-oss-120b",
        temperature: float = 0.4,
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature

    def interpret(self, user_input: str) -> dict[str, Any]:
        user_message = USER_PROMPT.format(user_input=user_input)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=1500,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            return _validate_icp(result)
        except Exception as exc:
            print(f"[error] ICP interpretation failed: {exc}")
            return _fallback_icp(user_input)


def _validate_icp(raw: dict[str, Any]) -> dict[str, Any]:
    def _str_list(key: str, default: list[str] | None = None) -> list[str]:
        val = raw.get(key, default or [])
        if isinstance(val, list):
            return [str(v) for v in val if v]
        return default or []

    return {
        "product_name": str(raw.get("product_name", "")).strip() or "Untitled Product",
        "product_pitch": str(raw.get("product_pitch", "")).strip() or "",
        "industries": _str_list("industries"),
        "employee_ranges": _str_list("employee_ranges", ["1,50", "51,200"]),
        "locations": _str_list("locations", ["United States"]),
        "persona_titles": _str_list("persona_titles"),
        "tech_stack": _str_list("tech_stack"),
        "keywords": _str_list("keywords"),
        "search_queries": _str_list("search_queries"),
        "exclude_domains": _str_list("exclude_domains"),
        "max_companies": int(raw.get("max_companies", 75)),
        "max_contacts": int(raw.get("max_contacts", 200)),
        "interpretation": str(raw.get("interpretation", "")).strip(),
    }


def _fallback_icp(user_input: str) -> dict[str, Any]:
    words = user_input.lower().split()
    return {
        "product_name": "Custom Product",
        "product_pitch": user_input,
        "industries": ["SaaS", "Technology"],
        "employee_ranges": ["1,50", "51,200"],
        "locations": ["United States"],
        "persona_titles": ["CEO", "CTO", "Founder", "Head of Operations"],
        "tech_stack": [],
        "keywords": words[:10],
        "search_queries": [f'companies that need {user_input}'],
        "exclude_domains": [],
        "max_companies": 75,
        "max_contacts": 200,
        "interpretation": "Fallback: LLM interpretation failed. Using basic keyword extraction.",
    }
