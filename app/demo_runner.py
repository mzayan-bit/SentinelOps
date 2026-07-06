import cv2
import base64
import time
import asyncio
import logging
import threading
from pathlib import Path
from app.services.pipeline import InferencePipeline
from app.services.stream_manager import stream_manager
from app.api.camera_routes import camera_manager

logger = logging.getLogger(__name__)

# Colors (BGR)
COLOR_SAFE = (0, 255, 0)
COLOR_WARNING = (0, 165, 255)
COLOR_DANGER = (0, 0, 255)

class DemoRunner:
    def __init__(self):
        self.pipeline = InferencePipeline()
        self.stop_event = threading.Event()
        self.threads = []
        
        # Mapping fake camera IDs to local test assets
        self.cameras = [
            {"id": "CAM-MAIN-GATE", "name": "Main Entrance", "video": "test_assets/cam1.mp4"},
            {"id": "CAM-SCAFFOLDING-01", "name": "Scaffolding Zone A", "video": "test_assets/cam2.mp4"},
            {"id": "CAM-ZONE-B", "name": "Warehouse B", "video": "test_assets/cam3.mp4"},
            {"id": "CAM-LOADING-DOCK", "name": "Loading Dock", "video": "test_assets/cam4.mp4"},
        ]

    def _draw_boxes(self, frame, prediction, assessment):
        """Draws bounding boxes based on raw detections and violations."""
        
        # 1. Resize large frames (like 1080p) down to 720p or 480p for WebSocket streaming
        h, w = frame.shape[:2]
        if w > 1280:
            scale = 1280 / w
            frame = cv2.resize(frame, (1280, int(h * scale)))

        scale_w = 1280 / w if w > 1280 else 1.0
        scale_h = 1280 / w if w > 1280 else 1.0

        # 2. Draw actual PPE detections (what YOLO actually saw)
        for det in prediction.get("detections", []):
            bbox = det["bounding_box"]
            cls_name = det["class_name"]
            
            x1 = int(bbox["x_min"] * scale_w)
            y1 = int(bbox["y_min"] * scale_h)
            x2 = int(bbox["x_max"] * scale_w)
            y2 = int(bbox["y_max"] * scale_h)
            
            # Green for helmet, Yellow for vest
            color = (0, 255, 255) if "vest" in cls_name.lower() or "jacket" in cls_name.lower() else COLOR_SAFE
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, cls_name, (x1, max(y1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
        # 3. Draw red outlines for the violation regions
        for v in assessment.get("violations", []):
            if v["status"] != "SAFE":
                bbox = v["person_bbox"]
                x1 = int(bbox["x_min"] * scale_w)
                y1 = int(bbox["y_min"] * scale_h)
                x2 = int(bbox["x_max"] * scale_w)
                y2 = int(bbox["y_max"] * scale_h)
                
                # Draw a distinct red bounding box for the violation area
                cv2.rectangle(frame, (x1, y1), (x2, y2), COLOR_DANGER, 3)
                cv2.putText(frame, f"VIOLATION: {v['status']}", (x1, max(y1 - 25, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_DANGER, 2)
                
        return frame

    def _run_camera_loop(self, cam_id: str, video_path: str, main_loop: asyncio.AbstractEventLoop):
        """Continuous thread looping over the video file."""
        video_file = Path(video_path)
        if not video_file.exists():
            logger.error(f"Demo video not found: {video_path}")
            return
            
        cap = cv2.VideoCapture(str(video_file))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_time = 1.0 / fps
        
        logger.info(f"Started loop for {cam_id} using {video_path} at {fps} FPS")

        logger.info(f"Started loop for {cam_id} using {video_path} at {fps} FPS")

        while not self.stop_event.is_set():
            start = time.time()
            ret, frame = cap.read()
            
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            prediction, assessment = self.pipeline.process_frame(cam_id, frame)
            annotated_frame = self._draw_boxes(frame, prediction, assessment)
            
            _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            b64_image = base64.b64encode(buffer).decode('utf-8')
            
            payload = {
                "camera_id": cam_id,
                "timestamp": time.time(),
                "fps": round(fps, 1),
                "violation_count": assessment.get("total_violations", 0),
                "frame": b64_image
            }
            
            # Broadcast to Connected Clients safely on the main loop
            asyncio.run_coroutine_threadsafe(
                stream_manager.broadcast(cam_id, payload), 
                main_loop
            )

            elapsed = time.time() - start
            sleep_time = frame_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

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
