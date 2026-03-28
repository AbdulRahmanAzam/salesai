from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    # API sources
    apollo_api_key: str | None
    apollo_base_url: str
    hunter_api_key: str | None
    opencorporates_api_token: str | None
    github_token: str | None
    producthunt_token: str | None
    google_cse_api_key: str | None
    google_cse_cx: str | None
    serper_api_key: str | None

    # LLM for ICP interpretation + relevance scoring
    llm_api_key: str | None
    llm_base_url: str
    llm_model: str

    # Runtime
    http_timeout_seconds: int
    max_source_results: int
    enable_mock_fallback: bool


def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        apollo_api_key=os.getenv("APOLLO_API_KEY"),
        apollo_base_url=os.getenv("APOLLO_BASE_URL", "https://api.apollo.io"),
        hunter_api_key=os.getenv("HUNTER_API_KEY"),
        opencorporates_api_token=os.getenv("OPENCORPORATES_API_TOKEN"),
        github_token=os.getenv("GITHUB_TOKEN"),
        producthunt_token=os.getenv("PRODUCTHUNT_TOKEN"),
        google_cse_api_key=os.getenv("GOOGLE_CSE_API_KEY"),
        google_cse_cx=os.getenv("GOOGLE_CSE_CX"),
        serper_api_key=os.getenv("SERPER_API_KEY"),
        llm_api_key=os.getenv("PROSPECTING_LLM_API_KEY"),
        llm_base_url=os.getenv(
            "PROSPECTING_LLM_BASE_URL", "https://inference.do-ai.run/v1"
        ),
        llm_model=os.getenv("PROSPECTING_LLM_MODEL", "openai-gpt-oss-120b"),
        http_timeout_seconds=int(os.getenv("HTTP_TIMEOUT_SECONDS", "30")),
        max_source_results=int(os.getenv("MAX_SOURCE_RESULTS", "100")),
        enable_mock_fallback=os.getenv("ENABLE_MOCK_FALLBACK", "true").lower() in ("true", "1", "yes"),
    )
