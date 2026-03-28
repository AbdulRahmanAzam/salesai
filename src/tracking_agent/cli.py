from __future__ import annotations

import argparse
import json
from pathlib import Path

from tracking_agent.config import get_tracking_settings
from tracking_agent.pipeline import (
    approve_follow_up,
    reject_follow_up,
    run_tracking,
)


from event_emitter import make_callback


def add_tracking_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "tracking",
        help="Run the tracking agent to monitor responses, analyse sentiment, and generate follow-ups.",
    )
    parser.add_argument(
        "--queue",
        required=True,
        help="Path to outreach_queue.json from the outreach agent.",
    )
    parser.add_argument(
        "--out",
        default="output/tracking",
        help="Output directory for tracking entries, follow-ups, and logs.",
    )
    parser.add_argument(
        "--action",
        choices=["check", "analyze", "follow-up", "send", "status"],
        default="check",
        help=(
            "Action: 'check' polls IMAP for responses, 'analyze' re-classifies existing responses, "
            "'follow-up' generates follow-up drafts, 'send' sends approved follow-ups, "
            "'status' reports tracking state."
        ),
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Only check emails since this date (IMAP format: '01-Jan-2026').",
    )
    parser.add_argument(
        "--auto-follow-up",
        action="store_true",
        default=False,
        help="Auto-approve follow-ups for warm/hot leads.",
    )
    parser.add_argument(
        "--product-name",
        type=str,
        default="",
        help="Product name for follow-up context.",
    )
    parser.add_argument(
        "--product-pitch",
        type=str,
        default="",
        help="Product pitch for follow-up context.",
    )
    parser.add_argument(
        "--json-events",
        action="store_true",
        help="Emit JSON-line progress events to stderr (for server integration).",
    )
    # Single follow-up operations
    parser.add_argument(
        "--approve-id",
        type=str,
        default=None,
        help="Approve a single follow-up by ID.",
    )
    parser.add_argument(
        "--reject-id",
        type=str,
        default=None,
        help="Reject a single follow-up by ID.",
    )


def run_tracking_command(args: argparse.Namespace) -> None:
    settings = get_tracking_settings()
    output_dir = Path(args.out)
    follow_ups_path = output_dir / "tracking_follow_ups.json"

    # Single follow-up operations
    if args.approve_id:
        result = approve_follow_up(follow_ups_path, args.approve_id)
        print(json.dumps(result, indent=2))
        return
    if args.reject_id:
        result = reject_follow_up(follow_ups_path, args.reject_id)
        print(json.dumps(result, indent=2))
        return

    summary = run_tracking(
        queue_path=Path(args.queue),
        settings=settings,
        output_dir=output_dir,
        action=args.action,
        since_date=args.since,
        auto_follow_up=args.auto_follow_up,
        product_name=args.product_name,
        product_pitch=args.product_pitch,
        progress=make_callback(getattr(args, "json_events", False)),
    )

    if not getattr(args, "json_events", False):
        print("\nTracking agent finished")
        print(json.dumps(summary, indent=2))
        print("\nFollow-ups are never auto-sent without explicit --action send.")
    else:
        import sys
        sys.stdout.write(json.dumps(summary))
        sys.stdout.flush()
