"""
Workspace Schemas - Request and Response Models
Pydantic models for workspace management endpoints
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class WorkspaceBase(BaseModel):
    """Base workspace fields"""
    workspace_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    environment: str = Field(default="production", description="production, staging, development, testing")


class CreateWorkspaceRequest(WorkspaceBase):
    """Create workspace request"""
    config: Optional[dict] = Field(default={}, description="Workspace-specific security config overrides")

    class Config:
        schema_extra = {
            "example": {
                "workspace_name": "Mobile App",
                "description": "Production mobile application workspace",
                "environment": "production",
                "config": {
                    "enable_strict_mode": True,
                    "block_threshold": 0.9
                }
            }
        }


class WorkspaceResponse(BaseModel):
    """Workspace response"""
    workspace_id: UUID
    org_id: UUID
    workspace_name: str
    workspace_slug: str
    description: Optional[str]
    environment: str
    config: dict
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UpdateWorkspaceRequest(BaseModel):
    """Update workspace request"""
    workspace_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    environment: Optional[str] = Field(None, description="production, staging, development, testing")
    config: Optional[dict] = None


class WorkspaceListResponse(BaseModel):
    """List of workspaces"""
    workspaces: List[WorkspaceResponse]
    total: int
    org_id: UUID
