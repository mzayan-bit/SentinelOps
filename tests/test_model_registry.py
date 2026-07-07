"""
SentinelOps — Model Registry Tests
====================================
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from schemas.model_registry import RegisteredModel
from app.services.model_registry import ModelRegistryService
from config.settings import settings

@pytest.fixture
def mock_registry_dir(tmp_path):
    """Use a temporary directory for the registry JSON."""
    original_dir = settings.registry_dir
    settings.registry_dir = tmp_path
    
    yield tmp_path
    
    settings.registry_dir = original_dir

@pytest.fixture
def registry_service(mock_registry_dir):
    """Provide a fresh instance of the service pointing to tmp_path."""
    return ModelRegistryService()

def test_registry_initialization(mock_registry_dir):
    """Test that the registry initializes correctly with an empty JSON file."""
    service = ModelRegistryService()
    assert service.registry_file.exists()
    assert service.list_models() == []

def test_register_model(registry_service):
    """Test registering a new model."""
    model = RegisteredModel(
        name="yolo-test",
        version="v1",
        path="models/test_v1.pt",
        description="A test model",
        metrics={"mAP": 0.95},
        active=True
    )
    
    registered = registry_service.register_model(model)
    assert registered.name == "yolo-test"
    
    models = registry_service.list_models()
    assert len(models) == 1
    assert models[0].name == "yolo-test"
    assert models[0].active is True

def test_register_duplicate_model_updates(registry_service):
    """Test that registering a model with the same name and version updates metadata."""
    model1 = RegisteredModel(name="yolo", version="1", path="path1.pt")
    registry_service.register_model(model1)
    
    model2 = RegisteredModel(name="yolo", version="1", path="path2.pt", description="updated")
    registry_service.register_model(model2)
    
    models = registry_service.list_models()
    assert len(models) == 1
    # Path is not updated during registration to avoid prod wipes
    assert models[0].description == "updated"

@patch("inference.model_loader.ModelLoader.switch_model")
def test_set_active_model(mock_switch, registry_service):
    """Test setting an active model."""
    registry_service.register_model(RegisteredModel(name="m1", version="1", path="p1.pt"))
    registry_service.register_model(RegisteredModel(name="m2", version="1", path="p2.pt"))
    
    # Set m2 as active
    active = registry_service.set_active_model("m2", "1")
    assert active is not None
    assert active.name == "m2"
    
    # Verify the switch happened
    mock_switch.assert_called_once_with("p2.pt")
    
    # Verify state
    assert registry_service.get_active_model().name == "m2"
    
    # Verify others are inactive
    for m in registry_service.list_models():
        if m.name == "m1":
            assert m.active is False

def test_get_active_model_none(registry_service):
    """Test that get_active_model returns None if none are active."""
    registry_service.register_model(RegisteredModel(name="m1", version="1", path="p1.pt", active=False))
    assert registry_service.get_active_model() is None
