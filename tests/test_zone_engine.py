"""
SentinelOps — Zone Engine Tests
====================================
Tests for the CV polygon zone engine logic.
"""

import pytest
import numpy as np
from inference.zone_engine import ZoneEngine, ZoneConfig

class MockBox:
    def __init__(self, track_id, x_min, y_min, x_max, y_max):
        import torch
        self.id = torch.tensor([track_id])
        self.xyxy = torch.tensor([[x_min, y_min, x_max, y_max]])

class MockResults:
    def __init__(self, boxes):
        self.boxes = boxes


def test_zone_engine_entry_and_dwell():
    zones_data = [{
        "id": "zone-1",
        "name": "Danger Zone",
        "points_json": "[[0, 0], [100, 0], [100, 100], [0, 100]]",
        "is_restricted": False,
        "max_dwell_time": 5
    }]
    
    engine = ZoneEngine(zones_data)
    
    # Frame 1: Person enters the zone (bottom center of bbox is inside)
    # Bbox: 40,40, 60,60 -> Bottom center is 50, 60 (Inside 0-100 rect)
    results1 = MockResults([MockBox(1, 40, 40, 60, 60)])
    
    violations1 = engine.evaluate_frame(results1, timestamp_override=100.0)
    assert len(violations1) == 0  # Just entered, no dwell violation yet
    assert 1 in engine.entry_records
    assert "zone-1" in engine.entry_records[1]
    
    # Frame 2: Person dwells for 6 seconds (exceeds max_dwell_time of 5)
    violations2 = engine.evaluate_frame(results1, timestamp_override=106.0)
    assert len(violations2) == 1
    assert violations2[0].violation_type == "DWELL_TIME_EXCEEDED"
    assert violations2[0].dwell_time == 6.0
    
    # Frame 3: Person still there, but violation already emitted (should not spam)
    violations3 = engine.evaluate_frame(results1, timestamp_override=107.0)
    assert len(violations3) == 0
    
    # Frame 4: Person exits the zone
    # Bbox: 110,110, 120,120 -> Bottom center is 115, 120 (Outside)
    results2 = MockResults([MockBox(1, 110, 110, 120, 120)])
    violations4 = engine.evaluate_frame(results2, timestamp_override=108.0)
    assert len(violations4) == 0
    assert "zone-1" not in engine.entry_records.get(1, {})


def test_zone_engine_restricted_entry():
    zones_data = [{
        "id": "zone-2",
        "name": "Restricted Area",
        "points_json": "[[0, 0], [10, 0], [10, 10], [0, 10]]",
        "is_restricted": True,
        "max_dwell_time": None
    }]
    
    engine = ZoneEngine(zones_data)
    
    # Bottom center: 5, 5 (Inside)
    results = MockResults([MockBox(2, 0, 0, 10, 5)])
    
    violations = engine.evaluate_frame(results, timestamp_override=200.0)
    assert len(violations) == 1
    assert violations[0].violation_type == "RESTRICTED_ENTRY"
    assert violations[0].dwell_time == 0.0


def test_zone_engine_track_cleanup():
    zones_data = [{
        "id": "zone-3",
        "name": "Cleanup Zone",
        "points_json": "[[0, 0], [100, 0], [100, 100], [0, 100]]",
        "is_restricted": False,
        "max_dwell_time": 10
    }]
    
    engine = ZoneEngine(zones_data)
    
    # Track 1 enters
    engine.evaluate_frame(MockResults([MockBox(1, 50, 50, 60, 60)]), timestamp_override=100.0)
    assert 1 in engine.entry_records
    
    # Track 1 disappears, Track 2 appears
    engine.evaluate_frame(MockResults([MockBox(2, 10, 10, 20, 20)]), timestamp_override=101.0)
    
    # Track 1 should be cleaned up
    assert 1 not in engine.entry_records
    assert 2 in engine.entry_records
