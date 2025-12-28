"""
Workspace Model - Projects/Environments within an Organization
Allows organizations to separate data by project or environment
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from . import Base


class Workspace(Base):
    """
    Workspace table - Sub-organizations for projects/environments

    Workspaces allow an organization to separate data:
    - By project (e.g., "Mobile App", "Web Platform")
    - By environment (e.g., "production", "staging", "development")
    """
    __tablename__ = "workspaces"

    # Primary Key
    workspace_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Organization (tenant isolation)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Workspace Identity
    workspace_name = Column(String(255), nullable=False)
    workspace_slug = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Environment Type
    environment = Column(
        String(50),
        default="production",
        comment="production, staging, development, testing"
    )

    # Workspace-Specific Configuration
    # This can override organization-level SentinelConfig
    config = Column(
        JSONB,
        default={},
        comment="Workspace-specific security config overrides"
    )

    # Audit timestamps
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="workspaces")
    api_keys = relationship("APIKey", back_populates="workspace", cascade="all, delete-orphan")
    policies = relationship("Policy", back_populates="workspace", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="workspace")

    def __repr__(self):
        return f"<Workspace {self.workspace_slug} ({self.environment}) org={self.org_id}>"
