from __future__ import annotations

import asyncio
import json
import os
import random
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from aegis_engine.replay_evals import (
    build_replay_metadata,
    build_replay_summary,
    build_structured_report,
    run_replay_suite,
)

app = FastAPI(title="Aegis-Air Engine", description="Local incident review engine for structured RCA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = os.getenv("AEGIS_AIR_OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("AEGIS_AIR_MODEL", "phi3")
TARGET_API_URL = os.getenv("AEGIS_AIR_TARGET_API_URL", "http://localhost:8000/api/checkout")
CHAOS_PROBE_COUNT = int(os.getenv("AEGIS_AIR_CHAOS_PROBE_COUNT", "10"))


class AlertPayload(BaseModel):
    service_name: str
    incident_time: str
    status_code: int
    error_details: str
    metrics: dict[str, Any] | None = None
    probe_observations: list[dict[str, Any]] | None = None


AlertPayload.model_rebuild()


def build_engine_diagnostics() -> dict[str, Any]:
    ollama_configured = OLLAMA_URL.startswith("http")
    target_api_configured = TARGET_API_URL.startswith("http")
    return {
        "llm_mode": "local-ollama-with-deterministic-fallback",
        "ollama_configured": ollama_configured,
        "target_api_configured": target_api_configured,
        "replay_eval_ready": True,
        "live_loop_ready": target_api_configured,
        "next_action": (
            "Trigger /api/chaos/trigger for a live probe loop or review /api/evals/replays for replay cases."
            if target_api_configured
            else "Configure AEGIS_AIR_TARGET_API_URL to probe a live service. Replay cases remain available."
        ),
    }


def build_incident_report_schema() -> dict[str, Any]:
    return {
        "schema": "aegis-air-incident-report-v1",
        "version": 1,
        "required_fields": [
            "severity",
            "failure_bucket",
            "summary",
            "primary_hypothesis",
            "supporting_evidence",
            "immediate_actions",
            "operator_questions",
            "timeline",
            "metrics",
            "probe_observations",
            "rca_report",
        ],
        "delivery_modes": ["live-probe", "webhook-alert", "recorded-review"],
        "operator_rules": [
            "Keep the structured report valid even when Ollama is unavailable.",
            "Separate deterministic evidence from optional narrative generation.",
            "Never claim live target readiness unless the target service meta is reachable.",
        ],
    }


def _derive_target_meta_url(target_api_url: str) -> str | None:
    parsed = urlsplit(target_api_url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return urlunsplit((parsed.scheme, parsed.netloc, "/meta", "", ""))


async def _fetch_target_service_meta() -> dict[str, Any]:
    meta_url = _derive_target_meta_url(TARGET_API_URL)
    if not meta_url:
        return {
            "status": "unavailable",
            "meta_url": None,
            "reason": "target-api-url-not-configured",
        }

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(meta_url)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError, OSError) as exc:
        return {
            "status": "unavailable",
            "meta_url": meta_url,
            "reason": f"target-meta-unreachable:{type(exc).__name__}",
        }

    return {
        "status": "ok",
        "meta_url": meta_url,
        "service": payload.get("service", "unknown"),
        "chaos_profile": payload.get("chaos_profile", {}),
        "diagnostics": payload.get("diagnostics", {}),
        "ops_contract": payload.get("ops_contract", {}),
        "routes": payload.get("routes", []),
    }


async def build_runtime_brief() -> dict[str, Any]:
    replay_suite = run_replay_suite()
    target_service = await _fetch_target_service_meta()

    return {
        "status": "ok",
        "service": "aegis-air-engine",
        "headline": "Air-gapped incident review engine with deterministic replay evidence and local-first operator handoff.",
        "readiness_contract": "aegis-air-runtime-brief-v1",
        "mode": "air-gapped-local-first",
        "generated_at": _utc_now(),
        "diagnostics": build_engine_diagnostics(),
        "report_contract": build_incident_report_schema(),
        "replay_summary": replay_suite["summary"],
        "evidence_counts": {
            "replay_cases": replay_suite["summary"]["cases"],
            "rubric_checks": replay_suite["summary"]["total_checks"],
            "frontend_surfaces": 4,
            "api_routes": 10,
        },
        "trust_boundary": [
            "telemetry stays local to the operator environment",
            "structured RCA is deterministic even without Ollama",
            "replay suite acts as a regression gate before deployment",
            "target service health is optional and explicitly surfaced as reachable/unreachable",
        ],
        "review_flow": [
            "Open /health to confirm live-loop readiness and review links.",
            "Read /api/runtime/brief for trust boundary, replay score, and target reachability.",
            "Use the local console to run a live or recorded incident review.",
            "Validate the schema at /api/schema/report before integrating downstream handoff flows.",
        ],
        "two_minute_review": [
            "Open /health to confirm whether the target meta surface is actually reachable.",
            "Read /api/runtime/brief for replay score, trust boundary, and watchouts.",
            "Read /api/review-pack for delivery modes and downstream handoff contract.",
            "Open /api/evals/replays to verify replay evidence before claiming live-loop readiness.",
        ],
        "operator_rules": [
            "Treat replay score and live probe evidence as separate signals.",
            "Do not block incident reporting on the local narrative model.",
            "Prefer structured RCA sections over free-form prose during handoff.",
        ],
        "watchouts": [
            "The default target API is a local demo service, not a production dependency.",
            "Frontend Pages mode can only show recorded review data when the engine is absent.",
            "Narrative streaming is optional; the schema-backed report is the source of truth.",
        ],
        "artifacts": [
            {"label": "Engine Meta", "href": "/api/meta", "kind": "route"},
            {"label": "Runtime Brief", "href": "/api/runtime/brief", "kind": "route"},
            {"label": "Incident Schema", "href": "/api/schema/report", "kind": "route"},
            {"label": "Replay Summary", "href": "/api/evals/replays/summary", "kind": "route"},
            {"label": "Replay Evals", "href": "/api/evals/replays", "kind": "route"},
            {"label": "Replay Eval Docs", "href": "docs/INCIDENT_REPLAY_EVALS.md", "kind": "doc"},
            {"label": "Replay Suite Runner", "href": "scripts/run_replay_suite.py", "kind": "script"},
        ],
        "proof_assets": [
            {"label": "Health Surface", "href": "/health", "kind": "route"},
            {"label": "Runtime Brief", "href": "/api/runtime/brief", "kind": "route"},
            {"label": "Review Pack", "href": "/api/review-pack", "kind": "route"},
            {"label": "Replay Summary", "href": "/api/evals/replays/summary", "kind": "route"},
            {"label": "Replay Evals", "href": "/api/evals/replays", "kind": "route"},
        ],
        "target_service": target_service,
        "routes": [
            "/health",
            "/api/meta",
            "/api/runtime/brief",
            "/api/schema/report",
            "/api/chaos/trigger",
            "/api/incidents/report",
            "/api/replays",
            "/api/evals/replays/summary",
            "/api/evals/replays",
            "/webhook/alert",
        ],
    }


async def build_review_pack() -> dict[str, Any]:
    runtime_brief = await build_runtime_brief()
    report_contract = runtime_brief["report_contract"]
    replay_summary = runtime_brief["replay_summary"]
    target_service = runtime_brief["target_service"]

    return {
        "status": runtime_brief["status"],
        "service": "aegis-air-engine",
        "generated_at": _utc_now(),
        "readiness_contract": "aegis-air-review-pack-v1",
        "headline": "Reviewer-first pack for replay evidence, target reachability, and downstream handoff readiness in air-gapped environments.",
        "proof_bundle": {
            "replay_cases": replay_summary["cases"],
            "rubric_checks": replay_summary["total_checks"],
            "score_pct": replay_summary["score_pct"],
            "target_meta_reachable": target_service.get("status") == "ok",
            "review_endpoints": [
                "/health",
                "/api/meta",
                "/api/runtime/brief",
                "/api/review-pack",
                "/api/schema/report",
                "/api/evals/replays/summary",
                "/api/evals/replays",
            ],
        },
        "target_boundary": {
            "status": target_service.get("status", "unavailable"),
            "meta_url": target_service.get("meta_url"),
            "service": target_service.get("service", "unknown"),
        },
        "handoff_contract": {
            "schema": report_contract["schema"],
            "delivery_modes": report_contract["delivery_modes"],
            "required_fields": report_contract["required_fields"],
        },
        "review_sequence": [
            "Confirm /health and /api/meta before claiming live target readiness.",
            "Read /api/runtime/brief for replay score and trust boundary.",
            "Read /api/review-pack for downstream handoff contract and review endpoints.",
            "Run live or recorded incident review only after schema and replay evidence align.",
        ],
        "two_minute_review": runtime_brief["two_minute_review"],
        "artifacts": runtime_brief["artifacts"],
        "proof_assets": runtime_brief["proof_assets"],
        "watchouts": runtime_brief["watchouts"],
        "links": {
            "health": "/health",
            "meta": "/api/meta",
            "runtime_brief": "/api/runtime/brief",
            "review_pack": "/api/review-pack",
            "report_schema": "/api/schema/report",
            "replay_summary": "/api/evals/replays/summary",
            "replay_evals": "/api/evals/replays",
        },
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sse_event(event_type: str, content: Any) -> str:
    return f"data: {json.dumps({'type': event_type, 'content': content})}\n\n"


def _chunk_text(text: str, chunk_size: int = 36) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(f"{current} ")
        current = word
    if current:
        chunks.append(f"{current} ")
    return chunks


async def _stream_narrative_tokens(report: dict[str, Any]) -> AsyncIterator[str]:
    prompt = (
        "You are Aegis-Air, a zero-trust SRE copilot. Convert the structured incident report below "
        "into a concise operator handoff with one paragraph of RCA and two action bullets.\n\n"
        f"{report['rca_report']}"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                OLLAMA_URL,
                json={"model": MODEL_NAME, "prompt": prompt, "stream": True},
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_lines():
                    if not chunk:
                        continue
                    try:
                        data = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
                    token = data.get("response", "")
                    if token:
                        yield token
        return
    except (httpx.HTTPError, OSError):
        pass

    for chunk in _chunk_text(report["rca_report"]):
        await asyncio.sleep(0.02)
        yield chunk


async def _probe_target(client: httpx.AsyncClient, probe_number: int) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        response = await client.get(TARGET_API_URL)
        latency_ms = int((time.perf_counter() - start) * 1000)
        detail = response.text.strip() or f"HTTP {response.status_code}"
        outcome = "success"
        if response.status_code >= 400:
            outcome = "error"
        elif latency_ms >= 1000:
            outcome = "latency"
            detail = f"Latency spike observed at {latency_ms} ms"
        return {
            "probe": probe_number,
            "outcome": outcome,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "detail": detail,
        }
    except (httpx.HTTPError, OSError) as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "probe": probe_number,
            "outcome": "error",
            "status_code": 503,
            "latency_ms": latency_ms,
            "detail": f"Connection failed: {type(exc).__name__}: {exc}",
        }


async def generate_chaos_and_stream_response() -> AsyncIterator[str]:
    yield _sse_event("log", "[Chaos Engine] Starting zero-trust probe loop against the target API.\n")

    probe_observations: list[dict[str, Any]] = []
    anomaly_seen = False

    async with httpx.AsyncClient(timeout=10.0) as client:
        for probe_number in range(1, CHAOS_PROBE_COUNT + 1):
            yield _sse_event("log", f"[Probe {probe_number}] -> GET {TARGET_API_URL}\n")
            observation = await _probe_target(client, probe_number)
            probe_observations.append(observation)

            if observation["outcome"] == "success":
                yield _sse_event("log", f"      SUCCESS {observation['status_code']} in {observation['latency_ms']} ms\n")
            elif observation["outcome"] == "latency":
                anomaly_seen = True
                yield _sse_event("log", f"      LATENCY SPIKE {observation['latency_ms']} ms\n")
            else:
                anomaly_seen = True
                yield _sse_event("log", f"      INCIDENT SIGNAL {observation['status_code']}: {observation['detail']}\n")

            if anomaly_seen and len(probe_observations) >= 6:
                break
            await asyncio.sleep(0.25 + random.random() * 0.35)

    if not anomaly_seen:
        yield _sse_event("log", "[Chaos Engine] Probe loop completed without a strong incident signal.\n")
        yield _sse_event("done", {"status": "no-incident"})
        return

    lead_observation = next((item for item in probe_observations if item["outcome"] != "success"), probe_observations[-1])
    payload = {
        "service_name": "e-commerce-checkout-api",
        "incident_time": _utc_now(),
        "status_code": lead_observation["status_code"],
        "error_details": lead_observation["detail"],
        "probe_observations": probe_observations,
    }
    report = build_structured_report(payload)

    yield _sse_event(
        "log",
        f"\n[Aegis-Air] Structured incident report ready: {report['severity']} {report['failure_bucket']}.\n",
    )
    yield _sse_event("report", report)
    yield _sse_event("log", "[Aegis-Air] Drafting concise operator handoff.\n\n")

    async for token in _stream_narrative_tokens(report):
        yield _sse_event("token", token)

    yield _sse_event("log", "\n\n[Aegis-Air] Incident review complete.\n")
    yield _sse_event("done", {"status": "completed"})


@app.get("/api/chaos/trigger")
async def trigger_chaos_endpoint() -> StreamingResponse:
    return StreamingResponse(generate_chaos_and_stream_response(), media_type="text/event-stream")


@app.post("/api/incidents/report")
async def build_report_endpoint(payload: AlertPayload) -> dict[str, Any]:
    report = build_structured_report(payload.model_dump())
    return {"status": "success", "report": report, "rca_report": report["rca_report"]}


@app.post("/webhook/alert")
async def handle_alert(payload: AlertPayload) -> dict[str, Any]:
    report = build_structured_report(payload.model_dump())
    return {
        "status": "success",
        "message": "Webhook received and analyzed locally.",
        "report": report,
        "rca_report": report["rca_report"],
    }


@app.get("/api/replays")
def list_replays() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "aegis-air-engine",
        "replays": build_replay_metadata(),
    }


@app.get("/api/evals/replays")
def replay_eval_summary() -> dict[str, Any]:
    suite = run_replay_suite()
    return {
        "status": "ok",
        "service": "aegis-air-engine",
        **suite,
    }


@app.get("/api/evals/replays/summary")
def replay_eval_review_summary(
    min_score_pct: float | None = None,
    failure_bucket: str | None = None,
) -> dict[str, Any]:
    try:
        summary = build_replay_summary(
            min_score_pct=min_score_pct,
            failure_bucket=failure_bucket,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "ok",
        "service": "aegis-air-engine",
        **summary,
    }


@app.get("/api/schema/report")
def report_schema() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "aegis-air-engine",
        "generated_at": _utc_now(),
        **build_incident_report_schema(),
    }


