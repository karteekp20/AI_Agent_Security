"""Integration Configuration Storage"""

from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from . import Base


class Integration(Base):
    """Stores Slack/Teams/SIEM integration configurations"""
    __tablename__ = "integrations"

    integration_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    integration_type = Column(
        String(50),
        nullable=False,
        comment="slack, teams, siem"
    )
    config = Column(
        JSONB,
        nullable=False,
        comment="Type-specific configuration"
    )

    status = Column(
        String(20),
        default="configured",
        comment="configured, connected, error"
    )
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Integration {self.integration_type} status={self.status}>"
