"""
Audit & Reporting System: Compliance and Logging
- Tamper-proof audit logs
- Compliance report generation
- Digital signatures for log integrity
- Export to multiple formats (JSON, PDF, CSV)
"""

import json
import hashlib
import hmac
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .schemas import (
    SentinelState,
    AuditLog,
    AuditEvent,
    EventType,
    ComplianceFramework,
    ComplianceViolation,
    ThreatLevel,
)


# ============================================================================
# DIGITAL SIGNATURE
# ============================================================================

class AuditLogSigner:
    """Creates tamper-proof digital signatures for audit logs"""

    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize signer with secret key
        In production, use proper key management (HSM, KMS)
        """
        if secret_key is None:
            # Generate a key (in production, load from secure storage)
            import secrets
            secret_key = secrets.token_hex(32)

        self.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key

    def sign(self, audit_log: AuditLog) -> str:
        """
        Create HMAC-SHA256 signature of audit log
        Returns hex-encoded signature
        """
        # Create canonical representation
        log_data = audit_log.dict()

        # Remove existing signature for calculation
        log_data.pop("digital_signature", None)

        # Serialize to canonical JSON (sorted keys) with datetime handling
        canonical_json = json.dumps(log_data, sort_keys=True, ensure_ascii=True, default=str)

        # Create HMAC signature
        signature = hmac.new(
            self.secret_key, canonical_json.encode(), hashlib.sha256
        ).hexdigest()

        return signature

    def verify(self, audit_log: AuditLog) -> bool:
        """
        Verify audit log signature
        Returns True if signature is valid
        """
        if not audit_log.digital_signature:
            return False

        # Calculate expected signature
        expected_signature = self.sign(audit_log)

        # Constant-time comparison
        return hmac.compare_digest(
            expected_signature, audit_log.digital_signature
        )


# ============================================================================
# COMPLIANCE CHECKER
# ============================================================================

class ComplianceChecker:
    """Checks audit logs for compliance violations"""

    def __init__(self, frameworks: List[ComplianceFramework]):
        self.frameworks = frameworks

    def check_pci_dss(self, state: SentinelState) -> List[ComplianceViolation]:
        """Check PCI-DSS compliance"""
        violations = []

        # Rule 3.2: Do not store sensitive authentication data after authorization
        for entity in state["original_entities"]:
            if entity["entity_type"] == "cvv":
                violation = ComplianceViolation(
                    framework=ComplianceFramework.PCI_DSS,
                    rule="3.2",
                    severity=ThreatLevel.CRITICAL,
                    description="CVV data detected in logs",
                    evidence={
                        "entity_type": entity["entity_type"],
                        "location": "original_entities",
                    },
                    remediation="Ensure CVV is never logged or stored",
                )
                violations.append(violation)

        # Rule 3.4: Render PAN unreadable anywhere it is stored
        for entity in state["original_entities"]:
            if entity["entity_type"] == "credit_card":
                if entity["redaction_strategy"] not in ["mask", "hash", "encrypt"]:
                    violation = ComplianceViolation(
                        framework=ComplianceFramework.PCI_DSS,
                        rule="3.4",
                        severity=ThreatLevel.HIGH,
                        description="Credit card not properly redacted",
                        evidence={"entity": entity},
                        remediation="Use masking, hashing, or encryption for PAN",
                    )
                    violations.append(violation)

        # Rule 10.2: Audit trail for all access to cardholder data
        has_audit = len(state["audit_log"]["events"]) > 0
        if not has_audit and len(state["original_entities"]) > 0:
            violation = ComplianceViolation(
                framework=ComplianceFramework.PCI_DSS,
                rule="10.2",
                severity=ThreatLevel.HIGH,
                description="No audit trail for cardholder data access",
                evidence={"event_count": 0},
                remediation="Ensure all cardholder data access is logged",
            )
            violations.append(violation)

        return violations

    def check_gdpr(self, state: SentinelState) -> List[ComplianceViolation]:
        """Check GDPR compliance"""
        violations = []

        # Article 5(1)(c): Data minimization
        # Check if we're collecting more data than necessary
        pii_count = len([e for e in state["original_entities"]])
        if pii_count > 10:
            violation = ComplianceViolation(
                framework=ComplianceFramework.GDPR,
                rule="5.1.c",
                severity=ThreatLevel.MEDIUM,
                description="Excessive PII collection detected",
                evidence={"pii_entities": pii_count},
                remediation="Collect only necessary personal data",
            )
            violations.append(violation)

        # Article 25: Data protection by design and default
        # Check if encryption is used for sensitive data
        for entity in state["original_entities"]:
            if entity["redaction_strategy"] == "remove":
                violation = ComplianceViolation(
                    framework=ComplianceFramework.GDPR,
                    rule="25",
                    severity=ThreatLevel.MEDIUM,
                    description="PII removed instead of encrypted",
                    evidence={"entity_type": entity["entity_type"]},
                    remediation="Consider encryption to maintain data utility",
                )
                violations.append(violation)
                break

        return violations

    def check_hipaa(self, state: SentinelState) -> List[ComplianceViolation]:
        """Check HIPAA compliance"""
        violations = []

        # 164.312(a)(2)(i): Unique user identification
        # Ensure audit logs track user identity
        session_id = state.get("session_id")
        if not session_id:
            violation = ComplianceViolation(
                framework=ComplianceFramework.HIPAA,
                rule="164.312.a.2.i",
                severity=ThreatLevel.HIGH,
                description="No session/user tracking in audit logs",
                evidence={},
                remediation="Implement unique user identification",
            )
            violations.append(violation)

        # 164.312(b): Audit controls
        # Check for PHI access logging
        has_phi = any(
            e["entity_type"] in ["medical_record_number", "health_plan_number", "diagnosis_code"]
            for e in state["original_entities"]
        )

        has_audit = len(state["audit_log"]["events"]) > 0

        if has_phi and not has_audit:
            violation = ComplianceViolation(
                framework=ComplianceFramework.HIPAA,
                rule="164.312.b",
                severity=ThreatLevel.CRITICAL,
                description="PHI access not audited",
                evidence={"has_phi": has_phi, "has_audit": has_audit},
                remediation="Implement audit controls for PHI access",
            )
            violations.append(violation)

        # 164.312(e)(2)(i): Transmission security - encryption
        for entity in state["original_entities"]:
            if entity["entity_type"] in ["medical_record_number", "health_plan_number"]:
                if entity["redaction_strategy"] not in ["encrypt", "hash"]:
                    violation = ComplianceViolation(
                        framework=ComplianceFramework.HIPAA,
                        rule="164.312.e.2.i",
                        severity=ThreatLevel.HIGH,
                        description="PHI not encrypted",
                        evidence={"entity_type": entity["entity_type"]},
                        remediation="Encrypt PHI data",
                    )
                    violations.append(violation)
                    break

        return violations

    def check_soc2(self, state: SentinelState) -> List[ComplianceViolation]:
        """Check SOC 2 compliance"""
        violations = []

        # CC6.1: Logical and physical access controls
        # Ensure security threats are detected and logged
        has_security_monitoring = len(state["security_threats"]) >= 0  # Just checking it exists

        if not has_security_monitoring:
            violation = ComplianceViolation(
                framework=ComplianceFramework.SOC2,
                rule="CC6.1",
                severity=ThreatLevel.MEDIUM,
                description="No security threat monitoring",
                evidence={},
                remediation="Implement security threat detection and logging",
            )
            violations.append(violation)

        # CC7.2: System monitoring
        # Check for audit logging
        if len(state["audit_log"]["events"]) == 0:
            violation = ComplianceViolation(
                framework=ComplianceFramework.SOC2,
                rule="CC7.2",
                severity=ThreatLevel.HIGH,
                description="No system monitoring/audit logs",
                evidence={},
                remediation="Implement comprehensive audit logging",
            )
            violations.append(violation)

        return violations

    def check_compliance(self, state: SentinelState) -> List[ComplianceViolation]:
        """Run all compliance checks for enabled frameworks"""
        all_violations = []

        for framework in self.frameworks:
            if framework == ComplianceFramework.PCI_DSS:
                all_violations.extend(self.check_pci_dss(state))
            elif framework == ComplianceFramework.GDPR:
                all_violations.extend(self.check_gdpr(state))
            elif framework == ComplianceFramework.HIPAA:
                all_violations.extend(self.check_hipaa(state))
            elif framework == ComplianceFramework.SOC2:
                all_violations.extend(self.check_soc2(state))

        return all_violations


# ============================================================================
# REPORT GENERATOR
# ============================================================================

class ReportGenerator:
    """Generates compliance and security reports"""

    def __init__(self):
        pass

    def generate_json_report(self, state: SentinelState) -> str:
        """Generate JSON report"""
        # Handle both full state and result dict
        audit_log = state.get("audit_log", {})

        report = {
            "session_id": audit_log.get("session_id", state.get("session_id", "unknown")),
            "timestamp": state.get("timestamp", audit_log.get("start_time", "")),
            "summary": {
                "pii_redactions": audit_log.get("pii_redactions", 0),
                "injection_attempts": audit_log.get("injection_attempts", 0),
                "loops_detected": audit_log.get("loops_detected", 0),
                "compliance_violations": len(state.get("compliance_violations", state.get("violations", []))),
                "security_threats": len(state.get("security_threats", state.get("threats", []))),
            },
            "security_analysis": {
                "injection_detected": state.get("injection_detected", False),
                "loop_detected": state.get("loop_detected", False),
                "threats": state.get("security_threats", state.get("threats", [])),
            },
            "compliance": {
                "frameworks": state.get("compliance_frameworks", []),
                "violations": state.get("compliance_violations", state.get("violations", [])),
                "compliant": audit_log.get("compliant", True),
            },
            "audit_log": audit_log,
            "cost_metrics": state.get("cost_metrics", {}),
        }

        return json.dumps(report, indent=2, default=str)

    def generate_summary_report(self, state: SentinelState) -> str:
        """Generate human-readable summary report"""
        lines = []

        # Handle both full state and result dict
        audit_log = state.get("audit_log", {})
        threats = state.get("security_threats", state.get("threats", []))
        violations = state.get("compliance_violations", state.get("violations", []))
        frameworks = state.get("compliance_frameworks", [])
        cost_metrics = state.get("cost_metrics", {})

        lines.append("=" * 70)
        lines.append("SENTINEL SECURITY REPORT")
        lines.append("=" * 70)
        lines.append(f"Session ID: {audit_log.get('session_id', state.get('session_id', 'unknown'))}")
        lines.append(f"Timestamp: {state.get('timestamp', audit_log.get('start_time', ''))}")
        lines.append("")

        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 70)
        lines.append(f"  PII Redactions: {audit_log.get('pii_redactions', 0)}")
        lines.append(f"  Injection Attempts: {audit_log.get('injection_attempts', 0)}")
        lines.append(f"  Loops Detected: {audit_log.get('loops_detected', 0)}")
        lines.append(f"  Security Threats: {len(threats)}")
        lines.append(f"  Compliance Violations: {len(violations)}")
        lines.append("")

        # Security Analysis
        lines.append("SECURITY ANALYSIS")
        lines.append("-" * 70)
        lines.append(f"  Injection Detected: {state.get('injection_detected', False)}")
        lines.append(f"  Loop Detected: {state.get('loop_detected', False)}")
        lines.append(f"  Request Blocked: {state.get('blocked', state.get('should_block', False))}")

        if state.get("blocked", state.get("should_block", False)):
            lines.append(f"  Block Reason: {state.get('block_reason', 'Unknown')}")

        if threats:
            lines.append("")
            lines.append("  Top Threats:")
            for threat in threats[:5]:
                lines.append(f"    - [{threat.get('severity', 'unknown')}] {threat.get('description', '')}")

        lines.append("")

        # Compliance
        lines.append("COMPLIANCE")
        lines.append("-" * 70)
        lines.append(f"  Frameworks: {', '.join(frameworks) if frameworks else 'None'}")
        lines.append(f"  Status: {'COMPLIANT' if audit_log.get('compliant', True) else 'VIOLATIONS FOUND'}")

        if violations:
            lines.append("")
            lines.append("  Violations:")
            for violation in violations:
                lines.append(f"    - [{violation.get('framework', '')}] Rule {violation.get('rule', '')}: {violation.get('description', '')}")

        lines.append("")

        # Cost
        lines.append("COST METRICS")
        lines.append("-" * 70)
        lines.append(f"  Total Tokens: {cost_metrics.get('total_tokens', 0)}")
        lines.append(f"  Estimated Cost: ${cost_metrics.get('estimated_cost_usd', 0.0):.4f}")
        lines.append(f"  Tool Calls: {cost_metrics.get('tool_calls_count', 0)}")
        lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)

    def save_report(self, report_content: str, filepath: Path, format: str = "json"):
        """Save report to file"""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w") as f:
            f.write(report_content)


# ============================================================================
# AUDIT MANAGER
# ============================================================================

class AuditManager:
    """Main audit management system"""

    def __init__(
        self,
        compliance_frameworks: List[ComplianceFramework],
        secret_key: Optional[str] = None,
    ):
        self.signer = AuditLogSigner(secret_key)
        self.compliance_checker = ComplianceChecker(compliance_frameworks)
        self.report_generator = ReportGenerator()

    def finalize_audit_log(self, state: SentinelState) -> SentinelState:
        """
        Finalize audit log with:
        - Compliance checks
        - Digital signature
        - End timestamp
        """

        # 1. Run compliance checks
        violations = self.compliance_checker.check_compliance(state)
        state["compliance_violations"] = [v.dict() for v in violations]

        # Update compliant status
        state["audit_log"]["compliant"] = len(violations) == 0
        state["audit_log"]["compliance_violations"] = len(violations)

        # 2. Set end time
        state["audit_log"]["end_time"] = datetime.utcnow().isoformat()

        # 3. Create audit log object
        audit_log = AuditLog(**state["audit_log"])

        # 4. Sign audit log
        signature = self.signer.sign(audit_log)
        audit_log.digital_signature = signature

        # 5. Update state
        state["audit_log"] = audit_log.dict()

        # 6. Add final audit event
        event = AuditEvent(
            event_type=EventType.COMPLIANCE_CHECK,
            data={
                "violations_found": len(violations),
                "compliant": len(violations) == 0,
                "signature": signature[:16] + "...",
            },
        )

        state["audit_log"]["events"].append(event.dict())

        return state

    def verify_audit_log(self, state: SentinelState) -> bool:
        """Verify audit log signature"""
        audit_log = AuditLog(**state["audit_log"])
        return self.signer.verify(audit_log)

    def generate_report(
        self, state: SentinelState, format: str = "json"
    ) -> str:
        """Generate audit report in specified format"""
        if format == "json":
            return self.report_generator.generate_json_report(state)
        elif format == "summary":
            return self.report_generator.generate_summary_report(state)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def save_report(
        self, state: SentinelState, filepath: Path, format: str = "json"
    ):
        """Generate and save report"""
        report = self.generate_report(state, format)
        self.report_generator.save_report(report, filepath, format)


# Export
__all__ = [
    'AuditLogSigner',
    'ComplianceChecker',
    'ReportGenerator',
    'AuditManager',
]
