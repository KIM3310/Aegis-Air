"""Load runtime events into the Aegis-Air engine and print scorecard.

Submits a configurable number of incident reports and then fetches
the runtime scorecard and drift board to verify persistence.

Usage::

    python scripts/load_runtime.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aegis_engine.main import app  # noqa: E402


ITERATIONS: int = max(1, int(os.getenv("AEGIS_AIR_LOAD_ITERATIONS", "6")))
TOKEN: str = str(os.getenv("AEGIS_AIR_OPERATOR_TOKEN", "")).strip()


def main() -> None:
    """Submit incident reports and print the resulting scorecard."""
    headers: dict[str, str] = {}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    with TestClient(app) as client:
        for index in range(ITERATIONS):
            response = client.post(
                "/api/incidents/report",
                json={
                    "service_name": f"checkout-{index}",
                    "incident_time": "2026-03-09T10:05:00Z",
                    "status_code": 503,
                    "error_details": "Checkout timed out during payment capture.",
                    "metrics": {
                        "sample_size": 8,
                        "success_count": 2,
                        "error_count": 6,
                        "error_rate": 0.75,
                        "p95_latency_ms": 2100,
                        "latency_spike_count": 4,
                    },
                },
                headers=headers,
            )
            response.raise_for_status()

        scorecard = client.get("/api/runtime/scorecard")
        scorecard.raise_for_status()
        drift_board = client.get("/api/replay-drift-board")
        drift_board.raise_for_status()
        body: dict[str, Any] = scorecard.json()

    print(
        json.dumps(
            {
                "schema": body["schema"],
                "telemetry": body["telemetry"],
                "drift_board": drift_board.json()["summary"],
                "persistence": body["persistence"],
                "operator_auth": body["operator_auth"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
