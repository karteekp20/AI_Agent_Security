"""Microsoft Teams Integration - Adaptive Cards notifications"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import aiohttp
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class TeamsConfig:
    """Configuration for Microsoft Teams integration"""
    webhook_url: str
    enabled: bool = True
    timeout: int = 30


class TeamsIntegration:
    """Microsoft Teams webhook integration using Adaptive Cards"""

    def __init__(self, config: TeamsConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def test_connection(self) -> bool:
        """Test the webhook connection"""
        try:
            card = self._build_test_card()
            return await self._send_card(card)
        except Exception as e:
            logger.error(f"Teams connection test failed: {e}")
            return False

    async def send_threat_alert(self, threat: Dict[str, Any]) -> bool:
        """Send a threat alert to Teams"""
        card = self._build_threat_card(threat)
        return await self._send_card(card)

    async def send_anomaly_alert(self, anomaly: Dict[str, Any]) -> bool:
        """Send an anomaly alert to Teams"""
        card = self._build_anomaly_card(anomaly)
        return await self._send_card(card)

    async def send_daily_digest(self, stats: Dict[str, Any]) -> bool:
        """Send a daily security digest to Teams"""
        card = self._build_digest_card(stats)
        return await self._send_card(card)

    async def send_policy_update(self, policy: Dict[str, Any], action: str) -> bool:
        """Send a policy update notification"""
        card = self._build_policy_card(policy, action)
        return await self._send_card(card)

    async def _send_card(self, card: Dict[str, Any]) -> bool:
        """Send an Adaptive Card to Teams"""
        if not self.config.enabled:
            logger.debug("Teams integration is disabled")
            return False

        session = await self._get_session()

        payload = {
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": card
            }]
        }

        try:
            async with session.post(
                self.config.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    logger.debug("Teams message sent successfully")
                    return True
                else:
                    body = await response.text()
                    logger.error(f"Teams webhook failed: {response.status} - {body}")
                    return False
        except aiohttp.ClientError as e:
            logger.error(f"Teams webhook error: {e}")
            return False

    def _build_test_card(self) -> Dict[str, Any]:
        """Build a test connection card"""
        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Sentinel AI Security",
                    "weight": "Bolder",
                    "size": "Large",
                    "color": "Accent"
                },
                {
                    "type": "TextBlock",
                    "text": "Connection test successful!",
                    "color": "Good",
                    "spacing": "Medium"
                },
                {
                    "type": "TextBlock",
                    "text": f"Tested at: {datetime.utcnow().isoformat()}Z",
                    "size": "Small",
                    "isSubtle": True
                }
            ]
        }

    def _build_threat_card(self, threat: Dict[str, Any]) -> Dict[str, Any]:
        """Build a threat alert Adaptive Card"""
        severity = threat.get("severity", "medium")
        color_map = {
            "critical": "Attention",
            "high": "Attention",
            "medium": "Warning",
            "low": "Good"
        }
        color = color_map.get(severity, "Default")

        # Severity indicator emoji
        severity_emoji = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "⚡",
            "low": "ℹ️"
        }.get(severity, "📋")

        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "Container",
                    "style": color,
                    "bleed": True,
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": f"{severity_emoji} Security Threat Detected",
                            "weight": "Bolder",
                            "size": "Large",
                            "wrap": True
                        }
                    ]
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "Type:", "value": threat.get("type", "Unknown")},
                        {"title": "Severity:", "value": severity.upper()},
                        {"title": "User:", "value": threat.get("user_id", "N/A")},
                        {"title": "IP Address:", "value": threat.get("ip_address", "N/A")},
                        {"title": "Time:", "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")},
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": f"**Description:** {threat.get('description', 'No description available')}",
                    "wrap": True,
                    "spacing": "Medium"
                }
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "View Details",
                    "url": threat.get("details_url", "#")
                },
                {
                    "type": "Action.OpenUrl",
                    "title": "View User",
                    "url": threat.get("user_url", "#")
                }
            ]
        }

    def _build_anomaly_card(self, anomaly: Dict[str, Any]) -> Dict[str, Any]:
        """Build an anomaly alert Adaptive Card"""
        score = anomaly.get("score", 0)

        # Determine severity based on score
        if score >= 0.8:
            severity = "critical"
            color = "Attention"
        elif score >= 0.6:
            severity = "high"
            color = "Warning"
        elif score >= 0.4:
            severity = "medium"
            color = "Warning"
        else:
            severity = "low"
            color = "Accent"

        top_features = anomaly.get("top_features", [])
        features_text = ", ".join(f[:20] for f in top_features[:5]) if top_features else "N/A"

        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "Container",
                    "style": color,
                    "bleed": True,
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "🔍 Behavioral Anomaly Detected",
                            "weight": "Bolder",
                            "size": "Large"
                        }
                    ]
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "User:", "value": anomaly.get("user_id", "N/A")},
                        {"title": "Anomaly Score:", "value": f"{score:.2f} ({severity})"},
                        {"title": "Time:", "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")},
                        {"title": "Top Features:", "value": features_text},
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": anomaly.get("explanation", "Unusual behavior pattern detected"),
                    "wrap": True,
                    "spacing": "Medium"
                }
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "View Analysis",
                    "url": anomaly.get("details_url", "#")
                }
            ]
        }

    def _build_digest_card(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Build a daily digest Adaptive Card"""
        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "📊 Daily Security Digest",
                    "weight": "Bolder",
                    "size": "Large",
                    "color": "Accent"
                },
                {
                    "type": "TextBlock",
                    "text": f"Report for {datetime.utcnow().strftime('%Y-%m-%d')}",
                    "isSubtle": True
                },
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {"type": "TextBlock", "text": "Total Requests", "weight": "Bolder"},
                                {"type": "TextBlock", "text": str(stats.get("total_requests", 0)), "size": "ExtraLarge"}
                            ]
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {"type": "TextBlock", "text": "Threats Blocked", "weight": "Bolder"},
                                {"type": "TextBlock", "text": str(stats.get("threats_blocked", 0)), "size": "ExtraLarge", "color": "Attention"}
                            ]
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {"type": "TextBlock", "text": "PII Detected", "weight": "Bolder"},
                                {"type": "TextBlock", "text": str(stats.get("pii_detected", 0)), "size": "ExtraLarge", "color": "Warning"}
                            ]
                        }
                    ]
                },
                {
                    "type": "FactSet",
                    "spacing": "Medium",
                    "facts": [
                        {"title": "Active Policies:", "value": str(stats.get("active_policies", 0))},
                        {"title": "Anomalies Detected:", "value": str(stats.get("anomalies", 0))},
                        {"title": "False Positive Rate:", "value": f"{stats.get('fp_rate', 0):.1%}"},
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "View Full Report",
                    "url": stats.get("report_url", "#")
                }
            ]
        }

    def _build_policy_card(self, policy: Dict[str, Any], action: str) -> Dict[str, Any]:
        """Build a policy update notification card"""
        action_emoji = {
            "created": "✨",
            "updated": "📝",
            "deployed": "🚀",
            "archived": "📦",
            "deleted": "🗑️"
        }.get(action, "📋")

        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": f"{action_emoji} Policy {action.title()}",
                    "weight": "Bolder",
                    "size": "Large"
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "Policy:", "value": policy.get("name", "Unknown")},
                        {"title": "Type:", "value": policy.get("type", "N/A")},
                        {"title": "Status:", "value": policy.get("status", "N/A")},
                        {"title": "Version:", "value": str(policy.get("version", 1))},
                        {"title": "Modified By:", "value": policy.get("modified_by", "System")},
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "View Policy",
                    "url": policy.get("url", "#")
                }
            ]
        }
