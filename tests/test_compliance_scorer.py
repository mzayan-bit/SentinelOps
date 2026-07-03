"""
SentinelOps — Compliance Scorer Tests
========================================
Verifies per-worker scoring, compliance percentage computation,
violation-type tracking, and aggregate summaries.
"""

import pytest
from inference.compliance_engine import ComplianceStatus, WorkerAssessment
from app.services.compliance_scorer import ComplianceScorer, WorkerScore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def scorer():
    """Fresh scorer for each test."""
    return ComplianceScorer()


def _assessment(track_id, status=ComplianceStatus.SAFE, **kw):
    """Shorthand factory for WorkerAssessment."""
    return WorkerAssessment(
        track_id=track_id,
        status=status,
        has_helmet=status in (ComplianceStatus.SAFE, ComplianceStatus.NO_VEST),
        has_vest=status in (ComplianceStatus.SAFE, ComplianceStatus.NO_HELMET),
        **kw,
    )


# ---------------------------------------------------------------------------
# WorkerScore dataclass
# ---------------------------------------------------------------------------
class TestWorkerScore:
    def test_compliance_percentage_no_observations(self):
        s = WorkerScore(track_id=1)
        assert s.compliance_percentage == 0.0

    def test_compliance_percentage_all_compliant(self):
        s = WorkerScore(track_id=1, total_observations=10, compliant_frames=10)
        assert s.compliance_percentage == 100.0

    def test_compliance_percentage_mixed(self):
        s = WorkerScore(track_id=1, total_observations=4, compliant_frames=3, violation_frames=1)
        assert s.compliance_percentage == 75.0

    def test_duration_seconds(self):
        s = WorkerScore(track_id=1, first_seen=100.0, last_seen=110.5)
        assert s.duration_seconds == 10.5

    def test_duration_clamps_negative(self):
        s = WorkerScore(track_id=1, first_seen=100.0, last_seen=90.0)
        assert s.duration_seconds == 0.0

    def test_to_dict(self):
        s = WorkerScore(
            track_id=5,
            total_observations=10,
            compliant_frames=8,
            violation_frames=2,
            first_seen=100.0,
            last_seen=110.0,
            violation_types={"NO_HELMET": 2},
        )
        d = s.to_dict()
        assert d["track_id"] == 5
        assert d["compliance_percentage"] == 80.0
        assert d["duration_seconds"] == 10.0
        assert d["violation_types"] == {"NO_HELMET": 2}


# ---------------------------------------------------------------------------
# ComplianceScorer — recording
# ---------------------------------------------------------------------------
class TestScorerRecord:
    def test_record_single_compliant(self, scorer):
        scorer.record([_assessment(1)], timestamp=100.0)
        s = scorer.get_score(1)
        assert s is not None
        assert s.total_observations == 1
        assert s.compliant_frames == 1
        assert s.violation_frames == 0
        assert s.compliance_percentage == 100.0

    def test_record_single_violation(self, scorer):
        scorer.record([_assessment(1, ComplianceStatus.NO_HELMET)], timestamp=100.0)
        s = scorer.get_score(1)
        assert s.total_observations == 1
        assert s.compliant_frames == 0
        assert s.violation_frames == 1
        assert s.compliance_percentage == 0.0
        assert s.violation_types == {"NO_HELMET": 1}

    def test_record_multiple_frames(self, scorer):
        # 3 safe, 1 violation
        for i in range(3):
            scorer.record([_assessment(1)], timestamp=100.0 + i)
        scorer.record([_assessment(1, ComplianceStatus.NO_VEST)], timestamp=103.0)

        s = scorer.get_score(1)
        assert s.total_observations == 4
        assert s.compliant_frames == 3
        assert s.violation_frames == 1
        assert s.compliance_percentage == 75.0
        assert s.first_seen == 100.0
        assert s.last_seen == 103.0

    def test_record_multiple_workers(self, scorer):
        scorer.record([
            _assessment(1, ComplianceStatus.SAFE),
            _assessment(2, ComplianceStatus.NO_HELMET),
            _assessment(3, ComplianceStatus.NO_PPE),
        ], timestamp=100.0)

        assert scorer.get_score(1).compliance_percentage == 100.0
        assert scorer.get_score(2).compliance_percentage == 0.0
        assert scorer.get_score(3).compliance_percentage == 0.0

    def test_record_ignores_none_track_id(self, scorer):
        scorer.record([_assessment(None)], timestamp=100.0)
        assert scorer.get_all_scores() == []

    def test_violation_types_accumulate(self, scorer):
        scorer.record([_assessment(1, ComplianceStatus.NO_HELMET)], timestamp=100.0)
        scorer.record([_assessment(1, ComplianceStatus.NO_HELMET)], timestamp=101.0)
        scorer.record([_assessment(1, ComplianceStatus.NO_VEST)], timestamp=102.0)

        s = scorer.get_score(1)
        assert s.violation_types == {"NO_HELMET": 2, "NO_VEST": 1}


# ---------------------------------------------------------------------------
# ComplianceScorer — queries
# ---------------------------------------------------------------------------
class TestScorerQueries:
    def test_get_score_missing(self, scorer):
        assert scorer.get_score(999) is None

    def test_get_all_scores_sorted_ascending(self, scorer):
        # Worker 1: 100% compliant, Worker 2: 50%, Worker 3: 0%
        scorer.record([_assessment(1)], timestamp=100.0)
        scorer.record([_assessment(2)], timestamp=100.0)
        scorer.record([_assessment(2, ComplianceStatus.NO_HELMET)], timestamp=101.0)
        scorer.record([_assessment(3, ComplianceStatus.NO_PPE)], timestamp=100.0)

        scores = scorer.get_all_scores()
        percentages = [s.compliance_percentage for s in scores]
        assert percentages == [0.0, 50.0, 100.0]

    def test_get_summary_empty(self, scorer):
        summary = scorer.get_summary()
        assert summary["total_workers"] == 0
        assert summary["average_compliance"] == 0.0

    def test_get_summary(self, scorer):
        # Worker 1: 100%, Worker 2: 0%
        scorer.record([_assessment(1)], timestamp=100.0)
        scorer.record([_assessment(2, ComplianceStatus.NO_HELMET)], timestamp=100.0)

        summary = scorer.get_summary()
        assert summary["total_workers"] == 2
        assert summary["average_compliance"] == 50.0
        assert summary["fully_compliant"] == 1
        assert summary["with_violations"] == 1


# ---------------------------------------------------------------------------
# ComplianceScorer — management
# ---------------------------------------------------------------------------
class TestScorerManagement:
    def test_reset(self, scorer):
        scorer.record([_assessment(1)], timestamp=100.0)
        assert len(scorer.get_all_scores()) == 1

        scorer.reset()
        assert len(scorer.get_all_scores()) == 0
        assert scorer.get_score(1) is None