@app.get("/api/runtime/brief")
async def runtime_brief() -> dict[str, Any]:
    return await build_runtime_brief()


@app.get("/api/review-pack")
async def review_pack() -> dict[str, Any]:
    return await build_review_pack()


@app.get("/api/meta")
def engine_meta() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "aegis-air-engine",
        "mode": "zero-trust",
        "model": MODEL_NAME,
        "ollama_url": OLLAMA_URL,
        "target_api_url": TARGET_API_URL,
        "diagnostics": build_engine_diagnostics(),
        "report_contract": build_incident_report_schema(),
        "ops_contract": {
            "schema": "ops-envelope-v1",
            "version": 2,
            "required_fields": ["service", "status", "diagnostics.next_action"],
        },
        "features": [
            "chaos-trigger",
            "structured-incident-report",
            "replay-summary",
            "replay-evals",
            "runtime-brief",
            "review-pack",
            "report-schema",
            "webhook-alert-ingest",
            "static-frontend-mount",
        ],
        "routes": [
            "/health",
            "/api/meta",
            "/api/runtime/brief",
            "/api/review-pack",
            "/api/schema/report",
            "/api/chaos/trigger",
            "/api/incidents/report",
            "/api/replays",
            "/api/evals/replays/summary",
            "/api/evals/replays",
            "/webhook/alert",
        ],
    }


@app.get("/health")
def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "aegis-air-engine",
        "message": "Aegis-Air engine online. Zero-trust mode active.",
        "diagnostics": build_engine_diagnostics(),
        "capabilities": [
            "runtime-brief-surface",
            "review-pack-surface",
            "report-schema-surface",
            "replay-summary-surface",
            "replay-eval-surface",
        ],
        "ops_contract": {
            "schema": "ops-envelope-v1",
            "version": 2,
            "required_fields": ["service", "status", "diagnostics.next_action"],
        },
        "links": {
            "meta": "/api/meta",
            "runtime_brief": "/api/runtime/brief",
            "review_pack": "/api/review-pack",
            "report_schema": "/api/schema/report",
            "chaos_trigger": "/api/chaos/trigger",
            "replay_summary": "/api/evals/replays/summary",
            "replay_evals": "/api/evals/replays",
        },
    }


frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
