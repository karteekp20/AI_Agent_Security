"""
Policy Schemas - Request/Response Models
"""

from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class CreatePolicyRequest(BaseModel):
    """Create new security policy"""
    policy_name: str = Field(..., min_length=3, max_length=255)
    policy_type: str = Field(..., description="pii, injection, profanity, custom")
    pattern_value: str = Field(..., description="Regex pattern or keyword")
    action: str = Field(default="block", description="block, redact, flag")
    severity: str = Field(default="medium", description="low, medium, high, critical")
    description: Optional[str] = None
    workspace_id: Optional[UUID] = None  # Optional: workspace-specific policy
    is_active: bool = Field(default=True)
    test_percentage: int = Field(default=0, ge=0, le=100, description="Canary rollout percentage")


class UpdatePolicyRequest(BaseModel):
    """Update existing policy"""
    policy_name: Optional[str] = Field(None, min_length=3, max_length=255)
    pattern_value: Optional[str] = None
    action: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    test_percentage: Optional[int] = Field(None, ge=0, le=100)


class TestPolicyRequest(BaseModel):
    """Test policy against sample input"""
    test_input: str = Field(..., description="Sample text to test policy against")


class DeployPolicyRequest(BaseModel):
    """Deploy policy with canary rollout"""
    test_percentage: int = Field(..., ge=0, le=100, description="Percentage of traffic to apply policy")
    description: Optional[str] = Field(None, description="Deployment notes")


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class PolicyResponse(BaseModel):
    """Policy details response"""
    policy_id: UUID
    org_id: UUID
    workspace_id: Optional[UUID]
    policy_name: str
    policy_type: str
    pattern_value: str
    action: str
    severity: str
    description: Optional[str]
    is_active: bool
    test_percentage: int

    # Metrics
    triggered_count: int
    false_positive_count: int

    # Versioning
    version: int
    parent_policy_id: Optional[UUID]

    # Timestamps
    created_at: datetime
    updated_at: datetime
    deployed_at: Optional[datetime]

    class Config:
        from_attributes = True


class PolicyListResponse(BaseModel):
    """List of policies with pagination"""
    policies: list[PolicyResponse]
    total: int
    page: int
    page_size: int


class TestPolicyResponse(BaseModel):
    """Policy test result"""
    matched: bool
    match_details: Optional[dict] = None
    action_taken: str
    redacted_output: Optional[str] = None
    explanation: str


class DeployPolicyResponse(BaseModel):
    """Policy deployment result"""
    policy_id: UUID
    test_percentage: int
    deployed_at: datetime
    message: str
