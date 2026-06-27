"""
SentinelOps — Report Routes Integration Tests
=================================================
Tests for the ``/reports/*`` HTTP endpoints using FastAPI ``TestClient``.

Report generation is now asynchronous — ``POST /reports/generate`` returns
``202 Accepted`` with a ``task_id``.  The tests poll the task status endpoint
until the job finishes, then validate the generated report via the existing
list / download endpoints.
"""

from __future__ import annotations

import time

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


def _wait_for_task(client, task_id: str, timeout: float = 10.0) -> dict:
    """Poll ``GET /api/tasks/{task_id}`` until it reaches a terminal state."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] in ("COMPLETED", "FAILED"):
            return data
        time.sleep(0.1)
    raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")


# ---------------------------------------------------------------------------
# POST /reports/generate  (now returns 202 + task_id)
# ---------------------------------------------------------------------------
class TestGenerateEndpoint:
    def test_csv_returns_202(self, client):
        _seed(client.alert_service)
        resp = client.post("/reports/generate", json={"format": "csv"})
        assert resp.status_code == 202
        assert "task_id" in resp.json()

    def test_excel_returns_202(self, client):
        _seed(client.alert_service)
        resp = client.post("/reports/generate", json={"format": "excel"})
        assert resp.status_code == 202
        assert "task_id" in resp.json()

    def test_pdf_returns_202(self, client):
        _seed(client.alert_service)
        resp = client.post("/reports/generate", json={"format": "pdf"})
        assert resp.status_code == 202
        assert "task_id" in resp.json()

    def test_response_has_task_fields(self, client):
        _seed(client.alert_service)
        resp = client.post("/reports/generate", json={"format": "csv"})
        data = resp.json()

        assert "task_id" in data
        assert "status" in data
        assert data["status"] == "PENDING"

    def test_task_completes_with_report_metadata(self, client):
        """After polling, the completed task should carry ReportMetadata."""
        _seed(client.alert_service)
        resp = client.post("/reports/generate", json={"format": "csv"})
        task_id = resp.json()["task_id"]

        task = _wait_for_task(client, task_id)
        assert task["status"] == "COMPLETED"
        assert "result" in task
        assert "report_id" in task["result"]
        assert task["result"]["format"] == "csv"

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
        r1 = client.post("/reports/generate", json={"format": "csv"})
        r2 = client.post("/reports/generate", json={"format": "pdf"})

        _wait_for_task(client, r1.json()["task_id"])
        _wait_for_task(client, r2.json()["task_id"])

        resp = client.get("/reports")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


# ---------------------------------------------------------------------------
# GET /reports/{report_id}/download
# ---------------------------------------------------------------------------
class TestDownloadEndpoint:
    def _generate_and_wait(self, client, fmt: str) -> str:
        """Submit, wait, and return the report_id."""
        _seed(client.alert_service)
        resp = client.post("/reports/generate", json={"format": fmt})
        task_id = resp.json()["task_id"]
        task = _wait_for_task(client, task_id)
        return task["result"]["report_id"]

    def test_csv_download(self, client):
        report_id = self._generate_and_wait(client, "csv")
        dl_resp = client.get(f"/reports/{report_id}/download")
        assert dl_resp.status_code == 200
        assert "text/csv" in dl_resp.headers["content-type"]

    def test_excel_download(self, client):
        report_id = self._generate_and_wait(client, "excel")
        dl_resp = client.get(f"/reports/{report_id}/download")
        assert dl_resp.status_code == 200
        assert "spreadsheetml" in dl_resp.headers["content-type"]

    def test_pdf_download(self, client):
        report_id = self._generate_and_wait(client, "pdf")
        dl_resp = client.get(f"/reports/{report_id}/download")
        assert dl_resp.status_code == 200
        assert "application/pdf" in dl_resp.headers["content-type"]

    def test_nonexistent_report_returns_404(self, client):
        resp = client.get("/reports/RPT-nonexistent/download")
        assert resp.status_code == 404
