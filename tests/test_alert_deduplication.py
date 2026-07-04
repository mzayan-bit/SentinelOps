"""
SentinelOps — Alert Deduplication Tests
=========================================
Verifies that duplicate alerts are suppressed within the cooldown window,
grouped by worker, and correctly created once the cooldown expires.
"""

import time
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from app.models.alert import AlertCreate, AlertType, Severity, AlertStatus
from app.services.alert_service import AlertService
from config.settings import settings


@pytest.fixture
def alert_svc(tmp_path):
    """Fresh AlertService backed by a temp directory."""
    return AlertService(alerts_dir=tmp_path)


def _make_payload(**overrides) -> AlertCreate:
    """Build a default AlertCreate, merging any overrides."""
    defaults = dict(
        camera_id="CAM-01",
        alert_type=AlertType.NO_HELMET,
        severity=Severity.HIGH,
        confidence=0.85,
        worker_id="W-42",
    )
    defaults.update(overrides)
    return AlertCreate(**defaults)


# ------------------------------------------------------------------
# Deduplication within cooldown
# ------------------------------------------------------------------

@patch("app.services.alert_service.settings")
def test_duplicate_within_cooldown_increments_count(mock_settings, tmp_path):
    """Firing the same alert twice within the cooldown should NOT create two records."""
    mock_settings.alert_cooldown_seconds = 60
    mock_settings.alerts_dir = tmp_path
    mock_settings.escalate_to_medium_threshold = 3
    mock_settings.escalate_to_high_threshold = 5
    mock_settings.escalate_to_critical_threshold = 10
    svc = AlertService(alerts_dir=tmp_path)

    payload = _make_payload()

    first = svc.create(payload)
    assert first.duplicate_count == 0
    assert first.last_seen_at is not None

    second = svc.create(payload)

    # Should return the SAME alert, not a new one
    assert second.alert_id == first.alert_id
    assert second.duplicate_count == 1
    assert second.last_seen_at >= first.last_seen_at


@patch("app.services.alert_service.settings")
def test_duplicate_keeps_highest_confidence(mock_settings, tmp_path):
    """Deduplication should keep the maximum confidence seen so far."""
    mock_settings.alert_cooldown_seconds = 60
    mock_settings.alerts_dir = tmp_path
    mock_settings.escalate_to_medium_threshold = 3
    mock_settings.escalate_to_high_threshold = 5
    mock_settings.escalate_to_critical_threshold = 10
    svc = AlertService(alerts_dir=tmp_path)

    first = svc.create(_make_payload(confidence=0.70))
    second = svc.create(_make_payload(confidence=0.95))

    assert second.alert_id == first.alert_id
    assert second.confidence == 0.95


# ------------------------------------------------------------------
# Different workers → separate alerts
# ------------------------------------------------------------------

@patch("app.services.alert_service.settings")
def test_different_worker_creates_new_alert(mock_settings, tmp_path):
    """Alerts from different workers should never be deduplicated together."""
    mock_settings.alert_cooldown_seconds = 60
    mock_settings.alerts_dir = tmp_path
    mock_settings.escalate_to_medium_threshold = 3
    mock_settings.escalate_to_high_threshold = 5
    mock_settings.escalate_to_critical_threshold = 10
    svc = AlertService(alerts_dir=tmp_path)

    a = svc.create(_make_payload(worker_id="W-1"))
    b = svc.create(_make_payload(worker_id="W-2"))

    assert a.alert_id != b.alert_id
    assert a.worker_id == "W-1"
    assert b.worker_id == "W-2"


# ------------------------------------------------------------------
# Cooldown expiry → new alert
# ------------------------------------------------------------------

@patch("app.services.alert_service.settings")
def test_alert_after_cooldown_creates_new(mock_settings, tmp_path):
    """Once the cooldown expires, a new alert record should be created."""
    mock_settings.alert_cooldown_seconds = 1  # 1 second cooldown
    mock_settings.alerts_dir = tmp_path
    svc = AlertService(alerts_dir=tmp_path)

    first = svc.create(_make_payload())

    # Wait for cooldown to expire
    time.sleep(1.1)

    second = svc.create(_make_payload())

    assert second.alert_id != first.alert_id
    assert second.duplicate_count == 0


# ------------------------------------------------------------------
# Cooldown disabled
# ------------------------------------------------------------------

@patch("app.services.alert_service.settings")
def test_cooldown_zero_disables_dedup(mock_settings, tmp_path):
    """Setting cooldown to 0 should disable deduplication entirely."""
    mock_settings.alert_cooldown_seconds = 0
    mock_settings.alerts_dir = tmp_path
    svc = AlertService(alerts_dir=tmp_path)

    a = svc.create(_make_payload())
    b = svc.create(_make_payload())

    assert a.alert_id != b.alert_id


# ------------------------------------------------------------------
# Resolved alerts should not be deduplicated
# ------------------------------------------------------------------

@patch("app.services.alert_service.settings")
def test_resolved_alert_not_deduplicated(mock_settings, tmp_path):
    """A resolved alert should not absorb new duplicates."""
    mock_settings.alert_cooldown_seconds = 60
    mock_settings.alerts_dir = tmp_path
    mock_settings.escalate_to_medium_threshold = 3
    mock_settings.escalate_to_high_threshold = 5
    mock_settings.escalate_to_critical_threshold = 10
    svc = AlertService(alerts_dir=tmp_path)

    first = svc.create(_make_payload())

    # Manually resolve it via the index
    from app.models.alert import AlertResolve
    svc.resolve(first.alert_id, AlertResolve(notes="done"))

    second = svc.create(_make_payload())

    assert second.alert_id != first.alert_id


# ------------------------------------------------------------------
# Multiple rapid duplicates
# ------------------------------------------------------------------

@patch("app.services.alert_service.settings")
def test_many_duplicates_increment_correctly(mock_settings, tmp_path):
    """Firing 5 rapid duplicates should result in count=4 on one alert."""
    mock_settings.alert_cooldown_seconds = 60
    mock_settings.alerts_dir = tmp_path
    mock_settings.escalate_to_medium_threshold = 3
    mock_settings.escalate_to_high_threshold = 5
    mock_settings.escalate_to_critical_threshold = 10
    svc = AlertService(alerts_dir=tmp_path)

    payload = _make_payload()
    results = [svc.create(payload) for _ in range(5)]

    # All should be the same alert
    ids = {r.alert_id for r in results}
    assert len(ids) == 1

    final = results[-1]
    assert final.duplicate_count == 4
