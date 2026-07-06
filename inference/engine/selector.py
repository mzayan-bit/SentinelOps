from typing import List, Type
import logging
from pathlib import Path

from inference.engine.backend import InferenceBackend, UltralyticsBackend, ONNXBackend, TensorRTBackend, OpenVINOBackend
from inference.engine.benchmark import Benchmarker

logger = logging.getLogger("sentinelops.engine.selector")

class AutoBackendSelector:
    """
    Intelligently analyzes the available hardware and model file format
    to select the optimal inference backend. Optionally runs the Benchmarker
    to definitively rank backends.
    """

    @staticmethod
    def get_compatible_backends(model_path: str) -> List[Type[InferenceBackend]]:
        """
        Determines which backends can potentially load the given model format.
        """
        path = Path(model_path)
        ext = path.suffix.lower()
        
        if ext == ".pt":
            return [UltralyticsBackend]
        elif ext == ".onnx":
            return [ONNXBackend, OpenVINOBackend, TensorRTBackend]
        elif ext == ".engine":
            return [TensorRTBackend]
        elif ext == ".xml": # OpenVINO format
            return [OpenVINOBackend]
            
        # Fallback to PyTorch for unknown or pt formats
        return [UltralyticsBackend]

    @staticmethod
    def select_best_backend(model_path: str, device: str = "auto", run_benchmark: bool = True) -> InferenceBackend:
        """
        Instantiates and returns the most optimal loaded backend.
        If `run_benchmark` is True, it will load and profile all compatible
        backends and return the fastest one.
        """
        compatible_classes = AutoBackendSelector.get_compatible_backends(model_path)
        
        if not compatible_classes:
            raise ValueError(f"No compatible backends found for {model_path}")

        # If only one compatible, skip benchmarking overhead
        if len(compatible_classes) == 1 or not run_benchmark:
            logger.info(f"[AutoBackendSelector] Selected {compatible_classes[0].__name__} directly.")
            backend = compatible_classes[0](model_path=model_path, device=device)
            backend.load()
            return backend

        logger.info(f"[AutoBackendSelector] Benchmarking {len(compatible_classes)} backends...")
        
        best_backend = None
        best_fps = -1.0
        
        # We instantiate, load, and benchmark each one
        # To avoid VRAM exhaustion, we MUST unload them after testing
        for backend_cls in compatible_classes:
            try:
                backend_instance = backend_cls(model_path=model_path, device=device)
                backend_instance.load()
                
                stats = Benchmarker.run_benchmark(backend_instance)
                throughput = stats["throughput_fps"]
                
                if throughput > best_fps:
                    best_fps = throughput
                    # If we already had a best_backend, unload it
                    if best_backend:
                        best_backend.unload()
                    best_backend = backend_instance
                else:
                    # Not the best, unload it immediately
                    backend_instance.unload()
            except Exception as e:
                logger.warning(f"[AutoBackendSelector] Failed to benchmark {backend_cls.__name__}: {e}")
                
        if best_backend is None:
            raise RuntimeError(f"All compatible backends failed to load or benchmark for {model_path}.")
            
        logger.info(f"[AutoBackendSelector] Optimal Backend Selected: {type(best_backend).__name__} (Score: {best_fps:.1f} FPS)")
        return best_backend
