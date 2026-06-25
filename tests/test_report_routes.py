"""
SentinelOps — Report Routes Integration Tests
=================================================
Tests for the ``/reports/*`` HTTP endpoints using FastAPI ``TestClient``.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.models.alert import AlertCreate, AlertType, Severity
from app.models.report import ReportFormat


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def client(tmp_path):
    """Create a TestClient with isolated storage for reports."""
    from app.services.alert_service import AlertService
    from app.services.analytics_service import AnalyticsService
    from app.services.report_service import ReportService
    import app.api.report_routes as report_mod

    alert_svc = AlertService(alerts_dir=tmp_path / "alerts")
    analytics_svc = AnalyticsService(alert_svc)
    report_svc = ReportService(alert_svc, analytics_svc, reports_dir=tmp_path / "reports")

    orig_alert = report_mod._alert_service
    orig_analytics = report_mod._analytics_service
    orig_report = report_mod._report_service

    report_mod._alert_service = alert_svc
    report_mod._analytics_service = analytics_svc
    report_mod._report_service = report_svc

    from app.api.app import app

    with TestClient(app) as tc:
        tc.alert_service = alert_svc  # type: ignore[attr-defined]
        yield tc

    report_mod._alert_service = orig_alert
    report_mod._analytics_service = orig_analytics
    report_mod._report_service = orig_report


def _seed(alert_svc, n: int = 3, **kwargs):
    defaults = dict(
        camera_id="cam_01",
        alert_type=AlertType.NO_HELMET,
        severity=Severity.HIGH,
        confidence=0.9,
    )
    defaults.update(kwargs)
    for _ in range(n):
        alert_svc.create(AlertCreate(**defaults))


# ---------------------------------------------------------------------------
# POST /reports/generate
# ---------------------------------------------------------------------------
class TestGenerateEndpoint:
    def test_csv_returns_201(self, client):
        _seed(client.alert_service)
        resp = client.post("/reports/generate", json={"format": "csv"})
        assert resp.status_code == 201

    def test_excel_returns_201(self, client):
        _seed(client.alert_service)
        resp = client.post("/reports/generate", json={"format": "excel"})
        assert resp.status_code == 201

    def test_pdf_returns_201(self, client):
        _seed(client.alert_service)
        resp = client.post("/reports/generate", json={"format": "pdf"})
        assert resp.status_code == 201

    def test_response_has_metadata(self, client):
        _seed(client.alert_service)
        resp = client.post("/reports/generate", json={"format": "csv"})
        data = resp.json()

        assert "report_id" in data
        assert "format" in data
        assert "filename" in data
        assert "generated_at" in data
        assert "file_size_bytes" in data
        assert data["format"] == "csv"

    def test_invalid_format_returns_422(self, client):
        resp = client.post("/reports/generate", json={"format": "invalid"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /reports
# ---------------------------------------------------------------------------
class TestListEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/reports")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_lists_generated_reports(self, client):
        _seed(client.alert_service)
        client.post("/reports/generate", json={"format": "csv"})
        client.post("/reports/generate", json={"format": "pdf"})

        resp = client.get("/reports")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


# ---------------------------------------------------------------------------
# GET /reports/{report_id}/download
# ---------------------------------------------------------------------------
class TestDownloadEndpoint:
    def test_csv_download(self, client):
        _seed(client.alert_service)
        gen_resp = client.post("/reports/generate", json={"format": "csv"})
        report_id = gen_resp.json()["report_id"]

        dl_resp = client.get(f"/reports/{report_id}/download")
        assert dl_resp.status_code == 200
        assert "text/csv" in dl_resp.headers["content-type"]

    def test_excel_download(self, client):
        _seed(client.alert_service)
        gen_resp = client.post("/reports/generate", json={"format": "excel"})
        report_id = gen_resp.json()["report_id"]

        dl_resp = client.get(f"/reports/{report_id}/download")
        assert dl_resp.status_code == 200
        assert "spreadsheetml" in dl_resp.headers["content-type"]

    def test_pdf_download(self, client):
        _seed(client.alert_service)
        gen_resp = client.post("/reports/generate", json={"format": "pdf"})
        report_id = gen_resp.json()["report_id"]

        dl_resp = client.get(f"/reports/{report_id}/download")
        assert dl_resp.status_code == 200
        assert "application/pdf" in dl_resp.headers["content-type"]

    def test_nonexistent_report_returns_404(self, client):
        resp = client.get("/reports/RPT-nonexistent/download")
        assert resp.status_code == 404
