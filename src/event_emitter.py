"""Structured JSON-line event emitter for pipeline progress reporting.

Events are written to *stderr* so that stdout remains clean for the final
JSON result.  Each line is a self-contained JSON object:

    {"event": "step",    "index": 0, "status": "running", "label": "Searching..."}
    {"event": "item",    "data": { ... }}
    {"event": "summary", "data": { ... }}
    {"event": "error",   "message": "..."}
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from typing import Any, Callable

ProgressCallback = Callable[[str, dict[str, Any]], None]


def emit_event(event_type: str, data: dict[str, Any] | None = None, **kwargs: Any) -> None:
    """Write a single JSON event line to stderr."""
    payload: dict[str, Any] = {"event": event_type}
    if data is not None:
        payload.update(data)
    payload.update(kwargs)
    line = json.dumps(payload, default=str)
    sys.stderr.write(line + "\n")
    sys.stderr.flush()


def emit_step(index: int, status: str, label: str, **extra: Any) -> None:
    emit_event("step", index=index, status=status, label=label, **extra)


def emit_item(item: dict[str, Any] | object) -> None:
    if hasattr(item, "to_record"):
        item = item.to_record()
    elif hasattr(item, "to_dict"):
        item = item.to_dict()
    elif hasattr(item, "__dataclass_fields__"):
        item = asdict(item)
    emit_event("item", data=item)


def emit_summary(summary: dict[str, Any]) -> None:
    emit_event("summary", data=summary)


def emit_error(message: str) -> None:
    emit_event("error", message=message)


def make_callback(enabled: bool) -> ProgressCallback | None:
    """Return a generic callback that routes through emit_event, or None."""
    if not enabled:
        return None

    def _callback(event_type: str, data: dict[str, Any]) -> None:
        emit_event(event_type, data)

    return _callback
