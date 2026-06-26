"""
SentinelOps — Structural & Sanity Tests
==========================================
Lightweight tests to verify that the project structure,
configuration, and core health modules are functioning correctly.
"""

from pathlib import Path

from config.settings import settings
from inference.health import HealthChecker


def test_critical_directories_exist() -> None:
    """Verify that essential project directories exist or can be created."""
    # Ensure the models directory exists (where the weights are expected to be)
    models_dir = Path(settings.model_path).parent
    assert models_dir.exists(), f"Models directory '{models_dir}' does not exist."

    # Ensure artifacts parent exists, so artifacts can be written
    for artifacts_dir in [
        settings.alerts_dir, 
        settings.reports_dir, 
        settings.snapshots_dir, 
        settings.events_dir,
        settings.registry_dir
    ]:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        assert artifacts_dir.exists(), f"Artifacts directory '{artifacts_dir}' does not exist."


def test_configuration_loads() -> None:
    """Verify that the central settings singleton is populated with valid types."""
    assert settings is not None, "Settings singleton should be instantiated."
    
    # Verify key attributes exist
    assert hasattr(settings, "model_path")
    assert hasattr(settings, "confidence_threshold")
    assert hasattr(settings, "log_level")
    
    # Verify basic validation rules applied during __post_init__
    assert 0.0 <= settings.confidence_threshold <= 1.0, "Confidence must be between 0 and 1."
    assert settings.api_port > 0, "API port must be a positive integer."


def test_model_path_resolves() -> None:
    """Verify that the configured model path is correctly formed."""
    model_path = Path(settings.model_path)
    
    # We do not strictly assert model_path.exists() here to allow tests to pass
    # in CI environments before weights are downloaded, but we ensure the path 
    # is logically sound.
    assert model_path.suffix == ".pt", f"Model path '{model_path}' should be a .pt file."
    assert model_path.name != ".pt", "Model filename cannot be empty."


def test_health_module_works() -> None:
    """Verify that the HealthChecker executes without crashing and returns a valid schema."""
    checker = HealthChecker()
    report = checker.run()
    
    # The system might be 'unhealthy' if weights aren't present,
    # but the checker itself must not crash.
    assert report is not None
    assert isinstance(report.healthy, bool)
    assert isinstance(report.checks, list)
    assert len(report.checks) == 4, "Expected exactly 4 diagnostic checks to run."
    
    # Validate individual check structure
    for check in report.checks:
        assert check.name, "Check must have a name."
        assert check.status.value in ("pass", "fail", "warn"), f"Invalid status: {check.status}"
        assert check.duration_ms >= 0, "Check duration cannot be negative."
