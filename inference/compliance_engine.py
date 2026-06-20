"""
SentinelOps — PPE Compliance Engine
=======================================
Evaluates PPE compliance from YOLO tracker results.
Designed to consume raw ``ultralytics`` tracking output (with persistent IDs)
and return per-worker compliance assessments.

This module is **pure business logic** — it contains no model loading,
no video I/O, and no API code.  It is fully unit-testable with plain
dictionaries.

Usage::

    from inference.compliance_engine import ComplianceEngine

    engine = ComplianceEngine()

    # `results` comes from model.track(frame, persist=True)
    assessments = engine.evaluate_frame(results[0])

    for a in assessments:
        print(a["track_id"], a["status"], a["equipment"])
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("sentinelops.compliance_engine")


# ---------------------------------------------------------------------------
# Constants & enums
# ---------------------------------------------------------------------------
class ComplianceStatus(str, Enum):
    """PPE compliance verdict for a tracked worker."""

    SAFE = "SAFE"
    NO_HELMET = "NO_HELMET"
    NO_VEST = "NO_VEST"
    NO_PPE = "NO_PPE"


# ---------------------------------------------------------------------------
# Configurable rules
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ComplianceRules:
    """Configurable thresholds and class mappings.

    Parameters
    ----------
    helmet_class : str
        Class name in the YOLO model that represents a helmet.
    vest_class : str
        Class name in the YOLO model that represents a vest.
    min_confidence : float
        Ignore detections below this confidence.
    proximity_px : float
        Maximum pixel distance (centre-to-centre) to associate a
        PPE item with a nearby PPE item of a different type.
    """

    helmet_class: str = "safety_helmet"
    vest_class: str = "reflective_jacket"
    min_confidence: float = 0.30
    proximity_px: float = 300.0


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class TrackedDetection:
    """Normalised representation of a single tracked detection."""

    track_id: int | None
    class_name: str
    confidence: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def cx(self) -> float:
        """Centre x."""
        return (self.x_min + self.x_max) / 2

    @property
    def cy(self) -> float:
        """Centre y."""
        return (self.y_min + self.y_max) / 2

    def distance_to(self, other: TrackedDetection) -> float:
        """Euclidean centre-to-centre distance."""
        return ((self.cx - other.cx) ** 2 + (self.cy - other.cy) ** 2) ** 0.5


@dataclass
class WorkerAssessment:
    """Compliance assessment for one tracked entity.

    Attributes
    ----------
    track_id : int | None
        Persistent tracking ID from ByteTrack (None if tracking lost).
    status : ComplianceStatus
        Overall compliance verdict.
    has_helmet : bool
    has_vest : bool
    equipment : list[str]
        Names of matched PPE items.
    bbox : dict[str, float]
        Bounding box of the primary detection.
    """

    track_id: int | None
    status: ComplianceStatus
    has_helmet: bool
    has_vest: bool
    equipment: list[str] = field(default_factory=list)
    bbox: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "status": self.status.value,
            "has_helmet": self.has_helmet,
            "has_vest": self.has_vest,
            "equipment": self.equipment,
            "bbox": self.bbox,
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
class ComplianceEngine:
    """Stateless PPE compliance evaluator.

    Takes raw YOLO tracker output and returns a list of per-entity
    :class:`WorkerAssessment` objects.

    Parameters
    ----------
    rules : ComplianceRules | None
        Custom rules; defaults are used if ``None``.
    """

    def __init__(self, rules: ComplianceRules | None = None) -> None:
        self._rules = rules or ComplianceRules()

    @property
    def rules(self) -> ComplianceRules:
        """Currently active compliance rules."""
        return self._rules

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate_frame(self, result: Any) -> list[WorkerAssessment]:
        """Evaluate PPE compliance for a single frame's tracking result.

        Parameters
        ----------
        result
            A single ``ultralytics.engine.results.Results`` object
            (i.e. ``results[0]`` from ``model.track()``).

        Returns
        -------
        list[WorkerAssessment]
            One assessment per tracked equipment group.
        """
        detections = self._extract_detections(result)

        # Partition by class type
        helmets = [d for d in detections if d.class_name == self._rules.helmet_class]
        vests = [d for d in detections if d.class_name == self._rules.vest_class]

        # Associate helmets ↔ vests using proximity
        assessments = self._associate_and_assess(helmets, vests)

        return assessments

    def evaluate_detections(
        self,
        detections: list[dict[str, Any]],
    ) -> list[WorkerAssessment]:
        """Evaluate compliance from plain dictionaries (for unit testing).

        Each dict must have keys: ``track_id``, ``class_name``,
        ``confidence``, ``x_min``, ``y_min``, ``x_max``, ``y_max``.
        """
        parsed = [
            TrackedDetection(**d)
            for d in detections
            if d.get("confidence", 0) >= self._rules.min_confidence
        ]

        helmets = [d for d in parsed if d.class_name == self._rules.helmet_class]
        vests = [d for d in parsed if d.class_name == self._rules.vest_class]

        return self._associate_and_assess(helmets, vests)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _extract_detections(self, result: Any) -> list[TrackedDetection]:
        """Parse a YOLO Results object into ``TrackedDetection`` list."""
        detections: list[TrackedDetection] = []
        boxes = result.boxes
        names: dict[int, str] = result.names

        for box in boxes:
            conf = float(box.conf[0].item())
            if conf < self._rules.min_confidence:
                continue

            cls_id = int(box.cls[0].item())
            xyxy = box.xyxy[0].tolist()

            track_id: int | None = None
            if box.id is not None:
                track_id = int(box.id[0].item())

            detections.append(
                TrackedDetection(
                    track_id=track_id,
                    class_name=names.get(cls_id, f"class_{cls_id}"),
                    confidence=conf,
                    x_min=xyxy[0],
                    y_min=xyxy[1],
                    x_max=xyxy[2],
                    y_max=xyxy[3],
                )
            )

        return detections

    def _associate_and_assess(
        self,
        helmets: list[TrackedDetection],
        vests: list[TrackedDetection],
    ) -> list[WorkerAssessment]:
        """Match helmets to vests by proximity and produce assessments."""
        used_vests: set[int] = set()
        assessments: list[WorkerAssessment] = []

        # For each helmet, find the nearest vest within range
        for helmet in helmets:
            best_vest: TrackedDetection | None = None
            best_dist: float = float("inf")
            best_idx: int = -1

            for idx, vest in enumerate(vests):
                if idx in used_vests:
                    continue
                dist = helmet.distance_to(vest)
                if dist < best_dist and dist <= self._rules.proximity_px:
                    best_dist = dist
                    best_vest = vest
                    best_idx = idx

            has_vest = best_vest is not None
            if has_vest:
                used_vests.add(best_idx)

            equipment = [self._rules.helmet_class]
            if has_vest:
                equipment.append(self._rules.vest_class)

            status = ComplianceStatus.SAFE if has_vest else ComplianceStatus.NO_VEST

            assessments.append(
                WorkerAssessment(
                    track_id=helmet.track_id,
                    status=status,
                    has_helmet=True,
                    has_vest=has_vest,
                    equipment=equipment,
                    bbox={
                        "x_min": round(helmet.x_min, 2),
                        "y_min": round(helmet.y_min, 2),
                        "x_max": round(helmet.x_max, 2),
                        "y_max": round(helmet.y_max, 2),
                    },
                )
            )

        # Remaining unmatched vests → NO_HELMET
        for idx, vest in enumerate(vests):
            if idx in used_vests:
                continue

            assessments.append(
                WorkerAssessment(
                    track_id=vest.track_id,
                    status=ComplianceStatus.NO_HELMET,
                    has_helmet=False,
                    has_vest=True,
                    equipment=[self._rules.vest_class],
                    bbox={
                        "x_min": round(vest.x_min, 2),
                        "y_min": round(vest.y_min, 2),
                        "x_max": round(vest.x_max, 2),
                        "y_max": round(vest.y_max, 2),
                    },
                )
            )

        if assessments:
            safe = sum(1 for a in assessments if a.status == ComplianceStatus.SAFE)
            violations = len(assessments) - safe
            logger.debug(
                "Frame compliance: %d assessed, %d safe, %d violations",
                len(assessments),
                safe,
                violations,
            )

        return assessments
