"""
SentinelOps — Alert Management API (standalone application)
=============================================================
FastAPI application that serves the Alert Management REST API.

Run::

    uvicorn app.api.app:app --host 0.0.0.0 --port 8001 --reload
"""

from __future__ import annotations

import logging
import time
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
from app.auth import set_auth_enabled
from app.services.task_worker import task_worker

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("sentinelops.alert_app")

_start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _start_time
    _start_time = time.time()
    
    # Enable API key authentication in production/runtime (skip if testing)
    import os
    if not os.getenv("TESTING"):
        set_auth_enabled(True)
    
    logger.info("SentinelOps Alert Management API starting …")
    yield
    logger.info("SentinelOps Alert Management API shutting down.")
    task_worker.shutdown(wait=True)


app = FastAPI(
    title="SentinelOps Alert Management API",
    description="Production-grade alert lifecycle management for security & safety monitoring.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/health", tags=["System"])
async def health():
    uptime = time.time() - _start_time if _start_time else 0
    return {"status": "healthy", "uptime_seconds": round(uptime, 2)}
