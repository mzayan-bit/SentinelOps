"""
SentinelOps — YOLO Model Loader (Singleton)
=============================================
Thread-safe singleton that loads a YOLO model exactly once and
exposes it for inference throughout the application lifetime.

Usage::

    from inference.model_loader import ModelLoader

    loader = ModelLoader()          # same instance every time
    model  = loader.get_model()     # loads on first call, cached after
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

from ultralytics import YOLO

logger = logging.getLogger("sentinelops.model_loader")

from config.settings import settings
DEFAULT_MODEL_PATH = settings.model_path


class ModelNotFoundError(FileNotFoundError):
    """Raised when the configured model weights file does not exist."""


class ModelLoader:
    """Singleton YOLO model loader.

    The model path is read from the ``MODEL_PATH`` environment variable,
    falling back to ``models/best.pt``.  The actual weights are loaded
    lazily on the first call to :meth:`get_model` and reused thereafter.
    """

    _instance: ModelLoader | None = None
    _lock: threading.Lock = threading.Lock()

    # -- Singleton ---------------------------------------------------------

    def __new__(cls) -> ModelLoader:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._model: YOLO | None = None
                    cls._instance._model_path: Path = Path(
                        os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH)
                    )
        return cls._instance

    # -- Public API --------------------------------------------------------

    @property
    def model_path(self) -> Path:
        """Resolved path to the YOLO weights file."""
        return self._model_path

    @property
    def is_loaded(self) -> bool:
        """Whether the model has already been loaded into memory."""
        return self._model is not None

    def get_model(self) -> YOLO:
        """Return the loaded YOLO model, initialising it on first call.

        Raises
        ------
        ModelNotFoundError
            If the weights file does not exist on disk.
        """
        if self._model is None:
            with self._lock:
                if self._model is None:
                    self._model = self._load()
        return self._model

    # -- Internal ----------------------------------------------------------

    def _load(self) -> YOLO:
        """Validate the path, load weights, and log the result."""
        if not self._model_path.exists():
            raise ModelNotFoundError(
                f"Model weights not found at '{self._model_path}'. "
                "Set the MODEL_PATH environment variable to a valid .pt file."
            )

        logger.info("Loading YOLO model from '%s' …", self._model_path)
        model = YOLO(str(self._model_path))
        logger.info(
            "Model loaded successfully (%d classes, device=%s).",
            len(getattr(model, "names", {})),
            next(model.model.parameters()).device,
        )
        return model
