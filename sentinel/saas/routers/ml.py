"""ML/Anomaly Detection Router"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from ..dependencies import get_db, get_current_user, require_role
from ..models import User
from ..models.ml_model import MLModel
from ..models.user_baseline import UserBaseline
from ..schemas.ml import (
    AnomalyAnalyzeRequest, AnomalyAnalyzeResponse,
    AnomalyListResponse, UserBehaviorResponse,
    MLModelListResponse, MLModelResponse,
    TrainModelRequest, TrainModelResponse
)
from ..rls import set_org_context

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/anomalies", response_model=AnomalyListResponse)
async def list_anomalies(
    user_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List recent anomalies for the organization"""
    set_org_context(db, current_user.org_id)
    # TODO: Query anomalies from audit logs or dedicated table
    return AnomalyListResponse(anomalies=[], total=0, page=page, page_size=page_size)


@router.post("/anomaly/analyze", response_model=AnomalyAnalyzeResponse)
async def analyze_anomaly(
    request: AnomalyAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Real-time anomaly analysis"""
    set_org_context(db, current_user.org_id)

    try:
        from sentinel.ml.anomaly_detector import AnomalyDetectionService
        service = AnomalyDetectionService(db)
        result = await service.analyze_request(
            org_id=str(current_user.org_id),
            user_id=request.user_id,
            user_input=request.user_input,
            context=request.request_context or {}
        )
        return AnomalyAnalyzeResponse(**result)
    except ImportError:
        # Fallback if ML module not available
        return AnomalyAnalyzeResponse(
            is_anomaly=False,
            anomaly_score=0.0,
            threshold=0.5,
            features={},
            explanation="ML module not available"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/behavior/{user_id}", response_model=UserBehaviorResponse)
async def get_user_behavior(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user behavioral baseline"""
    set_org_context(db, current_user.org_id)

    baseline = db.query(UserBaseline).filter(
        UserBaseline.org_id == current_user.org_id,
        UserBaseline.user_id == user_id
    ).first()

    if not baseline:
        raise HTTPException(status_code=404, detail="User baseline not found")

    return baseline


@router.get("/models", response_model=MLModelListResponse)
async def list_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List ML models for the organization"""
    set_org_context(db, current_user.org_id)

    models = db.query(MLModel).filter(
        MLModel.org_id == current_user.org_id
    ).all()

    return MLModelListResponse(models=models, total=len(models))


@router.get("/models/{model_id}", response_model=MLModelResponse)
async def get_model(
    model_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get ML model details"""
    set_org_context(db, current_user.org_id)

    model = db.query(MLModel).filter(
        MLModel.model_id == model_id,
        MLModel.org_id == current_user.org_id
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    return model


@router.post("/models/train", response_model=TrainModelResponse)
async def train_model(
    request: TrainModelRequest,
    current_user: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    """Trigger model training (admin only)"""
    set_org_context(db, current_user.org_id)
    # TODO: Trigger async training job via Celery
    raise HTTPException(status_code=501, detail="Training not yet implemented")
