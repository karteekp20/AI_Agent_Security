"""Webhook Configuration Storage"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from . import Base


class Webhook(Base):
    """Webhook configuration for event notifications"""
    __tablename__ = "webhooks"

    webhook_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    webhook_url = Column(String(2000), nullable=False)
    webhook_secret = Column(
        String(255),
        nullable=True,
        comment="HMAC signing secret"
    )
    description = Column(String(500), nullable=True)

    events = Column(
        JSONB,
        nullable=False,
        default=list,
        comment="List of subscribed event types"
    )
    headers = Column(JSONB, nullable=True, comment="Custom headers to include")

    enabled = Column(Boolean, default=True)
    failure_count = Column(Integer, default=0)
    last_triggered = Column(DateTime(timezone=True), nullable=True)
    last_success = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    deliveries = relationship("WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Webhook {self.webhook_url[:50]} enabled={self.enabled}>"
