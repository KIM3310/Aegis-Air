"""Persistent runtime event store for the Aegis-Air engine.

Events are appended to a JSONL file (one JSON object per line) so that
runtime telemetry survives process restarts and can be aggregated across
multiple workers.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from aegis_engine.logging import get_logger

logger = get_logger(__name__)


def resolve_runtime_store_path() -> Path:
    """Resolve the filesystem path for the JSONL runtime event store.

    The path can be overridden via ``AEGIS_AIR_RUNTIME_STORE_PATH``.
    When unset the store defaults to ``.runtime/aegis-air-runtime-events.jsonl``
    relative to the current working directory.

    Returns:
        The resolved :class:`~pathlib.Path` to the store file.
    """
    configured: str = str(os.getenv("AEGIS_AIR_RUNTIME_STORE_PATH", "")).strip()
    if configured:
        return Path(configured).expanduser()
    return Path.cwd() / ".runtime" / "aegis-air-runtime-events.jsonl"


def append_runtime_event(event: dict[str, Any]) -> None:
    """Append a single runtime event to the JSONL store.

    The parent directory is created automatically if it does not exist.

    Args:
        event: A JSON-serializable dict describing the runtime event.
    """
    target: Path = resolve_runtime_store_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("a", encoding="utf-8") as handle:
            handle.write(f"{json.dumps(event)}\n")
        logger.debug(
            "Runtime event persisted",
            extra={"event_type": event.get("event", "unknown")},
        )
    except OSError as exc:
        logger.error(
            "Failed to persist runtime event",
            extra={"error_class": type(exc).__name__},
            exc_info=exc,
        )


def _parse_runtime_event(line: str) -> dict[str, Any] | None:
    """Parse a single JSONL line into a dict.

    Args:
        line: A single line from the JSONL store.

    Returns:
        The parsed dict, or ``None`` if the line is not valid JSON.
    """
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def build_runtime_store_summary(limit: int = 25) -> dict[str, Any]:
    """Build an aggregated summary of persisted runtime events.

    Args:
        limit: Maximum number of recent events to include in the
            ``recent_events`` list.

    Returns:
        A dict with ``enabled``, ``path``, ``persisted_count``,
        ``last_event_at``, ``event_type_counts``, and ``recent_events``
        keys.
    """
    target: Path = resolve_runtime_store_path()
    if not target.exists():
        return {
            "enabled": True,
            "path": str(target),
            "persisted_count": 0,
            "last_event_at": None,
            "event_type_counts": {},
            "recent_events": [],
        }

    lines: list[str] = [
        line.strip()
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    recent_events: list[dict[str, Any]] = [
        event
        for line in lines[-max(1, limit):]
        if (event := _parse_runtime_event(line)) is not None
    ]
    all_events: list[dict[str, Any]] = [
        event
        for line in lines
        if (event := _parse_runtime_event(line)) is not None
    ]

    event_type_counts: dict[str, int] = {}
    last_event_at: str | None = None
    for event in all_events:
        event_type: str = str(event.get("event_type") or event.get("event") or "unknown")
        event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
        at: str | None = event.get("at") or event.get("timestamp")
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
