from __future__ import annotations

import argparse
import json
from pathlib import Path

from prospecting_agent.config import get_settings
from prospecting_agent.models import ICP
from prospecting_agent.pipeline import interpret_and_run, run_prospecting
from event_emitter import make_callback


def add_prospect_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "prospect",
        help="Run the prospecting agent and generate a review queue.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--icp",
        help="Path to ICP JSON file.",
    )
    group.add_argument(
        "--prompt",
        help='Natural language description, e.g. "AI invoice tool for freelancers in the US".',
    )
    parser.add_argument(
        "--out",
        default="output",
        help="Output directory for queue and intermediate artifacts.",
    )
    parser.add_argument(
        "--max-leads",
        type=int,
        default=None,
        help="Optional cap for final number of leads in review queue.",
    )
    parser.add_argument(
        "--no-llm-scoring",
        action="store_true",
        help="Skip LLM-based relevance scoring (use rule-based only).",
    )
    parser.add_argument(
        "--json-events",
        action="store_true",
        help="Emit JSON-line progress events to stderr (for server integration).",
    )


def run_prospect_command(args: argparse.Namespace) -> None:
    settings = get_settings()
    progress = make_callback(getattr(args, "json_events", False))

    if args.prompt:
        summary = interpret_and_run(
            natural_language_input=args.prompt,
            settings=settings,
            output_dir=Path(args.out),
            max_leads=args.max_leads,
            progress=progress,
        )
    else:
        icp_data = json.loads(Path(args.icp).read_text(encoding="utf-8"))
        icp = ICP(**{k: v for k, v in icp_data.items() if k in ICP.__dataclass_fields__})

        summary = run_prospecting(
            icp,
            settings,
            Path(args.out),
            max_leads=args.max_leads,
            use_llm_scoring=not getattr(args, "no_llm_scoring", False),
            progress=progress,
        )

    if not getattr(args, "json_events", False):
        print("\nProspecting finished")
        print(json.dumps(summary, indent=2))
        print("\nSafety note: queue is draft-only and review_required by default.")
    else:
        import sys
        sys.stdout.write(json.dumps(summary))
        sys.stdout.flush()
