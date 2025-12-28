"""
Reports API Router
Generate and manage compliance reports
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID

from ..dependencies import get_db, get_current_user
from ..models import User, Report
from ..schemas.report import (
    GenerateReportRequest,
    ReportResponse,
    ReportListResponse,
)
from ..tasks.report_tasks import generate_report_task

router = APIRouter(prefix="/reports", tags=["reports"])


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("", response_model=ReportResponse, status_code=202)
async def generate_report(
    request: GenerateReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a new compliance report (async)

    **Supported Report Types:**
    - `pci_dss`: PCI-DSS Compliance (credit card data protection)
    - `gdpr`: GDPR Compliance (personal data protection)
    - `hipaa`: HIPAA Compliance (health information security)
    - `soc2`: SOC 2 Type II Compliance (trust service criteria)

    **Supported Formats:**
    - `pdf`: PDF document (default)
    - `excel`: Excel spreadsheet
    - `json`: JSON data export

    **Flow:**
    1. Creates report record with status "pending"
    2. Queues background task for report generation
    3. Returns immediately with report metadata
    4. Client can poll GET /reports/{id} to check status
    5. When status="completed", file_url contains download link

    **Example Request:**
    ```json
    {
      "report_name": "Q4 2024 PCI-DSS Compliance Report",
      "report_type": "pci_dss",
      "file_format": "pdf",
      "date_range_start": "2024-10-01T00:00:00Z",
      "date_range_end": "2024-12-31T23:59:59Z",
      "workspace_id": "770e8400-..."
    }
    ```
    """
    # Validate report type
    valid_types = ["pci_dss", "gdpr", "hipaa", "soc2"]
    if request.report_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid report_type. Must be one of: {', '.join(valid_types)}"
        )

    # Validate file format
    valid_formats = ["pdf", "excel", "json"]
    if request.file_format not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file_format. Must be one of: {', '.join(valid_formats)}"
        )

    # Validate date range
    if request.date_range_start >= request.date_range_end:
        raise HTTPException(
            status_code=400,
            detail="date_range_start must be before date_range_end"
        )

    # Create report record
    report = Report(
        org_id=current_user.org_id,
        workspace_id=request.workspace_id,
        report_name=request.report_name,
        report_type=request.report_type,
        description=request.description,
        date_range_start=request.date_range_start,
        date_range_end=request.date_range_end,
        file_format=request.file_format,
        status="pending",
        progress_percentage=0,
        generated_by=current_user.user_id,
        metadata={},
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    # Queue background task
    task = generate_report_task.delay(
        report_id=str(report.report_id),
        org_id=str(current_user.org_id),
        workspace_id=str(request.workspace_id) if request.workspace_id else None,
        report_type=request.report_type,
        report_format=request.file_format,
        start_date=request.date_range_start.isoformat(),
        end_date=request.date_range_end.isoformat(),
    )

    # Update with task ID
    report.metadata = {"task_id": task.id}
    db.commit()

    return ReportResponse.model_validate(report)


@router.get("", response_model=ReportListResponse)
async def list_reports(
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all reports for the current organization

    **Query Parameters:**
    - `report_type`: Filter by compliance framework (pci_dss, gdpr, hipaa, soc2)
    - `status`: Filter by status (pending, processing, completed, failed)
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 20, max: 100)

    **Response:**
    ```json
    {
      "reports": [
        {
          "report_id": "880e8400-...",
          "report_name": "Q4 2024 PCI-DSS Report",
          "report_type": "pci_dss",
          "status": "completed",
          "file_url": "/reports/880e8400-.../download",
          "created_at": "2024-01-15T10:00:00Z",
          "completed_at": "2024-01-15T10:05:30Z"
        }
      ],
      "total": 1,
      "page": 1,
      "page_size": 20
    }
    ```
    """
    # Build query
    query = db.query(Report).filter(Report.org_id == current_user.org_id)

    # Apply filters
    if report_type:
        query = query.filter(Report.report_type == report_type)

    if status:
        query = query.filter(Report.status == status)

    # Order by created_at descending
    query = query.order_by(Report.created_at.desc())

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    reports = query.offset(offset).limit(page_size).all()

    return ReportListResponse(
        reports=[ReportResponse.model_validate(r) for r in reports],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get report details by ID

    Use this endpoint to poll for report generation progress:
    - `status="pending"`: Queued, not yet started
    - `status="processing"`: Currently generating (check progress_percentage)
    - `status="completed"`: Ready for download (use file_url)
    - `status="failed"`: Generation failed (check error_message)
    """
    report = db.query(Report).filter(
        Report.report_id == report_id,
        Report.org_id == current_user.org_id,
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return ReportResponse.model_validate(report)


@router.get("/{report_id}/download", response_class=PlainTextResponse)
async def download_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Download report file

    **Returns:**
    - Content-Type: application/pdf, application/vnd.ms-excel, or application/json
    - Content-Disposition: attachment; filename="report.pdf"

    **Errors:**
    - 404: Report not found
    - 400: Report not yet completed
    - 410: Report file expired (for S3 signed URLs)
    """
    report = db.query(Report).filter(
        Report.report_id == report_id,
        Report.org_id == current_user.org_id,
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Report not ready. Current status: {report.status}"
        )

    # In production, this would redirect to S3 signed URL
    # For demo, generate a simple report content
    if report.file_format == "pdf":
        file_content = f"""
        <html>
        <head><title>{report.report_name}</title></head>
        <body>
            <h1>{report.report_name}</h1>
            <h2>Report Type: {report.report_type.upper()}</h2>
            <p>Date Range: {report.date_range_start} to {report.date_range_end}</p>
            <hr>
            <h3>Summary</h3>
            <ul>
                <li>Total Requests Analyzed: {report.total_requests_analyzed or 0}</li>
                <li>Threats Detected: {report.threats_detected or 0}</li>
                <li>PII Instances: {report.pii_instances or 0}</li>
                <li>Injections Blocked: {report.injections_blocked or 0}</li>
            </ul>
            <p><em>Note: This is a demo report. In production, this would be a full PDF from S3.</em></p>
        </body>
        </html>
        """
        media_type = "text/html"
    else:
        file_content = {
            "report_name": report.report_name,
            "report_type": report.report_type,
            "date_range": {
                "start": report.date_range_start.isoformat(),
                "end": report.date_range_end.isoformat()
            },
            "summary": {
                "total_requests_analyzed": report.total_requests_analyzed or 0,
                "threats_detected": report.threats_detected or 0,
                "pii_instances": report.pii_instances or 0,
                "injections_blocked": report.injections_blocked or 0
            },
            "note": "This is a demo report. In production, this would contain full audit data."
        }
        import json
        file_content = json.dumps(file_content, indent=2)
        media_type = "application/json"

    return PlainTextResponse(
        content=file_content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{report.report_name}.{report.file_format}"'
        }
    )


@router.delete("/{report_id}", status_code=204)
async def delete_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a report

    **Effect:**
    - Removes report metadata from database
    - In production, would also delete file from S3

    **Response:** 204 No Content
    """
    report = db.query(Report).filter(
        Report.report_id == report_id,
        Report.org_id == current_user.org_id,
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # In production, delete from S3 if file exists
    # For now, just delete from database
    db.delete(report)
    db.commit()

    return None
