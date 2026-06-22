from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
import uuid

class SeverityLevel(str, Enum):
    """Defines the severity of an incident."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class IncidentCreate(BaseModel):
    """Schema for logging a new violation incident."""
    camera_id: str = Field(..., description="ID of the camera where the violation occurred")
    severity: SeverityLevel = Field(..., description="Severity level of the violation")
    description: str = Field(..., description="Description of the violation (e.g., 'Missing helmet')")
    screenshot_path: Optional[str] = Field(None, description="Optional path to the violation screenshot")

class IncidentResponse(BaseModel):
    """Schema representing an incident in the timeline."""
    id: uuid.UUID
    camera_id: str
    severity: SeverityLevel
    description: str
    screenshot_path: Optional[str]
    timestamp: float

    class Config:
        from_attributes = True
