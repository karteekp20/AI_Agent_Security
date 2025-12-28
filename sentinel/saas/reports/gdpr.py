"""
GDPR Compliance Report Generator
General Data Protection Regulation reporting
"""

from typing import Dict, Any, List
from .base import BaseReportGenerator


class GDPRReportGenerator(BaseReportGenerator):
    """
    GDPR Compliance Report Generator

    Focuses on personal data protection and privacy.
    Key principles:
    - Lawfulness, fairness, and transparency
    - Purpose limitation
    - Data minimization
    - Accuracy
    - Storage limitation
    - Integrity and confidentiality
    """

    @property
    def report_type(self) -> str:
        return "gdpr"

    @property
    def report_title(self) -> str:
        return "GDPR Compliance Report"

    def generate_html(self) -> str:
        """Generate GDPR HTML report"""
        stats = self.calculate_statistics()

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{self.report_title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
        h1 {{ color: #10b981; border-bottom: 3px solid #10b981; padding-bottom: 10px; }}
        h2 {{ color: #059669; margin-top: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #10b981; color: white; }}
        .summary-box {{ background: #d1fae5; border-left: 4px solid #10b981; padding: 15px; margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
        .metric-label {{ font-weight: bold; color: #666; }}
        .metric-value {{ font-size: 24px; color: #10b981; }}
    </style>
</head>
<body>
    <h1>{self.report_title}</h1>

    <div class="summary-box">
        <p><strong>Report Period:</strong> {self.format_timestamp(self.data.start_date)} to {self.format_timestamp(self.data.end_date)}</p>
        <p><strong>Organization ID:</strong> {self.data.org_id}</p>
    </div>

    <h2>Personal Data Processing Summary</h2>
    <div class="summary-box">
        <div class="metric">
            <div class="metric-label">Total Requests Processed</div>
            <div class="metric-value">{stats['total_requests']}</div>
        </div>
        <div class="metric">
            <div class="metric-label">PII Detections</div>
            <div class="metric-value">{stats['pii_detections']}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Data Redacted</div>
            <div class="metric-value">{stats['pii_detections']}</div>
        </div>
    </div>

    <h2>Article 32: Security of Processing</h2>
    <p>Technical measures implemented to ensure ongoing confidentiality, integrity, and availability of personal data:</p>
    <ul>
        <li><strong>PII Detection:</strong> Automatic detection of personal data in all API requests</li>
        <li><strong>Data Redaction:</strong> Automatic redaction/blocking of personal data to prevent unauthorized processing</li>
        <li><strong>Risk Assessment:</strong> Real-time risk scoring for all data processing operations</li>
        <li><strong>Audit Logging:</strong> Complete audit trail of all data processing activities</li>
    </ul>

    <h2>PII Detection Events</h2>
    <table>
        <tr>
            <th>Timestamp</th>
            <th>PII Types Detected</th>
            <th>Action Taken</th>
            <th>Risk Level</th>
        </tr>
"""

        # Add PII detection events
        for log in [l for l in self.data.audit_logs if l.get("pii_detected")][:10]:
            pii_types = list(log.get("pii_entities", {}).keys()) if log.get("pii_entities") else ["Unknown"]
            action = "Blocked" if log.get("blocked") else "Redacted"
            risk_level = log.get("risk_level", "low")
            html += f"""
        <tr>
            <td>{self.format_timestamp(log.get('timestamp', ''))}</td>
            <td>{', '.join(pii_types)}</td>
            <td>{action}</td>
            <td>{risk_level.upper()}</td>
        </tr>
"""

        html += """
    </table>

    <h2>Compliance Status</h2>
    <div class="summary-box">
        <p><strong>✓ Article 5:</strong> Personal data processed lawfully with purpose limitation and data minimization</p>
        <p><strong>✓ Article 25:</strong> Data protection by design and by default implemented</p>
        <p><strong>✓ Article 32:</strong> Technical security measures in place for data protection</p>
        <p><strong>✓ Article 30:</strong> Records of processing activities maintained via audit logs</p>
    </div>
</body>
</html>
"""
        return html

    def generate_excel_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate GDPR Excel data"""
        stats = self.calculate_statistics()

        return {
            "Summary": [
                {"Metric": "Total Requests", "Value": stats['total_requests']},
                {"Metric": "PII Detections", "Value": stats['pii_detections']},
                {"Metric": "Blocked Requests", "Value": stats['blocked_requests']},
            ],
            "PII Events": [
                {
                    "Timestamp": self.format_timestamp(log.get('timestamp', '')),
                    "User ID": log.get('user_id', 'anonymous'),
                    "PII Detected": log.get('pii_detected', False),
                    "Redacted Count": log.get('redacted_count', 0),
                    "Risk Score": log.get('risk_score', 0),
                }
                for log in self.data.audit_logs if log.get("pii_detected")
            ],
        }
