"""
SentinelOps — Alert Data Models
=================================
Pydantic schemas, enums, and type definitions for the Alert
Management system.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class AlertType(str, Enum):
    """Types of security / safety alerts."""

    PERSON_DETECTED = "Person Detected"
    NO_HELMET = "No Helmet"
    NO_VEST = "No Vest"
    RESTRICTED_AREA_ENTRY = "Restricted Area Entry"
    LOITERING = "Loitering"
    CROWD_FORMATION = "Crowd Formation"
    UNKNOWN_OBJECT = "Unknown Object"
    SUSPICIOUS_ACTIVITY = "Suspicious Activity"


class Severity(str, Enum):
    """Alert severity levels (ascending)."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class AlertStatus(str, Enum):
    """Alert lifecycle status."""

    NEW = "New"
    INVESTIGATING = "Investigating"
    CONFIRMED = "Confirmed"
    FALSE_POSITIVE = "False Positive"
    RESOLVED = "Resolved"


# Valid status transitions (current → set of allowed next statuses)
STATUS_TRANSITIONS: dict[AlertStatus, set[AlertStatus]] = {
    AlertStatus.NEW: {AlertStatus.INVESTIGATING, AlertStatus.FALSE_POSITIVE, AlertStatus.RESOLVED},
    AlertStatus.INVESTIGATING: {AlertStatus.CONFIRMED, AlertStatus.FALSE_POSITIVE, AlertStatus.RESOLVED},
    AlertStatus.CONFIRMED: {AlertStatus.RESOLVED},
    AlertStatus.FALSE_POSITIVE: {AlertStatus.NEW},  # allow re-opening
    AlertStatus.RESOLVED: {AlertStatus.NEW},  # allow re-opening
}


# ---------------------------------------------------------------------------
# Schemas — core alert
# ---------------------------------------------------------------------------
class AlertBase(BaseModel):
    """Fields shared between create / update / read operations."""

    camera_id: str = Field(..., min_length=1, description="Source camera identifier.")
    alert_type: AlertType = Field(..., description="Type of detected event.")
    severity: Severity = Field(..., description="Alert severity level.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence.")
    image_path: str | None = Field(default=None, description="Path to evidence image.")
    video_clip_path: str | None = Field(default=None, description="Path to evidence video clip.")
    notes: str = Field(default="", description="Investigation notes.")


class AlertCreate(AlertBase):
    """Schema for creating a new alert (POST body)."""

    pass


class AlertUpdate(BaseModel):
    """Schema for partial update (PUT body).  All fields optional."""

    camera_id: str | None = None
    alert_type: AlertType | None = None
    severity: Severity | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    status: AlertStatus | None = None
    assigned_to: str | None = None
    notes: str | None = None
    image_path: str | None = None
    video_clip_path: str | None = None


class Alert(AlertBase):
    """Full alert record returned from the API."""

    alert_id: str = Field(..., description="Unique alert identifier.")
    timestamp: datetime = Field(..., description="Alert creation timestamp (UTC).")
    status: AlertStatus = Field(default=AlertStatus.NEW)
    assigned_to: str | None = Field(default=None, description="Assigned investigator.")
    resolved_at: datetime | None = Field(default=None, description="Resolution timestamp.")

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-safe dictionary."""
        data = self.model_dump()
        # Convert datetime to ISO strings for JSON
        for key in ("timestamp", "resolved_at"):
            if data.get(key) is not None:
                data[key] = data[key].isoformat()
        return data

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Schemas — actions
# ---------------------------------------------------------------------------
class AlertAssign(BaseModel):
    """Body for the assign endpoint."""

    assigned_to: str = Field(..., min_length=1, description="Name or ID of the assignee.")


class AlertResolve(BaseModel):
    """Body for the resolve endpoint."""

    notes: str = Field(default="", description="Resolution notes.")
    false_positive: bool = Field(default=False, description="Mark as false positive instead of resolved.")


# ---------------------------------------------------------------------------
# Schemas — query filters
# ---------------------------------------------------------------------------
class AlertFilter(BaseModel):
    """Query parameters for listing / filtering alerts."""

    severity: Severity | None = None
    status: AlertStatus | None = None
    alert_type: AlertType | None = None
    camera_id: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


# ---------------------------------------------------------------------------
# Schemas — responses
# ---------------------------------------------------------------------------
class AlertListResponse(BaseModel):
    """Paginated alert list response."""

    total: int
    alerts: list[Alert]


class AlertStatsResponse(BaseModel):
    """Aggregated alert statistics."""

    total: int
    by_severity: dict[str, int]
    by_status: dict[str, int]
    by_type: dict[str, int]
