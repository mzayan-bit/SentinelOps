"""
SentinelOps — Track History Tests
====================================
Tests for the stateful Person Tracking History manager.
"""

import pytest
import time
from inference.track_history import PersonTrack, TrackHistoryManager
from inference.compliance_engine import WorkerAssessment, ComplianceStatus


def test_person_track_compliance_score():
    t = PersonTrack(track_id=1, first_seen=0.0, last_seen=0.0)
    assert t.compliance_score == 0.0

    t.safe_frames = 10
    assert t.compliance_score == 1.0

    t.violation_frames = 10
    assert t.compliance_score == 0.5

    t.safe_frames = 90
    assert t.compliance_score == 0.9


def test_person_track_duration():
    t = PersonTrack(track_id=1, first_seen=100.0, last_seen=105.5)
    assert t.duration_seconds == 5.5

    # Edge case: negative duration should be clamped or at least 0.0
    t = PersonTrack(track_id=1, first_seen=100.0, last_seen=90.0)
    assert t.duration_seconds == 0.0


def test_manager_initialization():
    manager = TrackHistoryManager()
    assert len(manager.get_all_tracks()) == 0


def test_manager_update_new_tracks():
    manager = TrackHistoryManager()
    
    assessments = [
        WorkerAssessment(track_id=1, status=ComplianceStatus.SAFE, has_helmet=True, has_vest=True),
        WorkerAssessment(track_id=2, status=ComplianceStatus.NO_HELMET, has_helmet=False, has_vest=True),
    ]

    manager.update_from_assessments(assessments, timestamp_override=100.0)

    tracks = manager.get_all_tracks()
    assert len(tracks) == 2
    
    t1 = manager.tracks[1]
    assert t1.safe_frames == 1
    assert t1.violation_frames == 0
    assert t1.first_seen == 100.0

    t2 = manager.tracks[2]
    assert t2.safe_frames == 0
    assert t2.violation_frames == 1


def test_manager_update_existing_tracks():
    manager = TrackHistoryManager()
    
    # Frame 1
    assessments1 = [
        WorkerAssessment(track_id=1, status=ComplianceStatus.SAFE, has_helmet=True, has_vest=True),
    ]
    manager.update_from_assessments(assessments1, timestamp_override=100.0)

    # Frame 2 (Track 1 loses helmet, Track 3 appears)
    assessments2 = [
        WorkerAssessment(track_id=1, status=ComplianceStatus.NO_HELMET, has_helmet=False, has_vest=True),
        WorkerAssessment(track_id=3, status=ComplianceStatus.SAFE, has_helmet=True, has_vest=True),
    ]
    manager.update_from_assessments(assessments2, timestamp_override=101.0)

    t1 = manager.tracks[1]
    assert t1.safe_frames == 1
    assert t1.violation_frames == 1
    assert t1.first_seen == 100.0
    assert t1.last_seen == 101.0
    assert t1.duration_seconds == 1.0
    assert t1.compliance_score == 0.5

    t3 = manager.tracks[3]
    assert t3.first_seen == 101.0
    assert t3.last_seen == 101.0
    assert t3.safe_frames == 1


def test_manager_ignores_none_track_ids():
    manager = TrackHistoryManager()
    
    assessments = [
        WorkerAssessment(track_id=None, status=ComplianceStatus.SAFE, has_helmet=True, has_vest=True),
    ]
    
    manager.update_from_assessments(assessments)
    assert len(manager.get_all_tracks()) == 0


def test_manager_get_active_tracks():
    manager = TrackHistoryManager()
    now = time.time()
    
    # Track 1 updated 10 seconds ago
    manager.update_from_assessments(
        [WorkerAssessment(track_id=1, status=ComplianceStatus.SAFE, has_helmet=True, has_vest=True)],
        timestamp_override=now - 10.0
    )
    
    # Track 2 updated just now
    manager.update_from_assessments(
        [WorkerAssessment(track_id=2, status=ComplianceStatus.SAFE, has_helmet=True, has_vest=True)],
        timestamp_override=now
    )
    
    # Default timeout is 5.0s, so Track 1 should be inactive
    active = manager.get_active_tracks(timeout_seconds=5.0)
    assert len(active) == 1
    assert active[0].track_id == 2
