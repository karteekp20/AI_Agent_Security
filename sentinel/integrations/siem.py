from typing import Dict, Any, Optional
from datetime import datetime
import socket
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


class SIEMExporter:
    """
    Export security events to SIEM systems

    Supports:
    - Syslog (RFC 5424)
    - CEF (Common Event Format)
    - Splunk HEC (HTTP Event Collector)
    """

    # CEF severity mapping
    CEF_SEVERITY = {
        "low": 3,
        "medium": 5,
        "high": 7,
        "critical": 10,
    }

    def __init__(
        self,
        siem_type: str,  # syslog, cef, splunk
        config: Dict[str, Any],
    ):
        self.siem_type = siem_type
        self.config = config
        self._socket = None

    async def export_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        severity: str = "medium",
    ) -> bool:
        """
        Export a security event to SIEM

        Args:
            event_type: Type of event
            event_data: Event details
            severity: Event severity
        """
        if self.siem_type == "syslog":
            return await self._export_syslog(event_type, event_data, severity)
        elif self.siem_type == "cef":
            return await self._export_cef(event_type, event_data, severity)
        elif self.siem_type == "splunk":
            return await self._export_splunk(event_type, event_data, severity)
        else:
            raise ValueError(f"Unknown SIEM type: {self.siem_type}")
    import asyncio
    
    async def _export_syslog(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        severity: str,
    ) -> bool:
        """Export event via Syslog (RFC 5424)"""
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 514)
        protocol = self.config.get("protocol", "udp")

        # Build syslog message
        # PRI = facility * 8 + severity
        # Using LOCAL0 (16) facility
        syslog_severity = {"low": 6, "medium": 4, "high": 3, "critical": 2}
        pri = 16 * 8 + syslog_severity.get(severity, 4)

        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        hostname = socket.gethostname()
        app_name = "sentinel"

        # Structured data
        sd = f'[sentinel@12345 eventType="{event_type}" severity="{severity}"]'

        # Message
        msg = json.dumps(event_data)

        syslog_msg = f"<{pri}>1 {timestamp} {hostname} {app_name} - - {sd} {msg}"

        try:
            # Run blocking socket operations in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._sync_send_syslog,
                syslog_msg,
                host,
                port,
                protocol,
            )
            return True
        except Exception as e:
            logger.error(f"Syslog export failed: {e}")
            return False

    def _sync_send_syslog(
        self,
        message: str,
        host: str,
        port: int,
        protocol: str,
    ) -> None:
        """Synchronous syslog send - runs in thread pool"""
        if protocol == "udp":
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.sendto(message.encode(), (host, port))
            finally:
                sock.close()
        else:  # TCP
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect((host, port))
                sock.sendall((message + "\n").encode())
            finally:
                sock.close()

    async def _export_cef(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        severity: str,
    ) -> bool:
        """Export event in CEF format"""
        # CEF:Version|Device Vendor|Device Product|Device Version|Signature ID|Name|Severity|Extension

        cef_severity = self.CEF_SEVERITY.get(severity, 5)

        # Build extension (key=value pairs)
        extension_parts = []
        for key, value in event_data.items():
            # CEF key mapping
            cef_key = self._map_to_cef_key(key)
            clean_value = str(value).replace("\\", "\\\\").replace("=", "\\=")
            extension_parts.append(f"{cef_key}={clean_value}")

        extension = " ".join(extension_parts)

        cef_message = (
            f"CEF:0|Sentinel|SecurityPlatform|1.0|{event_type}|"
            f"{event_type}|{cef_severity}|{extension}"
        )

        # Send via syslog
        return await self._export_syslog(event_type, {"cef": cef_message}, severity)

    async def _export_splunk(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        severity: str,
    ) -> bool:
        """Export event to Splunk HEC"""
        import httpx

        hec_url = self.config.get("hec_url")
        hec_token = self.config.get("hec_token")

        if not hec_url or not hec_token:
            raise ValueError("Splunk HEC URL and token required")

        # Build HEC event
        hec_event = {
            "time": datetime.utcnow().timestamp(),
            "sourcetype": "sentinel:security",
            "source": "sentinel",
            "event": {
                "event_type": event_type,
                "severity": severity,
                **event_data,
            }
        }

        headers = {
            "Authorization": f"Splunk {hec_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    hec_url,
                    json=hec_event,
                    headers=headers,
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception as e:
            print(f"Splunk export failed: {e}")
            return False

    def _map_to_cef_key(self, key: str) -> str:
        """Map internal keys to CEF standard keys"""
        cef_mapping = {
            "user_id": "suser",
            "source_ip": "src",
            "destination_ip": "dst",
            "risk_score": "cn1",
            "event_type": "cat",
            "message": "msg",
            "request_url": "request",
        }
        return cef_mapping.get(key, f"cs1{key}")  # Custom string field