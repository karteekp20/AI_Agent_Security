"""
Organization Management Router - Organization and User Management
FastAPI endpoints for organization settings and user management
"""

import secrets
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..dependencies import (
    get_db,
    get_current_user,
    get_current_active_org,
    require_role,
)
from ..schemas import (
    CurrentUser,
    OrganizationResponse,
    OrganizationUpdateRequest,
    OrganizationStatsResponse,
    UserResponse,
    UserListResponse,
    InviteUserRequest,
    InviteUserResponse,
    UpdateUserRequest,
)
from ..auth import hash_password
from ..models import User, Organization


router = APIRouter(prefix="/orgs", tags=["Organizations"])


@router.get("/me", response_model=OrganizationResponse)
def get_my_organization(
    org: Organization = Depends(get_current_active_org),
):
    """
    Get current user's organization details

    Returns organization information including subscription tier,
    usage limits, and current usage.

    **Response:**
    ```json
    {
      "org_id": "660e8400-...",
      "org_name": "Acme Corp",
      "org_slug": "acme-corp",
      "subscription_tier": "pro",
      "subscription_status": "active",
      "current_users": 5,
      "max_users": 10,
      "api_requests_this_month": 15000,
      "max_api_requests_per_month": 100000,
      "storage_used_mb": 250.5,
      "max_storage_mb": 5000,
      "created_at": "2024-01-15T10:30:00Z"
    }
    ```
    """
    return org


@router.patch("/me", response_model=OrganizationResponse)
def update_my_organization(
    request: OrganizationUpdateRequest,
    current_user: CurrentUser = Depends(require_role("owner", "admin")),
    org: Organization = Depends(get_current_active_org),
    db: Session = Depends(get_db),
):
    """
    Update organization settings

    Requires: owner or admin role

    **Request Body:**
    ```json
    {
      "org_name": "New Acme Corp",
      "billing_email": "billing@acme.com",
      "settings": {
        "enable_sso": true,
        "custom_domain": "acme.sentinel.ai"
      }
    }
    ```
    """
    # Update fields if provided
    if request.org_name is not None:
        org.org_name = request.org_name

    if request.billing_email is not None:
        org.billing_email = request.billing_email

    if request.settings is not None:
        org.settings = request.settings

    db.commit()
    db.refresh(org)

    return org


@router.get("/me/stats", response_model=OrganizationStatsResponse)
def get_organization_stats(
    org: Organization = Depends(get_current_active_org),
):
    """
    Get organization usage statistics

    Returns current usage vs limits for users, API requests, and storage.

    **Response:**
    ```json
    {
      "org_id": "660e8400-...",
      "current_users": 5,
      "max_users": 10,
      "users_percentage": 50.0,
      "api_requests_this_month": 15000,
      "max_api_requests_per_month": 100000,
      "api_requests_percentage": 15.0,
      "storage_used_mb": 250.5,
      "max_storage_mb": 5000,
      "storage_percentage": 5.01,
      "is_within_limits": true
    }
    ```
    """
    return OrganizationStatsResponse(
        org_id=org.org_id,
        current_users=org.current_users,
        max_users=org.max_users,
        users_percentage=(org.current_users / org.max_users * 100) if org.max_users > 0 else 0,
        api_requests_this_month=org.api_requests_this_month,
        max_api_requests_per_month=org.max_api_requests_per_month,
        api_requests_percentage=(
            org.api_requests_this_month / org.max_api_requests_per_month * 100
            if org.max_api_requests_per_month > 0
            else 0
        ),
        storage_used_mb=org.storage_used_mb,
        max_storage_mb=org.max_storage_mb,
        storage_percentage=(org.storage_used_mb / org.max_storage_mb * 100) if org.max_storage_mb > 0 else 0,
        is_within_limits=org.is_within_limits,
    )


# User Management Endpoints

@router.get("/me/users", response_model=UserListResponse)
def list_organization_users(
    current_user: CurrentUser = Depends(get_current_user),
    org: Organization = Depends(get_current_active_org),
    db: Session = Depends(get_db),
):
    """
    List all users in organization

    Returns all users belonging to the current organization.

    **Response:**
    ```json
    {
      "users": [
        {
          "user_id": "550e8400-...",
          "email": "owner@acme.com",
          "full_name": "John Doe",
          "role": "owner",
          "permissions": [],
          "is_active": true,
          "email_verified": true,
          "last_login_at": "2024-01-20T15:30:00Z",
          "created_at": "2024-01-15T10:30:00Z"
        }
      ],
      "total": 5,
      "org_id": "660e8400-..."
    }
    ```
    """
    users = db.query(User).filter(User.org_id == org.org_id).all()

    return UserListResponse(
        users=users,
        total=len(users),
        org_id=org.org_id,
    )


