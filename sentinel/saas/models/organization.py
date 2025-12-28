"""
Organization Model - Core Tenant Entity
Represents a company/team using the Sentinel platform
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from . import Base


class Organization(Base):
    """
    Organization table - Core multi-tenant entity

    Each organization represents a separate tenant with complete data isolation.
    All other tables reference org_id for Row-Level Security.
    """
    __tablename__ = "organizations"

    # Primary Key
    org_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Organization Identity
    org_name = Column(String(255), nullable=False)
    org_slug = Column(String(100), unique=True, nullable=False, index=True)

    # Subscription Plan
    subscription_tier = Column(
        String(50),
        default="free",
        comment="free, starter, pro, enterprise"
    )
    subscription_status = Column(
        String(50),
        default="active",
        comment="active, suspended, cancelled, trialing"
    )
    subscription_started_at = Column(DateTime(timezone=True), server_default=func.now())
    subscription_ends_at = Column(DateTime(timezone=True), nullable=True)

    # Billing
    billing_email = Column(String(255), nullable=True)
    stripe_customer_id = Column(String(255), nullable=True, index=True)

    # Limits (based on subscription tier)
    max_users = Column(Integer, default=5)
    max_api_requests_per_month = Column(Integer, default=10000)
    max_storage_mb = Column(Integer, default=1000)

    # Usage Tracking
    current_users = Column(Integer, default=0)
    api_requests_this_month = Column(Integer, default=0)
    storage_used_mb = Column(Float, default=0.0)

    # Settings (flexible JSON field for org-specific config)
    settings = Column(
        JSONB,
        default={},
        comment="Custom settings: enable_sso, custom_domain, etc."
    )

    # Audit timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete

    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    workspaces = relationship("Workspace", back_populates="organization", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="organization", cascade="all, delete-orphan")
    policies = relationship("Policy", back_populates="organization", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="organization", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization {self.org_slug} ({self.subscription_tier})>"

    @property
    def is_active(self) -> bool:
        """Check if organization is active"""
        return self.subscription_status == "active" and self.deleted_at is None

    @property
    def is_within_limits(self) -> bool:
        """Check if organization is within usage limits"""
        return (
            self.current_users <= self.max_users and
            self.api_requests_this_month <= self.max_api_requests_per_month and
            self.storage_used_mb <= self.max_storage_mb
        )
