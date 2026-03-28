from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Response:
    """A response received from a contact."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    outreach_message_id: str = ""
    contact_name: str = ""
    contact_company: str = ""
    contact_email: str = ""
    subject: str = ""
    body: str = ""
    received_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    # Populated by analyzer
    warmth: str = "unknown"  # cold, neutral, warm, hot, meeting_requested
    sentiment: str = "unknown"  # positive, negative, neutral, interested, objection
    key_points: list[str] = field(default_factory=list)
    needs_follow_up: bool = False
    auto_classified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FollowUp:
    """A generated follow-up message."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    response_id: str = ""
    outreach_message_id: str = ""
    contact_name: str = ""
    contact_company: str = ""
    contact_email: str = ""
    subject: str = ""
    body: str = ""
    follow_up_number: int = 1  # 1st, 2nd, 3rd follow-up
    status: str = "draft"  # draft, approved, sent, failed
    sent_at: str | None = None
    message_id: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrackingEntry:
    """Tracks full lifecycle of an outreach message."""

    outreach_message_id: str = ""
    contact_name: str = ""
    contact_company: str = ""
    contact_email: str = ""
    original_subject: str = ""
    status: str = "sent"  # sent, opened, replied, warm_lead, no_response, bounced
    sent_at: str | None = None
    opened_at: str | None = None
    replied_at: str | None = None
    reply_snippet: str | None = None
    is_warm: bool = False
    warmth: str = "unknown"
    follow_up_count: int = 0
    responses: list[Response] = field(default_factory=list)
    follow_ups: list[FollowUp] = field(default_factory=list)
    last_activity_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["responses"] = [r.to_dict() if isinstance(r, Response) else r for r in self.responses]
        d["follow_ups"] = [f.to_dict() if isinstance(f, FollowUp) else f for f in self.follow_ups]
        return d


@dataclass
class TrackingResult:
    """Summary of a tracking pipeline run."""

    total_tracked: int = 0
    sent: int = 0
    opened: int = 0
    replied: int = 0
    warm_leads: int = 0
    no_response: int = 0
    follow_ups_generated: int = 0
    follow_ups_sent: int = 0
    open_rate: float = 0.0
    reply_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
