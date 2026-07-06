"""
SentinelOps — Alert REST API Routes
======================================
FastAPI router providing full CRUD + action endpoints for alerts.

Mount this router into any FastAPI application::

    from app.api.alert_routes import router as alert_router
    app.include_router(alert_router)

Endpoints:
    GET    /alerts              — List / filter alerts
    GET    /alerts/stats        — Aggregate statistics
    GET    /alerts/{id}         — Get a single alert
    POST   /alerts              — Create a new alert
    PUT    /alerts/{id}         — Update an alert
    DELETE /alerts/{id}         — Delete an alert
    POST   /alerts/{id}/assign  — Assign to investigator
    POST   /alerts/{id}/resolve — Resolve / mark false-positive
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import Role, get_current_user, require_role
from app.schemas.pagination import PaginationParams, build_page_meta

from app.models.alert import (
    Alert,
    AlertAssign,
    AlertCreate,
    AlertFilter,
    AlertListResponse,
    AlertResolve,
    AlertStatsResponse,
    AlertStatus,
    AlertType,
    AlertUpdate,
    Severity,
)
from app.services.alert_service import (
    AlertNotFoundError,
    AlertService,
    InvalidTransitionError,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("sentinelops.alert_api")

# ---------------------------------------------------------------------------
# Service singleton
# ---------------------------------------------------------------------------
_service = AlertService()

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/alerts", tags=["Alerts"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=AlertListResponse,
    summary="List alerts with optional filters",
)
async def list_alerts(
    severity: Severity | None = Query(default=None),
    status: AlertStatus | None = Query(default=None),
    alert_type: AlertType | None = Query(default=None),
    camera_id: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str = Query(default="timestamp"),
    sort_desc: bool = Query(default=True),
    user: UserModel = Depends(require_role(Role.VIEWER)),
):
    """Return all alerts matching the provided filters, paginated and sorted."""
    filters = AlertFilter(
        severity=severity,
        status=status,
        alert_type=alert_type,
        camera_id=camera_id,
        date_from=date_from,
        date_to=date_to,
    )
    alerts = _service.list_alerts(filters)
    
    # Sorting
    alerts.sort(key=lambda a: getattr(a, sort_by, a.timestamp), reverse=sort_desc)
    
    params = PaginationParams(
        limit=limit,
        offset=skip,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        order="desc" if sort_desc else "asc",
    )
    total = len(alerts)
    start = params.effective_offset
    paginated = alerts[start:start + params.effective_limit]
    meta = build_page_meta(total, params)

    return AlertListResponse(
        total=total,
        alerts=paginated,
        page=meta.page,
        page_size=meta.page_size,
        pages=meta.pages,
        next=meta.next,
        previous=meta.previous,
    )


@router.get(
    "/stats",
    response_model=AlertStatsResponse,
    summary="Aggregate alert statistics",
)
async def alert_stats(user: UserModel = Depends(require_role(Role.VIEWER))):
    """Return total counts grouped by severity, status, and type."""
    return _service.stats()


@router.get(
    "/{alert_id}",
    response_model=Alert,
    summary="Get a single alert",
)
async def get_alert(alert_id: str, user: UserModel = Depends(require_role(Role.VIEWER))):
    """Retrieve full alert details by ID."""
    try:
        return _service.get(alert_id)
    except AlertNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "",
    response_model=Alert,
    status_code=201,
    summary="Create a new alert",
)
async def create_alert(payload: AlertCreate, user: UserModel = Depends(require_role(Role.SUPERVISOR))):
    """Register a new security / safety alert."""
    return _service.create(payload)


@router.put(
    "/{alert_id}",
    response_model=Alert,
    summary="Update an alert",
)
async def update_alert(alert_id: str, payload: AlertUpdate, user: UserModel = Depends(require_role(Role.SUPERVISOR))):
    """Partially update an existing alert's fields."""
    try:
        return _service.update(alert_id, payload)
    except AlertNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete(
    "/{alert_id}",
    status_code=204,
    summary="Delete an alert",
)
async def delete_alert(alert_id: str, user: UserModel = Depends(require_role(Role.ORG_ADMIN))):
    """Permanently delete an alert."""
    try:
        _service.delete(alert_id)
    except AlertNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/{alert_id}/assign",
    response_model=Alert,
    summary="Assign an alert",
)
async def assign_alert(alert_id: str, payload: AlertAssign, user: UserModel = Depends(require_role(Role.SUPERVISOR))):
    """Assign an alert to an investigator and move to 'Investigating'."""
    try:
        return _service.assign(alert_id, payload.assigned_to)
    except AlertNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post(
    "/{alert_id}/resolve",
    response_model=Alert,
    summary="Resolve an alert",
)
async def resolve_alert(alert_id: str, payload: AlertResolve, user: UserModel = Depends(require_role(Role.SUPERVISOR))):
    """Resolve an alert or mark it as a false positive."""
    try:
        return _service.resolve(alert_id, payload)
    except AlertNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
