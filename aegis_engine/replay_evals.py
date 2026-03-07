from __future__ import annotations

from collections import Counter
from copy import deepcopy
from math import ceil
from typing import Any

FAILURE_TAXONOMY = {
    "dependency-outage": "Hard dependency unavailable or refusing connections.",
    "dependency-timeout": "Upstream dependency is responding too slowly or timing out.",
    "latency-saturation": "Service remains reachable but is saturated and breaching latency SLOs.",
    "auth-regression": "Credential, secret, or policy drift is rejecting otherwise valid traffic.",
}

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
    return any(candidate in text for candidate in candidates)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _percentile(values: list[int], ratio: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, ceil(len(ordered) * ratio) - 1))
    return ordered[index]


def _build_metrics_snapshot(raw_metrics: dict[str, Any] | None, probe_observations: list[dict[str, Any]]) -> dict[str, Any]:
    raw_metrics = raw_metrics or {}
    latencies = [_to_int(item.get("latency_ms")) for item in probe_observations if _to_int(item.get("latency_ms")) > 0]
    success_count = sum(1 for item in probe_observations if _to_int(item.get("status_code"), 200) < 400 and item.get("outcome") != "error")
    error_count = sum(1 for item in probe_observations if _to_int(item.get("status_code")) >= 400 or item.get("outcome") == "error")
    latency_spike_count = sum(
        1
        for item in probe_observations
        if _to_int(item.get("latency_ms")) >= 1000 or item.get("outcome") == "latency"
    )
    sample_size = len(probe_observations)
    computed_error_rate = round(error_count / sample_size, 3) if sample_size else 0.0

    metrics = {
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


def _classify_failure_bucket(status_code: int, error_details: str, metrics: dict[str, Any], probe_observations: list[dict[str, Any]]) -> str:
    text = " ".join(
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


def _classify_severity(status_code: int, failure_bucket: str, metrics: dict[str, Any]) -> str:
    error_rate = _to_float(metrics.get("error_rate"))
    p95_latency_ms = _to_int(metrics.get("p95_latency_ms"))
    if failure_bucket in {"dependency-outage", "dependency-timeout"} and (status_code >= 500 or error_rate >= 0.25):
        return "SEV1"
    if failure_bucket == "auth-regression" and error_rate >= 0.2:
        return "SEV2"
    if failure_bucket == "latency-saturation" and p95_latency_ms >= 2000:
        return "SEV2"
    return "SEV3"


def _build_confidence(failure_bucket: str, metrics: dict[str, Any], probe_observations: list[dict[str, Any]]) -> float:
    confidence = 0.58
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
    error_rate_pct = round(_to_float(metrics["error_rate"]) * 100, 1)
    p95_latency_ms = _to_int(metrics["p95_latency_ms"])
    sample_size = _to_int(metrics["sample_size"])
    label = service_name.replace("-", " ")

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
    mapping = {
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
    evidence = [
        f"Observed error rate: {round(_to_float(metrics['error_rate']) * 100, 1)}% across {metrics['sample_size']} probes.",
        f"Observed p95 latency: {metrics['p95_latency_ms']} ms with {metrics['latency_spike_count']} latency spikes.",
    ]

    detail_text = error_details.strip()
    if detail_text:
        evidence.append(f"Representative failure: {detail_text}")

    detailed_probe = next((item for item in probe_observations if item.get("detail")), None)
    if detailed_probe:
        evidence.append(f"Probe evidence: {detailed_probe['detail']}")

    if failure_bucket == "auth-regression":
        evidence.append("Failures are immediate authorization denials rather than slow degradations.")

    return evidence[:4]


def _build_counter_signals(metrics: dict[str, Any]) -> list[str]:
    signals: list[str] = []
    if metrics["success_count"] > 0:
        signals.append(f"{metrics['success_count']} probes still succeeded, so the outage is partial rather than total.")
    if metrics["error_rate"] < 0.2:
        signals.append("Failure rate is not yet overwhelming; confirm blast radius before a global rollback.")
    return signals[:2]


def _build_actions(failure_bucket: str) -> list[str]:
    mapping = {
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
    mapping = {
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


def _build_timeline(incident_time: str, metrics: dict[str, Any], failure_bucket: str) -> list[dict[str, str]]:
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
    evidence = "\n".join(f"- {item}" for item in report["supporting_evidence"])
    actions = "\n".join(f"- {item}" for item in report["immediate_actions"])
    return (
        f"[Summary] {report['summary']}\n"
        f"[Severity] {report['severity']} | [Bucket] {report['failure_bucket']} | [Confidence] {report['confidence']}\n"
        f"[Primary Hypothesis] {report['primary_hypothesis']}\n"
        f"[Supporting Evidence]\n{evidence}\n"
        f"[Immediate Actions]\n{actions}"
    )


def build_structured_report(payload: dict[str, Any]) -> dict[str, Any]:
    probe_observations = deepcopy(payload.get("probe_observations", []))
    metrics = _build_metrics_snapshot(payload.get("metrics"), probe_observations)
    status_code = _to_int(payload.get("status_code"), 500)
    error_details = str(payload.get("error_details", "")).strip()
    service_name = str(payload.get("service_name", "unknown-service")).strip() or "unknown-service"
    incident_time = str(payload.get("incident_time", "unknown-time"))

    failure_bucket = _classify_failure_bucket(status_code, error_details, metrics, probe_observations)
    severity = _classify_severity(status_code, failure_bucket, metrics)
    confidence = _build_confidence(failure_bucket, metrics, probe_observations)

    report = {
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
    expected = case["expected"]
    searchable_summary = " ".join(
        [
            report["summary"],
            report["primary_hypothesis"],
            " ".join(report["supporting_evidence"]),
        ]
    ).lower()
    searchable_actions = " ".join(report["immediate_actions"]).lower()

    checks = [
        {"name": "severity_match", "passed": report["severity"] == expected["severity"]},
        {"name": "failure_bucket_match", "passed": report["failure_bucket"] == expected["failure_bucket"]},
        {"name": f"summary:{expected['summary_terms'][0]}", "passed": expected["summary_terms"][0] in searchable_summary},
        {"name": f"summary:{expected['summary_terms'][1]}", "passed": expected["summary_terms"][1] in searchable_summary},
        {"name": f"evidence:{expected['evidence_terms'][0]}", "passed": expected["evidence_terms"][0] in searchable_summary},
        {"name": f"evidence:{expected['evidence_terms'][1]}", "passed": expected["evidence_terms"][1] in searchable_summary},
        {"name": f"action:{expected['action_terms'][0]}", "passed": expected["action_terms"][0] in searchable_actions},
        {"name": f"action:{expected['action_terms'][1]}", "passed": expected["action_terms"][1] in searchable_actions},
    ]

    passed_checks = sum(1 for item in checks if item["passed"])
    total_checks = len(checks)
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
    metadata = []
    for case in REPLAY_CASES:
        metrics = case["metrics"]
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
    runs = []
    passed_checks = 0
    total_checks = 0
    severities = Counter()
    buckets = Counter()

    for case in REPLAY_CASES:
        report = build_structured_report(case)
        scored = _score_report(case, report)
        runs.append(scored)
        passed_checks += scored["passed_checks"]
        total_checks += scored["total_checks"]
        severities[report["severity"]] += 1
        buckets[report["failure_bucket"]] += 1

    score_pct = round((passed_checks / total_checks) * 100, 1) if total_checks else 0.0
    severity_accuracy = round(
        (
            sum(1 for case, run in zip(REPLAY_CASES, runs) if case["expected"]["severity"] == run["severity"])
            / len(REPLAY_CASES)
        )
        * 100,
        1,
    )
    bucket_accuracy = round(
        (
            sum(1 for case, run in zip(REPLAY_CASES, runs) if case["expected"]["failure_bucket"] == run["failure_bucket"])
            / len(REPLAY_CASES)
        )
        * 100,
        1,
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


if __name__ == "__main__":
    suite = run_replay_suite()
    summary = suite["summary"]
    print(
        f"Aegis-Air replay suite: {summary['cases']} cases, "
        f"{summary['passed_checks']}/{summary['total_checks']} checks passed, "
        f"{summary['score_pct']}% overall."
    )
