from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from research_agent.models import CompanyProfile, PersonProfile


class ResearchSource(ABC):
    """Base class for all research data sources."""

    name: str = "base_research_source"

    @abstractmethod
    def research_company(self, company_name: str, domain: str | None) -> dict[str, Any]:
        """Return raw research data about a company.

        The returned dict is merged into CompanyProfile fields by the pipeline.
        Keys should match CompanyProfile field names where possible, plus an
        optional ``_raw`` key for unstructured data the LLM can reference.
        """
        raise NotImplementedError

    @abstractmethod
    def research_person(
        self,
        full_name: str,
        company_name: str | None,
        domain: str | None,
    ) -> dict[str, Any]:
        """Return raw research data about a person.

        The returned dict is merged into PersonProfile fields by the pipeline.
        Keys should match PersonProfile field names where possible, plus an
        optional ``_raw`` key for unstructured data the LLM can reference.
        """
        raise NotImplementedError
