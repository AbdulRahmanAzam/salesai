from __future__ import annotations

import argparse
import json
from pathlib import Path

from prospecting_agent.models import ICP
from research_agent.config import get_research_settings
from research_agent.pipeline import run_research
from event_emitter import make_callback


def add_research_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "research",
        help="Run the research agent on an existing prospect queue.",
    )
    parser.add_argument(
        "--queue",
        required=True,
        help="Path to prospect_queue.json from the prospecting agent.",
    )
    parser.add_argument(
        "--icp",
        required=True,
        help="Path to ICP JSON file (needed for product context in synthesis).",
    )
    parser.add_argument(
        "--out",
        default="output/research",
        help="Output directory for research dossiers.",
    )
    parser.add_argument(
        "--max-research",
        type=int,
        default=None,
        help="Max number of prospects to research.",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=30.0,
        help="Minimum prospect score to research (default 30).",
    )
    parser.add_argument(
        "--json-events",
        action="store_true",
        help="Emit JSON-line progress events to stderr (for server integration).",
    )


def run_research_command(args: argparse.Namespace) -> None:
    icp_data = json.loads(Path(args.icp).read_text(encoding="utf-8"))
    icp = ICP(**icp_data)
    progress = make_callback(getattr(args, "json_events", False))

    summary = run_research(
        prospect_queue_path=Path(args.queue),
        icp=icp,
        settings=get_research_settings(),
        output_dir=Path(args.out),
        max_research=args.max_research,
        min_prospect_score=args.min_score,
        progress=progress,
    )

    if not getattr(args, "json_events", False):
        print("\nResearch finished")
        print(json.dumps(summary, indent=2))
    else:
        import sys
        sys.stdout.write(json.dumps(summary))
        sys.stdout.flush()
