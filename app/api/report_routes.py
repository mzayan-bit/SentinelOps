"""
SentinelOps — Report REST API Routes
========================================
FastAPI router for generating and downloading violation reports.

Mount this router into any FastAPI application::

    from app.api.report_routes import router as report_router
    app.include_router(report_router)

Endpoints:
    POST /reports/generate            — Submit report generation (async)
    GET  /reports                     — List all generated reports
    GET  /reports/{report_id}/download — Download a report file
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.security import Role, get_current_user, require_role

from app.models.report import ReportFormat, ReportMetadata, ReportRequest
from app.services.alert_service import AlertService
from app.services.analytics_service import AnalyticsService
from app.services.report_service import ReportNotFoundError, ReportService
from app.services.task_worker import task_worker

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("sentinelops.report_api")

# ---------------------------------------------------------------------------
# Service singleton
# ---------------------------------------------------------------------------
_alert_service = AlertService()
_analytics_service = AnalyticsService(_alert_service)
_report_service = ReportService(_alert_service, _analytics_service)

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/reports", tags=["Reports"])

# ---------------------------------------------------------------------------
# Content type mapping
# ---------------------------------------------------------------------------
_CONTENT_TYPES: dict[ReportFormat, str] = {
    ReportFormat.CSV: "text/csv",
    ReportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ReportFormat.PDF: "application/pdf",
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "/generate",
    status_code=202,
    summary="Submit report generation (async)",
)
async def generate_report(request: ReportRequest, user: User = Depends(require_role(Role.SUPERVISOR))):
    """Submit a violation report for background generation.

    Returns immediately with a task_id that can be polled via
    ``GET /api/tasks/{task_id}`` for status and result.
    """
    task_id = task_worker.submit(
        _report_service.generate,
        request,
        task_type="report_generation",
    )
    logger.info("Report generation submitted as task %s", task_id)
    return {
        "task_id": task_id,
        "status": "PENDING",
        "message": "Report generation submitted. Poll /api/tasks/{task_id} for status.",
    }


@router.get(
    "",
    response_model=list[ReportMetadata],
    summary="List all generated reports",
)
async def list_reports(user: User = Depends(require_role(Role.VIEWER))):
    """Return metadata for all previously generated reports."""
    return _report_service.list_reports()


@router.get(
    "/{report_id}/download",
    summary="Download a report file",
)
async def download_report(report_id: str, user: User = Depends(require_role(Role.VIEWER))):
    """Download a generated report file by its ID."""
    try:
        path = _report_service.get_report_path(report_id)
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # Determine content type from file extension
    ext = path.suffix.lower()
    ext_format_map = {".csv": ReportFormat.CSV, ".xlsx": ReportFormat.EXCEL, ".pdf": ReportFormat.PDF}
    fmt = ext_format_map.get(ext, ReportFormat.CSV)
    media_type = _CONTENT_TYPES[fmt]

    return FileResponse(
        path=str(path),
        media_type=media_type,
        filename=path.name,
    )

