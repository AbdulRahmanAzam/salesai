from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tracking_agent.analyzer import ResponseAnalyzer
from tracking_agent.checker import ResponseChecker
from tracking_agent.config import TrackingSettings
from tracking_agent.models import (
    FollowUp,
    Response,
    TrackingEntry,
    TrackingResult,
)
from tracking_agent.sender import FollowUpSender
from event_emitter import emit_step, emit_item, emit_summary, ProgressCallback


def run_tracking(
    queue_path: Path,
    settings: TrackingSettings,
    output_dir: Path,
    action: str = "check",
    since_date: str | None = None,
    auto_follow_up: bool = False,
    product_name: str = "",
    product_pitch: str = "",
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """
    Main tracking pipeline.

    Actions:
      - 'check':     Check IMAP for responses → classify → output entries
      - 'analyze':   Re-analyze existing responses with LLM
      - 'follow-up': Generate follow-up drafts for leads that need them
      - 'send':      Send approved follow-ups via SMTP
      - 'status':    Report current tracking state
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    entries_path = output_dir / "tracking_entries.json"
    follow_ups_path = output_dir / "tracking_follow_ups.json"
    summary_path = output_dir / "tracking_summary.json"
    log_path = output_dir / "tracking_log.csv"

    def _step(idx: int, status: str, label: str, **kw: Any) -> None:
        print(f"[info] {label}")
        if progress:
            emit_step(idx, status, label, **kw)

    if action == "status":
        return _report_status(entries_path, follow_ups_path)

    # Load sent messages from outreach queue
    _step(0, "running", f"Loading sent messages from {queue_path.name}...")
    sent_messages = _load_sent_messages(queue_path)
    if not sent_messages:
        _step(0, "done", "No sent messages found in outreach queue.", count=0)
        return {"messages": 0, "action": action}

    # Load or create tracking entries
    entries = _load_entries(entries_path)
    entries = _sync_entries(entries, sent_messages)
    _step(0, "done", f"Loaded {len(sent_messages)} sent messages, {len(entries)} tracking entries", count=len(entries))

    follow_ups = _load_follow_ups(follow_ups_path)

    if action == "check":
        # Check for new responses via IMAP
        _step(1, "running", "Checking IMAP for responses...")
        checker = ResponseChecker(settings)

        if checker.is_configured():
            responses = checker.check_responses(sent_messages, since_date)
            print(f"[info] Found {len(responses)} new responses")

            # Analyze responses with LLM if available
            analyzer = _get_analyzer(settings)
            for resp in responses:
                entry = _find_entry(entries, resp.outreach_message_id)
                if not entry:
                    continue

                # Analyze response
                if analyzer:
                    orig_context = _get_original_context(sent_messages, resp.outreach_message_id)
                    analysis = analyzer.analyze_response(resp, orig_context)
                    resp.warmth = analysis.get("warmth", "unknown")
                    resp.sentiment = analysis.get("sentiment", "unknown")
                    resp.key_points = analysis.get("key_points", [])
                    resp.needs_follow_up = analysis.get("needs_follow_up", False)
                    resp.auto_classified = True

                # Update tracking entry
                entry.status = "replied"
                entry.replied_at = resp.received_at
                entry.reply_snippet = resp.body[:200] if resp.body else None
                entry.warmth = resp.warmth
                entry.is_warm = resp.warmth in ("warm", "hot", "meeting_requested")
                entry.last_activity_at = resp.received_at

                # Avoid duplicate responses
                existing_ids = {r.id if isinstance(r, Response) else r.get("id") for r in entry.responses}
                if resp.id not in existing_ids:
                    entry.responses.append(resp)
        else:
            _step(1, "done", "IMAP not configured. Skipping response check.", count=0)
            print("[info] Set TRACKING_IMAP_* environment variables to enable response checking.")

    elif action == "analyze":
        # Re-analyze existing responses with LLM
        analyzer = _get_analyzer(settings)
        if not analyzer:
            print("[warn] LLM not configured. Cannot analyze responses.")
            return {"error": "LLM not configured"}

        analyzed_count = 0
        for entry in entries:
            for resp in entry.responses:
                if isinstance(resp, dict):
                    resp = Response(**{k: v for k, v in resp.items() if k != "id"})
                orig_context = _get_original_context(sent_messages, entry.outreach_message_id)
                analysis = analyzer.analyze_response(resp, orig_context)
                resp.warmth = analysis.get("warmth", "unknown")
                resp.sentiment = analysis.get("sentiment", "unknown")
                resp.key_points = analysis.get("key_points", [])
                resp.needs_follow_up = analysis.get("needs_follow_up", False)
                resp.auto_classified = True

                entry.warmth = resp.warmth
                entry.is_warm = resp.warmth in ("warm", "hot", "meeting_requested")
                analyzed_count += 1

        print(f"[info] Re-analyzed {analyzed_count} responses")

    elif action == "follow-up":
        # Generate follow-up drafts
        analyzer = _get_analyzer(settings)
        if not analyzer:
            print("[warn] LLM not configured. Cannot generate follow-ups.")
            return {"error": "LLM not configured"}

        generated = 0
        for entry in entries:
            if entry.follow_up_count >= settings.max_follow_ups_per_lead:
                continue

            for resp in entry.responses:
                if isinstance(resp, dict):
                    r = Response(**{k: v for k, v in resp.items()})
                else:
                    r = resp

                needs = r.needs_follow_up if isinstance(r, Response) else resp.get("needs_follow_up", False)
                if not needs:
                    continue

                orig_context = _get_original_context(sent_messages, entry.outreach_message_id)
                warmth = r.warmth if isinstance(r, Response) else resp.get("warmth", "unknown")
                analysis = {
                    "warmth": warmth,
                    "sentiment": r.sentiment if isinstance(r, Response) else resp.get("sentiment", "unknown"),
                    "key_points": r.key_points if isinstance(r, Response) else resp.get("key_points", []),
                    "follow_up_strategy": "Continue engagement based on response analysis",
                }

                follow_up = analyzer.generate_follow_up(
                    response=r,
                    original_context=orig_context,
                    analysis=analysis,
                    product_name=product_name,
                    product_pitch=product_pitch,
                    follow_up_count=entry.follow_up_count,
                )

                # Auto-approve warm/hot leads if configured
                if auto_follow_up and warmth in ("warm", "hot", "meeting_requested"):
                    follow_up.status = "approved"

                follow_ups.append(follow_up)
                entry.follow_ups.append(follow_up)
                entry.follow_up_count += 1
                generated += 1

        print(f"[info] Generated {generated} follow-up drafts")

    elif action == "send":
        # Send approved follow-ups
        sender = FollowUpSender(settings)
        if not sender.is_configured():
            print("[warn] SMTP not configured. Follow-ups queued but not sent.")
            return {"error": "SMTP not configured"}

        sendable = [f for f in follow_ups if f.status == "approved" and f.contact_email]
        if isinstance(sendable[0] if sendable else None, dict):
            sendable = [FollowUp(**f) for f in sendable]

        sent_count = 0
        for fu in sendable:
            success, message_id, error = sender.send(
                to_email=fu.contact_email,
                to_name=fu.contact_name,
                subject=fu.subject,
                body=fu.body,
            )
            if success:
                fu.status = "sent"
                fu.sent_at = datetime.now(timezone.utc).isoformat()
                fu.message_id = message_id
                sent_count += 1
                print(f"  [ok] Follow-up sent to {fu.contact_name}")
            else:
                fu.status = "failed"
                print(f"  [fail] {fu.contact_name}: {error}")

        print(f"[info] Sent {sent_count}/{len(sendable)} follow-ups")

    # Build result
    _step(2, "running", "Building tracking summary...")
    result = _build_result(entries, follow_ups)

    # Emit individual tracking entry items for progressive rendering
    if progress:
        for entry in entries:
            emit_item(entry)

    # Write outputs
    _write_json(entries_path, [e.to_dict() for e in entries])
    _write_json(follow_ups_path, [f.to_dict() if isinstance(f, FollowUp) else f for f in follow_ups])
    _write_json(summary_path, result.to_dict())
    _write_log_csv(log_path, entries)
    _step(2, "done", f"Tracking complete — {result.total_tracked} entries tracked, {result.replied} replies")

    summary = {
        "action": action,
        **result.to_dict(),
        "entries_json": str(entries_path),
        "follow_ups_json": str(follow_ups_path),
    }

    if progress:
        emit_summary(summary)

    return summary


def approve_follow_up(
    follow_ups_path: Path, follow_up_id: str, notes: str = ""
) -> dict[str, Any]:
    """Approve a single follow-up by ID."""
    follow_ups = _load_follow_ups(follow_ups_path)
    for fu in follow_ups:
        fid = fu.id if isinstance(fu, FollowUp) else fu.get("id")
        if fid == follow_up_id:
            if isinstance(fu, FollowUp):
                fu.status = "approved"
            else:
                fu["status"] = "approved"
            _write_json(follow_ups_path, [f.to_dict() if isinstance(f, FollowUp) else f for f in follow_ups])
            return {"status": "approved", "id": follow_up_id}
    return {"error": f"Follow-up {follow_up_id} not found"}


def reject_follow_up(
    follow_ups_path: Path, follow_up_id: str
) -> dict[str, Any]:
    """Reject a single follow-up by ID."""
    follow_ups = _load_follow_ups(follow_ups_path)
    for fu in follow_ups:
        fid = fu.id if isinstance(fu, FollowUp) else fu.get("id")
        if fid == follow_up_id:
            if isinstance(fu, FollowUp):
                fu.status = "rejected"
            else:
                fu["status"] = "rejected"
            _write_json(follow_ups_path, [f.to_dict() if isinstance(f, FollowUp) else f for f in follow_ups])
            return {"status": "rejected", "id": follow_up_id}
    return {"error": f"Follow-up {follow_up_id} not found"}


# ── Internal helpers ──


def _load_sent_messages(path: Path) -> list[dict[str, Any]]:
    """Load sent/outreach messages from outreach queue JSON."""
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    return [m for m in raw if m.get("status") in ("sent", "delivered", "approved", "scheduled")]


def _load_entries(path: Path) -> list[TrackingEntry]:
    """Load existing tracking entries from JSON."""
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = []
    for item in raw:
        responses = []
        for r in item.get("responses", []):
            responses.append(Response(**{k: v for k, v in r.items()}))
        follow_ups = []
        for f in item.get("follow_ups", []):
            follow_ups.append(FollowUp(**{k: v for k, v in f.items()}))

        entry = TrackingEntry(
            outreach_message_id=item.get("outreach_message_id", ""),
            contact_name=item.get("contact_name", ""),
            contact_company=item.get("contact_company", ""),
            contact_email=item.get("contact_email", ""),
            original_subject=item.get("original_subject", ""),
            status=item.get("status", "sent"),
            sent_at=item.get("sent_at"),
            opened_at=item.get("opened_at"),
            replied_at=item.get("replied_at"),
            reply_snippet=item.get("reply_snippet"),
            is_warm=item.get("is_warm", False),
            warmth=item.get("warmth", "unknown"),
            follow_up_count=item.get("follow_up_count", 0),
            responses=responses,
            follow_ups=follow_ups,
            last_activity_at=item.get("last_activity_at"),
        )
        entries.append(entry)
    return entries


def _load_follow_ups(path: Path) -> list[FollowUp]:
    """Load existing follow-ups from JSON."""
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [FollowUp(**{k: v for k, v in f.items()}) for f in raw]


def _sync_entries(
    entries: list[TrackingEntry], sent_messages: list[dict]
) -> list[TrackingEntry]:
    """Ensure every sent message has a tracking entry."""
    existing_ids = {e.outreach_message_id for e in entries}
    for msg in sent_messages:
        msg_id = msg.get("id", "")
        if msg_id and msg_id not in existing_ids:
            entries.append(
                TrackingEntry(
                    outreach_message_id=msg_id,
                    contact_name=msg.get("contact_name", ""),
                    contact_company=msg.get("contact_company", ""),
                    contact_email=msg.get("contact_email", ""),
                    original_subject=msg.get("subject", ""),
                    status="sent",
                    sent_at=msg.get("sent_at"),
                    last_activity_at=msg.get("sent_at"),
                )
            )
    return entries


def _find_entry(
    entries: list[TrackingEntry], outreach_message_id: str
) -> TrackingEntry | None:
    for entry in entries:
        if entry.outreach_message_id == outreach_message_id:
            return entry
    return None


def _get_analyzer(settings: TrackingSettings) -> ResponseAnalyzer | None:
    """Build analyzer only if LLM is configured."""
    if not settings.llm_api_key:
        return None
    return ResponseAnalyzer(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )


def _get_original_context(
    sent_messages: list[dict], outreach_message_id: str
) -> dict[str, Any]:
    for msg in sent_messages:
        if msg.get("id") == outreach_message_id:
            return msg
    return {}


def _build_result(
    entries: list[TrackingEntry], follow_ups: list,
) -> TrackingResult:
    total = len(entries)
    sent = sum(1 for e in entries if e.status in ("sent",))
    opened = sum(1 for e in entries if e.opened_at)
    replied = sum(1 for e in entries if e.status == "replied")
    warm = sum(1 for e in entries if e.is_warm)
    no_response = sum(1 for e in entries if e.status in ("sent", "no_response") and not e.replied_at)

    fu_generated = len(follow_ups)
    fu_sent = sum(1 for f in follow_ups if (f.status if isinstance(f, FollowUp) else f.get("status")) == "sent")

    return TrackingResult(
        total_tracked=total,
        sent=total,
        opened=opened,
        replied=replied,
        warm_leads=warm,
        no_response=no_response,
        follow_ups_generated=fu_generated,
        follow_ups_sent=fu_sent,
        open_rate=round(opened / total * 100, 1) if total else 0,
        reply_rate=round(replied / total * 100, 1) if total else 0,
    )


def _report_status(
    entries_path: Path, follow_ups_path: Path
) -> dict[str, Any]:
    if not entries_path.exists():
        return {"error": "No tracking data found. Run 'tracking --action check' first."}
    entries = _load_entries(entries_path)
    follow_ups = _load_follow_ups(follow_ups_path)
    result = _build_result(entries, follow_ups)
    status_counts: dict[str, int] = {}
    for e in entries:
        status_counts[e.status] = status_counts.get(e.status, 0) + 1
    return {
        "total_tracked": len(entries),
        "statuses": status_counts,
        "warm_leads": result.warm_leads,
        "open_rate": result.open_rate,
        "reply_rate": result.reply_rate,
        "follow_ups_generated": result.follow_ups_generated,
        "follow_ups_sent": result.follow_ups_sent,
    }


def _write_json(path: Path, payload: list | dict) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _write_log_csv(path: Path, entries: list[TrackingEntry]) -> None:
    fields = [
        "outreach_message_id",
        "contact_name",
        "contact_company",
        "contact_email",
        "status",
        "warmth",
        "is_warm",
        "sent_at",
        "replied_at",
        "follow_up_count",
        "reply_snippet",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for e in entries:
            w.writerow({
                "outreach_message_id": e.outreach_message_id,
                "contact_name": e.contact_name,
                "contact_company": e.contact_company,
                "contact_email": e.contact_email,
                "status": e.status,
                "warmth": e.warmth,
                "is_warm": e.is_warm,
                "sent_at": e.sent_at or "",
                "replied_at": e.replied_at or "",
                "follow_up_count": e.follow_up_count,
                "reply_snippet": (e.reply_snippet or "")[:100],
            })
