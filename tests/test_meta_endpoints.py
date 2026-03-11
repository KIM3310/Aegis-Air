from __future__ import annotations

import importlib.util
import os
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
    runtime_brief = client.get("/api/runtime/brief")
    runtime_scorecard = client.get("/api/runtime/scorecard")
    command_board = client.get("/api/incident-command-board")
    review_pack = client.get("/api/review-pack")
    replay_summary = client.get("/api/evals/replays/summary")
    schema = client.get("/api/schema/report")

    assert health.status_code == 200
    assert health.json()["service"] == "aegis-air-engine"
    assert health.json()["links"]["meta"] == "/api/meta"
    assert health.json()["links"]["runtime_brief"] == "/api/runtime/brief"
    assert health.json()["links"]["review_pack"] == "/api/review-pack"
    assert health.json()["links"]["incident_command_board"] == "/api/incident-command-board"
    assert health.json()["links"]["report_schema"] == "/api/schema/report"
    assert health.json()["links"]["replay_summary"] == "/api/evals/replays/summary"
    assert health.json()["diagnostics"]["live_loop_ready"] is True
    assert health.json()["diagnostics"]["replay_eval_ready"] is True
    assert "runtime-brief-surface" in health.json()["capabilities"]
    assert "incident-command-board-surface" in health.json()["capabilities"]
    assert "review-pack-surface" in health.json()["capabilities"]
    assert health.json()["ops_contract"]["schema"] == "ops-envelope-v1"
    assert "next_action" in health.json()["diagnostics"]
    assert health.json()["links"]["replay_evals"] == "/api/evals/replays"

    assert meta.status_code == 200
    body = meta.json()
    assert body["service"] == "aegis-air-engine"
    assert body["status"] == "ok"
    assert body["model"] == "phi3"
    assert body["diagnostics"]["llm_mode"] == "local-ollama-with-deterministic-fallback"
    assert body["report_contract"]["schema"] == "aegis-air-incident-report-v1"
    assert "/api/chaos/trigger" in body["routes"]
    assert "/api/evals/replays/summary" in body["routes"]
    assert "/api/evals/replays" in body["routes"]
    assert "/api/incident-command-board" in body["routes"]
    assert "/api/incidents/report" in body["routes"]
    assert "/api/runtime/brief" in body["routes"]
    assert "/api/review-pack" in body["routes"]
    assert "/api/schema/report" in body["routes"]

    assert runtime_brief.status_code == 200
    brief = runtime_brief.json()
    assert brief["service"] == "aegis-air-engine"
    assert brief["readiness_contract"] == "aegis-air-runtime-brief-v1"
    assert brief["report_contract"]["schema"] == "aegis-air-incident-report-v1"
    assert brief["replay_summary"]["cases"] == 4
    assert brief["runtime_telemetry"]["chaos_trigger_runs"] >= 0
    assert any(item["href"] == "/api/evals/replays/summary" for item in brief["proof_assets"])
    assert isinstance(brief["review_flow"], list)
    assert isinstance(brief["target_service"], dict)

    assert runtime_scorecard.status_code == 200
    scorecard = runtime_scorecard.json()
    assert scorecard["schema"] == "aegis-air-runtime-scorecard-v1"
    assert scorecard["links"]["runtime_scorecard"] == "/api/runtime/scorecard"
    assert scorecard["links"]["incident_command_board"] == "/api/incident-command-board"
    assert scorecard["replay_scorecard"]["cases"] == 4
    assert "target_meta_reachable" in scorecard["runtime"]
    assert isinstance(scorecard["telemetry"]["incident_reports"], int)
    assert scorecard["persistence"]["enabled"] is True
    assert "event_type_counts" in scorecard["persistence"]
    assert "protected_routes" in scorecard["operator_auth"]

    assert command_board.status_code == 200
    board = command_board.json()
    assert board["contract_version"] == "aegis-air-incident-command-board-v1"
    assert board["summary"]["visible_runs"] >= 1
    assert board["links"]["incident_command_board"] == "/api/incident-command-board"

    assert review_pack.status_code == 200
    pack = review_pack.json()
    assert pack["readiness_contract"] == "aegis-air-review-pack-v1"
    assert pack["handoff_contract"]["schema"] == "aegis-air-incident-report-v1"
    assert "/api/review-pack" in pack["proof_bundle"]["review_endpoints"]
    assert "/api/incident-command-board" in pack["proof_bundle"]["review_endpoints"]
    assert "/api/runtime/scorecard" in pack["proof_bundle"]["review_endpoints"]
    assert "/api/evals/replays/summary" in pack["proof_bundle"]["review_endpoints"]
    assert isinstance(pack["review_sequence"], list)
    assert len(pack["two_minute_review"]) == 4
    assert pack["proof_assets"][0]["href"] == "/health"
    assert pack["links"]["incident_command_board"] == "/api/incident-command-board"
    assert pack["links"]["replay_summary"] == "/api/evals/replays/summary"

    assert replay_summary.status_code == 200
    replay_summary_body = replay_summary.json()
    assert replay_summary_body["schema"] == "aegis-air-replay-summary-v1"
    assert replay_summary_body["summary"]["visible_runs"] == 4
    assert len(replay_summary_body["spotlight_runs"]) >= 1

    assert schema.status_code == 200
    schema_body = schema.json()
    assert schema_body["schema"] == "aegis-air-incident-report-v1"
    assert "summary" in schema_body["required_fields"]
    assert "live-probe" in schema_body["delivery_modes"]


