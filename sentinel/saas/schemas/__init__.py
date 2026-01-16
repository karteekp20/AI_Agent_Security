"""
Pydantic Schemas for SaaS API
Request and response models for all API endpoints
"""

from .auth import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    AuthError,
    CurrentUser,
    ChangePasswordRequest,
    ChangePasswordResponse,
)
from .organization import (
    OrganizationResponse,
    OrganizationUpdateRequest,
    OrganizationStatsResponse,
    UserResponse,
    InviteUserRequest,
    InviteUserResponse,
    UpdateUserRequest,
    UserListResponse,
)
from .workspace import (
    CreateWorkspaceRequest,
    WorkspaceResponse,
    UpdateWorkspaceRequest,
    WorkspaceListResponse,
)

__all__ = [
    # Auth
    "RegisterRequest",
    "RegisterResponse",
    "LoginRequest",
    "LoginResponse",
    "RefreshTokenRequest",
    "RefreshTokenResponse",
    "AuthError",
    "CurrentUser",
    "ChangePasswordRequest",
    "ChangePasswordResponse",
    # Organization
    "OrganizationResponse",
    "OrganizationUpdateRequest",
    "OrganizationStatsResponse",
    "UserResponse",
    "InviteUserRequest",
    "InviteUserResponse",
    "UpdateUserRequest",
    "UserListResponse",
    # Workspace
    "CreateWorkspaceRequest",
    "WorkspaceResponse",
    "UpdateWorkspaceRequest",
    "WorkspaceListResponse",
]
