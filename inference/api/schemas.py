"""
SentinelOps — Pydantic Schemas
================================
Request / response models for the inference API.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Detection primitives
# ---------------------------------------------------------------------------
class BoundingBox(BaseModel):
    """Bounding box in xyxy (pixel) format."""

    x_min: float = Field(..., description="Left edge (px)")
    y_min: float = Field(..., description="Top edge (px)")
    x_max: float = Field(..., description="Right edge (px)")
    y_max: float = Field(..., description="Bottom edge (px)")
    width: float = Field(..., description="Box width (px)")
    height: float = Field(..., description="Box height (px)")


class Detection(BaseModel):
    """A single detected object."""

    class_id: int = Field(..., description="YOLO class index")
    class_name: str = Field(..., description="Human-readable class name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    bbox: BoundingBox


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------
class PredictionResponse(BaseModel):
    """Response for a single image prediction."""

    success: bool = True
    image_width: int = Field(..., description="Source image width (px)")
    image_height: int = Field(..., description="Source image height (px)")
    num_detections: int = Field(..., description="Total detections returned")
    detections: list[Detection]
    inference_time_ms: float = Field(..., description="Inference wall-clock time (ms)")


class BatchPredictionResponse(BaseModel):
    """Response for a batch prediction."""

    success: bool = True
    total_images: int
    results: list[PredictionResponse]
    total_inference_time_ms: float


class HealthResponse(BaseModel):
    """Service health check response."""

    status: str = "healthy"
    model_loaded: bool
    model_name: str | None = None
    uptime_seconds: float


class ModelInfoResponse(BaseModel):
    """Metadata about the currently loaded model."""

    model_name: str
    model_path: str
    num_classes: int
    class_names: list[str]
    input_size: int
    device: str


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    success: bool = False
    error: str
    detail: str | None = None
