"""Replay evaluation engine for Aegis-Air incident cases.

Provides deterministic incident classification, structured report generation,
and a replay test suite that validates classification accuracy against known
incident scenarios.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from math import ceil
from typing import Any

from aegis_engine.logging import get_logger
from aegis_engine.shared_eval.schemas import FAILURE_TAXONOMY
from aegis_engine.shared_eval.replay_runner import run_replay_suite as _shared_run_replay_suite

logger = get_logger(__name__)

REPLAY_CASES: list[dict[str, Any]] = [
    {
        "id": "db-connection-loss",
        "title": "Checkout database connection lost",
        "service_name": "checkout-api",
        "incident_time": "2026-03-07T09:00:00Z",
        "status_code": 500,
        "error_details": "Database connection lost to postgres-primary during checkout commit.",
        "metrics": {
            "sample_size": 14,
            "success_count": 8,
            "error_count": 6,
            "error_rate": 0.429,
            "p95_latency_ms": 460,
            "latency_spike_count": 1,
        },
        "probe_observations": [
            {"probe": 3, "outcome": "error", "status_code": 500, "latency_ms": 190, "detail": "database connection lost to postgres-primary"},
            {"probe": 4, "outcome": "error", "status_code": 500, "latency_ms": 205, "detail": "checkout transaction failed after dependency disconnect"},
            {"probe": 5, "outcome": "success", "status_code": 200, "latency_ms": 92, "detail": "one request succeeded after retry"},
        ],
        "expected": {
            "severity": "SEV1",
            "failure_bucket": "dependency-outage",
            "summary_terms": ["dependency", "checkout"],
            "evidence_terms": ["error rate", "connection lost"],
            "action_terms": ["restore database connectivity", "roll back recent dependency changes"],
        },
    },
    {
        "id": "redis-timeout-storm",
        "title": "Redis timeout storm on cart reads",
        "service_name": "cart-api",
        "incident_time": "2026-03-07T09:20:00Z",
        "status_code": 504,
        "error_details": "Redis timeout after 5s while loading cart session state.",
        "metrics": {
            "sample_size": 16,
            "success_count": 11,
            "error_count": 5,
            "error_rate": 0.313,
            "p95_latency_ms": 2840,
            "latency_spike_count": 5,
        },
        "probe_observations": [
            {"probe": 2, "outcome": "latency", "status_code": 200, "latency_ms": 2480, "detail": "cart read stalled on redis timeout"},
            {"probe": 7, "outcome": "error", "status_code": 504, "latency_ms": 5000, "detail": "upstream redis timeout after 5s"},
            {"probe": 9, "outcome": "error", "status_code": 504, "latency_ms": 5000, "detail": "retry also timed out against cache dependency"},
        ],
        "expected": {
            "severity": "SEV1",
            "failure_bucket": "dependency-timeout",
            "summary_terms": ["timeout", "latency"],
            "evidence_terms": ["p95 latency", "redis timeout"],
            "action_terms": ["shed traffic", "inspect the upstream dependency"],
        },
    },
    {
        "id": "checkout-cpu-saturation",
        "title": "Checkout worker CPU saturation",
        "service_name": "checkout-api",
        "incident_time": "2026-03-07T09:40:00Z",
        "status_code": 200,
        "error_details": "CPU saturation observed on checkout workers; requests complete but breach latency SLOs.",
        "metrics": {
            "sample_size": 18,
            "success_count": 17,
            "error_count": 1,
            "error_rate": 0.056,
            "p95_latency_ms": 3410,
            "latency_spike_count": 8,
        },
        "probe_observations": [
            {"probe": 1, "outcome": "latency", "status_code": 200, "latency_ms": 2860, "detail": "worker queueing increased during peak traffic"},
            {"probe": 6, "outcome": "latency", "status_code": 200, "latency_ms": 3325, "detail": "requests remain successful but exceed latency SLO"},
            {"probe": 8, "outcome": "success", "status_code": 200, "latency_ms": 210, "detail": "small subset remains healthy"},
        ],
        "expected": {
            "severity": "SEV2",
            "failure_bucket": "latency-saturation",
            "summary_terms": ["latency", "saturation"],
            "evidence_terms": ["p95 latency", "latency spikes"],
            "action_terms": ["reduce concurrency", "scale the worker pool"],
        },
    },
    {
        "id": "secret-rotation-auth-drift",
        "title": "Secret rotation caused auth drift",
        "service_name": "payments-api",
        "incident_time": "2026-03-07T10:05:00Z",
        "status_code": 401,
        "error_details": "Unauthorized after secret rotation; upstream token validation failed for payment capture.",
        "metrics": {
            "sample_size": 13,
            "success_count": 9,
            "error_count": 4,
            "error_rate": 0.308,
            "p95_latency_ms": 210,
            "latency_spike_count": 0,
        },
        "probe_observations": [
            {"probe": 2, "outcome": "error", "status_code": 401, "latency_ms": 140, "detail": "token validation failed after secret rotation"},
            {"probe": 4, "outcome": "error", "status_code": 403, "latency_ms": 155, "detail": "payment capture rejected due to credential drift"},
            {"probe": 7, "outcome": "success", "status_code": 200, "latency_ms": 88, "detail": "older worker still had valid cached credential"},
        ],
        "expected": {
            "severity": "SEV2",
            "failure_bucket": "auth-regression",
            "summary_terms": ["auth", "secret"],
            "evidence_terms": ["unauthorized", "credential drift"],
            "action_terms": ["validate the rotated secret", "roll back the last auth change"],
        },
    },
]


def _contains_any(text: str, candidates: tuple[str, ...]) -> bool:
    """Check whether *text* contains any of the *candidates*.

    Args:
        text: The haystack string to search.
        candidates: Tuple of substrings to look for.

    Returns:
        ``True`` if at least one candidate is found in *text*.
    """
    return any(candidate in text for candidate in candidates)


def _to_float(value: Any, default: float = 0.0) -> float:
    """Safely convert *value* to a float.

    Args:
        value: The value to convert.
        default: Fallback if conversion fails.

    Returns:
        The converted float, or *default* on failure.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    """Safely convert *value* to an int.

    Args:
        value: The value to convert.
        default: Fallback if conversion fails.

    Returns:
        The converted int, or *default* on failure.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _percentile(values: list[int], ratio: float) -> int:
    """Compute a percentile from a sorted list of integers.

    Args:
        values: List of integer measurements (need not be sorted).
        ratio: Percentile ratio in ``[0, 1]`` (e.g. ``0.95`` for p95).

    Returns:
        The value at the given percentile, or ``0`` if *values* is empty.
    """
    if not values:
        return 0
    ordered: list[int] = sorted(values)
    index: int = max(0, min(len(ordered) - 1, ceil(len(ordered) * ratio) - 1))
    return ordered[index]


def _build_metrics_snapshot(
    raw_metrics: dict[str, Any] | None,
    probe_observations: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Build a normalized metrics snapshot from raw data and probe observations.

    Fills in missing values by computing them from probe observations when
    the raw metrics dict does not supply them.

    Args:
        raw_metrics: Optional dict of pre-aggregated metrics.
        probe_observations: Optional list of probe observation dicts.

    Returns:
        A dict with ``sample_size``, ``success_count``, ``error_count``,
        ``error_rate``, ``p95_latency_ms``, and ``latency_spike_count``.
    """
    raw_metrics = raw_metrics or {}
    probe_observations = probe_observations or []
    latencies: list[int] = [
        _to_int(item.get("latency_ms"))
        for item in probe_observations
        if _to_int(item.get("latency_ms")) > 0
    ]
    success_count: int = sum(
        1 for item in probe_observations
        if _to_int(item.get("status_code"), 200) < 400 and item.get("outcome") != "error"
    )
    error_count: int = sum(
        1 for item in probe_observations
        if _to_int(item.get("status_code")) >= 400 or item.get("outcome") == "error"
    )
    latency_spike_count: int = sum(
        1
        for item in probe_observations
        if _to_int(item.get("latency_ms")) >= 1000 or item.get("outcome") == "latency"
    )
    sample_size: int = len(probe_observations)
    computed_error_rate: float = round(error_count / sample_size, 3) if sample_size else 0.0

    metrics: dict[str, Any] = {
        "sample_size": _to_int(raw_metrics.get("sample_size"), sample_size),
        "success_count": _to_int(raw_metrics.get("success_count"), success_count),
        "error_count": _to_int(raw_metrics.get("error_count"), error_count),
        "error_rate": round(_to_float(raw_metrics.get("error_rate"), computed_error_rate), 3),
        "p95_latency_ms": _to_int(raw_metrics.get("p95_latency_ms"), _percentile(latencies, 0.95)),
        "latency_spike_count": _to_int(raw_metrics.get("latency_spike_count"), latency_spike_count),
    }

    if metrics["sample_size"] == 0:
        metrics["sample_size"] = metrics["success_count"] + metrics["error_count"]
    if metrics["error_count"] == 0 and metrics["sample_size"] > 0 and metrics["error_rate"] > 0:
        metrics["error_count"] = round(metrics["sample_size"] * metrics["error_rate"])
    if metrics["success_count"] == 0 and metrics["sample_size"] > metrics["error_count"]:
        metrics["success_count"] = metrics["sample_size"] - metrics["error_count"]
    if metrics["error_rate"] == 0 and metrics["sample_size"] > 0:
        metrics["error_rate"] = round(metrics["error_count"] / metrics["sample_size"], 3)
    return metrics


