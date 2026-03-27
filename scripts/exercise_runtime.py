"""Exercise the Aegis-Air runtime by submitting an incident and fetching dashboards.

Attempts a live HTTP connection first, then falls back to the TestClient
when the engine is not running externally.

Usage::

    python scripts/exercise_runtime.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


BASE_URL: str = str(os.getenv("AEGIS_AIR_BASE_URL", "http://127.0.0.1:8001")).rstrip("/")
OPERATOR_TOKEN: str = str(os.getenv("AEGIS_AIR_OPERATOR_TOKEN", "")).strip()
ROOT: Path = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aegis_engine.main import app  # noqa: E402


def request_json(
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send an HTTP request and return the JSON response.

    Tries a live HTTP call first; falls back to TestClient if unreachable.

    Args:
        path: The API path to call.
        method: HTTP method (default ``GET``).
        payload: Optional JSON body for POST requests.

    Returns:
        The parsed JSON response dict.
    """
    body: bytes | None = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(f"{BASE_URL}{path}", data=body, method=method)
    request.add_header("Content-Type", "application/json")
    if OPERATOR_TOKEN:
        request.add_header("Authorization", f"Bearer {OPERATOR_TOKEN}")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError:
        with TestClient(app) as client:
            resp = client.request(
                method,
                path,
                json=payload,
                headers={
                    "Authorization": f"Bearer {OPERATOR_TOKEN}",
                }
                if OPERATOR_TOKEN
                else None,
            )
            resp.raise_for_status()
            return resp.json()


def main() -> None:
    """Submit an incident, then fetch scorecard and dashboards."""
    request_json(
        "/api/incidents/report",
        method="POST",
        payload={
            "service_name": "checkout",
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
    )
    scorecard: dict[str, Any] = request_json("/api/runtime/scorecard")
    drift_board: dict[str, Any] = request_json("/api/replay-drift-board")
    board: dict[str, Any] = request_json("/api/incident-command-board")
    print(
        json.dumps(
            {
                "telemetry": scorecard["telemetry"],
                "persistence": scorecard["persistence"],
                "operator_auth": scorecard["operator_auth"],
                "replay_drift_board": drift_board["summary"],
                "incident_command_board": board["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
