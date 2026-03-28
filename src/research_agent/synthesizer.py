from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

SYSTEM_PROMPT = """\
You are a sales intelligence research analyst. You receive raw data collected \
from multiple public sources about a person and their company. Your job is to \
synthesize this into actionable outreach intelligence.

Rules:
- Be specific: reference actual data points (blog titles, news, repos, funding).
- Be genuine: talking points must feel like a real human wrote them, not a template.
- Be honest: if data is sparse, say so via a lower confidence score.
- Never fabricate facts that aren't in the provided data.
- Output valid JSON only, no markdown fences."""

USER_PROMPT_TEMPLATE = """\
## Product Context
Product: {product_name}
Pitch: {product_pitch}

## Lead
Name: {person_name}
Title: {person_title}
Company: {company_name}
Domain: {company_domain}

## Raw Company Research Data
{company_data}

## Raw Person Research Data
{person_data}

---

Synthesize this into the following JSON structure (no extra keys):

{{
  "talking_points": ["3-5 specific, genuine conversation starters referencing real data above"],
  "pain_points": ["2-4 likely challenges this person faces given their role and company context"],
  "relevance_summary": "2-3 sentences explaining specifically why the product is relevant to this person",
  "research_confidence": 0.0
}}

research_confidence scoring guide:
- 0.0-0.2: almost no data found
- 0.2-0.4: minimal data, mostly company-level
- 0.4-0.6: moderate data, some person-level signals
- 0.6-0.8: good data with specific person activity
- 0.8-1.0: rich data with recent activity, news, and clear context"""


class LLMSynthesizer:
    """Calls OpenAI to transform raw research data into structured dossier insights."""

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model: str = "openai-gpt-oss-120b",
        temperature: float = 0.4,
        max_tokens: int = 1000,
    ):
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def synthesize(
        self,
        product_name: str,
        product_pitch: str,
        person_name: str,
        person_title: str | None,
        company_name: str,
        company_domain: str | None,
        company_data: dict[str, Any],
        person_data: dict[str, Any],
    ) -> dict[str, Any]:
        company_json = _trim_raw(company_data)
        person_json = _trim_raw(person_data)

        user_message = USER_PROMPT_TEMPLATE.format(
            product_name=product_name,
            product_pitch=product_pitch,
            person_name=person_name,
            person_title=person_title or "Unknown",
            company_name=company_name,
            company_domain=company_domain or "unknown",
            company_data=json.dumps(company_json, indent=2, default=str)[:4000],
            person_data=json.dumps(person_json, indent=2, default=str)[:4000],
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            return _validate_synthesis(result)
        except Exception as exc:
            print(f"[warn] LLM synthesis failed for {person_name}: {exc}")
            return _fallback_synthesis(company_data, person_data)


def _trim_raw(data: dict[str, Any]) -> dict[str, Any]:
    """Remove bulky _raw keys before sending to the LLM to save tokens."""
    return {k: v for k, v in data.items() if k != "_raw"}


def _validate_synthesis(result: dict[str, Any]) -> dict[str, Any]:
    talking_points = result.get("talking_points", [])
    if not isinstance(talking_points, list):
        talking_points = []

    pain_points = result.get("pain_points", [])
    if not isinstance(pain_points, list):
        pain_points = []

    relevance_summary = result.get("relevance_summary", "")
    if not isinstance(relevance_summary, str):
        relevance_summary = str(relevance_summary)

    confidence = result.get("research_confidence", 0.0)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        "talking_points": talking_points[:5],
        "pain_points": pain_points[:4],
        "relevance_summary": relevance_summary,
        "research_confidence": confidence,
    }


def _fallback_synthesis(
    company_data: dict[str, Any],
    person_data: dict[str, Any],
) -> dict[str, Any]:
    """When the LLM call fails, build a minimal synthesis from raw data."""
    talking_points: list[str] = []
    pain_points: list[str] = []

    news = company_data.get("recent_news", [])
    if news and isinstance(news, list) and len(news) > 0:
        first = news[0]
        if isinstance(first, dict) and first.get("title"):
            talking_points.append(f"Recent news: {first['title']}")

    activities = person_data.get("recent_activity", [])
    if activities and isinstance(activities, list) and len(activities) > 0:
        first = activities[0]
        if isinstance(first, dict) and first.get("title"):
            talking_points.append(f"Recent activity: {first['title']}")

    data_points = sum(1 for v in list(company_data.values()) + list(person_data.values()) if v)
    confidence = min(1.0, data_points * 0.05)

    return {
        "talking_points": talking_points or ["Insufficient data for personalized talking points."],
        "pain_points": pain_points or ["Manual research recommended -- limited public data found."],
        "relevance_summary": "Automated research found limited public data. Manual review recommended.",
        "research_confidence": round(confidence, 2),
    }
