"""
API Key Model - Multi-Tenant API Authentication
Secure API key management with SHA-256 hashing
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from . import Base


class APIKey(Base):
    """
    API Key table - Multi-tenant API authentication

    API keys allow programmatic access to the /process endpoint.
    Keys are SHA-256 hashed in database for security.
    Only the prefix (sk_live_abc...) is stored in plain text for UI display.
    """
    __tablename__ = "api_keys"

    # Primary Key
    key_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Organization (tenant isolation)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Workspace (optional - key can be org-wide or workspace-specific)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Key Data
    key_hash = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="SHA-256 hash of the actual API key"
    )
    key_prefix = Column(
        String(20),
        nullable=False,
        comment="First few characters for UI display (sk_live_abc...)"
    )
    key_name = Column(String(255), nullable=True, comment="User-friendly name")

    # Scope (what this key can do)
    scopes = Column(
        JSONB,
        default=["process"],
        comment="Allowed endpoints: ['process', 'metrics', 'reports']"
    )

    # Rate Limits
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_hour = Column(Integer, default=1000)

    # Status
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, comment="Optional expiration")

    # Audit
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="api_keys")
    workspace = relationship("Workspace", back_populates="api_keys")
    created_by_user = relationship("User", back_populates="api_keys", foreign_keys=[created_by])

    def __repr__(self):
        return f"<APIKey {self.key_prefix}... ({self.key_name}) org={self.org_id}>"

    @property
    def is_valid(self) -> bool:
        """Check if API key is valid (active and not expired)"""
        from datetime import datetime
        if not self.is_active or self.revoked_at:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True
