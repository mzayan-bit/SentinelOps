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
                    
                    # Try to load the active model from the registry
                    from app.services.model_registry import model_registry_service
                    active_model = model_registry_service.get_active_model()
                    
                    if active_model:
                        default_path = active_model.path
                    else:
                        default_path = os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH)
                        
                    cls._instance._model_path: Path = Path(default_path)
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

    def switch_model(self, model_path: str | Path) -> None:
        """Dynamically switch the active YOLO model safely.
        
        Performs Health Verification by loading the model and running
        a warmup inference. If it fails, the active model is untouched
        and an exception is raised.
        """
        with self._lock:
            new_path = Path(model_path)
            if not new_path.exists():
                raise ModelNotFoundError(f"Model weights not found at '{new_path}'.")
            
            logger.info("Verifying new YOLO model at '%s' …", new_path)
            
            # 1. Load and Verify new model IN MEMORY (do not destroy active yet)
            try:
                temp_model = self._load_and_verify(new_path)
            except Exception as e:
                logger.error(f"Health Verification Failed for {new_path}: {e}")
                raise RuntimeError(f"Model rejected due to failing Health Verification: {e}")
                
            # 2. Verification passed! Safely swap.
            logger.info("Health Verification passed. Hot-swapping model.")
            if self._model is not None:
                self._unload()
                
            self._model_path = new_path
            self._model = temp_model

    def _unload(self) -> None:
        """Safely destroy the current model and release VRAM."""
        import gc
        import torch
        logger.info("Unloading YOLO model and clearing memory.")
        del self._model
        self._model = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            torch.mps.empty_cache()

    # -- Internal ----------------------------------------------------------

    def _load(self) -> YOLO:
        """Helper to load the default model."""
        return self._load_and_verify(self._model_path)

    def _load_and_verify(self, target_path: Path) -> YOLO:
        """Validate the path, load weights, run warmup/health check, and return the model."""
        import torch
        import numpy as np
        
        if not target_path.exists():
            raise ModelNotFoundError(
                f"Model weights not found at '{target_path}'. "
                "Set the MODEL_PATH environment variable to a valid .pt file."
            )

        # 1. Device Selection
        device_override = settings.device.lower()
        if device_override != "auto":
            device = device_override
        else:
            if torch.cuda.is_available():
                device = "cuda:0"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"

        logger.info("Loading YOLO model from '%s' onto device '%s' …", target_path, device)
        model = YOLO(str(target_path))
        
        # Override device if explicit
        model.to(device)

        logger.info(
            "Model loaded successfully (%d classes).",
            len(getattr(model, "names", {}))
        )
        
        # 2. Warmup & Health Verification
        logger.info("Running warmup inference / health verification...")
        dummy_input = np.zeros((640, 640, 3), dtype=np.uint8)
        model.predict(source=dummy_input, imgsz=640, verbose=False, device=device)
        logger.info("Warmup complete. Model is verified and ready.")
        
        return model
