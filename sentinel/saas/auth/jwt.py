"""
JWT Token Management - Access and Refresh Tokens
Secure token generation and validation using jose library
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
import os

from jose import JWTError, jwt
from pydantic import BaseModel


# JWT Configuration
# Load from environment variables
SECRET_KEY = os.getenv("JWT_SECRET_KEY")

# Validate secret key
if not SECRET_KEY:
    raise ValueError(
        "JWT_SECRET_KEY environment variable not set. Generate a secure key with:\n"
        "python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )

if len(SECRET_KEY) < 32:
    raise ValueError(
        "JWT_SECRET_KEY must be at least 32 characters for security. "
        "Current length: {}".format(len(SECRET_KEY))
    )

# Support key rotation (optional previous key for validating old tokens)
SECRET_KEY_PREVIOUS = os.getenv("JWT_SECRET_KEY_PREVIOUS")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))


class TokenData(BaseModel):
    """
    Token payload data model
    Contains user and organization information
    """
    user_id: str
    org_id: str
    email: str
    role: str
    token_type: str  # "access" or "refresh"


def create_access_token(
    user_id: UUID,
    org_id: UUID,
    email: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token (short-lived, 15 minutes)

    Args:
        user_id: User UUID
        org_id: Organization UUID
        email: User email
        role: User role (owner, admin, member, viewer, auditor)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_access_token(
        ...     user_id=UUID("..."),
        ...     org_id=UUID("..."),
        ...     email="user@example.com",
        ...     role="admin"
        ... )
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "user_id": str(user_id),
        "org_id": str(org_id),
        "email": email,
        "role": role,
        "token_type": "access",
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    user_id: UUID,
    org_id: UUID,
    email: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT refresh token (long-lived, 7 days)

    Refresh tokens are used to obtain new access tokens without re-authenticating.
    They have a longer expiration time than access tokens.

    Args:
        user_id: User UUID
        org_id: Organization UUID
        email: User email
        role: User role
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string

    Example:
        >>> refresh_token = create_refresh_token(
        ...     user_id=UUID("..."),
        ...     org_id=UUID("..."),
        ...     email="user@example.com",
        ...     role="admin"
        ... )
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "user_id": str(user_id),
        "org_id": str(org_id),
        "email": email,
        "role": role,
        "token_type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode JWT token and return payload

    Args:
        token: Encoded JWT token string

    Returns:
        Decoded token payload as dictionary

    Raises:
        JWTError: If token is invalid, expired, or malformed

    Example:
        >>> payload = decode_token(token)
        >>> print(payload["user_id"])
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise JWTError(f"Invalid token: {str(e)}")


def verify_token(token: str, expected_type: str = "access") -> TokenData:
    """
    Verify JWT token and return TokenData

    Validates token signature, expiration, and type.

    Args:
        token: Encoded JWT token string
        expected_type: Expected token type ("access" or "refresh")

    Returns:
        TokenData object with user information

    Raises:
        JWTError: If token is invalid, expired, or wrong type
        ValueError: If token payload is missing required fields

    Example:
        >>> try:
        ...     token_data = verify_token(access_token, expected_type="access")
        ...     print(f"User: {token_data.email}, Role: {token_data.role}")
        ... except JWTError:
        ...     print("Invalid token")
    """
    try:
        payload = decode_token(token)

        # Validate required fields
        user_id: str = payload.get("user_id")
        org_id: str = payload.get("org_id")
        email: str = payload.get("email")
        role: str = payload.get("role")
        token_type: str = payload.get("token_type")

        if not all([user_id, org_id, email, role, token_type]):
            raise ValueError("Token payload missing required fields")

        # Validate token type
        if token_type != expected_type:
            raise ValueError(f"Expected {expected_type} token, got {token_type}")

        return TokenData(
            user_id=user_id,
            org_id=org_id,
            email=email,
            role=role,
            token_type=token_type,
        )

    except JWTError as e:
        raise JWTError(f"Token verification failed: {str(e)}")
    except (KeyError, ValueError) as e:
        raise ValueError(f"Invalid token payload: {str(e)}")


def refresh_access_token(refresh_token: str) -> str:
    """
    Generate new access token from refresh token

    Args:
        refresh_token: Valid refresh token

    Returns:
        New access token string

    Raises:
        JWTError: If refresh token is invalid or expired

    Example:
        >>> new_access_token = refresh_access_token(refresh_token)
    """
    # Verify refresh token
    token_data = verify_token(refresh_token, expected_type="refresh")

    # Create new access token with same user data
    new_access_token = create_access_token(
        user_id=UUID(token_data.user_id),
        org_id=UUID(token_data.org_id),
        email=token_data.email,
        role=token_data.role,
    )

    return new_access_token
