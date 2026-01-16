"""
Dashboard API Router
Real-time metrics, threat monitoring, and analytics
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from uuid import UUID

from ..dependencies import get_db, get_current_user
from ..models import User
from ...storage.postgres_adapter import PostgreSQLAdapter, PostgreSQLConfig
from .audit import mask_user_input_for_role

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ============================================================================
# RESPONSE MODELS
# ============================================================================

from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    """Dashboard metrics for a time period"""
    total_requests: int
    threats_blocked: int
    pii_detected: int
    injection_attempts: int
    avg_risk_score: float
    risk_score_trend: List[Dict[str, Any]]
    threat_distribution: List[Dict[str, Any]]
    threats_over_time: List[Dict[str, Any]]
    pii_types: List[Dict[str, Any]]
    top_affected_users: List[Dict[str, Any]]
    hourly_activity: List[Dict[str, Any]]


class RecentThreat(BaseModel):
    """Recent threat event"""
    timestamp: str
    threat_type: str
    risk_score: float
    blocked: bool
    user_input: str
    user_id: Optional[str] = None
    threat_count_by_type: Optional[Dict[str, int]] = None


class ThreatTypeCount(BaseModel):
    """Count of threats by type"""
    type: str
    count: int
    percentage: float


class ThreatBreakdown(BaseModel):
    """Detailed threat breakdown statistics"""
    pii_types: List[ThreatTypeCount]
    injection_types: List[ThreatTypeCount]
    content_violations: List[ThreatTypeCount]
    severity_distribution: Dict[str, int]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_postgres_adapter(db: Session) -> Optional[PostgreSQLAdapter]:
    """Get PostgreSQL adapter for audit log queries"""
    try:
        # Use the existing PostgreSQL connection from the database session
        config = PostgreSQLConfig(
            host=db.bind.url.host or "localhost",
            port=db.bind.url.port or 5432,
            database=db.bind.url.database or "sentinel",
            user=db.bind.url.username or "sentinel_user",
            password=db.bind.url.password or "sentinel_password",
        )
        adapter = PostgreSQLAdapter(config)
        return adapter if adapter.enabled else None
    except Exception as e:
        print(f"Failed to create PostgreSQL adapter: {e}")
        return None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    timeframe: str = Query("24h", description="Time range: 1h, 24h, 7d, 30d"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get dashboard metrics for specified timeframe

    Returns:
        - Total requests
        - Threats blocked
        - PII detected
        - Injection attempts
        - Average risk score
        - Risk score trend (time series)
        - Threat distribution (by type)
    """
    # Calculate time range
    timeframe_map = {
        "1h": timedelta(hours=1),
        "24h": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }

    delta = timeframe_map.get(timeframe, timedelta(days=1))
    start_time = datetime.now(timezone.utc) - delta
    end_time = datetime.now(timezone.utc)

    # Get PostgreSQL adapter
    adapter = get_postgres_adapter(db)

    if not adapter:
        # Return mock data if PostgreSQL adapter not available
        return DashboardMetrics(
            total_requests=12345,
            threats_blocked=127,
            pii_detected=43,
            injection_attempts=15,
            avg_risk_score=0.23,
            risk_score_trend=[
                {"timestamp": (datetime.now(timezone.utc) - timedelta(hours=i)).isoformat(), "risk_score": 0.2 + (i * 0.01)}
                for i in range(24, 0, -1)
            ],
            threat_distribution=[
                {"threat_type": "PII Leak", "count": 43},
                {"threat_type": "SQL Injection", "count": 8},
                {"threat_type": "Prompt Injection", "count": 7},
                {"threat_type": "XSS", "count": 5},
            ],
            threats_over_time=[
                {"timestamp": (datetime.now(timezone.utc) - timedelta(hours=i)).isoformat(), "count": 5 + i}
                for i in range(24, 0, -1)
            ],
            pii_types=[
                {"entity_type": "credit_card", "count": 15},
                {"entity_type": "ssn", "count": 12},
                {"entity_type": "phone", "count": 8},
                {"entity_type": "email", "count": 8},
            ],
            top_affected_users=[
                {"user_id": "user_123", "threat_count": 12},
                {"user_id": "user_456", "threat_count": 8},
                {"user_id": "user_789", "threat_count": 5},
            ],
            hourly_activity=[
                {"hour": i, "count": 5 + (i % 12)}
                for i in range(24)
            ],
        )

    # Get compliance stats (includes total requests, blocked, PII, injection)
    stats = adapter.get_compliance_stats(
        start_date=start_time,
        end_date=end_time,
        org_id=str(current_user.org_id),
    )

    # Get audit logs for trend analysis
    audit_logs = adapter.get_audit_logs(
        start_time=start_time,
        end_time=end_time,
        org_id=str(current_user.org_id),
        limit=1000,
    )

    # Calculate risk score trend (group by hour/day depending on timeframe)
    interval = timedelta(hours=1) if delta <= timedelta(days=1) else timedelta(days=1)
    risk_score_trend = []

    current = start_time
    while current < end_time:
        next_time = current + interval

        # Get logs in this interval
        interval_logs = [
            log for log in audit_logs
            if current <= log["timestamp"] < next_time and log["risk_score"] is not None
        ]

        if interval_logs:
            avg_risk = sum(log["risk_score"] for log in interval_logs) / len(interval_logs)
        else:
            avg_risk = 0.0

        risk_score_trend.append({
            "timestamp": current.isoformat(),
            "risk_score": round(avg_risk, 3),
        })

        current = next_time

    # Calculate threat distribution
    threat_counts = {}
    for log in audit_logs:
        if log.get("pii_detected"):
            threat_counts["PII Leak"] = threat_counts.get("PII Leak", 0) + 1
        if log.get("injection_detected"):
            injection_type = log.get("injection_type") or "Unknown Injection"
            threat_counts[injection_type] = threat_counts.get(injection_type, 0) + 1

    threat_distribution = [
        {"threat_type": threat_type, "count": count}
        for threat_type, count in sorted(threat_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    # Calculate threats over time (same interval as risk score trend)
    threats_over_time = []
    current = start_time
    while current < end_time:
        next_time = current + interval

        # Count threats in this interval
        interval_threats = [
            log for log in audit_logs
            if current <= log["timestamp"] < next_time and (log.get("blocked") or log.get("pii_detected") or log.get("injection_detected"))
        ]

        threats_over_time.append({
            "timestamp": current.isoformat(),
            "count": len(interval_threats),
        })

        current = next_time

    # Calculate PII types breakdown
    pii_type_counts = {}
    for log in audit_logs:
        if log.get("pii_entities") and isinstance(log["pii_entities"], list):
            for entity in log["pii_entities"]:
                if isinstance(entity, dict):
                    entity_type = entity.get("entity_type", "unknown")
                    pii_type_counts[entity_type] = pii_type_counts.get(entity_type, 0) + 1

    pii_types = [
        {"entity_type": entity_type, "count": count}
        for entity_type, count in sorted(pii_type_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    # Calculate top affected users
    user_threat_counts = {}
    for log in audit_logs:
        if log.get("blocked") or log.get("pii_detected") or log.get("injection_detected"):
            user_id = log.get("user_id", "anonymous")
            user_threat_counts[user_id] = user_threat_counts.get(user_id, 0) + 1

    top_affected_users = [
        {"user_id": user_id, "threat_count": count}
        for user_id, count in sorted(user_threat_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    # Calculate hourly activity (24-hour breakdown)
    hourly_counts = {i: 0 for i in range(24)}
    for log in audit_logs:
        if log.get("blocked") or log.get("pii_detected") or log.get("injection_detected"):
            hour = log["timestamp"].hour
            hourly_counts[hour] += 1

    hourly_activity = [
        {"hour": hour, "count": count}
        for hour, count in sorted(hourly_counts.items())
    ]

    return DashboardMetrics(
        total_requests=int(stats.get("total_requests", 0) or 0),
        threats_blocked=int(stats.get("blocked_requests", 0) or 0),
        pii_detected=int(stats.get("pii_detections", 0) or 0),
        injection_attempts=int(stats.get("injection_attempts", 0) or 0),
        avg_risk_score=round(float(stats.get("avg_risk_score", 0.0) or 0.0), 3),
        risk_score_trend=risk_score_trend,
        threat_distribution=threat_distribution,
        threats_over_time=threats_over_time,
        pii_types=pii_types,
        top_affected_users=top_affected_users,
        hourly_activity=hourly_activity,
    )


@router.get("/recent-threats", response_model=List[RecentThreat])
async def get_recent_threats(
    limit: int = Query(50, ge=1, le=100, description="Number of recent threats"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get recent threat events

    Returns list of recent blocked/detected threats with details
    """
    # Get PostgreSQL adapter
    adapter = get_postgres_adapter(db)

    if not adapter:
        # Return mock data if PostgreSQL adapter not available
        return [
            RecentThreat(
                timestamp=(datetime.now(timezone.utc) - timedelta(minutes=i*5)).isoformat(),
                threat_type="PII Leak" if i % 3 == 0 else "SQL Injection" if i % 3 == 1 else "Prompt Injection",
                risk_score=round(0.5 + (i * 0.02), 2),
                blocked=i % 2 == 0,
                user_input=f"Test input {i}",
                user_id=f"user_{i}",
            )
            for i in range(min(limit, 10))
        ]

    # Get recent audit logs with threats (blocked or high risk)
    audit_logs = adapter.get_audit_logs(
        start_time=datetime.now(timezone.utc) - timedelta(days=7),  # Last 7 days
        end_time=datetime.now(timezone.utc),
        org_id=str(current_user.org_id),
        limit=limit * 2,  # Get more to filter
    )

    # Filter to only threats (blocked or PII detected or injection detected)
    threat_logs = [
        log for log in audit_logs
        if log.get("blocked") or log.get("pii_detected") or log.get("injection_detected") or (log.get("risk_score", 0) > 0.5)
    ]

    # Convert to RecentThreat objects
    recent_threats = []
    for log in threat_logs[:limit]:
        # Determine threat type
        threat_type = "Unknown"
        if log.get("pii_detected"):
            threat_type = "PII Leak"
        elif log.get("injection_detected"):
            threat_type = log.get("injection_type") or "Injection Attempt"
        elif log.get("risk_score", 0) > 0.7:
            threat_type = "High Risk Content"

        # Count threats by type for this log
        threat_count_by_type = {}
        if log.get("pii_detected"):
            pii_count = len(log.get("pii_entities", [])) if log.get("pii_entities") else 1
            threat_count_by_type["pii"] = pii_count
        if log.get("injection_detected"):
            threat_count_by_type["injection"] = 1
        # Content violations would be in metadata
        metadata = log.get("metadata") or {}
        if metadata.get("content_violations"):
            threat_count_by_type["content_violation"] = len(metadata["content_violations"])

        # Mask user_input based on role before truncating
        masked_input = mask_user_input_for_role(
            log.get("user_input", ""),
            log.get("pii_entities"),
            current_user.role
        )

        recent_threats.append(RecentThreat(
            timestamp=log["timestamp"].isoformat() if isinstance(log["timestamp"], datetime) else log["timestamp"],
            threat_type=threat_type,
            risk_score=round(float(log.get("risk_score", 0.0) or 0.0), 2),
            blocked=bool(log.get("blocked", False)),
            user_input=masked_input[:100],  # Truncate for display
            user_id=log.get("user_id"),
            threat_count_by_type=threat_count_by_type if threat_count_by_type else None,
        ))

    return recent_threats


@router.get("/threat-breakdown", response_model=ThreatBreakdown)
async def get_threat_breakdown(
    timeframe: str = Query("24h", regex="^(1h|24h|7d|30d)$", description="Time range"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed threat breakdown statistics

    Returns aggregated statistics for:
    - PII types detected
    - Injection types detected
    - Content violations
    - Severity distribution
    """
    # Calculate time range
    timeframe_map = {
        "1h": timedelta(hours=1),
        "24h": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }

    delta = timeframe_map.get(timeframe, timedelta(days=1))
    start_time = datetime.now(timezone.utc) - delta
    end_time = datetime.now(timezone.utc)

    # Get PostgreSQL adapter
    adapter = get_postgres_adapter(db)

    if not adapter:
        # Return mock data if PostgreSQL adapter not available
        return ThreatBreakdown(
            pii_types=[
                ThreatTypeCount(type="credit_card", count=42, percentage=35.0),
                ThreatTypeCount(type="ssn", count=28, percentage=23.3),
                ThreatTypeCount(type="email", count=50, percentage=41.7),
            ],
            injection_types=[
                ThreatTypeCount(type="sql", count=15, percentage=60.0),
                ThreatTypeCount(type="prompt", count=10, percentage=40.0),
            ],
            content_violations=[],
            severity_distribution={"low": 10, "medium": 25, "high": 45, "critical": 20}
        )

    # Get audit logs for timeframe
    audit_logs = adapter.get_audit_logs(
        start_time=start_time,
        end_time=end_time,
        org_id=str(current_user.org_id),
        limit=10000,
    )

    # Aggregate PII types
    pii_type_counts = {}
    total_pii = 0
    for log in audit_logs:
        if log.get("pii_entities") and isinstance(log["pii_entities"], list):
            for entity in log["pii_entities"]:
                if isinstance(entity, dict):
                    entity_type = entity.get("entity_type", "unknown")
                    pii_type_counts[entity_type] = pii_type_counts.get(entity_type, 0) + 1
                    total_pii += 1

    # Convert to ThreatTypeCount with percentages
    pii_types = []
    for entity_type, count in sorted(pii_type_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_pii * 100) if total_pii > 0 else 0
        pii_types.append(ThreatTypeCount(
            type=entity_type,
            count=count,
            percentage=round(percentage, 1)
        ))

    # Aggregate injection types
    injection_type_counts = {}
    total_injections = 0
    for log in audit_logs:
        if log.get("injection_detected"):
            injection_type = log.get("injection_type", "unknown")
            injection_type_counts[injection_type] = injection_type_counts.get(injection_type, 0) + 1
            total_injections += 1

    # Convert to ThreatTypeCount with percentages
    injection_types = []
    for injection_type, count in sorted(injection_type_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_injections * 100) if total_injections > 0 else 0
        injection_types.append(ThreatTypeCount(
            type=injection_type,
            count=count,
            percentage=round(percentage, 1)
        ))

    # Aggregate content violations
    violation_type_counts = {}
    total_violations = 0
    for log in audit_logs:
        metadata = log.get("metadata") or {}
        if metadata.get("content_violations"):
            for violation in metadata["content_violations"]:
                violation_type = violation.get("type", "unknown")
                violation_type_counts[violation_type] = violation_type_counts.get(violation_type, 0) + 1
                total_violations += 1

    # Convert to ThreatTypeCount with percentages
    content_violations = []
    for violation_type, count in sorted(violation_type_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_violations * 100) if total_violations > 0 else 0
        content_violations.append(ThreatTypeCount(
            type=violation_type,
            count=count,
            percentage=round(percentage, 1)
        ))

    # Calculate severity distribution
    severity_distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for log in audit_logs:
        risk_score = log.get("risk_score", 0.0) or 0.0
        if risk_score < 0.2:
            severity_distribution["low"] += 1
        elif risk_score < 0.5:
            severity_distribution["medium"] += 1
        elif risk_score < 0.8:
            severity_distribution["high"] += 1
        else:
            severity_distribution["critical"] += 1

    return ThreatBreakdown(
        pii_types=pii_types,
        injection_types=injection_types,
        content_violations=content_violations,
        severity_distribution=severity_distribution
    )
