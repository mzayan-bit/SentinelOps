"""
SentinelOps — YOLO Prediction Service
========================================
Stateless prediction service that wraps the singleton
:class:`ModelLoader` and returns structured detection results.

Usage::

    from inference.predictor import PredictionService

    service = PredictionService()
    result  = service.predict("path/to/image.jpg")
    result  = service.predict("path/to/image.jpg", confidence=0.5)

    for det in result["detections"]:
        print(det["class_name"], det["confidence"], det["bounding_box"])
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from inference.model_loader import ModelLoader

logger = logging.getLogger("sentinelops.predictor")

# Default confidence threshold
DEFAULT_CONFIDENCE: float = 0.25
DEFAULT_INPUT_SIZE: int = 640


class PredictionService:
    """Run YOLO inference and return structured results.

    The underlying model is obtained from :class:`ModelLoader` (singleton),
    so it is loaded exactly once regardless of how many ``PredictionService``
    instances are created.

    Parameters
    ----------
    confidence : float
        Default minimum confidence threshold (can be overridden per call).
    input_size : int
        Image size passed to the model (pixels).
    """

    def __init__(
        self,
        confidence: float = DEFAULT_CONFIDENCE,
        input_size: int = DEFAULT_INPUT_SIZE,
    ) -> None:
        import threading
        self._loader = ModelLoader()
        self._default_conf = confidence
        self._input_size = input_size
        self._inference_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(
        self,
        image_source: str | Path | np.ndarray,
        confidence: float | None = None,
    ) -> dict[str, Any]:
        """Run inference on a single image.

        Parameters
        ----------
        image_source : str | Path | np.ndarray
            Path to an image file or a loaded numpy array.
        confidence : float | None
            Override the default confidence threshold for this call.

        Returns
        -------
        dict
            Structured result.
        """
        from app.services.threshold_service import threshold_service
        
        if confidence is not None:
            min_conf = confidence
        else:
            min_conf = threshold_service.get_min_threshold()

        backend = self._loader.get_model()

        if isinstance(image_source, (str, Path)):
            path = Path(image_source)
            if not path.exists():
                raise FileNotFoundError(f"Image not found: {path}")
            img = Image.open(path).convert("RGB")
            img_array = np.asarray(img)
            source_name = path.name
        else:
            img_array = image_source
            source_name = "live_frame"
            
        h, w = img_array.shape[:2]

        logger.info("Running inference on '%s' (conf=%.2f) …", source_name, min_conf)

        t0 = time.perf_counter()
        
        # Backend execution is locked internally if necessary, but we lock here
        # to ensure serial pipeline execution if strictly desired.
        with self._inference_lock:
            detections = backend.predict(
                image=img_array,
                confidence=min_conf,
                input_size=self._input_size,
            )

        elapsed_ms = (time.perf_counter() - t0) * 1000

        # We no longer need _parse_results because the backend abstraction standardizes the output!
        # We just dynamically filter detections that don't meet per-class thresholds
        config = threshold_service.get_config()
        filtered_detections = []
        for det in detections:
            class_name = det["class_name"]
            if confidence is not None:
                required_conf = confidence
            else:
                required_conf = config.per_class.get(class_name, config.global_threshold)
                
            if det["confidence"] >= required_conf:
                filtered_detections.append(det)

        logger.info(
            "Inference complete: %d detection(s) in %.1f ms",
            len(filtered_detections),
            elapsed_ms,
        )

        return {
            "image_path": source_name,
            "image_width": w,
            "image_height": h,
            "num_detections": len(filtered_detections),
            "detections": filtered_detections,
            "inference_time_ms": round(elapsed_ms, 2),
        }
