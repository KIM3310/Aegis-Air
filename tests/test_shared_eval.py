"""Tests for the shared eval framework.

Validates that the shared scoring, replay runner, and export work correctly
and produce results compatible with the existing replay_evals module.
"""

from __future__ import annotations

from aegis_engine.shared_eval.schemas import (
    FAILURE_TAXONOMY,
    EvalCheckCategory,
    FailureBucket,
    IncidentSeverity,
    ReplayCaseExpectation,
)
from aegis_engine.shared_eval.scoring import score_replay_case
from aegis_engine.shared_eval.replay_runner import run_replay_suite
from aegis_engine.shared_eval.export import export_all_schemas
from aegis_engine.replay_evals import (
    REPLAY_CASES,
    build_structured_report,
    run_replay_suite as legacy_run_replay_suite,
)


def test_shared_scoring_matches_legacy() -> None:
    """Shared scoring produces the same pass/fail for each case as the legacy scorer."""
    legacy_suite = legacy_run_replay_suite()

    for legacy_run, case in zip(legacy_suite["runs"], REPLAY_CASES):
        expected = ReplayCaseExpectation(**case["expected"])
        report = build_structured_report(case)
        result = score_replay_case(
            case_id=case["id"],
            title=case["title"],
            expected=expected,
            report=report,
            mode="probe",
        )
        # Same number of checks and same pass counts
        assert result.total_checks == legacy_run["total_checks"], (
            f"Case {case['id']}: total_checks {result.total_checks} != {legacy_run['total_checks']}"
        )
        assert result.passed_checks == legacy_run["passed_checks"], (
            f"Case {case['id']}: passed_checks {result.passed_checks} != {legacy_run['passed_checks']}"
        )


def test_shared_suite_runner_produces_valid_result() -> None:
    """Shared replay runner produces a valid ReplaySuiteResult."""
    result = run_replay_suite(
        cases=REPLAY_CASES,
        report_builder=build_structured_report,
        mode="probe",
        taxonomy=dict(FAILURE_TAXONOMY),
    )
    assert result.summary.cases == 4
    assert result.summary.total_checks == 32
    assert result.summary.score_pct >= 90.0
    assert result.summary.severity_accuracy_pct == 100.0
    assert result.summary.bucket_accuracy_pct == 100.0
    assert result.summary.taxonomy_coverage_pct == 100.0
    assert len(result.runs) == 4


def test_shared_suite_runner_matches_legacy_summary() -> None:
    """Shared suite summary matches the legacy suite summary."""
    legacy = legacy_run_replay_suite()
    shared = run_replay_suite(
        cases=REPLAY_CASES,
        report_builder=build_structured_report,
        mode="probe",
        taxonomy=dict(FAILURE_TAXONOMY),
    )
    assert shared.summary.cases == legacy["summary"]["cases"]
    assert shared.summary.score_pct == legacy["summary"]["score_pct"]
    assert shared.summary.severity_accuracy_pct == legacy["summary"]["severity_accuracy_pct"]
    assert shared.summary.bucket_accuracy_pct == legacy["summary"]["bucket_accuracy_pct"]


def test_json_schema_export_is_valid() -> None:
    """JSON Schema export contains all expected definitions."""
    schemas = export_all_schemas()
    assert schemas["version"] == "1.0.0"
    assert "IncidentSeverity" in schemas["definitions"]
    assert "FailureBucket" in schemas["definitions"]
    assert "EvalCheck" in schemas["definitions"]
    assert "ReplayCaseResult" in schemas["definitions"]
    assert schemas["failure_taxonomy"] == FAILURE_TAXONOMY


def test_all_severity_values_covered() -> None:
    """IncidentSeverity enum has the expected members."""
    values = {s.value for s in IncidentSeverity}
    assert values == {"SEV1", "SEV2", "SEV3", "UNKNOWN"}


def test_all_failure_buckets_covered() -> None:
    """FailureBucket enum has the expected members."""
    values = {b.value for b in FailureBucket}
    assert values == {"dependency-outage", "dependency-timeout", "latency-saturation", "auth-regression"}


def test_eval_check_categories_cover_both_styles() -> None:
    """EvalCheckCategory includes categories for both probe and log scoring."""
    values = {c.value for c in EvalCheckCategory}
    # Probe-style categories
    assert "severity_match" in values
    assert "failure_bucket_match" in values
    assert "summary_keywords" in values
    assert "evidence_keywords" in values
    assert "action_keywords" in values
    # Log-style categories
    assert "title_keywords" in values
    assert "tag_coverage" in values
    assert "timeline_coverage" in values
    assert "root_cause_coverage" in values
    assert "actionability" in values
    assert "reasoning_trace" in values
    assert "confidence_range" in values
