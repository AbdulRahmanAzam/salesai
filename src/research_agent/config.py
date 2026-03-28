from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class ResearchSettings:
    openai_api_key: str | None
    openai_base_url: str | None
    openai_model: str
    google_cse_api_key: str | None
    google_cse_cx: str | None
    github_token: str | None
    builtwith_api_key: str | None
    http_timeout_seconds: int
    max_concurrent_research: int


def get_research_settings() -> ResearchSettings:
    load_dotenv()
    return ResearchSettings(
        openai_api_key=os.getenv("RESEARCH_LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
        openai_base_url=os.getenv(
            "RESEARCH_LLM_BASE_URL", "https://inference.do-ai.run/v1"
        ),
        openai_model=os.getenv("RESEARCH_LLM_MODEL") or os.getenv("OPENAI_MODEL", "openai-gpt-oss-120b"),
        google_cse_api_key=os.getenv("GOOGLE_CSE_API_KEY"),
        google_cse_cx=os.getenv("GOOGLE_CSE_CX"),
        github_token=os.getenv("GITHUB_TOKEN"),
        builtwith_api_key=os.getenv("BUILTWITH_API_KEY"),
        http_timeout_seconds=int(os.getenv("HTTP_TIMEOUT_SECONDS", "30")),
        max_concurrent_research=int(os.getenv("MAX_CONCURRENT_RESEARCH", "5")),
    )
