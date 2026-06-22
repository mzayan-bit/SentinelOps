from pydantic import BaseModel, Field
import uuid

class CameraCreate(BaseModel):
    """Schema for registering a new camera source."""
    source: str = Field(..., description="RTSP URL, device ID, or local file path.", examples=["rtsp://admin:pass@192.168.1.100/stream"])
    name: str = Field(..., description="Human-readable name for the camera.", examples=["Main Entrance Gate"])

class CameraResponse(BaseModel):
    """Schema representing a registered camera and its current state."""
    id: uuid.UUID = Field(..., description="Unique identifier for the camera.")
    source: str = Field(..., description="The configured video source.")
    name: str = Field(..., description="The name of the camera.")
    status: str = Field(..., description="Current operational status (e.g., REGISTERED, RUNNING, STOPPED).")

    class Config:
        from_attributes = True
