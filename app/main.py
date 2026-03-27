"""Aegis-Air review target API.

A chaos-injected e-commerce checkout API used as a probing target by the
Aegis-Air engine.  Provides configurable error and latency injection rates
for testing incident detection and classification.
"""

from __future__ import annotations

import asyncio
import os
import random
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Aegis-Air Review Target API", version="1.0")


def _read_cors_origins() -> list[str]:
    raw = (os.getenv("AEGIS_AIR_CORS_ORIGINS") or "").strip()
    if raw:
        origins = [item.strip() for item in raw.split(",") if item.strip()]
        if origins:
            return origins
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://aegis-air.pages.dev",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_read_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


# Instrument the app to expose /metrics for Prometheus
Instrumentator().instrument(app).expose(app)

CHECKOUT_ERROR_RATE: float = 0.30
CHECKOUT_LATENCY_RATE: float = 0.10


def build_store_diagnostics() -> dict[str, Any]:
    """Build diagnostics payload for the target store API.

    Returns:
        A dict with chaos configuration and readiness flags.
    """
    return {
        "chaos_enabled": True,
        "metrics_ready": True,
        "checkout_error_rate": CHECKOUT_ERROR_RATE,
        "checkout_latency_rate": CHECKOUT_LATENCY_RATE,
        "next_action": "Drive /api/checkout repeatedly and confirm /metrics reflects the injected failure profile.",
    }


@app.get("/")
def read_root() -> dict[str, str]:
    """Return service identity payload.

    Returns:
        A dict with ``status`` and ``service`` keys.
    """
    return {"status": "ok", "service": "aegis-air-target-api"}


@app.get("/health")
def health() -> dict[str, Any]:
    """Return health check with diagnostics and ops contract.

    Returns:
        A dict with status, diagnostics, ops contract, and links.
    """
    return {
        "status": "ok",
        "service": "aegis-air-target-api",
        "diagnostics": build_store_diagnostics(),
        "ops_contract": {
            "schema": "ops-envelope-v1",
            "version": 1,
            "required_fields": ["service", "status", "diagnostics.next_action"],
        },
        "links": {
            "meta": "/meta",
            "metrics": "/metrics",
        },
    }


@app.get("/meta")
def meta() -> dict[str, Any]:
    """Return service metadata including chaos profile and routes.

    Returns:
        A dict with status, chaos profile, diagnostics, and route list.
    """
    return {
        "status": "ok",
        "service": "aegis-air-target-api",
        "version": "1.0",
        "chaos_profile": {
            "checkout_error_rate": CHECKOUT_ERROR_RATE,
            "checkout_latency_rate": CHECKOUT_LATENCY_RATE,
        },
        "diagnostics": build_store_diagnostics(),
        "ops_contract": {
            "schema": "ops-envelope-v1",
            "version": 1,
            "required_fields": ["service", "status", "diagnostics.next_action"],
        },
        "routes": ["/", "/health", "/meta", "/api/products", "/api/checkout", "/metrics"],
    }


@app.get("/api/products")
async def get_products() -> list[dict[str, Any]]:
    """Return a simulated product catalog with random latency.

    Returns:
        A list of product dicts with ``id`` and ``name`` keys.
    """
    await asyncio.sleep(random.uniform(0.01, 0.1))
    return [{"id": 1, "name": "Laptop"}, {"id": 2, "name": "Smartphone"}]


@app.get("/api/checkout")
async def checkout() -> dict[str, Any]:
    """Simulate a checkout with chaos-injected errors and latency.

    Randomly injects HTTP 500 errors or latency spikes based on the
    configured ``CHECKOUT_ERROR_RATE`` and ``CHECKOUT_LATENCY_RATE``.

    Returns:
        A success payload with ``status`` and ``order_id``.

    Raises:
        HTTPException: 500 when the chaos random value triggers an error.
    """
    chaos: float = random.random()
    if chaos < CHECKOUT_ERROR_RATE:
        raise HTTPException(status_code=500, detail="Internal Server Error: Database Connection Lost")
    elif chaos < CHECKOUT_ERROR_RATE + CHECKOUT_LATENCY_RATE:
        await asyncio.sleep(random.uniform(1.0, 3.0))

    return {"status": "success", "order_id": random.randint(1000, 9999)}
