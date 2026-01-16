"""
Authentication Schemas - Request and Response Models
Pydantic models for authentication endpoints
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator
from uuid import UUID


# Registration Schemas

class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    full_name: str = Field(..., min_length=1, description="Full name")
    org_name: str = Field(..., min_length=1, description="Organization name")

    @validator("password")
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class RegisterResponse(BaseModel):
    """User registration response"""
    user_id: UUID
    email: str
    full_name: str
    org_id: UUID
    org_name: str
    org_slug: str
    workspace_id: UUID
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# Login Schemas

class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    """User login response"""
    user_id: UUID
    email: str
    full_name: Optional[str]
    role: str
    org_id: UUID
    org_name: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    password_change_required: bool = False


# Token Refresh Schemas

class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str = Field(..., description="Valid refresh token")


class RefreshTokenResponse(BaseModel):
    """Refresh token response"""
    access_token: str
    token_type: str = "bearer"


# Error Response Schema

class AuthError(BaseModel):
    """Authentication error response"""
    detail: str
    error_code: Optional[str] = None


# Current User Schema (for authenticated endpoints)

class CurrentUser(BaseModel):
    """Current authenticated user"""
    user_id: UUID
    email: str
    full_name: Optional[str]
    role: str
    org_id: UUID
    workspace_id: Optional[UUID] = None
    permissions: list = []

    class Config:
        from_attributes = True  # Allow ORM model conversion


# Password Change Schemas

class ChangePasswordRequest(BaseModel):
    """Password change request"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")
    confirm_password: str = Field(..., description="Confirm new password")

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        """Validate that new password and confirmation match"""
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("Passwords do not match")
        return v

    @validator("new_password")
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class ChangePasswordResponse(BaseModel):
    """Password change response"""
    success: bool = True
    message: str = "Password changed successfully"
