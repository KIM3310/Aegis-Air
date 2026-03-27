from __future__ import annotations

import json
from pathlib import Path

from aegis_engine.runtime_store import build_runtime_store_summary


def test_runtime_store_summary_counts_all_events_but_limits_recent_window(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store_path = tmp_path / "runtime-events.jsonl"
    store_path.write_text(
        "\n".join(
            [
                json.dumps({"event": "chaos", "timestamp": "2026-03-10T10:00:00Z"}),
                json.dumps({"event": "incident", "timestamp": "2026-03-10T10:05:00Z"}),
                json.dumps({"event": "incident", "timestamp": "2026-03-10T10:10:00Z"}),
                json.dumps({"event": "webhook", "timestamp": "2026-03-10T10:15:00Z"}),
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AEGIS_AIR_RUNTIME_STORE_PATH", str(store_path))

    summary = build_runtime_store_summary(limit=2)

    assert summary["persisted_count"] == 4
    assert summary["event_type_counts"] == {
        "chaos": 1,
        "incident": 2,
        "webhook": 1,
    }
    assert summary["last_event_at"] == "2026-03-10T10:15:00Z"
    assert summary["recent_events"] == [
        {"event": "incident", "timestamp": "2026-03-10T10:10:00Z"},
        {"event": "webhook", "timestamp": "2026-03-10T10:15:00Z"},
    ]
