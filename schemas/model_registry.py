"""
SentinelOps — Model Registry Schemas
======================================
"""

from enum import Enum
from typing import Any, Optional, Dict
from pydantic import BaseModel, Field
import datetime

class Environment(str, Enum):
    DEVELOPMENT = "Development"
    STAGING = "Staging"
    PRODUCTION = "Production"
    ARCHIVED = "Archived"

class RegisteredModel(BaseModel):
    """Schema for an enterprise registered YOLO model."""
    name: str = Field(..., description="Unique name of the model")
    version: str = Field(..., description="Version tag of the model")
    path: str = Field(..., description="Path to the model weights file (.pt)")
    description: str = Field(default="", description="Description of the model")
    
    # Core Metadata
    date: str = Field(default_factory=lambda: datetime.datetime.now().isoformat(), description="Registration date")
    author: str = Field(default="system", description="Author or system that trained the model")
    dataset: str = Field(default="unknown", description="Dataset used for training")
    classes: list[str] = Field(default_factory=list, description="List of detectable classes")
    
    # Metrics
    precision: float = Field(default=0.0, description="Model Precision")
    recall: float = Field(default=0.0, description="Model Recall")
    mAP: float = Field(default=0.0, description="Model mAP50-95")
    
    # Performance
    latency: float = Field(default=0.0, description="Expected inference latency (ms)")
    fps: float = Field(default=0.0, description="Expected FPS")
    hardware: str = Field(default="CPU", description="Target hardware (e.g., T4 GPU, CPU)")
    
    # Enterprise Status
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Current deployment environment")
    status: str = Field(default="READY", description="Health status (e.g., READY, FAILED, DEPLOYED)")
    active: bool = Field(default=False, description="Whether this is the currently active production model")
    
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Additional custom metrics")

class DeploymentLog(BaseModel):
    """Logs every deployment event for auditability."""
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    model_name: str
    version: str
    environment: Environment
    user: str = "system"
    status: str = "SUCCESS"
    notes: str = ""

class ModelSwitchRequest(BaseModel):
    """Schema for requesting an active model switch."""
    name: str = Field(..., description="Unique name of the model to switch to")
    version: str = Field(..., description="Version tag of the model to switch to")

class ModelPromoteRequest(BaseModel):
    """Schema for promoting a model to a new environment."""
    name: str = Field(..., description="Unique name of the model")
    version: str = Field(..., description="Version tag of the model")
    target_environment: Environment = Field(..., description="Environment to promote to")
    notes: Optional[str] = None

