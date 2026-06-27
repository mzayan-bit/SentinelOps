"""
SentinelOps — Alert Service
==============================
Business-logic and persistence layer for the Alert Management system.

Alerts are stored as JSON files under ``artifacts/alerts/``.
A master index (``alerts_index.json``) provides fast look-ups without
scanning every file.

Thread-safety is achieved via ``threading.Lock``.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models.alert import (
    Alert,
    AlertCreate,
    AlertFilter,
    AlertResolve,
    AlertStatus,
    AlertStatsResponse,
    AlertUpdate,
    STATUS_TRANSITIONS,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("sentinelops.alert_service")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
from config.settings import settings

DEFAULT_ALERTS_DIR = settings.alerts_dir
INDEX_FILE = "alerts_index.json"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class AlertNotFoundError(Exception):
    """Raised when a requested alert does not exist."""


class InvalidTransitionError(Exception):
    """Raised when an illegal status transition is attempted."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class AlertService:
    """JSON-file-backed alert management service.

    Parameters
    ----------
    alerts_dir : Path
        Root directory for alert storage (default: ``artifacts/alerts``).
    """

    def __init__(self, alerts_dir: Path = DEFAULT_ALERTS_DIR) -> None:
        self._dir = alerts_dir
        self._index_path = alerts_dir / INDEX_FILE
        self._lock = threading.Lock()

        self._dir.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, dict[str, Any]] = self._load_index()

    # -- Persistence -------------------------------------------------------

    def _load_index(self) -> dict[str, dict[str, Any]]:
        if self._index_path.exists():
            return json.loads(self._index_path.read_text(encoding="utf-8"))
        return {}

    def _save_index(self) -> None:
        self._index_path.write_text(
            json.dumps(self._index, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def _alert_path(self, alert_id: str) -> Path:
        return self._dir / f"{alert_id}.json"

    def _save_alert(self, alert: Alert) -> None:
        self._alert_path(alert.alert_id).write_text(
            json.dumps(alert.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _read_alert(self, alert_id: str) -> Alert:
        path = self._alert_path(alert_id)
        if not path.exists():
            raise AlertNotFoundError(f"Alert '{alert_id}' not found.")
        data = json.loads(path.read_text(encoding="utf-8"))
        return Alert(**data)

    @staticmethod
    def _generate_id() -> str:
        """Generate a unique, sortable alert ID."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        short_uuid = uuid.uuid4().hex[:8]
        return f"ALR-{ts}-{short_uuid}"

    # -- CRUD --------------------------------------------------------------

    def create(self, payload: AlertCreate) -> Alert:
        """Create and persist a new alert.

        Returns the full ``Alert`` with generated ``alert_id`` and timestamp.
        """
        alert = Alert(
            alert_id=self._generate_id(),
            timestamp=datetime.now(timezone.utc),
            status=AlertStatus.NEW,
            **payload.model_dump(),
        )

        with self._lock:
            self._save_alert(alert)
            self._index[alert.alert_id] = {
                "timestamp": alert.timestamp.isoformat(),
                "camera_id": alert.camera_id,
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "confidence": alert.confidence,
                "assigned_to": alert.assigned_to,
            }
            self._save_index()

        logger.info(
            "Alert created: %s [%s] severity=%s camera=%s",
            alert.alert_id,
            alert.alert_type.value,
            alert.severity.value,
            alert.camera_id,
        )

        # Fire-and-forget: persist to PostgreSQL in the background
        from app.services.violation_persistence import persist_violation_async

        persist_violation_async(
            alert_id=alert.alert_id,
            camera_id=alert.camera_id,
            alert_type=alert.alert_type.value,
            severity=alert.severity.value,
            confidence=alert.confidence,
            status=alert.status.value,
            timestamp=alert.timestamp,
            image_path=alert.image_path,
            video_clip_path=alert.video_clip_path,
            notes=alert.notes,
            assigned_to=alert.assigned_to,
        )

        # Fire-and-forget: send email notification
        from app.services.email_service import email_service
        from app.services.task_worker import task_worker
        task_worker.submit(
            email_service.send_alert_notification, 
            alert, 
            task_type="email_notification"
        )

        # Fire-and-forget: send Slack notification
        from app.services.slack_service import slack_service
        task_worker.submit(
            slack_service.send_alert_notification,
            alert,
            task_type="slack_notification"
        )

        # Fire-and-forget: send Teams notification
        from app.services.teams_service import teams_service
        task_worker.submit(
            teams_service.send_alert_notification,
            alert,
            task_type="teams_notification"
        )

        return alert

    def get(self, alert_id: str) -> Alert:
        """Retrieve a single alert by ID.

        Raises
        ------
        AlertNotFoundError
        """
        with self._lock:
            return self._read_alert(alert_id)

    def update(self, alert_id: str, payload: AlertUpdate) -> Alert:
        """Partially update an existing alert.

        Raises
        ------
        AlertNotFoundError
        InvalidTransitionError
            If the requested status change violates the workflow.
        """
        with self._lock:
            alert = self._read_alert(alert_id)
            update_data = payload.model_dump(exclude_unset=True)

            # Validate status transition
            if "status" in update_data and update_data["status"] is not None:
                new_status = AlertStatus(update_data["status"])
                allowed = STATUS_TRANSITIONS.get(alert.status, set())
                if new_status not in allowed:
                    raise InvalidTransitionError(
                        f"Cannot transition from '{alert.status.value}' "
                        f"to '{new_status.value}'. "
                        f"Allowed: {[s.value for s in allowed]}"
                    )

            # Apply updates
            alert_dict = alert.to_dict()
            alert_dict.update(update_data)
            updated = Alert(**alert_dict)

            self._save_alert(updated)
            self._index[alert_id] = {
                "timestamp": updated.timestamp.isoformat(),
                "camera_id": updated.camera_id,
                "alert_type": updated.alert_type.value,
                "severity": updated.severity.value,
                "status": updated.status.value,
                "confidence": updated.confidence,
                "assigned_to": updated.assigned_to,
            }
            self._save_index()

        logger.info("Alert updated: %s", alert_id)
        return updated

    def delete(self, alert_id: str) -> None:
        """Delete an alert.

        Raises
        ------
        AlertNotFoundError
        """
        with self._lock:
            path = self._alert_path(alert_id)
            if not path.exists():
                raise AlertNotFoundError(f"Alert '{alert_id}' not found.")
            path.unlink()
            self._index.pop(alert_id, None)
            self._save_index()

        logger.info("Alert deleted: %s", alert_id)

    # -- Actions -----------------------------------------------------------

    def assign(self, alert_id: str, assigned_to: str) -> Alert:
        """Assign an alert to an investigator and set status to Investigating."""
        return self.update(
            alert_id,
            AlertUpdate(
                assigned_to=assigned_to,
                status=AlertStatus.INVESTIGATING,
            ),
        )

    def resolve(self, alert_id: str, payload: AlertResolve) -> Alert:
        """Resolve (or mark as false-positive) an alert."""
        new_status = (
            AlertStatus.FALSE_POSITIVE if payload.false_positive else AlertStatus.RESOLVED
        )
        with self._lock:
            alert = self._read_alert(alert_id)

            allowed = STATUS_TRANSITIONS.get(alert.status, set())
            if new_status not in allowed:
                raise InvalidTransitionError(
                    f"Cannot transition from '{alert.status.value}' "
                    f"to '{new_status.value}'. "
                    f"Allowed: {[s.value for s in allowed]}"
                )

            alert_dict = alert.to_dict()
            alert_dict["status"] = new_status.value
            alert_dict["resolved_at"] = datetime.now(timezone.utc).isoformat()
            if payload.notes:
                existing = alert_dict.get("notes", "")
                separator = "\n---\n" if existing else ""
                alert_dict["notes"] = f"{existing}{separator}[RESOLVED] {payload.notes}"

            updated = Alert(**alert_dict)
            self._save_alert(updated)
            self._index[alert_id] = {
                "timestamp": updated.timestamp.isoformat(),
                "camera_id": updated.camera_id,
                "alert_type": updated.alert_type.value,
                "severity": updated.severity.value,
                "status": updated.status.value,
                "confidence": updated.confidence,
                "assigned_to": updated.assigned_to,
            }
            self._save_index()

        logger.info("Alert resolved: %s → %s", alert_id, new_status.value)
        return updated

    # -- Listing & filtering -----------------------------------------------

    def list_alerts(self, filters: AlertFilter | None = None) -> list[Alert]:
        """Return all alerts matching the given filters, newest first."""
        with self._lock:
            ids = list(self._index.keys())

        # Pre-filter using the index (fast)
        if filters:
            ids = self._prefilter(ids, filters)

        # Load full records
        alerts: list[Alert] = []
        for aid in ids:
            try:
                alerts.append(self._read_alert(aid))
            except AlertNotFoundError:
                continue

        # Post-filter date range (requires full timestamp)
        if filters:
            if filters.date_from:
                alerts = [a for a in alerts if a.timestamp >= filters.date_from]
            if filters.date_to:
                alerts = [a for a in alerts if a.timestamp <= filters.date_to]

        # Sort newest first
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        return alerts

    def _prefilter(self, ids: list[str], f: AlertFilter) -> list[str]:
        """Fast pre-filtering using the in-memory index."""
        result: list[str] = []
        for aid in ids:
            entry = self._index.get(aid)
            if entry is None:
                continue
            if f.severity and entry.get("severity") != f.severity.value:
                continue
            if f.status and entry.get("status") != f.status.value:
                continue
            if f.alert_type and entry.get("alert_type") != f.alert_type.value:
                continue
            if f.camera_id and entry.get("camera_id") != f.camera_id:
                continue
            result.append(aid)
        return result

    # -- Statistics --------------------------------------------------------

    def stats(self) -> AlertStatsResponse:
        """Aggregate statistics across all alerts."""
        entries = list(self._index.values())
        return AlertStatsResponse(
            total=len(entries),
            by_severity=dict(Counter(e["severity"] for e in entries)),
            by_status=dict(Counter(e["status"] for e in entries)),
            by_type=dict(Counter(e["alert_type"] for e in entries)),
        )
