"""
SentinelOps — Analytics Routes Integration Tests
====================================================
Tests for the ``/analytics/*`` HTTP endpoints using FastAPI ``TestClient``.

These tests seed alerts via the ``AlertService`` directly, then hit
the analytics endpoints to verify correct HTTP status codes and response
shapes.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.models.alert import AlertCreate, AlertType, Severity


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def client(tmp_path):
    """Create a TestClient with isolated alert storage.

    We monkey-patch the module-level singletons in ``analytics_routes``
    and ``alert_routes`` to use a temp directory, then restore them after
    the test.
    """
    from app.services.alert_service import AlertService
    from app.services.analytics_service import AnalyticsService
    import app.api.analytics_routes as analytics_mod

    # Create isolated services
    alert_svc = AlertService(alerts_dir=tmp_path / "alerts")
    analytics_svc = AnalyticsService(alert_svc)

    # Patch module globals
    original_alert_svc = analytics_mod._alert_service
    original_analytics_svc = analytics_mod._analytics_service
    analytics_mod._alert_service = alert_svc
    analytics_mod._analytics_service = analytics_svc

    from app.api.app import app

    with TestClient(app) as tc:
        # Expose the alert service for seeding
        tc.alert_service = alert_svc  # type: ignore[attr-defined]
        yield tc

    # Restore
    analytics_mod._alert_service = original_alert_svc
    analytics_mod._analytics_service = original_analytics_svc


def _seed(alert_svc, n: int = 1, **kwargs):
    """Seed n alerts."""
    defaults = dict(
        camera_id="cam_01",
        alert_type=AlertType.NO_HELMET,
        severity=Severity.HIGH,
        confidence=0.9,
    )
    defaults.update(kwargs)
    for _ in range(n):
        alert_svc.create(AlertCreate(**defaults))


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------
class TestViolationsPerDayEndpoint:
    def test_returns_200(self, client):
        _seed(client.alert_service, n=2)
        resp = client.get("/analytics/violations-per-day")
        assert resp.status_code == 200

    def test_response_shape(self, client):
        _seed(client.alert_service, n=2)
        data = client.get("/analytics/violations-per-day").json()
        assert "data" in data
        assert "total" in data
        assert isinstance(data["data"], list)
        assert data["total"] == 2

    def test_empty(self, client):
        data = client.get("/analytics/violations-per-day").json()
        assert data["total"] == 0
        assert data["data"] == []


class TestViolationsPerCameraEndpoint:
    def test_returns_200(self, client):
        _seed(client.alert_service, n=1, camera_id="cam_A")
        _seed(client.alert_service, n=2, camera_id="cam_B")
        resp = client.get("/analytics/violations-per-camera")
        assert resp.status_code == 200

    def test_response_shape(self, client):
        _seed(client.alert_service, n=1, camera_id="cam_X")
        data = client.get("/analytics/violations-per-camera").json()
        assert "data" in data
        assert "total_cameras" in data
        assert data["total_cameras"] == 1
        assert data["data"][0]["camera_id"] == "cam_X"


class TestComplianceRateEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/analytics/compliance-rate")
        assert resp.status_code == 200

    def test_rate_range(self, client):
        _seed(client.alert_service, n=2, alert_type=AlertType.NO_HELMET)
        _seed(client.alert_service, n=2, alert_type=AlertType.LOITERING)
        data = client.get("/analytics/compliance-rate").json()
        assert 0.0 <= data["compliance_rate"] <= 1.0
        assert data["compliance_rate"] == 0.5

    def test_empty_returns_full_compliance(self, client):
        data = client.get("/analytics/compliance-rate").json()
        assert data["compliance_rate"] == 1.0
        assert data["total_checks"] == 0


class TestHourlyTrendsEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/analytics/hourly-trends")
        assert resp.status_code == 200

    def test_24_entries(self, client):
        _seed(client.alert_service, n=3)
        data = client.get("/analytics/hourly-trends").json()
        assert len(data["data"]) == 24
        hours = [e["hour"] for e in data["data"]]
        assert hours == list(range(24))


class TestTopViolationTypesEndpoint:
    def test_returns_200(self, client):
        _seed(client.alert_service, n=1)
        resp = client.get("/analytics/top-violation-types")
        assert resp.status_code == 200

    def test_limit_param(self, client):
        _seed(client.alert_service, n=2, alert_type=AlertType.NO_HELMET)
        _seed(client.alert_service, n=1, alert_type=AlertType.LOITERING)
        _seed(client.alert_service, n=1, alert_type=AlertType.NO_VEST)

        data = client.get("/analytics/top-violation-types?limit=2").json()
        assert len(data["data"]) == 2

    def test_response_shape(self, client):
        _seed(client.alert_service, n=1, alert_type=AlertType.NO_HELMET)
        data = client.get("/analytics/top-violation-types").json()
        assert "data" in data
        assert "total" in data
        entry = data["data"][0]
        assert "violation_type" in entry
        assert "count" in entry


class TestSummaryEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/analytics/summary")
        assert resp.status_code == 200

    def test_contains_all_sections(self, client):
        _seed(client.alert_service, n=3)
        data = client.get("/analytics/summary").json()
        assert "violations_per_day" in data
        assert "violations_per_camera" in data
        assert "compliance_rate" in data
        assert "hourly_trends" in data
        assert "top_violation_types" in data


class TestDateRangeQueryParams:
    def test_with_date_range(self, client):
        _seed(client.alert_service, n=3)
        # Use a future range → expect empty
        resp = client.get(
            "/analytics/violations-per-day",
            params={
                "date_from": "2099-01-01T00:00:00Z",
                "date_to": "2099-12-31T23:59:59Z",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_wide_range_includes_all(self, client):
        _seed(client.alert_service, n=3)
        resp = client.get(
            "/analytics/violations-per-day",
            params={
                "date_from": "2000-01-01T00:00:00Z",
                "date_to": "2099-12-31T23:59:59Z",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 3
