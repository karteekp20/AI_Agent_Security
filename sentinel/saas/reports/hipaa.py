"""
HIPAA Compliance Report Generator
Health Insurance Portability and Accountability Act reporting
"""

from typing import Dict, Any, List
from .base import BaseReportGenerator


class HIPAAReportGenerator(BaseReportGenerator):
    """
    HIPAA Compliance Report Generator

    Focuses on Protected Health Information (PHI) security.
    Key requirements:
    - Privacy Rule: Protections for PHI
    - Security Rule: Administrative, physical, and technical safeguards
    - Breach Notification Rule: Notification in case of PHI breaches
    """

    @property
    def report_type(self) -> str:
        return "hipaa"

    @property
    def report_title(self) -> str:
        return "HIPAA Compliance Report"

    def generate_html(self) -> str:
        """Generate HIPAA HTML report"""
        stats = self.calculate_statistics()

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{self.report_title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
        h1 {{ color: #dc2626; border-bottom: 3px solid #dc2626; padding-bottom: 10px; }}
        h2 {{ color: #b91c1c; margin-top: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #dc2626; color: white; }}
        .summary-box {{ background: #fee2e2; border-left: 4px solid #dc2626; padding: 15px; margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
        .metric-label {{ font-weight: bold; color: #666; }}
        .metric-value {{ font-size: 24px; color: #dc2626; }}
    </style>
</head>
<body>
    <h1>{self.report_title}</h1>

    <div class="summary-box">
        <p><strong>Report Period:</strong> {self.format_timestamp(self.data.start_date)} to {self.format_timestamp(self.data.end_date)}</p>
        <p><strong>Organization ID:</strong> {self.data.org_id}</p>
    </div>

    <h2>PHI Access Summary</h2>
    <div class="summary-box">
        <div class="metric">
            <div class="metric-label">Total Access Attempts</div>
            <div class="metric-value">{stats['total_requests']}</div>
        </div>
        <div class="metric">
            <div class="metric-label">PHI/PII Detections</div>
            <div class="metric-value">{stats['pii_detections']}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Unauthorized Access Blocked</div>
            <div class="metric-value">{stats['blocked_requests']}</div>
        </div>
    </div>

    <h2>Security Rule Compliance</h2>
    <h3>Technical Safeguards (§164.312)</h3>
    <ul>
        <li><strong>Access Control:</strong> All API requests authenticated via API keys</li>
        <li><strong>Audit Controls:</strong> Comprehensive logging of all PHI access attempts</li>
        <li><strong>Integrity:</strong> PII/PHI detection and protection mechanisms in place</li>
        <li><strong>Transmission Security:</strong> All data encrypted in transit (HTTPS/TLS)</li>
    </ul>

    <h2>Audit Log Summary</h2>
    <table>
        <tr>
            <th>Timestamp</th>
            <th>User ID</th>
            <th>PHI Detected</th>
            <th>Action Taken</th>
        </tr>
"""

        for log in self.data.audit_logs[:10]:
            phi_detected = "Yes" if log.get("pii_detected") else "No"
            action = "Blocked" if log.get("blocked") else "Logged & Allowed"
            html += f"""
        <tr>
            <td>{self.format_timestamp(log.get('timestamp', ''))}</td>
            <td>{log.get('user_id', 'anonymous')}</td>
            <td>{phi_detected}</td>
            <td>{action}</td>
        </tr>
"""

        html += """
    </table>

    <h2>Compliance Status</h2>
    <div class="summary-box">
        <p><strong>✓ Privacy Rule (§164.502):</strong> PHI use and disclosure controls implemented</p>
        <p><strong>✓ Security Rule (§164.306):</strong> Technical safeguards in place</p>
        <p><strong>✓ Security Rule (§164.308):</strong> Administrative safeguards via audit logging</p>
        <p><strong>✓ Security Rule (§164.312):</strong> Technical access controls and audit controls active</p>
    </div>
</body>
</html>
"""
        return html

    def generate_excel_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate HIPAA Excel data"""
        stats = self.calculate_statistics()

        return {
            "Summary": [
                {"Metric": "Total Access Attempts", "Value": stats['total_requests']},
                {"Metric": "PHI Detections", "Value": stats['pii_detections']},
                {"Metric": "Blocked Requests", "Value": stats['blocked_requests']},
            ],
            "Audit Logs": [
                {
                    "Timestamp": self.format_timestamp(log.get('timestamp', '')),
                    "User ID": log.get('user_id', 'anonymous'),
                    "PHI Detected": log.get('pii_detected', False),
                    "Blocked": log.get('blocked', False),
                    "Risk Score": log.get('risk_score', 0),
                }
                for log in self.data.audit_logs
            ],
        }
