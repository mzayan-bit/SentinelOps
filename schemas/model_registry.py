"""
SentinelOps — Model Registry Schemas
======================================
"""

from typing import Any
from pydantic import BaseModel, Field

class RegisteredModel(BaseModel):
    """Schema for a registered YOLO model."""
    name: str = Field(..., description="Unique name of the model")
    version: str = Field(..., description="Version tag of the model")
    path: str = Field(..., description="Path to the model weights file (.pt)")
    description: str = Field(default="", description="Description of the model")
    metrics: dict[str, Any] = Field(default_factory=dict, description="Performance metrics (e.g., mAP, inference time)")
    active: bool = Field(default=False, description="Whether this is the currently active model")

class ModelSwitchRequest(BaseModel):
    """Schema for requesting an active model switch."""
    name: str = Field(..., description="Unique name of the model to switch to")
    version: str = Field(..., description="Version tag of the model to switch to")
