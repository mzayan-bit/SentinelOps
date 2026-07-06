import time
import psutil
import logging
import numpy as np
from typing import Dict, Any

from inference.engine.backend import InferenceBackend

logger = logging.getLogger("sentinelops.engine.benchmark")

class Benchmarker:
    """
    Automated utility to evaluate backend inference performance.
    Measures Latency, FPS, CPU usage, and Memory footprint using dummy inputs.
    """

    @staticmethod
    def run_benchmark(backend: InferenceBackend, warmup_iterations: int = 2, benchmark_iterations: int = 10, input_size: int = 640) -> Dict[str, Any]:
        """
        Executes a dummy workload on the provided backend to measure its performance profile.
        Assumes the backend has already been loaded.
        """
        if not backend.is_loaded:
            raise RuntimeError(f"Cannot benchmark unloaded backend: {type(backend).__name__}")

        dummy_input = np.zeros((input_size, input_size, 3), dtype=np.uint8)
        
        logger.info(f"[{type(backend).__name__}] Starting warmup ({warmup_iterations} iter)...")
        for _ in range(warmup_iterations):
            backend.predict(image=dummy_input, confidence=0.5, input_size=input_size)

        logger.info(f"[{type(backend).__name__}] Starting benchmark ({benchmark_iterations} iter)...")
        
        # Baseline resources
        process = psutil.Process()
        baseline_mem = process.memory_info().rss
        psutil.cpu_percent(interval=None) # reset cpu counter
        
        latencies = []
        for _ in range(benchmark_iterations):
            start = time.perf_counter()
            backend.predict(image=dummy_input, confidence=0.5, input_size=input_size)
            end = time.perf_counter()
            latencies.append((end - start) * 1000.0) # convert to ms
            
        peak_cpu = psutil.cpu_percent(interval=None)
        peak_mem = process.memory_info().rss
        memory_overhead_mb = max(0, (peak_mem - baseline_mem) / (1024 * 1024))
        
        avg_latency = float(np.mean(latencies))
        p95_latency = float(np.percentile(latencies, 95))
        p99_latency = float(np.percentile(latencies, 99))
        throughput_fps = 1000.0 / avg_latency if avg_latency > 0 else 0.0
        
        result = {
            "backend_class": type(backend).__name__,
            "average_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
            "p99_latency_ms": round(p99_latency, 2),
            "throughput_fps": round(throughput_fps, 2),
            "cpu_utilization_percent": peak_cpu,
            "memory_overhead_mb": round(memory_overhead_mb, 2)
        }
        
        logger.info(f"[{type(backend).__name__}] Benchmark complete: {throughput_fps:.1f} FPS | {avg_latency:.1f}ms Avg | {memory_overhead_mb:.1f}MB overhead")
        return result
