from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

SYSTEM_PROMPT = """\
You are an elite B2B sales copywriter. You write personalised cold outreach emails \
that feel like they were written by a thoughtful human who genuinely researched the \
recipient. You never use generic templates, filler phrases, or mail-merge patterns.

Rules:
- Open with something SPECIFIC to the recipient (a recent article, launch, career move, \
  or company news). Never open with "I hope this finds you well" or "I came across your profile".
- Connect the specific detail to the product naturally -- don't force it.
- Keep messages under 150 words. Busy people skim.
- End with a soft, low-commitment ask (15 minutes, a quick take, share a demo).
- Tone: warm, direct, peer-to-peer. Not salesy, not sycophantic.
- NEVER fabricate facts. Only reference data provided in the research dossier.
- Output valid JSON only, no markdown fences."""

USER_PROMPT_TEMPLATE = """\
## Your Product
Name: {product_name}
Pitch: {product_pitch}

## Recipient
Name: {contact_name}
Title: {contact_title}
Company: {contact_company}
Email: {contact_email}
LinkedIn: {contact_linkedin}

## Research Dossier
Talking Points:
{talking_points}

Pain Points:
{pain_points}

Relevance Summary: {relevance_summary}

Company Technologies: {technologies}
Recent News: {recent_news}
Recent Activity: {recent_activity}

---

Write a personalised outreach email. Output JSON with exactly these keys:

{{
  "subject": "A compelling, specific subject line (not generic)",
  "body": "The full email body",
  "personalization_signals": ["List each specific detail from the dossier you referenced"],
  "personalization_score": 0
}}

personalization_score guide:
- 0-30: generic, could be sent to anyone
- 30-50: mentions company name / title but no specifics
- 50-70: references one specific detail (news, tech, activity)
- 70-85: weaves multiple specific details naturally
- 85-100: deeply personalised with genuine insight and creative connection"""


class DraftWriter:
    """Uses an LLM to write personalised outreach drafts from research dossiers."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://inference.do-ai.run/v1",
        model: str = "openai-gpt-oss-120b",
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def write_draft(
        self,
        product_name: str,
        product_pitch: str,
        dossier: dict[str, Any],
    ) -> dict[str, Any]:
        contact_name = dossier.get("contact_name", "Unknown")
        contact_title = dossier.get("contact_title") or "Unknown"
        contact_company = dossier.get("contact_company", "Unknown")
        contact_email = dossier.get("contact_email") or "N/A"
        contact_linkedin = dossier.get("contact_linkedin") or "N/A"

        cp = dossier.get("company_profile", {})
        pp = dossier.get("person_profile", {})

        talking_points = dossier.get("talking_points", [])
        pain_points = dossier.get("pain_points", [])
        relevance_summary = dossier.get("relevance_summary", "")

        technologies = cp.get("technologies", [])[:10]
        recent_news = _format_news(cp.get("recent_news", [])[:5])
        recent_activity = _format_activity(pp.get("recent_activity", [])[:5])

        user_message = USER_PROMPT_TEMPLATE.format(
            product_name=product_name,
            product_pitch=product_pitch,
            contact_name=contact_name,
            contact_title=contact_title,
            contact_company=contact_company,
            contact_email=contact_email,
            contact_linkedin=contact_linkedin,
            talking_points="\n".join(f"- {tp}" for tp in talking_points) or "- None available",
            pain_points="\n".join(f"- {pp}" for pp in pain_points) or "- None available",
            relevance_summary=relevance_summary or "No relevance summary available.",
            technologies=", ".join(technologies) or "Unknown",
            recent_news=recent_news or "None found",
            recent_activity=recent_activity or "None found",
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
            return _validate_draft(result)
        except Exception as exc:
            print(f"[warn] Draft generation failed for {contact_name}: {exc}")
            return _fallback_draft(
                product_name, contact_name, contact_title, contact_company
            )


def _format_news(news_items: list[dict]) -> str:
    lines = []
    for item in news_items:
        if isinstance(item, dict) and item.get("title"):
            source = item.get("source", "")
            date = item.get("published_date", "")
            lines.append(f"- {item['title']} ({source}, {date})")
    return "\n".join(lines)


def _format_activity(activities: list[dict]) -> str:
    lines = []
    for item in activities:
        if isinstance(item, dict) and item.get("title"):
            atype = item.get("activity_type", "")
            date = item.get("date", "")
            lines.append(f"- [{atype}] {item['title']} ({date})")
    return "\n".join(lines)


def _validate_draft(result: dict[str, Any]) -> dict[str, Any]:
    subject = result.get("subject", "")
    if not isinstance(subject, str) or not subject.strip():
        subject = "Quick question about your team's workflow"

    body = result.get("body", "")
    if not isinstance(body, str) or not body.strip():
        body = "I'd love to connect and share how we might help your team."

    signals = result.get("personalization_signals", [])
    if not isinstance(signals, list):
        signals = []

    score = result.get("personalization_score", 0)
    try:
        score = max(0, min(100, int(float(score))))
    except (TypeError, ValueError):
        score = 0

    return {
        "subject": subject.strip(),
        "body": body.strip(),
        "personalization_signals": [str(s) for s in signals[:10]],
        "personalization_score": score,
    }


def _fallback_draft(
    product_name: str,
    contact_name: str,
    contact_title: str | None,
    contact_company: str,
) -> dict[str, Any]:
    first_name = contact_name.split()[0] if contact_name else "there"
    return {
        "subject": f"{product_name} -- relevant for {contact_company}?",
        "body": (
            f"Hi {first_name},\n\n"
            f"I've been researching {contact_company} and believe {product_name} "
            f"could be valuable for your team.\n\n"
            f"Would you have 15 minutes this week for a quick conversation?"
        ),
        "personalization_signals": [],
        "personalization_score": 15,
    }
