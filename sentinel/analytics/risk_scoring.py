from typing import Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class OrgRiskScore:
    """Risk score for an organization"""
    org_id: str
    overall_score: float  # 0-100
    threat_score: float
    vulnerability_score: float
    compliance_score: float
    trend: str  # improving, stable, worsening
    last_calculated: datetime


class OrgRiskScorer:
    """
    Calculates risk scores at the organization level

    Combines multiple factors:
    - Threat activity (blocked attacks, anomalies)
    - Vulnerability indicators (policy gaps, false positives)
    - Compliance status (audit findings, policy coverage)
    """

    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or {
            "threat": 0.4,
            "vulnerability": 0.3,
            "compliance": 0.3,
        }

    def calculate_risk_score(
        self,
        org_id: str,
        metrics: Dict[str, Any],
        historical_data: List[Dict[str, Any]] = None,
    ) -> OrgRiskScore:
        """
        Calculate comprehensive risk score for an organization

        Args:
            org_id: Organization identifier
            metrics: Current security metrics
            historical_data: Historical metrics for trend analysis
        """
        # Calculate component scores
        threat_score = self._calculate_threat_score(metrics)
        vulnerability_score = self._calculate_vulnerability_score(metrics)
        compliance_score = self._calculate_compliance_score(metrics)

        # Weighted average
        overall = (
            threat_score * self.weights["threat"] +
            vulnerability_score * self.weights["vulnerability"] +
            compliance_score * self.weights["compliance"]
        )

        # Determine trend
        trend = "stable"
        if historical_data and len(historical_data) >= 2:
            prev_score = historical_data[-2].get("overall_score", overall)
            if overall < prev_score - 5:
                trend = "improving"
            elif overall > prev_score + 5:
                trend = "worsening"

        return OrgRiskScore(
            org_id=org_id,
            overall_score=round(overall, 1),
            threat_score=round(threat_score, 1),
            vulnerability_score=round(vulnerability_score, 1),
            compliance_score=round(compliance_score, 1),
            trend=trend,
            last_calculated=datetime.utcnow(),
        )

    def _calculate_threat_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate threat score (0-100, higher = more risk)

        Factors:
        - Blocked attack rate
        - Anomaly detection rate
        - High severity incidents
        """
        total_requests = metrics.get("total_requests", 1)
        blocked = metrics.get("blocked_requests", 0)
        anomalies = metrics.get("anomaly_count", 0)
        critical_incidents = metrics.get("critical_incidents", 0)

        # Normalize metrics
        block_rate = (blocked / max(total_requests, 1)) * 100
        anomaly_rate = (anomalies / max(total_requests, 1)) * 100

        # Weight and combine
        score = (
            min(block_rate * 10, 40) +  # Up to 40 points for blocks
            min(anomaly_rate * 20, 30) +  # Up to 30 points for anomalies
            min(critical_incidents * 10, 30)  # Up to 30 points for critical
        )

        return min(score, 100)

    def _calculate_vulnerability_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate vulnerability score (0-100, higher = more risk)

        Factors:
        - False positive rate (indicates policy gaps)
        - Unaddressed alerts
        - Policy coverage gaps
        """
        false_positives = metrics.get("false_positives", 0)
        total_alerts = metrics.get("total_alerts", 1)
        unaddressed_alerts = metrics.get("unaddressed_alerts", 0)
        policy_coverage = metrics.get("policy_coverage", 100)  # percentage

        fp_rate = (false_positives / max(total_alerts, 1)) * 100
        unaddressed_rate = (unaddressed_alerts / max(total_alerts, 1)) * 100
        coverage_gap = 100 - policy_coverage

        score = (
            min(fp_rate * 2, 30) +
            min(unaddressed_rate * 2, 40) +
            min(coverage_gap, 30)
        )

        return min(score, 100)

    def _calculate_compliance_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate compliance score (0-100, higher = more risk)

        Factors:
        - Audit findings
        - Missing required policies
        - Overdue reviews
        """
        audit_findings = metrics.get("audit_findings", 0)
        missing_policies = metrics.get("missing_required_policies", 0)
        overdue_reviews = metrics.get("overdue_policy_reviews", 0)

        score = (
            min(audit_findings * 15, 40) +
            min(missing_policies * 20, 40) +
            min(overdue_reviews * 5, 20)
        )

        return min(score, 100)