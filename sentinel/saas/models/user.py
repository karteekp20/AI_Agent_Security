"""
User Model - SaaS Platform Users with RBAC
Represents individual users within an organization
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from . import Base


class User(Base):
    """
    User table - Platform users with role-based access control

    Each user belongs to exactly one organization.
    Supports password-based auth, MFA, and SSO.
    """
    __tablename__ = "users"

    # Primary Key
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Organization (tenant isolation)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Identity
    email = Column(String(255), nullable=False, index=True)
    username = Column(String(100), nullable=True)
    password_hash = Column(String(255), nullable=True, comment="bcrypt hash")

    # Profile
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(String(512), nullable=True)

    # Role-Based Access Control (RBAC)
    role = Column(
        String(50),
        default="member",
        nullable=False,
        comment="owner, admin, member, viewer, auditor"
    )
    permissions = Column(
        JSONB,
        default=[],
        comment="Granular permissions: ['policies:write', 'reports:read', ...]"
    )

    # Multi-Factor Authentication (MFA)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255), nullable=True, comment="TOTP secret")

    # Single Sign-On (SSO)
    sso_provider = Column(
        String(50),
        nullable=True,
        comment="google, okta, azure_ad, github"
    )
    sso_user_id = Column(String(255), nullable=True, index=True)

    # Status
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Audit timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="users")
    api_keys = relationship("APIKey", back_populates="created_by_user", foreign_keys="APIKey.created_by")
    policies = relationship("Policy", back_populates="created_by_user", foreign_keys="Policy.created_by")
    reports = relationship("Report", back_populates="generated_by_user", foreign_keys="Report.generated_by")

    # Constraints
    __table_args__ = (
        # Unique email per organization
        CheckConstraint(
            "role IN ('owner', 'admin', 'member', 'viewer', 'auditor')",
            name="valid_role"
        ),
    )

    def __repr__(self):
        return f"<User {self.email} ({self.role}) org={self.org_id}>"

    @property
    def can_write_policies(self) -> bool:
        """Check if user can create/edit policies"""
        return self.role in ("owner", "admin") or "policies:write" in self.permissions

    @property
    def can_generate_reports(self) -> bool:
        """Check if user can generate compliance reports"""
        return self.role in ("owner", "admin", "auditor") or "reports:generate" in self.permissions

    @property
    def can_manage_users(self) -> bool:
        """Check if user can invite/remove users"""
        return self.role in ("owner", "admin")

    @property
    def can_manage_billing(self) -> bool:
        """Check if user can manage subscriptions/billing"""
        return self.role == "owner"
