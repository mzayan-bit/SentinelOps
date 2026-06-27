"""
SentinelOps — Email Service Tests
====================================
Tests for the email notification service, verifying severity filtering,
HTML templating, and mock SMTP dispatch.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime, timezone

from app.models.alert import Alert, AlertStatus, AlertType, Severity
from app.services.email_service import EmailService
from config.settings import settings


@pytest.fixture
def mock_settings(monkeypatch):
    """Enable email sending globally for tests and set threshold to HIGH."""
    monkeypatch.setattr(settings, "smtp_host", "localhost")
    monkeypatch.setattr(settings, "smtp_port", 1025)
    monkeypatch.setattr(settings, "smtp_user", "test")
    monkeypatch.setattr(settings, "smtp_password", "secret")
    monkeypatch.setattr(settings, "notify_emails", ["admin@sentinelops.local"])
    monkeypatch.setattr(settings, "notify_severity_threshold", "high")


@pytest.fixture
def email_svc(mock_settings):
    """Return a fresh instance of EmailService with mocked settings."""
    return EmailService()


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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_should_notify_filters_by_severity(email_svc):
    # Threshold is HIGH
    assert email_svc._should_notify(create_dummy_alert(severity=Severity.LOW)) is False
    assert email_svc._should_notify(create_dummy_alert(severity=Severity.MEDIUM)) is False
    assert email_svc._should_notify(create_dummy_alert(severity=Severity.HIGH)) is True
    assert email_svc._should_notify(create_dummy_alert(severity=Severity.CRITICAL)) is True


def test_send_alert_notification_skips_if_below_threshold(email_svc):
    alert = create_dummy_alert(severity=Severity.MEDIUM)
    
    with patch.object(email_svc, "_build_message") as mock_build:
        email_svc.send_alert_notification(alert)
        mock_build.assert_not_called()


@patch("smtplib.SMTP")
def test_send_alert_notification_success(mock_smtp_class, email_svc):
    mock_smtp_instance = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_smtp_instance
    
    alert = create_dummy_alert(severity=Severity.HIGH)
    
    email_svc.send_alert_notification(alert)
    
    mock_smtp_class.assert_called_once_with("localhost", 1025, timeout=10)
    mock_smtp_instance.starttls.assert_called_once()
    mock_smtp_instance.login.assert_called_once_with("test", "secret")
    mock_smtp_instance.send_message.assert_called_once()


@patch("smtplib.SMTP")
def test_send_alert_notification_with_image(mock_smtp_class, email_svc, tmp_path):
    mock_smtp_instance = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_smtp_instance
    
    alert = create_dummy_alert(severity=Severity.CRITICAL, has_image=True, tmp_path=tmp_path)
    
    email_svc.send_alert_notification(alert)
    
    msg = mock_smtp_instance.send_message.call_args[0][0]
    
    # Assert subject contains severity and type
    assert msg["Subject"] == "[CRITICAL] SentinelOps Alert: No Helmet"
    
    # Payload[0] is the text/html fallback, Payload[1] is the HTML, Payload[1].get_payload()[1] is the image 
    # (Because add_alternative creates a multipart/alternative, and add_related wraps it in multipart/related)
    assert msg.is_multipart()
    html_part = msg.get_payload()[0] if not isinstance(msg.get_payload()[0], list) else msg.get_payload()[0].get_payload()[0]
    
    # Just check string rendering worked
    assert "No Helmet" in str(msg)
    assert "ALR-TEST-01" in str(msg)
    
    # Ensure image data is embedded as base64
    assert "fake_jpeg_bytes" not in str(msg) # Because it gets base64 encoded
    assert "image/jpeg" in str(msg)


@patch("smtplib.SMTP")
def test_email_service_disabled_when_missing_config(mock_smtp_class, monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", None)
    
    svc = EmailService()
    assert svc._enabled is False
    
    alert = create_dummy_alert(severity=Severity.CRITICAL)
    svc.send_alert_notification(alert)
    
    mock_smtp_class.assert_not_called()


@patch("smtplib.SMTP")
def test_email_service_surfaces_smtp_exceptions(mock_smtp_class, email_svc):
    mock_smtp_instance = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_smtp_instance
    
    # Force an SMTP error
    import smtplib
    mock_smtp_instance.send_message.side_effect = smtplib.SMTPException("Connection refused")
    
    alert = create_dummy_alert(severity=Severity.HIGH)
    
    # EmailService logs and re-raises so the task worker marks it FAILED
    with pytest.raises(smtplib.SMTPException):
        email_svc.send_alert_notification(alert)
