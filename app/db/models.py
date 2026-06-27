"""
SentinelOps — Database ORM Models
====================================
SQLAlchemy mapped classes for all core domain entities.

These models mirror the existing Pydantic schemas but are designed for
PostgreSQL persistence. Existing JSON-based services are NOT affected.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------
class CameraModel(Base):
    """Registered camera / video source."""

    __tablename__ = "cameras"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String(512), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="REGISTERED"
    )

    # Relationships
    incidents: Mapped[list["IncidentModel"]] = relationship(
        back_populates="camera", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list["SnapshotModel"]] = relationship(
        back_populates="camera", cascade="all, delete-orphan"
    )
    zones: Mapped[list["ZoneModel"]] = relationship(
        back_populates="camera", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Camera {self.name!r} ({self.id})>"


# ---------------------------------------------------------------------------
# Polygon Zone
# ---------------------------------------------------------------------------
class ZoneModel(Base):
    """A polygon zone attached to a camera for entry/dwell detection."""

    __tablename__ = "zones"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("cameras.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    points_json: Mapped[str] = mapped_column(Text, nullable=False) # JSON list of [x, y] coordinates
    is_restricted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_dwell_time: Mapped[int | None] = mapped_column(Integer, nullable=True) # Seconds before violation

    # Relationships
    camera: Mapped["CameraModel"] = relationship(back_populates="zones")

    def __repr__(self) -> str:
        return f"<Zone {self.name!r} ({self.id})>"


# ---------------------------------------------------------------------------
# Violation (formerly "Alert")
# ---------------------------------------------------------------------------
class ViolationModel(Base):
    """A detected PPE violation event."""

    __tablename__ = "violations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    camera_id: Mapped[str] = mapped_column(String(128), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="New")
    assigned_to: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    video_clip_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Violation {self.id} [{self.alert_type}]>"


# ---------------------------------------------------------------------------
# Incident
# ---------------------------------------------------------------------------
class IncidentModel(Base):
    """A logged violation incident from the timeline."""

    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("cameras.id"), nullable=False
    )
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    screenshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    camera: Mapped["CameraModel"] = relationship(back_populates="incidents")

    def __repr__(self) -> str:
        return f"<Incident {self.id} severity={self.severity}>"


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------
class SnapshotModel(Base):
    """A persisted camera frame snapshot with metadata."""

    __tablename__ = "snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("cameras.id"), nullable=False
    )
    relative_path: Mapped[str] = mapped_column(String(512), nullable=False)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    camera: Mapped["CameraModel"] = relationship(back_populates="snapshots")

    def __repr__(self) -> str:
        return f"<Snapshot {self.id}>"


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
class ReportModel(Base):
    """Metadata for a generated report file."""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, default="SentinelOps Violation Report"
    )
    include_charts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<Report {self.id} [{self.format}]>"
