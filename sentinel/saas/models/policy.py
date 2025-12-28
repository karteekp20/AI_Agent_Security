"""
Policy Model - Custom Security Rules per Organization
Dynamic security policies with canary deployment support
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, func, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from . import Base


class Policy(Base):
    """
    Policy table - Custom security rules per organization/workspace

    Policies allow organizations to define custom security rules beyond
    the default Sentinel patterns. Supports canary deployments and A/B testing.
    """
    __tablename__ = "policies"

    # Primary Key
    policy_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Organization (tenant isolation)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Workspace (optional - policy can be org-wide or workspace-specific)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Policy Metadata
    policy_name = Column(String(255), nullable=False)
    policy_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="pii_pattern, injection_rule, custom_filter, content_moderation"
    )
    description = Column(Text, nullable=True)

    # Policy Definition
    policy_config = Column(
        JSONB,
        nullable=False,
        comment="Configuration: {pattern: '...', action: 'block', threshold: 0.8, ...}"
    )

    # Version Control
    version = Column(Integer, default=1)
    parent_policy_id = Column(
        UUID(as_uuid=True),
        ForeignKey("policies.policy_id"),
        nullable=True,
        comment="For versioning - points to previous version"
    )

    # Deployment Status
    status = Column(
        String(50),
        default="draft",
        nullable=False,
        index=True,
        comment="draft, testing, active, archived"
    )
    deployed_at = Column(DateTime(timezone=True), nullable=True)

    # Canary Deployment / A/B Testing
    test_mode = Column(Boolean, default=False, comment="Test mode before full deployment")
    test_percentage = Column(
        Integer,
        default=0,
        comment="Percentage of traffic (0-100) for canary rollout"
    )

    # Impact Tracking
    triggered_count = Column(Integer, default=0, comment="How many times this policy matched")
    false_positive_count = Column(Integer, default=0, comment="Reported false positives")

    # Audit
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="policies")
    workspace = relationship("Workspace", back_populates="policies")
    created_by_user = relationship("User", back_populates="policies", foreign_keys=[created_by])

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'testing', 'active', 'archived')",
            name="valid_policy_status"
        ),
        CheckConstraint(
            "test_percentage >= 0 AND test_percentage <= 100",
            name="valid_test_percentage"
        ),
    )

    def __repr__(self):
        return f"<Policy {self.policy_name} ({self.status}) type={self.policy_type}>"

    @property
    def is_active(self) -> bool:
        """Check if policy is actively deployed"""
        return self.status == "active"

    @property
    def false_positive_rate(self) -> float:
        """Calculate false positive rate"""
        if self.triggered_count == 0:
            return 0.0
        return self.false_positive_count / self.triggered_count
