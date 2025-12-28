"""
Audit Log Schemas - Request/Response Models
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class AuditLogResponse(BaseModel):
    """Audit log entry"""
    id: int
    timestamp: datetime
    session_id: str
    request_id: Optional[str]
    org_id: Optional[str]
    workspace_id: Optional[str]
    user_id: Optional[str]
    user_role: Optional[str]
    ip_address: Optional[str]
    user_input: str
    input_length: int
    blocked: bool
    risk_score: Optional[float]
    risk_level: Optional[str]
    pii_detected: bool
    pii_entities: Optional[list]
    redacted_count: int
    injection_detected: bool
    injection_type: Optional[str]
    injection_confidence: Optional[float]
    escalated: bool
    escalated_to: Optional[str]
    metadata: Optional[dict]

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """List of audit logs with pagination"""
    logs: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