def _classify_failure_bucket(
    status_code: int,
    error_details: str,
    metrics: dict[str, Any],
    probe_observations: list[dict[str, Any]],
) -> str:
    """Classify the incident into a failure bucket using deterministic rules.

    The classifier inspects error text, probe details, and metrics to assign
    a failure bucket from the shared taxonomy.

    Args:
        status_code: The HTTP status code of the lead observation.
        error_details: Free-text error description.
        metrics: Normalized metrics snapshot.
        probe_observations: List of probe observation dicts.

    Returns:
        A failure bucket string from the shared taxonomy.
    """
    text: str = " ".join(
        [
            str(error_details or ""),
            " ".join(str(item.get("detail", "")) for item in probe_observations),
        ]
    ).lower()

    if _contains_any(text, ("unauthorized", "forbidden", "invalid token", "expired secret", "credential drift", "secret rotation", "token validation")):
        return "auth-regression"
    if _contains_any(text, ("timeout", "timed out", "deadline exceeded")):
        return "dependency-timeout"
    if _contains_any(text, ("connection refused", "connection lost", "database", "postgres", "redis unavailable", "upstream unavailable", "dependency disconnect")):
        return "dependency-outage"
    if metrics["p95_latency_ms"] >= 1800 or metrics["latency_spike_count"] >= 3:
        return "latency-saturation"
    if status_code >= 500:
        return "dependency-outage"
    return "latency-saturation"


