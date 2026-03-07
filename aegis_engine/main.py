from __future__ import annotations

import asyncio
import json
import os
import random
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from aegis_engine.replay_evals import build_replay_metadata, build_structured_report, run_replay_suite

app = FastAPI(title="Aegis-Air Engine", description="Zero-Trust LLM SRE RCA Generator")

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
        "ops_contract": {
            "schema": "ops-envelope-v1",
            "version": 2,
            "required_fields": ["service", "status", "diagnostics.next_action"],
        },
        "features": [
            "chaos-trigger",
            "structured-incident-report",
            "replay-evals",
            "webhook-alert-ingest",
            "static-frontend-mount",
        ],
        "routes": [
            "/health",
            "/api/meta",
            "/api/chaos/trigger",
            "/api/incidents/report",
            "/api/replays",
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
        "ops_contract": {
            "schema": "ops-envelope-v1",
            "version": 2,
            "required_fields": ["service", "status", "diagnostics.next_action"],
        },
        "links": {
            "meta": "/api/meta",
            "chaos_trigger": "/api/chaos/trigger",
            "replay_evals": "/api/evals/replays",
        },
    }


frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
