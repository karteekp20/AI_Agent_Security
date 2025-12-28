"""
Subscription Model - Billing and Subscription Management
Tracks Stripe subscriptions and payment history
"""

from sqlalchemy import Column, String, Integer, Numeric, Boolean, DateTime, ForeignKey, func, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from . import Base


class Subscription(Base):
    """
    Subscription table - Billing and subscription management

    Tracks Stripe subscriptions, payment history, and plan changes.
    Each organization can have multiple subscription records (for history).
    Only one subscription per org should be active at a time.
    """
    __tablename__ = "subscriptions"

    # Primary Key
    subscription_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Organization (tenant isolation)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Stripe Integration
    stripe_subscription_id = Column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        comment="Stripe subscription ID (sub_xxx)"
    )
    stripe_customer_id = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Stripe customer ID (cus_xxx)"
    )
    stripe_price_id = Column(
        String(255),
        nullable=True,
        comment="Stripe price ID (price_xxx)"
    )

    # Plan Details
    plan_name = Column(
        String(100),
        nullable=False,
        comment="free, starter, pro, enterprise"
    )
    billing_cycle = Column(
        String(50),
        default="monthly",
        comment="monthly, yearly, lifetime"
    )
    amount = Column(
        Numeric(10, 2),
        default=0.00,
        comment="Subscription amount in USD"
    )
    currency = Column(String(3), default="USD")

    # Status
    status = Column(
        String(50),
        default="active",
        nullable=False,
        index=True,
        comment="active, trialing, past_due, canceled, unpaid"
    )
    trial_end = Column(DateTime(timezone=True), nullable=True, comment="Trial period end date")

    # Subscription Lifecycle
    current_period_start = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Current billing period start"
    )
    current_period_end = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Current billing period end"
    )
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Billing
    next_billing_date = Column(DateTime(timezone=True), nullable=True)
    last_payment_date = Column(DateTime(timezone=True), nullable=True)
    last_payment_amount = Column(Numeric(10, 2), default=0.00)
    payment_failed_count = Column(Integer, default=0, comment="Number of failed payment attempts")

    # Features & Limits (based on plan)
    features = Column(
        JSONB,
        default={},
        comment="Enabled features: {api_rate_limit: 10000, max_users: 10, reports: true, ...}"
    )

    # Stripe Metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    stripe_metadata = Column(
        JSONB,
        default={},
        comment="Additional Stripe metadata or custom fields"
    )

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="subscriptions")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'trialing', 'past_due', 'canceled', 'unpaid', 'incomplete')",
            name="valid_subscription_status"
        ),
        CheckConstraint(
            "billing_cycle IN ('monthly', 'yearly', 'lifetime')",
            name="valid_billing_cycle"
        ),
        CheckConstraint(
            "amount >= 0",
            name="valid_amount"
        ),
        CheckConstraint(
            "payment_failed_count >= 0",
            name="valid_payment_failed_count"
        ),
    )

    def __repr__(self):
        return f"<Subscription {self.plan_name} ({self.billing_cycle}) org={self.org_id} status={self.status}>"

    @property
    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        return self.status in ("active", "trialing")

    @property
    def is_past_due(self) -> bool:
        """Check if payment is past due"""
        return self.status == "past_due"

    @property
    def is_trial(self) -> bool:
        """Check if subscription is in trial period"""
        from datetime import datetime
        if self.status != "trialing" or not self.trial_end:
            return False
        return self.trial_end > datetime.utcnow()

    @property
    def days_until_renewal(self) -> int:
        """Calculate days until next billing date"""
        from datetime import datetime
        if not self.next_billing_date:
            return 0
        delta = self.next_billing_date - datetime.utcnow()
        return max(0, delta.days)

    @property
    def needs_payment_method_update(self) -> bool:
        """Check if payment method needs updating (multiple failures)"""
        return self.payment_failed_count >= 2
