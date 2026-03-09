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


def build_runtime_store_summary(limit: int = 25) -> dict[str, Any]:
    target = resolve_runtime_store_path()
    if not target.exists():
        return {
            "enabled": True,
            "path": str(target),
            "persisted_count": 0,
            "recent_events": [],
        }

    lines = [line.strip() for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
    recent_events = []
    for line in lines[-max(1, limit) :]:
        try:
            recent_events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return {
        "enabled": True,
        "path": str(target),
        "persisted_count": len(lines),
        "recent_events": recent_events,
    }
