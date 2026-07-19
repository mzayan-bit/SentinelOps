"""
SentinelOps — Video Tracker
==============================
Object tracking pipeline for video streams using YOLO and ByteTrack.
Persists entity IDs across consecutive frames.

Usage::

    from inference.tracker import VideoTracker

    tracker = VideoTracker(confidence=0.3)
    tracker.process_video(
        input_path="test_assets/worker_video.mp4",
        output_path="output_detected.mp4",
        show=True
    )
"""

from __future__ import annotations

import threading
import base64
import asyncio
import time
from pathlib import Path
import cv2

from inference.model_loader import ModelLoader
from inference.compliance_engine import ComplianceEngine, ComplianceStatus
from inference.track_history import TrackHistoryManager
from inference.zone_engine import ZoneEngine
from inference.heatmap_generator import HeatmapGenerator
from inference.privacy_engine import PrivacyEngine
from app.services.stream_manager import stream_manager
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIDENCE: float = 0.25
DEFAULT_TRACKER: str = "bytetrack.yaml"

# Global lock for the underlying YOLO model to prevent parallel tracking crashes
_tracker_lock = threading.Lock()

class VideoTracker:
    def __init__(self, confidence: float = DEFAULT_CONFIDENCE) -> None:
        self._loader = ModelLoader()
        self._confidence = confidence
        self.track_history = TrackHistoryManager()
        self._compliance_engine = ComplianceEngine()
        self._stop_event = threading.Event()

    def stop(self) -> None:
        """Signal the tracking loop to stop."""
        self._stop_event.set()

    def process_video(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        show: bool = False,
        tracker_type: str = DEFAULT_TRACKER,
        zones: list[dict] | None = None,
        privacy_mode: bool | None = None,
        camera_id: str | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        input_p = Path(input_path)
        if not input_p.exists():
            raise FileNotFoundError(f"Video file not found: {input_p}")

        model = self._loader.get_model()

        cap = cv2.VideoCapture(str(input_p))
        if not cap.isOpened():
            raise FileNotFoundError(f"OpenCV failed to open video stream: {input_p}")

        self.track_history = TrackHistoryManager()
        zone_engine = ZoneEngine(zones or [])
        zone_violations_count = 0

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        logger.info(
            "Tracking started: '%s' (%dx%d @ %.1f FPS, ~%d frames)",
            input_p.name,
            width,
            height,
            fps,
            total_frames,
        )

        writer: cv2.VideoWriter | None = None
        if output_path:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(out_p), fourcc, fps, (width, height))
            logger.info("Saving annotated output to '%s'", out_p)

        use_privacy = privacy_mode if privacy_mode is not None else settings.enable_privacy_mode
        privacy_engine = PrivacyEngine() if use_privacy else None

        frame_count = 0
        t0 = time.perf_counter()
        
        # Determine actual FPS for loop pacing (fallback to 30)
        actual_fps = fps if fps and fps > 0 else 30.0
        frame_time = 1.0 / actual_fps

        try:
            heatmap_generator: HeatmapGenerator | None = None
            
            while not self._stop_event.is_set():
                loop_start = time.perf_counter()
                
                success, frame = cap.read()
                if not success:
                    # Loop video for continuous testing if we hit the end
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    success, frame = cap.read()
                    if not success:
                        break

                frame_count += 1
                
                if frame_count == 1:
                    heatmap_generator = HeatmapGenerator(width, height, background_frame=frame)

                with _tracker_lock:
                    if hasattr(model, "model") and model.model is not None:
                        results = model.model.track(
                            frame,
                            persist=True,
                            tracker=tracker_type,
                            conf=self._confidence,
                            verbose=False,
                        )
                    else:
                        raise RuntimeError("Backend does not expose a compatible model for tracking.")
                
                annotated_frame = frame
                current_violations = 0
                
                if results and len(results) > 0:
                    result = results[0]
                    assessments = self._compliance_engine.evaluate_frame(result)
                    self.track_history.update_from_assessments(assessments)
                    
                    for a in assessments:
                        if a.status != ComplianceStatus.SAFE:
                            current_violations += 1
                    
                    if heatmap_generator and result.boxes is not None:
                        for idx, box in enumerate(result.boxes):
                            xyxy = box.xyxy[0].tolist()
                            x_min, y_min, x_max, y_max = xyxy
                            bx = (x_min + x_max) / 2.0
                            by = y_max
                            heatmap_generator.add_movement_point(bx, by)
                            if idx < len(assessments) and assessments[idx].status != ComplianceStatus.SAFE:
                                heatmap_generator.add_violation_point(bx, by)
                    
                    zone_violations = zone_engine.evaluate_frame(result)
                    for v in zone_violations:
                        zone_violations_count += 1

                    annotated_frame = result.plot()

                if privacy_engine:
                    annotated_frame = privacy_engine.apply_privacy(annotated_frame)

                # Broadcast to WebSockets
                if camera_id and loop:
                    # Resize to 640x360 and compress heavily to prevent WebSocket buffer bloat
                    resized = cv2.resize(annotated_frame, (640, 360))
                    _, buffer = cv2.imencode(".jpg", resized, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                    frame_b64 = base64.b64encode(buffer).decode("utf-8")
                    payload = {
                        "frame": frame_b64,
                        "fps": actual_fps,
                        "violation_count": current_violations,
                        "detections": []
                    }
                    future = asyncio.run_coroutine_threadsafe(
                        stream_manager.broadcast(camera_id, payload), loop
                    )
                    try:
                        # Wait for the broadcast to finish to provide backpressure
                        future.result(timeout=1.0)
                    except Exception as e:
                        logger.warning(f"Failed to broadcast frame: {e}")

                if writer:
                    writer.write(annotated_frame)

                if show:
                    cv2.imshow("SentinelOps Pipeline", annotated_frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                        
                # Pace the loop to simulate real-time playback
                elapsed = time.perf_counter() - loop_start
                sleep_time = frame_time - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        finally:
            elapsed = time.perf_counter() - t0
            avg_fps = frame_count / elapsed if elapsed > 0 else 0

            logger.info("Tracking complete: processed %d frames (%.1f FPS)", frame_count, avg_fps)
            self.track_history.log_summary()
            
            if heatmap_generator:
                try:
                    heatmap_generator.save_heatmaps(output_dir="artifacts/heatmaps", prefix=input_p.stem)
                except Exception as e:
                    logger.error(f"Failed to generate heatmaps: {e}")

            cap.release()
            if writer:
                writer.release()
            if show:
                cv2.destroyAllWindows()
