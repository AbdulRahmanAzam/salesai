from __future__ import annotations

import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from outreach_agent.config import OutreachSettings
from outreach_agent.models import OutreachMessage, OutreachQueueResult
from outreach_agent.sender import EmailSender


def run_outreach(
    drafts_path: Path,
    settings: OutreachSettings,
    output_dir: Path,
    action: str = "queue",
    auto_approve_above: float | None = None,
    max_sends: int | None = None,
) -> dict[str, Any]:
    """
    Main outreach pipeline.

    Actions:
      - 'queue':   Load drafts → build reviewed queue → output JSON/CSV (no sending)
      - 'approve': Load drafts → auto-approve those above threshold → output
      - 'send':    Load approved messages → send via SMTP → update statuses
      - 'status':  Load existing queue and report current statuses
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    queue_path = output_dir / "outreach_queue.json"
    log_path = output_dir / "outreach_log.csv"
    summary_path = output_dir / "outreach_summary.json"

    if action == "status":
        return _report_status(queue_path)

    # Load drafts from personalisation agent output
    drafts = _load_drafts(drafts_path)
    if not drafts:
        print("[info] No drafts found to process.")
        return {"messages": 0, "action": action}

    # Build OutreachMessage objects
    if queue_path.exists() and action in ("send", "approve"):
        # Load existing queue state to preserve approvals
        messages = _load_queue(queue_path)
        # Merge any new drafts
        existing_ids = {m.id for m in messages}
        for draft in drafts:
            msg = OutreachMessage.from_draft(draft)
            if msg.id not in existing_ids:
                messages.append(msg)
    else:
        messages = [OutreachMessage.from_draft(d) for d in drafts]

    result = OutreachQueueResult(total_loaded=len(messages))
    skipped_no_email = 0

    if action == "approve" or (action == "send" and auto_approve_above is not None):
        threshold = auto_approve_above if auto_approve_above is not None else 50.0
        messages, approved_count = _auto_approve(messages, threshold)
        result.approved = approved_count
        print(f"[info] Auto-approved {approved_count} messages (score >= {threshold})")

    if action == "send":
        sender = EmailSender(settings)
        if not sender.is_configured():
            print("[warn] SMTP not configured. Messages queued but not sent.")
            print("[info] Set OUTREACH_SMTP_* environment variables to enable sending.")
            # Mark approved messages as 'scheduled' to indicate intent
            for msg in messages:
                if msg.status == "approved":
                    msg.status = "scheduled"
                    msg.scheduled_at = datetime.now(timezone.utc).isoformat()
        else:
            sendable = [
                m for m in messages
                if m.status in ("approved", "scheduled") and m.contact_email
            ]
            if max_sends:
                sendable = sendable[:max_sends]

            print(f"[info] Sending {len(sendable)} emails via {settings.smtp_host}...")
            sent_count, fail_count = _send_messages(sendable, sender)
            result.sent = sent_count
            result.failed = fail_count
            print(f"[info] Sent: {sent_count}, Failed: {fail_count}")

    # Count skipped (no email)
    for msg in messages:
        if not msg.contact_email and msg.status == "draft":
            skipped_no_email += 1

    result.skipped_no_email = skipped_no_email
    result.rejected = sum(1 for m in messages if m.status == "rejected")
    result.messages = messages

    scores = [m.personalization_score for m in messages if m.personalization_score > 0]
    result.avg_personalization_score = (
        round(sum(scores) / len(scores), 1) if scores else 0
    )

    # Write outputs
    _write_json(queue_path, [m.to_dict() for m in messages])
    _write_log_csv(log_path, messages)
    _write_json(summary_path, result.to_dict())

    summary = {
        "action": action,
        **result.to_dict(),
        "queue_json": str(queue_path),
        "log_csv": str(log_path),
    }
    return summary


def approve_message(
    queue_path: Path, message_id: str, notes: str = ""
) -> dict[str, Any]:
    """Approve a single message by ID."""
    messages = _load_queue(queue_path)
    for msg in messages:
        if msg.id == message_id:
            msg.status = "approved"
            msg.approved_at = datetime.now(timezone.utc).isoformat()
            msg.reviewer_notes = notes
            _write_json(queue_path, [m.to_dict() for m in messages])
            return {"status": "approved", "id": message_id}
    return {"error": f"Message {message_id} not found"}


def reject_message(
    queue_path: Path, message_id: str, notes: str = ""
) -> dict[str, Any]:
    """Reject a single message by ID."""
    messages = _load_queue(queue_path)
    for msg in messages:
        if msg.id == message_id:
            msg.status = "rejected"
            msg.reviewer_notes = notes
            _write_json(queue_path, [m.to_dict() for m in messages])
            return {"status": "rejected", "id": message_id}
    return {"error": f"Message {message_id} not found"}


def update_draft(
    queue_path: Path,
    message_id: str,
    subject: str | None = None,
    body: str | None = None,
) -> dict[str, Any]:
    """Edit a draft's subject or body. Keeps status as draft for re-review."""
    messages = _load_queue(queue_path)
    for msg in messages:
        if msg.id == message_id:
            if subject is not None:
                msg.subject = subject
            if body is not None:
                msg.body = body
            msg.status = "draft"  # Reset to draft after edit
            _write_json(queue_path, [m.to_dict() for m in messages])
            return {"status": "updated", "id": message_id}
    return {"error": f"Message {message_id} not found"}


