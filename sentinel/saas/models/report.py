"""
Report Model - Compliance Report Generation Metadata
Tracks generated compliance reports (PCI-DSS, GDPR, HIPAA, SOC2)
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, func, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from . import Base


class Report(Base):
    """
    Report table - Compliance report generation metadata

    Tracks background report generation jobs for compliance frameworks.
    Actual PDF/Excel files stored in S3, metadata stored here.
    """
    __tablename__ = "reports"

    # Primary Key
    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Organization (tenant isolation)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Workspace (optional - report can be org-wide or workspace-specific)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Report Metadata
    report_name = Column(String(255), nullable=False)
    report_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="pci_dss, gdpr, hipaa, soc2, custom"
    )
    description = Column(Text, nullable=True)

    # Generation Parameters
    date_range_start = Column(DateTime(timezone=True), nullable=False, comment="Report data start date")
    date_range_end = Column(DateTime(timezone=True), nullable=False, comment="Report data end date")
    filters = Column(
        JSONB,
        default={},
        comment="Report filters: {workspace_id: '...', threat_type: 'pii', ...}"
    )

    # File Information
    file_format = Column(
        String(20),
        nullable=False,
        comment="pdf, excel, json"
    )
    file_url = Column(
        String(512),
        nullable=True,
        comment="S3 signed URL or file path"
    )
    file_size_bytes = Column(Integer, default=0)

    # Generation Status
    status = Column(
        String(50),
        default="pending",
        nullable=False,
        index=True,
        comment="pending, processing, completed, failed"
    )
    progress_percentage = Column(
        Integer,
        default=0,
        comment="0-100 for progress tracking"
    )
    error_message = Column(Text, nullable=True, comment="Error details if generation failed")

    # Statistics (included in report)
    total_requests_analyzed = Column(Integer, default=0)
    threats_detected = Column(Integer, default=0)
    pii_instances = Column(Integer, default=0)
    injections_blocked = Column(Integer, default=0)

    # Audit
    generated_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=True,
        comment="User who requested report generation"
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True, comment="When generation started")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="When generation finished")
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="S3 signed URL expiration (typically 24h after completion)"
    )

    # Relationships
    organization = relationship("Organization", back_populates="reports")
    workspace = relationship("Workspace", back_populates="reports")
    generated_by_user = relationship("User", back_populates="reports", foreign_keys=[generated_by])

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="valid_report_status"
        ),
        CheckConstraint(
            "file_format IN ('pdf', 'excel', 'json')",
            name="valid_file_format"
        ),
        CheckConstraint(
            "progress_percentage >= 0 AND progress_percentage <= 100",
            name="valid_progress_percentage"
        ),
        CheckConstraint(
            "date_range_start <= date_range_end",
            name="valid_date_range"
        ),
    )

    def __repr__(self):
        return f"<Report {self.report_name} ({self.report_type}) status={self.status}>"

    @property
    def is_ready(self) -> bool:
        """Check if report is ready for download"""
        return self.status == "completed" and self.file_url is not None

    @property
    def is_expired(self) -> bool:
        """Check if report S3 URL has expired"""
        from datetime import datetime
        if not self.expires_at:
            return False
        return self.expires_at < datetime.utcnow()

    @property
    def generation_time_seconds(self) -> float:
        """Calculate report generation time in seconds"""
        if not self.started_at or not self.completed_at:
            return 0.0
        delta = self.completed_at - self.started_at
        return delta.total_seconds()
