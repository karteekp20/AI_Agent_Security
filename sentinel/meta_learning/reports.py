"""
Meta-Learning: Reporting and Dashboard
Generates reports and analytics for the meta-learning system
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import json

from .schemas import (
    DiscoveredPattern,
    RuleVersion,
    ThreatIndicator,
    PatternType,
    PatternStatus,
    ThreatSeverity,
)
from .pattern_discoverer import MetaLearningAgent
from .rule_manager import RuleManager
from .threat_intelligence import ThreatIntelligence
from .approval_workflow import ApprovalWorkflow


class MetaLearningReports:
    """
    Generate reports and dashboards for meta-learning system

    Capabilities:
    1. Pattern discovery summaries
    2. Deployment health metrics
    3. Threat intelligence summaries
    4. Approval workflow status
    5. Trend analysis over time
    """

    def __init__(
        self,
        meta_agent: Optional[MetaLearningAgent] = None,
        rule_manager: Optional[RuleManager] = None,
        threat_intel: Optional[ThreatIntelligence] = None,
        approval_workflow: Optional[ApprovalWorkflow] = None
    ):
        """
        Initialize reporting system

        Args:
            meta_agent: MetaLearningAgent instance
            rule_manager: RuleManager instance
            threat_intel: ThreatIntelligence instance
            approval_workflow: ApprovalWorkflow instance
        """
        self.meta_agent = meta_agent
        self.rule_manager = rule_manager
        self.threat_intel = threat_intel
        self.approval_workflow = approval_workflow

    def generate_daily_summary(
        self,
        audit_logs: List[Dict[str, Any]],
        date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate daily summary report

        Args:
            audit_logs: Audit logs for analysis
            date: Date to generate report for (default: today)

        Returns:
            Daily summary report
        """
        date = date or datetime.utcnow()

        report = {
            "report_type": "daily_summary",
            "date": date.isoformat(),
            "generated_at": datetime.utcnow().isoformat(),
        }

        # Pattern discovery summary
        if self.meta_agent:
            discovered_patterns = self.meta_agent.analyze_audit_logs(
                audit_logs,
                time_window_hours=24
            )

            report["pattern_discovery"] = {
                "total_discovered": len(discovered_patterns),
                "by_type": Counter([p.pattern_type for p in discovered_patterns]),
                "high_confidence": sum(1 for p in discovered_patterns if p.confidence >= 0.9),
                "top_patterns": [
                    {
                        "type": p.pattern_type,
                        "value": p.pattern_value[:100],
                        "confidence": p.confidence,
                        "occurrences": p.occurrence_count,
                    }
                    for p in sorted(discovered_patterns, key=lambda x: x.confidence, reverse=True)[:5]
                ],
            }

        # Deployment status
        if self.rule_manager:
            active_rules = self.rule_manager.get_active_rules()
            version_history = self.rule_manager.get_version_history()

            report["deployment"] = {
                "current_version": active_rules.get("version"),
                "canary_version": active_rules.get("canary_version"),
                "total_pii_patterns": sum(
                    len(patterns) for patterns in active_rules.get("pii_patterns", {}).values()
                ),
                "total_injection_patterns": len(active_rules.get("injection_patterns", [])),
                "recent_deployments": len([
                    v for v in version_history
                    if (datetime.utcnow() - v.created_at).days < 7
                ]),
            }

        # Threat intelligence
        if self.threat_intel:
            threat_summary = self.threat_intel.get_threat_summary()
            report["threat_intelligence"] = threat_summary

        # Approval workflow
        if self.approval_workflow:
            workflow_summary = self.approval_workflow.get_workflow_summary()
            report["approval_workflow"] = workflow_summary

        # Security metrics from audit logs
        report["security_metrics"] = self._calculate_security_metrics(audit_logs, hours=24)

        return report

    def generate_weekly_summary(
        self,
        audit_logs: List[Dict[str, Any]],
        week_start: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate weekly summary report

        Args:
            audit_logs: Audit logs for analysis
            week_start: Start of week (default: 7 days ago)

        Returns:
            Weekly summary report
        """
        week_start = week_start or (datetime.utcnow() - timedelta(days=7))

        report = {
            "report_type": "weekly_summary",
            "week_start": week_start.isoformat(),
            "week_end": datetime.utcnow().isoformat(),
            "generated_at": datetime.utcnow().isoformat(),
        }

        # Security metrics over time
        report["security_metrics"] = self._calculate_security_metrics(audit_logs, hours=24*7)

        # Pattern discovery trends
        if self.meta_agent:
            daily_patterns = []

            for day_offset in range(7):
                day_start = week_start + timedelta(days=day_offset)
                day_end = day_start + timedelta(days=1)

                # Filter logs for this day
                day_logs = [
                    log for log in audit_logs
                    if day_start <= datetime.fromisoformat(log.get("timestamp", "")) < day_end
                ]

                if day_logs:
                    patterns = self.meta_agent.analyze_audit_logs(day_logs, time_window_hours=24)
                    daily_patterns.append({
                        "date": day_start.isoformat(),
                        "patterns_discovered": len(patterns),
                        "high_confidence": sum(1 for p in patterns if p.confidence >= 0.9),
                    })

            report["pattern_discovery_trend"] = daily_patterns

        # Deployment history
        if self.rule_manager:
            version_history = self.rule_manager.get_version_history()

            recent_deployments = [
                v for v in version_history
                if (datetime.utcnow() - v.created_at).days <= 7
            ]

            report["deployments"] = [
                {
                    "version": v.version,
                    "deployed_at": v.created_at.isoformat(),
                    "status": v.deployment_status,
                    "patterns_added": len(v.patterns_added),
                    "patterns_removed": len(v.patterns_removed),
                    "detection_rate": v.detection_rate,
                    "false_positive_rate": v.false_positive_rate,
                }
                for v in recent_deployments
            ]

        # Top threats
        if self.threat_intel:
            relevant_threats = []
            for log in audit_logs[-1000:]:  # Check recent logs
                user_input = log.get("user_input", "")
                threats = self.threat_intel.get_relevant_threats(user_input)
                relevant_threats.extend(threats)

            # Count threat occurrences
            threat_counts = Counter([t.indicator_id for t in relevant_threats])

            report["top_threats"] = [
                {
                    "indicator_id": indicator_id,
                    "occurrences": count,
                }
                for indicator_id, count in threat_counts.most_common(10)
            ]

        return report

    def generate_pattern_effectiveness_report(
        self,
        patterns: List[DiscoveredPattern],
        audit_logs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze effectiveness of deployed patterns

        Args:
            patterns: List of patterns to analyze
            audit_logs: Audit logs for effectiveness analysis

        Returns:
            Effectiveness report
        """
        report = {
            "report_type": "pattern_effectiveness",
            "generated_at": datetime.utcnow().isoformat(),
            "total_patterns": len(patterns),
        }

        # Analyze each pattern
        pattern_stats = []

        for pattern in patterns:
            # Count matches in logs
            matches = 0
            true_positives = 0
            false_positives = 0

            for log in audit_logs:
                user_input = log.get("user_input", "")

                # Check if pattern matches
                if pattern.pattern_value.lower() in user_input.lower():
                    matches += 1

                    # Check if it was a true positive (blocked correctly)
                    if log.get("blocked") and log.get("injection_detected"):
                        true_positives += 1
                    elif log.get("blocked") and not log.get("injection_detected"):
                        false_positives += 1

            # Calculate metrics
            precision = true_positives / matches if matches > 0 else 0
            fp_rate = false_positives / matches if matches > 0 else 0

            pattern_stats.append({
                "pattern_id": pattern.pattern_id,
                "pattern_type": pattern.pattern_type,
                "pattern_value": pattern.pattern_value[:100],
                "confidence": pattern.confidence,
                "matches": matches,
                "true_positives": true_positives,
                "false_positives": false_positives,
                "precision": precision,
                "false_positive_rate": fp_rate,
                "effectiveness_score": precision * (1 - fp_rate),  # Combined metric
            })

        # Sort by effectiveness
        pattern_stats.sort(key=lambda x: x["effectiveness_score"], reverse=True)

        report["patterns"] = pattern_stats

        # Summary
        report["summary"] = {
            "avg_precision": sum(p["precision"] for p in pattern_stats) / len(pattern_stats) if pattern_stats else 0,
            "avg_fp_rate": sum(p["false_positive_rate"] for p in pattern_stats) / len(pattern_stats) if pattern_stats else 0,
            "highly_effective": sum(1 for p in pattern_stats if p["effectiveness_score"] >= 0.9),
            "needs_review": sum(1 for p in pattern_stats if p["effectiveness_score"] < 0.5),
        }

        return report

    def generate_compliance_report(
        self,
        audit_logs: List[Dict[str, Any]],
        framework: str = "PCI-DSS"
    ) -> Dict[str, Any]:
        """
        Generate compliance report for regulatory frameworks

        Args:
            audit_logs: Audit logs for compliance analysis
            framework: Compliance framework (PCI-DSS, GDPR, HIPAA, SOC2)

        Returns:
            Compliance report
        """
        report = {
            "report_type": "compliance",
            "framework": framework,
            "generated_at": datetime.utcnow().isoformat(),
        }

        # General compliance metrics
        total_requests = len(audit_logs)
        pii_detections = sum(1 for log in audit_logs if log.get("pii_detected"))
        pii_redactions = sum(1 for log in audit_logs if log.get("redacted_entities"))
        blocked_requests = sum(1 for log in audit_logs if log.get("blocked"))

        report["metrics"] = {
            "total_requests": total_requests,
            "pii_detection_rate": pii_detections / total_requests if total_requests > 0 else 0,
            "pii_redaction_rate": pii_redactions / total_requests if total_requests > 0 else 0,
            "block_rate": blocked_requests / total_requests if total_requests > 0 else 0,
        }

        # Framework-specific checks
        if framework == "PCI-DSS":
            report["pci_dss"] = self._check_pci_dss_compliance(audit_logs)
        elif framework == "GDPR":
            report["gdpr"] = self._check_gdpr_compliance(audit_logs)
        elif framework == "HIPAA":
            report["hipaa"] = self._check_hipaa_compliance(audit_logs)
        elif framework == "SOC2":
            report["soc2"] = self._check_soc2_compliance(audit_logs)

        return report

    def export_dashboard_data(self) -> Dict[str, Any]:
        """
        Export data for dashboard visualization

        Returns:
            Dashboard data ready for UI rendering
        """
        dashboard = {
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Rule manager stats
        if self.rule_manager:
            active_rules = self.rule_manager.get_active_rules()
            dashboard["active_rules"] = {
                "version": active_rules.get("version"),
                "total_patterns": sum(
                    len(patterns) for patterns in active_rules.get("pii_patterns", {}).values()
                ) + len(active_rules.get("injection_patterns", [])),
            }

        # Approval workflow stats
        if self.approval_workflow:
            workflow = self.approval_workflow.get_workflow_summary()
            dashboard["pending_reviews"] = workflow.get("pending_reviews", 0)

        # Threat intelligence stats
        if self.threat_intel:
            threats = self.threat_intel.get_threat_summary()
            dashboard["threats"] = {
                "total": threats.get("total_threats", 0),
                "recent": threats.get("recent_threats", 0),
                "high_severity": threats.get("by_severity", {}).get("high", 0) +
                                threats.get("by_severity", {}).get("critical", 0),
            }

        return dashboard

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    def _calculate_security_metrics(
        self,
        audit_logs: List[Dict[str, Any]],
        hours: int = 24
    ) -> Dict[str, Any]:
        """Calculate security metrics from audit logs"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        # Filter recent logs
        recent_logs = [
            log for log in audit_logs
            if datetime.fromisoformat(log.get("timestamp", "")) > cutoff
        ]

        if not recent_logs:
            return {
                "total_requests": 0,
                "blocked_requests": 0,
                "pii_detections": 0,
                "injection_attempts": 0,
            }

        total = len(recent_logs)
        blocked = sum(1 for log in recent_logs if log.get("blocked"))
        pii_detected = sum(1 for log in recent_logs if log.get("pii_detected"))
        injections = sum(1 for log in recent_logs if log.get("injection_detected"))

        return {
            "total_requests": total,
            "blocked_requests": blocked,
            "block_rate": blocked / total,
            "pii_detections": pii_detected,
            "pii_detection_rate": pii_detected / total,
            "injection_attempts": injections,
            "injection_rate": injections / total,
        }

    def _check_pci_dss_compliance(self, audit_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check PCI-DSS compliance requirements"""
        # PCI-DSS: Must protect cardholder data
        credit_card_detections = sum(
            1 for log in audit_logs
            if "CREDIT_CARD" in str(log.get("redacted_entities", []))
        )

        return {
            "requirement_3": {
                "description": "Protect stored cardholder data",
                "status": "compliant" if credit_card_detections > 0 else "n/a",
                "detections": credit_card_detections,
            }
        }

    def _check_gdpr_compliance(self, audit_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check GDPR compliance requirements"""
        # GDPR: Must protect personal data
        pii_redactions = sum(1 for log in audit_logs if log.get("redacted_entities"))

        return {
            "article_5": {
                "description": "Data protection by design and by default",
                "status": "compliant" if pii_redactions > 0 else "n/a",
                "redactions": pii_redactions,
            }
        }

    def _check_hipaa_compliance(self, audit_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check HIPAA compliance requirements"""
        # HIPAA: Must protect PHI (Protected Health Information)
        phi_detections = sum(
            1 for log in audit_logs
            if any(entity_type in ["SSN", "PHONE", "EMAIL"]
                   for entity_type in str(log.get("redacted_entities", [])))
        )

        return {
            "privacy_rule": {
                "description": "Protect patient health information",
                "status": "compliant" if phi_detections > 0 else "n/a",
                "detections": phi_detections,
            }
        }

    def _check_soc2_compliance(self, audit_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check SOC2 compliance requirements"""
        # SOC2: Security monitoring and logging
        total_logs = len(audit_logs)
        logged_with_context = sum(
            1 for log in audit_logs
            if log.get("request_context")
        )

        return {
            "security": {
                "description": "System monitoring and logging",
                "status": "compliant" if logged_with_context / total_logs >= 0.95 else "needs_improvement",
                "logging_coverage": logged_with_context / total_logs if total_logs > 0 else 0,
            }
        }
