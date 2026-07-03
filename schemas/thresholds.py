"""
SentinelOps — Confidence Threshold Schemas
==========================================
"""

from typing import Dict
from pydantic import BaseModel, Field

class ThresholdConfig(BaseModel):
    """Schema for runtime-configurable confidence thresholds."""
    global_threshold: float = Field(default=0.25, ge=0.0, le=1.0, description="Baseline minimum confidence across all classes.")
    per_class: Dict[str, float] = Field(default_factory=dict, description="Specific thresholds for individual class names.")
