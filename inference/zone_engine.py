"""
SentinelOps — Polygon Zone Engine
====================================
Evaluates bounding boxes against configured polygonal zones.
Tracks entry, dwell time, and triggers zone violation events.
"""

from __future__ import annotations

import json
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import cv2
import numpy as np

logger = logging.getLogger("sentinelops.zone_engine")

@dataclass
class ZoneConfig:
    """Decoupled Zone configuration."""
    zone_id: str
    name: str
    points: np.ndarray  # Shape: (N, 1, 2) dtype=np.int32 for cv2
    is_restricted: bool
    max_dwell_time: int | None

    @classmethod
    def from_dict(cls, data: dict) -> ZoneConfig:
        """Parse from dictionary (e.g., from DB model)."""
        pts = json.loads(data["points_json"])
        # Format required by cv2.pointPolygonTest
        pts_array = np.array(pts, np.int32).reshape((-1, 1, 2))
        
        return cls(
            zone_id=str(data["id"]),
            name=data["name"],
            points=pts_array,
            is_restricted=data.get("is_restricted", False),
            max_dwell_time=data.get("max_dwell_time"),
        )

@dataclass
class ZoneViolation:
    """Event generated when a zone rule is broken."""
    zone_id: str
    zone_name: str
    track_id: int
    violation_type: str  # "RESTRICTED_ENTRY" or "DWELL_TIME_EXCEEDED"
    dwell_time: float


class ZoneEngine:
    """Stateful engine that monitors tracking IDs inside configured zones."""

    def __init__(self, zones: List[dict]):
        """
        Parameters
        ----------
        zones : List[dict]
            List of dictionaries representing ZoneModel objects.
        """
        self.zones: List[ZoneConfig] = [ZoneConfig.from_dict(z) for z in zones]
        
        # Dictionary mapping: track_id -> { zone_id -> entry_timestamp }
        self.entry_records: Dict[int, Dict[str, float]] = {}
        
        # Keep track of violations already emitted to prevent spamming
        # format: (track_id, zone_id, violation_type)
        self.emitted_violations: set = set()

    def evaluate_frame(self, result: Any, timestamp_override: float | None = None) -> List[ZoneViolation]:
        """Evaluate a frame of YOLO tracking results against all zones.

        Parameters
        ----------
        result
            A single `ultralytics.engine.results.Results` object.
        timestamp_override
            Current timestamp. If None, uses time.time().
            
        Returns
        -------
        List[ZoneViolation]
            Any new violations detected in this frame.
        """
        now = timestamp_override if timestamp_override is not None else time.time()
        violations: List[ZoneViolation] = []
        
        if not self.zones or result.boxes is None:
            return violations

        active_track_ids = set()

        for box in result.boxes:
            if box.id is None:
                continue
                
            track_id = int(box.id[0].item())
            active_track_ids.add(track_id)
            
            # Use the bottom-center of the bounding box as the person's location
            xyxy = box.xyxy[0].tolist()
            x_min, y_min, x_max, y_max = xyxy
            bottom_center_x = (x_min + x_max) / 2.0
            bottom_center_y = y_max
            
            point = (float(bottom_center_x), float(bottom_center_y))

            for zone in self.zones:
                # measureMeasure >= 0 means the point is inside or on the edge
                # False = return distance (if True, returns +1/-1/0)
                dist = cv2.pointPolygonTest(zone.points, point, False)
                is_inside = dist >= 0

                if is_inside:
                    violations.extend(self._handle_inside(track_id, zone, now))
                else:
                    self._handle_outside(track_id, zone)

        # Cleanup: Remove records for tracks that no longer exist
        # Note: If the tracker lost them briefly, their entry time is reset.
        dead_tracks = [tid for tid in self.entry_records.keys() if tid not in active_track_ids]
        for tid in dead_tracks:
            del self.entry_records[tid]
            # Also cleanup spam-prevention set
            to_remove = [v for v in self.emitted_violations if v[0] == tid]
            for r in to_remove:
                self.emitted_violations.remove(r)

        return violations

    def _handle_inside(self, track_id: int, zone: ZoneConfig, now: float) -> List[ZoneViolation]:
        violations = []
        
        if track_id not in self.entry_records:
            self.entry_records[track_id] = {}
            
        if zone.zone_id not in self.entry_records[track_id]:
            # First time entering this zone
            self.entry_records[track_id][zone.zone_id] = now
            logger.debug(f"Track {track_id} entered zone {zone.name}")

            # Check for restricted entry violation
            if zone.is_restricted:
                v_key = (track_id, zone.zone_id, "RESTRICTED_ENTRY")
                if v_key not in self.emitted_violations:
                    violations.append(ZoneViolation(
                        zone_id=zone.zone_id,
                        zone_name=zone.name,
                        track_id=track_id,
                        violation_type="RESTRICTED_ENTRY",
                        dwell_time=0.0
                    ))
                    self.emitted_violations.add(v_key)
        else:
            # Person has been in the zone, check dwell time
            entry_time = self.entry_records[track_id][zone.zone_id]
            dwell_time = now - entry_time
            
            if zone.max_dwell_time is not None and dwell_time > zone.max_dwell_time:
                v_key = (track_id, zone.zone_id, "DWELL_TIME_EXCEEDED")
                if v_key not in self.emitted_violations:
                    violations.append(ZoneViolation(
                        zone_id=zone.zone_id,
                        zone_name=zone.name,
                        track_id=track_id,
                        violation_type="DWELL_TIME_EXCEEDED",
                        dwell_time=dwell_time
                    ))
                    self.emitted_violations.add(v_key)
                    
        return violations

    def _handle_outside(self, track_id: int, zone: ZoneConfig):
        """If the person is outside, clear their entry record for this zone."""
        if track_id in self.entry_records and zone.zone_id in self.entry_records[track_id]:
            del self.entry_records[track_id][zone.zone_id]
            logger.debug(f"Track {track_id} exited zone {zone.name}")
