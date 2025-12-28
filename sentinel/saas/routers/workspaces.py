"""
Workspace Management Router - Project/Environment Management
FastAPI endpoints for workspace CRUD operations
"""

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
    CreateWorkspaceRequest,
    WorkspaceResponse,
    UpdateWorkspaceRequest,
    WorkspaceListResponse,
)
from ..models import Workspace, Organization


router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.get("", response_model=WorkspaceListResponse)
def list_workspaces(
    current_user: CurrentUser = Depends(get_current_user),
    org: Organization = Depends(get_current_active_org),
    db: Session = Depends(get_db),
):
    """
    List all workspaces in organization

    Returns all workspaces for the current user's organization.

    **Response:**
    ```json
    {
      "workspaces": [
        {
          "workspace_id": "770e8400-...",
          "org_id": "660e8400-...",
          "workspace_name": "Production",
          "workspace_slug": "production",
          "description": "Production environment",
          "environment": "production",
          "config": {"enable_strict_mode": true},
          "created_by": "550e8400-...",
          "created_at": "2024-01-15T10:30:00Z",
          "updated_at": "2024-01-15T10:30:00Z"
        }
      ],
      "total": 3,
      "org_id": "660e8400-..."
    }
    ```
    """
    workspaces = db.query(Workspace).filter(Workspace.org_id == org.org_id).all()

    return WorkspaceListResponse(
        workspaces=workspaces,
        total=len(workspaces),
        org_id=org.org_id,
    )


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    request: CreateWorkspaceRequest,
    current_user: CurrentUser = Depends(require_role("owner", "admin")),
    org: Organization = Depends(get_current_active_org),
    db: Session = Depends(get_db),
):
    """
    Create new workspace

    Creates a new workspace (project or environment) within the organization.
    Requires: owner or admin role

    **Request Body:**
    ```json
    {
      "workspace_name": "Mobile App",
      "description": "Production mobile application workspace",
      "environment": "production",
      "config": {
        "enable_strict_mode": true,
        "block_threshold": 0.9
      }
    }
    ```

    **Response:**
    ```json
    {
      "workspace_id": "880e8400-...",
      "org_id": "660e8400-...",
      "workspace_name": "Mobile App",
      "workspace_slug": "mobile-app",
      "description": "Production mobile application workspace",
      "environment": "production",
      "config": {"enable_strict_mode": true, "block_threshold": 0.9},
      "created_by": "550e8400-...",
      "created_at": "2024-01-20T15:30:00Z",
      "updated_at": "2024-01-20T15:30:00Z"
    }
    ```
    """
    # Validate environment
    valid_environments = ["production", "staging", "development", "testing"]
    if request.environment not in valid_environments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid environment. Must be one of: {', '.join(valid_environments)}",
        )

    # Create workspace slug from name
    workspace_slug = request.workspace_name.lower().replace(" ", "-").replace("_", "-")
    workspace_slug = "".join(c for c in workspace_slug if c.isalnum() or c == "-")

    # Check if workspace slug exists in org, append number if needed
    base_slug = workspace_slug
    counter = 1
    while db.query(Workspace).filter(
        Workspace.org_id == org.org_id,
        Workspace.workspace_slug == workspace_slug
    ).first():
        workspace_slug = f"{base_slug}-{counter}"
        counter += 1

    # Create workspace
    workspace = Workspace(
        workspace_id=uuid.uuid4(),
        org_id=org.org_id,
        workspace_name=request.workspace_name,
        workspace_slug=workspace_slug,
        description=request.description,
        environment=request.environment,
        config=request.config or {},
        created_by=current_user.user_id,
    )

    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    return workspace


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(
    workspace_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    org: Organization = Depends(get_current_active_org),
    db: Session = Depends(get_db),
):
    """
    Get workspace details

    Returns details of a specific workspace.
    """
    workspace = db.query(Workspace).filter(
        Workspace.workspace_id == workspace_id,
        Workspace.org_id == org.org_id
    ).first()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    return workspace


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: uuid.UUID,
    request: UpdateWorkspaceRequest,
    current_user: CurrentUser = Depends(require_role("owner", "admin")),
    org: Organization = Depends(get_current_active_org),
    db: Session = Depends(get_db),
):
    """
    Update workspace

    Updates workspace name, description, environment, or config.
    Requires: owner or admin role

    **Request Body:**
    ```json
    {
      "workspace_name": "Mobile App - Production",
      "description": "Updated description",
      "environment": "production",
      "config": {
        "enable_strict_mode": true,
        "block_threshold": 0.95
      }
    }
    ```
    """
    workspace = db.query(Workspace).filter(
        Workspace.workspace_id == workspace_id,
        Workspace.org_id == org.org_id
    ).first()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Update fields if provided
    if request.workspace_name is not None:
        workspace.workspace_name = request.workspace_name

        # Update slug if name changed
        workspace_slug = request.workspace_name.lower().replace(" ", "-").replace("_", "-")
        workspace_slug = "".join(c for c in workspace_slug if c.isalnum() or c == "-")

        # Check if new slug conflicts with existing workspace
        existing = db.query(Workspace).filter(
            Workspace.org_id == org.org_id,
            Workspace.workspace_slug == workspace_slug,
            Workspace.workspace_id != workspace_id
        ).first()

        if existing:
            # Append number to make unique
            base_slug = workspace_slug
            counter = 1
            while db.query(Workspace).filter(
                Workspace.org_id == org.org_id,
                Workspace.workspace_slug == workspace_slug,
                Workspace.workspace_id != workspace_id
            ).first():
                workspace_slug = f"{base_slug}-{counter}"
                counter += 1

        workspace.workspace_slug = workspace_slug

    if request.description is not None:
        workspace.description = request.description

    if request.environment is not None:
        valid_environments = ["production", "staging", "development", "testing"]
        if request.environment not in valid_environments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid environment. Must be one of: {', '.join(valid_environments)}",
            )
        workspace.environment = request.environment

    if request.config is not None:
        workspace.config = request.config

    db.commit()
    db.refresh(workspace)

    return workspace


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_role("owner", "admin")),
    org: Organization = Depends(get_current_active_org),
    db: Session = Depends(get_db),
):
    """
    Delete workspace

    Permanently deletes workspace and all associated data (policies, API keys, etc.).
    Requires: owner or admin role

    **Warning:** This action cannot be undone. All policies, API keys, and reports
    associated with this workspace will be deleted due to CASCADE foreign keys.
    """
    workspace = db.query(Workspace).filter(
        Workspace.workspace_id == workspace_id,
        Workspace.org_id == org.org_id
    ).first()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Prevent deleting the last workspace
    workspace_count = db.query(Workspace).filter(Workspace.org_id == org.org_id).count()
    if workspace_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last workspace. Organizations must have at least one workspace.",
        )

    # Delete workspace (CASCADE will handle related records)
    db.delete(workspace)
    db.commit()

    return None
