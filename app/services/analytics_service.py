"""
SentinelOps — Analytics Service
==================================
Business-logic layer that computes violation and compliance metrics
from the existing ``AlertService`` alert store.

The service does **not** maintain its own persistence — it queries
``AlertService.list_alerts()`` and aggregates in-memory.

Usage::

    from app.services.alert_service import AlertService
    from app.services.analytics_service import AnalyticsService

    alert_svc = AlertService()
    analytics  = AnalyticsService(alert_svc)
    summary    = analytics.summary()
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from app.models.alert import AlertFilter, AlertType
from app.models.analytics import (
    AnalyticsSummaryResponse,
    ComplianceRateResponse,
    HourlyTrend,
    HourlyTrendsResponse,
    TopViolationTypesResponse,
    ViolationsPerCamera,
    ViolationsPerCameraResponse,
    ViolationsPerDay,
    ViolationsPerDayResponse,
    ViolationTypeCount,
)
from app.services.alert_service import AlertService

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("sentinelops.analytics_service")

# PPE-violation alert types
_PPE_VIOLATION_TYPES: set[AlertType] = {
    AlertType.NO_HELMET,
    AlertType.NO_VEST,
}


class AnalyticsService:
    """Computes analytics metrics from an ``AlertService`` instance.

    Parameters
    ----------
    alert_service : AlertService
        The alert service to query for raw alert data.
    """

    def __init__(self, alert_service: AlertService) -> None:
        self._alert_service = alert_service

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _fetch_alerts(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch alerts as dicts, applying optional date range filters."""
        filters = AlertFilter(date_from=date_from, date_to=date_to)
        alerts = self._alert_service.list_alerts(filters)
        return [a.to_dict() for a in alerts]

    @staticmethod
    def _parse_timestamp(ts: str | datetime) -> datetime:
        """Normalise a timestamp value to a timezone-aware datetime."""
        if isinstance(ts, datetime):
            dt = ts
        else:
            dt = datetime.fromisoformat(ts)
        # Ensure timezone-aware (assume UTC if naive)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    @staticmethod
    def _occurrence_count(alert: dict[str, Any]) -> int:
        """Return total observed occurrences represented by a stored alert."""
        duplicate_count = alert.get("duplicate_count") or 0
        return max(int(duplicate_count) + 1, 1)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------
    def violations_per_day(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> ViolationsPerDayResponse:
        """Group violation counts by calendar date (YYYY-MM-DD)."""
        alerts = self._fetch_alerts(date_from, date_to)
        day_counter: Counter[str] = Counter()

        for alert in alerts:
            ts = self._parse_timestamp(alert["timestamp"])
            day_counter[ts.strftime("%Y-%m-%d")] += self._occurrence_count(alert)

        sorted_days = sorted(day_counter.items(), key=lambda x: x[0])
        data = [ViolationsPerDay(date=d, count=c) for d, c in sorted_days]
        total = sum(c for _, c in sorted_days)

        logger.debug("violations_per_day: %d days, %d total", len(data), total)
        return ViolationsPerDayResponse(data=data, total=total)

    def violations_per_camera(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> ViolationsPerCameraResponse:
        """Group violation counts by camera, sorted descending by count."""
        alerts = self._fetch_alerts(date_from, date_to)
        cam_counter: Counter[str] = Counter()
        for alert in alerts:
            cam_counter[alert["camera_id"]] += self._occurrence_count(alert)

        sorted_cams = cam_counter.most_common()
        data = [ViolationsPerCamera(camera_id=cid, count=cnt) for cid, cnt in sorted_cams]

        logger.debug("violations_per_camera: %d cameras", len(data))
        return ViolationsPerCameraResponse(data=data, total_cameras=len(data))

    def compliance_rate(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> ComplianceRateResponse:
        """Compute PPE compliance rate.

        PPE violations are alerts of type ``No Helmet`` or ``No Vest``.
        Compliance rate = 1 − (ppe_violations / total_alerts).
        If there are no alerts, returns 100 % compliance.
        """
        alerts = self._fetch_alerts(date_from, date_to)
        total = sum(self._occurrence_count(a) for a in alerts)

        if total == 0:
            return ComplianceRateResponse(
                total_checks=0,
                compliant=0,
                non_compliant=0,
                compliance_rate=1.0,
            )

        non_compliant = sum(
            self._occurrence_count(a) for a in alerts
            if a.get("alert_type") in {t.value for t in _PPE_VIOLATION_TYPES}
        )
        compliant = total - non_compliant
        rate = round(compliant / total, 4)

        logger.debug(
            "compliance_rate: %d/%d compliant (%.2f%%)",
            compliant, total, rate * 100,
        )
        return ComplianceRateResponse(
            total_checks=total,
            compliant=compliant,
            non_compliant=non_compliant,
            compliance_rate=rate,
        )

    def hourly_trends(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> HourlyTrendsResponse:
        """Group violations by hour-of-day (0–23).

        Always returns a full 24-entry array, filling missing hours with 0.
        """
        alerts = self._fetch_alerts(date_from, date_to)
        hour_counter: Counter[int] = Counter()

        for alert in alerts:
            ts = self._parse_timestamp(alert["timestamp"])
            hour_counter[ts.hour] += self._occurrence_count(alert)

        data = [
            HourlyTrend(hour=h, count=hour_counter.get(h, 0))
            for h in range(24)
        ]

        # Determine date label if a single-day filter was applied
        date_label: str | None = None
        if date_from and date_to and date_from.date() == date_to.date():
            date_label = date_from.strftime("%Y-%m-%d")

        logger.debug("hourly_trends: peak hour=%s", hour_counter.most_common(1))
        return HourlyTrendsResponse(data=data, date=date_label)

    def top_violation_types(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 10,
    ) -> TopViolationTypesResponse:
        """Return the most frequent violation types, sorted descending."""
        alerts = self._fetch_alerts(date_from, date_to)
        type_counter: Counter[str] = Counter()
        for alert in alerts:
            type_counter[alert["alert_type"]] += self._occurrence_count(alert)

        top = type_counter.most_common(limit)
        data = [ViolationTypeCount(violation_type=vt, count=cnt) for vt, cnt in top]
        total = sum(cnt for _, cnt in top)

        logger.debug("top_violation_types: %d types", len(data))
        return TopViolationTypesResponse(data=data, total=total)

    def summary(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> AnalyticsSummaryResponse:
        """Aggregate all analytics metrics into a single response."""
        return AnalyticsSummaryResponse(
            violations_per_day=self.violations_per_day(date_from, date_to),
            violations_per_camera=self.violations_per_camera(date_from, date_to),
            compliance_rate=self.compliance_rate(date_from, date_to),
            hourly_trends=self.hourly_trends(date_from, date_to),
            top_violation_types=self.top_violation_types(date_from, date_to),
        )
