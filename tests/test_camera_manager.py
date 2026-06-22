import uuid
import pytest
from app.services.camera_manager import CameraManager, CameraStatus

def test_add_camera():
    manager = CameraManager()
    cam_id = manager.add_camera("rtsp://admin:admin@192.168.1.100/stream", "Gate 1")
    
    assert isinstance(cam_id, uuid.UUID)
    cameras = manager.list_cameras()
    assert len(cameras) == 1
    assert cameras[0].id == cam_id
    assert cameras[0].name == "Gate 1"
    assert cameras[0].source == "rtsp://admin:admin@192.168.1.100/stream"
    assert cameras[0].status == CameraStatus.REGISTERED

def test_remove_camera():
    manager = CameraManager()
    cam_id = manager.add_camera("rtsp://dummy", "Dummy")
    
    # Successful removal
    assert manager.remove_camera(cam_id) is True
    assert len(manager.list_cameras()) == 0
    
    # Remove non-existent
    assert manager.remove_camera(uuid.uuid4()) is False

def test_remove_running_camera_stops_it_first():
    manager = CameraManager()
    cam_id = manager.add_camera("rtsp://dummy", "Dummy")
    manager.start_camera(cam_id)
    
    # Should stop it internally, then remove
    assert manager.remove_camera(cam_id) is True
    assert len(manager.list_cameras()) == 0

def test_start_and_stop_camera():
    manager = CameraManager()
    cam_id = manager.add_camera("rtsp://dummy", "Dummy")
    
    # Start
    assert manager.start_camera(cam_id) is True
    assert manager.get_camera_status(cam_id) == CameraStatus.RUNNING
    
    # Stop
    assert manager.stop_camera(cam_id) is True
    assert manager.get_camera_status(cam_id) == CameraStatus.STOPPED

def test_start_non_existent_camera_raises_error():
    manager = CameraManager()
    with pytest.raises(ValueError, match="not found"):
        manager.start_camera(uuid.uuid4())

def test_stop_non_existent_camera_raises_error():
    manager = CameraManager()
    with pytest.raises(ValueError, match="not found"):
        manager.stop_camera(uuid.uuid4())

def test_get_camera_status_returns_none_for_missing():
    manager = CameraManager()
    assert manager.get_camera_status(uuid.uuid4()) is None

def test_list_cameras_returns_all():
    manager = CameraManager()
    manager.add_camera("cam1", "Camera 1")
    manager.add_camera("cam2", "Camera 2")
    
    cameras = manager.list_cameras()
    assert len(cameras) == 2
    assert set(c.name for c in cameras) == {"Camera 1", "Camera 2"}
