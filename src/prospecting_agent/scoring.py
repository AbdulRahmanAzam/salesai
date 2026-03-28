from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from prospecting_agent.models import Company, Contact, ICP

LLM_SCORING_PROMPT = """\
You are a B2B sales intelligence analyst. Score how relevant this lead is for the product.

Product: {product_name}
Pitch: {product_pitch}

Lead:
- Name: {contact_name}
- Title: {contact_title}
- Company: {company_name} ({company_domain})
- Company Description: {company_desc}
- Industry: {industry}
- Technologies: {technologies}
- Signals: {signals}

Rate this lead. Output JSON:
{{
  "relevance_score": 0,
  "reasons": ["why this lead is or isn't relevant"],
  "explanation": "1-2 sentence summary"
}}

relevance_score: 0-100 where:
- 0-20: completely irrelevant
- 20-40: tangentially related
- 40-60: moderately relevant
- 60-80: strong fit
- 80-100: ideal customer"""


class LLMScorer:
    """Optional LLM-based relevance scoring for high-value leads."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://inference.do-ai.run/v1",
        model: str = "openai-gpt-oss-120b",
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def score(
        self,
        contact: Contact,
        company: Company | None,
        icp: ICP,
    ) -> tuple[float, list[str], str]:
        prompt = LLM_SCORING_PROMPT.format(
            product_name=icp.product_name,
            product_pitch=icp.product_pitch,
            contact_name=contact.full_name,
            contact_title=contact.title or "Unknown",
            company_name=contact.company_name,
            company_domain=contact.company_domain or "unknown",
            company_desc=(company.description or "No description")[:200] if company else "No data",
            industry=(company.industry or "Unknown") if company else "Unknown",
            technologies=", ".join((company.technologies or [])[:8]) if company else "Unknown",
            signals=", ".join(contact.signals[:5]) or "None",
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            score = max(0, min(100, int(float(result.get("relevance_score", 0)))))
            reasons = result.get("reasons", [])
            if not isinstance(reasons, list):
                reasons = [str(reasons)]
            explanation = str(result.get("explanation", ""))
            return score, reasons, explanation
        except Exception as exc:
            print(f"[warn] LLM scoring failed for {contact.full_name}: {exc}")
            score, reasons = _rule_based_score(contact, company, icp)
            return score, reasons, ""


def score_contact(
    contact: Contact,
    icp: ICP,
    company: Company | None = None,
) -> tuple[float, list[str]]:
    """Rule-based scoring. Used when LLM is unavailable or for initial filtering."""
    return _rule_based_score(contact, company, icp)


def _rule_based_score(
    contact: Contact,
    company: Company | None,
    icp: ICP,
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    title = (contact.title or "").lower()
    company_blob = f"{contact.company_name} {contact.company_domain or ''}".lower()
    if company and company.description:
        company_blob += f" {company.description}".lower()

    if any(t.lower() in title for t in icp.persona_titles):
        score += 30
        reasons.append("Persona title alignment")

    matched_keywords = [k for k in icp.keywords if k.lower() in company_blob]
    if matched_keywords:
        score += min(20, len(matched_keywords) * 5)
        reasons.append(f"ICP keyword match ({', '.join(matched_keywords[:3])})")

    if contact.email:
        score += 15
        reasons.append("Email available")

    if contact.linkedin_url and "guessed" not in " ".join(contact.signals).lower():
        score += 10
        reasons.append("LinkedIn profile available")
    elif contact.linkedin_url:
        score += 3
        reasons.append("LinkedIn URL guessed (unverified)")

    sources = (contact.source or "").lower().split("+")
    unique_sources = {s.strip() for s in sources if s.strip()}
    if len(unique_sources) >= 3:
        score += 18
        reasons.append(f"Verified across {len(unique_sources)} sources")
    elif len(unique_sources) == 2:
        score += 12
        reasons.append(f"Verified across 2 sources")
    elif unique_sources:
        source_name = next(iter(unique_sources))
        if "apollo" in source_name:
            score += 10
            reasons.append("Apollo-verified contact")
        elif "hunter" in source_name:
            score += 8
            reasons.append("Hunter-verified domain contact")
        elif source_name != "unknown":
            score += 4
            reasons.append(f"Source: {source_name}")

    if company and icp.tech_stack:
        tech_matches = [
            t for t in icp.tech_stack
            if t.lower() in " ".join(company.technologies).lower()
        ]
        if tech_matches:
            score += min(15, len(tech_matches) * 5)
            reasons.append(f"Tech overlap ({', '.join(tech_matches[:3])})")

    if contact.signals:
        signal_blob = " ".join(s.lower() for s in contact.signals)
        activity_keywords = ["recent", "active", "launch", "funded", "verified"]
        if any(k in signal_blob for k in activity_keywords):
            score += 8
            reasons.append("Recent activity / verification signal")

    if contact.confidence >= 0.9:
        score += 5
        reasons.append("High source confidence")
    elif contact.confidence >= 0.7:
        score += 3
        reasons.append("Good source confidence")

    if company and company.employee_range and icp.employee_ranges:
        if company.employee_range in icp.employee_ranges:
            score += 5
            reasons.append("Company size matches ICP range")

    if not reasons:
        reasons.append("Weak match; needs manual review")

    return min(100.0, score), reasons
