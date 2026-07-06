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

        model = self._loader.get_model()

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
        
        # YOLO model.predict() is NOT thread-safe. We must lock it!
        with self._inference_lock:
            results = model.predict(
                source=img_array,
                conf=min_conf,
                imgsz=self._input_size,
                verbose=False,
            )

        elapsed_ms = (time.perf_counter() - t0) * 1000

        detections = self._parse_results(results, model, explicit_confidence=confidence)

        logger.info(
            "Inference complete: %d detection(s) in %.1f ms",
            len(detections),
            elapsed_ms,
        )

        return {
            "image_path": source_name,
            "image_width": w,
            "image_height": h,
            "num_detections": len(detections),
            "detections": detections,
            "inference_time_ms": round(elapsed_ms, 2),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_results(
        results: list,
        model: Any,
        explicit_confidence: float | None = None
    ) -> list[dict[str, Any]]:
        """Convert raw YOLO results into a list of detection dicts."""
        from app.services.threshold_service import threshold_service
        detections: list[dict[str, Any]] = []

        if not results:
            return detections

        class_names: dict[int, str] = getattr(model, "names", {})
        boxes = results[0].boxes

        config = threshold_service.get_config()

        for box in boxes:
            xyxy = box.xyxy[0].tolist()
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            class_name = class_names.get(cls_id, f"class_{cls_id}")
            
            # Filter dynamically
            if explicit_confidence is not None:
                required_conf = explicit_confidence
            else:
                required_conf = config.per_class.get(class_name, config.global_threshold)

            if conf < required_conf:
                continue

            x_min, y_min, x_max, y_max = xyxy

            detections.append({
                "class_id": cls_id,
                "class_name": class_name,
                "confidence": round(conf, 4),
                "bounding_box": {
                    "x_min": round(x_min, 2),
                    "y_min": round(y_min, 2),
                    "x_max": round(x_max, 2),
                    "y_max": round(y_max, 2),
                    "width": round(x_max - x_min, 2),
                    "height": round(y_max - y_min, 2),
                },
            })

        return detections
