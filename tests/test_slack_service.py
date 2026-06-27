"""
SentinelOps — Slack Service Tests
====================================
Tests for the Slack notification service, verifying severity filtering
and API dispatch via both Bot Token (WebClient) and WebhookClient.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime, timezone

from slack_sdk.errors import SlackApiError

from app.models.alert import Alert, AlertStatus, AlertType, Severity
from schemas.incident import IncidentResponse, SeverityLevel
from app.services.slack_service import SlackService
from config.settings import settings


@pytest.fixture
def mock_settings(monkeypatch):
    """Enable Slack bot token and channel globally for tests."""
    monkeypatch.setattr(settings, "slack_webhook_url", None)
    monkeypatch.setattr(settings, "slack_bot_token", "xoxb-test-token")
    monkeypatch.setattr(settings, "slack_channel", "#alerts")
    monkeypatch.setattr(settings, "slack_severity_threshold", "high")


@pytest.fixture
def slack_svc(mock_settings):
    """Return a fresh instance of SlackService with mocked settings."""
    return SlackService()


def create_dummy_alert(severity: Severity = Severity.HIGH, has_image: bool = False, tmp_path: Path = None) -> Alert:
    image_path = None
    if has_image and tmp_path:
        img_file = tmp_path / "dummy_snapshot.jpg"
        img_file.write_bytes(b"fake_jpeg_bytes")
        image_path = str(img_file)

    return Alert(
        alert_id="ALR-TEST-01",
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

def test_should_notify_filters_by_severity(slack_svc):
    # Threshold is HIGH
    assert slack_svc._should_notify("low") is False
    assert slack_svc._should_notify("medium") is False
    assert slack_svc._should_notify("high") is True
    assert slack_svc._should_notify("critical") is True


def test_send_alert_notification_skips_if_below_threshold(slack_svc):
    alert = create_dummy_alert(severity=Severity.MEDIUM)
    
    with patch.object(slack_svc._web_client, "chat_postMessage") as mock_post:
        slack_svc.send_alert_notification(alert)
        mock_post.assert_not_called()


def test_send_alert_notification_success_no_image(slack_svc):
    alert = create_dummy_alert(severity=Severity.HIGH)
    
    with patch.object(slack_svc._web_client, "chat_postMessage") as mock_post:
        slack_svc.send_alert_notification(alert)
        
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["channel"] == "#alerts"
        assert "[HIGH] SentinelOps Alert: No Helmet" in kwargs["text"]
        assert len(kwargs["blocks"]) == 3  # Header, fields, divider


def test_send_alert_notification_with_image_upload(slack_svc, tmp_path):
    alert = create_dummy_alert(severity=Severity.CRITICAL, has_image=True, tmp_path=tmp_path)
    
    with patch.object(slack_svc._web_client, "chat_postMessage") as mock_post:
        with patch.object(slack_svc._web_client, "files_upload_v2") as mock_upload:
            slack_svc.send_alert_notification(alert)
            
            mock_upload.assert_called_once()
            args, kwargs = mock_upload.call_args
            assert kwargs["channel"] == "#alerts"
            assert kwargs["file"] == alert.image_path
            
            mock_post.assert_called_once()


def test_send_incident_summary_success(slack_svc):
    incident = create_dummy_incident(severity=SeverityLevel.HIGH)
    
    with patch.object(slack_svc._web_client, "chat_postMessage") as mock_post:
        slack_svc.send_incident_summary(incident)
        
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "[HIGH] SentinelOps Incident Logged" in kwargs["text"]
        assert len(kwargs["blocks"]) == 3


@patch("app.services.slack_service.WebhookClient")
def test_slack_webhook_fallback(mock_webhook_class, monkeypatch):
    monkeypatch.setattr(settings, "slack_bot_token", None)
    monkeypatch.setattr(settings, "slack_channel", None)
    monkeypatch.setattr(settings, "slack_webhook_url", "http://mock-slack.local/webhook")
    
    mock_webhook_instance = MagicMock()
    mock_webhook_instance.send.return_value.status_code = 200
    mock_webhook_class.return_value = mock_webhook_instance
    
    svc = SlackService()
    alert = create_dummy_alert(severity=Severity.HIGH)
    
    svc.send_alert_notification(alert)
    
    mock_webhook_instance.send.assert_called_once()
    args, kwargs = mock_webhook_instance.send.call_args
    assert "[HIGH] SentinelOps Alert: No Helmet" in kwargs["text"]
    assert len(kwargs["blocks"]) == 3


def test_slack_service_surfaces_api_exceptions(slack_svc):
    alert = create_dummy_alert(severity=Severity.HIGH)
    
    with patch.object(slack_svc._web_client, "chat_postMessage") as mock_post:
        mock_post.side_effect = SlackApiError("Error", response={"error": "channel_not_found"})
        
        with pytest.raises(SlackApiError):
            slack_svc.send_alert_notification(alert)
