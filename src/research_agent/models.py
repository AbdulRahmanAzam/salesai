from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    published_date: str | None = None
    snippet: str | None = None


@dataclass
class ActivityItem:
    activity_type: str
    title: str
    url: str | None = None
    date: str | None = None
    snippet: str | None = None


@dataclass
class CareerEntry:
    title: str
    company: str
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


@dataclass
class EducationEntry:
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    end_year: int | None = None


@dataclass
class CompanyProfile:
    name: str
    domain: str | None = None
    description: str | None = None
    industry: str | None = None
    employee_count: str | None = None
    founded_year: int | None = None
    funding_stage: str | None = None
    total_funding: str | None = None
    headquarters: str | None = None
    technologies: list[str] = field(default_factory=list)
    competitors: list[str] = field(default_factory=list)
    recent_news: list[NewsItem] = field(default_factory=list)
    social_profiles: dict[str, str] = field(default_factory=dict)
    key_metrics: dict[str, str] = field(default_factory=dict)
    raw_sources: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PersonProfile:
    full_name: str
    current_title: str | None = None
    current_company: str | None = None
    bio: str | None = None
    career_history: list[CareerEntry] = field(default_factory=list)
    education: list[EducationEntry] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    publications: list[str] = field(default_factory=list)
    social_profiles: dict[str, str] = field(default_factory=dict)
    recent_activity: list[ActivityItem] = field(default_factory=list)
    mutual_interests: list[str] = field(default_factory=list)
    raw_sources: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchDossier:
    prospect_score: float
    prospect_reasons: list[str]
    contact_name: str
    contact_title: str | None
    contact_company: str
    contact_email: str | None
    contact_linkedin: str | None
    company_profile: CompanyProfile
    person_profile: PersonProfile
    talking_points: list[str] = field(default_factory=list)
    pain_points: list[str] = field(default_factory=list)
    relevance_summary: str = ""
    research_confidence: float = 0.0
    researched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
