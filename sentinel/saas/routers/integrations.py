"""Integrations Router (Slack, SIEM)"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID, uuid4
from datetime import datetime, timezone

from ..dependencies import get_db, get_current_user, require_role
from ..models import User
from ..models.integration import Integration
from ..schemas.integration import (
    SlackConfigRequest, SlackConfigResponse,
    SIEMConfigRequest, SIEMConfigResponse,
    IntegrationListResponse, IntegrationResponse, TestIntegrationResponse
)
from ..rls import set_org_context

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("", response_model=IntegrationListResponse)
async def list_integrations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all integrations"""
    set_org_context(db, current_user.org_id)

    integrations = db.query(Integration).filter(
        Integration.org_id == current_user.org_id
    ).all()

    return IntegrationListResponse(integrations=integrations, total=len(integrations))


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get integration details"""
    set_org_context(db, current_user.org_id)

    integration = db.query(Integration).filter(
        Integration.integration_id == integration_id,
        Integration.org_id == current_user.org_id
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    return integration


@router.post("/slack", response_model=SlackConfigResponse, status_code=201)
async def configure_slack(
    request: SlackConfigRequest,
    current_user: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    """Configure Slack integration"""
    set_org_context(db, current_user.org_id)

    # Check if already exists
    existing = db.query(Integration).filter(
        Integration.org_id == current_user.org_id,
        Integration.integration_type == "slack"
    ).first()

    if existing:
        existing.config = {
            "bot_token": request.bot_token,
            "default_channel": request.default_channel
        }
        existing.status = "configured"
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        integration = existing
    else:
        integration = Integration(
            integration_id=uuid4(),
            org_id=current_user.org_id,
            integration_type="slack",
            config={
                "bot_token": request.bot_token,
                "default_channel": request.default_channel
            },
            status="configured"
        )
        db.add(integration)
        db.commit()

    db.refresh(integration)

    return SlackConfigResponse(
        integration_id=integration.integration_id,
        status=integration.status,
        default_channel=request.default_channel,
        created_at=integration.created_at
    )


@router.post("/slack/test", response_model=TestIntegrationResponse)
async def test_slack(
    request: SlackConfigRequest,
    current_user: User = Depends(require_role("admin", "owner")),
):
    """Test Slack connection"""
    try:
        from sentinel.integrations.slack import SlackIntegration, SlackConfig

        config = SlackConfig(
            bot_token=request.bot_token,
            default_channel=request.default_channel
        )
        slack = SlackIntegration(config)
        success = await slack.test_connection()
        await slack.close()

        return TestIntegrationResponse(
            success=success,
            message="Connection successful" if success else "Connection failed"
        )
    except ImportError:
        return TestIntegrationResponse(
            success=False,
            message="Slack integration module not available"
        )
    except Exception as e:
        return TestIntegrationResponse(success=False, message=str(e))


@router.delete("/slack", status_code=204)
async def remove_slack(
    current_user: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    """Remove Slack integration"""
    set_org_context(db, current_user.org_id)

    integration = db.query(Integration).filter(
        Integration.org_id == current_user.org_id,
        Integration.integration_type == "slack"
    ).first()

    if integration:
        db.delete(integration)
        db.commit()

    return None


@router.post("/siem", response_model=SIEMConfigResponse, status_code=201)
async def configure_siem(
    request: SIEMConfigRequest,
    current_user: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    """Configure SIEM integration"""
    set_org_context(db, current_user.org_id)

    # Check if already exists
    existing = db.query(Integration).filter(
        Integration.org_id == current_user.org_id,
        Integration.integration_type == "siem"
    ).first()

    if existing:
        existing.config = {"siem_type": request.siem_type, **request.config}
        existing.status = "configured"
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        integration = existing
    else:
        integration = Integration(
            integration_id=uuid4(),
            org_id=current_user.org_id,
            integration_type="siem",
            config={"siem_type": request.siem_type, **request.config},
            status="configured"
        )
        db.add(integration)
        db.commit()

    db.refresh(integration)

    return SIEMConfigResponse(
        integration_id=integration.integration_id,
        siem_type=request.siem_type,
        status=integration.status,
        created_at=integration.created_at
    )


@router.delete("/siem", status_code=204)
async def remove_siem(
    current_user: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    """Remove SIEM integration"""
    set_org_context(db, current_user.org_id)

    integration = db.query(Integration).filter(
        Integration.org_id == current_user.org_id,
        Integration.integration_type == "siem"
    ).first()

    if integration:
        db.delete(integration)
        db.commit()

    return None
