"""
SentinelOps — Email Notification Service
==========================================
Handles formatting and dispatching SMTP email alerts. 
Executed synchronously inside the TaskWorker background thread pool.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.models.alert import Alert
from config.settings import settings

logger = logging.getLogger("sentinelops.email_service")

# Severity ranking for filtering
_SEVERITY_RANKS = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

# Template setup
_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)))


class EmailService:
    """Service to handle SMTP email notifications."""

    def __init__(self):
        self._enabled = bool(
            settings.smtp_host
            and settings.smtp_user
            and settings.notify_emails
        )
        if not self._enabled:
            logger.info("Email notifications are disabled (missing SMTP config or recipients).")

        self.threshold_rank = _SEVERITY_RANKS.get(
            settings.notify_severity_threshold.lower(), 3
        )

    def _should_notify(self, alert: Alert) -> bool:
        if not self._enabled:
            return False
        alert_rank = _SEVERITY_RANKS.get(alert.severity.value.lower(), 1)
        return alert_rank >= self.threshold_rank

    def send_alert_notification(self, alert: Alert) -> None:
        """Render and send an HTML email for the given alert.
        
        Designed to be submitted to `task_worker` for background execution.
        """
        if not self._should_notify(alert):
            logger.debug(
                "Skipping email for alert %s (severity %s < threshold)",
                alert.alert_id,
                alert.severity.value,
            )
            return

        try:
            msg = self._build_message(alert)
            self._send_smtp(msg)
            logger.info("Email notification sent for alert %s", alert.alert_id)
        except Exception as exc:
            logger.error("Failed to send email for alert %s: %s", alert.alert_id, exc)
            # We catch and log here so the task worker marks it FAILED without 
            # crashing the parent process if executed directly.
            raise

    def _build_message(self, alert: Alert) -> EmailMessage:
        msg = EmailMessage()
        msg["Subject"] = f"[{alert.severity.value.upper()}] SentinelOps Alert: {alert.alert_type.value}"
        msg["From"] = settings.smtp_from_email or settings.smtp_user
        msg["To"] = ", ".join(settings.notify_emails)

        # Handle snapshot
        has_snapshot = False
        img_data = None
        img_cid = None
        
        if alert.image_path:
            img_path = Path(alert.image_path)
            if img_path.exists():
                has_snapshot = True
                img_data = img_path.read_bytes()
                img_cid = make_msgid(domain="sentinelops.local")

        # Render HTML
        template = _jinja_env.get_template("alert_email.html")
        html_content = template.render(
            alert=alert,
            has_snapshot=has_snapshot,
        )

        msg.set_content("Please enable HTML to view this SentinelOps alert.")
        msg.add_alternative(html_content, subtype="html")

        # Attach image inline if present
        if has_snapshot and img_data and img_cid:
            # add_related is used to embed images referenced via CID in the HTML
            msg.get_payload()[1].add_related(
                img_data,
                maintype="image",
                subtype="jpeg",
                cid=img_cid.strip("<>"),
            )

        return msg

    def _send_smtp(self, msg: EmailMessage) -> None:
        if not settings.smtp_host:
            raise ValueError("SMTP host not configured")
            
        port = settings.smtp_port
        
        if settings.smtp_tls:
            with smtplib.SMTP(settings.smtp_host, port, timeout=10) as server:
                server.starttls()
                if settings.smtp_user and settings.smtp_password:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, port, timeout=10) as server:
                if settings.smtp_user and settings.smtp_password:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)


email_service = EmailService()
