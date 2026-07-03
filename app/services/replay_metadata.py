"""
SentinelOps — Incident Replay Metadata Service
==================================================
Generates and stores replay metadata for incident recordings, associating
start/end timestamps with violation records to support future playback.

This module handles **metadata only** — no video player or rendering logic.

Usage::

    from app.services.replay_metadata import replay_metadata_service

    meta = replay_metadata_service.create(
        incident_id="...",
        camera_id="CAM-01",
        violation_data={"summary": {...}},
    )
    replay_metadata_service.get(meta.replay_id)
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sentinelops.replay_metadata")

# Default buffer: 10 s before and 10 s after the trigger
DEFAULT_PRE_SECONDS: float = 10.0
DEFAULT_POST_SECONDS: float = 10.0


# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------
@dataclass
class ReplayMetadata:
    """Immutable metadata record for a single incident replay segment."""

    replay_id: str
    incident_id: str
    camera_id: str
    trigger_timestamp: float
    replay_start: float
    replay_end: float
    duration_seconds: float
    violation_data: dict[str, Any] = field(default_factory=dict)
    alert_ids: list[str] = field(default_factory=list)
    worker_ids: list[str] = field(default_factory=list)
    created_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_id": self.replay_id,
            "incident_id": self.incident_id,
            "camera_id": self.camera_id,
            "trigger_timestamp": self.trigger_timestamp,
            "replay_start": self.replay_start,
            "replay_end": self.replay_end,
            "duration_seconds": round(self.duration_seconds, 2),
            "violation_data": self.violation_data,
            "alert_ids": list(self.alert_ids),
            "worker_ids": list(self.worker_ids),
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class ReplayMetadataService:
    """Thread-safe, in-memory store for incident replay metadata.

    Parameters
    ----------
    pre_seconds : float
        Seconds of context to include *before* the trigger event.
    post_seconds : float
        Seconds of context to include *after* the trigger event.
    """

    def __init__(
        self,
        pre_seconds: float = DEFAULT_PRE_SECONDS,
        post_seconds: float = DEFAULT_POST_SECONDS,
    ) -> None:
        self._pre = pre_seconds
        self._post = post_seconds
        self._store: dict[str, ReplayMetadata] = {}
        self._by_incident: dict[str, list[str]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create(
        self,
        incident_id: str,
        camera_id: str,
        trigger_timestamp: float | None = None,
        violation_data: dict[str, Any] | None = None,
        alert_ids: list[str] | None = None,
        worker_ids: list[str] | None = None,
        pre_seconds: float | None = None,
        post_seconds: float | None = None,
    ) -> ReplayMetadata:
        """Generate and store replay metadata for an incident.

        Parameters
        ----------
        incident_id
            The ID of the associated incident / violation record.
        camera_id
            Source camera identifier.
        trigger_timestamp
            Epoch time of the violation trigger. Defaults to ``time.time()``.
        violation_data
            Arbitrary violation context (summary dict, PPE status, etc.).
        alert_ids
            Optional list of associated alert IDs.
        worker_ids
            Optional list of tracked worker IDs involved.
        pre_seconds / post_seconds
            Per-call overrides for the replay window (defaults to service-level).

        Returns
        -------
        ReplayMetadata
        """
        now = time.time()
        trigger = trigger_timestamp if trigger_timestamp is not None else now
        pre = pre_seconds if pre_seconds is not None else self._pre
        post = post_seconds if post_seconds is not None else self._post

        replay_start = trigger - pre
        replay_end = trigger + post
        duration = replay_end - replay_start

        meta = ReplayMetadata(
            replay_id=f"RPL-{uuid.uuid4().hex[:12]}",
            incident_id=incident_id,
            camera_id=camera_id,
            trigger_timestamp=trigger,
            replay_start=replay_start,
            replay_end=replay_end,
            duration_seconds=duration,
            violation_data=violation_data or {},
            alert_ids=alert_ids or [],
            worker_ids=worker_ids or [],
            created_at=now,
        )

        with self._lock:
            self._store[meta.replay_id] = meta
            self._by_incident.setdefault(incident_id, []).append(meta.replay_id)

        logger.info(
            "Replay metadata created: %s for incident %s (%.1fs window)",
            meta.replay_id,
            incident_id,
            duration,
        )
        return meta

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, replay_id: str) -> ReplayMetadata | None:
        """Retrieve a single replay record by ID."""
        with self._lock:
            return self._store.get(replay_id)

    def get_by_incident(self, incident_id: str) -> list[ReplayMetadata]:
        """Return all replay records associated with a given incident."""
        with self._lock:
            ids = self._by_incident.get(incident_id, [])
            return [self._store[rid] for rid in ids if rid in self._store]

    def get_by_camera(self, camera_id: str) -> list[ReplayMetadata]:
        """Return all replay records for a specific camera, newest first."""
        with self._lock:
            results = [m for m in self._store.values() if m.camera_id == camera_id]
        results.sort(key=lambda m: m.trigger_timestamp, reverse=True)
        return results

    def list_all(self) -> list[ReplayMetadata]:
        """Return every replay record, newest first."""
        with self._lock:
            results = list(self._store.values())
        results.sort(key=lambda m: m.trigger_timestamp, reverse=True)
        return results

    # ------------------------------------------------------------------
    # Management
    # ------------------------------------------------------------------

    def delete(self, replay_id: str) -> bool:
        """Remove a single replay record. Returns ``True`` if found."""
        with self._lock:
            meta = self._store.pop(replay_id, None)
            if meta is None:
                return False
            ids = self._by_incident.get(meta.incident_id, [])
            if replay_id in ids:
                ids.remove(replay_id)
            return True

    def clear(self) -> None:
        """Remove all replay metadata."""
        with self._lock:
            self._store.clear()
            self._by_incident.clear()
        logger.info("All replay metadata cleared.")


# Module-level singleton
replay_metadata_service = ReplayMetadataService()
