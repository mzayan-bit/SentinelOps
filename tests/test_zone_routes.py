"""
SentinelOps — Zone API Tests
====================================
Tests for the zone CRUD endpoints.
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.app import app
from app.db.base import Base
from app.db.database import get_db

@pytest.fixture
def test_app():
    return app

@pytest.fixture
def client(test_app):
    with TestClient(test_app) as tc:
        yield tc

def test_create_and_list_zones_validation_error(client):
    # Without mocking the DB, we can at least test validation or 404s
    payload = {
        "name": "Test Zone",
        "points_json": "[[10, 10], [20, 10], [20, 20], [10, 20]]",
        "is_restricted": True,
        "max_dwell_time": 5
    }
    # Using a fake camera UUID
    fake_cam_id = str(uuid.uuid4())
    res = client.post(f"/api/cameras/{fake_cam_id}/zones", json=payload)
    # The endpoint should return 404 because the DB has no such camera
    assert res.status_code == 404
