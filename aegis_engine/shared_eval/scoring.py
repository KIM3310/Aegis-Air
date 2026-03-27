"""Unified scoring logic for replay evaluation.

Provides rubric checks, pass/fail thresholds, and score aggregation
used by both Aegis-Air and AegisOps replay suites.
"""

from __future__ import annotations

from typing import Any

from aegis_engine.shared_eval.schemas import (
    EvalCheck,
    EvalCheckCategory,
    FailureBucket,
    IncidentSeverity,
    ReplayCaseExpectation,
    ReplayCaseResult,
    ReplaySuiteResult,
    ReplaySuiteSummary,
)


# ---------------------------------------------------------------------------
# Pass/fail threshold (configurable per suite)
# ---------------------------------------------------------------------------

DEFAULT_PASS_THRESHOLD_PCT: float = 100.0


def _check(name: str, category: EvalCheckCategory, passed: bool, detail: str = "") -> EvalCheck:
    return EvalCheck(name=name, category=category, passed=passed, detail=detail)


# ---------------------------------------------------------------------------
# Probe-based scoring (Aegis-Air style)
# ---------------------------------------------------------------------------

def score_probe_report(
    expected: ReplayCaseExpectation,
    report: dict[str, Any],
) -> list[EvalCheck]:
    """Score a structured probe report against expected outcomes.

    This mirrors the Aegis-Air _score_report logic but uses the shared
    EvalCheck model.
    """
    checks: list[EvalCheck] = []

    # Severity match
    checks.append(_check(
        "severity_match",
        EvalCheckCategory.SEVERITY_MATCH,
        report.get("severity") == expected.severity.value,
        f"expected={expected.severity.value} actual={report.get('severity')}",
    ))

    # Failure bucket match
    if expected.failure_bucket is not None:
        checks.append(_check(
            "failure_bucket_match",
            EvalCheckCategory.FAILURE_BUCKET_MATCH,
            report.get("failure_bucket") == expected.failure_bucket.value,
            f"expected={expected.failure_bucket.value} actual={report.get('failure_bucket')}",
        ))

    # Searchable text for summary/evidence/action checks
    searchable_summary = " ".join([
        str(report.get("summary", "")),
        str(report.get("primary_hypothesis", "")),
        " ".join(report.get("supporting_evidence", [])),
    ]).lower()
    searchable_actions = " ".join(report.get("immediate_actions", [])).lower()

    # Summary terms
    for term in expected.summary_terms:
        checks.append(_check(
            f"summary:{term}",
            EvalCheckCategory.SUMMARY_KEYWORDS,
            term.lower() in searchable_summary,
            f"term='{term}' in_summary={term.lower() in searchable_summary}",
        ))

    # Evidence terms
    for term in expected.evidence_terms:
        checks.append(_check(
            f"evidence:{term}",
            EvalCheckCategory.EVIDENCE_KEYWORDS,
            term.lower() in searchable_summary,
            f"term='{term}' in_evidence={term.lower() in searchable_summary}",
        ))

    # Action terms
    for term in expected.action_terms:
        checks.append(_check(
            f"action:{term}",
            EvalCheckCategory.ACTION_KEYWORDS,
            term.lower() in searchable_actions,
            f"term='{term}' in_actions={term.lower() in searchable_actions}",
        ))

    return checks


# ---------------------------------------------------------------------------
# Log-based scoring (AegisOps style)
# ---------------------------------------------------------------------------

def _includes_all_terms(haystack: str, terms: list[str]) -> bool:
    target = haystack.strip().lower()
    return all(t.strip().lower() in target for t in terms)


def score_log_report(
    expected: ReplayCaseExpectation,
    report: dict[str, Any],
) -> list[EvalCheck]:
    """Score a log-based incident report against expected outcomes.

    This mirrors the AegisOps evaluateIncidentReplayCase logic but uses
    the shared EvalCheck model.
    """
    checks: list[EvalCheck] = []

    # Severity match
    checks.append(_check(
        "severity",
        EvalCheckCategory.SEVERITY_MATCH,
        report.get("severity") == expected.severity.value,
        f"expected={expected.severity.value} actual={report.get('severity')}",
    ))

    title_text = str(report.get("title", "")).strip().lower()
    tags = [str(t).strip().lower() for t in (report.get("tags") or [])]
    root_causes = report.get("rootCauses") or report.get("root_causes") or []
    root_cause_text = " | ".join(str(r).strip().lower() for r in root_causes)
    action_items = report.get("actionItems") or report.get("action_items") or []
    action_text = " | ".join(
        f"{item.get('task', '')} {item.get('owner', '')} {item.get('priority', '')}".strip().lower()
        if isinstance(item, dict) else str(item).strip().lower()
        for item in action_items
    )
    reasoning_text = str(report.get("reasoning", "")).strip().lower()

    # Title keywords
    if expected.title_includes:
        checks.append(_check(
            "title",
            EvalCheckCategory.TITLE_KEYWORDS,
            _includes_all_terms(title_text, expected.title_includes),
            f"expected_keywords={expected.title_includes} actual={report.get('title')}",
        ))

    # Tag coverage
    if expected.tags_include:
        missing = [t for t in expected.tags_include if t.strip().lower() not in tags]
        checks.append(_check(
            "tags",
            EvalCheckCategory.TAG_COVERAGE,
            len(missing) == 0,
            f"missing={missing}" if missing else f"observed={tags}",
        ))

    # Timeline coverage
    if expected.min_timeline_events is not None:
        timeline = report.get("timeline") or []
        checks.append(_check(
            "timeline",
            EvalCheckCategory.TIMELINE_COVERAGE,
            len(timeline) >= expected.min_timeline_events,
            f"expected>={expected.min_timeline_events} actual={len(timeline)}",
        ))

    # Root cause coverage
    if expected.root_cause_includes:
        checks.append(_check(
            "root-causes",
            EvalCheckCategory.ROOT_CAUSE_COVERAGE,
            _includes_all_terms(root_cause_text, expected.root_cause_includes),
            f"expected_keywords={expected.root_cause_includes}",
        ))

    # Actionability
    if expected.action_items_include:
        checks.append(_check(
            "actions",
            EvalCheckCategory.ACTIONABILITY,
            _includes_all_terms(action_text, expected.action_items_include),
            f"expected_keywords={expected.action_items_include}",
        ))

    # Reasoning trace
    if expected.reasoning_sections:
        checks.append(_check(
            "reasoning",
            EvalCheckCategory.REASONING_TRACE,
            _includes_all_terms(reasoning_text, expected.reasoning_sections),
            f"expected_sections={expected.reasoning_sections}",
        ))

    # Confidence range
    if expected.confidence_range is not None:
        confidence = float(report.get("confidenceScore", report.get("confidence", 0)))
        checks.append(_check(
            "confidence",
            EvalCheckCategory.CONFIDENCE_RANGE,
            expected.confidence_range.min <= confidence <= expected.confidence_range.max,
            f"expected={expected.confidence_range.min}-{expected.confidence_range.max} actual={confidence}",
        ))

    return checks


