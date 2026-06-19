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
from utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIDENCE: float = 0.25
DEFAULT_TRACKER: str = "bytetrack.yaml"


class VideoTracker:
    """Video inference service with object tracking.

    Uses the singleton :class:`ModelLoader` to obtain the YOLO model and
    applies the internal ``.track()`` mechanism (e.g., ByteTrack) to maintain
    IDs across frames.

    Parameters
    ----------
    confidence : float
        Minimum confidence threshold for detections.
    """

    def __init__(self, confidence: float = DEFAULT_CONFIDENCE) -> None:
        self._loader = ModelLoader()
        self._confidence = confidence

    def process_video(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        show: bool = False,
        tracker_type: str = DEFAULT_TRACKER,
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

        frame_count = 0
        t0 = time.perf_counter()

        try:
            while True:
                success, frame = cap.read()
                if not success:
                    break

                frame_count += 1

                # model.track() automatically handles ByteTrack and assigns 'id'
                # to the boxes if persist=True.
                results = model.track(
                    frame,
                    persist=True,
                    tracker=tracker_type,
                    conf=self._confidence,
                    verbose=False,
                )

                # The plot() method will automatically render tracking IDs
                # alongside the bounding boxes and class names.
                annotated_frame = results[0].plot()

                if writer:
                    writer.write(annotated_frame)

                if show:
                    cv2.imshow("SentinelOps Tracking (ByteTrack)", annotated_frame)
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

            cap.release()
            if writer:
                writer.release()
            if show:
                cv2.destroyAllWindows()
