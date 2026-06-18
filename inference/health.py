"""
SentinelOps — System Health Checker
======================================
Runs diagnostic checks against the inference stack and returns a
structured health report.  Designed to be called by API health
endpoints, monitoring crons, or CLI scripts.

Usage::

    from inference.health import HealthChecker

    checker = HealthChecker()
    report  = checker.run()

    print(report.healthy)       # True / False
    print(report.to_dict())     # full JSON-safe dict
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class CheckStatus(str, Enum):
    """Outcome of a single diagnostic check."""

    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class CheckResult:
    """Result of one diagnostic check."""

    name: str
    status: CheckStatus
    message: str
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass
class HealthReport:
    """Aggregated health report across all checks."""

    timestamp: str
    healthy: bool
    checks: list[CheckResult] = field(default_factory=list)
    total_duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "healthy": self.healthy,
            "total_checks": len(self.checks),
            "passed": sum(1 for c in self.checks if c.status == CheckStatus.PASS),
            "failed": sum(1 for c in self.checks if c.status == CheckStatus.FAIL),
            "warnings": sum(1 for c in self.checks if c.status == CheckStatus.WARN),
            "total_duration_ms": round(self.total_duration_ms, 2),
            "checks": [c.to_dict() for c in self.checks],
        }


# ---------------------------------------------------------------------------
# Health checker
# ---------------------------------------------------------------------------
class HealthChecker:
    """Runs all diagnostic checks and produces a :class:`HealthReport`."""

    def run(self) -> HealthReport:
        """Execute every registered check and return the report."""
        t0 = time.perf_counter()

        checks = [
            self._check_config(),
            self._check_model_file(),
            self._check_model_loadable(),
            self._check_artifacts_dir(),
        ]

        total_ms = (time.perf_counter() - t0) * 1000
        healthy = all(c.status != CheckStatus.FAIL for c in checks)

        report = HealthReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            healthy=healthy,
            checks=checks,
            total_duration_ms=total_ms,
        )

        log_fn = logger.info if healthy else logger.warning
        log_fn(
            "Health check complete: %s (%d/%d passed, %.1f ms)",
            "HEALTHY" if healthy else "UNHEALTHY",
            sum(1 for c in checks if c.status == CheckStatus.PASS),
            len(checks),
            total_ms,
        )
        return report

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_config() -> CheckResult:
        """Verify that project settings load without errors."""
        t0 = time.perf_counter()
        try:
            from config.settings import settings  # noqa: F811

            _ = settings.model_path
            _ = settings.confidence_threshold
            _ = settings.log_level
            return CheckResult(
                name="configuration",
                status=CheckStatus.PASS,
                message=f"Settings loaded (log_level={settings.log_level}).",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return CheckResult(
                name="configuration",
                status=CheckStatus.FAIL,
                message=f"Failed to load settings: {exc}",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

    @staticmethod
    def _check_model_file() -> CheckResult:
        """Verify that the model weights file exists on disk."""
        t0 = time.perf_counter()
        try:
            from config.settings import settings

            path = Path(settings.model_path)
            if path.exists():
                size_mb = path.stat().st_size / (1024 * 1024)
                return CheckResult(
                    name="model_file",
                    status=CheckStatus.PASS,
                    message=f"Model found at '{path}' ({size_mb:.1f} MB).",
                    duration_ms=(time.perf_counter() - t0) * 1000,
                )
            return CheckResult(
                name="model_file",
                status=CheckStatus.FAIL,
                message=f"Model not found at '{path}'.",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return CheckResult(
                name="model_file",
                status=CheckStatus.FAIL,
                message=f"Error checking model file: {exc}",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

    @staticmethod
    def _check_model_loadable() -> CheckResult:
        """Attempt to instantiate the model loader (does not load weights)."""
        t0 = time.perf_counter()
        try:
            from inference.model_loader import ModelLoader

            loader = ModelLoader()
            if loader.is_loaded:
                return CheckResult(
                    name="model_loadable",
                    status=CheckStatus.PASS,
                    message="Model already loaded in memory.",
                    duration_ms=(time.perf_counter() - t0) * 1000,
                )
            return CheckResult(
                name="model_loadable",
                status=CheckStatus.WARN,
                message="ModelLoader ready; weights not yet loaded (lazy init).",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return CheckResult(
                name="model_loadable",
                status=CheckStatus.FAIL,
                message=f"ModelLoader failed: {exc}",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

    @staticmethod
    def _check_artifacts_dir() -> CheckResult:
        """Verify the artifacts directory exists or can be created."""
        t0 = time.perf_counter()
        try:
            from config.settings import settings

            path = Path(settings.artifacts_dir)
            path.mkdir(parents=True, exist_ok=True)
            return CheckResult(
                name="artifacts_directory",
                status=CheckStatus.PASS,
                message=f"Artifacts directory ready at '{path}'.",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        except Exception as exc:
            return CheckResult(
                name="artifacts_directory",
                status=CheckStatus.FAIL,
                message=f"Cannot create artifacts directory: {exc}",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
