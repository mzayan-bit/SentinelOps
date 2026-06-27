import cv2
import threading
import json
import uuid
import time
from collections import deque
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class EventRecorderService:
    """
    Manages continuous rolling frame buffers for multiple cameras and
    asynchronously persists 20-second MP4 video clips (10s before, 10s after)
    when triggered by a violation.
    """
    def __init__(self, fps: int = 30, pre_seconds: int = 10, post_seconds: int = 10, base_dir: Path | None = None):
        from config.settings import settings
        self.base_dir = Path(base_dir) if base_dir else settings.events_dir
        self.fps = fps
        self.pre_max_frames = pre_seconds * fps
        self.post_max_frames = post_seconds * fps
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # State tracking per camera
        self.pre_buffers: Dict[str, deque] = {}
        self.post_buffers: Dict[str, List] = {}
        self.recording_states: Dict[str, bool] = {}
        self.metadata_cache: Dict[str, dict] = {}
        
        # Thread safety lock for managing state transitions
        self.lock = threading.Lock()

    def _init_camera(self, camera_id: str):
        """Initializes internal tracking buffers for a new camera source."""
        if camera_id not in self.pre_buffers:
            self.pre_buffers[camera_id] = deque(maxlen=self.pre_max_frames)
            self.post_buffers[camera_id] = []
            self.recording_states[camera_id] = False
            self.metadata_cache[camera_id] = None

    def push_frame(self, camera_id: str, frame: Any):
        """
        Ingests a frame continuously. Depending on the recording state, it either
        pushes to the rolling 'pre' buffer or collects into the 'post' buffer.
        """
        with self.lock:
            self._init_camera(camera_id)
            
            if self.recording_states[camera_id]:
                # Collect frames for the 'after' segment
                self.post_buffers[camera_id].append(frame)
                
                # Check if we have collected enough 'after' frames
                if len(self.post_buffers[camera_id]) >= self.post_max_frames:
                    self._dispatch_save(camera_id)
            else:
                # Normal rolling buffer
                self.pre_buffers[camera_id].append(frame)

    def trigger_recording(self, camera_id: str, metadata: dict):
        """
        Flags the camera to start collecting post-frames. The previous 10s
        are preserved in the rolling buffer automatically.
        """
        with self.lock:
            self._init_camera(camera_id)
            if not self.recording_states[camera_id]:
                self.recording_states[camera_id] = True
                self.metadata_cache[camera_id] = metadata
                logger.info(f"Event recording triggered for camera {camera_id}")

    def _dispatch_save(self, camera_id: str):
        """Copies buffers safely and submits the video encoder to the task worker."""
        from app.services.task_worker import task_worker

        pre_frames = list(self.pre_buffers[camera_id])
        post_frames = list(self.post_buffers[camera_id])
        metadata = self.metadata_cache[camera_id]
        
        # Reset state so the camera can immediately start buffering normal frames again
        self.pre_buffers[camera_id].clear()
        self.post_buffers[camera_id].clear()
        self.recording_states[camera_id] = False
        self.metadata_cache[camera_id] = None
        
        # Submit to unified task worker pool
        task_worker.submit(
            self._save_video_and_metadata,
            camera_id,
            pre_frames,
            post_frames,
            metadata,
            task_type="video_clip_export",
        )

    def _save_video_and_metadata(self, camera_id: str, pre_frames: list, post_frames: list, metadata: dict):
        """Heavy background task to write frames via OpenCV to MP4."""
        all_frames = pre_frames + post_frames
        if not all_frames:
            return

        now = datetime.now()
        date_path = self.base_dir / f"{now.year:04d}" / f"{now.month:02d}" / f"{now.day:02d}"
        date_path.mkdir(parents=True, exist_ok=True)
        
        file_id = f"{camera_id}_{now.strftime('%H%M%S')}_{uuid.uuid4().hex[:8]}"
        video_path = date_path / f"{file_id}.mp4"
        meta_path = date_path / f"{file_id}.json"
        
        try:
            # Assume all frames have identical shape (height, width, channels)
            height, width = all_frames[0].shape[:2]
            
            # Hardware-agnostic MP4 codec
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(str(video_path), fourcc, float(self.fps), (width, height))
            
            for frame in all_frames:
                writer.write(frame)
            
            writer.release()
            
            # Save metadata footprint
            full_meta = {
                "camera_id": camera_id,
                "timestamp": time.time(),
                "datetime": now.isoformat(),
                "video_path": str(video_path.relative_to(self.base_dir)),
                "total_frames": len(all_frames),
                **metadata
            }
            with open(meta_path, "w") as f:
                json.dump(full_meta, f, indent=2)
                
            logger.info(f"Successfully rendered event video: {video_path}")
            
        except Exception as e:
            logger.error(f"Failed to save event video for {camera_id}: {e}")

event_recorder = EventRecorderService()
