"""Integration Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class SlackConfigRequest(BaseModel):
    bot_token: str = Field(description="Slack Bot OAuth Token")
    default_channel: str = Field(description="Default channel ID")


class SlackConfigResponse(BaseModel):
    integration_id: UUID
    status: str
    default_channel: str
    created_at: datetime


class SIEMConfigRequest(BaseModel):
    siem_type: str = Field(description="syslog, cef, or splunk")
    config: Dict[str, Any]


class SIEMConfigResponse(BaseModel):
    integration_id: UUID
    siem_type: str
    status: str
    created_at: datetime


class IntegrationResponse(BaseModel):
    integration_id: UUID
    org_id: UUID
    integration_type: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class IntegrationListResponse(BaseModel):
    integrations: List[IntegrationResponse]
    total: int


class TestIntegrationResponse(BaseModel):
    success: bool
    message: str
