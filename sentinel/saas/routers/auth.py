"""
Authentication Router - User Registration, Login, Token Refresh
FastAPI endpoints for authentication
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_user
from ..schemas import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    CurrentUser,
)
from ..auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from ..models import User, Organization, Workspace


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register new user and create organization

    Creates:
    - New organization with free tier subscription
    - First user as owner
    - Default workspace (production)
    - Returns JWT access and refresh tokens

    **Flow:**
    1. Check if email already exists
    2. Create organization with unique slug
    3. Create owner user with hashed password
    4. Create default workspace
    5. Generate JWT tokens
    6. Return user and org data with tokens

    **Request Body:**
    ```json
    {
      "email": "user@example.com",
      "password": "SecurePass123",
      "full_name": "John Doe",
      "org_name": "Acme Corp"
    }
    ```

    **Response:**
    ```json
    {
      "user_id": "550e8400-...",
      "email": "user@example.com",
      "full_name": "John Doe",
      "org_id": "660e8400-...",
      "org_name": "Acme Corp",
      "org_slug": "acme-corp",
      "workspace_id": "770e8400-...",
      "access_token": "eyJ...",
      "refresh_token": "eyJ...",
      "token_type": "bearer"
    }
    ```
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create organization slug from name
    org_slug = request.org_name.lower().replace(" ", "-").replace("_", "-")
    org_slug = "".join(c for c in org_slug if c.isalnum() or c == "-")

    # Check if org slug exists, append number if needed
    base_slug = org_slug
    counter = 1
    while db.query(Organization).filter(Organization.org_slug == org_slug).first():
        org_slug = f"{base_slug}-{counter}"
        counter += 1

    # Create organization
    org = Organization(
        org_id=uuid.uuid4(),
        org_name=request.org_name,
        org_slug=org_slug,
        subscription_tier="free",
        subscription_status="active",
        current_users=1,
    )
    db.add(org)
    db.flush()  # Get org_id without committing

    # Create owner user
    user = User(
        user_id=uuid.uuid4(),
        org_id=org.org_id,
        email=request.email,
        password_hash=hash_password(request.password),
        full_name=request.full_name,
        role="owner",
        is_active=True,
        email_verified=False,  # TODO: Send verification email
    )
    db.add(user)
    db.flush()

    # Create default workspace
    workspace = Workspace(
        workspace_id=uuid.uuid4(),
        org_id=org.org_id,
        workspace_name="Default",
        workspace_slug="default",
        environment="production",
        created_by=user.user_id,
    )
    db.add(workspace)

    # Commit all changes
    db.commit()
    db.refresh(user)
    db.refresh(org)
    db.refresh(workspace)

    # Generate JWT tokens
    access_token = create_access_token(
        user_id=user.user_id,
        org_id=user.org_id,
        email=user.email,
        role=user.role,
    )
    refresh_token = create_refresh_token(
        user_id=user.user_id,
        org_id=user.org_id,
        email=user.email,
        role=user.role,
    )

    return RegisterResponse(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        org_id=org.org_id,
        org_name=org.org_name,
        org_slug=org.org_slug,
        workspace_id=workspace.workspace_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    User login with email and password

    **Flow:**
    1. Look up user by email
    2. Verify password hash
    3. Check user is active
    4. Update last_login_at
    5. Generate JWT tokens
    6. Return user data with tokens

    **Request Body:**
    ```json
    {
      "email": "user@example.com",
      "password": "SecurePass123"
    }
    ```

    **Response:**
    ```json
    {
      "user_id": "550e8400-...",
      "email": "user@example.com",
      "full_name": "John Doe",
      "role": "owner",
      "org_id": "660e8400-...",
      "org_name": "Acme Corp",
      "access_token": "eyJ...",
      "refresh_token": "eyJ...",
      "token_type": "bearer"
    }
    ```
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()

    # Verify user exists and password is correct
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Check user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Get organization
    org = db.query(Organization).filter(Organization.org_id == user.org_id).first()
    if not org or not org.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is suspended or inactive",
        )

    # Update last login timestamp
    user.last_login_at = datetime.utcnow()
    db.commit()

    # Generate JWT tokens
    access_token = create_access_token(
        user_id=user.user_id,
        org_id=user.org_id,
        email=user.email,
        role=user.role,
    )
    refresh_token = create_refresh_token(
        user_id=user.user_id,
        org_id=user.org_id,
        email=user.email,
        role=user.role,
    )

    return LoginResponse(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        org_id=org.org_id,
        org_name=org.org_name,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=RefreshTokenResponse)
def refresh_token_endpoint(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token

    **Flow:**
    1. Verify refresh token is valid
    2. Extract user data from token
    3. Generate new access token
    4. Return new access token

    **Request Body:**
    ```json
    {
      "refresh_token": "eyJ..."
    }
    ```

    **Response:**
    ```json
    {
      "access_token": "eyJ...",
      "token_type": "bearer"
    }
    ```
    """
    try:
        # Verify refresh token
        token_data = verify_token(request.refresh_token, expected_type="refresh")

        # Generate new access token
        new_access_token = create_access_token(
            user_id=uuid.UUID(token_data.user_id),
            org_id=uuid.UUID(token_data.org_id),
            email=token_data.email,
            role=token_data.role,
        )

        return RefreshTokenResponse(access_token=new_access_token)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )


@router.get("/me", response_model=CurrentUser)
def get_current_user_info(current_user: CurrentUser = Depends(get_current_user)):
    """
    Get current authenticated user information

    Requires: Bearer token in Authorization header

    **Headers:**
    ```
    Authorization: Bearer eyJ...
    ```

    **Response:**
    ```json
    {
      "user_id": "550e8400-...",
      "email": "user@example.com",
      "full_name": "John Doe",
      "role": "owner",
      "org_id": "660e8400-...",
      "permissions": []
    }
    ```
    """
    return current_user
