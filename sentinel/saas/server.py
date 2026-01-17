"""
Sentinel SaaS Server - Multi-Tenant AI Security Platform
Combines core Sentinel security with SaaS management APIs
"""

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import time
import uvicorn

# Sentinel Core Components
from sentinel import SentinelConfig, SentinelGateway, create_initial_state, EventType
from sentinel.observability import (
    SentinelMetrics,
    SentinelTracer,
    MetricsCollector,
    setup_logging,
    get_logger,
    log_security_event,
)
from sentinel.storage import RedisAdapter, RedisConfig, PostgreSQLAdapter
from sentinel.resilience import RateLimiter, RateLimitConfig

# SaaS Components
from .config import config as saas_config
from .dependencies import get_db, get_api_key_user, get_current_user
from .routers import auth_router, organizations_router, workspaces_router, dashboard_router, policies_router, audit_router, api_keys_router, reports_router
from .models import Organization
from sqlalchemy.orm import Session


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ProcessRequest(BaseModel):
    """Request to process user input (multi-tenant)"""
    user_input: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    user_role: Optional[str] = None
    ip_address: Optional[str] = None
    workspace_id: Optional[UUID] = None  # Optional: specify workspace
    metadata: Optional[Dict[str, Any]] = None


class ProcessResponse(BaseModel):
    """Response from processing"""
    allowed: bool
    redacted_input: str
    risk_score: float
    risk_level: str
    blocked: bool
    block_reason: Optional[str] = None
    pii_detected: bool
    pii_count: int
    injection_detected: bool
    escalated: bool
    processing_time_ms: float
    session_id: str
    org_id: UUID
    workspace_id: Optional[UUID]


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    mode: str
    components: Dict[str, str]


# ============================================================================
# APPLICATION FACTORY
# ============================================================================

def create_saas_app() -> FastAPI:
    """
    Create multi-tenant SaaS FastAPI application

    Returns:
        Configured FastAPI app with SaaS and security endpoints
    """
    app = FastAPI(
        title="Sentinel AI Security - SaaS Platform",
        description="Multi-tenant AI security control plane with dashboard and compliance reporting",
        version="2.0.0",
    )

    # ========================================================================
    # CORS
    # ========================================================================

    app.add_middleware(
        CORSMiddleware,
        allow_origins=saas_config.cors.allowed_origins,
        allow_credentials=saas_config.cors.allow_credentials,
        allow_methods=saas_config.cors.allow_methods,
        allow_headers=saas_config.cors.allow_headers,
    )

    # ========================================================================
    # INITIALIZE COMPONENTS
    # ========================================================================

    # Logging
    setup_logging(level="INFO", json_format=True)
    logger = get_logger("saas-api")
    logger.info("Starting Sentinel SaaS Server")

    # Metrics
    metrics = SentinelMetrics()
    app.state.metrics = metrics
    logger.info("✓ Prometheus metrics enabled")

    # Tracing
    if saas_config.environment == "production":
        tracer = SentinelTracer(
            service_name="sentinel-saas-api",
            otlp_endpoint="http://localhost:4317",  # Configure via environment
            console_export=False,
        )
        app.state.tracer = tracer
        logger.info("✓ OpenTelemetry tracing enabled")
    else:
        app.state.tracer = None

    # Redis
    redis_config = RedisConfig(
        host=saas_config.redis.url.split("//")[1].split(":")[0] if "//" in saas_config.redis.url else "localhost",
        port=6379,
    )
    redis = RedisAdapter(redis_config)
    app.state.redis = redis
    if redis.enabled:
        logger.info("✓ Redis connected")

    # PostgreSQL
    from sentinel.storage import PostgreSQLConfig
    from urllib.parse import urlparse

    # Parse database URL to extract connection parameters
    db_url = urlparse(saas_config.database.url)
    postgres_config = PostgreSQLConfig(
        host=db_url.hostname or "localhost",
        port=db_url.port or 5432,
        database=db_url.path.lstrip("/") or "sentinel",
        user=db_url.username or "sentinel_user",
        password=db_url.password or "sentinel_password",
    )
    postgres = PostgreSQLAdapter(postgres_config)
    app.state.postgres = postgres
    if postgres.enabled:
        logger.info(f"✓ PostgreSQL connected: {postgres_config.host}:{postgres_config.port}")

    # Rate Limiter
    rate_limit_config = RateLimitConfig(
        requests_per_second=10,
        requests_per_minute=100,
        requests_per_hour=1000,
    )
    rate_limiter = RateLimiter(rate_limit_config)
    app.state.rate_limiter = rate_limiter
    logger.info("✓ Rate limiting enabled")

    # Sentinel Gateway
    sentinel_config = SentinelConfig()
    gateway = SentinelGateway(sentinel_config)
    app.state.gateway = gateway
    logger.info("✓ Sentinel Gateway initialized")

    app.state.config = saas_config
    app.state.logger = logger

    # ========================================================================
    # INCLUDE SAAS ROUTERS
    # ========================================================================

    app.include_router(auth_router)
    app.include_router(organizations_router)
    app.include_router(workspaces_router)
    app.include_router(dashboard_router)
    app.include_router(policies_router)
    app.include_router(audit_router)
    app.include_router(api_keys_router)
    app.include_router(reports_router)

    logger.info("✓ SaaS management routes registered")

    return app


