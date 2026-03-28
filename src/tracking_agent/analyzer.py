from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from tracking_agent.models import FollowUp, Response

# ─── Response Analysis ───

ANALYSIS_SYSTEM_PROMPT = """\
You are a B2B sales response analyst. You receive a reply to a cold outreach email \
and must classify it and extract key insights for the sales team.

Rules:
- Be precise: classify based on actual content, not assumptions.
- Extract exact quotes when identifying key points.
- A "warm" lead is someone who shows genuine interest, asks questions, or suggests a meeting.
- A "hot" lead explicitly requests a meeting or demo.
- An "objection" is a reason they can't or don't want to proceed.
- "neutral" means polite acknowledgment without clear interest or rejection.
- Output valid JSON only, no markdown fences."""

ANALYSIS_USER_TEMPLATE = """\
## Original Outreach
To: {contact_name} ({contact_title} at {contact_company})
Subject: {original_subject}
Body:
{original_body}

## Their Reply
From: {contact_email}
Subject: {reply_subject}
Body:
{reply_body}

---

Analyze this reply. Output JSON with exactly these keys:

{{
  "warmth": "cold|neutral|warm|hot|meeting_requested",
  "sentiment": "positive|negative|neutral|interested|objection",
  "key_points": ["List 1-4 key takeaways from their reply"],
  "needs_follow_up": true or false,
  "follow_up_timing": "immediate|3_days|1_week|never",
  "follow_up_strategy": "Brief strategy note for follow-up if needed"
}}"""

# ─── Follow-up Generation ───

FOLLOW_UP_SYSTEM_PROMPT = """\
You are an elite B2B sales professional writing a follow-up reply. You are responding \
to someone who replied to your initial outreach. The follow-up must:

- Reference their specific reply and acknowledge what they said.
- Be concise (under 100 words).
- Feel conversational and genuine -- not scripted.
- Match the tone of the conversation so far.
- Advance the conversation toward a meeting or demo.
- If they raised an objection, address it thoughtfully without being pushy.
- If they requested a meeting, confirm and suggest specific times.
- NEVER fabricate facts.
- Output valid JSON only, no markdown fences."""

FOLLOW_UP_USER_TEMPLATE = """\
## Context
Product: {product_name}
Product Pitch: {product_pitch}

## Original Outreach
To: {contact_name} ({contact_title} at {contact_company})
Subject: {original_subject}
Body:
{original_body}

## Their Reply
{reply_body}

## Response Analysis
Warmth: {warmth}
Sentiment: {sentiment}
Key Points: {key_points}
Follow-up Strategy: {follow_up_strategy}

## Previous Follow-ups Sent: {follow_up_count}

---

Write a follow-up reply. Output JSON with exactly these keys:

{{
  "subject": "Re: <appropriate subject>",
  "body": "The follow-up reply text",
  "tone": "Description of the tone used",
  "next_step": "What we're trying to achieve with this follow-up"
}}"""


