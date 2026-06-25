"""
SentinelOps — Metrics API Integration Tests
=============================================
Tests for platform observability metrics collection.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.api.app import app
from app.services.health_monitor import health_monitor


@pytest.fixture
def client():
    # Health monitor is a singleton in memory, clear it
    health_monitor._health_data.clear()
    with TestClient(app) as tc:
        yield tc


def test_metrics_endpoint_returns_200(client):
    resp = client.get("/api/metrics")
    assert resp.status_code == 200


def test_metrics_endpoint_system_fields(client):
    resp = client.get("/api/metrics")
    data = resp.json()

    assert "timestamp" in data
    assert "system" in data
    
    sys = data["system"]
    assert "cpu_percent" in sys
    assert "ram_percent" in sys
    assert "gpu_available" in sys
    assert "gpus" in sys
    
    # Assert CPU and RAM are populated
    assert sys["cpu_percent"] >= 0.0
    assert sys["ram_percent"] >= 0.0


def test_metrics_endpoint_application_fields_empty(client):
    resp = client.get("/api/metrics")
    app_metrics = resp.json()["application"]

    assert app_metrics["active_cameras"] == 0
    assert app_metrics["average_fps"] == 0.0
    assert app_metrics["average_latency_ms"] == 0.0


def test_metrics_endpoint_application_computes_averages(client):
    # Mock some data in the health monitor
    health_monitor.record_frame("cam_1", latency_ms=10.0, current_fps=30.0)
    health_monitor.record_frame("cam_2", latency_ms=20.0, current_fps=20.0)
    
    resp = client.get("/api/metrics")
    app_metrics = resp.json()["application"]

    assert app_metrics["active_cameras"] == 2
    # (30 + 20) / 2 = 25
    assert app_metrics["average_fps"] == 25.0
    # (10 + 20) / 2 = 15
    assert app_metrics["average_latency_ms"] == 15.0


def test_offline_cameras_excluded_from_averages(client):
    # Mock online camera
    health_monitor.record_frame("cam_1", latency_ms=10.0, current_fps=30.0)
    
    # Mock offline camera
    health_monitor.record_offline("cam_2")
    
    resp = client.get("/api/metrics")
    app_metrics = resp.json()["application"]

    assert app_metrics["active_cameras"] == 1
    assert app_metrics["average_fps"] == 30.0
    assert app_metrics["average_latency_ms"] == 10.0
