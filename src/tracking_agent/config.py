from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class TrackingSettings:
    """Configuration for the tracking agent."""

    # IMAP for checking responses
    imap_host: str
    imap_port: int
    imap_username: str | None
    imap_password: str | None
    imap_use_ssl: bool
    imap_folder: str

    # SMTP for sending follow-ups (reuse outreach settings or separate)
    smtp_host: str
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None
    smtp_use_tls: bool
    sender_email: str
    sender_name: str

    # LLM for response analysis and follow-up generation
    llm_api_key: str | None
    llm_base_url: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int

    # Runtime
    check_interval_seconds: int
    max_follow_ups_per_lead: int
    follow_up_delay_days: int


def get_tracking_settings() -> TrackingSettings:
    load_dotenv()
    return TrackingSettings(
        # IMAP
        imap_host=os.getenv("TRACKING_IMAP_HOST", "imap.gmail.com"),
        imap_port=int(os.getenv("TRACKING_IMAP_PORT", "993")),
        imap_username=os.getenv("TRACKING_IMAP_USERNAME"),
        imap_password=os.getenv("TRACKING_IMAP_PASSWORD"),
        imap_use_ssl=os.getenv("TRACKING_IMAP_USE_SSL", "true").lower() == "true",
        imap_folder=os.getenv("TRACKING_IMAP_FOLDER", "INBOX"),
        # SMTP (defaults to outreach SMTP if not separately configured)
        smtp_host=os.getenv(
            "TRACKING_SMTP_HOST", os.getenv("OUTREACH_SMTP_HOST", "smtp.gmail.com")
        ),
        smtp_port=int(
            os.getenv("TRACKING_SMTP_PORT", os.getenv("OUTREACH_SMTP_PORT", "587"))
        ),
        smtp_username=os.getenv(
            "TRACKING_SMTP_USERNAME", os.getenv("OUTREACH_SMTP_USERNAME")
        ),
        smtp_password=os.getenv(
            "TRACKING_SMTP_PASSWORD", os.getenv("OUTREACH_SMTP_PASSWORD")
        ),
        smtp_use_tls=os.getenv(
            "TRACKING_SMTP_USE_TLS", os.getenv("OUTREACH_SMTP_USE_TLS", "true")
        ).lower() == "true",
        sender_email=os.getenv(
            "TRACKING_SENDER_EMAIL", os.getenv("OUTREACH_SENDER_EMAIL", "")
        ),
        sender_name=os.getenv(
            "TRACKING_SENDER_NAME", os.getenv("OUTREACH_SENDER_NAME", "")
        ),
        # LLM
        llm_api_key=os.getenv("TRACKING_LLM_API_KEY"),
        llm_base_url=os.getenv(
            "TRACKING_LLM_BASE_URL", "https://inference.do-ai.run/v1"
        ),
        llm_model=os.getenv("TRACKING_LLM_MODEL", "openai-gpt-oss-120b"),
        llm_temperature=float(os.getenv("TRACKING_LLM_TEMPERATURE", "0.5")),
        llm_max_tokens=int(os.getenv("TRACKING_LLM_MAX_TOKENS", "1200")),
        # Runtime
        check_interval_seconds=int(os.getenv("TRACKING_CHECK_INTERVAL", "300")),
        max_follow_ups_per_lead=int(os.getenv("TRACKING_MAX_FOLLOW_UPS", "3")),
        follow_up_delay_days=int(os.getenv("TRACKING_FOLLOW_UP_DELAY_DAYS", "3")),
    )
