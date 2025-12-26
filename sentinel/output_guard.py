"""
Output Guard Agent: Final line of defense
- Scans agent responses for data leaks
- Prevents accidental PII/PCI/PHI disclosure
- Validates responses against security policies
"""

import hashlib
from typing import List, Dict, Any
from datetime import datetime

from .schemas import (
    SentinelState,
    RedactedEntity,
    EntityType,
    SecurityThreat,
    ThreatLevel,
    PIIDetectionConfig,
    AuditEvent,
    EventType,
    RiskScore,  # Phase 1 addition
    RiskLevel,  # Phase 1 addition
)
from .input_guard import PIIDetector


# ============================================================================
# DATA LEAK DETECTION
# ============================================================================

class DataLeakDetector:
    """Detects potential data leaks in agent responses"""

    def __init__(self):
        self.leak_patterns = self._compile_leak_patterns()

    def _compile_leak_patterns(self) -> List[Dict[str, Any]]:
        """Define patterns that indicate data leaks"""
        return [
            {
                "name": "system_prompt_leak",
                "indicators": [
                    "my instructions are",
                    "i was told to",
                    "my system prompt",
                    "according to my instructions",
                ],
                "severity": ThreatLevel.HIGH,
            },
            {
                "name": "internal_data_leak",
                "indicators": [
                    "internal database",
                    "production credentials",
                    "api endpoint",
                    "secret key",
                ],
                "severity": ThreatLevel.CRITICAL,
            },
            {
                "name": "user_data_leak",
                "indicators": [
                    "other user",
                    "previous conversation",
                    "another customer",
                ],
                "severity": ThreatLevel.HIGH,
            },
            {
                "name": "debugging_info_leak",
                "indicators": [
                    "stack trace:",
                    "error:",
                    "exception:",
                    "debug:",
                ],
                "severity": ThreatLevel.MEDIUM,
            },
        ]

    def detect_leaks(self, response: str) -> List[SecurityThreat]:
        """Detect potential data leaks in response"""
        threats = []
        response_lower = response.lower()

        for pattern in self.leak_patterns:
            for indicator in pattern["indicators"]:
                if indicator in response_lower:
                    threat = SecurityThreat(
                        threat_type="data_leak",
                        severity=pattern["severity"],
                        description=f"Potential {pattern['name']}: found '{indicator}'",
                        detection_method="output_guard",
                        confidence=0.85,
                        evidence={
                            "pattern": pattern["name"],
                            "indicator": indicator,
                            "context": self._extract_context(response, indicator),
                        },
                        blocked=False,
                    )
                    threats.append(threat)

        return threats

    def _extract_context(self, text: str, keyword: str, context_size: int = 100) -> str:
        """Extract context around a keyword"""
        text_lower = text.lower()
        pos = text_lower.find(keyword.lower())

        if pos == -1:
            return ""

        start = max(0, pos - context_size)
        end = min(len(text), pos + len(keyword) + context_size)

        return text[start:end]


# ============================================================================
# RESPONSE VALIDATION
# ============================================================================

class ResponseValidator:
    """Validates agent responses against security policies"""

    def __init__(self):
        pass

    def validate(self, response: str, state: SentinelState) -> List[SecurityThreat]:
        """Validate response against security policies"""
        threats = []

        # Check 1: Response doesn't leak original (unredacted) PII
        threats.extend(self._check_pii_leakage(response, state))

        # Check 2: Response doesn't contain malicious content
        threats.extend(self._check_malicious_content(response))

        # Check 3: Response length is reasonable
        if len(response) > 50000:
            threat = SecurityThreat(
                threat_type="excessive_response",
                severity=ThreatLevel.MEDIUM,
                description=f"Response too long: {len(response)} characters",
                detection_method="output_guard",
                confidence=1.0,
                evidence={"length": len(response)},
                blocked=False,
            )
            threats.append(threat)

        return threats

    def _check_pii_leakage(self, response: str, state: SentinelState) -> List[SecurityThreat]:
        """Check if response leaks original PII that was redacted"""
        threats = []

        for entity_dict in state["original_entities"]:
            original_value = entity_dict.get("original_value")
            if original_value and original_value in response:
                threat = SecurityThreat(
                    threat_type="pii_leakage",
                    severity=ThreatLevel.CRITICAL,
                    description=f"Response contains original {entity_dict['entity_type']} that was redacted",
                    detection_method="output_guard",
                    confidence=1.0,
                    evidence={
                        "entity_type": entity_dict["entity_type"],
                        "token_id": entity_dict["token_id"],
                    },
                    blocked=True,
                )
                threats.append(threat)

        return threats

    def _check_malicious_content(self, response: str) -> List[SecurityThreat]:
        """Check for malicious content in response"""
        threats = []
        response_lower = response.lower()

        # Check for SQL injection attempts
        sql_keywords = ["drop table", "delete from", "insert into", "update set"]
        for keyword in sql_keywords:
            if keyword in response_lower:
                threat = SecurityThreat(
                    threat_type="malicious_content",
                    severity=ThreatLevel.HIGH,
                    description=f"Response contains SQL keyword: {keyword}",
                    detection_method="output_guard",
                    confidence=0.7,
                    evidence={"keyword": keyword},
                    blocked=False,
                )
                threats.append(threat)

        # Check for script injection
        script_patterns = ["<script", "javascript:", "onerror=", "onclick="]
        for pattern in script_patterns:
            if pattern in response_lower:
                threat = SecurityThreat(
                    threat_type="xss_attempt",
                    severity=ThreatLevel.HIGH,
                    description=f"Response contains script pattern: {pattern}",
                    detection_method="output_guard",
                    confidence=0.8,
                    evidence={"pattern": pattern},
                    blocked=False,
                )
                threats.append(threat)

        return threats


