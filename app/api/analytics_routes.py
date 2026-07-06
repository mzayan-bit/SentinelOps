"""
SentinelOps — Analytics REST API Routes
==========================================
FastAPI router providing read-only analytics endpoints.

Mount this router into any FastAPI application::

    from app.api.analytics_routes import router as analytics_router
    app.include_router(analytics_router)

Endpoints:
    GET /analytics/violations-per-day     — Daily violation counts
    GET /analytics/violations-per-camera  — Per-camera violation counts
    GET /analytics/compliance-rate        — PPE compliance rate
    GET /analytics/hourly-trends          — Hourly violation distribution
    GET /analytics/top-violation-types    — Most frequent violation types
    GET /analytics/summary                — Combined dashboard payload
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.core.security import Role, get_current_user, require_role

from app.models.analytics import (
    AnalyticsSummaryResponse,
    ComplianceRateResponse,
    HourlyTrendsResponse,
    TopViolationTypesResponse,
    ViolationsPerCameraResponse,
    ViolationsPerDayResponse,
)
from app.services.alert_service import AlertService
from app.services.analytics_service import AnalyticsService
from app.services.cache_service import cached

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("sentinelops.analytics_api")

# ---------------------------------------------------------------------------
# Service singleton
# ---------------------------------------------------------------------------
_alert_service = AlertService()
_analytics_service = AnalyticsService(_alert_service)

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get(
    "/violations-per-day",
    response_model=ViolationsPerDayResponse,
    summary="Daily violation counts",
)
@cached(prefix="analytics:", ttl_seconds=300)
async def violations_per_day(
    date_from: datetime | None = Query(default=None, description="Start of date range (ISO 8601)."),
    date_to: datetime | None = Query(default=None, description="End of date range (ISO 8601)."),
    user: User = Depends(require_role(Role.VIEWER)),
):
    """Return violation counts grouped by calendar date."""
    return _analytics_service.violations_per_day(date_from, date_to)


@router.get(
    "/violations-per-camera",
    response_model=ViolationsPerCameraResponse,
    summary="Per-camera violation counts",
)
@cached(prefix="analytics:", ttl_seconds=300)
async def violations_per_camera(
    date_from: datetime | None = Query(default=None, description="Start of date range (ISO 8601)."),
    date_to: datetime | None = Query(default=None, description="End of date range (ISO 8601)."),
    user: User = Depends(require_role(Role.VIEWER)),
):
    """Return violation counts grouped by camera, sorted descending."""
    return _analytics_service.violations_per_camera(date_from, date_to)


@router.get(
    "/compliance-rate",
    response_model=ComplianceRateResponse,
    summary="PPE compliance rate",
)
@cached(prefix="analytics:", ttl_seconds=300)
async def compliance_rate(
    date_from: datetime | None = Query(default=None, description="Start of date range (ISO 8601)."),
    date_to: datetime | None = Query(default=None, description="End of date range (ISO 8601)."),
    user: User = Depends(require_role(Role.VIEWER)),
):
    """Return PPE compliance rate (No Helmet / No Vest as non-compliant)."""
    return _analytics_service.compliance_rate(date_from, date_to)


@router.get(
    "/hourly-trends",
    response_model=HourlyTrendsResponse,
    summary="Hourly violation distribution",
)
@cached(prefix="analytics:", ttl_seconds=300)
async def hourly_trends(
    date_from: datetime | None = Query(default=None, description="Start of date range (ISO 8601)."),
    date_to: datetime | None = Query(default=None, description="End of date range (ISO 8601)."),
    user: User = Depends(require_role(Role.VIEWER)),
):
    """Return violation counts grouped by hour of day (0–23)."""
    return _analytics_service.hourly_trends(date_from, date_to)


@router.get(
    "/top-violation-types",
    response_model=TopViolationTypesResponse,
    summary="Most frequent violation types",
)
@cached(prefix="analytics:", ttl_seconds=300)
async def top_violation_types(
    date_from: datetime | None = Query(default=None, description="Start of date range (ISO 8601)."),
    date_to: datetime | None = Query(default=None, description="End of date range (ISO 8601)."),
    limit: int = Query(default=10, ge=1, le=50, description="Max number of types to return."),
    user: User = Depends(require_role(Role.VIEWER)),
):
    """Return the top N most frequent violation types."""
    return _analytics_service.top_violation_types(date_from, date_to, limit=limit)


@router.get("/summary", response_model=AnalyticsSummaryResponse, summary="Get full analytics summary")
@cached(prefix="analytics:summary", ttl_seconds=300)
async def get_analytics_summary(
    date_from: datetime | None = Query(None, description="Start date/time"),
    date_to: datetime | None = Query(None, description="End date/time"),
    user: User = Depends(require_role(Role.VIEWER))
):
    """
    Returns an aggregated payload containing all analytics metrics
    for the specified time window.
    """
    return _analytics_service.summary(date_from=date_from, date_to=date_to)

@router.get("/recommendations", summary="Get data-driven safety recommendations")
@cached(prefix="analytics:recommendations", ttl_seconds=300)
async def get_recommendations(
    date_from: datetime | None = Query(None, description="Start date/time"),
    date_to: datetime | None = Query(None, description="End date/time"),
    user: User = Depends(require_role(Role.VIEWER))
):
    """
    Analyzes site-wide telemetry and returns prioritized safety recommendations
    based on compliance rates, trends, and repeat violations.
    """
    from app.services.recommendation_engine import RecommendationEngine
    # We fetch the raw summary first
    summary = _analytics_service.summary(date_from=date_from, date_to=date_to)
    return RecommendationEngine.generate_recommendations(summary)
