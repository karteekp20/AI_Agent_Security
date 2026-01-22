"""ML/Anomaly Detection Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class AnomalyAnalyzeRequest(BaseModel):
    user_id: str
    user_input: str
    request_context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class AnomalyAnalyzeResponse(BaseModel):
    is_anomaly: bool
    anomaly_score: float = Field(ge=0.0, le=1.0)
    threshold: float
    features: Dict[str, Any]
    explanation: str


class AnomalyResponse(BaseModel):
    anomaly_id: UUID
    user_id: str
    anomaly_score: float
    is_anomaly: bool
    features: Dict[str, Any]
    detected_at: datetime


class AnomalyListResponse(BaseModel):
    anomalies: List[AnomalyResponse]
    total: int
    page: int
    page_size: int


class UserBehaviorResponse(BaseModel):
    user_id: str
    org_id: UUID
    feature_vector: Dict[str, Any]
    sample_count: int
    last_updated: datetime

    class Config:
        from_attributes = True


class MLModelResponse(BaseModel):
    model_id: UUID
    org_id: UUID
    model_type: str
    model_version: int
    status: str
    metrics: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class MLModelListResponse(BaseModel):
    models: List[MLModelResponse]
    total: int


class TrainModelRequest(BaseModel):
    model_type: str = Field(description="anomaly_detection or autoencoder")
    training_window_days: int = Field(default=30, ge=1, le=365)


class TrainModelResponse(BaseModel):
    model_id: UUID
    status: str
    message: str