def _classify_severity(
    status_code: int,
    failure_bucket: str,
    metrics: dict[str, Any],
) -> str:
    """Classify the incident severity based on the failure bucket and metrics.

    Args:
        status_code: The HTTP status code.
        failure_bucket: The classified failure bucket.
        metrics: Normalized metrics snapshot.

    Returns:
        A severity string (``SEV1``, ``SEV2``, or ``SEV3``).
    """
    error_rate: float = _to_float(metrics.get("error_rate"))
    p95_latency_ms: int = _to_int(metrics.get("p95_latency_ms"))
    if failure_bucket in {"dependency-outage", "dependency-timeout"} and (status_code >= 500 or error_rate >= 0.25):
        return "SEV1"
    if failure_bucket == "auth-regression" and error_rate >= 0.2:
        return "SEV2"
    if failure_bucket == "latency-saturation" and p95_latency_ms >= 2000:
        return "SEV2"
    return "SEV3"


def _build_confidence(
    failure_bucket: str,
    metrics: dict[str, Any],
    probe_observations: list[dict[str, Any]],
) -> float:
    """Compute a confidence score for the incident classification.

    The score starts at a base value and is adjusted upward based on
    evidence quality signals such as sample size, error count, and
    probe detail availability.

    Args:
        failure_bucket: The classified failure bucket.
        metrics: Normalized metrics snapshot.
        probe_observations: List of probe observation dicts.

    Returns:
        A confidence score in ``[0.58, 0.94]``.
    """
    confidence: float = 0.58
    if metrics["sample_size"] >= 10:
        confidence += 0.08
    if metrics["error_count"] > 0:
        confidence += 0.08
    if metrics["latency_spike_count"] >= 3:
        confidence += 0.06
    if failure_bucket in {"dependency-outage", "dependency-timeout", "auth-regression"}:
        confidence += 0.08
    if any(item.get("detail") for item in probe_observations):
        confidence += 0.04
    return round(min(confidence, 0.94), 2)


