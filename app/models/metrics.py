"""
SentinelOps — Metrics Data Models
===================================
Pydantic schemas for the platform metrics collection endpoints.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class GPUMetrics(BaseModel):
    """Detailed GPU metrics if available."""
    id: int
    name: str
    load_percent: float = Field(..., description="GPU utilization percent (0-100)")
    memory_percent: float = Field(..., description="VRAM utilization percent (0-100)")
    temperature_celsius: float


class SystemMetrics(BaseModel):
    """Hardware resource utilization."""
    cpu_percent: float = Field(..., description="Global CPU utilization percent (0-100)")
    ram_percent: float = Field(..., description="Global RAM utilization percent (0-100)")
    gpu_available: bool = Field(..., description="Whether NVIDIA GPUs were detected")
    gpus: List[GPUMetrics] = Field(default_factory=list, description="List of individual GPU metrics")

class CameraMetrics(BaseModel):
    """Granular telemetry per camera."""
    camera_id: str
    fps: float
    dropped_frames: int
    latency_ms: float
    total_detections: int
    total_alerts: int
    status: str

class ProfilingMetrics(BaseModel):
    """Percentile profiling for latency."""
    average_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_fps: float
    
class DriftMetrics(BaseModel):
    """Detects model degradation over time."""
    avg_confidence_last_1h: float = 0.0
    avg_confidence_last_24h: float = 0.0
    confidence_drift_detected: bool = False
    anomalous_alert_spike: bool = False

class ObservabilityMetrics(BaseModel):
    """Core enterprise AI observability metrics."""
    queue_size: int = 0
    dropped_frames_total: int = 0
    total_detections: int = 0
    total_tracks: int = 0
    total_alerts: int = 0
    profiling: Optional[ProfilingMetrics] = None
    drift: Optional[DriftMetrics] = None
    camera_metrics: List[CameraMetrics] = Field(default_factory=list)
    system_health_warnings: List[str] = Field(default_factory=list)

class ApplicationMetrics(BaseModel):
    """Software telemetry from SentinelOps managers. Maintained for backwards compatibility."""
    active_cameras: int = Field(..., description="Number of cameras currently streaming/online")
    total_cameras: int = Field(..., description="Total number of registered cameras")
    average_fps: float = Field(..., description="Average FPS across all online streams")
    average_latency_ms: float = Field(..., description="Average inference latency (ms) across all online streams")
    observability: Optional[ObservabilityMetrics] = None

class PlatformMetricsResponse(BaseModel):
    """Combined point-in-time metrics response payload."""
    timestamp: float = Field(..., description="Unix timestamp of the snapshot")
    system: SystemMetrics
    application: ApplicationMetrics