# ── Internal helpers ──


def _load_drafts(path: Path) -> list[dict[str, Any]]:
    """Load personalisation agent drafts from JSON."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Expected a JSON array in {path}")
    return raw


def _load_queue(path: Path) -> list[OutreachMessage]:
    """Load existing queue state."""
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    messages = []
    for item in raw:
        msg = OutreachMessage(
            id=item.get("id", ""),
            contact_name=item.get("contact_name", ""),
            contact_title=item.get("contact_title"),
            contact_company=item.get("contact_company", ""),
            contact_email=item.get("contact_email"),
            contact_linkedin=item.get("contact_linkedin"),
            subject=item.get("subject", ""),
            body=item.get("body", ""),
            personalization_score=item.get("personalization_score", 0),
            personalization_signals=item.get("personalization_signals", []),
            prospect_score=item.get("prospect_score", 0),
            research_confidence=item.get("research_confidence", 0),
            status=item.get("status", "draft"),
            reviewer_notes=item.get("reviewer_notes", ""),
            approved_at=item.get("approved_at"),
            scheduled_at=item.get("scheduled_at"),
            sent_at=item.get("sent_at"),
            delivered_at=item.get("delivered_at"),
            message_id=item.get("message_id"),
            send_error=item.get("send_error"),
            created_at=item.get("created_at", ""),
        )
        messages.append(msg)
    return messages


def _auto_approve(
    messages: list[OutreachMessage], threshold: float
) -> tuple[list[OutreachMessage], int]:
    """Auto-approve drafts with personalization_score >= threshold that have emails."""
    approved = 0
    now = datetime.now(timezone.utc).isoformat()
    for msg in messages:
        if (
            msg.status == "draft"
            and msg.personalization_score >= threshold
            and msg.contact_email
        ):
            msg.status = "approved"
            msg.approved_at = now
            approved += 1
    return messages, approved


def _send_messages(
    messages: list[OutreachMessage], sender: EmailSender
) -> tuple[int, int]:
    """Send messages via SMTP. Returns (sent_count, fail_count)."""
    sent = 0
    failed = 0

    for msg in messages:
        if not msg.contact_email:
            msg.send_error = "No email address"
            msg.status = "failed"
            failed += 1
            continue

        print(f"  [send] {msg.contact_name} <{msg.contact_email}>...")
        success, message_id, error = sender.send(
            to_email=msg.contact_email,
            to_name=msg.contact_name,
            subject=msg.subject,
            body=msg.body,
        )

        if success:
            msg.status = "sent"
            msg.sent_at = datetime.now(timezone.utc).isoformat()
            msg.message_id = message_id
            msg.send_error = None
            sent += 1
            print(f"  [ok] Sent to {msg.contact_name}")
        else:
            msg.status = "failed"
            msg.send_error = error
            failed += 1
            print(f"  [fail] {msg.contact_name}: {error}")

    return sent, failed


def _report_status(queue_path: Path) -> dict[str, Any]:
    """Report current status of the outreach queue."""
    if not queue_path.exists():
        return {"error": "No outreach queue found. Run 'outreach --action queue' first."}
    messages = _load_queue(queue_path)
    status_counts: dict[str, int] = {}
    for msg in messages:
        status_counts[msg.status] = status_counts.get(msg.status, 0) + 1
    return {
        "total": len(messages),
        "statuses": status_counts,
        "with_email": sum(1 for m in messages if m.contact_email),
        "queue_path": str(queue_path),
    }


def _write_json(path: Path, payload: list | dict) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _write_log_csv(path: Path, messages: list[OutreachMessage]) -> None:
    fields = [
        "id",
        "contact_name",
        "contact_company",
        "contact_email",
        "subject",
        "personalization_score",
        "status",
        "approved_at",
        "sent_at",
        "message_id",
        "send_error",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for m in messages:
            w.writerow({
                "id": m.id,
                "contact_name": m.contact_name,
                "contact_company": m.contact_company,
                "contact_email": m.contact_email,
                "subject": m.subject,
                "personalization_score": m.personalization_score,
                "status": m.status,
                "approved_at": m.approved_at or "",
                "sent_at": m.sent_at or "",
                "message_id": m.message_id or "",
                "send_error": m.send_error or "",
            })
