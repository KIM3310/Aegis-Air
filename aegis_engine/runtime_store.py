from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def resolve_runtime_store_path() -> Path:
    configured = str(os.getenv("AEGIS_AIR_RUNTIME_STORE_PATH", "")).strip()
    if configured:
        return Path(configured).expanduser()
    return Path.cwd() / ".runtime" / "aegis-air-runtime-events.jsonl"


def append_runtime_event(event: dict[str, Any]) -> None:
    target = resolve_runtime_store_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(f"{json.dumps(event)}\n")


def _parse_runtime_event(line: str) -> dict[str, Any] | None:
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def build_runtime_store_summary(limit: int = 25) -> dict[str, Any]:
    target = resolve_runtime_store_path()
    if not target.exists():
        return {
            "enabled": True,
            "path": str(target),
            "persisted_count": 0,
            "last_event_at": None,
            "event_type_counts": {},
            "recent_events": [],
        }

    lines = [line.strip() for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
    recent_events = [
        event
        for line in lines[-max(1, limit) :]
        if (event := _parse_runtime_event(line)) is not None
    ]
    all_events = [
        event
        for line in lines
        if (event := _parse_runtime_event(line)) is not None
    ]

    event_type_counts: dict[str, int] = {}
    last_event_at: str | None = None
    for event in all_events:
        event_type = str(event.get("event_type") or event.get("event") or "unknown")
        event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
        at = event.get("at") or event.get("timestamp")
        if isinstance(at, str) and (last_event_at is None or at > last_event_at):
            last_event_at = at

    return {
        "enabled": True,
        "path": str(target),
        "persisted_count": len(lines),
        "last_event_at": last_event_at,
        "event_type_counts": event_type_counts,
        "recent_events": recent_events,
    }
