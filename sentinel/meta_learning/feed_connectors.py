from abc import ABC, abstractmethod
from typing import List, Optional
import httpx
from datetime import datetime

from .schemas import ThreatIndicator, ThreatSeverity, ThreatFeed


class BaseFeedConnector(ABC):
    """Abstract base class for threat feed connectors"""

    @abstractmethod
    async def fetch_indicators(self, since: Optional[datetime] = None) -> List[ThreatIndicator]:
        """Fetch threat indicators from the feed"""
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate feed configuration"""
        pass


class AlienVaultOTXConnector(BaseFeedConnector):
    """
    AlienVault OTX (Open Threat Exchange) connector

    Documentation: https://otx.alienvault.com/api
    """

    BASE_URL = "https://otx.alienvault.com/api/v1"

    def __init__(self, api_key: str, pulse_days: int = 7):
        self.api_key = api_key
        self.pulse_days = pulse_days
        self.headers = {"X-OTX-API-KEY": api_key}

    def validate_config(self) -> bool:
        return bool(self.api_key)

    async def fetch_indicators(
        self,
        since: Optional[datetime] = None
    ) -> List[ThreatIndicator]:
        """Fetch indicators from subscribed pulses"""
        indicators = []

        async with httpx.AsyncClient() as client:
            # Get subscribed pulses
            response = await client.get(
                f"{self.BASE_URL}/pulses/subscribed",
                headers=self.headers,
                params={"modified_since": since.isoformat() if since else None},
                timeout=30.0,
            )
            response.raise_for_status()

            data = response.json()

            for pulse in data.get("results", []):
                for indicator_data in pulse.get("indicators", []):
                    indicator = self._parse_indicator(indicator_data, pulse)
                    if indicator:
                        indicators.append(indicator)

        return indicators

    def _parse_indicator(
        self,
        data: dict,
        pulse: dict
    ) -> Optional[ThreatIndicator]:
        """Parse OTX indicator format"""
        indicator_type_map = {
            "domain": "domain",
            "hostname": "domain",
            "IPv4": "ip",
            "IPv6": "ip",
            "URL": "url",
            "FileHash-MD5": "hash",
            "FileHash-SHA256": "hash",
        }

        otx_type = data.get("type", "")
        mapped_type = indicator_type_map.get(otx_type, "pattern")

        # Map pulse TLP to severity
        tlp = pulse.get("TLP", "white")
        severity_map = {
            "white": ThreatSeverity.LOW,
            "green": ThreatSeverity.MEDIUM,
            "amber": ThreatSeverity.HIGH,
            "red": ThreatSeverity.CRITICAL,
        }

        return ThreatIndicator(
            indicator_id=f"otx_{data.get('id', '')}",
            indicator_type=mapped_type,
            indicator_value=data.get("indicator", ""),
            severity=severity_map.get(tlp, ThreatSeverity.MEDIUM),
            confidence=0.85,  # OTX community-validated
            source_feed="AlienVault OTX",
            first_seen=datetime.fromisoformat(
                data.get("created", datetime.utcnow().isoformat())
            ),
            last_seen=datetime.utcnow(),
            description=pulse.get("description", ""),
            tags=pulse.get("tags", []),
            references=[pulse.get("id", "")],
        )


class MISPConnector(BaseFeedConnector):
    """
    MISP (Malware Information Sharing Platform) connector

    Documentation: https://www.misp-project.org/documentation/
    """

    def __init__(self, url: str, api_key: str, verify_ssl: bool = True):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.headers = {
            "Authorization": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def validate_config(self) -> bool:
        return bool(self.url and self.api_key)

    async def fetch_indicators(
        self,
        since: Optional[datetime] = None
    ) -> List[ThreatIndicator]:
        """Fetch indicators from MISP events"""
        indicators = []

        # Build search query
        search_body = {
            "returnFormat": "json",
            "enforceWarninglist": True,
            "includeDecayScore": True,
        }

        if since:
            search_body["timestamp"] = int(since.timestamp())

        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            response = await client.post(
                f"{self.url}/attributes/restSearch",
                headers=self.headers,
                json=search_body,
                timeout=60.0,
            )
            response.raise_for_status()

            data = response.json()

            for attr in data.get("response", {}).get("Attribute", []):
                indicator = self._parse_attribute(attr)
                if indicator:
                    indicators.append(indicator)

        return indicators

    def _parse_attribute(self, attr: dict) -> Optional[ThreatIndicator]:
        """Parse MISP attribute to ThreatIndicator"""
        # MISP type mapping
        type_map = {
            "ip-src": "ip",
            "ip-dst": "ip",
            "domain": "domain",
            "hostname": "domain",
            "url": "url",
            "md5": "hash",
            "sha256": "hash",
            "pattern-in-traffic": "pattern",
            "yara": "signature",
        }

        misp_type = attr.get("type", "")
        mapped_type = type_map.get(misp_type, "pattern")

        # Calculate confidence from decay score
        decay_score = attr.get("decay_score", {})
        confidence = decay_score.get("score", 80) / 100

        return ThreatIndicator(
            indicator_id=f"misp_{attr.get('uuid', '')}",
            indicator_type=mapped_type,
            indicator_value=attr.get("value", ""),
            severity=self._map_threat_level(attr.get("event", {}).get("threat_level_id")),
            confidence=confidence,
            source_feed="MISP",
            first_seen=datetime.fromtimestamp(int(attr.get("timestamp", 0))),
            last_seen=datetime.utcnow(),
            description=attr.get("comment", ""),
            tags=[tag.get("name", "") for tag in attr.get("Tag", [])],
            references=[attr.get("event_id", "")],
        )

    def _map_threat_level(self, level: Optional[str]) -> ThreatSeverity:
        """Map MISP threat level to severity"""
        levels = {
            "1": ThreatSeverity.CRITICAL,  # High
            "2": ThreatSeverity.HIGH,       # Medium
            "3": ThreatSeverity.MEDIUM,     # Low
            "4": ThreatSeverity.LOW,        # Undefined
        }
        return levels.get(level or "4", ThreatSeverity.MEDIUM)


class AbuseCHConnector(BaseFeedConnector):
    """
    abuse.ch threat feeds connector

    Supports: URLhaus, Feodo Tracker, SSL Blacklist
    """

    FEEDS = {
        "urlhaus": "https://urlhaus.abuse.ch/downloads/json_recent/",
        "feodo": "https://feodotracker.abuse.ch/downloads/ipblocklist_recommended.json",
        "sslbl": "https://sslbl.abuse.ch/blacklist/sslipblacklist.json",
    }

    def __init__(self, enabled_feeds: List[str] = None):
        self.enabled_feeds = enabled_feeds or ["urlhaus", "feodo"]

    def validate_config(self) -> bool:
        return len(self.enabled_feeds) > 0

    async def fetch_indicators(
        self,
        since: Optional[datetime] = None
    ) -> List[ThreatIndicator]:
        """Fetch indicators from enabled abuse.ch feeds"""
        indicators = []

        async with httpx.AsyncClient() as client:
            for feed_name in self.enabled_feeds:
                if feed_name not in self.FEEDS:
                    continue

                try:
                    response = await client.get(
                        self.FEEDS[feed_name],
                        timeout=30.0,
                    )
                    response.raise_for_status()

                    data = response.json()
                    feed_indicators = self._parse_feed(feed_name, data)
                    indicators.extend(feed_indicators)

                except Exception as e:
                    print(f"Error fetching {feed_name}: {e}")

        return indicators

    def _parse_feed(self, feed_name: str, data: dict) -> List[ThreatIndicator]:
        """Parse abuse.ch feed data"""
        indicators = []

        if feed_name == "urlhaus":
            for entry in data.get("urls", [])[:1000]:  # Limit
                indicators.append(ThreatIndicator(
                    indicator_id=f"urlhaus_{entry.get('id', '')}",
                    indicator_type="url",
                    indicator_value=entry.get("url", ""),
                    severity=ThreatSeverity.HIGH,
                    confidence=0.9,
                    source_feed="URLhaus",
                    first_seen=datetime.fromisoformat(
                        entry.get("date_added", datetime.utcnow().isoformat())
                    ),
                    last_seen=datetime.utcnow(),
                    description=f"Malware: {entry.get('threat', 'unknown')}",
                    tags=entry.get("tags", []),
                    references=[entry.get("urlhaus_reference", "")],
                ))

        elif feed_name == "feodo":
            for entry in data.get("ipblocklist", []):
                indicators.append(ThreatIndicator(
                    indicator_id=f"feodo_{entry.get('ip_address', '')}",
                    indicator_type="ip",
                    indicator_value=entry.get("ip_address", ""),
                    severity=ThreatSeverity.CRITICAL,
                    confidence=0.95,
                    source_feed="Feodo Tracker",
                    first_seen=datetime.fromisoformat(
                        entry.get("first_seen", datetime.utcnow().isoformat())
                    ),
                    last_seen=datetime.utcnow(),
                    description=f"Botnet C2: {entry.get('malware', 'unknown')}",
                    tags=[entry.get("malware", "")],
                    references=[],
                ))

        return indicators