"""Webhook Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime


class CreateWebhookRequest(BaseModel):
    url: str = Field(description="Webhook endpoint URL")
    description: Optional[str] = Field(None, max_length=500)
    events: List[str] = Field(description="Event types to subscribe to")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict)
    enabled: bool = Field(default=True)


class UpdateWebhookRequest(BaseModel):
    url: Optional[str] = None
    description: Optional[str] = None
    events: Optional[List[str]] = None
    headers: Optional[Dict[str, str]] = None
    enabled: Optional[bool] = None


class WebhookResponse(BaseModel):
    webhook_id: UUID
    org_id: UUID
    webhook_url: str
    description: Optional[str]
    events: List[str]
    enabled: bool
    failure_count: int
    last_triggered: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookListResponse(BaseModel):
    webhooks: List[WebhookResponse]
    total: int


class TestWebhookResponse(BaseModel):
    success: bool
    status_code: Optional[int]
    message: str
