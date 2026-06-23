import numpy as np
import time
from app.services.event_recorder import EventRecorderService

def test_rolling_buffer_caps_at_max():
    # 30 fps, 10s = 300 frames pre-buffer
    recorder = EventRecorderService(fps=30, pre_seconds=10, post_seconds=10)
    cam_id = "test_cam_01"
    
    # Create a dummy frame
    dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)
    
    # Push 400 frames (more than max)
    for _ in range(400):
        recorder.push_frame(cam_id, dummy_frame)
        
    assert len(recorder.pre_buffers[cam_id]) == 300
    assert not recorder.recording_states[cam_id]
    assert len(recorder.post_buffers[cam_id]) == 0

def test_trigger_collects_post_frames():
    recorder = EventRecorderService(fps=30, pre_seconds=2, post_seconds=2)
    cam_id = "test_cam_02"
    dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)
    
    # Push some pre frames
    for _ in range(30):
        recorder.push_frame(cam_id, dummy_frame)
        
    assert len(recorder.pre_buffers[cam_id]) == 30
    
    # Trigger
    recorder.trigger_recording(cam_id, metadata={"reason": "test"})
    assert recorder.recording_states[cam_id] is True
    
    # Push post frames, one less than max
    for _ in range(59):
        recorder.push_frame(cam_id, dummy_frame)
        
    # The background save thread shouldn't have dispatched yet
    assert recorder.recording_states[cam_id] is True
    assert len(recorder.post_buffers[cam_id]) == 59
    assert len(recorder.pre_buffers[cam_id]) == 30
    
    # Push the 60th frame to hit the limit (2 seconds * 30 fps = 60)
    recorder.push_frame(cam_id, dummy_frame)
    
    # Dispatch happens inside the push_frame lock, state resets immediately
    assert recorder.recording_states[cam_id] is False
    assert len(recorder.pre_buffers[cam_id]) == 0
    assert len(recorder.post_buffers[cam_id]) == 0
