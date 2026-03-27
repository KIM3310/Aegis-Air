"""Export eval schemas as JSON Schema for TypeScript consumption.

Run this module directly to emit JSON Schema to stdout:

    python -m aegis_engine.shared_eval.export

Or import and call export_all_schemas() to get a dict of model names
to their JSON Schema representations.
"""

from __future__ import annotations

import json
import sys
from typing import Any

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
    FAILURE_TAXONOMY,
)


_EXPORTABLE_MODELS = [
    ConfidenceRange,
    EvalCheck,
    IncidentMetrics,
    ProbeObservation,
    ReplayCaseExpectation,
    ReplayCaseResult,
    ReplaySuiteResult,
    ReplaySuiteSummary,
]

_EXPORTABLE_ENUMS = [
    IncidentSeverity,
    FailureBucket,
    EvalCheckCategory,
]


def _enum_to_json_schema(enum_cls: type) -> dict[str, Any]:
    """Convert a Python str Enum to a JSON Schema definition."""
    return {
        "title": enum_cls.__name__,
        "type": "string",
        "enum": [member.value for member in enum_cls],
        "description": (enum_cls.__doc__ or "").strip(),
    }


def export_all_schemas() -> dict[str, Any]:
    """Export all shared eval schemas as a JSON Schema document.

    Returns a dict with:
    - "$schema": JSON Schema draft URL
    - "title": document title
    - "definitions": all model and enum schemas
    - "failure_taxonomy": the shared failure taxonomy
    - "version": schema version for sync checking
    """
    definitions: dict[str, Any] = {}

    for model_cls in _EXPORTABLE_MODELS:
        definitions[model_cls.__name__] = model_cls.model_json_schema()

    for enum_cls in _EXPORTABLE_ENUMS:
        definitions[enum_cls.__name__] = _enum_to_json_schema(enum_cls)

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Aegis Shared Eval Schemas",
        "version": "1.0.0",
        "description": "Single source of truth for incident taxonomy and eval logic across the Aegis product family.",
        "definitions": definitions,
        "failure_taxonomy": FAILURE_TAXONOMY,
    }


def export_json(indent: int = 2) -> str:
    """Export all schemas as a formatted JSON string."""
    return json.dumps(export_all_schemas(), indent=indent, sort_keys=False)


if __name__ == "__main__":
    print(export_json())
    sys.exit(0)
