"""
SentinelOps — Slack Notification Service
==========================================
Handles formatting and dispatching Slack alerts and incident summaries.
Supports both simple incoming webhooks (text/blocks only) and Bot Tokens
(files.upload API for sending local snapshot images).

Executed synchronously inside the TaskWorker background thread pool.
"""

from __future__ import annotations

import logging
from pathlib import Path

from slack_sdk import WebClient
from slack_sdk.webhook import WebhookClient
from slack_sdk.errors import SlackApiError

from app.models.alert import Alert
from schemas.incident import IncidentResponse
from config.settings import settings

logger = logging.getLogger("sentinelops.slack_service")

# Severity ranking for filtering
_SEVERITY_RANKS = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


class SlackService:
    """Service to handle Slack notifications."""

    def __init__(self):
        self._webhook_url = settings.slack_webhook_url
        self._bot_token = settings.slack_bot_token
        self._channel = settings.slack_channel
        
        self._enabled = bool(self._webhook_url or (self._bot_token and self._channel))
        
        if not self._enabled:
            logger.info("Slack notifications are disabled (missing webhook URL or bot token + channel).")

        self.threshold_rank = _SEVERITY_RANKS.get(
            settings.slack_severity_threshold.lower(), 3
        )
        
        self._web_client = WebClient(token=self._bot_token) if self._bot_token else None
        self._webhook_client = WebhookClient(self._webhook_url) if self._webhook_url else None

    def _should_notify(self, severity_str: str) -> bool:
        if not self._enabled:
            return False
        rank = _SEVERITY_RANKS.get(severity_str.lower(), 1)
        return rank >= self.threshold_rank

    # -----------------------------------------------------------------------
    # Alerts
    # -----------------------------------------------------------------------
    def send_alert_notification(self, alert: Alert) -> None:
        """Send a Slack notification for a new alert."""
        if not self._should_notify(alert.severity.value):
            logger.debug(
                "Skipping Slack alert %s (severity %s < threshold)",
                alert.alert_id,
                alert.severity.value,
            )
            return

        blocks = self._build_alert_blocks(alert)
        text = f"[{alert.severity.value.upper()}] SentinelOps Alert: {alert.alert_type.value}"

        try:
            # If we have a bot token and an image, we can upload it
            has_image = alert.image_path and Path(alert.image_path).exists()
            
            if self._web_client and has_image:
                logger.debug("Uploading snapshot to Slack via Bot Token.")
                self._web_client.files_upload_v2(
                    channel=self._channel,
                    initial_comment=text,
                    file=alert.image_path,
                    title=f"Snapshot: {alert.alert_id}",
                )
                # Note: files.upload_v2 doesn't natively support attaching complex blocks 
                # in the same message, so we send the blocks separately
                self._web_client.chat_postMessage(
                    channel=self._channel,
                    text=text,
                    blocks=blocks
                )
            elif self._web_client:
                # Bot token but no image
                self._web_client.chat_postMessage(
                    channel=self._channel,
                    text=text,
                    blocks=blocks
                )
            elif self._webhook_client:
                # Webhook only (can't upload local images)
                response = self._webhook_client.send(text=text, blocks=blocks)
                if response.status_code != 200:
                    logger.error("Slack webhook failed: %s", response.body)
                    raise Exception(f"Slack webhook failed: {response.status_code}")
            
            logger.info("Slack notification sent for alert %s", alert.alert_id)
        except SlackApiError as e:
            logger.error("Slack API error for alert %s: %s", alert.alert_id, e.response["error"])
            raise
        except Exception as exc:
            logger.error("Failed to send Slack alert %s: %s", alert.alert_id, exc)
            raise

    def _build_alert_blocks(self, alert: Alert) -> list[dict]:
        """Construct Slack Block Kit layout for an alert."""
        
        # Color mapping (Slack doesn't natively color blocks except via attachments, 
        # but we can use emojis for visibility)
        emoji_map = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🟠",
            "critical": "🔴",
        }
        emoji = emoji_map.get(alert.severity.value.lower(), "⚪")
        
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} SentinelOps Alert: {alert.alert_type.value}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Alert ID:*\n`{alert.alert_id}`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Camera ID:*\n`{alert.camera_id}`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{alert.severity.value}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Confidence:*\n{alert.confidence * 100:.1f}%"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:*\n{alert.status.value}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Time (UTC):*\n{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                ]
            },
            {
                "type": "divider"
            }
        ]

    # -----------------------------------------------------------------------
    # Incidents
    # -----------------------------------------------------------------------
    def send_incident_summary(self, incident: IncidentResponse) -> None:
        """Send a Slack notification summarizing an incident."""
        if not self._should_notify(incident.severity.value):
            logger.debug(
                "Skipping Slack incident %s (severity %s < threshold)",
                incident.id,
                incident.severity.value,
            )
            return

        blocks = self._build_incident_blocks(incident)
        text = f"[{incident.severity.value.upper()}] SentinelOps Incident Logged"

        try:
            has_image = incident.screenshot_path and Path(incident.screenshot_path).exists()
            
            if self._web_client and has_image:
                self._web_client.files_upload_v2(
                    channel=self._channel,
                    initial_comment=text,
                    file=incident.screenshot_path,
                    title=f"Incident Screenshot: {incident.id}",
                )
                self._web_client.chat_postMessage(
                    channel=self._channel,
                    text=text,
                    blocks=blocks
                )
            elif self._web_client:
                self._web_client.chat_postMessage(
                    channel=self._channel,
                    text=text,
                    blocks=blocks
                )
            elif self._webhook_client:
                response = self._webhook_client.send(text=text, blocks=blocks)
                if response.status_code != 200:
                    raise Exception(f"Slack webhook failed: {response.status_code}")
                    
            logger.info("Slack summary sent for incident %s", incident.id)
        except Exception as exc:
            logger.error("Failed to send Slack incident %s: %s", incident.id, exc)
            raise

    def _build_incident_blocks(self, incident: IncidentResponse) -> list[dict]:
        """Construct Slack Block Kit layout for an incident summary."""
        import datetime
        dt = datetime.datetime.fromtimestamp(incident.timestamp, tz=datetime.timezone.utc)
        
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📋 SentinelOps Incident Logged",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Description:*\n{incident.description}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Incident ID:*\n`{incident.id}`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Camera ID:*\n`{incident.camera_id}`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{incident.severity.value}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Time (UTC):*\n{dt.strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                ]
            }
        ]


slack_service = SlackService()
