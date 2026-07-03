"""
SentinelOps — Threshold Service Tests
=======================================
"""

import pytest
from pathlib import Path

from config.settings import settings
from schemas.thresholds import ThresholdConfig
from app.services.threshold_service import ThresholdService

@pytest.fixture
def mock_registry_dir(tmp_path):
    """Use a temporary directory for the registry JSON."""
    original_dir = settings.registry_dir
    settings.registry_dir = tmp_path
    
    yield tmp_path
    
    settings.registry_dir = original_dir

@pytest.fixture
def threshold_service(mock_registry_dir):
    """Provide a fresh instance of the service pointing to tmp_path."""
    return ThresholdService()

def test_initialization(threshold_service):
    """Test it initializes and saves default config."""
    assert threshold_service.config_file.exists()
    config = threshold_service.get_config()
    assert config.global_threshold == settings.confidence_threshold
    assert config.per_class == {}

def test_update_config(threshold_service):
    """Test updating the configuration."""
    new_config = ThresholdConfig(global_threshold=0.5, per_class={"Helmet": 0.8})
    updated = threshold_service.update_config(new_config)
    
    assert updated.global_threshold == 0.5
    
    loaded = threshold_service.get_config()
    assert loaded.global_threshold == 0.5
    assert loaded.per_class["Helmet"] == 0.8

def test_get_threshold(threshold_service):
    """Test resolving the threshold for specific classes."""
    threshold_service.update_config(ThresholdConfig(
        global_threshold=0.3, 
        per_class={"Person": 0.5, "Vest": 0.9}
    ))
    
    assert threshold_service.get_threshold("Person") == 0.5
    assert threshold_service.get_threshold("Vest") == 0.9
    # Fallback to global
    assert threshold_service.get_threshold("Unknown") == 0.3

def test_get_min_threshold(threshold_service):
    """Test calculating the minimum threshold for YOLO."""
    # Only global
    threshold_service.update_config(ThresholdConfig(global_threshold=0.4))
    assert threshold_service.get_min_threshold() == 0.4
    
    # Per-class is higher
    threshold_service.update_config(ThresholdConfig(
        global_threshold=0.4, 
        per_class={"Person": 0.5}
    ))
    assert threshold_service.get_min_threshold() == 0.4
    
    # Per-class is lower
    threshold_service.update_config(ThresholdConfig(
        global_threshold=0.4, 
        per_class={"Person": 0.2}
    ))
    assert threshold_service.get_min_threshold() == 0.2
