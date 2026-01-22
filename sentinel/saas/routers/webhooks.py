"""Webhooks Router"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID, uuid4
from datetime import datetime, timezone
import secrets

from ..dependencies import get_db, get_current_user, require_role
from ..models import User
from ..models.webhook import Webhook
from ..schemas.webhook import (
    CreateWebhookRequest, UpdateWebhookRequest,
    WebhookResponse, WebhookListResponse, TestWebhookResponse
)
from ..rls import set_org_context

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all webhooks"""
    set_org_context(db, current_user.org_id)

    webhooks = db.query(Webhook).filter(
        Webhook.org_id == current_user.org_id
    ).all()

    return WebhookListResponse(webhooks=webhooks, total=len(webhooks))


@router.post("", response_model=WebhookResponse, status_code=201)
async def create_webhook(
    request: CreateWebhookRequest,
    current_user: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    """Create a new webhook"""
    set_org_context(db, current_user.org_id)

    webhook = Webhook(
        webhook_id=uuid4(),
        org_id=current_user.org_id,
        webhook_url=request.url,
        webhook_secret=secrets.token_hex(32),
        description=request.description,
        events=request.events,
        headers=request.headers or {},
        enabled=request.enabled,
    )

    db.add(webhook)
    db.commit()
    db.refresh(webhook)

    return webhook


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get webhook details"""
    set_org_context(db, current_user.org_id)

    webhook = db.query(Webhook).filter(
        Webhook.webhook_id == webhook_id,
        Webhook.org_id == current_user.org_id
    ).first()

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return webhook


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: UUID,
    request: UpdateWebhookRequest,
    current_user: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    """Update webhook"""
    set_org_context(db, current_user.org_id)

    webhook = db.query(Webhook).filter(
        Webhook.webhook_id == webhook_id,
        Webhook.org_id == current_user.org_id
    ).first()

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    update_data = request.model_dump(exclude_unset=True)
    if "url" in update_data:
        webhook.webhook_url = update_data.pop("url")
    for field, value in update_data.items():
        if hasattr(webhook, field):
            setattr(webhook, field, value)

    webhook.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(webhook)

    return webhook


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: UUID,
    current_user: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    """Delete webhook"""
    set_org_context(db, current_user.org_id)

    webhook = db.query(Webhook).filter(
        Webhook.webhook_id == webhook_id,
        Webhook.org_id == current_user.org_id
    ).first()

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    db.delete(webhook)
    db.commit()

    return None


@router.post("/{webhook_id}/test", response_model=TestWebhookResponse)
async def test_webhook(
    webhook_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    """Test webhook delivery"""
    set_org_context(db, current_user.org_id)

    webhook = db.query(Webhook).filter(
        Webhook.webhook_id == webhook_id,
        Webhook.org_id == current_user.org_id
    ).first()

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    # TODO: Send test delivery in background
    # background_tasks.add_task(send_test_webhook, webhook)

    return TestWebhookResponse(
        success=True,
        status_code=200,
        message="Test delivery queued"
    )
