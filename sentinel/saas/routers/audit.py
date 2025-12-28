"""
Audit Logs API Router
View and filter security audit logs
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta, timezone
from uuid import UUID

from ..dependencies import get_db, get_current_user
from ..models import User
from ..schemas.audit import AuditLogResponse, AuditLogListResponse
from ...storage.postgres_adapter import PostgreSQLAdapter, PostgreSQLConfig

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_postgres_adapter(db: Session) -> Optional[PostgreSQLAdapter]:
    """Get PostgreSQL adapter for audit log queries"""
    try:
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

@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    start_date: Optional[datetime] = Query(None, description="Start of date range"),
    end_date: Optional[datetime] = Query(None, description="End of date range"),
    workspace_id: Optional[UUID] = Query(None, description="Filter by workspace"),
    user_id: Optional[str] = Query(None, description="Filter by user"),
    blocked_only: bool = Query(False, description="Show only blocked requests"),
    pii_only: bool = Query(False, description="Show only PII detections"),
    injection_only: bool = Query(False, description="Show only injection attempts"),
    min_risk_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum risk score"),
    search: Optional[str] = Query(None, description="Search in user input"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get audit logs with advanced filtering

    Supports filtering by:
    - Date range
    - Workspace
    - User ID
    - Blocked status
    - PII detection
    - Injection detection
    - Risk score threshold
    - Text search
    """
    # Get PostgreSQL adapter
    adapter = get_postgres_adapter(db)

    if not adapter:
        # Return empty result if adapter not available
        return AuditLogListResponse(logs=[], total=0, page=page, page_size=page_size)

    # Set default date range if not provided (last 7 days)
    if not start_date:
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
    if not end_date:
        end_date = datetime.now(timezone.utc)

    # Get audit logs with filters
    all_logs = adapter.get_audit_logs(
        start_time=start_date,
        end_time=end_date,
        org_id=str(current_user.org_id),
        workspace_id=str(workspace_id) if workspace_id else None,
        user_id=user_id,
        blocked_only=blocked_only,
        limit=10000,  # Get more for client-side filtering
    )

    # Apply additional filters
    filtered_logs = all_logs

    if pii_only:
        filtered_logs = [log for log in filtered_logs if log.get("pii_detected")]

    if injection_only:
        filtered_logs = [log for log in filtered_logs if log.get("injection_detected")]

    if min_risk_score is not None:
        filtered_logs = [log for log in filtered_logs if (log.get("risk_score") or 0) >= min_risk_score]

    if search:
        search_lower = search.lower()
        filtered_logs = [
            log for log in filtered_logs
            if search_lower in (log.get("user_input") or "").lower()
        ]

    # Get total count
    total = len(filtered_logs)

    # Apply pagination
    offset = (page - 1) * page_size
    paginated_logs = filtered_logs[offset:offset + page_size]

    # Convert to response models
    logs = []
    for log in paginated_logs:
        logs.append(AuditLogResponse(
            id=log.get("id"),
            timestamp=log.get("timestamp"),
            session_id=log.get("session_id"),
            request_id=log.get("request_id"),
            org_id=log.get("org_id"),
            workspace_id=log.get("workspace_id"),
            user_id=log.get("user_id"),
            user_role=log.get("user_role"),
            ip_address=log.get("ip_address"),
            user_input=log.get("user_input", ""),
            input_length=log.get("input_length", 0),
            blocked=log.get("blocked", False),
            risk_score=log.get("risk_score"),
            risk_level=log.get("risk_level"),
            pii_detected=log.get("pii_detected", False),
            pii_entities=log.get("pii_entities"),
            redacted_count=log.get("redacted_count", 0),
            injection_detected=log.get("injection_detected", False),
            injection_type=log.get("injection_type"),
            injection_confidence=log.get("injection_confidence"),
            escalated=log.get("escalated", False),
            escalated_to=log.get("escalated_to"),
            metadata=log.get("metadata"),
        ))

    return AuditLogListResponse(
        logs=logs,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get single audit log by ID"""
    adapter = get_postgres_adapter(db)

    if not adapter:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Audit log storage not available")

    # Get all logs and filter by ID (simple approach)
    logs = adapter.get_audit_logs(
        start_time=datetime.now(timezone.utc) - timedelta(days=90),
        end_time=datetime.now(timezone.utc),
        org_id=str(current_user.org_id),
        limit=10000,
    )

    log = next((log for log in logs if log.get("id") == log_id), None)

    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Audit log not found")

    return AuditLogResponse(
        id=log.get("id"),
        timestamp=log.get("timestamp"),
        session_id=log.get("session_id"),
        request_id=log.get("request_id"),
        org_id=log.get("org_id"),
        workspace_id=log.get("workspace_id"),
        user_id=log.get("user_id"),
        user_role=log.get("user_role"),
        ip_address=log.get("ip_address"),
        user_input=log.get("user_input", ""),
        input_length=log.get("input_length", 0),
        blocked=log.get("blocked", False),
        risk_score=log.get("risk_score"),
        risk_level=log.get("risk_level"),
        pii_detected=log.get("pii_detected", False),
        pii_entities=log.get("pii_entities"),
        redacted_count=log.get("redacted_count", 0),
        injection_detected=log.get("injection_detected", False),
        injection_type=log.get("injection_type"),
        injection_confidence=log.get("injection_confidence"),
        escalated=log.get("escalated", False),
        escalated_to=log.get("escalated_to"),
        metadata=log.get("metadata"),
    )
