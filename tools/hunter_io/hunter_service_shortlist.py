from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


DEFAULT_KEYWORDS = [
    "founder",
    "co-founder",
    "ceo",
    "cto",
    "coo",
    "head",
    "director",
    "marketing",
    "growth",
    "brand",
    "design",
    "product",
    "operations",
    "sales",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a service-fit shortlist from Hunter leads for offers like "
            "website development and logo/branding design."
        )
    )
    parser.add_argument(
        "--in-json",
        type=Path,
        default=Path("output") / "hunter" / "hunter_leads.json",
        help="Input Hunter JSON file (default: output/hunter/hunter_leads.json)",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=Path("output") / "hunter" / "hunter_web_logo_targets.json",
        help="Output shortlist JSON path",
    )
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=Path("output") / "hunter" / "hunter_web_logo_targets.csv",
        help="Output shortlist CSV path",
    )
    parser.add_argument(
        "--title-keyword",
        action="append",
        default=[],
        help="Extra title keyword for inclusion (repeatable)",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=85.0,
        help="Minimum confidence threshold (0-100)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=200,
        help="Maximum shortlisted rows to export",
    )
    return parser.parse_args()


def _read_json(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"Input file does not exist: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit(f"Expected a JSON array in: {path}")
    return data


def _write_json(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _target_role(title: str, keywords: list[str]) -> bool:
    title_l = title.lower()
    return any(k in title_l for k in keywords)


def main() -> None:
    args = parse_args()
    rows = _read_json(args.in_json)

    keywords = sorted(
        set([k.lower().strip() for k in DEFAULT_KEYWORDS + args.title_keyword if k.strip()])
    )

    shortlisted: list[dict] = []
    for row in rows:
        title = str(row.get("position") or "")
        if not title:
            continue

        confidence = _as_float(row.get("confidence"), default=0.0)
        if confidence < max(0.0, min(100.0, args.min_confidence)):
            continue

        if not _target_role(title, keywords):
            continue

        shortlisted.append(row)

    shortlisted.sort(
        key=lambda r: (
            _as_float(r.get("confidence"), default=0.0),
            bool(r.get("email")),
            str(r.get("domain") or ""),
        ),
        reverse=True,
    )

    if args.max_results > 0:
        shortlisted = shortlisted[: args.max_results]

    _write_json(args.out_json, shortlisted)
    _write_csv(args.out_csv, shortlisted)

    print("Done")
    print(f"Input rows: {len(rows)}")
    print(f"Shortlisted rows: {len(shortlisted)}")
    print(f"JSON output: {args.out_json}")
    print(f"CSV output:  {args.out_csv}")


if __name__ == "__main__":
    main()
