"""
Email Log Model - Track all sent emails for compliance and troubleshooting
"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

from . import Base


class EmailStatus(str, enum.Enum):
    """Email delivery status"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"
    COMPLAINED = "complained"  # Recipient marked as spam


class EmailLog(Base):
    """
    Email log for compliance tracking and troubleshooting

    Tracks all emails sent by the system including status, delivery information,
    and any errors encountered during sending.
    """
    __tablename__ = "email_logs"

    # Primary key
    email_log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Multi-tenant
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)

    # Email details
    template_name = Column(String(100), nullable=False)  # e.g., "invitation", "verification"
    to_email = Column(String(255), nullable=False, index=True)
    subject = Column(String(500), nullable=False)

    # Delivery tracking
    status = Column(
        SQLEnum(EmailStatus, name="email_status_enum", create_type=True),
        nullable=False,
        default=EmailStatus.PENDING,
        index=True
    )
    provider = Column(String(20), nullable=False)  # "ses" or "smtp"
    ses_message_id = Column(String(255), nullable=True)  # AWS SES Message ID
    error_message = Column(Text, nullable=True)  # Error details if failed

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    sent_at = Column(DateTime, nullable=True)  # When successfully sent
    bounced_at = Column(DateTime, nullable=True)  # When bounce detected
    complained_at = Column(DateTime, nullable=True)  # When complaint detected

    # Relationships
    organization = relationship("Organization", back_populates="email_logs")
    user = relationship("User", back_populates="email_logs")

    def __repr__(self):
        return (
            f"<EmailLog(id={self.email_log_id}, "
            f"to={self.to_email}, "
            f"template={self.template_name}, "
            f"status={self.status})>"
        )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "email_log_id": str(self.email_log_id),
            "org_id": str(self.org_id),
            "user_id": str(self.user_id) if self.user_id else None,
            "template_name": self.template_name,
            "to_email": self.to_email,
            "subject": self.subject,
            "status": self.status.value,
            "provider": self.provider,
            "ses_message_id": self.ses_message_id,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "bounced_at": self.bounced_at.isoformat() if self.bounced_at else None,
            "complained_at": self.complained_at.isoformat() if self.complained_at else None,
        }
