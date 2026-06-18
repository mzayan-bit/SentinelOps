"""
SentinelOps — Inference API
==============================
Minimal FastAPI application with a health endpoint backed by the
:class:`inference.health.HealthChecker` module.

Run::

    uvicorn inference.api.main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from inference.health import HealthChecker
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class CheckSchema(BaseModel):
    """Single diagnostic check."""

    name: str
    status: str
    message: str
    duration_ms: float


class HealthSchema(BaseModel):
    """Full health report."""

    timestamp: str
    healthy: bool
    total_checks: int
    passed: int
    failed: int
    warnings: int
    total_duration_ms: float
    checks: list[CheckSchema]


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SentinelOps inference API starting …")
    yield
    logger.info("SentinelOps inference API shutting down.")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SentinelOps Inference API",
    description="Production-grade inference service for YOLO object detection.",
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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get(
    "/health",
    response_model=HealthSchema,
    tags=["System"],
    summary="Service health check",
)
async def health():
    """Run all diagnostic checks and return the system health report."""
    checker = HealthChecker()
    report = checker.run()
    return HealthSchema(**report.to_dict())
