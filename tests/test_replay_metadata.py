"""
SentinelOps — Replay Metadata Tests
=======================================
Verifies creation, timestamp computation, association with incidents,
querying, and deletion of replay metadata records.
"""

import time
import pytest

from app.services.replay_metadata import ReplayMetadataService, ReplayMetadata


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def svc():
    """Fresh service for each test."""
    return ReplayMetadataService(pre_seconds=10.0, post_seconds=10.0)


# ---------------------------------------------------------------------------
# ReplayMetadata dataclass
# ---------------------------------------------------------------------------
class TestReplayMetadata:
    def test_to_dict_keys(self):
        m = ReplayMetadata(
            replay_id="RPL-abc",
            incident_id="INC-1",
            camera_id="CAM-01",
            trigger_timestamp=1000.0,
            replay_start=990.0,
            replay_end=1010.0,
            duration_seconds=20.0,
            created_at=1000.0,
        )
        d = m.to_dict()
        assert d["replay_id"] == "RPL-abc"
        assert d["incident_id"] == "INC-1"
        assert d["camera_id"] == "CAM-01"
        assert d["replay_start"] == 990.0
        assert d["replay_end"] == 1010.0
        assert d["duration_seconds"] == 20.0


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------
class TestCreate:
    def test_basic_creation(self, svc):
        meta = svc.create(
            incident_id="INC-1",
            camera_id="CAM-01",
            trigger_timestamp=1000.0,
        )
        assert meta.replay_id.startswith("RPL-")
        assert meta.incident_id == "INC-1"
        assert meta.camera_id == "CAM-01"
        assert meta.trigger_timestamp == 1000.0
        assert meta.replay_start == 990.0
        assert meta.replay_end == 1010.0
        assert meta.duration_seconds == 20.0

    def test_custom_window(self, svc):
        meta = svc.create(
            incident_id="INC-1",
            camera_id="CAM-01",
            trigger_timestamp=500.0,
            pre_seconds=5.0,
            post_seconds=15.0,
        )
        assert meta.replay_start == 495.0
        assert meta.replay_end == 515.0
        assert meta.duration_seconds == 20.0

    def test_violation_data_attached(self, svc):
        violation = {"summary": {"NO_HELMET": 2}, "total_violations": 2}
        meta = svc.create(
            incident_id="INC-1",
            camera_id="CAM-01",
            trigger_timestamp=1000.0,
            violation_data=violation,
        )
        assert meta.violation_data == violation

    def test_alert_and_worker_ids(self, svc):
        meta = svc.create(
            incident_id="INC-1",
            camera_id="CAM-01",
            trigger_timestamp=1000.0,
            alert_ids=["ALR-001", "ALR-002"],
            worker_ids=["W-1", "W-2"],
        )
        assert meta.alert_ids == ["ALR-001", "ALR-002"]
        assert meta.worker_ids == ["W-1", "W-2"]

    def test_default_trigger_uses_current_time(self, svc):
        before = time.time()
        meta = svc.create(incident_id="INC-1", camera_id="CAM-01")
        after = time.time()
        assert before <= meta.trigger_timestamp <= after


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------
class TestQueries:
    def test_get_by_id(self, svc):
        meta = svc.create(incident_id="INC-1", camera_id="CAM-01", trigger_timestamp=100.0)
        found = svc.get(meta.replay_id)
        assert found is not None
        assert found.replay_id == meta.replay_id

    def test_get_missing(self, svc):
        assert svc.get("RPL-nonexistent") is None

    def test_get_by_incident(self, svc):
        svc.create(incident_id="INC-1", camera_id="CAM-01", trigger_timestamp=100.0)
        svc.create(incident_id="INC-1", camera_id="CAM-02", trigger_timestamp=200.0)
        svc.create(incident_id="INC-2", camera_id="CAM-01", trigger_timestamp=300.0)

        results = svc.get_by_incident("INC-1")
        assert len(results) == 2
        assert all(r.incident_id == "INC-1" for r in results)

    def test_get_by_incident_empty(self, svc):
        assert svc.get_by_incident("INC-999") == []

    def test_get_by_camera(self, svc):
        svc.create(incident_id="INC-1", camera_id="CAM-01", trigger_timestamp=100.0)
        svc.create(incident_id="INC-2", camera_id="CAM-01", trigger_timestamp=200.0)
        svc.create(incident_id="INC-3", camera_id="CAM-02", trigger_timestamp=300.0)

        results = svc.get_by_camera("CAM-01")
        assert len(results) == 2
        # Newest first
        assert results[0].trigger_timestamp == 200.0

    def test_list_all_sorted(self, svc):
        svc.create(incident_id="INC-1", camera_id="CAM-01", trigger_timestamp=100.0)
        svc.create(incident_id="INC-2", camera_id="CAM-02", trigger_timestamp=300.0)
        svc.create(incident_id="INC-3", camera_id="CAM-03", trigger_timestamp=200.0)

        results = svc.list_all()
        assert len(results) == 3
        timestamps = [r.trigger_timestamp for r in results]
        assert timestamps == [300.0, 200.0, 100.0]


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------
class TestDeletion:
    def test_delete_existing(self, svc):
        meta = svc.create(incident_id="INC-1", camera_id="CAM-01", trigger_timestamp=100.0)
        assert svc.delete(meta.replay_id) is True
        assert svc.get(meta.replay_id) is None

    def test_delete_missing(self, svc):
        assert svc.delete("RPL-nonexistent") is False

    def test_delete_removes_from_incident_index(self, svc):
        meta = svc.create(incident_id="INC-1", camera_id="CAM-01", trigger_timestamp=100.0)
        svc.delete(meta.replay_id)
        assert svc.get_by_incident("INC-1") == []

    def test_clear(self, svc):
        svc.create(incident_id="INC-1", camera_id="CAM-01", trigger_timestamp=100.0)
        svc.create(incident_id="INC-2", camera_id="CAM-02", trigger_timestamp=200.0)
        svc.clear()
        assert svc.list_all() == []
