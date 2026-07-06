from abc import ABC, abstractmethod
from typing import Any, Dict, List
import logging
import numpy as np

logger = logging.getLogger("sentinelops.engine.backend")

class InferenceBackend(ABC):
    """
    Abstract base class for all AI execution backends (PyTorch, TensorRT, OpenVINO, etc.).
    Provides a standardized interface for loading, predicting, and unloading models,
    decoupling the rest of the application from specific inference libraries.
    """

    def __init__(self, model_path: str, device: str = "auto"):
        self.model_path = model_path
        self.device = device
        self.model = None
        self.is_loaded = False
        self.class_names: Dict[int, str] = {}

    @abstractmethod
    def load(self) -> None:
        """Load the model weights into memory/VRAM."""
        pass

    @abstractmethod
    def predict(self, image: np.ndarray, confidence: float, input_size: int) -> List[Dict[str, Any]]:
        """
        Run inference on a single numpy image array.
        
        Returns:
            A list of dictionary detections:
            [
                {
                    "class_id": int,
                    "class_name": str,
                    "confidence": float,
                    "bounding_box": {x_min, y_min, x_max, y_max, width, height}
                }, ...
            ]
        """
        pass

    @abstractmethod
    def unload(self) -> None:
        """Safely destroy the model and release memory/VRAM to prevent leaks."""
        pass


class UltralyticsBackend(InferenceBackend):
    """
    Standard PyTorch execution backend utilizing the Ultralytics YOLO engine.
    """
    def load(self) -> None:
        from ultralytics import YOLO
        import torch

        if self.device == "auto":
            if torch.cuda.is_available():
                self.device = "cuda:0"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"

        logger.info(f"[UltralyticsBackend] Loading YOLO model from {self.model_path} onto {self.device}...")
        self.model = YOLO(self.model_path)
        self.model.to(self.device)
        self.class_names = getattr(self.model, "names", {})
        self.is_loaded = True

    def predict(self, image: np.ndarray, confidence: float, input_size: int) -> List[Dict[str, Any]]:
        if not self.is_loaded or self.model is None:
            raise RuntimeError("Backend model is not loaded.")

        results = self.model.predict(
            source=image,
            conf=confidence,
            imgsz=input_size,
            verbose=False,
        )

        detections = []
        if not results:
            return detections

        boxes = results[0].boxes
        for box in boxes:
            xyxy = box.xyxy[0].tolist()
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            class_name = self.class_names.get(cls_id, f"class_{cls_id}")

            x_min, y_min, x_max, y_max = xyxy
            detections.append({
                "class_id": cls_id,
                "class_name": class_name,
                "confidence": conf,
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

    def unload(self) -> None:
        import gc
        import torch
        logger.info("[UltralyticsBackend] Unloading model and clearing VRAM.")
        del self.model
        self.model = None
        self.is_loaded = False
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            torch.mps.empty_cache()


class TensorRTBackend(InferenceBackend):
    """
    Architecture-ready placeholder for NVIDIA TensorRT execution backend.
    """
    def load(self) -> None:
        logger.info(f"[TensorRTBackend] Preparing TensorRT engine from {self.model_path}...")
        self.is_loaded = True

    def predict(self, image: np.ndarray, confidence: float, input_size: int) -> List[Dict[str, Any]]:
        return []

    def unload(self) -> None:
        self.is_loaded = False


class OpenVINOBackend(InferenceBackend):
    """
    Architecture-ready placeholder for Intel OpenVINO execution backend.
    """
    def load(self) -> None:
        logger.info(f"[OpenVINOBackend] Preparing OpenVINO engine from {self.model_path}...")
        self.is_loaded = True

    def predict(self, image: np.ndarray, confidence: float, input_size: int) -> List[Dict[str, Any]]:
        return []

    def unload(self) -> None:
        self.is_loaded = False


class ONNXBackend(InferenceBackend):
    """
    Architecture-ready placeholder for ONNX Runtime execution backend.
    """
    def load(self) -> None:
        logger.info(f"[ONNXBackend] Preparing ONNX session from {self.model_path}...")
        self.is_loaded = True

    def predict(self, image: np.ndarray, confidence: float, input_size: int) -> List[Dict[str, Any]]:
        return []

    def unload(self) -> None:
        self.is_loaded = False
