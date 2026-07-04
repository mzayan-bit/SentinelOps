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
    Severity,
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

    # -- Deduplication -----------------------------------------------------

    def _find_duplicate(self, payload: AlertCreate) -> str | None:
        """Find an existing alert that matches the dedup key within cooldown.

        Dedup key: (camera_id, alert_type, worker_id).
        Returns the alert_id of the duplicate, or None.
        """
        cooldown = settings.alert_cooldown_seconds
        if cooldown <= 0:
            return None

        now = datetime.now(timezone.utc)

        for alert_id, entry in self._index.items():
            # Match on dedup key
            if entry.get("camera_id") != payload.camera_id:
                continue
            if entry.get("alert_type") != payload.alert_type.value:
                continue
            if entry.get("worker_id") != payload.worker_id:
                continue
            # Only deduplicate against active (non-resolved) alerts
            if entry.get("status") in (AlertStatus.RESOLVED.value, AlertStatus.FALSE_POSITIVE.value):
                continue

            # Check cooldown window
            last_seen_str = entry.get("last_seen_at") or entry.get("timestamp")
            if last_seen_str:
                last_seen = datetime.fromisoformat(last_seen_str)
                elapsed = (now - last_seen).total_seconds()
                if elapsed < cooldown:
                    return alert_id

        return None

    def _build_index_entry(self, alert: Alert) -> dict[str, Any]:
        """Build a consistent index entry from an Alert object."""
        return {
            "timestamp": alert.timestamp.isoformat(),
            "camera_id": alert.camera_id,
            "alert_type": alert.alert_type.value,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "confidence": alert.confidence,
            "assigned_to": alert.assigned_to,
            "worker_id": alert.worker_id,
            "duplicate_count": alert.duplicate_count,
            "last_seen_at": alert.last_seen_at.isoformat() if alert.last_seen_at else None,
        }

    # -- CRUD --------------------------------------------------------------

    def create(self, payload: AlertCreate) -> Alert:
        """Create a new alert, or deduplicate into an existing one.

        If a matching alert exists within the cooldown window, the existing
        alert's ``duplicate_count`` is incremented and ``last_seen_at`` is
        updated instead of creating a new record.

        Returns the full ``Alert`` (new or updated).
        """
        now = datetime.now(timezone.utc)

        with self._lock:
            # ---- Deduplication check ----
            dup_id = self._find_duplicate(payload)
            if dup_id is not None:
                existing = self._read_alert(dup_id)
                alert_dict = existing.to_dict()
                alert_dict["duplicate_count"] = existing.duplicate_count + 1
                alert_dict["last_seen_at"] = now.isoformat()
                
                # Escalation Logic
                new_count = alert_dict["duplicate_count"]
                current_severity = existing.severity
                escalated = False
                
                if new_count >= settings.escalate_to_critical_threshold and current_severity != Severity.CRITICAL:
                    alert_dict["severity"] = Severity.CRITICAL.value
                    escalated = True
                elif new_count >= settings.escalate_to_high_threshold and current_severity not in (Severity.HIGH, Severity.CRITICAL):
                    alert_dict["severity"] = Severity.HIGH.value
                    escalated = True
                elif new_count >= settings.escalate_to_medium_threshold and current_severity == Severity.LOW:
                    alert_dict["severity"] = Severity.MEDIUM.value
                    escalated = True
                    
                # Update confidence to the latest (higher-is-better)
                alert_dict["confidence"] = max(existing.confidence, payload.confidence)
                updated = Alert(**alert_dict)
                self._save_alert(updated)
                self._index[dup_id] = self._build_index_entry(updated)
                self._save_index()

                logger.info(
                    "Alert deduplicated: %s (count=%d) camera=%s worker=%s%s",
                    dup_id,
                    updated.duplicate_count,
                    updated.camera_id,
                    updated.worker_id,
                    f" [ESCALATED to {updated.severity.value}]" if escalated else ""
                )
                
                if escalated:
                    self._trigger_notifications(updated)
                    
                return updated

        # ---- No duplicate: create a fresh alert ----
        alert = Alert(
            alert_id=self._generate_id(),
            timestamp=now,
            status=AlertStatus.NEW,
            last_seen_at=now,
            **payload.model_dump(),
        )

        with self._lock:
            self._save_alert(alert)
            self._index[alert.alert_id] = self._build_index_entry(alert)
            self._save_index()

        logger.info(
            "Alert created: %s [%s] severity=%s camera=%s worker=%s",
            alert.alert_id,
            alert.alert_type.value,
            alert.severity.value,
            alert.camera_id,
            alert.worker_id,
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

        self._trigger_notifications(alert)

        return alert

    def _trigger_notifications(self, alert: Alert) -> None:
        """Fire-and-forget background notifications for the alert."""
        from app.services.task_worker import task_worker
        from app.services.email_service import email_service
        from app.services.slack_service import slack_service
        from app.services.teams_service import teams_service

        task_worker.submit(
            email_service.send_alert_notification, 
            alert, 
            task_type="email_notification"
        )
        task_worker.submit(
            slack_service.send_alert_notification,
            alert,
            task_type="slack_notification"
        )
        task_worker.submit(
            teams_service.send_alert_notification,
            alert,
            task_type="teams_notification"
        )

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
            self._index[alert_id] = self._build_index_entry(updated)
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
            self._index[alert_id] = self._build_index_entry(updated)
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
