"""
SentinelOps — Violation Persistence Layer
============================================
Writes violation events to PostgreSQL asynchronously, using a background
thread so that the existing synchronous AlertService is not modified.

This module is imported by the AlertService to fire-and-forget DB writes
after every ``create()`` call. If the database is unavailable, the write
fails silently (logged as a warning) and the JSON-based storage remains
the source of truth.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime

from app.db.database import AsyncSessionLocal
from app.db.models import ViolationModel

logger = logging.getLogger("sentinelops.violation_persistence")

# ---------------------------------------------------------------------------
# Internal async writer
# ---------------------------------------------------------------------------

async def _persist_violation(
    alert_id: str,
    camera_id: str,
    alert_type: str,
    severity: str,
    confidence: float,
    status: str,
    timestamp: datetime,
    image_path: str | None,
    video_clip_path: str | None,
    notes: str,
    assigned_to: str | None,
) -> None:
    """Insert a single violation row into the database."""
    try:
        async with AsyncSessionLocal() as session:
            violation = ViolationModel(
                id=alert_id,
                camera_id=camera_id,
                alert_type=alert_type,
                severity=severity,
                confidence=confidence,
                status=status,
                timestamp=timestamp,
                image_path=image_path,
                video_clip_path=video_clip_path,
                notes=notes,
                assigned_to=assigned_to,
            )
            session.add(violation)
            await session.commit()
            logger.debug("Violation persisted to DB: %s", alert_id)
    except Exception as exc:
        logger.warning("Failed to persist violation %s to DB: %s", alert_id, exc)


# ---------------------------------------------------------------------------
# Public sync API (called from AlertService)
# ---------------------------------------------------------------------------

def persist_violation_async(
    alert_id: str,
    camera_id: str,
    alert_type: str,
    severity: str,
    confidence: float,
    status: str,
    timestamp: datetime,
    image_path: str | None = None,
    video_clip_path: str | None = None,
    notes: str = "",
    assigned_to: str | None = None,
) -> None:
    """
    Fire-and-forget: schedule the DB write on a background thread.
    
    This is safe to call from synchronous code. If the event loop is
    unavailable or the database is down, the failure is logged and the
    caller is not affected.
    """
    def _run() -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                _persist_violation(
                    alert_id=alert_id,
                    camera_id=camera_id,
                    alert_type=alert_type,
                    severity=severity,
                    confidence=confidence,
                    status=status,
                    timestamp=timestamp,
                    image_path=image_path,
                    video_clip_path=video_clip_path,
                    notes=notes,
                    assigned_to=assigned_to,
                )
            )
        except Exception as exc:
            logger.warning("Background violation persist failed: %s", exc)
        finally:
            loop.close()

    thread = threading.Thread(target=_run, daemon=True, name="violation-persist")
    thread.start()
