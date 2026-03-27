"""Parameterized replay evaluation runner.

Decouples case definitions, report generation, and scoring so either repo
can plug in its own report builder while sharing evaluation logic.
"""

from __future__ import annotations

from typing import Any, Callable

from aegis_engine.shared_eval.schemas import (
    FAILURE_TAXONOMY,
    ReplayCaseExpectation,
    ReplayCaseResult,
    ReplaySuiteResult,
)
from aegis_engine.shared_eval.scoring import aggregate_suite, score_replay_case


def run_replay_suite(
    cases: list[dict[str, Any]],
    report_builder: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    mode: str = "probe",
    pass_threshold_pct: float = 100.0,
    taxonomy: dict[str, str] | None = None,
) -> ReplaySuiteResult:
    """Run a full replay evaluation suite.

    Args:
        cases: List of replay case dicts.  Each must have 'id', 'title',
               and 'expected' keys.
        report_builder: Function that takes a case dict and returns a
                       structured report dict.
        mode: 'probe' for Aegis-Air, 'log' for AegisOps.
        pass_threshold_pct: Minimum score to pass a case (default 100%).
        taxonomy: Failure taxonomy for coverage calculation.  Defaults to
                 the shared FAILURE_TAXONOMY.

    Returns:
        A ReplaySuiteResult with summary and per-case runs.
    """
    if taxonomy is None:
        taxonomy = dict(FAILURE_TAXONOMY)

    runs: list[ReplayCaseResult] = []
    for case in cases:
        report = report_builder(case)
        expected_raw = case["expected"]

        # Build expectation from dict, handling both styles
        expected = ReplayCaseExpectation(**expected_raw) if isinstance(expected_raw, dict) else expected_raw

        result = score_replay_case(
            case_id=case["id"],
            title=case["title"],
            expected=expected,
            report=report,
            mode=mode,
            pass_threshold_pct=pass_threshold_pct,
        )
        runs.append(result)

    return aggregate_suite(cases, runs, taxonomy)


def run_single_case(
    case: dict[str, Any],
    report_builder: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    mode: str = "probe",
    pass_threshold_pct: float = 100.0,
) -> ReplayCaseResult:
    """Run a single replay case evaluation.

    Convenience wrapper for testing or debugging individual cases.
    """
    report = report_builder(case)
    expected_raw = case["expected"]
    expected = ReplayCaseExpectation(**expected_raw) if isinstance(expected_raw, dict) else expected_raw

    return score_replay_case(
        case_id=case["id"],
        title=case["title"],
        expected=expected,
        report=report,
        mode=mode,
        pass_threshold_pct=pass_threshold_pct,
    )