def _bucket_summary(service_name: str, failure_bucket: str, metrics: dict[str, Any]) -> str:
    """Generate a human-readable summary sentence for the given failure bucket.

    Args:
        service_name: Name of the affected service.
        failure_bucket: The classified failure bucket.
        metrics: Normalized metrics snapshot.

    Returns:
        A prose summary of the incident.
    """
    error_rate_pct: float = round(_to_float(metrics["error_rate"]) * 100, 1)
    p95_latency_ms: int = _to_int(metrics["p95_latency_ms"])
    sample_size: int = _to_int(metrics["sample_size"])
    label: str = service_name.replace("-", " ")

    if failure_bucket == "dependency-outage":
        return (
            f"{label} is failing because a required dependency is unavailable, causing a {error_rate_pct}% "
            f"error rate across {sample_size} probes."
        )
    if failure_bucket == "dependency-timeout":
        return (
            f"{label} is timing out on an upstream dependency; p95 latency reached {p95_latency_ms} ms "
            f"while request failures climbed to {error_rate_pct}%."
        )
    if failure_bucket == "latency-saturation":
        return (
            f"{label} remains reachable, but saturation is pushing p95 latency to {p95_latency_ms} ms "
            f"and repeatedly breaching the latency budget."
        )
    return (
        f"{label} is rejecting traffic after an auth or secret change, with {error_rate_pct}% of probes "
        f"failing immediately."
    )


def _build_primary_hypothesis(failure_bucket: str) -> str:
    """Return the primary hypothesis for the given failure bucket.

    Args:
        failure_bucket: The classified failure bucket.

    Returns:
        A single-sentence hypothesis explaining the root cause.
    """
    mapping: dict[str, str] = {
        "dependency-outage": "A hard dependency outage is breaking request completion on the critical path.",
        "dependency-timeout": "The critical path is blocked by a slow or overloaded upstream dependency.",
        "latency-saturation": "The service is saturated and needs load shedding or capacity relief more than code rollback.",
        "auth-regression": "A recent secret or policy change introduced credential drift between callers and the target service.",
    }
    return mapping[failure_bucket]


def _build_supporting_evidence(
    failure_bucket: str,
    error_details: str,
    metrics: dict[str, Any],
    probe_observations: list[dict[str, Any]],
) -> list[str]:
    """Build a list of supporting evidence statements.

    Args:
        failure_bucket: The classified failure bucket.
        error_details: Free-text error description.
        metrics: Normalized metrics snapshot.
        probe_observations: List of probe observation dicts.

    Returns:
        Up to four evidence strings.
    """
    evidence: list[str] = [
        f"Observed error rate: {round(_to_float(metrics['error_rate']) * 100, 1)}% across {metrics['sample_size']} probes.",
        f"Observed p95 latency: {metrics['p95_latency_ms']} ms with {metrics['latency_spike_count']} latency spikes.",
    ]

    detail_text: str = error_details.strip()
    if detail_text:
        evidence.append(f"Representative failure: {detail_text}")

    detailed_probe: dict[str, Any] | None = next(
        (item for item in probe_observations if item.get("detail")), None
    )
    if detailed_probe:
        evidence.append(f"Probe evidence: {detailed_probe['detail']}")

    if failure_bucket == "auth-regression":
        evidence.append("Failures are immediate authorization denials rather than slow degradations.")

    return evidence[:4]


def _build_counter_signals(metrics: dict[str, Any]) -> list[str]:
    """Build counter-signal statements that qualify the incident.

    Args:
        metrics: Normalized metrics snapshot.

    Returns:
        Up to two counter-signal strings.
    """
    signals: list[str] = []
    if metrics["success_count"] > 0:
        signals.append(f"{metrics['success_count']} probes still succeeded, so the outage is partial rather than total.")
    if metrics["error_rate"] < 0.2:
        signals.append("Failure rate is not yet overwhelming; confirm blast radius before a global rollback.")
    return signals[:2]


