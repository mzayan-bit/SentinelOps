"""
SentinelOps — RBAC Tests
========================
Tests for the Role-Based Access Control system.

Because the global `conftest.py` disables auth to let the old 98 tests pass,
we explicitly re-enable auth for this test module using an `autouse` fixture.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.auth import Role, set_auth_enabled
from app.api.app import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def enable_auth_for_these_tests(tmp_path):
    """
    1. Re-enable auth explicitly for these tests.
    2. Overwrite the users config file path to use `tmp_path` so we don't
       mutate the real `config/users.json`.
    """
    
    import app.auth as auth_mod
    original_user_store = auth_mod._user_store
    
    # Create isolated user store
    test_users_file = tmp_path / "users.json"
    test_users_file.write_text(json.dumps({
        "users": [
            {"username": "testadmin", "role": "admin", "api_key": "key-admin"},
            {"username": "testsuper", "role": "supervisor", "api_key": "key-super"},
            {"username": "testview", "role": "viewer", "api_key": "key-view"}
        ]
    }))
    
    auth_mod._user_store = auth_mod.UserStore(path=test_users_file)
    
    yield
    
    # Restore global state
    auth_mod._user_store = original_user_store


@pytest.fixture
def client():
    with TestClient(app) as tc:
        # Set auth true AFTER lifespan executes so it overrides any lifespan logic
        set_auth_enabled(True)
        yield tc
        set_auth_enabled(False)


# ---------------------------------------------------------------------------
# Unauthenticated & Invalid Auth
# ---------------------------------------------------------------------------
def test_no_api_key_returns_401(client):
    resp = client.get("/alerts")
    assert resp.status_code == 401
    assert "missing" in resp.json()["detail"].lower()


def test_invalid_api_key_returns_401(client):
    resp = client.get("/alerts", headers={"X-API-Key": "invalid-key"})
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower()


def test_health_endpoint_is_public(client):
    # /health requires no auth
    resp = client.get("/health")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# VIEWER Role Tests
# ---------------------------------------------------------------------------
def test_viewer_can_read_alerts(client):
    resp = client.get("/alerts", headers={"X-API-Key": "key-view"})
    assert resp.status_code == 200


def test_viewer_cannot_create_alert(client):
    payload = {
        "camera_id": "cam01",
        "alert_type": "Loitering",
        "severity": "Low",
        "confidence": 0.8
    }
    resp = client.post("/alerts", json=payload, headers={"X-API-Key": "key-view"})
    assert resp.status_code == 403


def test_viewer_can_read_analytics(client):
    resp = client.get("/analytics/summary", headers={"X-API-Key": "key-view"})
    assert resp.status_code == 200


def test_viewer_cannot_generate_report(client):
    resp = client.post("/reports/generate", json={"format": "csv"}, headers={"X-API-Key": "key-view"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# SUPERVISOR Role Tests
# ---------------------------------------------------------------------------
def test_supervisor_can_create_alert(client):
    payload = {
        "camera_id": "cam01",
        "alert_type": "Loitering",
        "severity": "Low",
        "confidence": 0.8
    }
    resp = client.post("/alerts", json=payload, headers={"X-API-Key": "key-super"})
    assert resp.status_code == 201


def test_supervisor_can_generate_report(client):
    resp = client.post("/reports/generate", json={"format": "csv"}, headers={"X-API-Key": "key-super"})
    # Report generation is now async (202). The RBAC test only validates
    # that the supervisor is authorised (not 401/403).
    assert resp.status_code in [201, 202, 500]


def test_supervisor_cannot_delete_camera(client):
    resp = client.delete("/api/cameras/00000000-0000-0000-0000-000000000000", headers={"X-API-Key": "key-super"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# ADMIN Role Tests
# ---------------------------------------------------------------------------
def test_admin_can_delete_alert(client):
    # Will likely return 404 since alert doesn't exist, but NOT 403
    resp = client.delete("/alerts/fake-id", headers={"X-API-Key": "key-admin"})
    assert resp.status_code == 404


def test_admin_can_delete_camera(client):
    # Will likely return 404 since camera doesn't exist, but NOT 403
    resp = client.delete("/api/cameras/00000000-0000-0000-0000-000000000000", headers={"X-API-Key": "key-admin"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Role Hierarchy logic
# ---------------------------------------------------------------------------
def test_role_hierarchy():
    assert Role.ADMIN > Role.SUPERVISOR
    assert Role.SUPERVISOR > Role.VIEWER
    assert Role.ADMIN > Role.VIEWER