def test_store_api_health_and_meta():
    client = TestClient(STORE_API.app)

    health = client.get("/health")
    meta = client.get("/meta")

    assert health.status_code == 200
    assert health.json()["service"] == "aegis-air-target-api"
    assert health.json()["links"]["metrics"] == "/metrics"
    assert health.json()["diagnostics"]["metrics_ready"] is True
    assert health.json()["ops_contract"]["schema"] == "ops-envelope-v1"

    assert meta.status_code == 200
    body = meta.json()
    assert body["service"] == "aegis-air-target-api"
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


def test_runtime_scorecard_counts_runtime_events():
    client = TestClient(ENGINE.app)

    report_response = client.post(
        "/api/incidents/report",
        json={
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
    assert report_response.status_code == 200

    scorecard = client.get("/api/runtime/scorecard")
    assert scorecard.status_code == 200
    body = scorecard.json()
    assert body["telemetry"]["incident_reports"] >= 1
    assert body["activity"]["total_runtime_events"] >= 1
    assert body["links"]["review_pack"] == "/api/review-pack"


def test_operator_token_can_guard_mutating_routes():
    client = TestClient(ENGINE.app)
    previous = os.environ.get("AEGIS_AIR_OPERATOR_TOKEN")
    os.environ["AEGIS_AIR_OPERATOR_TOKEN"] = "test-token"
    try:
        denied = client.post(
            "/api/incidents/report",
            json={
                "service_name": "checkout",
                "incident_time": "2026-03-09T10:05:00Z",
                "status_code": 503,
                "error_details": "Checkout timed out during payment capture.",
            },
        )
        assert denied.status_code == 403

        allowed = client.post(
            "/api/incidents/report",
            headers={"authorization": "Bearer test-token"},
            json={
                "service_name": "checkout",
                "incident_time": "2026-03-09T10:05:00Z",
                "status_code": 503,
                "error_details": "Checkout timed out during payment capture.",
            },
        )
        assert allowed.status_code == 200
    finally:
        if previous is None:
            os.environ.pop("AEGIS_AIR_OPERATOR_TOKEN", None)
        else:
            os.environ["AEGIS_AIR_OPERATOR_TOKEN"] = previous


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


def test_replay_eval_review_summary_filters():
    client = TestClient(ENGINE.app)

    response = client.get(
        "/api/evals/replays/summary?failure_bucket=auth-regression&severity=SEV2&min_score_pct=90"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == "aegis-air-replay-summary-v1"
    assert body["filters"]["failure_bucket"] == "auth-regression"
    assert body["filters"]["severity"] == "SEV2"
    assert body["filters"]["min_score_pct"] == 90.0
    assert body["summary"]["visible_runs"] == 1
    assert isinstance(body["summary"]["top_failed_checks"], list)
    assert body["spotlight_runs"][0]["failure_bucket"] == "auth-regression"

    invalid = client.get("/api/evals/replays/summary?failure_bucket=bad-bucket")
    assert invalid.status_code == 400
    invalid_severity = client.get("/api/evals/replays/summary?severity=SEV9")
    assert invalid_severity.status_code == 400


def test_incident_command_board_filters():
    client = TestClient(ENGINE.app)

    response = client.get("/api/incident-command-board?failure_bucket=auth-regression&severity=SEV2")
    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "aegis-air-incident-command-board-v1"
    assert body["summary"]["visible_runs"] == 1
    assert body["items"][0]["failure_bucket"] == "auth-regression"
    assert body["items"][0]["severity"] == "SEV2"

    invalid = client.get("/api/incident-command-board?failure_bucket=bad-bucket")
    assert invalid.status_code == 400


def test_replay_metadata_endpoint():
    client = TestClient(ENGINE.app)

    response = client.get("/api/replays")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert len(body["replays"]) == 4
    assert body["replays"][0]["expected_severity"] == "SEV1"
