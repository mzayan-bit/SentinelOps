"""
SentinelOps — Prediction Schemas
===================================
Typed, validated data classes that serve as the canonical contract
between the inference layer, violation engine, API, and dashboard.

These schemas are **read-only representations** — they do not contain
business logic and never import from the inference package.

Usage::

    from schemas.prediction import Detection, PredictionResult, ComplianceResult

    det = Detection(
        class_id=0,
        class_name="safety_helmet",
        confidence=0.93,
        x_min=100, y_min=50, x_max=200, y_max=150,
    )
    print(det.to_dict())
    print(det.area)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class ComplianceStatus(str, Enum):
    """PPE compliance verdict."""

    SAFE = "SAFE"
    NO_HELMET = "NO_HELMET"
    NO_VEST = "NO_VEST"
    NO_PPE = "NO_PPE"


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Detection:
    """A single object detection with bounding-box coordinates.

    Coordinates are in **pixel** space (xyxy format).

    Parameters
    ----------
    class_id : int
        YOLO class index (≥ 0).
    class_name : str
        Human-readable label.
    confidence : float
        Model confidence in [0, 1].
    x_min, y_min, x_max, y_max : float
        Bounding-box corners.
    """

    class_id: int
    class_name: str
    confidence: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def __post_init__(self) -> None:
        errors: list[str] = []
        if self.class_id < 0:
            errors.append(f"class_id must be ≥ 0, got {self.class_id}")
        if not 0.0 <= self.confidence <= 1.0:
            errors.append(f"confidence must be in [0, 1], got {self.confidence}")
        if self.x_max <= self.x_min:
            errors.append(f"x_max ({self.x_max}) must be > x_min ({self.x_min})")
        if self.y_max <= self.y_min:
            errors.append(f"y_max ({self.y_max}) must be > y_min ({self.y_min})")
        if errors:
            raise ValueError("Invalid Detection:\n  • " + "\n  • ".join(errors))

    @property
    def width(self) -> float:
        """Bounding-box width in pixels."""
        return round(self.x_max - self.x_min, 2)

    @property
    def height(self) -> float:
        """Bounding-box height in pixels."""
        return round(self.y_max - self.y_min, 2)

    @property
    def area(self) -> float:
        """Bounding-box area in pixels²."""
        return round(self.width * self.height, 2)

    @property
    def center(self) -> tuple[float, float]:
        """(cx, cy) centre point."""
        return (
            round((self.x_min + self.x_max) / 2, 2),
            round((self.y_min + self.y_max) / 2, 2),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-safe dictionary."""
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "bounding_box": {
                "x_min": self.x_min,
                "y_min": self.y_min,
                "x_max": self.x_max,
                "y_max": self.y_max,
                "width": self.width,
                "height": self.height,
            },
        }


# ---------------------------------------------------------------------------
# PredictionResult
# ---------------------------------------------------------------------------
@dataclass
class PredictionResult:
    """Structured output from a single image inference.

    Parameters
    ----------
    image_path : str
        Source image path.
    image_width : int
        Image width in pixels.
    image_height : int
        Image height in pixels.
    detections : list[Detection]
        Detected objects.
    inference_time_ms : float
        Wall-clock inference time in milliseconds.
    """

    image_path: str
    image_width: int
    image_height: int
    detections: list[Detection] = field(default_factory=list)
    inference_time_ms: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        if self.image_width <= 0 or self.image_height <= 0:
            raise ValueError(
                f"Image dimensions must be positive, "
                f"got {self.image_width}×{self.image_height}"
            )

    @property
    def num_detections(self) -> int:
        """Total number of detections."""
        return len(self.detections)

    @property
    def class_counts(self) -> dict[str, int]:
        """Detection count per class name."""
        counts: dict[str, int] = {}
        for d in self.detections:
            counts[d.class_name] = counts.get(d.class_name, 0) + 1
        return counts

    def filter_by_confidence(self, threshold: float) -> list[Detection]:
        """Return detections at or above the given confidence."""
        return [d for d in self.detections if d.confidence >= threshold]

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_path": self.image_path,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "num_detections": self.num_detections,
            "detections": [d.to_dict() for d in self.detections],
            "inference_time_ms": self.inference_time_ms,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# ComplianceResult
# ---------------------------------------------------------------------------
@dataclass
class ComplianceResult:
    """PPE compliance assessment for a detected person.

    Parameters
    ----------
    status : ComplianceStatus
        Overall compliance verdict.
    has_helmet : bool
        Whether a helmet was detected.
    has_vest : bool
        Whether a vest was detected.
    person_bbox : Detection | None
        Region associated with this person (may be synthesised).
    matched_equipment : list[Detection]
        PPE detections matched to this person.
    """

    status: ComplianceStatus
    has_helmet: bool
    has_vest: bool
    person_bbox: Detection | None = None
    matched_equipment: list[Detection] = field(default_factory=list)

    @property
    def is_compliant(self) -> bool:
        """Whether the person is fully PPE-compliant."""
        return self.status == ComplianceStatus.SAFE

    @property
    def missing_items(self) -> list[str]:
        """Human-readable list of missing PPE items."""
        missing: list[str] = []
        if not self.has_helmet:
            missing.append("helmet")
        if not self.has_vest:
            missing.append("vest")
        return missing

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "is_compliant": self.is_compliant,
            "has_helmet": self.has_helmet,
            "has_vest": self.has_vest,
            "missing_items": self.missing_items,
            "person_bbox": self.person_bbox.to_dict() if self.person_bbox else None,
            "matched_equipment": [e.to_dict() for e in self.matched_equipment],
        }
