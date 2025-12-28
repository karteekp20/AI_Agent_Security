"""
Organization Schemas - Request and Response Models
Pydantic models for organization management endpoints
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


# Organization Schemas

class OrganizationBase(BaseModel):
    """Base organization fields"""
    org_name: str
    subscription_tier: str = "free"
    subscription_status: str = "active"


class OrganizationResponse(BaseModel):
    """Organization response"""
    org_id: UUID
    org_name: str
    org_slug: str
    subscription_tier: str
    subscription_status: str
    current_users: int
    max_users: int
    api_requests_this_month: int
    max_api_requests_per_month: int
    storage_used_mb: float
    max_storage_mb: int
    created_at: datetime

    class Config:
        from_attributes = True


class OrganizationUpdateRequest(BaseModel):
    """Update organization settings"""
    org_name: Optional[str] = None
    billing_email: Optional[str] = None
    settings: Optional[dict] = None


class OrganizationStatsResponse(BaseModel):
    """Organization usage statistics"""
    org_id: UUID
    current_users: int
    max_users: int
    users_percentage: float
    api_requests_this_month: int
    max_api_requests_per_month: int
    api_requests_percentage: float
    storage_used_mb: float
    max_storage_mb: int
    storage_percentage: float
    is_within_limits: bool


# User Management Schemas

class UserResponse(BaseModel):
    """User response (for organization user list)"""
    user_id: UUID
    email: str
    full_name: Optional[str]
    role: str
    permissions: List[str] = []
    is_active: bool
    email_verified: bool
    last_login_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class InviteUserRequest(BaseModel):
    """Invite user to organization"""
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., description="Full name")
    role: str = Field(default="member", description="Role: owner, admin, member, viewer, auditor")
    permissions: List[str] = Field(default=[], description="Additional permissions")

    class Config:
        schema_extra = {
            "example": {
                "email": "newuser@example.com",
                "full_name": "Jane Doe",
                "role": "member",
                "permissions": ["policies:write"]
            }
        }


class InviteUserResponse(BaseModel):
    """Invite user response"""
    user_id: UUID
    email: str
    full_name: str
    role: str
    temporary_password: str  # Only shown once
    message: str = "User invited successfully. Send them the temporary password."


class UpdateUserRequest(BaseModel):
    """Update user role and permissions"""
    role: Optional[str] = Field(None, description="Role: owner, admin, member, viewer, auditor")
    permissions: Optional[List[str]] = Field(None, description="Permissions list")
    is_active: Optional[bool] = Field(None, description="Active status")


class UserListResponse(BaseModel):
    """List of users in organization"""
    users: List[UserResponse]
    total: int
    org_id: UUID
