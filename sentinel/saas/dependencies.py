"""
FastAPI Dependencies
Database sessions, authentication, and authorization dependencies
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from jose import JWTError

from .config import config
from .auth import verify_token, TokenData, APIKeyValidator
from .models import User, Organization
from .schemas import CurrentUser


# Database Setup
engine = create_engine(
    config.database.url,
    pool_size=config.database.pool_size,
    max_overflow=config.database.max_overflow,
    echo=config.database.echo,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Database Session Dependency
def get_db() -> Generator[Session, None, None]:
    """
    Provide database session to route handlers

    Usage:
        @router.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Authentication Dependencies

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """
    Get current authenticated user from JWT token

    Extracts Bearer token from Authorization header and validates it.

    Args:
        authorization: Authorization header (Bearer {token})
        db: Database session

    Returns:
        CurrentUser object

    Raises:
        HTTPException: 401 if token is invalid or missing

    Usage:
        @router.get("/me")
        def get_me(current_user: CurrentUser = Depends(get_current_user)):
            return current_user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not authorization:
        raise credentials_exception

    # Extract token from "Bearer {token}" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise credentials_exception

    token = parts[1]

    # Verify JWT token
    try:
        token_data: TokenData = verify_token(token, expected_type="access")
    except (JWTError, ValueError):
        raise credentials_exception

    # Get user from database
    user = db.query(User).filter(User.user_id == token_data.user_id).first()
    if not user or not user.is_active:
        raise credentials_exception

    # Return current user data
    return CurrentUser(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        org_id=user.org_id,
        permissions=user.permissions or [],
    )


async def get_current_active_org(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Organization:
    """
    Get current user's organization and verify it's active

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Organization object

    Raises:
        HTTPException: 403 if organization is inactive or suspended

    Usage:
        @router.get("/org")
        def get_org(org: Organization = Depends(get_current_active_org)):
            return org
    """
    org = db.query(Organization).filter(Organization.org_id == current_user.org_id).first()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    if not org.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is suspended or inactive",
        )

    return org


# API Key Authentication Dependency

async def get_api_key_user(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Authenticate using API key from X-API-Key header

    Args:
        x_api_key: API key from X-API-Key header
        db: Database session

    Returns:
        Dictionary with API key metadata

    Raises:
        HTTPException: 401 if API key is invalid

    Usage:
        @router.post("/process")
        def process(
            request: ProcessRequest,
            api_key_data: dict = Depends(get_api_key_user)
        ):
            org_id = api_key_data["org_id"]
            ...
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    validator = APIKeyValidator(db)
    key_data = validator.validate_api_key(x_api_key)

    if not key_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return key_data


# Permission Check Dependency Factory

def require_permission(required_permission: str):
    """
    Dependency factory for permission checking

    Args:
        required_permission: Permission string (e.g., "policies:write")

    Returns:
        Dependency function

    Usage:
        @router.post("/policies", dependencies=[Depends(require_permission("policies:write"))])
        def create_policy(...):
            ...
    """
    async def permission_checker(current_user: CurrentUser = Depends(get_current_user)):
        # Owner and admin have all permissions
        if current_user.role in ("owner", "admin"):
            return current_user

        # Check specific permission
        if required_permission not in current_user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {required_permission}",
            )

        return current_user

    return permission_checker


# Role Check Dependency Factory

def require_role(*allowed_roles: str):
    """
    Dependency factory for role checking

    Args:
        allowed_roles: Tuple of allowed roles

    Returns:
        Dependency function

    Usage:
        @router.delete("/users/{user_id}", dependencies=[Depends(require_role("owner", "admin"))])
        def delete_user(...):
            ...
    """
    async def role_checker(current_user: CurrentUser = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {', '.join(allowed_roles)}",
            )

        return current_user

    return role_checker
