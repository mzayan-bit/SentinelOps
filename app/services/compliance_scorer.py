"""
SentinelOps — Worker Compliance Scoring Service
===================================================
Maintains an in-memory scorecard for every tracked worker, aggregating
observations from the compliance engine into per-worker compliance
percentages.

This service is intentionally decoupled from the tracking layer — it
consumes ``WorkerAssessment`` objects and does not touch models or video.

Usage::

    from app.services.compliance_scorer import compliance_scorer

    # After each frame:
    compliance_scorer.record(assessments)

    # Query a single worker:
    score = compliance_scorer.get_score(track_id=7)

    # Leaderboard:
    all_scores = compliance_scorer.get_all_scores()
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from inference.compliance_engine import ComplianceStatus, WorkerAssessment

logger = logging.getLogger("sentinelops.compliance_scorer")


# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------
@dataclass
class WorkerScore:
    """Compliance scorecard for a single tracked worker."""

    track_id: int
    total_observations: int = 0
    compliant_frames: int = 0
    violation_frames: int = 0
    first_seen: float = 0.0
    last_seen: float = 0.0
    violation_types: dict[str, int] = field(default_factory=dict)

    @property
    def compliance_percentage(self) -> float:
        """Compliance as a percentage (0.0 – 100.0)."""
        if self.total_observations == 0:
            return 0.0
        return (self.compliant_frames / self.total_observations) * 100.0

    @property
    def duration_seconds(self) -> float:
        """Total tracked duration in seconds."""
        return max(0.0, self.last_seen - self.first_seen)

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "total_observations": self.total_observations,
            "compliant_frames": self.compliant_frames,
            "violation_frames": self.violation_frames,
            "compliance_percentage": round(self.compliance_percentage, 2),
            "duration_seconds": round(self.duration_seconds, 2),
            "violation_types": dict(self.violation_types),
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class ComplianceScorer:
    """Thread-safe, in-memory compliance scoring service.

    Call :meth:`record` after every frame to ingest worker assessments.
    Query scores via :meth:`get_score` or :meth:`get_all_scores`.
    """

    def __init__(self) -> None:
        self._scores: dict[int, WorkerScore] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def record(
        self,
        assessments: list[WorkerAssessment],
        timestamp: float | None = None,
    ) -> None:
        """Ingest a batch of assessments from one frame.

        Parameters
        ----------
        assessments
            Output of ``ComplianceEngine.evaluate_frame()``.
        timestamp
            Optional override (defaults to ``time.time()``).
        """
        now = timestamp if timestamp is not None else time.time()

        with self._lock:
            for a in assessments:
                if a.track_id is None:
                    continue

                if a.track_id not in self._scores:
                    self._scores[a.track_id] = WorkerScore(
                        track_id=a.track_id,
                        first_seen=now,
                        last_seen=now,
                    )

                score = self._scores[a.track_id]
                score.total_observations += 1
                score.last_seen = now

                if a.status == ComplianceStatus.SAFE:
                    score.compliant_frames += 1
                else:
                    score.violation_frames += 1
                    vtype = a.status.value
                    score.violation_types[vtype] = score.violation_types.get(vtype, 0) + 1

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_score(self, track_id: int) -> WorkerScore | None:
        """Return the score for a single worker, or ``None``."""
        with self._lock:
            return self._scores.get(track_id)

    def get_all_scores(self) -> list[WorkerScore]:
        """Return all scores, sorted by compliance percentage (ascending)."""
        with self._lock:
            return sorted(
                self._scores.values(),
                key=lambda s: s.compliance_percentage,
            )

    def get_summary(self) -> dict[str, Any]:
        """Aggregate summary across all workers."""
        with self._lock:
            scores = list(self._scores.values())

        if not scores:
            return {
                "total_workers": 0,
                "average_compliance": 0.0,
                "fully_compliant": 0,
                "with_violations": 0,
            }

        avg = sum(s.compliance_percentage for s in scores) / len(scores)
        fully = sum(1 for s in scores if s.violation_frames == 0)

        return {
            "total_workers": len(scores),
            "average_compliance": round(avg, 2),
            "fully_compliant": fully,
            "with_violations": len(scores) - fully,
        }

    # ------------------------------------------------------------------
    # Management
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all scores (e.g. between video sessions)."""
        with self._lock:
            self._scores.clear()
        logger.info("Compliance scores reset.")


# Module-level singleton
compliance_scorer = ComplianceScorer()
