from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ENGINE = load_module("aegis_air_engine_main", "aegis_engine/main.py")
STORE_API = load_module("aegis_air_store_main", "app/main.py")


def test_engine_health_and_meta():
    client = TestClient(ENGINE.app)

    health = client.get("/health")
    meta = client.get("/api/meta")

    assert health.status_code == 200
    assert health.json()["service"] == "aegis-air-engine"
    assert health.json()["links"]["meta"] == "/api/meta"

    assert meta.status_code == 200
    body = meta.json()
    assert body["service"] == "aegis-air-engine"
    assert body["model"] == "phi3"
    assert "/api/chaos/trigger" in body["routes"]


def test_store_api_health_and_meta():
    client = TestClient(STORE_API.app)

    health = client.get("/health")
    meta = client.get("/meta")

    assert health.status_code == 200
    assert health.json()["service"] == "dummy-ecommerce-api"
    assert health.json()["links"]["metrics"] == "/metrics"

    assert meta.status_code == 200
    body = meta.json()
    assert body["service"] == "dummy-ecommerce-api"
    assert body["chaos_profile"]["checkout_error_rate"] == 0.30
    assert "/api/checkout" in body["routes"]
