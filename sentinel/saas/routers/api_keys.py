"""
API Keys Management Router
CRUD operations for API key management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from uuid import UUID
import secrets
import hashlib

from ..dependencies import get_db, get_current_user
from ..models import User, APIKey, Workspace
from ..schemas.api_key import (
    CreateAPIKeyRequest,
    UpdateAPIKeyRequest,
    APIKeyResponse,
    CreatedAPIKeyResponse,
    APIKeyListResponse,
)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_api_key(prefix: str = "sk_live") -> tuple[str, str, str]:
    """
    Generate a secure API key with prefix

    Returns:
        tuple: (full_key, key_hash, key_prefix)
        - full_key: sk_live_abc123xyz... (show once)
        - key_hash: SHA-256 hash for storage
        - key_prefix: sk_live_abc... (for UI display)
    """
    # Generate 32 bytes of random data (256 bits)
    random_part = secrets.token_urlsafe(32)

    # Create full key
    full_key = f"{prefix}_{random_part}"

    # Create SHA-256 hash
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()

    # Create display prefix (first 15 characters)
    key_prefix = full_key[:15] + "..."

    return full_key, key_hash, key_prefix


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("", response_model=CreatedAPIKeyResponse, status_code=201)
async def create_api_key(
    request: CreateAPIKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a new API key

    **IMPORTANT:** The full API key is returned ONCE in this response.
    Store it securely - you won't be able to retrieve it again.

    **Request Body:**
    ```json
    {
      "key_name": "Production API Key",
      "workspace_id": "770e8400-...",
      "scopes": ["process", "metrics"],
      "rate_limit_per_minute": 100,
      "rate_limit_per_hour": 5000
    }
    ```

    **Response:**
    ```json
    {
      "key_id": "880e8400-...",
      "api_key": "sk_live_abc123xyz...",
      "key_prefix": "sk_live_abc...",
      "key_name": "Production API Key",
      "org_id": "660e8400-...",
      "workspace_id": "770e8400-...",
      "scopes": ["process", "metrics"],
      "created_at": "2024-01-15T10:30:00Z",
      "warning": "Store this API key securely. You won't be able to see it again."
    }
    ```
    """
    # Validate workspace belongs to user's org (if specified)
    if request.workspace_id:
        workspace = db.query(Workspace).filter(
            Workspace.workspace_id == request.workspace_id,
            Workspace.org_id == current_user.org_id,
            Workspace.deleted_at.is_(None),
        ).first()

        if not workspace:
            raise HTTPException(
                status_code=404,
                detail="Workspace not found or does not belong to your organization"
            )

    # Generate API key
    full_key, key_hash, key_prefix = generate_api_key()

    # Create database record
    api_key = APIKey(
        org_id=current_user.org_id,
        workspace_id=request.workspace_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        key_name=request.key_name,
        scopes=request.scopes,
        rate_limit_per_minute=request.rate_limit_per_minute,
        rate_limit_per_hour=request.rate_limit_per_hour,
        expires_at=request.expires_at,
        created_by=current_user.user_id,
        is_active=True,
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    # Return full key ONCE
    return CreatedAPIKeyResponse(
        key_id=api_key.key_id,
        api_key=full_key,  # Full key shown once
        key_prefix=api_key.key_prefix,
        key_name=api_key.key_name,
        org_id=api_key.org_id,
        workspace_id=api_key.workspace_id,
        scopes=api_key.scopes,
        created_at=api_key.created_at,
    )


@router.get("", response_model=APIKeyListResponse)
async def list_api_keys(
    workspace_id: Optional[UUID] = Query(None, description="Filter by workspace"),
    include_revoked: bool = Query(False, description="Include revoked keys"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all API keys for the current organization

    **Query Parameters:**
    - `workspace_id`: Filter by workspace (optional)
    - `include_revoked`: Include revoked keys (default: false)

    **Response:**
    ```json
    {
      "api_keys": [
        {
          "key_id": "880e8400-...",
          "org_id": "660e8400-...",
          "workspace_id": "770e8400-...",
          "key_prefix": "sk_live_abc...",
          "key_name": "Production API Key",
          "scopes": ["process"],
          "rate_limit_per_minute": 60,
          "is_active": true,
          "last_used_at": "2024-01-15T10:30:00Z",
          "created_at": "2024-01-10T08:00:00Z"
        }
      ],
      "total": 1
    }
    ```
    """
    # Build query
    query = db.query(APIKey).filter(APIKey.org_id == current_user.org_id)

    # Filter by workspace if specified
    if workspace_id:
        query = query.filter(APIKey.workspace_id == workspace_id)

    # Exclude revoked keys unless requested
    if not include_revoked:
        query = query.filter(APIKey.revoked_at.is_(None))

    # Order by created_at descending
    query = query.order_by(APIKey.created_at.desc())

    # Execute
    api_keys = query.all()

    return APIKeyListResponse(
        api_keys=[APIKeyResponse.model_validate(key) for key in api_keys],
        total=len(api_keys),
    )


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get details of a specific API key"""
    api_key = db.query(APIKey).filter(
        APIKey.key_id == key_id,
        APIKey.org_id == current_user.org_id,
    ).first()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    return APIKeyResponse.model_validate(api_key)


@router.patch("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: UUID,
    request: UpdateAPIKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update API key metadata

    **Note:** You cannot change the actual key value or org/workspace.
    Only metadata (name, scopes, rate limits, active status) can be updated.

    **Request Body:**
    ```json
    {
      "key_name": "Updated Production Key",
      "scopes": ["process", "metrics", "reports"],
      "rate_limit_per_minute": 120,
      "is_active": false
    }
    ```
    """
    # Find API key
    api_key = db.query(APIKey).filter(
        APIKey.key_id == key_id,
        APIKey.org_id == current_user.org_id,
    ).first()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    # Prevent updating revoked keys
    if api_key.revoked_at:
        raise HTTPException(status_code=400, detail="Cannot update revoked API key")

    # Update fields
    if request.key_name is not None:
        api_key.key_name = request.key_name

    if request.scopes is not None:
        api_key.scopes = request.scopes

    if request.rate_limit_per_minute is not None:
        api_key.rate_limit_per_minute = request.rate_limit_per_minute

    if request.rate_limit_per_hour is not None:
        api_key.rate_limit_per_hour = request.rate_limit_per_hour

    if request.is_active is not None:
        api_key.is_active = request.is_active

    db.commit()
    db.refresh(api_key)

    return APIKeyResponse.model_validate(api_key)


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke (soft delete) an API key

    **Effect:** The API key will be permanently disabled and cannot be used.
    The record is kept for audit purposes with `revoked_at` timestamp.

    **Response:** 204 No Content (successful deletion)
    """
    # Find API key
    api_key = db.query(APIKey).filter(
        APIKey.key_id == key_id,
        APIKey.org_id == current_user.org_id,
    ).first()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    # Check if already revoked
    if api_key.revoked_at:
        raise HTTPException(status_code=400, detail="API key already revoked")

    # Soft delete (revoke)
    api_key.revoked_at = datetime.utcnow()
    api_key.is_active = False

    db.commit()

    # Return 204 No Content
    return None
