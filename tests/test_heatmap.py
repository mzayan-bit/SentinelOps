"""
SentinelOps — Heatmap Generator Tests
====================================
Tests for the CV heatmap aggregation and rendering logic.
"""

import pytest
import numpy as np
from pathlib import Path
from inference.heatmap_generator import HeatmapGenerator

def test_heatmap_initialization():
    gen = HeatmapGenerator(width=100, height=50)
    assert gen.width == 100
    assert gen.height == 50
    assert gen.background_frame.shape == (50, 100, 3)
    assert gen.movement_accumulator.shape == (50, 100)
    assert gen.violation_accumulator.shape == (50, 100)
    
def test_heatmap_initialization_with_background():
    bg = np.ones((50, 100, 3), dtype=np.uint8) * 128
    gen = HeatmapGenerator(width=100, height=50, background_frame=bg)
    assert np.all(gen.background_frame == 128)
    
def test_add_points():
    gen = HeatmapGenerator(width=100, height=50)
    
    # Valid points
    gen.add_movement_point(10.5, 20.2)
    gen.add_violation_point(10.1, 20.9)
    
    # Out of bounds points (should not crash)
    gen.add_movement_point(-1, 0)
    gen.add_movement_point(100, 50)
    gen.add_violation_point(0, -5)
    
    assert gen.movement_accumulator[20, 10] == 1.0
    assert gen.violation_accumulator[20, 10] == 1.0
    
    # Sum of accumulators should only be 1 (since out-of-bounds were ignored)
    assert np.sum(gen.movement_accumulator) == 1.0
    assert np.sum(gen.violation_accumulator) == 1.0

def test_generate_overlays():
    gen = HeatmapGenerator(width=100, height=50)
    
    # Add a cluster of points
    for i in range(10):
        gen.add_movement_point(50, 25)
        gen.add_violation_point(20, 10)
        
    movement_img = gen.generate_movement_heatmap()
    violation_img = gen.generate_violation_hotspot()
    
    # Ensure they return 3-channel images of the correct shape
    assert movement_img.shape == (50, 100, 3)
    assert violation_img.shape == (50, 100, 3)
    assert movement_img.dtype == np.uint8

def test_save_heatmaps(tmp_path):
    gen = HeatmapGenerator(width=100, height=50)
    gen.add_movement_point(50, 25)
    
    out_dir = tmp_path / "heatmaps"
    gen.save_heatmaps(out_dir, prefix="test")
    
    assert (out_dir / "test_movement_heatmap.jpg").exists()
    assert (out_dir / "test_violation_hotspot.jpg").exists()
