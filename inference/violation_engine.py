"""
SentinelOps — PPE Violation Engine
=====================================
Business-rule engine that evaluates prediction output and determines
the PPE compliance status for each detected person.

This module intentionally contains **zero** model logic — it only
applies deterministic rules to structured prediction results produced
by :class:`inference.predictor.PredictionService`.

Usage::

    from inference.predictor import PredictionService
    from inference.violation_engine import PPEViolationEngine

    service = PredictionService()
    engine  = PPEViolationEngine()

    prediction = service.predict("frame.jpg")
    assessment = engine.evaluate(prediction)

    for v in assessment["violations"]:
        print(v["status"], v["details"])
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("sentinelops.violation_engine")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class PPEStatus(str, Enum):
    """PPE compliance status for a detected person."""

    SAFE = "SAFE"
    NO_HELMET = "NO_HELMET"
    NO_VEST = "NO_VEST"
    NO_PPE = "NO_PPE"


class ClassName:
    """Canonical class name constants (must match YOLO training labels)."""

    HELMET = "safety_helmet"
    VEST = "reflective_jacket"


# IoU threshold for associating PPE items with a person bbox
DEFAULT_IOU_THRESHOLD: float = 0.05
# Minimum confidence to consider a detection valid for rule evaluation
DEFAULT_MIN_CONFIDENCE: float = 0.30


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class ViolationResult:
    """Assessment result for a single person."""

    status: PPEStatus
    has_helmet: bool
    has_vest: bool
    person_bbox: dict[str, float]
    matched_equipment: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "has_helmet": self.has_helmet,
            "has_vest": self.has_vest,
            "person_bbox": self.person_bbox,
            "matched_equipment": self.matched_equipment,
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
class PPEViolationEngine:
    """Stateless engine that applies PPE compliance rules.

    Parameters
    ----------
    iou_threshold : float
        Minimum IoU between a person bbox and an equipment bbox to
        consider the equipment "associated" with that person.
    min_confidence : float
        Detections below this confidence are ignored.
    """

    def __init__(
        self,
        iou_threshold: float = DEFAULT_IOU_THRESHOLD,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    ) -> None:
        self._iou_threshold = iou_threshold
        self._min_confidence = min_confidence

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(self, prediction: dict[str, Any]) -> dict[str, Any]:
        """Evaluate PPE compliance for every detected entity.

        Parameters
        ----------
        prediction : dict
            Output of :meth:`PredictionService.predict`.

        Returns
        -------
        dict
            Keys: ``image_path``, ``total_persons``, ``total_violations``,
            ``violations`` (list of per-person assessments), ``summary``.
        """
        detections: list[dict[str, Any]] = prediction.get("detections", [])

        # Filter by minimum confidence
        valid = [d for d in detections if d["confidence"] >= self._min_confidence]

        helmets = [d for d in valid if d["class_name"] == ClassName.HELMET]
        vests = [d for d in valid if d["class_name"] == ClassName.VEST]

        # When no person class is trained, treat every helmet / vest
        # region as an implicit person location and check for the
        # *other* PPE item nearby.  If the model **does** produce a
        # "person" class, swap in person-centric logic here.
        equipment_locations = self._merge_equipment_locations(helmets, vests)

        violations: list[dict[str, Any]] = []
        for loc in equipment_locations:
            result = self._assess(loc, helmets, vests)
            violations.append(result.to_dict())

        # Handle the edge-case where no equipment is detected at all
        # but there are other unknown detections (potential persons).
        if not equipment_locations and valid:
            for det in valid:
                if det["class_name"] not in (ClassName.HELMET, ClassName.VEST):
                    result = ViolationResult(
                        status=PPEStatus.NO_PPE,
                        has_helmet=False,
                        has_vest=False,
                        person_bbox=det["bounding_box"],
                    )
                    violations.append(result.to_dict())

        total_violations = sum(
            1 for v in violations if v["status"] != PPEStatus.SAFE.value
        )

        summary = self._build_summary(violations)

        logger.info(
            "Evaluated '%s': %d region(s), %d violation(s)",
            prediction.get("image_path", "unknown"),
            len(violations),
            total_violations,
        )

        return {
            "image_path": prediction.get("image_path", ""),
            "total_persons": len(violations),
            "total_violations": total_violations,
            "violations": violations,
            "summary": summary,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _nms(items: list[dict[str, Any]], iou_threshold: float = 0.5) -> list[dict[str, Any]]:
        if not items:
            return []
        items_sorted = sorted(items, key=lambda x: x["confidence"], reverse=True)
        keep = []
        for item in items_sorted:
            overlap = False
            for kept in keep:
                if _compute_iou(item["bounding_box"], kept["bounding_box"]) > iou_threshold:
                    overlap = True
                    break
            if not overlap:
                keep.append(item)
        return keep

    @staticmethod
    def _merge_equipment_locations(
        helmets: list[dict[str, Any]],
        vests: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build a list of approximate person locations from PPE detections.

        Each unique equipment bbox is treated as a potential person region.
        Duplicates are avoided by pairing closest helmets and vests.
        """
        import math
        
        # Apply NMS to remove duplicate overlapping boxes from YOLO
        helmets = PPEViolationEngine._nms(helmets)
        vests = PPEViolationEngine._nms(vests)
        
        locations: list[dict[str, Any]] = []
        used_vests: set[int] = set()

        for helmet in helmets:
            best_vest: dict[str, Any] | None = None
            min_dist: float = float('inf')
            best_vest_idx = -1

            hx_center = (helmet["bounding_box"]["x_min"] + helmet["bounding_box"]["x_max"]) / 2
            hy_center = (helmet["bounding_box"]["y_min"] + helmet["bounding_box"]["y_max"]) / 2
            h_height = helmet["bounding_box"]["height"]

            for idx, vest in enumerate(vests):
                if idx in used_vests:
                    continue
                vx_center = (vest["bounding_box"]["x_min"] + vest["bounding_box"]["x_max"]) / 2
                vy_center = (vest["bounding_box"]["y_min"] + vest["bounding_box"]["y_max"]) / 2
                v_height = vest["bounding_box"]["height"]
                
                # Distance between centers
                dist = math.hypot(hx_center - vx_center, hy_center - vy_center)
                
                # Dynamic threshold: The distance between a helmet and vest on the same person 
                # shouldn't exceed roughly the height of the vest + height of helmet.
                max_allowed_dist = (h_height + v_height) * 1.5
                
                # We expect the helmet to be above or slightly overlapping the vest (y increases downwards)
                # so hy_center should generally be < vy_center + some margin
                is_above = hy_center < vy_center + (v_height * 0.5)

                if dist < min_dist and dist < max_allowed_dist and is_above:
                    min_dist = dist
                    best_vest = vest
                    best_vest_idx = idx

            merged_bbox = helmet["bounding_box"]
            if best_vest is not None:
                merged_bbox = _union_bbox(helmet["bounding_box"], best_vest["bounding_box"])
                used_vests.add(best_vest_idx)

            locations.append({"bbox": merged_bbox, "helmet": helmet, "vest": best_vest})

        # Remaining unmatched vests
        for idx, vest in enumerate(vests):
            if idx not in used_vests:
                locations.append({"bbox": vest["bounding_box"], "helmet": None, "vest": vest})

        return locations

    def _assess(
        self,
        location: dict[str, Any],
        helmets: list[dict[str, Any]],
        vests: list[dict[str, Any]],
    ) -> ViolationResult:
        """Determine PPE status for a single person location."""
        has_helmet = location.get("helmet") is not None
        has_vest = location.get("vest") is not None

        matched: list[dict[str, Any]] = []
        if has_helmet:
            matched.append(location["helmet"])
        if has_vest:
            matched.append(location["vest"])

        if has_helmet and has_vest:
            status = PPEStatus.SAFE
        elif has_helmet and not has_vest:
            status = PPEStatus.NO_VEST
        elif has_vest and not has_helmet:
            status = PPEStatus.NO_HELMET
        else:
            status = PPEStatus.NO_PPE

        return ViolationResult(
            status=status,
            has_helmet=has_helmet,
            has_vest=has_vest,
            person_bbox=location["bbox"],
            matched_equipment=matched,
        )

    @staticmethod
    def _build_summary(violations: list[dict[str, Any]]) -> dict[str, int]:
        """Count violations by status."""
        summary: dict[str, int] = {s.value: 0 for s in PPEStatus}
        for v in violations:
            summary[v["status"]] = summary.get(v["status"], 0) + 1
        return summary


