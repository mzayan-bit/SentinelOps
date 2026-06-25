"""
SentinelOps — Metrics Service
===============================
Aggregates hardware and application telemetry for platform observability.
"""

import logging
import time

import psutil

try:
    import GPUtil
    _HAS_GPUTIL = True
except ImportError:
    GPUtil = None
    _HAS_GPUTIL = False

from app.models.metrics import (
    ApplicationMetrics,
    GPUMetrics,
    PlatformMetricsResponse,
    SystemMetrics,
)
from app.services.camera_manager import CameraManager
from app.services.health_monitor import HealthMonitorService

logger = logging.getLogger("sentinelops.metrics_service")


class MetricsService:
    """Service to collect real-time system and application metrics."""

    def __init__(self, camera_manager: CameraManager, health_monitor: HealthMonitorService):
        self._camera_manager = camera_manager
        self._health_monitor = health_monitor

        # Initial call to cpu_percent to calibrate baseline (non-blocking)
        psutil.cpu_percent(interval=None)

    def _get_system_metrics(self) -> SystemMetrics:
        """Fetch CPU, RAM, and GPU utilization."""
        cpu_pct = psutil.cpu_percent(interval=None)
        ram_pct = psutil.virtual_memory().percent

        gpu_metrics: list[GPUMetrics] = []
        gpu_available = False

        if _HAS_GPUTIL:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_available = True
                    for gpu in gpus:
                        gpu_metrics.append(
                            GPUMetrics(
                                id=gpu.id,
                                name=gpu.name,
                                load_percent=gpu.load * 100.0,
                                memory_percent=gpu.memoryUtil * 100.0,
                                temperature_celsius=gpu.temperature,
                            )
                        )
            except Exception as e:
                logger.warning("Failed to collect GPU metrics via GPUtil: %s", e)

        return SystemMetrics(
            cpu_percent=cpu_pct,
            ram_percent=ram_pct,
            gpu_available=gpu_available,
            gpus=gpu_metrics,
        )

    def _get_application_metrics(self) -> ApplicationMetrics:
        """Fetch telemetry from internal components (Cameras, Health)."""
        registered_cameras = self._camera_manager.list_cameras()
        total_cameras = len(registered_cameras)

        health_data = self._health_monitor.get_all_health()

        online_count = 0
        total_fps = 0.0
        total_latency = 0.0

        for cam_health in health_data.values():
            if cam_health and cam_health.status == "online":
                online_count += 1
                total_fps += cam_health.fps
                total_latency += cam_health.stream_latency_ms

        avg_fps = total_fps / online_count if online_count > 0 else 0.0
        avg_latency = total_latency / online_count if online_count > 0 else 0.0

        return ApplicationMetrics(
            active_cameras=online_count,
            total_cameras=total_cameras,
            average_fps=round(avg_fps, 2),
            average_latency_ms=round(avg_latency, 2),
        )

    def get_snapshot(self) -> PlatformMetricsResponse:
        """Generate a point-in-time combined snapshot of all metrics."""
        return PlatformMetricsResponse(
            timestamp=time.time(),
            system=self._get_system_metrics(),
            application=self._get_application_metrics(),
        )
