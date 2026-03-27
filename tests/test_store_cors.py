from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


STORE_API = load_module("aegis_air_store_main_cors", "app/main.py")


def test_store_api_cors_allows_known_frontend_origin():
    client = TestClient(STORE_API.app)

    response = client.options(
        "/health",
        headers={
            "Origin": "https://aegis-air.pages.dev",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://aegis-air.pages.dev"


def test_store_api_cors_omits_unknown_origin():
    client = TestClient(STORE_API.app)

    response = client.options(
        "/health",
        headers={
            "Origin": "https://unexpected.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
