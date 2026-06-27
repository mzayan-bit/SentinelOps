"""
SentinelOps — Track History Manager
======================================
Maintains lifecycle metrics for tracked individuals over time.
Designed to consume WorkerAssessments frame-by-frame.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from typing import Dict, List

from inference.compliance_engine import WorkerAssessment, ComplianceStatus

logger = logging.getLogger("sentinelops.track_history")


@dataclass
class PersonTrack:
    """Historical tracking metrics for a single individual."""
    track_id: int
    first_seen: float
    last_seen: float
    safe_frames: int = 0
    violation_frames: int = 0

    @property
    def compliance_score(self) -> float:
        """Percentage of frames where the person was fully compliant (0.0 to 1.0)."""
        total = self.safe_frames + self.violation_frames
        return self.safe_frames / total if total > 0 else 0.0

    @property
    def duration_seconds(self) -> float:
        """Total time this person has been tracked."""
        return max(0.0, self.last_seen - self.first_seen)


class TrackHistoryManager:
    """Stateful manager that accumulates frame assessments into person histories."""

    def __init__(self):
        self.tracks: Dict[int, PersonTrack] = {}

    def update_from_assessments(self, assessments: List[WorkerAssessment], timestamp_override: float | None = None) -> None:
        """Update track histories based on a frame's compliance assessments.

        Parameters
        ----------
        assessments : List[WorkerAssessment]
            The output from `ComplianceEngine.evaluate_frame`.
        timestamp_override : float | None
            Use a specific timestamp (useful for testing or syncing to video clock).
            If None, uses `time.time()`.
        """
        now = timestamp_override if timestamp_override is not None else time.time()

        for assessment in assessments:
            track_id = assessment.track_id
            
            if track_id is None:
                # We can't track history without a valid track_id
                continue

            # Initialize track if new
            if track_id not in self.tracks:
                self.tracks[track_id] = PersonTrack(
                    track_id=track_id,
                    first_seen=now,
                    last_seen=now,
                )
            
            track = self.tracks[track_id]
            track.last_seen = now

            if assessment.status == ComplianceStatus.SAFE:
                track.safe_frames += 1
            else:
                track.violation_frames += 1

    def get_all_tracks(self) -> List[PersonTrack]:
        """Return all historical tracks."""
        return list(self.tracks.values())

    def get_active_tracks(self, timeout_seconds: float = 5.0) -> List[PersonTrack]:
        """Return tracks that have been seen recently."""
        now = time.time()
        return [
            t for t in self.tracks.values() 
            if (now - t.last_seen) <= timeout_seconds
        ]

    def log_summary(self) -> None:
        """Log a summary of all tracked individuals."""
        all_tracks = self.get_all_tracks()
        if not all_tracks:
            logger.info("No persons tracked during this session.")
            return

        logger.info("--- Tracking History Summary ---")
        for t in all_tracks:
            score_pct = t.compliance_score * 100
            logger.info(
                f"Track ID: {t.track_id:3d} | "
                f"Duration: {t.duration_seconds:.1f}s | "
                f"Frames: {t.safe_frames + t.violation_frames:4d} | "
                f"Compliance: {score_pct:5.1f}%"
            )
        logger.info("--------------------------------")