# ---------------------------------------------------------------------------
# Geometry utilities
# ---------------------------------------------------------------------------
def _compute_iou(a: dict[str, float], b: dict[str, float]) -> float:
    """Compute Intersection-over-Union between two bboxes (xyxy dicts)."""
    x1 = max(a["x_min"], b["x_min"])
    y1 = max(a["y_min"], b["y_min"])
    x2 = min(a["x_max"], b["x_max"])
    y2 = min(a["y_max"], b["y_max"])

    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = a["width"] * a["height"]
    area_b = b["width"] * b["height"]
    union = area_a + area_b - inter

    return inter / union if union > 0 else 0.0


def _union_bbox(a: dict[str, float], b: dict[str, float]) -> dict[str, float]:
    """Return the smallest bbox enclosing both *a* and *b*."""
    x_min = min(a["x_min"], b["x_min"])
    y_min = min(a["y_min"], b["y_min"])
    x_max = max(a["x_max"], b["x_max"])
    y_max = max(a["y_max"], b["y_max"])
    return {
        "x_min": round(x_min, 2),
        "y_min": round(y_min, 2),
        "x_max": round(x_max, 2),
        "y_max": round(y_max, 2),
        "width": round(x_max - x_min, 2),
        "height": round(y_max - y_min, 2),
    }
