from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class OutreachSettings:
    """Configuration for the outreach agent."""

    # SMTP for sending emails
    smtp_host: str
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None
    smtp_use_tls: bool
    sender_email: str
    sender_name: str

    # LLM for refining drafts and generating follow-ups
    llm_api_key: str | None
    llm_base_url: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int

    # Runtime
    max_concurrent_sends: int
    send_delay_seconds: float
    daily_send_limit: int


def get_outreach_settings() -> OutreachSettings:
    load_dotenv()
    return OutreachSettings(
        smtp_host=os.getenv("OUTREACH_SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("OUTREACH_SMTP_PORT", "587")),
        smtp_username=os.getenv("OUTREACH_SMTP_USERNAME"),
        smtp_password=os.getenv("OUTREACH_SMTP_PASSWORD"),
        smtp_use_tls=os.getenv("OUTREACH_SMTP_USE_TLS", "true").lower() == "true",
        sender_email=os.getenv("OUTREACH_SENDER_EMAIL", ""),
        sender_name=os.getenv("OUTREACH_SENDER_NAME", ""),
        llm_api_key=os.getenv("OUTREACH_LLM_API_KEY"),
        llm_base_url=os.getenv(
            "OUTREACH_LLM_BASE_URL", "https://inference.do-ai.run/v1"
        ),
        llm_model=os.getenv("OUTREACH_LLM_MODEL", "openai-gpt-oss-120b"),
        llm_temperature=float(os.getenv("OUTREACH_LLM_TEMPERATURE", "0.5")),
        llm_max_tokens=int(os.getenv("OUTREACH_LLM_MAX_TOKENS", "1200")),
        max_concurrent_sends=int(os.getenv("OUTREACH_MAX_CONCURRENT", "3")),
        send_delay_seconds=float(os.getenv("OUTREACH_SEND_DELAY", "2.0")),
        daily_send_limit=int(os.getenv("OUTREACH_DAILY_LIMIT", "50")),
    )
