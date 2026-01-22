"""ML Model Metadata Storage"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from . import Base


class MLModel(Base):
    """Stores ML model metadata and versions"""
    __tablename__ = "ml_models"

    model_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    model_type = Column(
        String(50),
        nullable=False,
        comment="anomaly_detection, behavioral, autoencoder"
    )
    model_version = Column(Integer, nullable=False, default=1)
    model_path = Column(
        String(500),
        nullable=False,
        comment="S3 or local path to model file"
    )

    metrics = Column(JSONB, nullable=True, comment="Training metrics, accuracy, etc.")
    feature_names = Column(JSONB, nullable=True, comment="List of feature names used")

    status = Column(
        String(20),
        default="training",
        comment="training, active, archived"
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<MLModel {self.model_type} v{self.model_version} ({self.status})>"
