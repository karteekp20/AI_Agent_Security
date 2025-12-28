"""
Report Generation Celery Tasks
Background tasks for generating compliance reports
"""

from celery import Task
from datetime import datetime
from typing import Dict, Any, Optional
import io
import json

from ..celery_app import celery_app
from ..database import SessionLocal
from ..models import Report
from ..reports import (
    BaseReportGenerator,
    PCIDSSReportGenerator,
    GDPRReportGenerator,
    HIPAAReportGenerator,
    SOC2ReportGenerator,
)
from ..reports.base import ReportData
from ...storage.postgres_adapter import PostgreSQLAdapter, PostgreSQLConfig


class ReportGenerationTask(Task):
    """Custom task class with database session management"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        db = SessionLocal()
        try:
            report_id = kwargs.get('report_id')
            if report_id:
                report = db.query(Report).filter(Report.report_id == report_id).first()
                if report:
                    report.status = "failed"
                    report.error_message = str(exc)
                    report.completed_at = datetime.utcnow()
                    db.commit()
        finally:
            db.close()


@celery_app.task(base=ReportGenerationTask, bind=True, name="generate_report")
def generate_report_task(
    self,
    report_id: str,
    org_id: str,
    workspace_id: Optional[str],
    report_type: str,
    report_format: str,
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    """
    Generate compliance report asynchronously

    Args:
        report_id: UUID of the report record
        org_id: Organization ID
        workspace_id: Optional workspace ID
        report_type: Report type (pci_dss, gdpr, hipaa, soc2)
        report_format: Output format (pdf, excel, json)
        start_date: ISO format datetime string
        end_date: ISO format datetime string

    Returns:
        Dictionary with report generation results
    """
    db = SessionLocal()

    try:
        # Update report status to processing
        report = db.query(Report).filter(Report.report_id == report_id).first()
        if not report:
            raise ValueError(f"Report {report_id} not found")

        report.status = "processing"
        report.started_at = datetime.utcnow()
        db.commit()

        # Parse dates
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        # Get audit logs from PostgreSQL
        # For demo purposes, using empty config - in production, get from environment
        pg_adapter = PostgreSQLAdapter(PostgreSQLConfig(
            host="localhost",
            port=5432,
            database="sentinel",
            user="sentinel_user",
            password="sentinel_password",
        ))

        audit_logs = []
        statistics = {}

        if pg_adapter.enabled:
            audit_logs = pg_adapter.get_audit_logs(
                start_time=start_dt,
                end_time=end_dt,
                org_id=org_id,
                workspace_id=workspace_id,
                limit=10000,
            )

            # Calculate statistics
            statistics = pg_adapter.get_compliance_stats(
                start_date=start_dt,
                end_date=end_dt,
                org_id=org_id,
                workspace_id=workspace_id,
            )

        # Create report data
        report_data = ReportData(
            org_id=org_id,
            workspace_id=workspace_id,
            start_date=start_dt,
            end_date=end_dt,
            audit_logs=audit_logs,
            statistics=statistics or {},
            metadata={
                "generated_at": datetime.utcnow().isoformat(),
                "task_id": self.request.id,
            }
        )

        # Select appropriate generator
        generator_map = {
            "pci_dss": PCIDSSReportGenerator,
            "gdpr": GDPRReportGenerator,
            "hipaa": HIPAAReportGenerator,
            "soc2": SOC2ReportGenerator,
        }

        GeneratorClass = generator_map.get(report_type)
        if not GeneratorClass:
            raise ValueError(f"Unknown report type: {report_type}")

        generator = GeneratorClass(report_data)

        # Generate report based on format
        file_content = None
        file_size = 0

        if report_format == "json":
            report_json = generator.generate_json()
            file_content = json.dumps(report_json, indent=2)
            file_size = len(file_content.encode('utf-8'))

        elif report_format == "excel":
            # Generate Excel using pandas (placeholder - would need pandas/openpyxl)
            excel_data = generator.generate_excel_data()
            # For now, store as JSON - in production, use pandas.ExcelWriter
            file_content = json.dumps(excel_data, indent=2)
            file_size = len(file_content.encode('utf-8'))

        elif report_format == "pdf":
            # Generate HTML first
            html_content = generator.generate_html()
            # For now, store HTML - in production, use WeasyPrint or similar
            file_content = html_content
            file_size = len(file_content.encode('utf-8'))

        # In production, upload to S3 and get signed URL
        # For now, store content in metadata
        report.file_url = f"/reports/{report_id}/download"
        report.file_size_bytes = file_size
        report.status = "completed"
        report.completed_at = datetime.utcnow()

        # Store statistics
        report.total_requests_analyzed = statistics.get("total_requests", 0)
        report.threats_detected = statistics.get("total_threats", 0)
        report.pii_instances = statistics.get("pii_detections", 0)
        report.injections_blocked = statistics.get("injection_attempts", 0)

        # Update filters with task metadata
        current_filters = report.filters or {}
        report.filters = {
            **current_filters,
            "generated_by_task": self.request.id,
        }

        db.commit()

        return {
            "status": "completed",
            "report_id": str(report_id),
            "file_url": report.file_url,
            "file_size": file_size,
        }

    except Exception as e:
        # Error handling - update report status
        report.status = "failed"
        report.error_message = str(e)
        report.completed_at = datetime.utcnow()
        db.commit()
        raise

    finally:
        db.close()
