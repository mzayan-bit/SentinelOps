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
        self._loader = ModelLoader()
        self._default_conf = confidence
        self._input_size = input_size

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(
        self,
        image_path: str | Path,
        confidence: float | None = None,
    ) -> dict[str, Any]:
        """Run inference on a single image.

        Parameters
        ----------
        image_path : str | Path
            Path to an image file (JPEG, PNG, etc.).
        confidence : float | None
            Override the default confidence threshold for this call.

        Returns
        -------
        dict
            Structured result with keys:
            ``image_path``, ``image_width``, ``image_height``,
            ``num_detections``, ``detections``, ``inference_time_ms``.

        Raises
        ------
        FileNotFoundError
            If ``image_path`` does not exist.
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        conf = confidence if confidence is not None else self._default_conf
        model = self._loader.get_model()

        # Load image
        img = Image.open(path).convert("RGB")
        img_array = np.asarray(img)
        h, w = img_array.shape[:2]

        logger.info("Running inference on '%s' (conf=%.2f) …", path.name, conf)

        t0 = time.perf_counter()
        results = model.predict(
            source=img_array,
            conf=conf,
            imgsz=self._input_size,
            verbose=False,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        detections = self._parse_results(results, model)

        logger.info(
            "Inference complete: %d detection(s) in %.1f ms",
            len(detections),
            elapsed_ms,
        )

        return {
            "image_path": str(path),
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
    ) -> list[dict[str, Any]]:
        """Convert raw YOLO results into a list of detection dicts."""
        detections: list[dict[str, Any]] = []

        if not results:
            return detections

        class_names: dict[int, str] = getattr(model, "names", {})
        boxes = results[0].boxes

        for box in boxes:
            xyxy = box.xyxy[0].tolist()
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())

            x_min, y_min, x_max, y_max = xyxy

            detections.append({
                "class_id": cls_id,
                "class_name": class_names.get(cls_id, f"class_{cls_id}"),
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
