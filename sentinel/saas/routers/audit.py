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
from ..schemas.audit import (
    AuditLogResponse,
    AuditLogListResponse,
    ThreatDetails,
    PIIEntityDetail,
    InjectionDetail,
    ContentViolationDetail,
)
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


def build_threat_details(log: dict, user_role: str) -> ThreatDetails:
    """
    Build structured threat details from audit log JSONB data.
    Apply role-based masking for sensitive values.

    Args:
        log: Audit log dictionary from database
        user_role: Current user's role (for determining masked value visibility)

    Returns:
        ThreatDetails object with structured threat information
    """
    threat_details = ThreatDetails(
        pii=[],
        injections=[],
        content_violations=[],
        total_threat_count=0,
        blocking_reasons=[]
    )

    # Process PII entities from pii_entities JSONB field
    if log.get("pii_entities"):
        for entity in log["pii_entities"]:
            try:
                # Skip if missing critical position data
                if "start_position" not in entity or "end_position" not in entity:
                    continue
                pii_detail = PIIEntityDetail(
                    entity_type=entity.get("entity_type", "unknown"),
                    redaction_strategy=entity.get("redaction_strategy", "token"),
                    start_position=entity["start_position"],
                    end_position=entity["end_position"],
                    confidence=entity.get("confidence", 0.85),
                    detection_method=entity.get("detection_method", "regex"),
                    token_id=entity.get("token_id", ""),
                )
                # Set masked_value based on role
                if user_role in ["admin", "owner"]:
                    # Admin/owner see original values (for auditing)
                    pii_detail.masked_value = entity.get("original_value", "[UNKNOWN]")
                else:
                    # Viewer/member/auditor see redacted values
                    pii_detail.masked_value = entity.get("redacted_value", f"[{entity.get('entity_type', 'UNKNOWN').upper()}_REDACTED]")

                threat_details.pii.append(pii_detail)
                threat_details.total_threat_count += 1
            except Exception as e:
                print(f"Error processing PII entity: {e}")
                continue

    # Process injection attempts
    if log.get("injection_detected"):
        try:
            # Extract matched patterns from metadata
            metadata = log.get("metadata") or {}
            matched_patterns = metadata.get("injection_patterns", [])

            injection = InjectionDetail(
                injection_type=log.get("injection_type", "unknown"),
                confidence=log.get("injection_confidence", 0.0),
                matched_patterns=matched_patterns if isinstance(matched_patterns, list) else [],
                severity="high" if log.get("injection_confidence", 0) > 0.8 else "medium"
            )
            threat_details.injections.append(injection)
            threat_details.total_threat_count += 1
        except Exception as e:
            print(f"Error processing injection detail: {e}")

    # Process content violations (if present in metadata)
    metadata = log.get("metadata") or {}
    if metadata.get("content_violations"):
        try:
            for violation in metadata["content_violations"]:
                content_violation = ContentViolationDetail(
                    violation_type=violation.get("type", "unknown"),
                    matched_terms=violation.get("terms", []),
                    severity=violation.get("severity", "medium")
                )
                threat_details.content_violations.append(content_violation)
                threat_details.total_threat_count += 1
        except Exception as e:
            print(f"Error processing content violations: {e}")

    # Build blocking reasons
    if log.get("blocked"):
        if threat_details.pii:
            # Get unique entity types
            entity_types = list(set(p.entity_type for p in threat_details.pii))
            types_str = ", ".join(entity_types[:3])
            if len(entity_types) > 3:
                types_str += f", +{len(entity_types) - 3} more"

            threat_details.blocking_reasons.append(
                f"PII detected ({len(threat_details.pii)} instances): {types_str}"
            )

        if threat_details.injections:
            for inj in threat_details.injections:
                threat_details.blocking_reasons.append(
                    f"{inj.injection_type.upper()} injection detected (confidence: {inj.confidence:.2f})"
                )

        if threat_details.content_violations:
            for violation in threat_details.content_violations:
                threat_details.blocking_reasons.append(
                    f"Content violation: {violation.violation_type}"
                )

        # If no specific reasons but blocked, add generic reason
        if not threat_details.blocking_reasons:
            risk_score = log.get("risk_score", 0)
            if risk_score > 0.8:
                threat_details.blocking_reasons.append(
                    f"High risk score: {risk_score:.2f}"
                )

    return threat_details


def mask_user_input_for_role(
    user_input: str,
    pii_entities: Optional[list],
    user_role: str
) -> str:
    """
    Mask PII in user_input based on user role.

    - admin/owner: See original text
    - viewer/member/auditor: See fully redacted text with tokens

    Args:
        user_input: Original user input text
        pii_entities: List of detected PII entities with positions
        user_role: Current user's role

    Returns:
        Masked user input (or original for admin/owner)
    """
    if user_role in ["admin", "owner"]:
        return user_input  # Full access for admins

    if not pii_entities:
        return user_input  # No PII to mask

    # For viewers: Replace PII with redaction tokens
    masked_text = user_input

    # Sort entities by position (reverse order to maintain positions during replacement)
    try:
        sorted_entities = sorted(
            pii_entities,
            key=lambda e: e.get("start_position", 0),
            reverse=True
        )

        for entity in sorted_entities:
            start = entity.get("start_position")
            end = entity.get("end_position")
            entity_type = entity.get("entity_type", "SENSITIVE")
            if start is None or end is None:
                original = entity.get("original_value", "")
                if original and original in masked_text:
                    start = masked_text.find(original)
                    end = start + len(original)

            if start is not None and end is not None and 0 <= start < end <= len(masked_text):
                # Replace with redaction token
                token = f"[{entity_type.upper()}_REDACTED]"
                masked_text = masked_text[:start] + token + masked_text[end:]

    except Exception as e:
        print(f"Error masking user input: {e}")
        # Return original on error (for admins) or generic message (for viewers)
        return user_input if user_role in ["admin", "owner"] else "[REDACTED_INPUT]"

    return masked_text


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
        # Build threat details with role-based masking
        threat_details = build_threat_details(log, current_user.role)

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
            user_input=mask_user_input_for_role(
                log.get("user_input", ""),
                log.get("pii_entities"),
                current_user.role
            ),
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
            threat_details=threat_details,
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

    # Build threat details with role-based masking
    threat_details = build_threat_details(log, current_user.role)

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
        user_input=mask_user_input_for_role(
            log.get("user_input", ""),
            log.get("pii_entities"),
            current_user.role
        ),
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
        threat_details=threat_details,
    )