# ============================================================================
# CREATE APP INSTANCE
# ============================================================================

app = create_saas_app()


# ============================================================================
# MIDDLEWARE
# ============================================================================

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header"""
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000  # ms
    response.headers["X-Process-Time-Ms"] = str(process_time)
    return response


@app.middleware("http")
async def collect_metrics(request: Request, call_next):
    """Collect request metrics"""
    if app.state.metrics:
        collector = MetricsCollector(app.state.metrics)
        collector.start_request("saas-api")

        try:
            response = await call_next(request)
            collector.end_request("saas-api", "success")
            return response
        except Exception as e:
            collector.end_request("saas-api", "error")
            collector.record_error("saas-api", type(e).__name__)
            raise
    else:
        return await call_next(request)


# ============================================================================
# CORE SECURITY ENDPOINTS (MULTI-TENANT)
# ============================================================================

@app.post("/process", response_model=ProcessResponse)
async def process_input(
    req: ProcessRequest,
    request: Request,
    api_key_data: dict = Depends(get_api_key_user),
    db: Session = Depends(get_db),
):
    """
    Process user input through all security layers (Multi-Tenant)

    **Authentication:** Requires valid API key in X-API-Key header

    **Request Headers:**
    ```
    X-API-Key: sk_live_abc123...
    ```

    **Request Body:**
    ```json
    {
      "user_input": "What is my credit card number 4532-1234-5678-9010?",
      "user_id": "customer_123",
      "workspace_id": "770e8400-...",
      "metadata": {"source": "mobile_app"}
    }
    ```

    **Response:**
    ```json
    {
      "allowed": false,
      "redacted_input": "What is my credit card number [CREDIT_CARD_REDACTED]?",
      "risk_score": 0.95,
      "risk_level": "high",
      "blocked": true,
      "block_reason": "PII detected: credit_card",
      "pii_detected": true,
      "pii_count": 1,
      "injection_detected": false,
      "escalated": false,
      "processing_time_ms": 45.2,
      "session_id": "550e8400-...",
      "org_id": "660e8400-...",
      "workspace_id": "770e8400-..."
    }
    ```

    **Flow:**
    1. Authenticate via API key
    2. Extract org_id and workspace_id from API key
    3. Check rate limits (per org/workspace)
    4. Process input through Sentinel security layers
    5. Save audit log with multi-tenant context
    6. Update organization API usage stats
    7. Return security analysis result
    """
    start_time = time.time()
    logger = app.state.logger

    # Extract multi-tenant context from API key
    org_id = api_key_data["org_id"]
    workspace_id = req.workspace_id or api_key_data.get("workspace_id")

    # Get organization for rate limit enforcement
    org = db.query(Organization).filter(Organization.org_id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check organization is active and within limits
    if not org.is_active:
        raise HTTPException(status_code=403, detail="Organization is suspended")

    if not org.is_within_limits:
        raise HTTPException(
            status_code=429,
            detail=f"Organization has exceeded usage limits. Current: {org.api_requests_this_month}/{org.max_api_requests_per_month} requests."
        )

    # Rate limiting (per API key)
    if app.state.rate_limiter:
        user_id = req.user_id or str(api_key_data["key_id"])
        ip_address = req.ip_address or request.client.host

        allowed, reason = app.state.rate_limiter.check_rate_limit(
            user_id=user_id,
            ip_address=ip_address,
        )

        if not allowed:
            if app.state.metrics:
                app.state.metrics.blocks_total.labels(layer="rate_limiter", reason=reason).inc()

            raise HTTPException(status_code=429, detail=f"Rate limit exceeded: {reason}")

    # Create initial state
    state = create_initial_state(
        user_input=req.user_input,
        config=app.state.gateway.config,
        user_id=req.user_id,
        user_role=req.user_role,
        ip_address=req.ip_address or request.client.host,
        metadata={
            **(req.metadata or {}),
            "org_id": str(org_id),
            "workspace_id": str(workspace_id) if workspace_id else None,
        },
        session_id=req.session_id,
    )

    session_id = state["session_id"]

    # Demo agent executor
    def demo_agent(redacted_input: str) -> str:
        responses = {
            "weather": "The weather is sunny and 72°F today.",
            "hello": "Hello! How can I assist you today?",
            "default": f"I've processed your request: '{redacted_input[:50]}...' - This is a demo response."
        }

        lower_input = redacted_input.lower()
        if "weather" in lower_input:
            return responses["weather"]
        elif "hello" in lower_input or "hi" in lower_input:
            return responses["hello"]
        else:
            return responses["default"]

    # Process through Sentinel security layers
    result = app.state.gateway.invoke(
        user_input=req.user_input,
        agent_executor=demo_agent
    )
    result_state = result

    # Collect metrics
    if app.state.metrics:
        collector = MetricsCollector(app.state.metrics)
        threats = result_state.get("threats", [])

        if threats:
            max_risk = max([t.get("risk_score", 0.0) for t in threats] if isinstance(threats[0], dict) else [t.risk_score for t in threats], default=0.0)
            collector.record_risk_score("overall", max_risk)

        if result_state.get("blocked"):
            collector.record_block("overall", "security_threat")

    # Save to Redis (session state)
    if app.state.redis and app.state.redis.enabled:
        app.state.redis.save_session_state(session_id, result_state, ttl=3600)

    # Save to PostgreSQL with multi-tenant context
    if app.state.postgres and app.state.postgres.enabled:
        # Convert state to dict if it's a Pydantic model
        state_dict = state.model_dump() if hasattr(state, 'model_dump') else state

        threats = result_state.get("threats", [])
        max_risk = 0.0
        injection_type = None
        injection_confidence = None

        # Extract PII detection info from audit_log
        audit_log = result_state.get("audit_log", {})
        pii_count = audit_log.get("pii_redactions", 0)
        pii_detected = pii_count > 0

        # Extract redacted entities from original_entities
        redacted_entities = []
        original_entities = result_state.get("original_entities", [])

        if original_entities:
            # Extract entity types and values
            redacted_entities = [                
                {
        "entity_type": entity.get("entity_type") if isinstance(entity, dict) else getattr(entity, "entity_type", "unknown"),
        "original_value": entity.get("original_value") if isinstance(entity, dict) else getattr(entity, "original_value", ""),
        "redacted_value": entity.get("redacted_value") if isinstance(entity, dict) else getattr(entity, "redacted_value", ""),
        "start_position": entity.get("start_position") if isinstance(entity, dict) else getattr(entity, "start_position", 0),
        "end_position": entity.get("end_position") if isinstance(entity, dict) else getattr(entity, "end_position", 0),
        "confidence": entity.get("confidence") if isinstance(entity, dict) else getattr(entity, "confidence", 0.0),
        "detection_method": entity.get("detection_method") if isinstance(entity, dict) else getattr(entity, "detection_method", "regex"),
        "redaction_strategy": entity.get("redaction_strategy") if isinstance(entity, dict) else getattr(entity, "redaction_strategy", "token"),
        "token_id": entity.get("token_id") if isinstance(entity, dict) else getattr(entity, "token_id", ""),
    }

                for entity in original_entities
            ]

        if threats and isinstance(threats[0], dict):
            # Extract risk score from threat evidence or calculate from severity
            risk_scores = []
            for t in threats:
                # Try to get risk_score from evidence first
                evidence = t.get("evidence", {})
                risk = evidence.get("risk_score", None)

                # If not in evidence, calculate from severity
                if risk is None:
                    severity = t.get("severity", "low")
                    severity_map = {"critical": 0.95, "high": 0.8, "medium": 0.5, "low": 0.2, "none": 0.0}
                    risk = severity_map.get(severity, 0.0)

                risk_scores.append(risk)

            max_risk = max(risk_scores) if risk_scores else 0.0

            # Extract injection type from threats
            for threat in threats:
                threat_type = threat.get("threat_type", "")
                if "injection" in threat_type.lower():
                    injection_confidence = threat.get("confidence", 0.0)

                    # Classify injection type based on patterns
                    user_input_lower = req.user_input.lower()
                    if any(keyword in user_input_lower for keyword in ["select", "drop", "insert", "update", "delete", "union", "--", "/*"]):
                        injection_type = "SQL Injection"
                    elif any(keyword in user_input_lower for keyword in ["<script", "javascript:", "onerror=", "onload=", "<img", "<iframe"]):
                        injection_type = "XSS (Cross-Site Scripting)"
                    elif any(keyword in user_input_lower for keyword in ["system:", "ignore previous", "disregard", "you are now", "new instructions"]):
                        injection_type = "Prompt Injection"
                    elif any(keyword in user_input_lower for keyword in ["../", "..\\", "/etc/passwd", "c:\\"]):
                        injection_type = "Path Traversal"
                    elif any(keyword in user_input_lower for keyword in ["{", "}", "{{", "}}", "${", "<%", "%>"]):
                        injection_type = "Template Injection"
                    else:
                        injection_type = "Code Injection"
                    break

        audit_log_data = {
            "timestamp": state.request_context.request_timestamp if hasattr(state, 'request_context') else datetime.utcnow(),
            "session_id": session_id,
            "request_id": state_dict.get("request_id"),
            "request_context": state_dict.get("request_context", {}),
            "user_input": req.user_input,
            "redacted_input": result_state.get("redacted_input", ""),
            "org_id": str(org_id),
            "blocked": result_state.get("blocked", False),
            "aggregated_risk": {"overall_risk_score": max_risk, "overall_risk_level": "high" if max_risk > 0.7 else "medium" if max_risk > 0.4 else "low"},
            "pii_detected": pii_detected,
            "redacted_entities": redacted_entities,
            "injection_detected": result_state.get("blocked", False) and injection_type is not None,
            "injection_details": {"injection_type": injection_type, "confidence": injection_confidence} if injection_type else {},
            "escalated": False,
            "escalated_to": None,
            "metadata": {
                **(req.metadata or {}),
                "org_id": str(org_id),
                "workspace_id": str(workspace_id) if workspace_id else None,
            },
        }
        print('Audit Log Data:', audit_log_data)
        app.state.postgres.save_audit_log(audit_log_data)

    # Update organization API request count
    org.api_requests_this_month += 1
    db.commit()

    # Log security event
    if result_state.get("blocked"):
        threats = result_state.get("threats", [])
        max_risk = 0.0

        # Calculate risk score using same logic
        if threats:
            risk_scores = []
            for t in threats:
                if isinstance(t, dict):
                    evidence = t.get("evidence", {})
                    risk = evidence.get("risk_score", None)
                    if risk is None:
                        severity = t.get("severity", "low")
                        severity_map = {"critical": 0.95, "high": 0.8, "medium": 0.5, "low": 0.2, "none": 0.0}
                        risk = severity_map.get(severity, 0.0)
                    risk_scores.append(risk)
            max_risk = max(risk_scores) if risk_scores else 0.0

        log_security_event(
            event_type=EventType.SECURITY_VIOLATION,
            message=f"Request blocked for org {org_id}",
            request_id=state.get("request_id"),
            session_id=session_id,
            user_id=req.user_id,
            risk_score=max_risk,
            blocked=True,
            layer="gateway",
        )

    # Calculate processing time
    processing_time_ms = (time.time() - start_time) * 1000

    # Build response
    audit_log = result_state.get("audit_log", {})
    threats = result_state.get("threats", [])

    # Calculate max risk score using same logic as audit log
    max_risk_score = 0.0
    if threats:
        risk_scores = []
        for t in threats:
            if isinstance(t, dict):
                # Try to get risk_score from evidence first
                evidence = t.get("evidence", {})
                risk = evidence.get("risk_score", None)

                # If not in evidence, calculate from severity
                if risk is None:
                    severity = t.get("severity", "low")
                    severity_map = {"critical": 0.95, "high": 0.8, "medium": 0.5, "low": 0.2, "none": 0.0}
                    risk = severity_map.get(severity, 0.0)

                risk_scores.append(risk)
            else:
                # Handle non-dict threats (Pydantic models)
                risk_scores.append(getattr(t, "risk_score", 0.0))

        max_risk_score = max(risk_scores) if risk_scores else 0.0

    pii_count = audit_log.get("pii_redactions", 0)
    pii_detected = pii_count > 0
    injection_detected = audit_log.get("injection_attempts", 0) > 0
    #redacted_input = req.user_input if not pii_detected else "[PII Redacted]"
    redacted_input = result_state.get("redacted_input", req.user_input)
    return ProcessResponse(
        allowed=not result_state.get("blocked", False),
        redacted_input=redacted_input,
        risk_score=max_risk_score,
        risk_level="high" if max_risk_score > 0.7 else "medium" if max_risk_score > 0.4 else "low",
        blocked=result_state.get("blocked", False),
        block_reason="Security threat detected" if result_state.get("blocked") else None,
        pii_detected=pii_detected,
        pii_count=pii_count,
        injection_detected=injection_detected,
        escalated=result_state.get("shadow_agent_escalated", False),
        processing_time_ms=processing_time_ms,
        session_id=session_id,
        org_id=org_id,
        workspace_id=workspace_id,
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    components = {
        "gateway": "healthy",
        "redis": "healthy" if (app.state.redis and app.state.redis.ping()) else "unavailable",
        "metrics": "enabled",
        "tracing": "enabled" if app.state.tracer else "disabled",
        "database": "healthy",  # SQLAlchemy connection pool
    }

    return HealthResponse(
        status="healthy",
        version="2.0.0",
        mode="saas",
        components=components,
    )


@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    if app.state.redis and app.state.redis.enabled:
        if not app.state.redis.ping():
            raise HTTPException(status_code=503, detail="Redis not ready")

    return {"status": "ready"}


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    if not app.state.metrics:
        raise HTTPException(status_code=404, detail="Metrics not enabled")

    metrics_data = app.state.metrics.export_metrics()
    return PlainTextResponse(
        content=metrics_data.decode("utf-8"),
        media_type=app.state.metrics.get_content_type(),
    )


# ============================================================================
# MAIN (for development)
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "sentinel.saas.server:app",
        host=saas_config.api.host,
        port=saas_config.api.port,
        workers=saas_config.api.workers,
        log_level="info",
        reload=saas_config.api.reload,
    )
