"""
SentinelOps — Analytics Service Unit Tests
=============================================
Tests for ``AnalyticsService`` business logic.

Each test creates an isolated ``AlertService`` backed by ``tmp_path``,
seeds it with controlled alert data, then verifies analytics computations.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.alert import AlertCreate, AlertType, Severity
from app.services.alert_service import AlertService
from app.services.analytics_service import AnalyticsService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_alert_service(tmp_path) -> AlertService:
    """Create an AlertService rooted in a temporary directory."""
    return AlertService(alerts_dir=tmp_path / "alerts")


def _seed_alert(
    svc: AlertService,
    camera_id: str = "cam_01",
    alert_type: AlertType = AlertType.NO_HELMET,
    severity: Severity = Severity.HIGH,
    confidence: float = 0.9,
) -> None:
    """Create a single alert using the service."""
    svc.create(
        AlertCreate(
            camera_id=camera_id,
            alert_type=alert_type,
            severity=severity,
            confidence=confidence,
        )
    )


def _make_services(tmp_path):
    """Return (AlertService, AnalyticsService) pair."""
    alert_svc = _make_alert_service(tmp_path)
    analytics_svc = AnalyticsService(alert_svc)
    return alert_svc, analytics_svc


# ---------------------------------------------------------------------------
# violations_per_day
# ---------------------------------------------------------------------------
class TestViolationsPerDay:
    def test_basic_grouping(self, tmp_path):
        alert_svc, analytics = _make_services(tmp_path)

        # Seed 3 alerts (all created "now", same day)
        for _ in range(3):
            _seed_alert(alert_svc)

        result = analytics.violations_per_day()
        assert result.total == 3
        assert len(result.data) == 1  # all same day
        assert result.data[0].count == 3

    def test_empty(self, tmp_path):
        _, analytics = _make_services(tmp_path)

        result = analytics.violations_per_day()
        assert result.total == 0
        assert result.data == []

    def test_date_format(self, tmp_path):
        alert_svc, analytics = _make_services(tmp_path)
        _seed_alert(alert_svc)

        result = analytics.violations_per_day()
        date_str = result.data[0].date
        # Verify YYYY-MM-DD format
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        assert parsed is not None


# ---------------------------------------------------------------------------
# violations_per_camera
# ---------------------------------------------------------------------------
class TestViolationsPerCamera:
    def test_grouping_and_sort(self, tmp_path):
        alert_svc, analytics = _make_services(tmp_path)

        # cam_02 gets 3, cam_01 gets 1 → cam_02 should appear first
        _seed_alert(alert_svc, camera_id="cam_01")
        for _ in range(3):
            _seed_alert(alert_svc, camera_id="cam_02")

        result = analytics.violations_per_camera()
        assert result.total_cameras == 2
        assert len(result.data) == 2
        # Sorted descending by count
        assert result.data[0].camera_id == "cam_02"
        assert result.data[0].count == 3
        assert result.data[1].camera_id == "cam_01"
        assert result.data[1].count == 1

    def test_single_camera(self, tmp_path):
        alert_svc, analytics = _make_services(tmp_path)
        _seed_alert(alert_svc, camera_id="cam_99")

        result = analytics.violations_per_camera()
        assert result.total_cameras == 1
        assert result.data[0].camera_id == "cam_99"

    def test_empty(self, tmp_path):
        _, analytics = _make_services(tmp_path)

        result = analytics.violations_per_camera()
        assert result.total_cameras == 0
        assert result.data == []


# ---------------------------------------------------------------------------
# compliance_rate
# ---------------------------------------------------------------------------
class TestComplianceRate:
    def test_all_compliant(self, tmp_path):
        """Non-PPE alert types → 100% compliance."""
        alert_svc, analytics = _make_services(tmp_path)
        # Loitering is NOT a PPE violation
        _seed_alert(alert_svc, alert_type=AlertType.LOITERING)
        _seed_alert(alert_svc, alert_type=AlertType.RESTRICTED_AREA_ENTRY)

        result = analytics.compliance_rate()
        assert result.total_checks == 2
        assert result.compliant == 2
        assert result.non_compliant == 0
        assert result.compliance_rate == 1.0

    def test_mixed(self, tmp_path):
        """Mix of PPE and non-PPE alerts."""
        alert_svc, analytics = _make_services(tmp_path)
        # 2 PPE violations
        _seed_alert(alert_svc, alert_type=AlertType.NO_HELMET)
        _seed_alert(alert_svc, alert_type=AlertType.NO_VEST)
        # 2 non-PPE
        _seed_alert(alert_svc, alert_type=AlertType.LOITERING)
        _seed_alert(alert_svc, alert_type=AlertType.PERSON_DETECTED)

        result = analytics.compliance_rate()
        assert result.total_checks == 4
        assert result.non_compliant == 2
        assert result.compliant == 2
        assert result.compliance_rate == 0.5

    def test_all_non_compliant(self, tmp_path):
        """All alerts are PPE violations → 0% compliance."""
        alert_svc, analytics = _make_services(tmp_path)
        _seed_alert(alert_svc, alert_type=AlertType.NO_HELMET)
        _seed_alert(alert_svc, alert_type=AlertType.NO_VEST)
        _seed_alert(alert_svc, alert_type=AlertType.NO_HELMET)

        result = analytics.compliance_rate()
        assert result.total_checks == 3
        assert result.non_compliant == 3
        assert result.compliance_rate == 0.0

    def test_no_alerts(self, tmp_path):
        """Empty store → 100% compliance by convention."""
        _, analytics = _make_services(tmp_path)

        result = analytics.compliance_rate()
        assert result.total_checks == 0
        assert result.compliance_rate == 1.0


# ---------------------------------------------------------------------------
# hourly_trends
# ---------------------------------------------------------------------------
class TestHourlyTrends:
    def test_full_24_hours(self, tmp_path):
        """Always returns 24 entries, even with sparse data."""
        alert_svc, analytics = _make_services(tmp_path)
        _seed_alert(alert_svc)

        result = analytics.hourly_trends()
        assert len(result.data) == 24
        # Hours 0–23
        hours = [entry.hour for entry in result.data]
        assert hours == list(range(24))

    def test_counts_correct(self, tmp_path):
        alert_svc, analytics = _make_services(tmp_path)
        for _ in range(5):
            _seed_alert(alert_svc)

        result = analytics.hourly_trends()
        total = sum(entry.count for entry in result.data)
        assert total == 5

    def test_empty(self, tmp_path):
        _, analytics = _make_services(tmp_path)

        result = analytics.hourly_trends()
        assert len(result.data) == 24
        assert all(entry.count == 0 for entry in result.data)


# ---------------------------------------------------------------------------
# top_violation_types
# ---------------------------------------------------------------------------
class TestTopViolationTypes:
    def test_ordering(self, tmp_path):
        alert_svc, analytics = _make_services(tmp_path)

        # 3 × No Helmet, 2 × Loitering, 1 × No Vest
        for _ in range(3):
            _seed_alert(alert_svc, alert_type=AlertType.NO_HELMET)
        for _ in range(2):
            _seed_alert(alert_svc, alert_type=AlertType.LOITERING)
        _seed_alert(alert_svc, alert_type=AlertType.NO_VEST)

        result = analytics.top_violation_types()
        assert len(result.data) == 3
        assert result.data[0].violation_type == AlertType.NO_HELMET.value
        assert result.data[0].count == 3
        assert result.data[1].violation_type == AlertType.LOITERING.value
        assert result.data[1].count == 2
        assert result.data[2].violation_type == AlertType.NO_VEST.value
        assert result.data[2].count == 1

    def test_limit(self, tmp_path):
        alert_svc, analytics = _make_services(tmp_path)

        for alert_type in [AlertType.NO_HELMET, AlertType.NO_VEST, AlertType.LOITERING]:
            _seed_alert(alert_svc, alert_type=alert_type)

        result = analytics.top_violation_types(limit=2)
        assert len(result.data) == 2

    def test_empty(self, tmp_path):
        _, analytics = _make_services(tmp_path)

        result = analytics.top_violation_types()
        assert result.total == 0
        assert result.data == []


# ---------------------------------------------------------------------------
# summary (combined)
# ---------------------------------------------------------------------------
class TestSummary:
    def test_contains_all_metrics(self, tmp_path):
        alert_svc, analytics = _make_services(tmp_path)
        _seed_alert(alert_svc)

        result = analytics.summary()
        assert result.violations_per_day is not None
        assert result.violations_per_camera is not None
        assert result.compliance_rate is not None
        assert result.hourly_trends is not None
        assert result.top_violation_types is not None

    def test_consistency(self, tmp_path):
        """Summary sub-metrics should be consistent with each other."""
        alert_svc, analytics = _make_services(tmp_path)
        for _ in range(4):
            _seed_alert(alert_svc)

        result = analytics.summary()
        # Total across days == total across cameras
        assert result.violations_per_day.total == 4
        assert (
            sum(c.count for c in result.violations_per_camera.data) == 4
        )
        assert result.compliance_rate.total_checks == 4


# ---------------------------------------------------------------------------
# Date range filtering
# ---------------------------------------------------------------------------
class TestDateRangeFiltering:
    def test_filters_applied(self, tmp_path):
        alert_svc, analytics = _make_services(tmp_path)

        # Seed alerts (all "now")
        for _ in range(3):
            _seed_alert(alert_svc)

        now = datetime.now(timezone.utc)

        # Query for a future range → should return nothing
        future_from = now + timedelta(days=1)
        future_to = now + timedelta(days=2)

        result = analytics.violations_per_day(
            date_from=future_from, date_to=future_to
        )
        assert result.total == 0

    def test_inclusive_range(self, tmp_path):
        alert_svc, analytics = _make_services(tmp_path)

        for _ in range(3):
            _seed_alert(alert_svc)

        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)
        future = now + timedelta(hours=1)

        result = analytics.violations_per_day(date_from=past, date_to=future)
        assert result.total == 3
