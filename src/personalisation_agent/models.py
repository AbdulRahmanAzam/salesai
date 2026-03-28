from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class OutreachDraft:
    """A single personalised outreach message ready for human review."""

    contact_name: str
    contact_title: str | None
    contact_company: str
    contact_email: str | None
    contact_linkedin: str | None
    subject: str
    body: str
    personalization_score: float
    personalization_signals: list[str] = field(default_factory=list)
    status: str = "draft"
    prospect_score: float = 0.0
    research_confidence: float = 0.0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PersonalisationResult:
    """Wraps the full output for one contact: the draft + context used."""

    draft: OutreachDraft
    dossier_used: dict[str, Any]
    icp_product: str
    icp_pitch: str

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.draft.to_dict(),
            "dossier_used": {
                "contact_name": self.dossier_used.get("contact_name"),
                "contact_company": self.dossier_used.get("contact_company"),
                "research_confidence": self.dossier_used.get("research_confidence"),
                "talking_points_count": len(
                    self.dossier_used.get("talking_points", [])
                ),
                "pain_points_count": len(self.dossier_used.get("pain_points", [])),
            },
            "icp_product": self.icp_product,
            "icp_pitch": self.icp_pitch,
        }
