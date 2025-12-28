"""
Meta-Learning Agent: Threat Intelligence Integration
Integrates external threat feeds (MISP, STIX/TAXII, custom sources)
"""

from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
import hashlib
import requests
from collections import Counter

from .schemas import (
    ThreatFeed,
    ThreatIndicator,
    ThreatSeverity,
    DiscoveredPattern,
    PatternType,
    PatternStatus,
)


class ThreatIntelligence:
    """
    Integrates external threat intelligence feeds into security system

    Capabilities:
    1. Fetch threat indicators from multiple sources (MISP, AlienVault, etc.)
    2. Convert threat indicators to security patterns
    3. Correlate threats across sessions
    4. Prioritize threats by severity and confidence
    """

    def __init__(
        self,
        feeds: Optional[List[ThreatFeed]] = None,
        auto_update: bool = True
    ):
        """
        Initialize threat intelligence system

        Args:
            feeds: List of threat feeds to monitor
            auto_update: Automatically update feeds on schedule
        """
        self.feeds = feeds or []
        self.auto_update = auto_update

        # Cache of active threats
        self._threat_cache: Dict[str, ThreatIndicator] = {}
        self._last_update: Dict[str, datetime] = {}

    def add_feed(
        self,
        feed_name: str,
        feed_source: str,
        feed_url: Optional[str] = None,
        update_frequency_hours: int = 24
    ) -> ThreatFeed:
        """
        Add a new threat intelligence feed

        Args:
            feed_name: Human-readable name
            feed_source: Source type (MISP, AlienVault, custom)
            feed_url: API endpoint URL
            update_frequency_hours: How often to update (default: 24h)

        Returns:
            ThreatFeed object
        """
        feed_id = self._generate_feed_id(feed_name, feed_source)

        feed = ThreatFeed(
            feed_id=feed_id,
            feed_name=feed_name,
            feed_source=feed_source,
            feed_url=feed_url,
            enabled=True,
            update_frequency_hours=update_frequency_hours,
        )

        self.feeds.append(feed)
        return feed

    def update_all_feeds(self) -> Dict[str, Any]:
        """
        Update all enabled threat feeds

        Returns:
            Summary of update results
        """
        results = {
            "updated_feeds": [],
            "failed_feeds": [],
            "new_threats": 0,
            "total_threats": 0,
        }

        for feed in self.feeds:
            if not feed.enabled:
                continue

            # Check if update is needed
            if self._should_update_feed(feed):
                try:
                    indicators = self._fetch_feed_data(feed)

                    # Add to cache
                    new_count = 0
                    for indicator in indicators:
                        if indicator.indicator_id not in self._threat_cache:
                            new_count += 1
                        self._threat_cache[indicator.indicator_id] = indicator

                    # Update feed metadata
                    feed.last_updated = datetime.utcnow()
                    feed.total_threats = len(indicators)
                    feed.active_threats = sum(
                        1 for i in indicators
                        if (datetime.utcnow() - i.last_seen).days < 30
                    )

                    self._last_update[feed.feed_id] = datetime.utcnow()

                    results["updated_feeds"].append(feed.feed_name)
                    results["new_threats"] += new_count

                except Exception as e:
                    results["failed_feeds"].append({
                        "feed": feed.feed_name,
                        "error": str(e),
                    })

        results["total_threats"] = len(self._threat_cache)
        return results

    def get_relevant_threats(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[ThreatIndicator]:
        """
        Get threat indicators relevant to a user input

        Args:
            user_input: User's input text
            context: Additional context (IP, user_id, etc.)

        Returns:
            List of matching ThreatIndicators
        """
        relevant = []

        for indicator in self._threat_cache.values():
            # Check pattern match
            if indicator.indicator_type == "pattern":
                if indicator.indicator_value.lower() in user_input.lower():
                    relevant.append(indicator)

            # Check IP match (if context provided)
            elif indicator.indicator_type == "ip" and context:
                if context.get("ip_address") == indicator.indicator_value:
                    relevant.append(indicator)

            # Check domain match
            elif indicator.indicator_type == "domain":
                if indicator.indicator_value in user_input:
                    relevant.append(indicator)

        # Sort by severity and confidence
        relevant.sort(
            key=lambda i: (
                self._severity_to_int(i.severity),
                i.confidence
            ),
            reverse=True
        )

        return relevant

    def convert_to_patterns(
        self,
        min_confidence: float = 0.8,
        min_severity: ThreatSeverity = ThreatSeverity.MEDIUM
    ) -> List[DiscoveredPattern]:
        """
        Convert threat indicators to security patterns

        Args:
            min_confidence: Minimum confidence threshold
            min_severity: Minimum severity level

        Returns:
            List of DiscoveredPattern objects
        """
        patterns = []

        # Group indicators by type
        pattern_indicators = [
            i for i in self._threat_cache.values()
            if i.indicator_type == "pattern"
            and i.confidence >= min_confidence
            and self._severity_to_int(i.severity) >= self._severity_to_int(min_severity)
        ]

        signature_indicators = [
            i for i in self._threat_cache.values()
            if i.indicator_type == "signature"
            and i.confidence >= min_confidence
            and self._severity_to_int(i.severity) >= self._severity_to_int(min_severity)
        ]

        # Convert patterns
        for indicator in pattern_indicators:
            pattern_id = self._generate_pattern_id(indicator.indicator_value)

            pattern = DiscoveredPattern(
                pattern_id=pattern_id,
                pattern_type=PatternType.INJECTION_VARIANT,
                pattern_value=indicator.indicator_value,
                discovered_at=indicator.first_seen,
                discovery_method=f"threat_intelligence_{indicator.source_feed}",
                confidence=indicator.confidence,
                occurrence_count=1,  # From external source
                example_inputs=[indicator.description],
                false_positive_rate=0.0,
                status=PatternStatus.PENDING_REVIEW,
            )

            patterns.append(pattern)

        # Convert signatures
        for indicator in signature_indicators:
            pattern_id = self._generate_pattern_id(indicator.indicator_value)

            pattern = DiscoveredPattern(
                pattern_id=pattern_id,
                pattern_type=PatternType.ATTACK_SIGNATURE,
                pattern_value=indicator.indicator_value,
                discovered_at=indicator.first_seen,
                discovery_method=f"threat_intelligence_{indicator.source_feed}",
                confidence=indicator.confidence,
                occurrence_count=1,
                example_inputs=[indicator.description],
                false_positive_rate=0.0,
                status=PatternStatus.PENDING_REVIEW,
            )

            patterns.append(pattern)

        return patterns

    def correlate_threats_across_sessions(
        self,
        audit_logs: List[Dict[str, Any]],
        time_window_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Correlate threat patterns across multiple sessions

        Args:
            audit_logs: List of audit log entries
            time_window_hours: Time window for correlation

        Returns:
            List of correlated threat events
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)

        # Filter recent logs
        recent_logs = [
            log for log in audit_logs
            if datetime.fromisoformat(log.get("timestamp", "")) > cutoff_time
        ]

        correlations = []

        # Group by threat pattern
        threat_sessions: Dict[str, List[Dict[str, Any]]] = {}

        for log in recent_logs:
            # Check if log matches any threat indicators
            user_input = log.get("user_input", "")
            session_id = log.get("session_id", "")

            for indicator in self._threat_cache.values():
                if indicator.indicator_type == "pattern":
                    if indicator.indicator_value.lower() in user_input.lower():
                        threat_id = indicator.indicator_id

                        if threat_id not in threat_sessions:
                            threat_sessions[threat_id] = []

                        threat_sessions[threat_id].append({
                            "session_id": session_id,
                            "timestamp": log.get("timestamp"),
                            "user_input": user_input,
                            "ip_address": log.get("request_context", {}).get("ip_address"),
                            "user_id": log.get("request_context", {}).get("user_id"),
                        })

        # Find patterns affecting multiple sessions
        for threat_id, sessions in threat_sessions.items():
            if len(sessions) >= 3:  # Seen in 3+ sessions
                indicator = self._threat_cache[threat_id]

                # Count unique IPs and users
                unique_ips = len(set(s["ip_address"] for s in sessions if s["ip_address"]))
                unique_users = len(set(s["user_id"] for s in sessions if s["user_id"]))

                correlations.append({
                    "threat_id": threat_id,
                    "threat_type": indicator.indicator_type,
                    "threat_value": indicator.indicator_value,
                    "severity": indicator.severity,
                    "affected_sessions": len(sessions),
                    "unique_ips": unique_ips,
                    "unique_users": unique_users,
                    "first_seen": min(s["timestamp"] for s in sessions),
                    "last_seen": max(s["timestamp"] for s in sessions),
                    "description": indicator.description,
                    "recommendation": self._generate_recommendation(indicator, sessions),
                })

        # Sort by severity and affected sessions
        correlations.sort(
            key=lambda c: (
                self._severity_to_int(c["severity"]),
                c["affected_sessions"]
            ),
            reverse=True
        )

        return correlations

    def get_threat_summary(self) -> Dict[str, Any]:
        """
        Get summary of current threat landscape

        Returns:
            Summary statistics
        """
        if not self._threat_cache:
            return {
                "total_threats": 0,
                "by_severity": {},
                "by_type": {},
                "active_feeds": 0,
            }

        by_severity = Counter([i.severity for i in self._threat_cache.values()])
        by_type = Counter([i.indicator_type for i in self._threat_cache.values()])

        # Count recently seen threats (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_threats = sum(
            1 for i in self._threat_cache.values()
            if i.last_seen > thirty_days_ago
        )

        return {
            "total_threats": len(self._threat_cache),
            "recent_threats": recent_threats,
            "by_severity": dict(by_severity),
            "by_type": dict(by_type),
            "active_feeds": sum(1 for f in self.feeds if f.enabled),
            "high_confidence_threats": sum(
                1 for i in self._threat_cache.values() if i.confidence >= 0.9
            ),
        }

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    def _should_update_feed(self, feed: ThreatFeed) -> bool:
        """Check if feed needs updating"""
        if feed.feed_id not in self._last_update:
            return True

        time_since_update = datetime.utcnow() - self._last_update[feed.feed_id]
        return time_since_update.total_seconds() / 3600 >= feed.update_frequency_hours

    def _fetch_feed_data(self, feed: ThreatFeed) -> List[ThreatIndicator]:
        """
        Fetch threat data from external feed

        Note: This is a placeholder. Real implementation would integrate with
        actual threat intelligence APIs (MISP, STIX/TAXII, AlienVault OTX, etc.)
        """
        # Placeholder implementation
        # Real implementation would:
        # 1. Authenticate with feed API
        # 2. Fetch latest indicators
        # 3. Parse response format (STIX, JSON, etc.)
        # 4. Convert to ThreatIndicator objects

        if feed.feed_source == "MISP":
            return self._fetch_from_misp(feed)
        elif feed.feed_source == "AlienVault":
            return self._fetch_from_alienvault(feed)
        elif feed.feed_source == "custom":
            return self._fetch_from_custom(feed)
        else:
            return []

    def _fetch_from_misp(self, feed: ThreatFeed) -> List[ThreatIndicator]:
        """Fetch from MISP threat intelligence platform"""
        # Placeholder - real implementation would use PyMISP library
        indicators = []

        # Example: Would fetch from MISP API
        # from pymisp import PyMISP
        # misp = PyMISP(feed.feed_url, api_key, ssl=True)
        # events = misp.search(...)
        # for event in events:
        #     indicators.extend(self._parse_misp_event(event))

        return indicators

    def _fetch_from_alienvault(self, feed: ThreatFeed) -> List[ThreatIndicator]:
        """Fetch from AlienVault OTX"""
        # Placeholder - real implementation would use OTX API
        return []

    def _fetch_from_custom(self, feed: ThreatFeed) -> List[ThreatIndicator]:
        """Fetch from custom JSON feed"""
        if not feed.feed_url:
            return []

        try:
            # Fetch from URL
            response = requests.get(feed.feed_url, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Parse custom format
            indicators = []
            for item in data.get("indicators", []):
                indicator = ThreatIndicator(
                    indicator_id=item.get("id", self._generate_indicator_id(item)),
                    indicator_type=item.get("type", "pattern"),
                    indicator_value=item.get("value", ""),
                    severity=ThreatSeverity(item.get("severity", "medium")),
                    confidence=item.get("confidence", 0.8),
                    source_feed=feed.feed_name,
                    first_seen=datetime.fromisoformat(
                        item.get("first_seen", datetime.utcnow().isoformat())
                    ),
                    last_seen=datetime.fromisoformat(
                        item.get("last_seen", datetime.utcnow().isoformat())
                    ),
                    description=item.get("description", ""),
                    tags=item.get("tags", []),
                    references=item.get("references", []),
                )
                indicators.append(indicator)

            return indicators

        except Exception as e:
            print(f"Error fetching custom feed {feed.feed_name}: {e}")
            return []

    def _generate_feed_id(self, name: str, source: str) -> str:
        """Generate unique feed ID"""
        hash_obj = hashlib.sha256(f"{name}_{source}".encode())
        return f"feed_{hash_obj.hexdigest()[:16]}"

    def _generate_indicator_id(self, data: Dict[str, Any]) -> str:
        """Generate unique indicator ID"""
        hash_obj = hashlib.sha256(str(data).encode())
        return f"indicator_{hash_obj.hexdigest()[:16]}"

    def _generate_pattern_id(self, pattern: str) -> str:
        """Generate unique pattern ID"""
        hash_obj = hashlib.sha256(pattern.encode())
        return f"pattern_{hash_obj.hexdigest()[:16]}"

    def _severity_to_int(self, severity: ThreatSeverity) -> int:
        """Convert severity enum to integer for sorting"""
        severity_map = {
            ThreatSeverity.INFO: 1,
            ThreatSeverity.LOW: 2,
            ThreatSeverity.MEDIUM: 3,
            ThreatSeverity.HIGH: 4,
            ThreatSeverity.CRITICAL: 5,
        }
        return severity_map.get(severity, 0)

    def _generate_recommendation(
        self,
        indicator: ThreatIndicator,
        sessions: List[Dict[str, Any]]
    ) -> str:
        """Generate security recommendation based on threat correlation"""
        if len(sessions) >= 10:
            return f"CRITICAL: Widespread attack detected. Block pattern '{indicator.indicator_value}' immediately."

        unique_ips = len(set(s["ip_address"] for s in sessions if s["ip_address"]))
        if unique_ips >= 5:
            return f"WARNING: Coordinated attack from {unique_ips} IPs. Consider rate limiting."

        return f"NOTICE: Pattern detected in {len(sessions)} sessions. Monitor closely."
