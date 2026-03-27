"""Operator authentication boundary for the Aegis-Air engine.

Provides token-based access control for mutating API routes.  When the
``AEGIS_AIR_OPERATOR_TOKEN`` environment variable is set, requests to
protected endpoints must include the token as either a Bearer token in
the ``Authorization`` header or a plain value in the ``X-Operator-Token``
header.
"""

from __future__ import annotations

import os

from fastapi import HTTPException, Request

from aegis_engine.logging import get_logger

logger = get_logger(__name__)


def operator_token_enabled() -> bool:
    """Check whether operator-token authentication is active.

    Returns:
        ``True`` if ``AEGIS_AIR_OPERATOR_TOKEN`` is set and non-empty.
    """
    return bool(str(os.getenv("AEGIS_AIR_OPERATOR_TOKEN", "")).strip())


def _read_bearer_token(request: Request) -> str:
    """Extract the Bearer token from an HTTP ``Authorization`` header.

    Args:
        request: The incoming FastAPI request.

    Returns:
        The token string if present, otherwise an empty string.
    """
    authorization: str = str(request.headers.get("authorization", "")).strip()
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


def require_operator_token(request: Request) -> None:
    """Enforce operator-token authentication on a request.

    If ``AEGIS_AIR_OPERATOR_TOKEN`` is not set the check is a no-op.
    Otherwise the request must carry the correct token via either the
    ``X-Operator-Token`` or ``Authorization: Bearer <token>`` header.

    Args:
        request: The incoming FastAPI request.

    Raises:
        HTTPException: 403 if the token is missing or does not match.
    """
    expected: str = str(os.getenv("AEGIS_AIR_OPERATOR_TOKEN", "")).strip()
    if not expected:
        return

    header_token: str = str(request.headers.get("x-operator-token", "")).strip()
    bearer_token: str = _read_bearer_token(request)
    if header_token == expected or bearer_token == expected:
        return

    logger.warning(
        "Operator token rejected",
        extra={"event_type": "auth_rejected"},
    )
    raise HTTPException(status_code=403, detail="missing or invalid operator token")
