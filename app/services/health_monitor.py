import time
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class CameraHealth(BaseModel):
    camera_id: str
    status: str  # "online", "offline", "degraded"
    fps: float
    reconnect_attempts: int
    last_frame_timestamp: float
    stream_latency_ms: float

class HealthMonitorService:
    """
    Tracks and reports real-time health metrics for all camera streams.
    """
    def __init__(self):
        # Maps camera_id -> dict of internal health metrics
        self._health_data: Dict[str, Dict[str, Any]] = {}

    def _init_camera(self, camera_id: str):
        if camera_id not in self._health_data:
            self._health_data[camera_id] = {
                "status": "offline",
                "fps": 0.0,
                "reconnect_attempts": 0,
                "last_frame_timestamp": 0.0,
                "stream_latency_ms": 0.0,
            }

    def record_frame(self, camera_id: str, latency_ms: float, current_fps: float):
        """Called when a new frame is successfully processed."""
        self._init_camera(camera_id)
        data = self._health_data[camera_id]
        data["status"] = "online"
        data["last_frame_timestamp"] = time.time()
        data["stream_latency_ms"] = latency_ms
        data["fps"] = current_fps
        data["reconnect_attempts"] = 0

    def record_reconnect_attempt(self, camera_id: str):
        """Called when the connection to the stream drops and a retry happens."""
        self._init_camera(camera_id)
        data = self._health_data[camera_id]
        data["reconnect_attempts"] += 1
        data["status"] = "offline" if data["reconnect_attempts"] > 3 else "degraded"

    def record_offline(self, camera_id: str):
        """Explicitly marks a camera as offline."""
        self._init_camera(camera_id)
        self._health_data[camera_id]["status"] = "offline"
        self._health_data[camera_id]["fps"] = 0.0

    def get_health(self, camera_id: str) -> Optional[CameraHealth]:
        """Retrieves health metrics for a specific camera."""
        data = self._health_data.get(camera_id)
        if not data:
            return None
            
        # Dynamically calculate offline status if it's been too long since last frame
        if data["status"] == "online" and (time.time() - data["last_frame_timestamp"]) > 5.0:
            data["status"] = "offline"
            data["fps"] = 0.0
            
        return CameraHealth(camera_id=camera_id, **data)

    def get_all_health(self) -> Dict[str, CameraHealth]:
        """Retrieves health metrics for all tracked cameras."""
        return {cam_id: self.get_health(cam_id) for cam_id in self._health_data}

health_monitor = HealthMonitorService()
