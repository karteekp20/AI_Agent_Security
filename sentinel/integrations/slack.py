from typing import Dict, Any, Optional, List
from datetime import datetime
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError


class SlackIntegration:
    """
    Slack integration for security alerts

    Supports:
    - Direct messages to users
    - Channel notifications
    - Interactive message actions
    - Block kit formatted messages
    """

    def __init__(
        self,
        bot_token: str,
        default_channel: Optional[str] = None,
    ):
        self.client = AsyncWebClient(token=bot_token)
        self.default_channel = default_channel

    async def send_alert(
        self,
        channel: Optional[str],
        alert_type: str,
        title: str,
        details: Dict[str, Any],
        severity: str = "medium",
    ) -> bool:
        """
        Send a security alert to Slack

        Args:
            channel: Channel ID (uses default if not provided)
            alert_type: Type of alert (threat, anomaly, policy, etc.)
            title: Alert title
            details: Alert details
            severity: Alert severity (low, medium, high, critical)
        """
        channel = channel or self.default_channel
        if not channel:
            raise ValueError("No channel specified")

        # Build Block Kit message
        blocks = self._build_alert_blocks(alert_type, title, details, severity)

        try:
            response = await self.client.chat_postMessage(
                channel=channel,
                blocks=blocks,
                text=f"Security Alert: {title}",  # Fallback text
            )
            return response["ok"]
        except SlackApiError as e:
            print(f"Slack API error: {e.response['error']}")
            return False

    def _build_alert_blocks(
        self,
        alert_type: str,
        title: str,
        details: Dict[str, Any],
        severity: str,
    ) -> List[Dict[str, Any]]:
        """Build Slack Block Kit blocks for alert message"""

        severity_emoji = {
            "low": ":white_circle:",
            "medium": ":large_yellow_circle:",
            "high": ":large_orange_circle:",
            "critical": ":red_circle:",
        }

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity_emoji.get(severity, ':warning:')} {title}",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Type:*\n{alert_type}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{severity.upper()}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:*\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    },
                ]
            },
        ]

        # Add details section
        if details:
            detail_text = "\n".join(
                f"• *{k}:* {v}" for k, v in details.items()
            )
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Details:*\n{detail_text}",
                }
            })

        # Add action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View in Dashboard",
                        "emoji": True,
                    },
                    "url": details.get("dashboard_url", "https://sentinel.example.com"),
                    "action_id": "view_dashboard",
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Acknowledge",
                        "emoji": True,
                    },
                    "style": "primary",
                    "action_id": "acknowledge_alert",
                },
            ]
        })

        return blocks

    async def send_daily_digest(
        self,
        channel: str,
        metrics: Dict[str, Any],
    ) -> bool:
        """
        Send daily security digest to Slack
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":shield: Daily Security Digest",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Requests:*\n{metrics.get('total_requests', 0):,}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Threats Blocked:*\n{metrics.get('blocked_requests', 0):,}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*PII Detections:*\n{metrics.get('pii_detections', 0):,}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Avg Risk Score:*\n{metrics.get('avg_risk_score', 0):.2f}",
                    },
                ]
            },
            {
                "type": "divider",
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Report generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    }
                ]
            },
        ]

        try:
            response = await self.client.chat_postMessage(
                channel=channel,
                blocks=blocks,
                text="Daily Security Digest",
            )
            return response["ok"]
        except SlackApiError as e:
            print(f"Slack API error: {e.response['error']}")
            return False