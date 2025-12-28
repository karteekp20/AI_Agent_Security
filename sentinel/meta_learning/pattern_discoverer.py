"""
Meta-Learning Agent: Pattern Discovery
Automatically discovers new attack patterns from audit logs
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import Counter
import re
import hashlib

from .schemas import (
    DiscoveredPattern,
    PatternType,
    PatternStatus,
    MetaLearningConfig,
)


class MetaLearningAgent:
    """
    Discovers new security patterns from historical audit logs

    Capabilities:
    1. Analyzes blocked requests to find common attack signatures
    2. Identifies new injection variants
    3. Discovers false positive patterns
    4. Suggests policy updates
    """

    def __init__(self, config: MetaLearningConfig):
        self.config = config
        self._llm_client = None  # Optional LLM for deep analysis

    def analyze_audit_logs(
        self,
        audit_logs: List[Dict[str, Any]],
        time_window_hours: Optional[int] = None
    ) -> List[DiscoveredPattern]:
        """
        Analyze audit logs to discover new patterns

        Args:
            audit_logs: List of audit log entries
            time_window_hours: Time window to analyze (default: config.lookback_hours)

        Returns:
            List of discovered patterns
        """
        if time_window_hours is None:
            time_window_hours = self.config.lookback_hours

        # Filter logs to time window
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        recent_logs = [
            log for log in audit_logs
            if datetime.fromisoformat(log.get('timestamp', '')) > cutoff_time
        ]

        discovered_patterns = []

        # 1. Analyze blocked requests for new attack signatures
        discovered_patterns.extend(
            self._discover_injection_variants(recent_logs)
        )

        # 2. Analyze false positives (blocked but shouldn't have been)
        discovered_patterns.extend(
            self._discover_false_positive_patterns(recent_logs)
        )

        # 3. Analyze PII detection misses
        discovered_patterns.extend(
            self._discover_missed_pii_patterns(recent_logs)
        )

        # 4. Filter by confidence and occurrence thresholds
        filtered_patterns = [
            p for p in discovered_patterns
            if p.occurrence_count >= self.config.min_pattern_occurrences
            and p.confidence >= self.config.min_pattern_confidence
        ]

        return filtered_patterns

    def _discover_injection_variants(
        self,
        audit_logs: List[Dict[str, Any]]
    ) -> List[DiscoveredPattern]:
        """
        Discover new prompt injection variants from blocked requests

        Looks for:
        - Common phrases in blocked requests
        - Paraphrased attack patterns
        - Novel injection techniques
        """
        discovered = []

        # Extract all blocked inputs with injection detected
        blocked_injections = []
        for log in audit_logs:
            if log.get('blocked') and log.get('injection_detected'):
                user_input = log.get('user_input', '')
                if user_input:
                    blocked_injections.append(user_input)

        if len(blocked_injections) < self.config.min_pattern_occurrences:
            return []

        # Find common phrases using n-gram analysis
        common_phrases = self._extract_common_phrases(
            blocked_injections,
            min_length=3,
            max_length=8
        )

        # Create patterns from common phrases
        for phrase, count in common_phrases.items():
            if count >= self.config.min_pattern_occurrences:
                # Generate regex pattern
                pattern_value = self._phrase_to_regex(phrase)

                # Calculate confidence based on frequency
                confidence = min(count / len(blocked_injections), 1.0)

                if confidence >= self.config.min_pattern_confidence:
                    pattern_id = self._generate_pattern_id(pattern_value)

                    pattern = DiscoveredPattern(
                        pattern_id=pattern_id,
                        pattern_type=PatternType.INJECTION_VARIANT,
                        pattern_value=pattern_value,
                        discovery_method="n-gram_frequency",
                        confidence=confidence,
                        occurrence_count=count,
                        example_inputs=[
                            inp for inp in blocked_injections
                            if phrase.lower() in inp.lower()
                        ][:5],  # Keep 5 examples
                        status=PatternStatus.PENDING_REVIEW,
                    )

                    discovered.append(pattern)

        return discovered

    def _discover_false_positive_patterns(
        self,
        audit_logs: List[Dict[str, Any]]
    ) -> List[DiscoveredPattern]:
        """
        Discover patterns that frequently cause false positives

        Helps identify overly aggressive rules that need refinement
        """
        discovered = []

        # Look for patterns in requests that were blocked but had low actual risk
        # (This would require feedback/labeling from security team)

        # For now, use heuristic: blocked + low final risk score
        false_positives = []
        for log in audit_logs:
            if log.get('blocked'):
                risk_score = log.get('aggregated_risk', {}).get('overall_risk_score', 1.0)
                if risk_score < 0.5:  # Low risk but still blocked = potential FP
                    user_input = log.get('user_input', '')
                    if user_input:
                        false_positives.append(user_input)

        if len(false_positives) < self.config.min_pattern_occurrences:
            return []

        # Find common patterns in FPs
        common_phrases = self._extract_common_phrases(
            false_positives,
            min_length=2,
            max_length=5
        )

        for phrase, count in common_phrases.items():
            if count >= self.config.min_pattern_occurrences:
                pattern_id = self._generate_pattern_id(phrase)
                confidence = min(count / len(false_positives), 1.0)

                pattern = DiscoveredPattern(
                    pattern_id=pattern_id,
                    pattern_type=PatternType.FALSE_POSITIVE,
                    pattern_value=phrase,
                    discovery_method="false_positive_analysis",
                    confidence=confidence,
                    occurrence_count=count,
                    example_inputs=[inp for inp in false_positives if phrase.lower() in inp.lower()][:5],
                    false_positive_rate=1.0,  # These ARE false positives
                    status=PatternStatus.PENDING_REVIEW,
                )

                discovered.append(pattern)

        return discovered

    def _discover_missed_pii_patterns(
        self,
        audit_logs: List[Dict[str, Any]]
    ) -> List[DiscoveredPattern]:
        """
        Discover PII patterns that current rules miss

        Looks for:
        - Custom ID formats
        - Domain-specific identifiers
        - New PII types
        """
        discovered = []

        # Look for inputs that had low PII detection but were flagged by humans
        # (Would require human feedback loop)

        # Placeholder for now - would integrate with feedback system
        return discovered

    def _extract_common_phrases(
        self,
        texts: List[str],
        min_length: int = 3,
        max_length: int = 8
    ) -> Dict[str, int]:
        """
        Extract common phrases from texts using n-gram analysis

        Returns:
            Dict of {phrase: count}
        """
        phrase_counts = Counter()

        for text in texts:
            words = text.lower().split()

            # Generate n-grams
            for n in range(min_length, min(max_length + 1, len(words) + 1)):
                for i in range(len(words) - n + 1):
                    phrase = ' '.join(words[i:i+n])
                    phrase_counts[phrase] += 1

        # Filter to phrases appearing in multiple texts
        min_documents = max(2, len(texts) // 10)  # At least 10% of documents

        return {
            phrase: count
            for phrase, count in phrase_counts.items()
            if count >= min_documents
        }

    def _phrase_to_regex(self, phrase: str) -> str:
        """
        Convert a phrase to a regex pattern

        Makes it more flexible (handles variations in spacing, punctuation)
        """
        # Escape special regex characters
        escaped = re.escape(phrase)

        # Allow flexible whitespace
        pattern = escaped.replace(r'\ ', r'\s+')

        # Case insensitive flag
        pattern = f"(?i){pattern}"

        return pattern

    def _generate_pattern_id(self, pattern: str) -> str:
        """Generate unique pattern ID from pattern value"""
        hash_obj = hashlib.sha256(pattern.encode())
        return f"pattern_{hash_obj.hexdigest()[:16]}"

    def get_pattern_summary(
        self,
        patterns: List[DiscoveredPattern]
    ) -> Dict[str, Any]:
        """
        Generate summary report of discovered patterns

        Args:
            patterns: List of discovered patterns

        Returns:
            Summary statistics
        """
        if not patterns:
            return {
                "total_patterns": 0,
                "by_type": {},
                "by_status": {},
                "high_confidence_count": 0,
            }

        by_type = Counter([p.pattern_type for p in patterns])
        by_status = Counter([p.status for p in patterns])
        high_confidence = sum(1 for p in patterns if p.confidence >= 0.9)

        return {
            "total_patterns": len(patterns),
            "by_type": dict(by_type),
            "by_status": dict(by_status),
            "high_confidence_count": high_confidence,
            "average_confidence": sum(p.confidence for p in patterns) / len(patterns),
            "total_occurrences": sum(p.occurrence_count for p in patterns),
        }

    def suggest_policy_updates(
        self,
        patterns: List[DiscoveredPattern]
    ) -> Dict[str, Any]:
        """
        Suggest policy updates based on discovered patterns

        Returns:
            Policy update recommendations
        """
        recommendations = {
            "new_injection_patterns": [],
            "false_positive_fixes": [],
            "new_pii_patterns": [],
            "priority": "low",
        }

        # High priority if many high-confidence patterns
        high_conf_count = sum(1 for p in patterns if p.confidence >= 0.9)
        if high_conf_count >= 5:
            recommendations["priority"] = "high"
        elif high_conf_count >= 2:
            recommendations["priority"] = "medium"

        # Categorize by type
        for pattern in patterns:
            if pattern.pattern_type == PatternType.INJECTION_VARIANT:
                recommendations["new_injection_patterns"].append({
                    "pattern": pattern.pattern_value,
                    "confidence": pattern.confidence,
                    "occurrences": pattern.occurrence_count,
                })

            elif pattern.pattern_type == PatternType.FALSE_POSITIVE:
                recommendations["false_positive_fixes"].append({
                    "pattern": pattern.pattern_value,
                    "occurrences": pattern.occurrence_count,
                    "suggestion": f"Consider excluding '{pattern.pattern_value}' from injection detection",
                })

            elif pattern.pattern_type == PatternType.PII_PATTERN:
                recommendations["new_pii_patterns"].append({
                    "pattern": pattern.pattern_value,
                    "confidence": pattern.confidence,
                })

        return recommendations
