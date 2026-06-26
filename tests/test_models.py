"""
SentinelOps — ORM Model Tests
================================
Verifies that all five database models can be instantiated, persisted,
and queried via the async session using an in-memory SQLite backend.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import (
    CameraModel,
    IncidentModel,
    ReportModel,
    SnapshotModel,
    ViolationModel,
)


# ---------------------------------------------------------------------------
# Fixtures — in-memory async SQLite for isolated test runs
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def async_session():
    """Spin up a fresh in-memory database, create all tables, yield a session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def sample_camera(async_session: AsyncSession) -> CameraModel:
    """Insert and return a reference camera row."""
    cam = CameraModel(
        id=uuid.uuid4(),
        source="rtsp://192.168.1.100/stream",
        name="Main Gate",
        status="REGISTERED",
    )
    async_session.add(cam)
    await async_session.commit()
    await async_session.refresh(cam)
    return cam


# ---------------------------------------------------------------------------
# Camera Model Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_camera_create_and_read(async_session: AsyncSession):
    cam_id = uuid.uuid4()
    cam = CameraModel(
        id=cam_id,
        source="rtsp://10.0.0.1/live",
        name="Warehouse East",
        status="RUNNING",
    )
    async_session.add(cam)
    await async_session.commit()

    result = await async_session.get(CameraModel, cam_id)
    assert result is not None
    assert result.name == "Warehouse East"
    assert result.status == "RUNNING"


@pytest.mark.asyncio
async def test_camera_default_status(async_session: AsyncSession):
    cam = CameraModel(
        id=uuid.uuid4(),
        source="/dev/video0",
        name="Test Cam",
    )
    async_session.add(cam)
    await async_session.commit()
    await async_session.refresh(cam)

    assert cam.status == "REGISTERED"


# ---------------------------------------------------------------------------
# Violation Model Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_violation_create_with_camera_fk(
    async_session: AsyncSession, sample_camera: CameraModel
):
    viol = ViolationModel(
        id="ALR-20260626-abc123",
        camera_id=sample_camera.id,
        alert_type="No Helmet",
        severity="High",
        confidence=0.92,
        status="New",
        timestamp=datetime.now(timezone.utc),
    )
    async_session.add(viol)
    await async_session.commit()

    result = await async_session.get(ViolationModel, "ALR-20260626-abc123")
    assert result is not None
    assert result.alert_type == "No Helmet"
    assert result.camera_id == sample_camera.id


@pytest.mark.asyncio
async def test_violation_optional_fields(
    async_session: AsyncSession, sample_camera: CameraModel
):
    viol = ViolationModel(
        id="ALR-20260626-opt01",
        camera_id=sample_camera.id,
        alert_type="No Vest",
        severity="Medium",
        confidence=0.75,
        status="New",
        timestamp=datetime.now(timezone.utc),
        image_path="/screenshots/frame_001.jpg",
        assigned_to="inspector_1",
        notes="Needs review",
    )
    async_session.add(viol)
    await async_session.commit()
    await async_session.refresh(viol)

    assert viol.image_path == "/screenshots/frame_001.jpg"
    assert viol.assigned_to == "inspector_1"
    assert viol.notes == "Needs review"


# ---------------------------------------------------------------------------
# Incident Model Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_incident_create(
    async_session: AsyncSession, sample_camera: CameraModel
):
    inc = IncidentModel(
        camera_id=sample_camera.id,
        severity="HIGH",
        description="Worker without helmet in Zone A",
        timestamp=1719420000.0,
    )
    async_session.add(inc)
    await async_session.commit()
    await async_session.refresh(inc)

    assert inc.id is not None
    assert inc.severity == "HIGH"
    assert inc.description == "Worker without helmet in Zone A"


# ---------------------------------------------------------------------------
# Snapshot Model Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_snapshot_create(
    async_session: AsyncSession, sample_camera: CameraModel
):
    snap = SnapshotModel(
        camera_id=sample_camera.id,
        relative_path="2026/06/26/cam1_120000_abcdef12.jpg",
        timestamp=1719420000.0,
    )
    async_session.add(snap)
    await async_session.commit()
    await async_session.refresh(snap)

    assert snap.id is not None
    assert snap.relative_path == "2026/06/26/cam1_120000_abcdef12.jpg"


# ---------------------------------------------------------------------------
# Report Model Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_report_create(async_session: AsyncSession):
    rpt = ReportModel(
        id="RPT-20260626-001",
        format="pdf",
        filename="report_20260626.pdf",
        generated_at=datetime.now(timezone.utc),
        file_path="artifacts/reports/report_20260626.pdf",
        file_size_bytes=102400,
        title="Weekly Safety Report",
        include_charts=True,
    )
    async_session.add(rpt)
    await async_session.commit()

    result = await async_session.get(ReportModel, "RPT-20260626-001")
    assert result is not None
    assert result.format == "pdf"
    assert result.file_size_bytes == 102400


@pytest.mark.asyncio
async def test_report_defaults(async_session: AsyncSession):
    rpt = ReportModel(
        id="RPT-20260626-002",
        format="csv",
        filename="report.csv",
        generated_at=datetime.now(timezone.utc),
        file_path="artifacts/reports/report.csv",
    )
    async_session.add(rpt)
    await async_session.commit()
    await async_session.refresh(rpt)

    assert rpt.file_size_bytes == 0
    assert rpt.title == "SentinelOps Violation Report"
    assert rpt.include_charts is True


# ---------------------------------------------------------------------------
# Relationship Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_camera_has_violations_relationship(
    async_session: AsyncSession, sample_camera: CameraModel
):
    viol = ViolationModel(
        id="ALR-REL-001",
        camera_id=sample_camera.id,
        alert_type="Loitering",
        severity="Low",
        confidence=0.6,
        status="New",
        timestamp=datetime.now(timezone.utc),
    )
    async_session.add(viol)
    await async_session.commit()

    # Re-fetch camera with relationship loaded
    stmt = select(CameraModel).where(CameraModel.id == sample_camera.id)
    result = await async_session.execute(stmt)
    cam = result.scalar_one()

    await async_session.refresh(cam, ["violations"])
    assert len(cam.violations) == 1
    assert cam.violations[0].id == "ALR-REL-001"


@pytest.mark.asyncio
async def test_camera_cascade_delete(
    async_session: AsyncSession,
):
    """Deleting a camera should cascade-delete its violations, incidents, snapshots."""
    cam = CameraModel(
        id=uuid.uuid4(),
        source="rtsp://test/cascade",
        name="Cascade Test",
    )
    async_session.add(cam)
    await async_session.flush()

    viol = ViolationModel(
        id="ALR-CASCADE-001",
        camera_id=cam.id,
        alert_type="No Helmet",
        severity="High",
        confidence=0.9,
        status="New",
        timestamp=datetime.now(timezone.utc),
    )
    inc = IncidentModel(
        camera_id=cam.id,
        severity="HIGH",
        description="Cascade test incident",
        timestamp=1719420000.0,
    )
    snap = SnapshotModel(
        camera_id=cam.id,
        relative_path="test/cascade.jpg",
        timestamp=1719420000.0,
    )
    async_session.add_all([viol, inc, snap])
    await async_session.commit()

    # Delete the camera
    await async_session.delete(cam)
    await async_session.commit()

    # Verify cascaded deletes
    assert await async_session.get(ViolationModel, "ALR-CASCADE-001") is None
    assert await async_session.get(IncidentModel, inc.id) is None
    assert await async_session.get(SnapshotModel, snap.id) is None
