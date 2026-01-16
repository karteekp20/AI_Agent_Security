"""
Audit Log Schemas - Request/Response Models
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============================================================================
# THREAT DETAILS SCHEMAS
# ============================================================================

class PIIEntityDetail(BaseModel):
    """Detailed PII entity information for display"""
    entity_type: str
    masked_value: Optional[str] = None  # Only for admin/owner users
    redaction_strategy: str
    start_position: int
    end_position: int
    confidence: float
    detection_method: str
    token_id: str


class InjectionDetail(BaseModel):
    """Injection attempt details"""
    injection_type: str
    confidence: float
    matched_patterns: List[str] = Field(default_factory=list)
    severity: str


class ContentViolationDetail(BaseModel):
    """Content policy violations"""
    violation_type: str
    matched_terms: List[str] = Field(default_factory=list)
    severity: str


class ThreatDetails(BaseModel):
    """Complete threat information structure"""
    pii: List[PIIEntityDetail] = Field(default_factory=list)
    injections: List[InjectionDetail] = Field(default_factory=list)
    content_violations: List[ContentViolationDetail] = Field(default_factory=list)
    total_threat_count: int = 0
    blocking_reasons: List[str] = Field(default_factory=list)


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
    threat_details: Optional[ThreatDetails] = None

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """List of audit logs with pagination"""
    logs: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