def _build_actions(failure_bucket: str) -> list[str]:
    """Return recommended immediate actions for the given failure bucket.

    Args:
        failure_bucket: The classified failure bucket.

    Returns:
        A list of three actionable recommendations.
    """
    mapping: dict[str, list[str]] = {
        "dependency-outage": [
            "Restore database connectivity or fail traffic over to a healthy dependency replica.",
            "Roll back recent dependency changes before widening blast radius.",
            "Throttle or queue new checkout attempts until the dependency recovers.",
        ],
        "dependency-timeout": [
            "Shed traffic on the slow path and inspect the upstream dependency for queue growth or timeouts.",
            "Increase timeout visibility before increasing timeout budgets blindly.",
            "Route around the degraded cache or dependency if a safe bypass exists.",
        ],
        "latency-saturation": [
            "Reduce concurrency on the hot path and disable non-critical synchronous work.",
            "Scale the worker pool or cache tier that is backing up under load.",
            "Inspect the hottest query or handler before restarting healthy capacity.",
        ],
        "auth-regression": [
            "Validate the rotated secret or token issuer against the active runtime configuration.",
            "Roll back the last auth change if a clean reissue path is not immediately available.",
            "Expire stale workers so every instance picks up the same credential set.",
        ],
    }
    return mapping[failure_bucket]


def _build_operator_questions(failure_bucket: str) -> list[str]:
    """Return operator investigation questions for the given failure bucket.

    Args:
        failure_bucket: The classified failure bucket.

    Returns:
        A list of two investigation questions.
    """
    mapping: dict[str, list[str]] = {
        "dependency-outage": [
            "Did a database or network change precede the first failing probe?",
            "Are adjacent services failing against the same dependency?",
        ],
        "dependency-timeout": [
            "Is the upstream dependency saturated or simply unavailable from this service?",
            "Did retry amplification begin before the latency spike worsened?",
        ],
        "latency-saturation": [
            "Which endpoint or query started consuming the extra capacity?",
            "Can traffic be shifted or load-shed without breaking revenue-critical flows?",
        ],
        "auth-regression": [
            "Which deployment or secret rotation changed the credential contract?",
            "Are any workers still healthy because they retained an older secret set?",
        ],
    }
    return mapping[failure_bucket]


def _build_timeline(
    incident_time: str,
    metrics: dict[str, Any],
    failure_bucket: str,
) -> list[dict[str, str]]:
    """Build a three-phase incident timeline.

    Args:
        incident_time: ISO-formatted timestamp of the incident.
        metrics: Normalized metrics snapshot.
        failure_bucket: The classified failure bucket.

    Returns:
        A list of timeline phase dicts with ``phase`` and ``detail`` keys.
    """
    return [
        {
            "phase": "Detect",
            "detail": f"{incident_time}: elevated failure signals observed across {metrics['sample_size']} probes.",
        },
        {
            "phase": "Scope",
            "detail": f"Current bucket is {failure_bucket} with p95 latency {metrics['p95_latency_ms']} ms.",
        },
        {
            "phase": "Act",
            "detail": _build_actions(failure_bucket)[0],
        },
    ]


def format_report_text(report: dict[str, Any]) -> str:
    """Format a structured report dict as human-readable text.

    Args:
        report: A structured incident report dict.

    Returns:
        A multi-line text representation of the report.
    """
    evidence: str = "\n".join(f"- {item}" for item in report["supporting_evidence"])
    actions: str = "\n".join(f"- {item}" for item in report["immediate_actions"])
    return (
        f"[Summary] {report['summary']}\n"
        f"[Severity] {report['severity']} | [Bucket] {report['failure_bucket']} | [Confidence] {report['confidence']}\n"
        f"[Primary Hypothesis] {report['primary_hypothesis']}\n"
        f"[Supporting Evidence]\n{evidence}\n"
        f"[Immediate Actions]\n{actions}"
    )


