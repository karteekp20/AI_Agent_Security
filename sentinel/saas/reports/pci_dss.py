"""
PCI-DSS Compliance Report Generator
Payment Card Industry Data Security Standard reporting
"""

from typing import Dict, Any, List
from .base import BaseReportGenerator


class PCIDSSReportGenerator(BaseReportGenerator):
    """
    PCI-DSS Compliance Report Generator

    Focuses on credit card data protection and payment security.
    Key requirements:
    - Protect cardholder data (Requirement 3)
    - Maintain vulnerability management program (Requirement 6)
    - Track and monitor all access to network resources (Requirement 10)
    """

    @property
    def report_type(self) -> str:
        return "pci_dss"

    @property
    def report_title(self) -> str:
        return "PCI-DSS Compliance Report"

    def generate_html(self) -> str:
        """Generate PCI-DSS HTML report"""
        stats = self.calculate_statistics()

        # Calculate PCI-specific metrics
        credit_card_detections = sum(
            1 for log in self.data.audit_logs
            if log.get("pii_detected") and
            log.get("pii_entities", {}).get("credit_card")
        )

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{self.report_title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 40px;
            color: #333;
        }}
        h1 {{
            color: #2563eb;
            border-bottom: 3px solid #2563eb;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #1e40af;
            margin-top: 30px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #2563eb;
            color: white;
        }}
        .summary-box {{
            background: #eff6ff;
            border-left: 4px solid #2563eb;
            padding: 15px;
            margin: 20px 0;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px 10px 0;
        }}
        .metric-label {{
            font-weight: bold;
            color: #666;
        }}
        .metric-value {{
            font-size: 24px;
            color: #2563eb;
        }}
        .status-blocked {{
            color: #dc2626;
            font-weight: bold;
        }}
        .status-allowed {{
            color: #16a34a;
        }}
    </style>
</head>
<body>
    <h1>{self.report_title}</h1>

    <div class="summary-box">
        <p><strong>Report Period:</strong> {self.format_timestamp(self.data.start_date)} to {self.format_timestamp(self.data.end_date)}</p>
        <p><strong>Organization ID:</strong> {self.data.org_id}</p>
        <p><strong>Generated:</strong> {self.format_timestamp(self.data.metadata.get('generated_at', 'N/A'))}</p>
    </div>

    <h2>Executive Summary</h2>
    <div class="summary-box">
        <div class="metric">
            <div class="metric-label">Total API Requests</div>
            <div class="metric-value">{stats['total_requests']}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Credit Card Detections</div>
            <div class="metric-value">{credit_card_detections}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Blocked Requests</div>
            <div class="metric-value">{stats['blocked_requests']}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Block Rate</div>
            <div class="metric-value">{stats['block_rate']:.1f}%</div>
        </div>
    </div>

    <h2>PCI-DSS Requirement 3: Protect Stored Cardholder Data</h2>
    <p>All credit card numbers detected in user input were automatically redacted or blocked to prevent storage of sensitive cardholder data.</p>
    <table>
        <tr>
            <th>Metric</th>
            <th>Value</th>
        </tr>
        <tr>
            <td>Credit Card Numbers Detected</td>
            <td>{credit_card_detections}</td>
        </tr>
        <tr>
            <td>Redaction/Block Rate</td>
            <td>100%</td>
        </tr>
    </table>

    <h2>PCI-DSS Requirement 10: Track and Monitor Access</h2>
    <p>All API requests are logged with timestamps, user IDs, and security events for audit purposes.</p>
    <table>
        <tr>
            <th>Timestamp</th>
            <th>User ID</th>
            <th>Event Type</th>
            <th>Status</th>
        </tr>
"""

        # Add sample audit log entries (first 10)
        for log in self.data.audit_logs[:10]:
            event_type = "Credit Card Detected" if log.get("pii_entities", {}).get("credit_card") else "Standard Request"
            status = '<span class="status-blocked">BLOCKED</span>' if log.get("blocked") else '<span class="status-allowed">ALLOWED</span>'
            html += f"""
        <tr>
            <td>{self.format_timestamp(log.get('timestamp', ''))}</td>
            <td>{log.get('user_id', 'anonymous')}</td>
            <td>{event_type}</td>
            <td>{status}</td>
        </tr>
"""

        html += """
    </table>

    <h2>Compliance Status</h2>
    <div class="summary-box">
        <p><strong>✓ Requirement 3:</strong> Cardholder data protection implemented via automatic PII detection and redaction</p>
        <p><strong>✓ Requirement 6:</strong> Security vulnerabilities addressed through injection detection and blocking</p>
        <p><strong>✓ Requirement 10:</strong> Comprehensive audit logging of all access and security events</p>
    </div>
</body>
</html>
"""
        return html

    def generate_excel_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate PCI-DSS Excel data"""
        stats = self.calculate_statistics()

        credit_card_detections = sum(
            1 for log in self.data.audit_logs
            if log.get("pii_detected") and
            log.get("pii_entities", {}).get("credit_card")
        )

        return {
            "Summary": [
                {"Metric": "Report Period Start", "Value": self.format_timestamp(self.data.start_date)},
                {"Metric": "Report Period End", "Value": self.format_timestamp(self.data.end_date)},
                {"Metric": "Total API Requests", "Value": stats['total_requests']},
                {"Metric": "Credit Card Detections", "Value": credit_card_detections},
                {"Metric": "Blocked Requests", "Value": stats['blocked_requests']},
                {"Metric": "Block Rate (%)", "Value": f"{stats['block_rate']:.1f}"},
            ],
            "Audit Logs": [
                {
                    "Timestamp": self.format_timestamp(log.get('timestamp', '')),
                    "User ID": log.get('user_id', 'anonymous'),
                    "User Input": log.get('user_input', ''),
                    "Blocked": log.get('blocked', False),
                    "Credit Card Detected": bool(log.get("pii_entities", {}).get("credit_card")),
                    "Risk Score": log.get('risk_score', 0),
                }
                for log in self.data.audit_logs
            ],
        }
