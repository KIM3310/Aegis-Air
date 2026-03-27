"""Sync check: verify Python schemas and TypeScript types are compatible.

This test reads the TypeScript types file from the sibling AegisOps repo
and validates that the shared enums, model shapes, and schema version
match the Python source of truth.

Run with:
    python -m pytest tests/test_shared_eval_sync.py -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from aegis_engine.shared_eval.schemas import (
    EvalCheckCategory,
    FailureBucket,
    IncidentSeverity,
    FAILURE_TAXONOMY,
)
from aegis_engine.shared_eval.export import export_all_schemas


# Path to the TypeScript shared types (sibling repo)
_AEGISOPS_ROOT = Path(__file__).resolve().parents[2] / "AegisOps"
_TS_TYPES_PATH = _AEGISOPS_ROOT / "server" / "lib" / "aegis-shared-types.ts"


def _read_ts_types() -> str:
    """Read the TypeScript shared types file, skipping if not present."""
    if not _TS_TYPES_PATH.exists():
        pytest.skip(
            f"AegisOps shared types not found at {_TS_TYPES_PATH}. "
            "Run this sync suite only when both repos are checked out as siblings."
        )
    return _TS_TYPES_PATH.read_text(encoding="utf-8")


def _extract_ts_string_union(ts_source: str, type_name: str) -> list[str]:
    """Extract string literal union values from a TypeScript type alias."""
    pattern = rf'export type {type_name}\s*=\s*([\s\S]*?);'
    match = re.search(pattern, ts_source)
    if not match:
        return []
    body = match.group(1)
    return re.findall(r'"([^"]+)"', body)


def _extract_ts_const_string(ts_source: str, const_name: str) -> str | None:
    """Extract a string constant value from TypeScript source."""
    pattern = rf'export const {const_name}\s*=\s*"([^"]+)"'
    match = re.search(pattern, ts_source)
    return match.group(1) if match else None


def _extract_ts_record_keys(ts_source: str, const_name: str) -> list[str]:
    """Extract keys from a TypeScript Record/object constant."""
    pattern = rf'export const {const_name}[^{{]*\{{([\s\S]*?)\}};'
    match = re.search(pattern, ts_source)
    if not match:
        return []
    body = match.group(1)
    return re.findall(r'"([^"]+)":', body)


def test_severity_enum_sync() -> None:
    """IncidentSeverity values in Python match SharedIncidentSeverity in TypeScript."""
    ts = _read_ts_types()
    ts_values = set(_extract_ts_string_union(ts, "SharedIncidentSeverity"))
    py_values = {member.value for member in IncidentSeverity}
    assert ts_values == py_values, f"Severity mismatch: TS={ts_values} PY={py_values}"


def test_failure_bucket_enum_sync() -> None:
    """FailureBucket values in Python match SharedFailureBucket in TypeScript."""
    ts = _read_ts_types()
    ts_values = set(_extract_ts_string_union(ts, "SharedFailureBucket"))
    py_values = {member.value for member in FailureBucket}
    assert ts_values == py_values, f"Bucket mismatch: TS={ts_values} PY={py_values}"


def test_eval_check_category_enum_sync() -> None:
    """EvalCheckCategory values in Python match SharedEvalCheckCategory in TypeScript."""
    ts = _read_ts_types()
    ts_values = set(_extract_ts_string_union(ts, "SharedEvalCheckCategory"))
    py_values = {member.value for member in EvalCheckCategory}
    assert ts_values == py_values, f"Category mismatch: TS={ts_values} PY={py_values}"


def test_failure_taxonomy_sync() -> None:
    """FAILURE_TAXONOMY keys in Python match SHARED_FAILURE_TAXONOMY keys in TypeScript."""
    ts = _read_ts_types()
    ts_keys = set(_extract_ts_record_keys(ts, "SHARED_FAILURE_TAXONOMY"))
    py_keys = set(FAILURE_TAXONOMY.keys())
    assert ts_keys == py_keys, f"Taxonomy key mismatch: TS={ts_keys} PY={py_keys}"


def test_schema_version_sync() -> None:
    """Schema version in Python export matches SHARED_EVAL_SCHEMA_VERSION in TypeScript."""
    ts = _read_ts_types()
    ts_version = _extract_ts_const_string(ts, "SHARED_EVAL_SCHEMA_VERSION")
    py_schemas = export_all_schemas()
    py_version = py_schemas["version"]
    assert ts_version == py_version, f"Version mismatch: TS={ts_version} PY={py_version}"


def test_json_schema_export_structure() -> None:
    """JSON Schema export has expected top-level keys and definitions."""
    schemas = export_all_schemas()
    assert schemas["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert "definitions" in schemas
    assert "failure_taxonomy" in schemas
    assert "version" in schemas

    defs = schemas["definitions"]
    expected_models = {
        "ConfidenceRange",
        "EvalCheck",
        "IncidentMetrics",
        "ProbeObservation",
        "ReplayCaseExpectation",
        "ReplayCaseResult",
        "ReplaySuiteResult",
        "ReplaySuiteSummary",
    }
    expected_enums = {
        "IncidentSeverity",
        "FailureBucket",
        "EvalCheckCategory",
    }
    for name in expected_models | expected_enums:
        assert name in defs, f"Missing definition: {name}"


def test_typescript_interfaces_present() -> None:
    """All expected TypeScript interfaces exist in the shared types file."""
    ts = _read_ts_types()
    expected_interfaces = [
        "SharedConfidenceRange",
        "SharedProbeObservation",
        "SharedIncidentMetrics",
        "SharedReplayCaseExpectation",
        "SharedEvalCheck",
        "SharedReplayCaseResult",
        "SharedReplaySuiteSummary",
        "SharedReplaySuiteResult",
    ]
    for iface in expected_interfaces:
        assert f"export interface {iface}" in ts, f"Missing interface: {iface}"
