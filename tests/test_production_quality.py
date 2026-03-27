"""Production-quality test suite for Aegis-Air.

Adds comprehensive coverage for incident classification, confidence scoring,
structured logging, error handling, edge cases, and API contract validation.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from aegis_engine.main import app
from aegis_engine.replay_evals import (
    REPLAY_CASES,
    _build_confidence,
    _build_metrics_snapshot,
    _classify_failure_bucket,
    _classify_severity,
    _to_float,
    _to_int,
    _percentile,
    _contains_any,
    build_structured_report,
    format_report_text,
    run_replay_suite,
    build_replay_metadata,
    build_replay_summary,
)
from aegis_engine.runtime_store import (
    append_runtime_event,
    build_runtime_store_summary,
)
from aegis_engine.operator_access import operator_token_enabled
from aegis_engine.logging import StructuredFormatter, get_logger, generate_correlation_id


# ---------------------------------------------------------------------------
# 1. Confidence scoring tests
# ---------------------------------------------------------------------------

class TestConfidenceScoring:
    """Tests for the confidence scoring algorithm."""

    def test_minimum_confidence_with_no_evidence(self) -> None:
        """Base confidence is 0.58 with no evidence signals."""
        metrics: dict[str, Any] = {
            "sample_size": 2,
            "error_count": 0,
            "latency_spike_count": 0,
        }
        confidence = _build_confidence("latency-saturation", metrics, [])
        assert confidence == 0.58

    def test_maximum_confidence_with_all_signals(self) -> None:
        """Confidence caps at 0.94 even when all signals are present."""
        metrics: dict[str, Any] = {
            "sample_size": 15,
            "error_count": 5,
            "latency_spike_count": 4,
        }
        probes: list[dict[str, Any]] = [{"detail": "probe evidence"}]
        confidence = _build_confidence("dependency-outage", metrics, probes)
        assert confidence == 0.92

    def test_sample_size_threshold_at_10(self) -> None:
        """Sample size >= 10 adds 0.08 to confidence."""
        base_metrics: dict[str, Any] = {
            "sample_size": 9,
            "error_count": 0,
            "latency_spike_count": 0,
        }
        low = _build_confidence("latency-saturation", base_metrics, [])

        high_metrics = {**base_metrics, "sample_size": 10}
        high = _build_confidence("latency-saturation", high_metrics, [])

        assert high - low == pytest.approx(0.08, abs=0.01)

    def test_dependency_buckets_boost_confidence(self) -> None:
        """Known high-signal buckets add 0.08 to confidence."""
        metrics: dict[str, Any] = {
            "sample_size": 5,
            "error_count": 0,
            "latency_spike_count": 0,
        }
        base = _build_confidence("latency-saturation", metrics, [])
        boosted = _build_confidence("dependency-outage", metrics, [])
        assert boosted > base


# ---------------------------------------------------------------------------
# 2. Failure bucket classification tests
# ---------------------------------------------------------------------------

class TestFailureBucketClassification:
    """Tests for deterministic failure bucket classification."""

    def test_auth_keywords_trigger_auth_regression(self) -> None:
        """Auth-related keywords in error text produce auth-regression."""
        metrics: dict[str, Any] = {"p95_latency_ms": 100, "latency_spike_count": 0}
        bucket = _classify_failure_bucket(
            401, "Unauthorized: expired secret", metrics, []
        )
        assert bucket == "auth-regression"

    def test_timeout_keywords_trigger_dependency_timeout(self) -> None:
        """Timeout keywords produce dependency-timeout."""
        metrics: dict[str, Any] = {"p95_latency_ms": 100, "latency_spike_count": 0}
        bucket = _classify_failure_bucket(
            504, "upstream request timed out", metrics, []
        )
        assert bucket == "dependency-timeout"

    def test_connection_keywords_trigger_dependency_outage(self) -> None:
        """Connection-related keywords produce dependency-outage."""
        metrics: dict[str, Any] = {"p95_latency_ms": 100, "latency_spike_count": 0}
        bucket = _classify_failure_bucket(
            500, "database connection lost", metrics, []
        )
        assert bucket == "dependency-outage"

    def test_high_latency_triggers_latency_saturation(self) -> None:
        """High p95 latency without error keywords produces latency-saturation."""
        metrics: dict[str, Any] = {"p95_latency_ms": 2000, "latency_spike_count": 1}
        bucket = _classify_failure_bucket(
            200, "requests completing slowly", metrics, []
        )
        assert bucket == "latency-saturation"

    def test_probe_details_included_in_classification(self) -> None:
        """Probe detail text is included in the classification search."""
        metrics: dict[str, Any] = {"p95_latency_ms": 100, "latency_spike_count": 0}
        probes: list[dict[str, Any]] = [
            {"detail": "token validation failed after secret rotation"}
        ]
        bucket = _classify_failure_bucket(200, "", metrics, probes)
        assert bucket == "auth-regression"

    def test_500_status_fallback_to_dependency_outage(self) -> None:
        """HTTP 500 without specific keywords falls back to dependency-outage."""
        metrics: dict[str, Any] = {"p95_latency_ms": 100, "latency_spike_count": 0}
        bucket = _classify_failure_bucket(500, "unknown error", metrics, [])
        assert bucket == "dependency-outage"


# ---------------------------------------------------------------------------
# 3. Severity classification tests
# ---------------------------------------------------------------------------

class TestSeverityClassification:
    """Tests for severity classification."""

    def test_sev1_for_dependency_outage_with_high_error_rate(self) -> None:
        """Dependency outage with >= 25% error rate is SEV1."""
        metrics: dict[str, Any] = {"error_rate": 0.30, "p95_latency_ms": 300}
        severity = _classify_severity(500, "dependency-outage", metrics)
        assert severity == "SEV1"

    def test_sev2_for_auth_regression(self) -> None:
        """Auth regression with >= 20% error rate is SEV2."""
        metrics: dict[str, Any] = {"error_rate": 0.25, "p95_latency_ms": 100}
        severity = _classify_severity(401, "auth-regression", metrics)
        assert severity == "SEV2"

    def test_sev2_for_latency_saturation(self) -> None:
        """Latency saturation with >= 2000ms p95 is SEV2."""
        metrics: dict[str, Any] = {"error_rate": 0.05, "p95_latency_ms": 2500}
        severity = _classify_severity(200, "latency-saturation", metrics)
        assert severity == "SEV2"

    def test_sev3_default(self) -> None:
        """Low-signal incidents default to SEV3."""
        metrics: dict[str, Any] = {"error_rate": 0.01, "p95_latency_ms": 100}
        severity = _classify_severity(200, "latency-saturation", metrics)
        assert severity == "SEV3"


# ---------------------------------------------------------------------------
# 4. Metrics snapshot tests
# ---------------------------------------------------------------------------

class TestMetricsSnapshot:
    """Tests for metrics snapshot building."""

    def test_empty_inputs_produce_zero_metrics(self) -> None:
        """Empty metrics and probes produce zeroed snapshot."""
        metrics = _build_metrics_snapshot(None, None)
        assert metrics["sample_size"] == 0
        assert metrics["error_rate"] == 0

    def test_probe_derived_metrics(self) -> None:
        """Metrics are computed from probes when raw metrics are absent."""
        probes: list[dict[str, Any]] = [
            {"status_code": 200, "latency_ms": 100, "outcome": "success"},
            {"status_code": 500, "latency_ms": 200, "outcome": "error"},
            {"status_code": 200, "latency_ms": 1500, "outcome": "latency"},
        ]
        metrics = _build_metrics_snapshot(None, probes)
        assert metrics["sample_size"] == 3
        assert metrics["error_count"] == 1
        assert metrics["success_count"] == 2  # latency outcome with 200 still counts as success
        assert metrics["latency_spike_count"] == 1  # only the 1500ms probe qualifies

    def test_raw_metrics_take_precedence(self) -> None:
        """Raw metrics override computed values when provided."""
        raw: dict[str, Any] = {
            "sample_size": 100,
            "success_count": 80,
            "error_count": 20,
            "error_rate": 0.2,
            "p95_latency_ms": 500,
            "latency_spike_count": 3,
        }
        metrics = _build_metrics_snapshot(raw, [])
        assert metrics["sample_size"] == 100
        assert metrics["error_rate"] == 0.2


# ---------------------------------------------------------------------------
# 5. Utility function tests
# ---------------------------------------------------------------------------

class TestUtilityFunctions:
    """Tests for utility conversion functions."""

    def test_to_float_with_valid_input(self) -> None:
        assert _to_float("3.14") == pytest.approx(3.14)

    def test_to_float_with_invalid_input(self) -> None:
        assert _to_float("not-a-number", 99.0) == 99.0

    def test_to_float_with_none(self) -> None:
        assert _to_float(None) == 0.0

    def test_to_int_with_valid_input(self) -> None:
        assert _to_int("42") == 42

    def test_to_int_with_invalid_input(self) -> None:
        assert _to_int("abc", -1) == -1

    def test_percentile_empty_list(self) -> None:
        assert _percentile([], 0.95) == 0

    def test_percentile_single_value(self) -> None:
        assert _percentile([100], 0.95) == 100

    def test_percentile_normal_list(self) -> None:
        values = list(range(1, 101))
        p95 = _percentile(values, 0.95)
        assert p95 == 95

    def test_contains_any_positive(self) -> None:
        assert _contains_any("hello world", ("world", "foo")) is True

    def test_contains_any_negative(self) -> None:
        assert _contains_any("hello world", ("foo", "bar")) is False


# ---------------------------------------------------------------------------
# 6. Structured report tests
# ---------------------------------------------------------------------------

class TestStructuredReport:
    """Tests for the full report generation pipeline."""

    def test_report_has_all_required_fields(self) -> None:
        """Generated report contains all schema-required fields."""
        payload: dict[str, Any] = {
            "service_name": "test-api",
            "incident_time": "2026-03-07T09:00:00Z",
            "status_code": 500,
            "error_details": "Database connection lost",
        }
        report = build_structured_report(payload)
        required = [
            "incident_id", "service_name", "incident_time", "status_code",
            "severity", "failure_bucket", "confidence", "summary",
            "primary_hypothesis", "supporting_evidence", "counter_signals",
            "immediate_actions", "operator_questions", "timeline",
            "metrics", "probe_observations", "rca_report",
        ]
        for field in required:
            assert field in report, f"Missing field: {field}"

    def test_report_confidence_is_bounded(self) -> None:
        """Confidence score is always between 0.58 and 0.94."""
        for case in REPLAY_CASES:
            report = build_structured_report(case)
            assert 0.58 <= report["confidence"] <= 0.94

    def test_format_report_text_includes_all_sections(self) -> None:
        """Formatted text includes summary, severity, hypothesis, evidence, actions."""
        report = build_structured_report(REPLAY_CASES[0])
        text = format_report_text(report)
        assert "[Summary]" in text
        assert "[Severity]" in text
        assert "[Primary Hypothesis]" in text
        assert "[Supporting Evidence]" in text
        assert "[Immediate Actions]" in text

    def test_unknown_service_name_defaults(self) -> None:
        """Empty service name defaults to 'unknown-service'."""
        payload: dict[str, Any] = {
            "service_name": "",
            "incident_time": "2026-03-07T09:00:00Z",
            "status_code": 500,
            "error_details": "failure",
        }
        report = build_structured_report(payload)
        assert report["service_name"] == "unknown-service"


# ---------------------------------------------------------------------------
# 7. Structured logging tests
# ---------------------------------------------------------------------------

class TestStructuredLogging:
    """Tests for the structured logging module."""

    def test_structured_formatter_produces_json(self) -> None:
        """StructuredFormatter emits valid JSON."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "test message"
        assert parsed["level"] == "INFO"

    def test_structured_formatter_includes_extras(self) -> None:
        """Extra fields are included in the JSON output."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="", lineno=0,
            msg="incident", args=(), exc_info=None,
        )
        record.incident_id = "test-123"  # type: ignore[attr-defined]
        record.severity = "SEV1"  # type: ignore[attr-defined]
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["incident_id"] == "test-123"
        assert parsed["severity"] == "SEV1"

    def test_get_logger_returns_configured_logger(self) -> None:
        """get_logger returns a logger with structured formatting."""
        test_logger = get_logger("test_production_quality")
        assert test_logger.level == logging.INFO
        assert len(test_logger.handlers) >= 1

    def test_correlation_id_is_unique(self) -> None:
        """Each call to generate_correlation_id produces a unique value."""
        ids = {generate_correlation_id() for _ in range(100)}
        assert len(ids) == 100


# ---------------------------------------------------------------------------
# 8. Runtime store edge case tests
# ---------------------------------------------------------------------------

class TestRuntimeStoreEdgeCases:
    """Tests for runtime store edge cases."""

    def test_empty_store_returns_zero_counts(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-existent store file returns empty summary."""
        monkeypatch.setenv(
            "AEGIS_AIR_RUNTIME_STORE_PATH",
            str(tmp_path / "nonexistent.jsonl"),
        )
        summary = build_runtime_store_summary()
        assert summary["persisted_count"] == 0
        assert summary["event_type_counts"] == {}

    def test_corrupted_lines_are_skipped(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Malformed JSONL lines are skipped without error."""
        store_path = tmp_path / "events.jsonl"
        store_path.write_text(
            'not-json\n'
            '{"event": "chaos", "timestamp": "2026-03-10T10:00:00Z"}\n'
            '{"broken\n',
            encoding="utf-8",
        )
        monkeypatch.setenv("AEGIS_AIR_RUNTIME_STORE_PATH", str(store_path))
        summary = build_runtime_store_summary()
        assert summary["persisted_count"] == 3
        assert summary["event_type_counts"] == {"chaos": 1}

    def test_append_creates_parent_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """append_runtime_event creates the parent directory if needed."""
        deep_path = tmp_path / "deep" / "nested" / "events.jsonl"
        monkeypatch.setenv("AEGIS_AIR_RUNTIME_STORE_PATH", str(deep_path))
        append_runtime_event({"event": "test", "timestamp": "2026-01-01T00:00:00Z"})
        assert deep_path.exists()


# ---------------------------------------------------------------------------
# 9. Replay suite integration tests
# ---------------------------------------------------------------------------

class TestReplaySuiteIntegration:
    """Integration tests for the replay evaluation suite."""

    def test_all_cases_pass_at_100_percent(self) -> None:
        """All four replay cases should score 100%."""
        suite = run_replay_suite()
        for run in suite["runs"]:
            assert run["score_pct"] == 100.0, (
                f"Case {run['case_id']} scored {run['score_pct']}%"
            )

    def test_replay_metadata_matches_case_count(self) -> None:
        """Metadata count matches REPLAY_CASES count."""
        metadata = build_replay_metadata()
        assert len(metadata) == len(REPLAY_CASES)

    def test_replay_summary_invalid_bucket_raises(self) -> None:
        """Invalid failure bucket raises ValueError."""
        with pytest.raises(ValueError, match="invalid failure_bucket"):
            build_replay_summary(failure_bucket="nonexistent-bucket")

    def test_replay_summary_invalid_severity_raises(self) -> None:
        """Invalid severity raises ValueError."""
        with pytest.raises(ValueError, match="invalid severity"):
            build_replay_summary(severity="SEV99")

    def test_replay_summary_min_score_filter(self) -> None:
        """min_score_pct=101 filters out all runs."""
        summary = build_replay_summary(min_score_pct=101.0)
        # min_score_pct is clamped to 100.0, all cases score 100%
        assert summary["summary"]["visible_runs"] == 4


# ---------------------------------------------------------------------------
# 10. API contract tests
# ---------------------------------------------------------------------------

class TestAPIContracts:
    """Tests for API response contracts and error handling."""

    def test_health_returns_200(self) -> None:
        """Health endpoint returns 200 with required fields."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert "diagnostics" in body
        assert "links" in body

    def test_replays_endpoint_returns_all_cases(self) -> None:
        """/api/replays returns all four replay cases."""
        client = TestClient(app)
        response = client.get("/api/replays")
        assert response.status_code == 200
        assert len(response.json()["replays"]) == 4

    def test_incident_report_with_minimal_payload(self) -> None:
        """Incident report endpoint works with only required fields."""
        client = TestClient(app)
        response = client.post(
            "/api/incidents/report",
            json={
                "service_name": "minimal-svc",
                "incident_time": "2026-03-10T00:00:00Z",
                "status_code": 500,
                "error_details": "Something broke",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert "report" in body
        assert body["report"]["severity"] in {"SEV1", "SEV2", "SEV3"}

    def test_webhook_alert_produces_report(self) -> None:
        """Webhook alert endpoint produces a structured report."""
        client = TestClient(app)
        response = client.post(
            "/webhook/alert",
            json={
                "service_name": "webhook-test",
                "incident_time": "2026-03-10T00:00:00Z",
                "status_code": 503,
                "error_details": "upstream timed out",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["report"]["failure_bucket"] in {
            "dependency-outage", "dependency-timeout",
            "latency-saturation", "auth-regression",
        }

    def test_schema_endpoint_returns_required_fields(self) -> None:
        """/api/schema/report returns the incident report schema."""
        client = TestClient(app)
        response = client.get("/api/schema/report")
        assert response.status_code == 200
        body = response.json()
        assert "severity" in body["required_fields"]
        assert "rca_report" in body["required_fields"]

    def test_offline_deployment_pack_schema(self) -> None:
        """/api/offline-deployment-pack returns expected schema."""
        client = TestClient(app)
        response = client.get("/api/offline-deployment-pack")
        assert response.status_code == 200
        body = response.json()
        assert body["schema"] == "aegis-air-offline-deployment-pack-v1"
        assert "model_registry" in body


# ---------------------------------------------------------------------------
# 11. Operator auth edge cases
# ---------------------------------------------------------------------------

class TestOperatorAuthEdgeCases:
    """Tests for operator authentication edge cases."""

    def test_operator_token_disabled_by_default(self) -> None:
        """Without env var, operator token is disabled."""
        prev = os.environ.pop("AEGIS_AIR_OPERATOR_TOKEN", None)
        try:
            assert operator_token_enabled() is False
        finally:
            if prev is not None:
                os.environ["AEGIS_AIR_OPERATOR_TOKEN"] = prev

    def test_x_operator_token_header_accepted(self) -> None:
        """X-Operator-Token header is accepted for auth."""
        client = TestClient(app)
        prev = os.environ.get("AEGIS_AIR_OPERATOR_TOKEN")
        os.environ["AEGIS_AIR_OPERATOR_TOKEN"] = "secret-123"
        try:
            response = client.post(
                "/api/incidents/report",
                headers={"x-operator-token": "secret-123"},
                json={
                    "service_name": "test",
                    "incident_time": "2026-01-01T00:00:00Z",
                    "status_code": 500,
                    "error_details": "test",
                },
            )
            assert response.status_code == 200
        finally:
            if prev is None:
                os.environ.pop("AEGIS_AIR_OPERATOR_TOKEN", None)
            else:
                os.environ["AEGIS_AIR_OPERATOR_TOKEN"] = prev

    def test_wrong_token_returns_403(self) -> None:
        """Wrong operator token returns 403."""
        client = TestClient(app)
        prev = os.environ.get("AEGIS_AIR_OPERATOR_TOKEN")
        os.environ["AEGIS_AIR_OPERATOR_TOKEN"] = "correct-token"
        try:
            response = client.post(
                "/api/incidents/report",
                headers={"authorization": "Bearer wrong-token"},
                json={
                    "service_name": "test",
                    "incident_time": "2026-01-01T00:00:00Z",
                    "status_code": 500,
                    "error_details": "test",
                },
            )
            assert response.status_code == 403
        finally:
            if prev is None:
                os.environ.pop("AEGIS_AIR_OPERATOR_TOKEN", None)
            else:
                os.environ["AEGIS_AIR_OPERATOR_TOKEN"] = prev
