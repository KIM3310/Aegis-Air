"""Structured logging for the Aegis-Air engine.

Provides a pre-configured logger with JSON-formatted output and incident
tracking context.  All engine modules should import ``get_logger`` from
this module instead of using ``logging.getLogger`` directly.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any


class StructuredFormatter(logging.Formatter):
    """JSON log formatter that attaches incident-tracking fields.

    Each log record is emitted as a single JSON line with the following
    guaranteed keys: ``timestamp``, ``level``, ``logger``, ``message``.
    Extra fields passed via the ``extra`` dict are merged at the top level.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format *record* as a JSON string.

        Args:
            record: The log record to format.

        Returns:
            A single-line JSON string.
        """
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Merge any extra fields that were passed via `extra=`
        for key in ("incident_id", "event_type", "service_name",
                     "severity", "failure_bucket", "confidence",
                     "correlation_id", "probe_number", "status_code",
                     "latency_ms", "error_class"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        if record.exc_info and record.exc_info[1] is not None:
            payload["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
            }

        return json.dumps(payload, default=str)


def get_logger(name: str, *, level: int = logging.INFO) -> logging.Logger:
    """Return a logger configured with structured JSON output.

    Args:
        name: Logger name, typically ``__name__`` of the calling module.
        level: Minimum log level (default ``INFO``).

    Returns:
        A :class:`logging.Logger` with a :class:`StructuredFormatter`
        attached to its ``stderr`` handler.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for tracing an incident through the pipeline.

    Returns:
        A string UUID suitable for use as a correlation/trace ID.
    """
    return str(uuid.uuid4())
