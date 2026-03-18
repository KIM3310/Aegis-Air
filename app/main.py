from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import random
import time
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Aegis-Air Review Target API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Instrument the app to expose /metrics for Prometheus
Instrumentator().instrument(app).expose(app)

CHECKOUT_ERROR_RATE = 0.30
CHECKOUT_LATENCY_RATE = 0.10


def build_store_diagnostics():
    return {
        "chaos_enabled": True,
        "metrics_ready": True,
        "checkout_error_rate": CHECKOUT_ERROR_RATE,
        "checkout_latency_rate": CHECKOUT_LATENCY_RATE,
        "next_action": "Drive /api/checkout repeatedly and confirm /metrics reflects the injected failure profile.",
    }

@app.get("/")
def read_root():
    return {"status": "ok", "service": "aegis-air-target-api"}


@app.get("/health")
def health():
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
def meta():
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
async def get_products():
    # Simulate some processing time
    await asyncio.sleep(random.uniform(0.01, 0.1))
    return [{"id": 1, "name": "Laptop"}, {"id": 2, "name": "Smartphone"}]

@app.get("/api/checkout")
async def checkout():
    # Simulate random latency and potential 500 errors to create interesting metrics and trigger chaos testing
    chaos = random.random()
    if chaos < CHECKOUT_ERROR_RATE:
        raise HTTPException(status_code=500, detail="Internal Server Error: Database Connection Lost")
    elif chaos < CHECKOUT_ERROR_RATE + CHECKOUT_LATENCY_RATE:
        await asyncio.sleep(random.uniform(1.0, 3.0))

    return {"status": "success", "order_id": random.randint(1000, 9999)}
