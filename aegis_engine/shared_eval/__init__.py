"""Shared evaluation framework for the Aegis incident-analysis product family.

This package is the single source of truth for:
- Incident severity and failure-bucket taxonomy (schemas.py)
- Parameterized replay evaluation runner (replay_runner.py)
- Unified scoring logic with rubric checks and pass/fail thresholds (scoring.py)
- JSON Schema export for cross-language consumption (export.py)

Consumed by both Aegis-Air (Python) and AegisOps (TypeScript).
"""

from aegis_engine.shared_eval.schemas import (
    ConfidenceRange,
    EvalCheck,
    EvalCheckCategory,
    FailureBucket,
    IncidentMetrics,
    IncidentSeverity,
    ProbeObservation,
    ReplayCaseExpectation,
    ReplayCaseResult,
    ReplaySuiteResult,
    ReplaySuiteSummary,
)
from aegis_engine.shared_eval.scoring import score_replay_case
from aegis_engine.shared_eval.replay_runner import run_replay_suite as run_shared_replay_suite

__all__ = [
    "ConfidenceRange",
    "EvalCheck",
    "EvalCheckCategory",
    "FailureBucket",
    "IncidentMetrics",
    "IncidentSeverity",
    "ProbeObservation",
    "ReplayCaseExpectation",
    "ReplayCaseResult",
    "ReplaySuiteResult",
    "ReplaySuiteSummary",
    "score_replay_case",
    "run_shared_replay_suite",
]