# ============================================================================
# RESPONSE SANITIZER
# ============================================================================

class ResponseSanitizer:
    """Sanitizes agent responses before returning to user"""

    def __init__(self, pii_detector: PIIDetector):
        self.pii_detector = pii_detector

    def sanitize(self, response: str, original_entities: List[Dict[str, Any]]) -> tuple[str, List[RedactedEntity]]:
        """
        Sanitize response by:
        1. Detecting new PII that might have leaked
        2. Removing malicious content
        3. Ensuring original redacted entities stay redacted
        """

        # Detect any new PII in the response
        new_entities = self.pii_detector.detect_pii(response)

        # Combine with original entities (in case they leaked through)
        all_entities = new_entities + [
            RedactedEntity(**e) for e in original_entities
        ]

        # Redact all entities
        sanitized = self.pii_detector.redact_text(response, all_entities)

        # Remove potentially malicious HTML/script tags
        sanitized = self._remove_scripts(sanitized)

        return sanitized, new_entities

    def _remove_scripts(self, text: str) -> str:
        """Remove script tags and event handlers"""
        import re

        # Remove script tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)

        # Remove event handlers
        text = re.sub(r'\son\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)

        return text


# ============================================================================
# OUTPUT GUARD AGENT
# ============================================================================

class OutputGuardAgent:
    """
    Output Guard Agent: Final security check
    Scans agent response before returning to user
    """

    def __init__(self, pii_config: PIIDetectionConfig):
        self.pii_detector = PIIDetector(pii_config)
        self.leak_detector = DataLeakDetector()
        self.validator = ResponseValidator()
        self.sanitizer = ResponseSanitizer(self.pii_detector)

    def calculate_risk_score(
        self,
        leak_threats: List[SecurityThreat],
        validation_threats: List[SecurityThreat],
        new_entities: List[RedactedEntity]
    ) -> RiskScore:
        """
        Calculate risk score for output guard layer (Phase 1)

        Risk factors:
        - Data leak severity
        - Validation threat severity
        - New PII discovered in output
        """
        risk_factors = {}

        # 1. Leak Risk (0.0-1.0)
        leak_risk = 0.0
        if leak_threats:
            # Calculate severity-weighted risk
            severity_weights = {
                ThreatLevel.NONE: 0.0,
                ThreatLevel.LOW: 0.2,
                ThreatLevel.MEDIUM: 0.5,
                ThreatLevel.HIGH: 0.8,
                ThreatLevel.CRITICAL: 1.0,
            }

            total_severity = sum(severity_weights.get(t.severity, 0.5) for t in leak_threats)
            leak_risk = min(total_severity / len(leak_threats), 1.0)

        risk_factors["leak_risk"] = leak_risk

        # 2. Validation Risk (0.0-1.0)
        validation_risk = 0.0
        if validation_threats:
            severity_weights = {
                ThreatLevel.NONE: 0.0,
                ThreatLevel.LOW: 0.2,
                ThreatLevel.MEDIUM: 0.5,
                ThreatLevel.HIGH: 0.8,
                ThreatLevel.CRITICAL: 1.0,
            }

            total_severity = sum(severity_weights.get(t.severity, 0.5) for t in validation_threats)
            validation_risk = min(total_severity / len(validation_threats), 1.0)

        risk_factors["validation_risk"] = validation_risk

        # 3. New PII Risk (0.0-1.0)
        new_pii_risk = 0.0
        if new_entities:
            # Risk increases with entity count
            new_pii_risk = min(len(new_entities) / 3.0, 1.0)  # 3+ entities = max risk

        risk_factors["new_pii_risk"] = new_pii_risk

        # 4. Combined Risk (weighted average)
        # Weight: 50% leaks, 30% validation, 20% new PII
        combined_risk = (leak_risk * 0.5) + (validation_risk * 0.3) + (new_pii_risk * 0.2)

        # 5. Determine risk level
        if combined_risk >= 0.95:
            risk_level = RiskLevel.CRITICAL
        elif combined_risk >= 0.8:
            risk_level = RiskLevel.HIGH
        elif combined_risk >= 0.5:
            risk_level = RiskLevel.MEDIUM
        elif combined_risk >= 0.2:
            risk_level = RiskLevel.LOW
        else:
            risk_level = RiskLevel.NONE

        # 6. Build explanation
        explanation_parts = []
        if leak_risk > 0:
            explanation_parts.append(f"Data leak threats ({len(leak_threats)}, risk={leak_risk:.2f})")
        if validation_risk > 0:
            explanation_parts.append(f"Validation threats ({len(validation_threats)}, risk={validation_risk:.2f})")
        if new_pii_risk > 0:
            explanation_parts.append(f"New PII in output ({len(new_entities)}, risk={new_pii_risk:.2f})")

        explanation = "; ".join(explanation_parts) if explanation_parts else "No significant risks detected"

        return RiskScore(
            layer="output_guard",
            risk_score=combined_risk,
            risk_level=risk_level,
            risk_factors=risk_factors,
            explanation=explanation,
        )

    def process(self, state: SentinelState) -> SentinelState:
        """
        Process agent response through output guard
        Returns updated state
        """
        agent_response = state["agent_response"]

        # 1. Detect potential data leaks
        leak_threats = self.leak_detector.detect_leaks(agent_response)
        state["security_threats"].extend([t.dict() for t in leak_threats])

        # 2. Validate response
        validation_threats = self.validator.validate(agent_response, state)
        state["security_threats"].extend([t.dict() for t in validation_threats])

        # 3. Sanitize response
        sanitized_response, new_entities = self.sanitizer.sanitize(
            agent_response, state["original_entities"]
        )

        state["sanitized_response"] = sanitized_response

        # 4. Check for critical threats that should block the response
        critical_threats = [
            t for t in leak_threats + validation_threats
            if t.severity == ThreatLevel.CRITICAL or t.blocked
        ]

        if critical_threats:
            state["should_block"] = True
            state["block_reason"] = f"Critical security threat in response: {critical_threats[0].description}"

            # Override response with error message
            state["sanitized_response"] = (
                "I apologize, but I cannot provide that response due to security concerns. "
                "Please rephrase your request."
            )

        # 5. Add new PII detections to audit
        if new_entities:
            state["audit_log"]["pii_redactions"] += len(new_entities)

        # 6. Calculate risk score (Phase 1 enhancement)
        risk_score = self.calculate_risk_score(leak_threats, validation_threats, new_entities)
        state["risk_scores"].append(risk_score.dict())

        # 7. Add audit events
        event = AuditEvent(
            event_type=EventType.OUTPUT_SANITIZATION,
            data={
                "leak_threats_found": len(leak_threats),
                "validation_threats_found": len(validation_threats),
                "new_pii_entities_found": len(new_entities),
                "critical_threats": len(critical_threats),
                "response_blocked": state["should_block"],
            },
            response_hash=hashlib.sha256(agent_response.encode()).hexdigest(),
        )

        state["audit_log"]["events"].append(event.dict())

        # Add risk assessment audit event
        risk_event = AuditEvent(
            event_type=EventType.RISK_ASSESSMENT,
            data={
                "layer": "output_guard",
                "risk_score": risk_score.risk_score,
                "risk_level": risk_score.risk_level,
                "risk_factors": risk_score.risk_factors,
                "explanation": risk_score.explanation,
            },
        )
        state["audit_log"]["events"].append(risk_event.dict())

        return state


# Export
__all__ = [
    'DataLeakDetector',
    'ResponseValidator',
    'ResponseSanitizer',
    'OutputGuardAgent',
]
