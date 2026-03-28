from __future__ import annotations

import argparse
import json
from pathlib import Path

from outreach_agent.config import get_outreach_settings
from outreach_agent.pipeline import (
    approve_message,
    reject_message,
    run_outreach,
    update_draft,
)


def add_outreach_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "outreach",
        help="Run the outreach agent to manage, review, and send personalised messages.",
    )
    parser.add_argument(
        "--drafts",
        required=True,
        help="Path to outreach_drafts.json from the personalisation agent.",
    )
    parser.add_argument(
        "--out",
        default="output/outreach",
        help="Output directory for outreach queue and logs.",
    )
    parser.add_argument(
        "--action",
        choices=["queue", "approve", "send", "status"],
        default="queue",
        help=(
            "Action: 'queue' builds reviewed queue, 'approve' auto-approves above threshold, "
            "'send' sends approved messages via SMTP, 'status' reports queue state."
        ),
    )
    parser.add_argument(
        "--approve-above",
        type=float,
        default=None,
        help="Auto-approve drafts with personalization score >= this value (default: 50).",
    )
    parser.add_argument(
        "--max-sends",
        type=int,
        default=None,
        help="Max number of messages to send in one run.",
    )
    # Single-message operations
    parser.add_argument(
        "--approve-id",
        type=str,
        default=None,
        help="Approve a single message by ID.",
    )
    parser.add_argument(
        "--reject-id",
        type=str,
        default=None,
        help="Reject a single message by ID.",
    )
    parser.add_argument(
        "--notes",
        type=str,
        default="",
        help="Reviewer notes for approve/reject operations.",
    )


def run_outreach_command(args: argparse.Namespace) -> None:
    settings = get_outreach_settings()
    output_dir = Path(args.out)
    queue_path = output_dir / "outreach_queue.json"

    # Single-message operations
    if args.approve_id:
        result = approve_message(queue_path, args.approve_id, args.notes)
        print(json.dumps(result, indent=2))
        return
    if args.reject_id:
        result = reject_message(queue_path, args.reject_id, args.notes)
        print(json.dumps(result, indent=2))
        return

    summary = run_outreach(
        drafts_path=Path(args.drafts),
        settings=settings,
        output_dir=output_dir,
        action=args.action,
        auto_approve_above=args.approve_above,
        max_sends=args.max_sends,
    )

    print("\nOutreach agent finished")
    print(json.dumps(summary, indent=2))
    print("\nSafety note: messages are never auto-sent without explicit --action send.")
