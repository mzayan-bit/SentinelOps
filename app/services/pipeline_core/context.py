from dataclasses import dataclass, field
from typing import Any, Dict, List
import time

@dataclass
class PipelineContext:
    """
    State object passed sequentially through all pipeline stages.
    """
    camera_id: str
    original_frame: Any  # Raw numpy array from OpenCV
    timestamp: float = field(default_factory=time.time)
    
    # Populated by stages:
    processed_frame: Any = None
    detections: List[Dict[str, Any]] = field(default_factory=list)
    tracks: List[Dict[str, Any]] = field(default_factory=list)
    assessment: Dict[str, Any] = field(default_factory=dict)
    
    # Output
    encoded_frame_b64: str | None = None
    
    # Telemetry
    metrics: Dict[str, float] = field(default_factory=dict)
    
    def record_metric(self, stage_name: str, duration_ms: float):
        self.metrics[stage_name] = duration_ms