class ResponseAnalyzer:
    """LLM-powered response analysis and follow-up generation."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://inference.do-ai.run/v1",
        model: str = "openai-gpt-oss-120b",
        temperature: float = 0.5,
        max_tokens: int = 1200,
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def analyze_response(
        self,
        response: Response,
        original_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Classify a response's warmth, sentiment, and extract key points.

        Returns dict with: warmth, sentiment, key_points, needs_follow_up,
                          follow_up_timing, follow_up_strategy
        """
        user_message = ANALYSIS_USER_TEMPLATE.format(
            contact_name=response.contact_name,
            contact_title=original_context.get("contact_title", "Unknown"),
            contact_company=response.contact_company,
            contact_email=response.contact_email,
            original_subject=original_context.get("subject", ""),
            original_body=original_context.get("body", "")[:1000],
            reply_subject=response.subject,
            reply_body=response.body[:2000],
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
            result = json.loads(content)
            return _validate_analysis(result)
        except Exception as exc:
            print(f"[warn] Analysis failed for {response.contact_name}: {exc}")
            return _fallback_analysis(response)

    def generate_follow_up(
        self,
        response: Response,
        original_context: dict[str, Any],
        analysis: dict[str, Any],
        product_name: str = "",
        product_pitch: str = "",
        follow_up_count: int = 0,
    ) -> FollowUp:
        """Generate a contextual follow-up reply using LLM."""
        user_message = FOLLOW_UP_USER_TEMPLATE.format(
            product_name=product_name or "Our Product",
            product_pitch=product_pitch or "Our solution",
            contact_name=response.contact_name,
            contact_title=original_context.get("contact_title", "Unknown"),
            contact_company=response.contact_company,
            original_subject=original_context.get("subject", ""),
            original_body=original_context.get("body", "")[:1000],
            reply_body=response.body[:2000],
            warmth=analysis.get("warmth", "unknown"),
            sentiment=analysis.get("sentiment", "unknown"),
            key_points=", ".join(analysis.get("key_points", [])),
            follow_up_strategy=analysis.get("follow_up_strategy", "Standard follow-up"),
            follow_up_count=follow_up_count,
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                temperature=min(0.7, self.temperature + 0.1),
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": FOLLOW_UP_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
            result = json.loads(content)
            result = _validate_follow_up(result, response, original_context)
        except Exception as exc:
            print(f"[warn] Follow-up generation failed for {response.contact_name}: {exc}")
            result = _fallback_follow_up(response, original_context, analysis)

        return FollowUp(
            response_id=response.id,
            outreach_message_id=response.outreach_message_id,
            contact_name=response.contact_name,
            contact_company=response.contact_company,
            contact_email=response.contact_email,
            subject=result["subject"],
            body=result["body"],
            follow_up_number=follow_up_count + 1,
            status="draft",
        )


# ─── Validation & Fallbacks ───


def _validate_analysis(result: dict[str, Any]) -> dict[str, Any]:
    valid_warmth = {"cold", "neutral", "warm", "hot", "meeting_requested"}
    valid_sentiment = {"positive", "negative", "neutral", "interested", "objection"}

    warmth = result.get("warmth", "unknown")
    if warmth not in valid_warmth:
        warmth = "neutral"

    sentiment = result.get("sentiment", "unknown")
    if sentiment not in valid_sentiment:
        sentiment = "neutral"

    key_points = result.get("key_points", [])
    if not isinstance(key_points, list):
        key_points = []

    needs_follow_up = result.get("needs_follow_up", True)
    if not isinstance(needs_follow_up, bool):
        needs_follow_up = True

    return {
        "warmth": warmth,
        "sentiment": sentiment,
        "key_points": [str(p) for p in key_points[:4]],
        "needs_follow_up": needs_follow_up,
        "follow_up_timing": result.get("follow_up_timing", "3_days"),
        "follow_up_strategy": str(result.get("follow_up_strategy", "")),
    }


def _fallback_analysis(response: Response) -> dict[str, Any]:
    """Simple keyword-based fallback when LLM is unavailable."""
    body_lower = response.body.lower()

    # Simple keyword classification
    hot_keywords = ["meeting", "demo", "schedule", "call", "let's talk", "interested", "set up"]
    warm_keywords = ["sounds good", "tell me more", "curious", "intrigued", "could you"]
    cold_keywords = ["not interested", "unsubscribe", "remove me", "stop", "no thanks"]
    objection_keywords = ["budget", "not a priority", "already use", "not the right time"]

    warmth = "neutral"
    sentiment = "neutral"
    needs_follow_up = True

    if any(kw in body_lower for kw in hot_keywords):
        warmth = "hot"
        sentiment = "interested"
    elif any(kw in body_lower for kw in warm_keywords):
        warmth = "warm"
        sentiment = "positive"
    elif any(kw in body_lower for kw in cold_keywords):
        warmth = "cold"
        sentiment = "negative"
        needs_follow_up = False
    elif any(kw in body_lower for kw in objection_keywords):
        warmth = "neutral"
        sentiment = "objection"

    return {
        "warmth": warmth,
        "sentiment": sentiment,
        "key_points": ["Keyword-based analysis (LLM unavailable)"],
        "needs_follow_up": needs_follow_up,
        "follow_up_timing": "3_days" if needs_follow_up else "never",
        "follow_up_strategy": "Manual review recommended -- analysis was keyword-based.",
    }


def _validate_follow_up(
    result: dict[str, Any],
    response: Response,
    original_context: dict[str, Any],
) -> dict[str, Any]:
    subject = result.get("subject", "")
    if not isinstance(subject, str) or not subject.strip():
        orig_subj = original_context.get("subject", "Follow up")
        subject = f"Re: {orig_subj}"

    body = result.get("body", "")
    if not isinstance(body, str) or not body.strip():
        body = _fallback_follow_up(response, original_context, {})["body"]

    return {"subject": subject.strip(), "body": body.strip()}


def _fallback_follow_up(
    response: Response,
    original_context: dict[str, Any],
    analysis: dict[str, Any],
) -> dict[str, Any]:
    first_name = response.contact_name.split()[0] if response.contact_name else "there"
    orig_subj = original_context.get("subject", "our previous conversation")

    return {
        "subject": f"Re: {orig_subj}",
        "body": (
            f"Hi {first_name},\n\n"
            f"Thanks for getting back to me. I appreciate you taking the time to respond.\n\n"
            f"I'd love to continue this conversation and explore how we might be able to help "
            f"{response.contact_company}. Would you have 15 minutes this week for a quick chat?\n\n"
            f"Happy to work around your schedule."
        ),
    }
