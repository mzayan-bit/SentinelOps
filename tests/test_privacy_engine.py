"""
SentinelOps — Privacy Engine Tests
====================================
Tests for the CV face blurring module.
"""

import pytest
import numpy as np
import cv2
from inference.privacy_engine import PrivacyEngine

def test_privacy_engine_initialization():
    engine = PrivacyEngine()
    if getattr(cv2, 'CascadeClassifier', None) is not None:
        assert engine._is_ready is True
        assert not engine.face_cascade.empty()
    else:
        assert engine._is_ready is False
    
def test_privacy_engine_invalid_cascade():
    engine = PrivacyEngine(cascade_path="invalid_path.xml")
    if getattr(cv2, 'CascadeClassifier', None) is not None:
        assert engine._is_ready is True
        assert not engine.face_cascade.empty()
    else:
        assert engine._is_ready is False

def test_apply_privacy_no_faces():
    engine = PrivacyEngine()
    # Create a blank black frame (no faces)
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    processed = engine.apply_privacy(frame)
    
    # Ensure it doesn't crash and returns a frame of the same shape
    assert processed is not None
    assert processed.shape == (100, 100, 3)
    
    # Because there are no faces, the frame should be identical to the input
    assert np.array_equal(frame, processed)

def test_apply_privacy_empty_frame():
    engine = PrivacyEngine()
    frame = np.array([])
    processed = engine.apply_privacy(frame)
    assert processed.size == 0

def test_apply_privacy_none():
    engine = PrivacyEngine()
    processed = engine.apply_privacy(None)
    assert processed is None
