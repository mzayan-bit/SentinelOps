from __future__ import annotations

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from logging import LogRecord
from typing import Any

from app.core.request_context import get_camera_id, get_request_id, get_user_id


class JsonLogFormatter(logging.Formatter):
    """Minimal JSON formatter suitable for container and log pipeline ingestion."""

    def format(self, record: LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "severity": record.levelname,
            "service": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or get_request_id(),
            "user_id": getattr(record, "user_id", None) or get_user_id(),
            "camera_id": getattr(record, "camera_id", None) or get_camera_id(),
        }

        for key in ("endpoint", "method", "status_code", "latency_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        if record.exc_info:
            payload["error_stack"] = "".join(traceback.format_exception(*record.exc_info)).strip()

        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(level: str, json_logs: bool = True) -> None:
    handler = logging.StreamHandler(sys.stdout)
    if json_logs:
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.addHandler(handler)

    for noisy_logger in ("aiosqlite", "sqlalchemy.engine"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