# ---------------------------------------------------------------------------
# Case result builder
# ---------------------------------------------------------------------------

def score_replay_case(
    case_id: str,
    title: str,
    expected: ReplayCaseExpectation,
    report: dict[str, Any],
    *,
    mode: str = "probe",
    pass_threshold_pct: float = DEFAULT_PASS_THRESHOLD_PCT,
) -> ReplayCaseResult:
    """Score a replay case and return a structured result.

    Args:
        case_id: Unique case identifier.
        title: Human-readable case title.
        expected: Expected outcomes from the replay case definition.
        report: The actual report produced by the analysis engine.
        mode: 'probe' for Aegis-Air style, 'log' for AegisOps style.
        pass_threshold_pct: Minimum score percentage to pass (default 100%).

    Returns:
        A ReplayCaseResult with check details and pass/fail status.
    """
    if mode == "log":
        checks = score_log_report(expected, report)
    else:
        checks = score_probe_report(expected, report)

    total = len(checks)
    passed = sum(1 for c in checks if c.passed)
    pct = round((passed / total) * 100, 1) if total > 0 else 0.0

    severity_val = report.get("severity", "UNKNOWN")
    try:
        severity = IncidentSeverity(severity_val)
    except ValueError:
        severity = IncidentSeverity.UNKNOWN

    bucket_val = report.get("failure_bucket")
    bucket = None
    if bucket_val:
        try:
            bucket = FailureBucket(bucket_val)
        except ValueError:
            bucket = None

    return ReplayCaseResult(
        case_id=case_id,
        title=title,
        severity=severity,
        failure_bucket=bucket,
        score_pct=pct,
        passed_checks=passed,
        total_checks=total,
        checks=checks,
        status="pass" if pct >= pass_threshold_pct else "fail",
    )


# ---------------------------------------------------------------------------
# Suite-level aggregation
# ---------------------------------------------------------------------------

def aggregate_suite(
    cases: list[dict[str, Any]],
    runs: list[ReplayCaseResult],
    taxonomy: dict[str, str] | None = None,
) -> ReplaySuiteResult:
    """Aggregate individual case results into a suite-level summary.

    Args:
        cases: Original replay case definitions (need 'expected' key).
        runs: Scored results from score_replay_case.
        taxonomy: Optional failure taxonomy dict for coverage calculation.
    """
    from collections import Counter

    taxonomy = taxonomy or {}
    total_checks = sum(r.total_checks for r in runs)
    passed_checks = sum(r.passed_checks for r in runs)
    score_pct = round((passed_checks / total_checks) * 100, 1) if total_checks else 0.0

    severity_matches = sum(
        1 for case, run in zip(cases, runs)
        if case["expected"].get("severity") == run.severity.value
        or case["expected"].get("severity") == run.severity
    )
    severity_accuracy = round((severity_matches / len(cases)) * 100, 1) if cases else 0.0

    bucket_matches = sum(
        1 for case, run in zip(cases, runs)
        if (
            run.failure_bucket is not None
            and case["expected"].get("failure_bucket") == (
                run.failure_bucket.value if hasattr(run.failure_bucket, "value") else run.failure_bucket
            )
        )
    )
    bucket_accuracy = round((bucket_matches / len(cases)) * 100, 1) if cases else 0.0

    sev_counter = Counter(r.severity.value for r in runs)
    bucket_counter = Counter(r.failure_bucket.value for r in runs if r.failure_bucket)

    taxonomy_coverage = (
        round((len(bucket_counter) / len(taxonomy)) * 100, 1) if taxonomy else 0.0
    )

    return ReplaySuiteResult(
        summary=ReplaySuiteSummary(
            cases=len(runs),
            passed_checks=passed_checks,
            total_checks=total_checks,
            score_pct=score_pct,
            severity_accuracy_pct=severity_accuracy,
            bucket_accuracy_pct=bucket_accuracy,
            taxonomy_coverage_pct=taxonomy_coverage,
        ),
        severity_breakdown=dict(sev_counter),
        bucket_breakdown=dict(bucket_counter),
        failure_taxonomy=taxonomy,
        runs=runs,
    )
