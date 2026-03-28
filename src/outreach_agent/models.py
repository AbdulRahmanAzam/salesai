from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class OutreachMessage:
    """A single outreach message in the reviewed queue."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    contact_name: str = ""
    contact_title: str | None = None
    contact_company: str = ""
    contact_email: str | None = None
    contact_linkedin: str | None = None
    subject: str = ""
    body: str = ""
    personalization_score: float = 0.0
    personalization_signals: list[str] = field(default_factory=list)
    prospect_score: float = 0.0
    research_confidence: float = 0.0
    # Workflow states: draft → approved → scheduled → sent → delivered / bounced / failed
    # Also: rejected (human decided not to send)
    status: str = "draft"
    reviewer_notes: str = ""
    approved_at: str | None = None
    scheduled_at: str | None = None
    sent_at: str | None = None
    delivered_at: str | None = None
    message_id: str | None = None  # SMTP Message-ID for tracking replies
    send_error: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_draft(cls, draft: dict[str, Any]) -> OutreachMessage:
        """Create an OutreachMessage from a personalisation agent draft dict."""
        return cls(
            contact_name=draft.get("contact_name", "Unknown"),
            contact_title=draft.get("contact_title"),
            contact_company=draft.get("contact_company", "Unknown"),
            contact_email=draft.get("contact_email"),
            contact_linkedin=draft.get("contact_linkedin"),
            subject=draft.get("subject", ""),
            body=draft.get("body", ""),
            personalization_score=draft.get("personalization_score", 0),
            personalization_signals=draft.get("personalization_signals", []),
            prospect_score=draft.get("prospect_score", 0),
            research_confidence=draft.get("research_confidence", 0),
            status=draft.get("status", "draft"),
            created_at=draft.get(
                "created_at", datetime.now(timezone.utc).isoformat()
            ),
        )


@dataclass
class OutreachQueueResult:
    """Summary of an outreach pipeline run."""

    total_loaded: int = 0
    approved: int = 0
    sent: int = 0
    failed: int = 0
    rejected: int = 0
    skipped_no_email: int = 0
    avg_personalization_score: float = 0.0
    messages: list[OutreachMessage] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_loaded": self.total_loaded,
            "approved": self.approved,
            "sent": self.sent,
            "failed": self.failed,
            "rejected": self.rejected,
            "skipped_no_email": self.skipped_no_email,
            "avg_personalization_score": self.avg_personalization_score,
        }
