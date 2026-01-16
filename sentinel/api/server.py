"""
FastAPI Server - Complete Integration
Integrates all 4 phases: Risk Scoring, Shadow Agents, Meta-Learning, Production Infrastructure
"""

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import time
import uvicorn

# Sentinel Components (Phases 1-3)
from sentinel import SentinelConfig, SentinelGateway, create_initial_state, EventType
from sentinel.meta_learning import (
    MetaLearningAgent,
    RuleManager,
    ThreatIntelligence,
    ApprovalWorkflow,
    MetaLearningReports,
    MetaLearningConfig,
)

# Phase 4: Production Infrastructure
from sentinel.observability import (
    SentinelMetrics,
    SentinelTracer,
    MetricsCollector,
    setup_logging,
    get_logger,
    log_security_event,
)
from sentinel.storage import RedisAdapter, RedisConfig, PostgreSQLAdapter, PostgreSQLConfig
from sentinel.resilience import (
    CircuitBreaker,
    RateLimiter,
    RateLimitConfig,
    RateLimitExceeded,
)

from .config import APIConfig, get_config

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ProcessRequest(BaseModel):
    """Request to process user input"""
    user_input: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    user_role: Optional[str] = None
    ip_address: Optional[str] = None
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


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    components: Dict[str, str]


# ============================================================================
# APPLICATION FACTORY
# ============================================================================

def create_app(config: Optional[APIConfig] = None) -> FastAPI:
    """
    Create and configure FastAPI application

    Args:
        config: API configuration (default: from environment)

    Returns:
        Configured FastAPI app
    """
    if config is None:
        config = get_config()

    app = FastAPI(
        title="Sentinel AI Security Control Plane",
        description="Production-ready AI security with 4-layer defense",
        version="1.0.0",
    )

    # ========================================================================
    # CORS
    # ========================================================================

    if config.cors_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # ========================================================================
    # INITIALIZE COMPONENTS
    # ========================================================================

    # Logging
    if config.enable_logging:
        setup_logging(level=config.log_level, json_format=True)
        logger = get_logger("api")
        logger.info("Starting Sentinel API Server")

    # Metrics
    if config.enable_metrics:
        metrics = SentinelMetrics()
        app.state.metrics = metrics
        logger.info("✓ Prometheus metrics enabled")
    else:
        app.state.metrics = None

    # Tracing
    if config.enable_tracing:
        tracer = SentinelTracer(
            service_name="sentinel-api",
            otlp_endpoint=config.otlp_endpoint,
            console_export=False,
        )
        app.state.tracer = tracer
        logger.info(f"✓ OpenTelemetry tracing enabled (endpoint: {config.otlp_endpoint})")
    else:
        app.state.tracer = None

    # Redis
    if config.redis_enabled:
        redis_config = RedisConfig(
            host=config.redis_host,
            port=config.redis_port,
            password=config.redis_password,
        )
        redis = RedisAdapter(redis_config)
        app.state.redis = redis
        if redis.enabled:
            logger.info(f"✓ Redis connected: {config.redis_host}:{config.redis_port}")
    else:
        app.state.redis = None

    # PostgreSQL
    if config.postgres_enabled:
        postgres_config = PostgreSQLConfig(
            host=config.postgres_host,
            port=config.postgres_port,
            database=config.postgres_db,
            user=config.postgres_user,
            password=config.postgres_password,
        )
        postgres = PostgreSQLAdapter(postgres_config)
        app.state.postgres = postgres
        if postgres.enabled:
            logger.info(f"✓ PostgreSQL connected: {config.postgres_host}:{config.postgres_port}")
    else:
        app.state.postgres = None

    # Rate Limiter
    if config.rate_limit_enabled:
        rate_limit_config = RateLimitConfig(
            requests_per_second=config.requests_per_second,
            requests_per_minute=config.requests_per_minute,
            requests_per_hour=config.requests_per_hour,
        )
        rate_limiter = RateLimiter(rate_limit_config)
        app.state.rate_limiter = rate_limiter
        logger.info("✓ Rate limiting enabled")
    else:
        app.state.rate_limiter = None

    # Circuit Breaker (for LLM calls)
    if config.circuit_breaker_enabled:
        circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_breaker_threshold,
            recovery_timeout=config.circuit_breaker_timeout,
        )
        app.state.circuit_breaker = circuit_breaker
        logger.info("✓ Circuit breaker enabled")
    else:
        app.state.circuit_breaker = None

    # Sentinel Gateway (Phases 1-3)
    sentinel_config = SentinelConfig()
    gateway = SentinelGateway(sentinel_config)
    app.state.gateway = gateway
    logger.info("✓ Sentinel Gateway initialized")

    # Meta-Learning Components
    meta_config = MetaLearningConfig()
    app.state.meta_agent = MetaLearningAgent(meta_config)
    app.state.rule_manager = RuleManager(storage_path="./rule_versions")
    app.state.threat_intel = ThreatIntelligence()
    logger.info("✓ Meta-learning components initialized")

    app.state.config = config
    app.state.logger = logger

    # ========================================================================
    # INCLUDE SAAS ROUTERS
    # ========================================================================

    from sentinel.saas.routers import (
        auth,
        dashboard,
        policies,
        audit,
        reports,
        api_keys,
        organizations,
        workspaces,
    )

    app.include_router(auth.router, tags=["Authentication"])
    app.include_router(dashboard.router, tags=["Dashboard"])
    app.include_router(policies.router, tags=["Policies"])
    app.include_router(audit.router, tags=["Audit Logs"])
    app.include_router(reports.router, tags=["Reports"])
    app.include_router(api_keys.router, tags=["API Keys"])
    app.include_router(organizations.router, tags=["Organizations"])
    app.include_router(workspaces.router, tags=["Workspaces"])

    logger.info("✓ SaaS routers registered")

    return app


