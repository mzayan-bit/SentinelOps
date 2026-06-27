"""
SentinelOps — MS Teams Service Tests
====================================
Tests for the MS Teams notification service, verifying severity filtering
and API dispatch via mocked urllib.request.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime, timezone
import urllib.error

from app.models.alert import Alert, AlertStatus, AlertType, Severity
from schemas.incident import IncidentResponse, SeverityLevel
from app.services.teams_service import TeamsService
from config.settings import settings


@pytest.fixture
def mock_settings(monkeypatch):
    """Enable Teams webhook globally for tests."""
    monkeypatch.setattr(settings, "teams_webhook_url", "http://mock-teams.local/webhook")
    monkeypatch.setattr(settings, "teams_severity_threshold", "high")


@pytest.fixture
def teams_svc(mock_settings):
    """Return a fresh instance of TeamsService with mocked settings."""
    return TeamsService()


def create_dummy_alert(severity: Severity = Severity.HIGH, has_image: bool = False, tmp_path: Path = None) -> Alert:
    image_path = None
    if has_image and tmp_path:
        img_file = tmp_path / "dummy_snapshot.jpg"
        img_file.write_bytes(b"fake_jpeg_bytes")
        image_path = str(img_file)

    return Alert(
        alert_id="ALR-TEAMS-01",
        camera_id="cam_01",
        alert_type=AlertType.NO_HELMET,
        severity=severity,
        confidence=0.9,
        status=AlertStatus.NEW,
        timestamp=datetime.now(timezone.utc),
        image_path=image_path,
    )


def create_dummy_incident(severity: SeverityLevel = SeverityLevel.HIGH, has_image: bool = False, tmp_path: Path = None) -> IncidentResponse:
    import uuid
    image_path = None
    if has_image and tmp_path:
        img_file = tmp_path / "dummy_incident.jpg"
        img_file.write_bytes(b"fake_bytes")
        image_path = str(img_file)
        
    return IncidentResponse(
        id=uuid.uuid4(),
        camera_id="cam_01",
        severity=severity,
        description="Test incident",
        screenshot_path=image_path,
        timestamp=datetime.now().timestamp(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_should_notify_filters_by_severity(teams_svc):
    # Threshold is HIGH
    assert teams_svc._should_notify("low") is False
    assert teams_svc._should_notify("medium") is False
    assert teams_svc._should_notify("high") is True
    assert teams_svc._should_notify("critical") is True


def test_send_alert_notification_skips_if_below_threshold(teams_svc):
    alert = create_dummy_alert(severity=Severity.MEDIUM)
    
    with patch("urllib.request.urlopen") as mock_urlopen:
        teams_svc.send_alert_notification(alert)
        mock_urlopen.assert_not_called()


@patch("urllib.request.urlopen")
def test_send_alert_notification_success(mock_urlopen_class, teams_svc):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_urlopen_class.return_value.__enter__.return_value = mock_response
    
    alert = create_dummy_alert(severity=Severity.HIGH)
    
    teams_svc.send_alert_notification(alert)
    
    mock_urlopen_class.assert_called_once()
    req = mock_urlopen_class.call_args[0][0]
    
    assert req.full_url == "http://mock-teams.local/webhook"
    assert req.headers["Content-type"] == "application/json"
    
    payload = json.loads(req.data.decode("utf-8"))
    assert payload["@type"] == "MessageCard"
    assert "No Helmet" in payload["summary"]
    
    section = payload["sections"][0]
    assert "No Helmet" in section["activityTitle"]
    assert "High" in section["activitySubtitle"]


@patch("urllib.request.urlopen")
def test_send_alert_notification_with_image_note(mock_urlopen_class, teams_svc, tmp_path):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_urlopen_class.return_value.__enter__.return_value = mock_response
    
    alert = create_dummy_alert(severity=Severity.CRITICAL, has_image=True, tmp_path=tmp_path)
    
    teams_svc.send_alert_notification(alert)
    
    req = mock_urlopen_class.call_args[0][0]
    payload = json.loads(req.data.decode("utf-8"))
    
    # Assert the image note was appended because we can't upload images to Teams
    section = payload["sections"][0]
    assert "A snapshot was captured" in section["text"]


@patch("urllib.request.urlopen")
def test_send_incident_summary_success(mock_urlopen_class, teams_svc):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_urlopen_class.return_value.__enter__.return_value = mock_response
    
    incident = create_dummy_incident(severity=SeverityLevel.HIGH)
    
    teams_svc.send_incident_summary(incident)
    
    req = mock_urlopen_class.call_args[0][0]
    payload = json.loads(req.data.decode("utf-8"))
    
    assert payload["@type"] == "MessageCard"
    assert payload["summary"] == "SentinelOps Incident Logged"
    
    section = payload["sections"][0]
    assert "Test incident" in section["text"]


@patch("urllib.request.urlopen")
def test_teams_service_surfaces_http_exceptions(mock_urlopen_class, teams_svc):
    mock_urlopen_class.side_effect = urllib.error.HTTPError(
        url="http://mock-teams.local/webhook", 
        code=400, 
        msg="Bad Request", 
        hdrs={}, 
        fp=None
    )
    
    alert = create_dummy_alert(severity=Severity.HIGH)
    
    with pytest.raises(Exception, match="HTTP Error 400"):
        teams_svc.send_alert_notification(alert)


def test_teams_service_disabled_when_missing_config(monkeypatch):
    monkeypatch.setattr(settings, "teams_webhook_url", None)
    
    svc = TeamsService()
    assert svc._enabled is False
    
    alert = create_dummy_alert(severity=Severity.CRITICAL)
    
    with patch("urllib.request.urlopen") as mock_urlopen:
        svc.send_alert_notification(alert)
        mock_urlopen.assert_not_called()
