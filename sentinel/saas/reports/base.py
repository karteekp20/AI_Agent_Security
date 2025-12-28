"""
Base Report Generator
Abstract base class for all compliance report generators
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ReportData:
    """Container for report generation data"""
    org_id: str
    workspace_id: Optional[str]
    start_date: datetime
    end_date: datetime
    audit_logs: List[Dict[str, Any]]
    statistics: Dict[str, Any]
    metadata: Dict[str, Any]


class BaseReportGenerator(ABC):
    """
    Abstract base class for compliance report generators

    Each compliance framework (PCI-DSS, GDPR, HIPAA, SOC2) extends this class.
    """

    def __init__(self, report_data: ReportData):
        self.data = report_data

    @property
    @abstractmethod
    def report_type(self) -> str:
        """Return report type identifier (e.g., 'pci_dss', 'gdpr')"""
        pass

    @property
    @abstractmethod
    def report_title(self) -> str:
        """Return human-readable report title"""
        pass

    @abstractmethod
    def generate_html(self) -> str:
        """
        Generate HTML report content

        Returns:
            HTML string ready for PDF conversion or display
        """
        pass

    @abstractmethod
    def generate_excel_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate Excel report data

        Returns:
            Dictionary mapping sheet names to lists of row dictionaries
            Example: {
                "Summary": [{"metric": "Total Requests", "value": 1000}],
                "Audit Logs": [{"timestamp": "...", "user_input": "..."}]
            }
        """
        pass

    def generate_json(self) -> Dict[str, Any]:
        """
        Generate JSON report data

        Returns:
            Dictionary containing all report data in JSON-serializable format
        """
        return {
            "report_type": self.report_type,
            "title": self.report_title,
            "generated_at": datetime.utcnow().isoformat(),
            "period": {
                "start": self.data.start_date.isoformat(),
                "end": self.data.end_date.isoformat(),
            },
            "organization_id": self.data.org_id,
            "workspace_id": self.data.workspace_id,
            "statistics": self.data.statistics,
            "audit_logs": self.data.audit_logs,
            "metadata": self.data.metadata,
        }

    def calculate_statistics(self) -> Dict[str, Any]:
        """
        Calculate basic statistics from audit logs

        Returns:
            Dictionary of calculated metrics
        """
        logs = self.data.audit_logs

        total_requests = len(logs)
        blocked_requests = sum(1 for log in logs if log.get("blocked"))
        pii_detections = sum(1 for log in logs if log.get("pii_detected"))
        injection_detections = sum(1 for log in logs if log.get("injection_detected"))

        # Calculate risk scores
        risk_scores = [log.get("risk_score", 0) for log in logs if log.get("risk_score") is not None]
        avg_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0

        # High risk threshold
        high_risk_count = sum(1 for score in risk_scores if score >= 0.7)

        return {
            "total_requests": total_requests,
            "blocked_requests": blocked_requests,
            "allowed_requests": total_requests - blocked_requests,
            "block_rate": (blocked_requests / total_requests * 100) if total_requests > 0 else 0,
            "pii_detections": pii_detections,
            "injection_detections": injection_detections,
            "average_risk_score": avg_risk_score,
            "high_risk_requests": high_risk_count,
        }

    def format_timestamp(self, timestamp: Any) -> str:
        """Format timestamp for display"""
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

    def render_html_template(self, template_content: str, context: Dict[str, Any]) -> str:
        """
        Simple template rendering (placeholder replacement)

        For production, use Jinja2. This is a minimal implementation.
        """
        result = template_content
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        return result