# ============================================================================
# CREATE APP INSTANCE
# ============================================================================

app = create_app()


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
        collector.start_request("api")

        try:
            response = await call_next(request)
            collector.end_request("api", "success")
            return response
        except Exception as e:
            collector.end_request("api", "error")
            collector.record_error("api", type(e).__name__)
            raise
    else:
        return await call_next(request)


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.post("/process", response_model=ProcessResponse)
async def process_input(
    req: ProcessRequest,
    request: Request,
    api_key_data: dict = Depends(lambda x_api_key: None)  # Will be replaced with proper dependency
):
    """
    Process user input through all security layers

    Phases executed:
    1. Risk Scoring (input guard, state monitor, output guard)
    2. Shadow Agents (if high risk)
    3. Metrics/Tracing (Phase 4)
    4. Audit logging (Phase 4)

    Requires X-API-Key header for authentication
    """
    print("Start Server processing request...")
    start_time = time.time()
    logger = app.state.logger

    # Extract API key from header
    from fastapi import Header
    from typing import Optional
    x_api_key = request.headers.get("x-api-key")
    print('X-API-Key:', x_api_key)
    # Get org_id and workspace_id from API key
    org_id = None
    workspace_id = None
    if x_api_key:
        from sentinel.saas.dependencies import get_db
        from sentinel.saas.auth import APIKeyValidator
        db = next(get_db())
        try:
            validator = APIKeyValidator(db)
            key_data = validator.validate_api_key(x_api_key)
            if key_data:
                org_id = key_data.get("org_id")
                workspace_id = key_data.get("workspace_id")
        finally:
            db.close()
    print('org_id, workspace_id:', org_id, workspace_id)
    # Rate limiting
    if app.state.rate_limiter:
        user_id = req.user_id or "anonymous"
        ip_address = req.ip_address or request.client.host

        allowed, reason = app.state.rate_limiter.check_rate_limit(
            user_id=user_id, 
            ip_address=ip_address,
        )

        if not allowed:
            if app.state.metrics:
                app.state.metrics.blocks_total.labels(layer="rate_limiter", reason=reason).inc()

            raise HTTPException(status_code=429, detail=f"Rate limit exceeded: {reason}")

    # Create initial state (preserve session_id if provided)
    state = create_initial_state(
        user_input=req.user_input,
        config=app.state.gateway.config,
        user_id=req.user_id,
        user_role=req.user_role,
        ip_address=req.ip_address or request.client.host,
        metadata=req.metadata or {},
        session_id=req.session_id,  # Use provided session_id or auto-generate
    )
    print('Initial state:', state)
    session_id = state["session_id"]

    # Demo agent executor - simulates an AI agent
    def demo_agent(redacted_input: str) -> str:
        """
        Demo AI agent that the security system protects.
        In production, this would be your real AI/LLM agent.
        """
        # Simulate agent processing
        responses = {
            "weather": "The weather is sunny and 72°F today.",
            "hello": "Hello! How can I assist you today?",
            "default": f"I've processed your request: '{redacted_input[:50]}...' - This is a demo response from the protected AI agent."
        }

        lower_input = redacted_input.lower()
        if "weather" in lower_input:
            return responses["weather"]
        elif "hello" in lower_input or "hi" in lower_input:
            return responses["hello"]
        else:
            return responses["default"]

    # Start tracing
    if app.state.tracer and app.state.tracer.enabled:
        with app.state.tracer.trace_request(session_id, req.user_input) as span:
            result = app.state.gateway.invoke(
                user_input=req.user_input,
                agent_executor=demo_agent  # Pass the demo agent
            )
            result_state = result  # The invoke returns a state dict
            span.set_attribute("blocked", result.get("blocked", False))
            span.set_attribute("risk_score", result.get("threats", [{}])[0].get("risk_score", 0.0) if result.get("threats") else 0.0)
    else:
        result = app.state.gateway.invoke(
            user_input=req.user_input,
            agent_executor=demo_agent  # Pass the demo agent
        )
        result_state = result
    print('Result state:', result_state)
    # Collect metrics
    if app.state.metrics:
        collector = MetricsCollector(app.state.metrics)
        threats = result_state.get("threats", [])

        # Risk score
        if threats:
            max_risk = max([t.get("risk_score", 0.0) for t in threats] if isinstance(threats[0], dict) else [t.risk_score for t in threats], default=0.0)
            collector.record_risk_score("overall", max_risk)

        # PII and Injection - simplified
        if result_state.get("blocked"):
            collector.record_block("overall", "security_threat")

    # Save to Redis (session state)
    if app.state.redis and app.state.redis.enabled:
        app.state.redis.save_session_state(session_id, result_state, ttl=3600)
    pii_detected = pii_count > 0
    # Save to PostgreSQL (audit log)
    if app.state.postgres and app.state.postgres.enabled:
        threats = result_state.get("threats", [])
        max_risk = 0.0
        if threats and isinstance(threats[0], dict):
            max_risk = max([t.get("risk_score", 0.0) for t in threats], default=0.0)

        # Prepare metadata with org_id and workspace_id
        metadata = req.metadata or {}
        if org_id:
            metadata["org_id"] = str(org_id)
        if workspace_id:
            metadata["workspace_id"] = str(workspace_id)
        print('metadata for audit log:', metadata)
        audit_log_data = {
            "timestamp": state["request_context"]["timestamp"],
            "session_id": session_id,
            "request_id": state.get("request_id"),
            "request_context": state["request_context"],
            "user_input": req.user_input,
            "blocked": result_state.get("blocked", False),
            "aggregated_risk": {"overall_risk_score": max_risk},
            "pii_detected": pii_detected,
            "redacted_entities": result_state.get("original_entities", []),
            "injection_detected": result_state.get("blocked", False),
            "injection_details": None,
            "escalated": False,
            "escalated_to": None,
            "metadata": metadata,
        }
        app.state.postgres.save_audit_log(audit_log_data)

    # Log security event
    if result_state.get("blocked"):
        threats = result_state.get("threats", [])
        max_risk = 0.0
        if threats and isinstance(threats[0], dict):
            max_risk = max([t.get("risk_score", 0.0) for t in threats], default=0.0)

        log_security_event(
            event_type=EventType.SECURITY_VIOLATION,
            message=f"Request blocked: security threat detected",
            request_id=state.get("request_id"),
            session_id=session_id,
            user_id=req.user_id,
            risk_score=max_risk,
            blocked=True,
            layer="gateway",
        )
  
    # Calculate processing time
    processing_time_ms = (time.time() - start_time) * 1000

    # Build response from invoke result
    audit_log = result_state.get("audit_log", {})
    threats = result_state.get("threats", [])

    # Extract threat info - handle both dict and object formats
    max_risk_score = 0.0
    if threats:
        if isinstance(threats[0], dict):
            max_risk_score = max([t.get("risk_score", 0.0) for t in threats], default=0.0)
        else:
            max_risk_score = max([t.risk_score for t in threats], default=0.0)

    # Extract PII information from audit log
    pii_count = audit_log.get("pii_redactions", 0)
    pii_detected = pii_count > 0

    # Extract injection detection from audit log
    injection_detected = audit_log.get("injection_attempts", 0) > 0

    # Get redacted input from the state (already properly redacted by input guard)
    print('result_state:', result_state)
    redacted_input = result_state.get("redacted_input", req.user_input)
    # Get risk score from input guard risk scores
    # Priority: risk_scores from input_guard layer > aggregated_risk > threats
    final_risk_score = 0.0
    risk_scores = result_state.get("risk_scores", [])
    
    # Find the input_guard risk score
    for risk_score in risk_scores:
        if risk_score.get("layer") == "input_guard":
            final_risk_score = risk_score.get("risk_score", 0.0)
            break
    
    # Fallback to aggregated risk if no input_guard score
    if final_risk_score == 0.0:
        aggregated_risk = result_state.get("aggregated_risk", {})
        final_risk_score = aggregated_risk.get("overall_risk_score", max_risk_score)
    print('redacted_input##### :', redacted_input)
    return ProcessResponse(
        allowed=not result_state.get("blocked", False),
        redacted_input=redacted_input, 
        risk_score=final_risk_score,
        risk_level="high" if final_risk_score > 0.7 else "medium" if final_risk_score > 0.4 else "low",
        blocked=result_state.get("blocked", False),
        block_reason="Security threat detected" if result_state.get("blocked") else None,
        pii_detected=pii_detected,
        pii_count=pii_count,
        injection_detected=injection_detected,
        escalated=result_state.get("shadow_agent_escalated", False),
        org_id=org_id,
        workspace_id=workspace_id,
        processing_time_ms=processing_time_ms,
        session_id=session_id,
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    components = {
        "gateway": "healthy",
        "redis": "healthy" if (app.state.redis and app.state.redis.ping()) else "unavailable",
        "postgres": "healthy" if (app.state.postgres and app.state.postgres.ping()) else "unavailable",
        "metrics": "enabled" if app.state.metrics else "disabled",
        "tracing": "enabled" if app.state.tracer else "disabled",
    }

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        components=components,
    )


@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    # Check critical dependencies
    if app.state.redis and app.state.redis.enabled:
        if not app.state.redis.ping():
            raise HTTPException(status_code=503, detail="Redis not ready")

    if app.state.postgres and app.state.postgres.enabled:
        if not app.state.postgres.ping():
            raise HTTPException(status_code=503, detail="PostgreSQL not ready")

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


@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    stats = {
        "redis": app.state.redis.get_stats() if app.state.redis else {"enabled": False},
        "circuit_breaker": (
            app.state.circuit_breaker.get_stats()
            if app.state.circuit_breaker
            else {"enabled": False}
        ),
    }

    return stats


# ============================================================================
# MAIN (for development)
# ============================================================================

if __name__ == "__main__":
    config = get_config()

    uvicorn.run(
        "sentinel.api.server:app",
        host=config.host,
        port=config.port,
        workers=config.workers,
        log_level=config.log_level.lower(),
        reload=False,  # Disable in production
    )
