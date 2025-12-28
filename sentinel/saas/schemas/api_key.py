"""
API Key Schemas - Request/Response Models
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class CreateAPIKeyRequest(BaseModel):
    """Request to create a new API key"""
    key_name: str = Field(..., description="User-friendly name for the key")
    workspace_id: Optional[UUID] = Field(None, description="Workspace scope (optional)")
    scopes: List[str] = Field(["process"], description="Allowed endpoints")
    rate_limit_per_minute: int = Field(60, ge=1, le=1000)
    rate_limit_per_hour: int = Field(1000, ge=1, le=100000)
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date")


class UpdateAPIKeyRequest(BaseModel):
    """Request to update an existing API key"""
    key_name: Optional[str] = None
    scopes: Optional[List[str]] = None
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=1000)
    rate_limit_per_hour: Optional[int] = Field(None, ge=1, le=100000)
    is_active: Optional[bool] = None


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class APIKeyResponse(BaseModel):
    """API key information (without the actual key)"""
    key_id: UUID
    org_id: UUID
    workspace_id: Optional[UUID]
    key_prefix: str  # e.g., "sk_live_abc..."
    key_name: Optional[str]
    scopes: List[str]
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    is_active: bool
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_by: Optional[UUID]
    created_at: datetime
    revoked_at: Optional[datetime]

    class Config:
        from_attributes = True


class CreatedAPIKeyResponse(BaseModel):
    """Response when creating a new API key (includes the full key once)"""
    key_id: UUID
    api_key: str  # Full key shown ONCE (sk_live_abc123xyz...)
    key_prefix: str
    key_name: Optional[str]
    org_id: UUID
    workspace_id: Optional[UUID]
    scopes: List[str]
    created_at: datetime
    warning: str = "Store this API key securely. You won't be able to see it again."


class APIKeyListResponse(BaseModel):
    """List of API keys"""
    api_keys: List[APIKeyResponse]
    total: int
