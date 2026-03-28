from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ICP:
    product_name: str
    product_pitch: str
    industries: list[str] = field(default_factory=list)
    employee_ranges: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    persona_titles: list[str] = field(default_factory=list)
    tech_stack: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    search_queries: list[str] = field(default_factory=list)
    exclude_domains: list[str] = field(default_factory=list)
    max_companies: int = 75
    max_contacts: int = 200


@dataclass
class Company:
    name: str
    domain: str | None = None
    linkedin_url: str | None = None
    location: str | None = None
    employee_range: str | None = None
    industry: str | None = None
    description: str | None = None
    source: str = "unknown"
    source_url: str | None = None
    technologies: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def key(self) -> str:
        if self.domain:
            return self.domain.lower().strip()
        return self.name.lower().strip()


@dataclass
class Contact:
    full_name: str
    title: str | None
    company_name: str
    company_domain: str | None
    email: str | None = None
    linkedin_url: str | None = None
    phone: str | None = None
    location: str | None = None
    source: str = "unknown"
    source_url: str | None = None
    confidence: float = 0.0
    signals: list[str] = field(default_factory=list)
    research_notes: list[str] = field(default_factory=list)

    def key(self) -> str:
        base = (self.full_name or "").lower().strip()
        domain = (self.company_domain or self.company_name or "").lower().strip()
        return f"{base}|{domain}"


@dataclass
class ProspectDraft:
    contact: Contact
    company: Company | None
    score: float
    reasons: list[str]
    relevance_explanation: str = ""
    status: str = "review_required"
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_record(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["contact"] = asdict(self.contact)
        if self.company:
            payload["company"] = asdict(self.company)
        else:
            payload["company"] = None
        return payload
