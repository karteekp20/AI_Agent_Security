"""A/B Tests Router"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from ..dependencies import get_db, get_current_user, require_role
from ..models import User, Policy
from ..schemas.ab_test import (
    CreateABTestRequest, ABTestResponse, ABTestListResponse,
    ABTestResultsResponse, ConcludeABTestRequest, ConcludeABTestResponse,
    ABTestMetrics
)
from ..services.ab_testing import ABTestingService
from ..rls import set_org_context

router = APIRouter(prefix="/ab-tests", tags=["ab-tests"])


def get_ab_service(db: Session = Depends(get_db)) -> ABTestingService:
    return ABTestingService(db)


@router.get("", response_model=ABTestListResponse)
async def list_tests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ABTestingService = Depends(get_ab_service),
):
    """List all A/B tests"""
    set_org_context(db, current_user.org_id)
    tests = service.get_active_tests(str(current_user.org_id))

    # Convert to response format
    test_responses = []
    for test in tests:
        test_responses.append(ABTestResponse(
            test_id=test.get("test_id", ""),
            control_policy_id=UUID(test.get("control_policy_id")),
            variant_policy_id=UUID(test.get("variant_policy_id")),
            traffic_percentage=test.get("traffic_percentage", 10),
            start_time=test.get("start_time"),
            end_time=test.get("end_time"),
            status=test.get("status", "active")
        ))

    return ABTestListResponse(tests=test_responses, total=len(test_responses))


@router.post("", response_model=ABTestResponse, status_code=201)
async def create_test(
    request: CreateABTestRequest,
    current_user: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
    service: ABTestingService = Depends(get_ab_service),
):
    """Create a new A/B test"""
    set_org_context(db, current_user.org_id)

    # Verify policies exist and belong to the organization
    control = db.query(Policy).filter(
        Policy.policy_id == request.control_policy_id,
        Policy.org_id == current_user.org_id
    ).first()
    variant = db.query(Policy).filter(
        Policy.policy_id == request.variant_policy_id,
        Policy.org_id == current_user.org_id
    ).first()

    if not control:
        raise HTTPException(status_code=404, detail="Control policy not found")
    if not variant:
        raise HTTPException(status_code=404, detail="Variant policy not found")

    test = await service.create_test(
        org_id=str(current_user.org_id),
        control_policy_id=str(request.control_policy_id),
        variant_policy_id=str(request.variant_policy_id),
        traffic_percentage=request.traffic_percentage
    )

    return ABTestResponse(
        test_id=test.get("test_id", ""),
        control_policy_id=request.control_policy_id,
        variant_policy_id=request.variant_policy_id,
        traffic_percentage=request.traffic_percentage,
        start_time=test.get("start_time"),
        end_time=test.get("end_time"),
        status=test.get("status", "active")
    )


@router.get("/{test_id}", response_model=ABTestResponse)
async def get_test(
    test_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ABTestingService = Depends(get_ab_service),
):
    """Get A/B test details"""
    set_org_context(db, current_user.org_id)

    tests = service.get_active_tests(str(current_user.org_id))
    test = next((t for t in tests if t.get("test_id") == test_id), None)

    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    return ABTestResponse(
        test_id=test.get("test_id", ""),
        control_policy_id=UUID(test.get("control_policy_id")),
        variant_policy_id=UUID(test.get("variant_policy_id")),
        traffic_percentage=test.get("traffic_percentage", 10),
        start_time=test.get("start_time"),
        end_time=test.get("end_time"),
        status=test.get("status", "active")
    )


@router.get("/{test_id}/results", response_model=ABTestResultsResponse)
async def get_results(
    test_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ABTestingService = Depends(get_ab_service),
):
    """Get A/B test results"""
    set_org_context(db, current_user.org_id)

    results = await service.get_test_results(test_id)
    if not results:
        raise HTTPException(status_code=404, detail="Test not found")

    # Convert to response format
    control_metrics = results.get("control", {})
    variant_metrics = results.get("variant", {})

    return ABTestResultsResponse(
        test_id=test_id,
        control=ABTestMetrics(
            policy_id=UUID(control_metrics.get("policy_id", "00000000-0000-0000-0000-000000000000")),
            total_evaluations=control_metrics.get("total_evaluations", 0),
            blocked_count=control_metrics.get("blocked_count", 0),
            false_positive_reports=control_metrics.get("false_positive_reports", 0),
            detection_rate=control_metrics.get("detection_rate", 0.0)
        ),
        variant=ABTestMetrics(
            policy_id=UUID(variant_metrics.get("policy_id", "00000000-0000-0000-0000-000000000000")),
            total_evaluations=variant_metrics.get("total_evaluations", 0),
            blocked_count=variant_metrics.get("blocked_count", 0),
            false_positive_reports=variant_metrics.get("false_positive_reports", 0),
            detection_rate=variant_metrics.get("detection_rate", 0.0)
        ),
        recommendation=results.get("recommendation")
    )


@router.post("/{test_id}/conclude", response_model=ConcludeABTestResponse)
async def conclude_test(
    test_id: str,
    request: ConcludeABTestRequest,
    current_user: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
    service: ABTestingService = Depends(get_ab_service),
):
    """Conclude A/B test and select winner"""
    set_org_context(db, current_user.org_id)

    if request.winner not in ("control", "variant"):
        raise HTTPException(status_code=400, detail="Winner must be 'control' or 'variant'")

    result = await service.conclude_test(test_id, request.winner)

    return ConcludeABTestResponse(
        test_id=test_id,
        winner=request.winner,
        message=f"Test concluded. {request.winner.title()} policy promoted."
    )


@router.delete("/{test_id}", status_code=204)
async def delete_test(
    test_id: str,
    current_user: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
    service: ABTestingService = Depends(get_ab_service),
):
    """Delete/cancel an A/B test"""
    set_org_context(db, current_user.org_id)

    # Cancel the test
    await service.conclude_test(test_id, "control")

    return None
