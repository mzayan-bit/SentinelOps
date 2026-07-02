import uuid
import logging
import asyncio
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from app.services.task_worker import task_worker
from inference.tracker import VideoTracker

logger = logging.getLogger(__name__)

class CameraStatus(Enum):
    """Lifecycle states for a camera source."""
    REGISTERED = "REGISTERED"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"

@dataclass
class Camera:
    """
    Represents a registered video source (RTSP, file, or device).
    
    Attributes:
        source (str): The video source URL or path.
        name (str): Human-readable name for the camera.
        id (uuid.UUID): Automatically assigned unique identifier.
        status (CameraStatus): Current operational status.
    """
    source: str
    name: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: CameraStatus = CameraStatus.REGISTERED

class CameraManager:
    """
    Service for managing multiple camera video streams.
    
    Provides capabilities to register new sources, start/stop them,
    and retrieve their current status without modifying the underlying
    model detection logic.
    """

    def __init__(self):
        # Maps camera UUID to the Camera instance
        self._cameras: Dict[uuid.UUID, Camera] = {}
        # Maps camera UUID to its active VideoTracker instance
        self._trackers: Dict[uuid.UUID, VideoTracker] = {}

    def add_camera(self, source: str, name: str) -> uuid.UUID:
        """
        Registers a new camera source and assigns it a UUID.
        
        Args:
            source (str): RTSP stream URL, device ID, or file path.
            name (str): Friendly name for the camera.
            
        Returns:
            uuid.UUID: The uniquely assigned ID for the new camera.
        """
        camera = Camera(source=source, name=name)
        self._cameras[camera.id] = camera
        logger.info(f"Added camera '{name}' with ID {camera.id}")
        return camera.id

    def remove_camera(self, camera_id: uuid.UUID) -> bool:
        """
        Stops and removes a camera from the manager.
        
        Args:
            camera_id (uuid.UUID): The UUID of the camera to remove.
            
        Returns:
            bool: True if removed successfully, False if not found.
        """
        if camera_id not in self._cameras:
            logger.warning(f"Attempted to remove unknown camera: {camera_id}")
            return False
            
        # Ensure it's stopped before removing
        if self._cameras[camera_id].status == CameraStatus.RUNNING:
            self.stop_camera(camera_id)
            
        del self._cameras[camera_id]
        logger.info(f"Removed camera {camera_id}")
        return True

    def start_camera(self, camera_id: uuid.UUID) -> bool:
        """
        Starts processing for the specified camera.
        
        Args:
            camera_id (uuid.UUID): The UUID of the camera to start.
            
        Returns:
            bool: True if successfully started, False otherwise.
            
        Raises:
            ValueError: If the camera_id is not registered.
        """
        if camera_id not in self._cameras:
            raise ValueError(f"Camera with ID {camera_id} not found.")
            
        camera = self._cameras[camera_id]
        if camera.status == CameraStatus.RUNNING:
            logger.info(f"Camera {camera_id} is already running.")
            return True
            
        camera.status = CameraStatus.RUNNING
        logger.info(f"Started camera {camera_id} ({camera.name})")

        # Start the video tracker in the background
        tracker = VideoTracker()
        self._trackers[camera_id] = tracker
        
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        task_worker.submit(
            tracker.process_video,
            input_path=camera.source,
            camera_id=str(camera_id),
            loop=loop,
            task_type="camera_stream"
        )
        
        return True

    def stop_camera(self, camera_id: uuid.UUID) -> bool:
        """
        Stops processing for the specified camera.
        
        Args:
            camera_id (uuid.UUID): The UUID of the camera to stop.
            
        Returns:
            bool: True if successfully stopped, False otherwise.
            
        Raises:
            ValueError: If the camera_id is not registered.
        """
        if camera_id not in self._cameras:
            raise ValueError(f"Camera with ID {camera_id} not found.")
            
        camera = self._cameras[camera_id]
        if camera.status != CameraStatus.RUNNING:
            logger.info(f"Camera {camera_id} is not currently running.")
            return True
            
        camera.status = CameraStatus.STOPPED
        logger.info(f"Stopped camera {camera_id} ({camera.name})")
        
        # Stop the tracker loop
        if camera_id in self._trackers:
            self._trackers[camera_id].stop()
            del self._trackers[camera_id]
            
        return True

    def get_camera_status(self, camera_id: uuid.UUID) -> Optional[CameraStatus]:
        """
        Retrieves the current status of a specific camera.
        
        Args:
            camera_id (uuid.UUID): The UUID of the camera.
            
        Returns:
            Optional[CameraStatus]: The status, or None if not found.
        """
        camera = self._cameras.get(camera_id)
        return camera.status if camera else None

    def list_cameras(self) -> List[Camera]:
        """
        Returns a list of all registered cameras.
        
        Returns:
            List[Camera]: A list of all camera configurations.
        """
        return list(self._cameras.values())
