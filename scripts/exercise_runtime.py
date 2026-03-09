from __future__ import annotations

import json
import os
import urllib.request


BASE_URL = str(os.getenv("AEGIS_AIR_BASE_URL", "http://127.0.0.1:8001")).rstrip("/")
OPERATOR_TOKEN = str(os.getenv("AEGIS_AIR_OPERATOR_TOKEN", "")).strip()


def request_json(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(f"{BASE_URL}{path}", data=body, method=method)
    request.add_header("Content-Type", "application/json")
    if OPERATOR_TOKEN:
        request.add_header("Authorization", f"Bearer {OPERATOR_TOKEN}")
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
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
    scorecard = request_json("/api/runtime/scorecard")
    print(
        json.dumps(
            {
                "telemetry": scorecard["telemetry"],
                "persistence": scorecard["persistence"],
                "operator_auth": scorecard["operator_auth"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
