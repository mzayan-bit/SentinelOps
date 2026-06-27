"""
SentinelOps — Microsoft Teams Notification Service
==================================================
Handles formatting and dispatching alerts/incidents to MS Teams Incoming Webhooks.
Utilises Adaptive Cards (or legacy MessageCards) for rich layout.

Executed synchronously inside the TaskWorker background thread pool.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone

from app.models.alert import Alert
from schemas.incident import IncidentResponse
from config.settings import settings

logger = logging.getLogger("sentinelops.teams_service")

# Severity ranking for filtering
_SEVERITY_RANKS = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


class TeamsService:
    """Service to handle Microsoft Teams notifications."""

    def __init__(self):
        self._webhook_url = settings.teams_webhook_url
        self._enabled = bool(self._webhook_url)
        
        if not self._enabled:
            logger.info("MS Teams notifications are disabled (missing webhook URL).")

        self.threshold_rank = _SEVERITY_RANKS.get(
            settings.teams_severity_threshold.lower(), 3
        )

    def _should_notify(self, severity_str: str) -> bool:
        if not self._enabled:
            return False
        rank = _SEVERITY_RANKS.get(severity_str.lower(), 1)
        return rank >= self.threshold_rank

    # -----------------------------------------------------------------------
    # Alerts
    # -----------------------------------------------------------------------
    def send_alert_notification(self, alert: Alert) -> None:
        """Send a Teams notification for a new alert."""
        if not self._should_notify(alert.severity.value):
            logger.debug(
                "Skipping Teams alert %s (severity %s < threshold)",
                alert.alert_id,
                alert.severity.value,
            )
            return

        payload = self._build_alert_payload(alert)
        
        try:
            self._send_webhook(payload)
            logger.info("Teams notification sent for alert %s", alert.alert_id)
        except Exception as exc:
            logger.error("Failed to send Teams alert %s: %s", alert.alert_id, exc)
            raise

    def _build_alert_payload(self, alert: Alert) -> dict:
        """Construct a MessageCard payload for an alert.
        MessageCard is the most universally supported format for generic Incoming Webhooks.
        """
        color_map = {
            "low": "28A745",
            "medium": "FFC107",
            "high": "FD7E14",
            "critical": "DC3545",
        }
        theme_color = color_map.get(alert.severity.value.lower(), "0078D7")
        
        # We can't attach local images to Teams webhooks, so we just mention it
        image_note = ""
        if alert.image_path:
            image_note = "\n\n*(A snapshot was captured. Please view it in the SentinelOps dashboard.)*"

        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": theme_color,
            "summary": f"SentinelOps Alert: {alert.alert_type.value}",
            "sections": [{
                "activityTitle": f"**SentinelOps Alert: {alert.alert_type.value}**",
                "activitySubtitle": f"Severity: {alert.severity.value}",
                "facts": [
                    {"name": "Alert ID", "value": alert.alert_id},
                    {"name": "Camera ID", "value": alert.camera_id},
                    {"name": "Confidence", "value": f"{alert.confidence * 100:.1f}%"},
                    {"name": "Status", "value": alert.status.value},
                    {"name": "Time (UTC)", "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')},
                ],
                "markdown": True,
                "text": image_note
            }]
        }

    # -----------------------------------------------------------------------
    # Incidents
    # -----------------------------------------------------------------------
    def send_incident_summary(self, incident: IncidentResponse) -> None:
        """Send a Teams notification summarizing an incident."""
        if not self._should_notify(incident.severity.value):
            logger.debug(
                "Skipping Teams incident %s (severity %s < threshold)",
                incident.id,
                incident.severity.value,
            )
            return

        payload = self._build_incident_payload(incident)
        
        try:
            self._send_webhook(payload)
            logger.info("Teams summary sent for incident %s", incident.id)
        except Exception as exc:
            logger.error("Failed to send Teams incident %s: %s", incident.id, exc)
            raise

    def _build_incident_payload(self, incident: IncidentResponse) -> dict:
        import datetime
        dt = datetime.datetime.fromtimestamp(incident.timestamp, tz=datetime.timezone.utc)
        
        color_map = {
            "low": "28A745",
            "medium": "FFC107",
            "high": "FD7E14",
            "critical": "DC3545",
        }
        theme_color = color_map.get(incident.severity.value.lower(), "0078D7")

        image_note = ""
        if incident.screenshot_path:
            image_note = "\n\n*(A screenshot was captured. Please view it in the SentinelOps dashboard.)*"

        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": theme_color,
            "summary": "SentinelOps Incident Logged",
            "sections": [{
                "activityTitle": "**SentinelOps Incident Logged**",
                "activitySubtitle": f"Severity: {incident.severity.value}",
                "facts": [
                    {"name": "Incident ID", "value": str(incident.id)},
                    {"name": "Camera ID", "value": incident.camera_id},
                    {"name": "Time (UTC)", "value": dt.strftime('%Y-%m-%d %H:%M:%S')},
                ],
                "markdown": True,
                "text": f"**Description:** {incident.description}{image_note}"
            }]
        }

    def _send_webhook(self, payload: dict) -> None:
        if not self._webhook_url:
            raise ValueError("Teams webhook URL not configured")

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self._webhook_url, 
            data=data, 
            headers={"Content-Type": "application/json"}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status not in (200, 202):
                    raise ValueError(f"Unexpected status code: {response.status}")
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP Error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"URL Error: {e.reason}")


teams_service = TeamsService()
