"""User Behavioral Baseline Storage"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from . import Base


class UserBaseline(Base):
    """Stores per-user behavioral feature vectors"""
    __tablename__ = "user_baselines"

    baseline_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(String(255), nullable=False, index=True)

    feature_vector = Column(
        JSONB,
        nullable=False,
        comment="17+ dimensional feature vector"
    )
    sample_count = Column(
        Integer,
        default=0,
        comment="Number of samples used to build baseline"
    )

    last_updated = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('org_id', 'user_id', name='uq_user_baseline_org_user'),
    )

    def __repr__(self):
        return f"<UserBaseline user={self.user_id} samples={self.sample_count}>"
