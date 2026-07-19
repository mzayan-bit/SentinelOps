"""
SentinelOps — PPE Compliance Rules
=====================================
Business rules that detect missing PPE by cross-referencing tracked
equipment detections.  The YOLO model produces two classes:

    0: reflective_jacket
    1: safety_helmet

There is NO person class.  Instead, each detected PPE item implies a
person at that location. A violation fires when one item is detected
without the complementary item nearby (e.g., helmet found but no vest
within spatial proximity → NO_VEST violation).
"""

import math
from typing import Dict, Any
from inference.rules.base_rule import BaseRule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _bbox_center(bbox: dict) -> tuple[float, float]:
    """Return (cx, cy) from a bounding_box dict."""
    return (
        (bbox["x_min"] + bbox["x_max"]) / 2,
        (bbox["y_min"] + bbox["y_max"]) / 2,
    )


def _bbox_height(bbox: dict) -> float:
    return bbox["y_max"] - bbox["y_min"]


def _has_nearby_class(
    anchor_bbox: tuple,
    target_class: str,
    detections: list,
    max_distance_factor: float = 3.0,
    anchor_height: float = 50.0,
) -> bool:
    """Check if *any* detection of `target_class` is spatially close to `anchor_bbox`."""
    ax, ay = anchor_bbox
    for det in detections:
        if det["class_name"] != target_class:
            continue
        bx, by = _bbox_center(det["bounding_box"])
        dist = math.hypot(ax - bx, ay - by)
        # Allow distance up to N× the anchor height (adaptive threshold)
        if dist < anchor_height * max_distance_factor:
            return True
    return False


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------
class HelmetRule(BaseRule):
    """Fires when a vest (reflective_jacket) is detected but NO safety_helmet
    is found nearby — indicating a worker without a hard hat."""

    @property
    def name(self) -> str:
        return "NO_HELMET"

    @property
    def priority(self) -> int:
        return 90

    @property
    def severity(self) -> str:
        return "HIGH"

    @property
    def cooldown_seconds(self) -> int:
        return 30

    @property
    def escalation_level(self) -> int:
        return 1

    @property
    def description(self) -> str:
        return "Worker detected wearing a vest but missing a safety helmet."

    @property
    def recommendation(self) -> str:
        return "Ensure all personnel in active zones wear hard hats."

    def evaluate(self, track: Dict[str, Any], context: "PipelineContext") -> float:
        # Only evaluate tracks that are vests (i.e., we see a vest → is there a helmet?)
        if track.get("class_name") != "reflective_jacket":
            return 0.0

        bbox = track["bbox"]  # [x1, y1, x2, y2] from tracker
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        height = bbox[3] - bbox[1]

        # Look for a safety_helmet above / near this vest
        has_helmet = _has_nearby_class(
            anchor_bbox=(cx, cy),
            target_class="safety_helmet",
            detections=context.detections,
            max_distance_factor=2.5,
            anchor_height=max(height, 40),
        )

        if has_helmet:
            return 0.0  # Compliant — has both vest and helmet

        # Violation: vest without helmet
        return track.get("confidence", 0.7)


class VestRule(BaseRule):
    """Fires when a safety_helmet is detected but NO reflective_jacket
    is found nearby — indicating a worker without a vest."""

    @property
    def name(self) -> str:
        return "NO_VEST"

    @property
    def priority(self) -> int:
        return 80

    @property
    def severity(self) -> str:
        return "MEDIUM"

    @property
    def cooldown_seconds(self) -> int:
        return 30

    @property
    def escalation_level(self) -> int:
        return 0

    @property
    def description(self) -> str:
        return "Worker detected wearing a helmet but missing a high-visibility vest."

    @property
    def recommendation(self) -> str:
        return "Verify high-visibility vests are worn on the floor."

    def evaluate(self, track: Dict[str, Any], context: "PipelineContext") -> float:
        # Only evaluate tracks that are helmets
        if track.get("class_name") != "safety_helmet":
            return 0.0

        bbox = track["bbox"]  # [x1, y1, x2, y2] from tracker
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        height = bbox[3] - bbox[1]

        # Look for a reflective_jacket below / near this helmet
        has_vest = _has_nearby_class(
            anchor_bbox=(cx, cy),
            target_class="reflective_jacket",
            detections=context.detections,
            max_distance_factor=3.0,
            anchor_height=max(height, 40),
        )

        if has_vest:
            return 0.0  # Compliant

        # Violation: helmet without vest
        return track.get("confidence", 0.7)
