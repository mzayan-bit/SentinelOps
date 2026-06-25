"""
SentinelOps — Metrics Data Models
===================================
Pydantic schemas for the platform metrics collection endpoints.
"""

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
    gpus: list[GPUMetrics] = Field(default_factory=list, description="List of individual GPU metrics")


class ApplicationMetrics(BaseModel):
    """Software telemetry from SentinelOps managers."""
    active_cameras: int = Field(..., description="Number of cameras currently streaming/online")
    total_cameras: int = Field(..., description="Total number of registered cameras")
    average_fps: float = Field(..., description="Average FPS across all online streams")
    average_latency_ms: float = Field(..., description="Average inference latency (ms) across all online streams")


class PlatformMetricsResponse(BaseModel):
    """Combined point-in-time metrics response payload."""
    timestamp: float = Field(..., description="Unix timestamp of the snapshot")
    system: SystemMetrics
    application: ApplicationMetrics
