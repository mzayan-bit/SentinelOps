"""
SentinelOps — Auto-Optimized Model Loader (Singleton)
=====================================================
Thread-safe singleton that loads an abstract inference engine exactly once.
Utilizes the AutoBackendSelector to dynamically benchmark and select the optimal
backend (PyTorch, ONNX, TensorRT, OpenVINO) for the current hardware environment.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

from config.settings import settings
from inference.engine.backend import InferenceBackend
from inference.engine.selector import AutoBackendSelector

logger = logging.getLogger("sentinelops.model_loader")
DEFAULT_MODEL_PATH = settings.model_path

class ModelNotFoundError(FileNotFoundError):
    """Raised when the configured model weights file does not exist."""

class ModelLoader:
    """Singleton Inference Backend loader."""

    _instance: ModelLoader | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> ModelLoader:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._backend: InferenceBackend | None = None
                    
                    from app.services.model_registry import model_registry_service
                    active_model = model_registry_service.get_active_model()
                    
                    if active_model:
                        default_path = active_model.path
                    else:
                        default_path = os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH)
                        
                    cls._instance._model_path: Path = Path(default_path)
        return cls._instance

    @property
    def model_path(self) -> Path:
        return self._model_path

    @property
    def is_loaded(self) -> bool:
        return self._backend is not None and self._backend.is_loaded

    def get_model(self) -> InferenceBackend:
        """Return the optimized Backend Engine, initialising and benchmarking it on first call."""
        if self._backend is None:
            with self._lock:
                if self._backend is None:
                    self._backend = self._load()
        return self._backend

    def switch_model(self, model_path: str | Path) -> None:
        """Dynamically switch the active model and trigger auto-benchmarking safely."""
        with self._lock:
            new_path = Path(model_path)
            if not new_path.exists():
                raise ModelNotFoundError(f"Model weights not found at '{new_path}'.")
            
            logger.info("Verifying and benchmarking new model at '%s' …", new_path)
            
            try:
                temp_backend = self._load_and_verify(new_path)
            except Exception as e:
                logger.error(f"Health Verification Failed for {new_path}: {e}")
                raise RuntimeError(f"Model rejected due to failing Health Verification: {e}")
                
            logger.info("Health Verification passed. Hot-swapping model.")
            if self._backend is not None:
                self._unload()
                
            self._model_path = new_path
            self._backend = temp_backend

    def _unload(self) -> None:
        if self._backend:
            self._backend.unload()
            self._backend = None

    def _load(self) -> InferenceBackend:
        return self._load_and_verify(self._model_path)

    def _load_and_verify(self, target_path: Path) -> InferenceBackend:
        if not target_path.exists():
            raise ModelNotFoundError(f"Model weights not found at '{target_path}'.")

        device_override = settings.device.lower()
        
        # This will instantiate, load, AND benchmark the engine against alternatives automatically
        backend = AutoBackendSelector.select_best_backend(
            model_path=str(target_path),
            device=device_override,
            run_benchmark=True # Perform rigorous benchmarking on load
        )
        
        return backend
