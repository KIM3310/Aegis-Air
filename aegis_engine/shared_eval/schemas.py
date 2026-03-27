"""Shared incident/severity/failure-bucket taxonomy as Pydantic models.

This module is the source of truth for the incident evaluation taxonomy
consumed by both Aegis-Air (Python) and AegisOps (TypeScript).
TypeScript types are generated from these schemas via export.py.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class IncidentSeverity(str, Enum):
    """Incident severity levels used across both repos."""
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"
    UNKNOWN = "UNKNOWN"


class FailureBucket(str, Enum):
    """Failure-bucket taxonomy shared across the Aegis product family.

    Each bucket maps to a deterministic classification rule and a set of
    operator-facing actions.
    """
    DEPENDENCY_OUTAGE = "dependency-outage"
    DEPENDENCY_TIMEOUT = "dependency-timeout"
    LATENCY_SATURATION = "latency-saturation"
    AUTH_REGRESSION = "auth-regression"


FAILURE_TAXONOMY: Dict[str, str] = {
    FailureBucket.DEPENDENCY_OUTAGE.value: "Hard dependency unavailable or refusing connections.",
    FailureBucket.DEPENDENCY_TIMEOUT.value: "Upstream dependency is responding too slowly or timing out.",
    FailureBucket.LATENCY_SATURATION.value: "Service remains reachable but is saturated and breaching latency SLOs.",
    FailureBucket.AUTH_REGRESSION.value: "Credential, secret, or policy drift is rejecting otherwise valid traffic.",
}


class EvalCheckCategory(str, Enum):
    """Categories of rubric checks used during replay evaluation.

    These are shared between the AegisOps check-based rubric and the
    Aegis-Air score-based rubric.
    """
    SEVERITY_MATCH = "severity_match"
    FAILURE_BUCKET_MATCH = "failure_bucket_match"
    TITLE_KEYWORDS = "title_keywords"
    TAG_COVERAGE = "tag_coverage"
    TIMELINE_COVERAGE = "timeline_coverage"
    ROOT_CAUSE_COVERAGE = "root_cause_coverage"
    ACTIONABILITY = "actionability"
    REASONING_TRACE = "reasoning_trace"
    CONFIDENCE_RANGE = "confidence_range"
    SUMMARY_KEYWORDS = "summary_keywords"
    EVIDENCE_KEYWORDS = "evidence_keywords"
    ACTION_KEYWORDS = "action_keywords"


# ---------------------------------------------------------------------------
# Shared data models
# ---------------------------------------------------------------------------

class ConfidenceRange(BaseModel):
    """Min/max confidence score band for a replay expectation."""
    min: float = Field(..., ge=0, le=100)
    max: float = Field(..., ge=0, le=100)


class ProbeObservation(BaseModel):
    """A single probe observation from a replay case or live loop."""
    probe: int
    outcome: Literal["success", "error", "latency"]
    status_code: int
    latency_ms: int
    detail: str = ""


class IncidentMetrics(BaseModel):
    """Aggregated metrics snapshot for an incident or replay case."""
    sample_size: int = 0
    success_count: int = 0
    error_count: int = 0
    error_rate: float = 0.0
    p95_latency_ms: int = 0
    latency_spike_count: int = 0


class ReplayCaseExpectation(BaseModel):
    """Expected outcomes for a replay case, used by both repos' rubrics.

    AegisOps uses title_includes/tags_include/root_cause_includes for its
    log-based replay.  Aegis-Air uses summary_terms/evidence_terms/action_terms
    for its probe-based replay.  Both share severity and failure_bucket.
    """
    severity: IncidentSeverity

    # Aegis-Air probe-based expectations
    failure_bucket: Optional[FailureBucket] = None
    summary_terms: List[str] = Field(default_factory=list)
    evidence_terms: List[str] = Field(default_factory=list)
    action_terms: List[str] = Field(default_factory=list)

    # AegisOps log-based expectations
    title_includes: List[str] = Field(default_factory=list)
    tags_include: List[str] = Field(default_factory=list)
    root_cause_includes: List[str] = Field(default_factory=list)
    action_items_include: List[str] = Field(default_factory=list)
    reasoning_sections: List[str] = Field(default_factory=list)
    min_timeline_events: Optional[int] = None
    confidence_range: Optional[ConfidenceRange] = None


class EvalCheck(BaseModel):
    """A single rubric check result."""
    name: str
    category: EvalCheckCategory
    passed: bool
    detail: str = ""


class ReplayCaseResult(BaseModel):
    """Scored result for a single replay case."""
    case_id: str
    title: str
    severity: IncidentSeverity
    failure_bucket: Optional[FailureBucket] = None
    score_pct: float
    passed_checks: int
    total_checks: int
    checks: List[EvalCheck]
    status: Literal["pass", "fail"] = "fail"


class ReplaySuiteSummary(BaseModel):
    """Aggregate summary for a replay suite run."""
    cases: int
    passed_checks: int
    total_checks: int
    score_pct: float
    severity_accuracy_pct: float
    bucket_accuracy_pct: float = 0.0
    taxonomy_coverage_pct: float = 0.0


class ReplaySuiteResult(BaseModel):
    """Full replay suite result with summary and per-case runs."""
    summary: ReplaySuiteSummary
    severity_breakdown: Dict[str, int] = Field(default_factory=dict)
    bucket_breakdown: Dict[str, int] = Field(default_factory=dict)
    failure_taxonomy: Dict[str, str] = Field(default_factory=dict)
    runs: List[ReplayCaseResult] = Field(default_factory=list)
