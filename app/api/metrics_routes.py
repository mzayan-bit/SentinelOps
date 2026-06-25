"""
SentinelOps — Metrics REST API Routes
========================================
FastAPI router providing platform observability metrics endpoints.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.auth import Role, User, require_role
from app.models.metrics import PlatformMetricsResponse
from app.services.camera_manager import CameraManager
from app.services.health_monitor import health_monitor
from app.services.metrics_service import MetricsService

logger = logging.getLogger("sentinelops.metrics_api")

# We import the global singletons used across the app
from app.api.camera_routes import camera_manager

_metrics_service = MetricsService(camera_manager=camera_manager, health_monitor=health_monitor)

router = APIRouter(prefix="/api/metrics", tags=["System"])


@router.get(
    "",
    response_model=PlatformMetricsResponse,
    summary="Get platform snapshot metrics",
)
async def get_platform_metrics(user: User = Depends(require_role(Role.VIEWER))):
    """Retrieve real-time hardware utilization and application telemetry snapshot."""
    return _metrics_service.get_snapshot()
