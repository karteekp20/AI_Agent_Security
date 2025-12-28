"""
Database models (stub for future implementation)
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
from datetime import datetime

Base = declarative_base()

class Report(Base):
    """Report model stub"""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String, unique=True, index=True)
    organization_id = Column(String, index=True)
    workspace_id = Column(String, index=True)
    report_type = Column(String)
    status = Column(String, default="pending")
    file_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata = Column(JSON, default={})
