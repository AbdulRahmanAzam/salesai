from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class PersonalisationSettings:
    llm_api_key: str | None
    llm_base_url: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int
    max_concurrent_drafts: int
    min_research_confidence: float


def get_personalisation_settings() -> PersonalisationSettings:
    load_dotenv()
    return PersonalisationSettings(
        llm_api_key=os.getenv("PERSONALISATION_LLM_API_KEY"),
        llm_base_url=os.getenv(
            "PERSONALISATION_LLM_BASE_URL", "https://inference.do-ai.run/v1"
        ),
        llm_model=os.getenv("PERSONALISATION_LLM_MODEL", "openai-gpt-oss-120b"),
        llm_temperature=float(os.getenv("PERSONALISATION_LLM_TEMPERATURE", "0.7")),
        llm_max_tokens=int(os.getenv("PERSONALISATION_LLM_MAX_TOKENS", "1500")),
        max_concurrent_drafts=int(
            os.getenv("PERSONALISATION_MAX_CONCURRENT", "5")
        ),
        min_research_confidence=float(
            os.getenv("PERSONALISATION_MIN_CONFIDENCE", "0.1")
        ),
    )
