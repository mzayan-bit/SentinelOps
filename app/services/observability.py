"""
SentinelOps — Enterprise AI Observability Engine
================================================
A thread-safe, high-performance in-memory metric aggregator for Datadog-style
telemetry, drift detection, and health monitoring.
"""

import threading
import time
from collections import deque
from typing import Dict, List, Optional
import numpy as np

from app.models.metrics import (
    ObservabilityMetrics,
    ProfilingMetrics,
    DriftMetrics,
    CameraMetrics,
)

class ObservabilityService:
    def __init__(self, history_window_size: int = 1000):
        self._lock = threading.Lock()
        
        self.history_window_size = history_window_size
        
        # Global Counters
        self.total_dropped_frames = 0
        self.total_detections = 0
        self.total_tracks = 0
        self.total_alerts = 0
        
        # Queues and buffers for profiling (sliding windows)
        self.latency_buffer: deque[float] = deque(maxlen=history_window_size)
        self.confidence_buffer_1h: deque[float] = deque(maxlen=5000)
        self.confidence_buffer_24h: deque[float] = deque(maxlen=20000)
        
        # Camera-specific counters
        # camera_id -> { "dropped": 0, "detections": 0, "alerts": 0, "latencies": deque, "last_frame_time": float }
        self.camera_stats: Dict[str, Dict] = {}

    def _get_or_create_camera_stats(self, camera_id: str):
        if camera_id not in self.camera_stats:
            self.camera_stats[camera_id] = {
                "dropped": 0,
                "detections": 0,
                "alerts": 0,
                "latencies": deque(maxlen=self.history_window_size),
                "last_frame_time": 0.0,
                "fps_buffer": deque(maxlen=100)
            }
        return self.camera_stats[camera_id]

    def record_inference(self, camera_id: str, latency_ms: float, confidences: List[float], detections_count: int, tracking_count: int):
        with self._lock:
            # Update global
            self.latency_buffer.append(latency_ms)
            self.total_detections += detections_count
            self.total_tracks += tracking_count
            
            # Update confidence buffers
            for c in confidences:
                self.confidence_buffer_1h.append(c)
                self.confidence_buffer_24h.append(c)
                
            # Update camera
            cstats = self._get_or_create_camera_stats(camera_id)
            cstats["detections"] += detections_count
            cstats["latencies"].append(latency_ms)
            
            now = time.time()
            if cstats["last_frame_time"] > 0:
                fps = 1.0 / max(now - cstats["last_frame_time"], 0.001)
                cstats["fps_buffer"].append(fps)
            cstats["last_frame_time"] = now

    def record_tracking(self, camera_id: str, count: int):
        with self._lock:
            self.total_tracks += count

    def record_alert(self, camera_id: str):
        with self._lock:
            self.total_alerts += 1
            cstats = self._get_or_create_camera_stats(camera_id)
            cstats["alerts"] += 1

    def record_frame_drop(self, camera_id: str, count: int = 1):
        with self._lock:
            self.total_dropped_frames += count
            if camera_id:
                cstats = self._get_or_create_camera_stats(camera_id)
                cstats["dropped"] += count

    def get_snapshot(self, current_queue_size: int = 0) -> ObservabilityMetrics:
        with self._lock:
            # Profiling Metrics
            lats = list(self.latency_buffer)
            if lats:
                avg_lat = float(np.mean(lats))
                p95_lat = float(np.percentile(lats, 95))
                p99_lat = float(np.percentile(lats, 99))
            else:
                avg_lat = p95_lat = p99_lat = 0.0

            prof = ProfilingMetrics(
                average_latency_ms=round(avg_lat, 2),
                p95_latency_ms=round(p95_lat, 2),
                p99_latency_ms=round(p99_lat, 2),
                throughput_fps=round(1000.0 / avg_lat, 2) if avg_lat > 0 else 0.0
            )
            
            # Drift Metrics
            conf_1h = list(self.confidence_buffer_1h)
            conf_24h = list(self.confidence_buffer_24h)
            avg_1h = float(np.mean(conf_1h)) if conf_1h else 0.0
            avg_24h = float(np.mean(conf_24h)) if conf_24h else 0.0
            
            # Simple drift rule: if 1h confidence drops by more than 15% compared to 24h baseline
            drift_detected = False
            if avg_24h > 0.0 and avg_1h < (avg_24h * 0.85) and len(conf_1h) > 100:
                drift_detected = True

            drift = DriftMetrics(
                avg_confidence_last_1h=round(avg_1h, 3),
                avg_confidence_last_24h=round(avg_24h, 3),
                confidence_drift_detected=drift_detected,
                anomalous_alert_spike=False # simplified
            )
            
            # Camera Metrics
            cam_metrics = []
            health_warnings = []
            for cid, cstats in self.camera_stats.items():
                cfps = list(cstats["fps_buffer"])
                clats = list(cstats["latencies"])
                avg_cfps = float(np.mean(cfps)) if cfps else 0.0
                avg_clats = float(np.mean(clats)) if clats else 0.0
                
                status = "ONLINE"
                if cstats["dropped"] > 50:
                    status = "DEGRADED"
                    health_warnings.append(f"Camera {cid} has {cstats['dropped']} dropped frames.")
                if avg_clats > 200:
                    status = "SLOW"
                    health_warnings.append(f"Camera {cid} inference latency is high ({round(avg_clats,2)}ms).")
                    
                cam_metrics.append(CameraMetrics(
                    camera_id=cid,
                    fps=round(avg_cfps, 2),
                    dropped_frames=cstats["dropped"],
                    latency_ms=round(avg_clats, 2),
                    total_detections=cstats["detections"],
                    total_alerts=cstats["alerts"],
                    status=status
                ))

            if drift_detected:
                health_warnings.append("Confidence drift detected. Model accuracy may be degrading.")

            return ObservabilityMetrics(
                queue_size=current_queue_size,
                dropped_frames_total=self.total_dropped_frames,
                total_detections=self.total_detections,
                total_tracks=self.total_tracks,
                total_alerts=self.total_alerts,
                profiling=prof,
                drift=drift,
                camera_metrics=cam_metrics,
                system_health_warnings=health_warnings
            )

# Singleton global instance
observability_engine = ObservabilityService()
