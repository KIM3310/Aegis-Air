from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ENGINE = load_module("aegis_air_engine_main", "aegis_engine/main.py")
STORE_API = load_module("aegis_air_store_main", "app/main.py")


def test_engine_health_and_meta():
    client = TestClient(ENGINE.app)

    health = client.get("/health")
    meta = client.get("/api/meta")

    assert health.status_code == 200
    assert health.json()["service"] == "aegis-air-engine"
    assert health.json()["links"]["meta"] == "/api/meta"
    assert health.json()["diagnostics"]["live_loop_ready"] is True
    assert health.json()["diagnostics"]["replay_eval_ready"] is True
    assert health.json()["ops_contract"]["schema"] == "ops-envelope-v1"
    assert "next_action" in health.json()["diagnostics"]
    assert health.json()["links"]["replay_evals"] == "/api/evals/replays"

    assert meta.status_code == 200
    body = meta.json()
    assert body["service"] == "aegis-air-engine"
    assert body["status"] == "ok"
    assert body["model"] == "phi3"
    assert body["diagnostics"]["llm_mode"] == "local-ollama-with-deterministic-fallback"
    assert "/api/chaos/trigger" in body["routes"]
    assert "/api/evals/replays" in body["routes"]
    assert "/api/incidents/report" in body["routes"]


def test_store_api_health_and_meta():
    client = TestClient(STORE_API.app)

    health = client.get("/health")
    meta = client.get("/meta")

    assert health.status_code == 200
    assert health.json()["service"] == "dummy-ecommerce-api"
    assert health.json()["links"]["metrics"] == "/metrics"
    assert health.json()["diagnostics"]["metrics_ready"] is True
    assert health.json()["ops_contract"]["schema"] == "ops-envelope-v1"

    assert meta.status_code == 200
    body = meta.json()
    assert body["service"] == "dummy-ecommerce-api"
    assert body["status"] == "ok"
    assert body["chaos_profile"]["checkout_error_rate"] == 0.30
    assert body["diagnostics"]["chaos_enabled"] is True
    assert "/api/checkout" in body["routes"]


def test_webhook_returns_structured_report():
    client = TestClient(ENGINE.app)

    response = client.post(
        "/webhook/alert",
        json={
            "service_name": "payments-api",
            "incident_time": "2026-03-07T10:05:00Z",
            "status_code": 401,
            "error_details": "Unauthorized after secret rotation; upstream token validation failed.",
            "metrics": {
                "sample_size": 13,
                "success_count": 9,
                "error_count": 4,
                "error_rate": 0.308,
                "p95_latency_ms": 210,
                "latency_spike_count": 0,
            },
            "probe_observations": [
                {
                    "probe": 2,
                    "outcome": "error",
                    "status_code": 401,
                    "latency_ms": 140,
                    "detail": "token validation failed after secret rotation",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert "rca_report" in body
    assert body["report"]["failure_bucket"] == "auth-regression"
    assert body["report"]["severity"] == "SEV2"
    assert len(body["report"]["immediate_actions"]) == 3


def test_replay_eval_summary():
    client = TestClient(ENGINE.app)

    response = client.get("/api/evals/replays")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["summary"]["cases"] == 4
    assert body["summary"]["total_checks"] == 32
    assert body["summary"]["score_pct"] >= 90.0
    assert body["summary"]["bucket_accuracy_pct"] == 100.0
    assert body["summary"]["taxonomy_coverage_pct"] == 100.0
    assert len(body["runs"]) == 4
    assert "dependency-outage" in body["failure_taxonomy"]


def test_replay_metadata_endpoint():
    client = TestClient(ENGINE.app)

    response = client.get("/api/replays")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert len(body["replays"]) == 4
    assert body["replays"][0]["expected_severity"] == "SEV1"
