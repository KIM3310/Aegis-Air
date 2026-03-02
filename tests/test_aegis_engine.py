import json
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch


def install_dependency_stubs() -> None:
    if "fastapi" not in sys.modules:
        fastapi_module = types.ModuleType("fastapi")

        class FastAPI:
            def __init__(self, *args, **kwargs):
                pass

            def add_middleware(self, *args, **kwargs):
                return None

            def get(self, *args, **kwargs):
                def decorator(func):
                    return func

                return decorator

            def post(self, *args, **kwargs):
                def decorator(func):
                    return func

                return decorator

            def mount(self, *args, **kwargs):
                return None

        fastapi_module.FastAPI = FastAPI
        sys.modules["fastapi"] = fastapi_module

        cors_module = types.ModuleType("fastapi.middleware.cors")

        class CORSMiddleware:
            pass

        cors_module.CORSMiddleware = CORSMiddleware
        sys.modules["fastapi.middleware"] = types.ModuleType("fastapi.middleware")
        sys.modules["fastapi.middleware.cors"] = cors_module

        responses_module = types.ModuleType("fastapi.responses")

        class StreamingResponse:
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

        responses_module.StreamingResponse = StreamingResponse
        sys.modules["fastapi.responses"] = responses_module

        staticfiles_module = types.ModuleType("fastapi.staticfiles")

        class StaticFiles:
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

        staticfiles_module.StaticFiles = StaticFiles
        sys.modules["fastapi.staticfiles"] = staticfiles_module

    if "pydantic" not in sys.modules:
        pydantic_module = types.ModuleType("pydantic")

        class BaseModel:
            pass

        pydantic_module.BaseModel = BaseModel
        sys.modules["pydantic"] = pydantic_module

    if "httpx" not in sys.modules:
        httpx_module = types.ModuleType("httpx")

        class HTTPError(Exception):
            pass

        class ConnectError(HTTPError):
            pass

        class AsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        httpx_module.HTTPError = HTTPError
        httpx_module.ConnectError = ConnectError
        httpx_module.AsyncClient = AsyncClient
        sys.modules["httpx"] = httpx_module


install_dependency_stubs()

from aegis_engine import main as engine


def parse_event(raw_event: str) -> dict:
    if not raw_event.startswith("data: "):
        raise ValueError(f"Unexpected SSE payload: {raw_event!r}")
    return json.loads(raw_event[len("data: "):].strip())


async def collect_events() -> list[dict]:
    events = []
    async for raw_event in engine.generate_chaos_and_stream_response():
        events.append(parse_event(raw_event))
    return events


class TestAegisEngineSSE(unittest.IsolatedAsyncioTestCase):
    async def test_llm_failure_streams_fallback_and_done(self):
        class MockIncidentResponse:
            status_code = 500
            text = "Internal Server Error: Database Connection Lost"

        class MockFailedLLMStream:
            async def __aenter__(self):
                raise engine.httpx.ConnectError("dial tcp 127.0.0.1:11434: connect: connection refused")

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class MockAsyncClient:
            def __init__(self, timeout: float):
                self.timeout = timeout

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get(self, _url):
                if self.timeout != 10.0:
                    raise AssertionError("Unexpected HTTP GET on non-chaos client")
                return MockIncidentResponse()

            def stream(self, _method, _url, json=None):
                if self.timeout != 60.0:
                    raise AssertionError("Unexpected stream on chaos client")
                return MockFailedLLMStream()

        with patch("aegis_engine.main.httpx.AsyncClient", MockAsyncClient), patch(
            "aegis_engine.main.asyncio.sleep", new=AsyncMock()
        ), patch("aegis_engine.main.random.random", return_value=0.0):
            events = await collect_events()

        self.assertEqual(events[-1]["type"], "done")
        self.assertTrue(
            any(
                event["type"] == "log"
                and "Local LLM request failed" in event.get("content", "")
                for event in events
            )
        )
        self.assertTrue(
            any(
                event["type"] == "token"
                and engine.LLM_FALLBACK_RESPONSE in event.get("content", "")
                for event in events
            )
        )

    async def test_connection_failures_still_emit_valid_json_events(self):
        class MockAsyncClient:
            def __init__(self, timeout: float):
                self.timeout = timeout

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get(self, _url):
                raise RuntimeError('upstream "db" unreachable')

            def stream(self, _method, _url, json=None):
                raise AssertionError("No LLM call should happen when incident is never detected")

        with patch("aegis_engine.main.httpx.AsyncClient", MockAsyncClient), patch(
            "aegis_engine.main.asyncio.sleep", new=AsyncMock()
        ), patch("aegis_engine.main.random.random", return_value=0.0):
            events = await collect_events()

        self.assertEqual(events[-1]["type"], "done")
        self.assertTrue(
            any(
                event["type"] == "log"
                and 'Connection Failed: upstream "db" unreachable' in event.get("content", "")
                for event in events
            )
        )


if __name__ == "__main__":
    unittest.main()
