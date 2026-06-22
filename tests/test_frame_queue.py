import time
import pytest
import threading
from app.services.frame_queue import CameraFrameQueue

def test_queue_initialization():
    q = CameraFrameQueue(camera_id="cam_01", max_size=10)
    metrics = q.get_metrics()
    assert metrics["camera_id"] == "cam_01"
    assert metrics["queue_size"] == 0
    assert metrics["dropped_frames"] == 0
    assert metrics["fps"] == 0.0

def test_frame_dropping_strategy():
    q = CameraFrameQueue(camera_id="cam_02", max_size=3)
    # Don't start the consumer thread, just fill the queue
    
    q.put_frame("frame_1")
    q.put_frame("frame_2")
    q.put_frame("frame_3")
    
    metrics = q.get_metrics()
    assert metrics["queue_size"] == 3
    assert metrics["dropped_frames"] == 0
    
    # Adding 4th frame should drop frame_1
    q.put_frame("frame_4")
    metrics = q.get_metrics()
    assert metrics["queue_size"] == 3
    assert metrics["dropped_frames"] == 1

def test_consumer_processing():
    processed_frames = []
    
    def mock_callback(frame):
        processed_frames.append(frame)

    q = CameraFrameQueue(camera_id="cam_03", max_size=10, process_callback=mock_callback)
    q.start()
    
    q.put_frame("A")
    q.put_frame("B")
    
    # Give the thread a moment to process
    time.sleep(0.1)
    
    q.stop()
    
    assert processed_frames == ["A", "B"]
    metrics = q.get_metrics()
    assert metrics["total_processed"] == 2
    assert metrics["queue_size"] == 0

def test_fps_calculation():
    def dummy_callback(frame):
        pass

    q = CameraFrameQueue(camera_id="cam_04", max_size=100, process_callback=dummy_callback)
    q.start()
    
    # Send 10 frames
    for i in range(10):
        q.put_frame(f"frame_{i}")
        
    time.sleep(0.2)
    q.stop()
    
    metrics = q.get_metrics()
    # It processed 10 frames in ~0.2 seconds -> FPS > 0
    assert metrics["fps"] > 0
    assert metrics["total_processed"] == 10