@router.post("/me/users/invite", response_model=InviteUserResponse, status_code=status.HTTP_201_CREATED)
def invite_user_to_organization(
    request: InviteUserRequest,
    current_user: CurrentUser = Depends(require_role("owner", "admin")),
    org: Organization = Depends(get_current_active_org),
    db: Session = Depends(get_db),
):
    """
    Invite user to organization

    Creates a new user account with a temporary password.
    Requires: owner or admin role

    **Flow:**
    1. Check if organization is within user limits
    2. Check if email already exists
    3. Generate temporary password
    4. Create user account
    5. Send invitation email (TODO: implement email sending)
    6. Return temporary password (show once)

    **Request Body:**
    ```json
    {
      "email": "newuser@example.com",
      "full_name": "Jane Doe",
      "role": "member",
      "permissions": ["policies:write"]
    }
    ```

    **Response:**
    ```json
    {
      "user_id": "770e8400-...",
      "email": "newuser@example.com",
      "full_name": "Jane Doe",
      "role": "member",
      "temporary_password": "TempPass123!xyz",
      "message": "User invited successfully. Send them the temporary password."
    }
    ```
    """
    # Check organization user limit
    if org.current_users >= org.max_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Organization has reached maximum user limit ({org.max_users}). Please upgrade your plan.",
        )

    # Check if email already exists in organization
    existing_user = db.query(User).filter(
        User.org_id == org.org_id,
        User.email == request.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists in organization",
        )

    # Validate role
    valid_roles = ["owner", "admin", "member", "viewer", "auditor"]
    if request.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
        )

    # Generate temporary password (user should change on first login)
    temp_password = secrets.token_urlsafe(12)

    # Create user
    new_user = User(
        user_id=uuid.uuid4(),
        org_id=org.org_id,
        email=request.email,
        full_name=request.full_name,
        password_hash=hash_password(temp_password),
        role=request.role,
        permissions=request.permissions,
        is_active=True,
        email_verified=False,  # User needs to verify email
    )

    db.add(new_user)

    # Update organization user count
    org.current_users += 1

    db.commit()
    db.refresh(new_user)

    # TODO: Send invitation email with temporary password

    return InviteUserResponse(
        user_id=new_user.user_id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        temporary_password=temp_password,
    )


@router.get("/me/users/{user_id}", response_model=UserResponse)
def get_organization_user(
    user_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    org: Organization = Depends(get_current_active_org),
    db: Session = Depends(get_db),
):
    """
    Get user details

    Returns details of a specific user in the organization.
    """
    user = db.query(User).filter(
        User.user_id == user_id,
        User.org_id == org.org_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.patch("/me/users/{user_id}", response_model=UserResponse)
def update_organization_user(
    user_id: uuid.UUID,
    request: UpdateUserRequest,
    current_user: CurrentUser = Depends(require_role("owner", "admin")),
    org: Organization = Depends(get_current_active_org),
    db: Session = Depends(get_db),
):
    """
    Update user role and permissions

    Requires: owner or admin role

    **Request Body:**
    ```json
    {
      "role": "admin",
      "permissions": ["policies:write", "reports:generate"],
      "is_active": true
    }
    ```
    """
    user = db.query(User).filter(
        User.user_id == user_id,
        User.org_id == org.org_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent modifying self
    if user.user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify your own user account",
        )

    # Prevent non-owners from modifying owners
    if user.role == "owner" and current_user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can modify owner accounts",
        )

    # Update fields if provided
    if request.role is not None:
        valid_roles = ["owner", "admin", "member", "viewer", "auditor"]
        if request.role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
            )
        user.role = request.role

    if request.permissions is not None:
        user.permissions = request.permissions

    if request.is_active is not None:
        user.is_active = request.is_active

    db.commit()
    db.refresh(user)

    return user


@router.delete("/me/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user_from_organization(
    user_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_role("owner", "admin")),
    org: Organization = Depends(get_current_active_org),
    db: Session = Depends(get_db),
):
    """
    Remove user from organization

    Permanently deletes user account.
    Requires: owner or admin role

    **Note:** This action cannot be undone.
    """
    user = db.query(User).filter(
        User.user_id == user_id,
        User.org_id == org.org_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent deleting self
    if user.user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own user account",
        )

    # Prevent non-owners from deleting owners
    if user.role == "owner" and current_user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can delete owner accounts",
        )

    # Delete user (CASCADE will handle related records)
    db.delete(user)

    # Update organization user count
    org.current_users -= 1

    db.commit()

    return None
