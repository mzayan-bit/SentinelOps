"""
SentinelOps — Alert Management API (standalone application)
=============================================================
FastAPI application that serves the Alert Management REST API.

Run::

    uvicorn app.api.app:app --host 0.0.0.0 --port 8001 --reload
"""

from __future__ import annotations

import time
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.alert_routes import router as alert_router
from app.api.camera_routes import router as camera_router
from app.api.stream_routes import router as stream_router
from app.api.incident_routes import router as incident_router
from app.api.snapshot_routes import router as snapshot_router
from app.api.analytics_routes import router as analytics_router
from app.api.report_routes import router as report_router
from app.api.metrics_routes import router as metrics_router
from app.api.task_routes import router as task_router
from app.api.zone_routes import router as zone_router
from app.api.search_routes import router as search_router
from app.api.model_routes import router as model_router
from app.api.auth_routes import router as auth_router
from app.core.errors import register_error_handlers
from app.db.database import check_database, dispose_engine
from app.middleware.request_context import RequestContextMiddleware
from app.services.task_worker import task_worker
from app.demo_runner import demo_runner
from app.services.health_monitor import health_monitor
from config.settings import settings

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
settings.configure_logging()
import logging

logger = logging.getLogger("sentinelops.alert_app")

_start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _start_time
    _start_time = time.time()

    testing = os.getenv("TESTING") == "1"
    if not testing:
        logger.info("Starting background demo simulation...")
        demo_runner.start()
    
    logger.info("SentinelOps Alert Management API starting …")
    yield
    logger.info("SentinelOps Alert Management API shutting down.")
    task_worker.shutdown(wait=True)
    if not testing:
        demo_runner.stop()
    await dispose_engine()


app = FastAPI(
    title="SentinelOps Alert Management API",
    description="Production-grade alert lifecycle management for security & safety monitoring.",
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

register_error_handlers(app)

app.add_middleware(RequestContextMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.middleware.rate_limiter import RateLimiter
from app.middleware.security_headers import SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    RateLimiter,
    requests_per_minute=settings.rate_limit_rpm,
    enabled=settings.rate_limit_enabled and os.getenv("TESTING") != "1",
)

app.include_router(alert_router)
app.include_router(camera_router)
app.include_router(stream_router)
app.include_router(incident_router)
app.include_router(snapshot_router)
app.include_router(analytics_router)
app.include_router(report_router)
app.include_router(metrics_router)
app.include_router(task_router)
app.include_router(zone_router)
app.include_router(search_router)
app.include_router(model_router)
app.include_router(auth_router)


@app.get("/health", tags=["System"])
async def health():
    try:
        import psutil
    except ImportError:
        psutil = None

    uptime = time.time() - _start_time if _start_time else 0
    database = "healthy" if await check_database() else "unhealthy"

    disk = None
    memory = None
    if psutil is not None:
        disk_usage = psutil.disk_usage(str(settings.reports_dir.parent))
        memory_usage = psutil.virtual_memory()
        disk = {
            "total_bytes": disk_usage.total,
            "used_bytes": disk_usage.used,
            "free_bytes": disk_usage.free,
            "percent": disk_usage.percent,
        }
        memory = {
            "total_bytes": memory_usage.total,
            "available_bytes": memory_usage.available,
            "percent": memory_usage.percent,
        }

    cameras = health_monitor.get_all_health()
    return {
        "status": "healthy" if database != "unhealthy" else "degraded",
        "api": "healthy",
        "database": database,
        "ai_model": "configured" if settings.model_path else "unconfigured",
        "websocket": {
            "tracked_cameras": len(cameras),
            "status": "healthy",
        },
        "worker": {
            "status": "healthy",
            "recent_tasks": len(task_worker.list_tasks(limit=200)),
        },
        "disk": disk,
        "memory": memory,
        "uptime_seconds": round(uptime, 2),
        "version": settings.api_version,
        "environment": settings.environment,
    }
