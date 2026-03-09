from __future__ import annotations

import os

from fastapi import HTTPException, Request


def operator_token_enabled() -> bool:
    return bool(str(os.getenv("AEGIS_AIR_OPERATOR_TOKEN", "")).strip())


def _read_bearer_token(request: Request) -> str:
    authorization = str(request.headers.get("authorization", "")).strip()
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


def require_operator_token(request: Request) -> None:
    expected = str(os.getenv("AEGIS_AIR_OPERATOR_TOKEN", "")).strip()
    if not expected:
        return

    header_token = str(request.headers.get("x-operator-token", "")).strip()
    bearer_token = _read_bearer_token(request)
    if header_token == expected or bearer_token == expected:
        return

    raise HTTPException(status_code=403, detail="missing or invalid operator token")
