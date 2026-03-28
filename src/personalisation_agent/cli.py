from __future__ import annotations

import argparse
import json
from dataclasses import fields as dc_fields
from pathlib import Path

from prospecting_agent.models import ICP
from personalisation_agent.config import get_personalisation_settings
from personalisation_agent.pipeline import run_personalisation
from event_emitter import make_callback

# Aliases the frontend/user might send → canonical ICP field names
_ICP_ALIASES = {
    "product_description": "product_pitch",
    "target_titles": "persona_titles",
    "target_industries": "industries",
    "target_company_size": "employee_ranges",
    "target_geography": "locations",
    "pain_points": "keywords",
    "value_propositions": "keywords",
}


def add_personalise_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "personalise",
        help="Run the personalisation agent to generate outreach drafts from research dossiers.",
    )
    parser.add_argument(
        "--dossiers",
        required=True,
        help="Path to research_dossiers.json from the research agent.",
    )
    parser.add_argument(
        "--icp",
        required=True,
        help="Path to ICP JSON file (needed for product context in drafts).",
    )
    parser.add_argument(
        "--out",
        default="output/personalisation",
        help="Output directory for outreach drafts.",
    )
    parser.add_argument(
        "--max-drafts",
        type=int,
        default=None,
        help="Max number of drafts to generate.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=None,
        help="Minimum research confidence to personalise (default from settings: 0.1).",
    )
    parser.add_argument(
        "--json-events",
        action="store_true",
        help="Emit JSON-line progress events to stderr (for server integration).",
    )


def run_personalise_command(args: argparse.Namespace) -> None:
    icp_data = json.loads(Path(args.icp).read_text(encoding="utf-8"))

    # Normalise aliases so frontend ICP shapes don't crash the dataclass
    valid_fields = {f.name for f in dc_fields(ICP)}
    normalised: dict = {}
    for key, value in icp_data.items():
        canonical = _ICP_ALIASES.get(key, key)
        if canonical in valid_fields:
            # Merge list values for keys that map to the same field
            if canonical in normalised and isinstance(normalised[canonical], list) and isinstance(value, list):
                normalised[canonical] = normalised[canonical] + value
            else:
                normalised[canonical] = value
        # else: silently skip unknown fields

    # Ensure required fields have fallbacks
    normalised.setdefault("product_name", "Unknown Product")
    normalised.setdefault("product_pitch", normalised.get("product_name", ""))

    # Wrap scalar employee_ranges / locations if a plain string was sent
    for list_field in ("employee_ranges", "locations", "industries", "persona_titles",
                       "tech_stack", "keywords", "search_queries", "exclude_domains"):
        val = normalised.get(list_field)
        if isinstance(val, str):
            normalised[list_field] = [val] if val else []

    icp = ICP(**normalised)
    progress = make_callback(getattr(args, "json_events", False))

    summary = run_personalisation(
        dossiers_path=Path(args.dossiers),
        icp=icp,
        settings=get_personalisation_settings(),
        output_dir=Path(args.out),
        max_drafts=args.max_drafts,
        min_confidence=args.min_confidence,
        progress=progress,
    )

    if not getattr(args, "json_events", False):
        print("\nPersonalisation finished")
        print(json.dumps(summary, indent=2))
        print("\nSafety note: all drafts are status=draft and require human review.")
    else:
        import sys
        sys.stdout.write(json.dumps(summary))
        sys.stdout.flush()
