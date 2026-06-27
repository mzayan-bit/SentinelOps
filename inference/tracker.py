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

import time
from pathlib import Path

import cv2

from inference.model_loader import ModelLoader
from inference.compliance_engine import ComplianceEngine, ComplianceStatus
from inference.track_history import TrackHistoryManager
from inference.zone_engine import ZoneEngine
from inference.heatmap_generator import HeatmapGenerator
from inference.privacy_engine import PrivacyEngine
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIDENCE: float = 0.25
DEFAULT_TRACKER: str = "bytetrack.yaml"


class VideoTracker:
    """Video inference service with object tracking.

    Uses the singleton :class:`ModelLoader` to obtain the YOLO model and
    applies the internal ``.track()`` mechanism (e.g., ByteTrack) to maintain
    IDs across frames. Also tracks PPE compliance history per person.

    Parameters
    ----------
    confidence : float
        Minimum confidence threshold for detections.
    """

    def __init__(self, confidence: float = DEFAULT_CONFIDENCE) -> None:
        self._loader = ModelLoader()
        self._confidence = confidence
        self.track_history = TrackHistoryManager()
        self._compliance_engine = ComplianceEngine()

    def process_video(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        show: bool = False,
        tracker_type: str = DEFAULT_TRACKER,
        zones: list[dict] | None = None,
        privacy_mode: bool | None = None,
    ) -> None:
        """Run tracking on a video file.

        Parameters
        ----------
        input_path : str | Path
            Path to the source video file.
        output_path : str | Path | None
            If provided, the annotated video will be saved here.
        show : bool
            If True, display the video live using OpenCV window.
        tracker_type : str
            Tracking algorithm config. Usually 'bytetrack.yaml' or 'botsort.yaml'.
        zones: list[dict] | None
            Configured polygon zones for evaluation.
        privacy_mode : bool | None
            If True, faces will be blurred in the output video. If None, checks settings.

        Raises
        ------
        FileNotFoundError
            If ``input_path`` does not exist or OpenCV cannot open it.
        """
        input_p = Path(input_path)
        if not input_p.exists():
            raise FileNotFoundError(f"Video file not found: {input_p}")

        model = self._loader.get_model()

        cap = cv2.VideoCapture(str(input_p))
        if not cap.isOpened():
            raise FileNotFoundError(f"OpenCV failed to open video stream: {input_p}")

        # Reset history for a fresh video run
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
            # Use mp4v for standard MP4 writing
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(out_p), fourcc, fps, (width, height))
            logger.info("Saving annotated output to '%s'", out_p)

        # Privacy mode configuration
        use_privacy = privacy_mode if privacy_mode is not None else settings.enable_privacy_mode
        privacy_engine = PrivacyEngine() if use_privacy else None

        frame_count = 0
        t0 = time.perf_counter()

        try:
            heatmap_generator: HeatmapGenerator | None = None
            
            while True:
                success, frame = cap.read()
                if not success:
                    break

                frame_count += 1
                
                if frame_count == 1:
                    heatmap_generator = HeatmapGenerator(width, height, background_frame=frame)

                # model.track() automatically handles ByteTrack and assigns 'id'
                # to the boxes if persist=True.
                results = model.track(
                    frame,
                    persist=True,
                    tracker=tracker_type,
                    conf=self._confidence,
                    verbose=False,
                )
                
                annotated_frame = frame
                if results and len(results) > 0:
                    result = results[0]
                    # Evaluate compliance and update history
                    assessments = self._compliance_engine.evaluate_frame(result)
                    self.track_history.update_from_assessments(assessments)
                    
                    # Feed Heatmaps
                    if heatmap_generator and result.boxes is not None:
                        for idx, box in enumerate(result.boxes):
                            # Bottom-center coordinate for movement
                            xyxy = box.xyxy[0].tolist()
                            x_min, y_min, x_max, y_max = xyxy
                            bx = (x_min + x_max) / 2.0
                            by = y_max
                            heatmap_generator.add_movement_point(bx, by)
                            
                            # Check if this specific box had a violation this frame
                            if idx < len(assessments) and assessments[idx].status != ComplianceStatus.SAFE:
                                heatmap_generator.add_violation_point(bx, by)
                    
                    # Evaluate zone entry/dwell time
                    zone_violations = zone_engine.evaluate_frame(result)
                    for v in zone_violations:
                        zone_violations_count += 1
                        logger.warning(
                            f"[Zone Breach] Person {v.track_id} in {v.zone_name} (Dwell: {v.dwell_time:.1f}s)"
                        )

                    # YOLO's built-in plotting helper
                    annotated_frame = result.plot()

                # Apply Privacy Face Blurring (if enabled)
                if privacy_engine:
                    annotated_frame = privacy_engine.apply_privacy(annotated_frame)

                # Visualization / Export
                if writer:
                    writer.write(annotated_frame)

                if show:
                    cv2.imshow("SentinelOps Pipeline", annotated_frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        logger.info("User interrupted video playback.")
                        break

        finally:
            elapsed = time.perf_counter() - t0
            actual_fps = frame_count / elapsed if elapsed > 0 else 0

            logger.info(
                "Tracking complete: processed %d frames in %.1fs (%.1f FPS)",
                frame_count,
                elapsed,
                actual_fps,
            )
            
            # Log the person tracking history summary
            self.track_history.log_summary()
            
            # Generate and save Heatmaps
            if heatmap_generator:
                try:
                    heatmap_generator.save_heatmaps(
                        output_dir="artifacts/heatmaps", 
                        prefix=input_p.stem
                    )
                except Exception as e:
                    logger.error(f"Failed to generate heatmaps: {e}")

            cap.release()
            if writer:
                writer.release()
            if show:
                cv2.destroyAllWindows()