def build_structured_report(payload: dict[str, Any]) -> dict[str, Any]:
    """Build a complete structured incident report from an alert payload.

    This is the core analysis function that takes raw incident data and
    produces a deterministic, schema-backed report with severity
    classification, failure bucket assignment, confidence scoring, and
    operator-ready actions.

    Args:
        payload: An alert payload dict with ``service_name``, ``status_code``,
            ``error_details``, ``incident_time``, and optional ``metrics``
            and ``probe_observations``.

    Returns:
        A fully populated incident report dict.
    """
    probe_observations: list[dict[str, Any]] = deepcopy(payload.get("probe_observations") or [])
    metrics: dict[str, Any] = _build_metrics_snapshot(payload.get("metrics"), probe_observations)
    status_code: int = _to_int(payload.get("status_code"), 500)
    error_details: str = str(payload.get("error_details", "")).strip()
    service_name: str = str(payload.get("service_name", "unknown-service")).strip() or "unknown-service"
    incident_time: str = str(payload.get("incident_time", "unknown-time"))

    failure_bucket: str = _classify_failure_bucket(status_code, error_details, metrics, probe_observations)
    severity: str = _classify_severity(status_code, failure_bucket, metrics)
    confidence: float = _build_confidence(failure_bucket, metrics, probe_observations)

    logger.info(
        "Incident classified",
        extra={
            "incident_id": f"{service_name}-{failure_bucket}",
            "service_name": service_name,
            "severity": severity,
            "failure_bucket": failure_bucket,
            "confidence": confidence,
            "status_code": status_code,
        },
    )

    report: dict[str, Any] = {
        "incident_id": f"{service_name}-{failure_bucket}",
        "service_name": service_name,
        "incident_time": incident_time,
        "status_code": status_code,
        "severity": severity,
        "failure_bucket": failure_bucket,
        "confidence": confidence,
        "summary": _bucket_summary(service_name, failure_bucket, metrics),
        "primary_hypothesis": _build_primary_hypothesis(failure_bucket),
        "supporting_evidence": _build_supporting_evidence(failure_bucket, error_details, metrics, probe_observations),
        "counter_signals": _build_counter_signals(metrics),
        "immediate_actions": _build_actions(failure_bucket),
        "operator_questions": _build_operator_questions(failure_bucket),
        "timeline": _build_timeline(incident_time, metrics, failure_bucket),
        "metrics": metrics,
        "probe_observations": probe_observations,
        "narrative_source": "deterministic-local",
    }
    report["rca_report"] = format_report_text(report)
    return report


