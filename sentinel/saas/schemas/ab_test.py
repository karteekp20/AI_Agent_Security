"""A/B Test Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class CreateABTestRequest(BaseModel):
    control_policy_id: UUID
    variant_policy_id: UUID
    traffic_percentage: int = Field(default=10, ge=1, le=50)
    duration_days: int = Field(default=7, ge=1, le=30)


class ABTestResponse(BaseModel):
    test_id: str
    control_policy_id: UUID
    variant_policy_id: UUID
    traffic_percentage: int
    start_time: datetime
    end_time: Optional[datetime]
    status: str


class ABTestListResponse(BaseModel):
    tests: List[ABTestResponse]
    total: int


class ABTestMetrics(BaseModel):
    policy_id: UUID
    total_evaluations: int
    blocked_count: int
    false_positive_reports: int
    detection_rate: float


class ABTestResultsResponse(BaseModel):
    test_id: str
    control: ABTestMetrics
    variant: ABTestMetrics
    recommendation: Optional[str]


class ConcludeABTestRequest(BaseModel):
    winner: str = Field(description="'control' or 'variant'")


class ConcludeABTestResponse(BaseModel):
    test_id: str
    winner: str
    message: str
