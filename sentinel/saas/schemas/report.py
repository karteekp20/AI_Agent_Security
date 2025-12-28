"""
Report Schemas - Request/Response Models
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class GenerateReportRequest(BaseModel):
    """Request to generate a new compliance report"""
    report_name: str = Field(..., description="User-friendly report name")
    report_type: str = Field(..., description="Compliance framework: pci_dss, gdpr, hipaa, soc2")
    file_format: str = Field("pdf", description="Output format: pdf, excel, json")
    date_range_start: datetime = Field(..., description="Report data start date")
    date_range_end: datetime = Field(..., description="Report data end date")
    workspace_id: Optional[UUID] = Field(None, description="Optional workspace filter")
    description: Optional[str] = Field(None, description="Report description")


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class ReportResponse(BaseModel):
    """Report metadata"""
    report_id: UUID
    org_id: UUID
    workspace_id: Optional[UUID] = None
    report_name: str
    report_type: str
    description: Optional[str] = None
    date_range_start: datetime
    date_range_end: datetime
    file_format: str
    file_url: Optional[str] = None
    file_size_bytes: Optional[int] = 0
    status: str  # pending, processing, completed, failed
    progress_percentage: Optional[int] = 0
    error_message: Optional[str] = None
    total_requests_analyzed: Optional[int] = 0
    threats_detected: Optional[int] = 0
    pii_instances: Optional[int] = 0
    injections_blocked: Optional[int] = 0
    generated_by: Optional[UUID] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    """List of reports with pagination"""
    reports: list[ReportResponse]
    total: int
    page: int
    page_size: int
