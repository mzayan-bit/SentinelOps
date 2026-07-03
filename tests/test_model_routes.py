"""
SentinelOps — Model Registry API Routes Tests
=============================================
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.api.app import app
from app.services.model_registry import model_registry_service
from schemas.model_registry import RegisteredModel

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure the registry is clean before each test."""
    # Backup
    models = model_registry_service.list_models()
    # Clear
    model_registry_service._save([])
    
    yield
    
    # Restore
    model_registry_service._save(models)


def test_list_models_empty():
    response = client.get("/api/models")
    assert response.status_code == 200
    assert response.json() == []

def test_register_model():
    payload = {
        "name": "yolo-v8n",
        "version": "1.0",
        "path": "dummy_path.pt",
        "description": "Test model",
        "metrics": {"mAP": 0.8},
        "active": False
    }
    
    response = client.post("/api/models", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "yolo-v8n"
    assert data["version"] == "1.0"
    
    # Check it's in the list
    response = client.get("/api/models")
    assert len(response.json()) == 1

def test_get_active_model_none():
    response = client.get("/api/models/active")
    assert response.status_code == 404
    assert response.json()["detail"] == "No active model found in the registry."

def test_get_active_model():
    model_registry_service.register_model(RegisteredModel(
        name="test", version="1", path="p.pt", active=True
    ))
    response = client.get("/api/models/active")
    assert response.status_code == 200
    assert response.json()["name"] == "test"

@patch("inference.model_loader.ModelLoader.switch_model")
def test_switch_active_model(mock_switch_model):
    # Register models
    model_registry_service.register_model(RegisteredModel(
        name="m1", version="1", path="p1.pt", active=True
    ))
    model_registry_service.register_model(RegisteredModel(
        name="m2", version="1", path="p2.pt", active=False
    ))
    
    # Switch
    payload = {"name": "m2", "version": "1"}
    response = client.post("/api/models/active", json=payload)
    assert response.status_code == 200
    assert response.json()["name"] == "m2"
    assert response.json()["active"] is True
    
    mock_switch_model.assert_called_once_with("p2.pt")
    
    # Verify via get active
    response = client.get("/api/models/active")
    assert response.json()["name"] == "m2"

def test_switch_active_model_not_found():
    payload = {"name": "nonexistent", "version": "1"}
    response = client.post("/api/models/active", json=payload)
    assert response.status_code == 404
