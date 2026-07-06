import cv2
import time
import asyncio
import logging
import threading
from pathlib import Path

from app.services.pipeline_core.context import PipelineContext
from app.services.pipeline_core.manager import PipelineManager
from inference.stages.preprocessing import PreprocessingStage
from inference.stages.inference import InferenceStage
from inference.stages.tracking import TrackingStage
from inference.stages.violation import ViolationStage
from inference.stages.alerting import AlertingStage
from inference.stages.visualization import VisualizationStage
from inference.stages.streaming import StreamingStage

from app.api.camera_routes import camera_manager

logger = logging.getLogger(__name__)

class DemoRunner:
    def __init__(self):
        self.stop_event = threading.Event()
        self.threads = []
        
        # Mapping fake camera IDs to local test assets
        self.cameras = [
            {"id": "CAM-MAIN-GATE", "name": "Main Entrance", "video": "test_assets/cam1.mp4"},
            {"id": "CAM-SCAFFOLDING-01", "name": "Scaffolding Zone A", "video": "test_assets/cam2.mp4"},
            {"id": "CAM-ZONE-B", "name": "Warehouse B", "video": "test_assets/cam3.mp4"},
            {"id": "CAM-LOADING-DOCK", "name": "Loading Dock", "video": "test_assets/cam4.mp4"},
        ]

    def _build_pipeline(self, main_loop: asyncio.AbstractEventLoop) -> PipelineManager:
        """Constructs the Pipeline Manager and registers all AI stages."""
        manager = PipelineManager(stages=[])
        manager.add_stage(PreprocessingStage(max_width=1280))
        manager.add_stage(InferenceStage())
        manager.add_stage(TrackingStage(max_age=15, iou_threshold=0.3))
        manager.add_stage(ViolationStage())
        manager.add_stage(AlertingStage())
        manager.add_stage(VisualizationStage(target_width=1280))
        manager.add_stage(StreamingStage(main_loop=main_loop))
        return manager

    def _run_camera_loop(self, cam_id: str, video_path: str, main_loop: asyncio.AbstractEventLoop):
        """Continuous thread looping over the video file with Frame Skipping (Backpressure)."""
        video_file = Path(video_path)
        if not video_file.exists():
            logger.error(f"Demo video not found: {video_path}")
            return
            
        cap = cv2.VideoCapture(str(video_file))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_time = 1.0 / fps
        
        # Each camera thread gets its own pipeline instance (though underlying models may be singletons)
        pipeline = self._build_pipeline(main_loop)
        
        logger.info(f"Started Enterprise Pipeline loop for {cam_id} using {video_path} at {fps} FPS")

        while not self.stop_event.is_set():
            start = time.time()
            ret, frame = cap.read()
            
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            # -------------------------------------------------------------
            # BACKPRESSURE / FRAME SKIPPING LOGIC
            # If the pipeline takes longer than 'frame_time' to process a frame,
            # we simply let the video loop continue reading (and effectively dropping) 
            # frames to catch up to real-time. We don't queue them.
            # -------------------------------------------------------------
            
            context = PipelineContext(camera_id=cam_id, original_frame=frame)
            pipeline.process(context)

            elapsed = time.time() - start
            sleep_time = frame_time - elapsed
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                # We are falling behind real-time. Calculate how many frames to skip.
                # E.g. If frame_time is 33ms and elapsed is 100ms, we should skip ~2 frames.
                frames_to_skip = int(-sleep_time // frame_time)
                if frames_to_skip > 0:
                    logger.debug(f"[{cam_id}] Pipeline overloaded (took {elapsed*1000:.1f}ms). Skipping {frames_to_skip} frames to maintain real-time.")
                    for _ in range(frames_to_skip):
                        cap.read() # Read and discard

        cap.release()

    def start(self):
        """Registers cameras and boots background threads."""
        from app.services.camera_manager import CameraStatus
        try:
            main_loop = asyncio.get_running_loop()
        except RuntimeError:
            main_loop = asyncio.get_event_loop()
            
        for cam in self.cameras:
            # Register in CameraManager
            try:
                cam_id = camera_manager.add_camera(source=cam["video"], name=cam["name"])
                # Set status to RUNNING for the demo dashboard KPIs
                camera_manager._cameras[cam_id].status = CameraStatus.RUNNING
                
                # Start background thread using the registered UUID
                t = threading.Thread(
                    target=self._run_camera_loop, 
                    args=(str(cam_id), cam["video"], main_loop),
                    daemon=True,
                    name=f"DemoRunner-{cam_id}"
                )
                self.threads.append(t)
                t.start()
            except Exception as e:
                logger.error(f"Failed to start demo camera {cam['name']}: {e}")

    def stop(self):
        """Stops all demo loops."""
        self.stop_event.set()
        for t in self.threads:
            t.join(timeout=2.0)
        self.threads.clear()

demo_runner = DemoRunner()
