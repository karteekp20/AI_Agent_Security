"""
Policies API Router
Manage security policies, test patterns, and deploy with canary rollout
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
import re

from ..dependencies import get_db, get_current_user, require_role, require_permission
from ..models import User, Policy
from ..schemas.policy import (
    CreatePolicyRequest,
    UpdatePolicyRequest,
    TestPolicyRequest,
    DeployPolicyRequest,
    PolicyResponse,
    PolicyListResponse,
    TestPolicyResponse,
    DeployPolicyResponse,
)
from ..rls import set_org_context

router = APIRouter(prefix="/policies", tags=["policies"])


# ============================================================================
# CRUD ENDPOINTS
# ============================================================================

@router.post("", response_model=PolicyResponse, status_code=201)
async def create_policy(
    request: CreatePolicyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("policies:write")),
):
    """
    Create new security policy

    Requires: policies:write permission or admin/owner role
    """
    # Set org context for RLS
    set_org_context(db, current_user.org_id)

    # Validate pattern is valid regex
    try:
        re.compile(request.pattern_value)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")

    # Create policy
    policy = Policy(
        policy_id=uuid4(),
        org_id=current_user.org_id,
        workspace_id=request.workspace_id,
        policy_name=request.policy_name,
        policy_type=request.policy_type,
        pattern_value=request.pattern_value,
        action=request.action,
        severity=request.severity,
        description=request.description,
        is_active=request.is_active,
        test_percentage=request.test_percentage,
        version=1,
        created_by=current_user.user_id,
    )

    db.add(policy)
    db.commit()
    db.refresh(policy)

    return PolicyResponse.model_validate(policy)


@router.get("", response_model=PolicyListResponse)
async def list_policies(
    workspace_id: Optional[UUID] = Query(None, description="Filter by workspace"),
    policy_type: Optional[str] = Query(None, description="Filter by type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all policies for current organization

    Supports filtering by workspace, type, and active status
    """
    # Set org context for RLS
    set_org_context(db, current_user.org_id)

    # Build query
    query = db.query(Policy).filter(Policy.org_id == current_user.org_id)

    # Apply filters
    if workspace_id:
        query = query.filter(Policy.workspace_id == workspace_id)

    if policy_type:
        query = query.filter(Policy.policy_type == policy_type)

    if is_active is not None:
        query = query.filter(Policy.is_active == is_active)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    policies = query.order_by(Policy.created_at.desc()).offset(offset).limit(page_size).all()

    return PolicyListResponse(
        policies=[PolicyResponse.model_validate(p) for p in policies],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get policy details by ID"""
    # Set org context for RLS
    set_org_context(db, current_user.org_id)

    policy = db.query(Policy).filter(
        Policy.policy_id == policy_id,
        Policy.org_id == current_user.org_id,
    ).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    return PolicyResponse.model_validate(policy)


@router.patch("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: UUID,
    request: UpdatePolicyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("policies:write")),
):
    """
    Update existing policy

    Requires: policies:write permission or admin/owner role
    """
    # Set org context for RLS
    set_org_context(db, current_user.org_id)

    policy = db.query(Policy).filter(
        Policy.policy_id == policy_id,
        Policy.org_id == current_user.org_id,
    ).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Validate pattern if provided
    if request.pattern_value:
        try:
            re.compile(request.pattern_value)
        except re.error as e:
            raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)

    policy.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(policy)

    return PolicyResponse.model_validate(policy)


@router.delete("/{policy_id}", status_code=204)
async def delete_policy(
    policy_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_role("owner", "admin")),
):
    """
    Delete policy (soft delete)

    Requires: owner or admin role
    """
    # Set org context for RLS
    set_org_context(db, current_user.org_id)

    policy = db.query(Policy).filter(
        Policy.policy_id == policy_id,
        Policy.org_id == current_user.org_id,
    ).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Soft delete
    policy.deleted_at = datetime.utcnow()
    db.commit()

    return None


# ============================================================================
# POLICY TESTING
# ============================================================================

@router.post("/{policy_id}/test", response_model=TestPolicyResponse)
async def test_policy(
    policy_id: UUID,
    request: TestPolicyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Test policy against sample input

    Returns match result and action that would be taken
    """
    # Set org context for RLS
    set_org_context(db, current_user.org_id)

    policy = db.query(Policy).filter(
        Policy.policy_id == policy_id,
        Policy.org_id == current_user.org_id,
    ).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Test pattern matching
    try:
        pattern = re.compile(policy.pattern_value, re.IGNORECASE)
        matches = pattern.findall(request.test_input)
        matched = len(matches) > 0
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")

    # Determine action and output
    action_taken = policy.action if matched else "none"
    redacted_output = None
    explanation = ""

    if matched:
        if policy.action == "block":
            explanation = f"Input would be BLOCKED. Matched pattern: {policy.pattern_value}"
        elif policy.action == "redact":
            redacted_output = pattern.sub("[REDACTED]", request.test_input)
            explanation = f"Input would be REDACTED. Found {len(matches)} match(es)."
        elif policy.action == "flag":
            explanation = f"Input would be FLAGGED for review. Matched pattern: {policy.pattern_value}"
    else:
        explanation = "Input does not match policy pattern. No action would be taken."

    return TestPolicyResponse(
        matched=matched,
        match_details={"matches": matches[:10], "count": len(matches)} if matches else None,
        action_taken=action_taken,
        redacted_output=redacted_output,
        explanation=explanation,
    )


# ============================================================================
# POLICY DEPLOYMENT
# ============================================================================

@router.post("/{policy_id}/deploy", response_model=DeployPolicyResponse)
async def deploy_policy(
    policy_id: UUID,
    request: DeployPolicyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("policies:write")),
):
    """
    Deploy policy with canary rollout

    Canary deployment: Gradually roll out policy to percentage of traffic
    - 0%: Policy disabled
    - 1-99%: Canary mode (apply to X% of requests)
    - 100%: Fully deployed

    Requires: policies:write permission or admin/owner role
    """
    # Set org context for RLS
    set_org_context(db, current_user.org_id)

    policy = db.query(Policy).filter(
        Policy.policy_id == policy_id,
        Policy.org_id == current_user.org_id,
    ).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Update deployment settings
    policy.test_percentage = request.test_percentage
    policy.deployed_at = datetime.utcnow()

    # Auto-activate if deploying > 0%
    if request.test_percentage > 0:
        policy.is_active = True
    else:
        policy.is_active = False

    db.commit()
    db.refresh(policy)

    # Determine message
    if request.test_percentage == 0:
        message = "Policy disabled (0% rollout)"
    elif request.test_percentage == 100:
        message = "Policy fully deployed (100% rollout)"
    else:
        message = f"Policy in canary mode ({request.test_percentage}% rollout)"

    return DeployPolicyResponse(
        policy_id=policy.policy_id,
        test_percentage=policy.test_percentage,
        deployed_at=policy.deployed_at,
        message=message,
    )


@router.post("/{policy_id}/rollback", response_model=PolicyResponse)
async def rollback_policy(
    policy_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("policies:write")),
):
    """
    Rollback policy to parent version

    If policy has a parent_policy_id, reverts to parent settings

    Requires: policies:write permission or admin/owner role
    """
    # Set org context for RLS
    set_org_context(db, current_user.org_id)

    policy = db.query(Policy).filter(
        Policy.policy_id == policy_id,
        Policy.org_id == current_user.org_id,
    ).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    if not policy.parent_policy_id:
        raise HTTPException(status_code=400, detail="No parent version to rollback to")

    # Get parent policy
    parent = db.query(Policy).filter(
        Policy.policy_id == policy.parent_policy_id,
        Policy.org_id == current_user.org_id,
    ).first()

    if not parent:
        raise HTTPException(status_code=404, detail="Parent policy not found")

    # Rollback to parent settings
    policy.pattern_value = parent.pattern_value
    policy.action = parent.action
    policy.severity = parent.severity
    policy.description = parent.description
    policy.test_percentage = parent.test_percentage
    policy.is_active = parent.is_active
    policy.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(policy)

    return PolicyResponse.model_validate(policy)
