"""Webhook Delivery Audit Log"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from . import Base


class WebhookDelivery(Base):
    """Tracks webhook delivery attempts"""
    __tablename__ = "webhook_deliveries"

    delivery_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id = Column(
        UUID(as_uuid=True),
        ForeignKey("webhooks.webhook_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    event_type = Column(String(100), nullable=False)
    payload = Column(JSONB, nullable=False)

    status = Column(
        String(20),
        default="pending",
        comment="pending, success, failed"
    )
    response_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    retry_count = Column(Integer, default=0)
    next_retry = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    webhook = relationship("Webhook", back_populates="deliveries")

    def __repr__(self):
        return f"<WebhookDelivery {self.event_type} status={self.status}>"