def _score_report(case: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    """Score a report against its replay case expectations.

    Args:
        case: The replay case dict with an ``expected`` key.
        report: The generated structured report to evaluate.

    Returns:
        A scored result dict with checks, scores, and pass counts.
    """
    expected: dict[str, Any] = case["expected"]
    searchable_summary: str = " ".join(
        [
            report["summary"],
            report["primary_hypothesis"],
            " ".join(report["supporting_evidence"]),
        ]
    ).lower()
    searchable_actions: str = " ".join(report["immediate_actions"]).lower()

    checks: list[dict[str, Any]] = [
        {"name": "severity_match", "passed": report["severity"] == expected["severity"]},
        {"name": "failure_bucket_match", "passed": report["failure_bucket"] == expected["failure_bucket"]},
        {"name": f"summary:{expected['summary_terms'][0]}", "passed": expected["summary_terms"][0] in searchable_summary},
        {"name": f"summary:{expected['summary_terms'][1]}", "passed": expected["summary_terms"][1] in searchable_summary},
        {"name": f"evidence:{expected['evidence_terms'][0]}", "passed": expected["evidence_terms"][0] in searchable_summary},
        {"name": f"evidence:{expected['evidence_terms'][1]}", "passed": expected["evidence_terms"][1] in searchable_summary},
        {"name": f"action:{expected['action_terms'][0]}", "passed": expected["action_terms"][0] in searchable_actions},
        {"name": f"action:{expected['action_terms'][1]}", "passed": expected["action_terms"][1] in searchable_actions},
    ]

    passed_checks: int = sum(1 for item in checks if item["passed"])
    total_checks: int = len(checks)
    return {
        "case_id": case["id"],
        "title": case["title"],
        "severity": report["severity"],
        "failure_bucket": report["failure_bucket"],
        "score_pct": round((passed_checks / total_checks) * 100, 1),
        "passed_checks": passed_checks,
        "total_checks": total_checks,
        "checks": checks,
        "report": {
            "summary": report["summary"],
            "primary_hypothesis": report["primary_hypothesis"],
            "confidence": report["confidence"],
            "immediate_actions": report["immediate_actions"][:2],
        },
    }


def build_replay_metadata() -> list[dict[str, Any]]:
    """Build metadata summaries for all replay cases.

    Returns:
        A list of dicts, each containing the case ID, title, service name,
        expected severity and bucket, and key metrics.
    """
    metadata: list[dict[str, Any]] = []
    for case in REPLAY_CASES:
        metrics: dict[str, Any] = case["metrics"]
        metadata.append(
            {
                "id": case["id"],
                "title": case["title"],
                "service_name": case["service_name"],
                "expected_severity": case["expected"]["severity"],
                "expected_failure_bucket": case["expected"]["failure_bucket"],
                "sample_size": metrics["sample_size"],
                "error_rate_pct": round(metrics["error_rate"] * 100, 1),
                "p95_latency_ms": metrics["p95_latency_ms"],
            }
        )
    return metadata


def run_replay_suite() -> dict[str, Any]:
    """Run the full replay evaluation suite against all known cases.

    Executes ``build_structured_report`` on each replay case and scores
    the result against expected outcomes.

    Returns:
        A suite result dict with ``summary``, ``severity_breakdown``,
        ``bucket_breakdown``, ``failure_taxonomy``, and ``runs`` keys.
    """
    runs: list[dict[str, Any]] = []
    passed_checks: int = 0
    total_checks: int = 0
    severities: Counter[str] = Counter()
    buckets: Counter[str] = Counter()

    for case in REPLAY_CASES:
        report: dict[str, Any] = build_structured_report(case)
        scored: dict[str, Any] = _score_report(case, report)
        runs.append(scored)
        passed_checks += scored["passed_checks"]
        total_checks += scored["total_checks"]
        severities[report["severity"]] += 1
        buckets[report["failure_bucket"]] += 1

    score_pct: float = round((passed_checks / total_checks) * 100, 1) if total_checks else 0.0
    severity_accuracy: float = round(
        (
            sum(1 for case, run in zip(REPLAY_CASES, runs) if case["expected"]["severity"] == run["severity"])
            / len(REPLAY_CASES)
        )
        * 100,
        1,
    )
    bucket_accuracy: float = round(
        (
            sum(1 for case, run in zip(REPLAY_CASES, runs) if case["expected"]["failure_bucket"] == run["failure_bucket"])
            / len(REPLAY_CASES)
        )
        * 100,
        1,
    )

    logger.info(
        "Replay suite completed",
        extra={
            "event_type": "replay_suite",
            "incident_id": f"suite-{len(REPLAY_CASES)}-cases",
        },
    )

    return {
        "summary": {
            "cases": len(REPLAY_CASES),
            "passed_checks": passed_checks,
            "total_checks": total_checks,
            "score_pct": score_pct,
            "severity_accuracy_pct": severity_accuracy,
            "bucket_accuracy_pct": bucket_accuracy,
            "taxonomy_coverage_pct": round((len(buckets) / len(FAILURE_TAXONOMY)) * 100, 1),
        },
        "severity_breakdown": dict(severities),
        "bucket_breakdown": dict(buckets),
        "failure_taxonomy": FAILURE_TAXONOMY,
        "runs": runs,
    }


def build_replay_summary(
    *,
    min_score_pct: float | None = None,
    failure_bucket: str | None = None,
    severity: str | None = None,
) -> dict[str, Any]:
    """Build a filtered replay summary with spotlight runs and failed-check analysis.

    Args:
        min_score_pct: Minimum score percentage filter (0-100).
        failure_bucket: Failure bucket filter (must be a valid taxonomy key).
        severity: Severity filter (``SEV1``, ``SEV2``, or ``SEV3``).

    Returns:
        A summary dict with ``schema``, ``filters``, ``summary``,
        ``spotlight_runs``, and ``reviewer_notes`` keys.

    Raises:
        ValueError: If *failure_bucket* or *severity* is not a valid value.
    """
    suite: dict[str, Any] = run_replay_suite()
    normalized_bucket: str | None = str(failure_bucket or "").strip().lower() or None
    if normalized_bucket and normalized_bucket not in FAILURE_TAXONOMY:
        raise ValueError("invalid failure_bucket filter")
    normalized_severity: str | None = str(severity or "").strip().upper() or None
    valid_severities: set[str] = {"SEV1", "SEV2", "SEV3"}
    if normalized_severity and normalized_severity not in valid_severities:
        raise ValueError("invalid severity filter")

    normalized_min_score: float | None = None
    if min_score_pct is not None:
        normalized_min_score = max(0.0, min(100.0, float(min_score_pct)))

    runs: list[dict[str, Any]] = list(suite["runs"])
    if normalized_bucket:
        runs = [run for run in runs if run["failure_bucket"] == normalized_bucket]
    if normalized_severity:
        runs = [run for run in runs if run["severity"] == normalized_severity]
    if normalized_min_score is not None:
        runs = [run for run in runs if float(run["score_pct"]) >= normalized_min_score]

    spotlight_runs: list[dict[str, Any]] = sorted(
        runs,
        key=lambda item: (
            float(item["score_pct"]),
            item["passed_checks"] - item["total_checks"],
            str(item["case_id"]),
        ),
    )[:3]
    visible_buckets: Counter[str] = Counter(run["failure_bucket"] for run in runs)
    visible_severities: Counter[str] = Counter(run["severity"] for run in runs)
    top_failed_checks: Counter[str] = Counter(
        check["name"]
        for run in runs
        for check in run["checks"]
        if not check["passed"]
    )

    return {
        "schema": "aegis-air-replay-summary-v1",
        "filters": {
            "min_score_pct": normalized_min_score,
            "failure_bucket": normalized_bucket,
            "severity": normalized_severity,
        },
        "summary": {
            "visible_runs": len(runs),
            "total_runs": len(suite["runs"]),
            "avg_score_pct": round(
                sum(float(run["score_pct"]) for run in runs) / len(runs), 1
            )
            if runs
            else 0.0,
            "bucket_breakdown": dict(visible_buckets),
            "severity_breakdown": dict(visible_severities),
            "top_failed_checks": [
                {"name": name, "count": count}
                for name, count in top_failed_checks.most_common(5)
            ],
        },
        "spotlight_runs": [
            {
                "case_id": run["case_id"],
                "title": run["title"],
                "failure_bucket": run["failure_bucket"],
                "severity": run["severity"],
                "score_pct": run["score_pct"],
                "failed_checks": [
                    check["name"] for check in run["checks"] if not check["passed"]
                ],
            }
            for run in spotlight_runs
        ],
        "reviewer_notes": [
            "Replay summary keeps the weakest cases visible instead of hiding behind the aggregate score.",
            "Use failure_bucket filters to isolate one RCA class before changing deterministic rules.",
            "Use min_score_pct as a promotion screen, then inspect /api/evals/replays for full run detail.",
        ],
    }


def run_replay_suite_shared() -> dict[str, Any]:
    """Run the replay suite using the shared eval framework.

    Returns the same dict shape as ``run_replay_suite()`` but delegates
    scoring to the ``shared_eval`` module so the taxonomy and rubric
    logic stay in one place.

    Returns:
        A suite result dict compatible with the legacy format.
    """
    result = _shared_run_replay_suite(
        cases=REPLAY_CASES,
        report_builder=build_structured_report,
        mode="probe",
        taxonomy=dict(FAILURE_TAXONOMY),
    )
    # Convert Pydantic model to dict for backward compatibility
    suite_dict: dict[str, Any] = result.model_dump()
    # Restore legacy key names for API compatibility
    for run in suite_dict["runs"]:
        run["case_id"] = run.pop("case_id", run.get("case_id"))
        run["report"] = {
            "summary": "",
            "primary_hypothesis": "",
            "confidence": 0.0,
            "immediate_actions": [],
        }
    return suite_dict


if __name__ == "__main__":
    suite = run_replay_suite()
    summary = suite["summary"]
    print(
        f"Aegis-Air replay suite: {summary['cases']} cases, "
        f"{summary['passed_checks']}/{summary['total_checks']} checks passed, "
        f"{summary['score_pct']}% overall."
    )
