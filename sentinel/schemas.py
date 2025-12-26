"""
Pydantic schemas for Sentinel Agentic Framework State Management
Aligned with LangGraph state tracking requirements
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict
from pydantic import BaseModel, Field, validator
import hashlib
import uuid


# ============================================================================
# ENUMERATIONS
# ============================================================================

class ThreatLevel(str, Enum):
    """Security threat severity levels"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RedactionStrategy(str, Enum):
    """Methods for redacting sensitive data"""
    MASK = "mask"              # "4111-****-****-1111"
    HASH = "hash"              # "SHA256:a3f2..."
    TOKEN = "token"            # "[REDACTED_SSN_001]"
    ENCRYPT = "encrypt"        # Encrypt and store, use token
    REMOVE = "remove"          # Complete removal


class EntityType(str, Enum):
    """Types of sensitive entities detected"""
    # PCI (Payment Card Industry)
    CREDIT_CARD = "credit_card"
    CVV = "cvv"
    CARD_EXPIRY = "card_expiry"

    # PII (Personally Identifiable Information)
    SSN = "ssn"
    EMAIL = "email"
    PHONE = "phone"
    DRIVERS_LICENSE = "drivers_license"
    PASSPORT = "passport"
    ADDRESS = "address"
    PERSON_NAME = "person_name"
    DATE_OF_BIRTH = "date_of_birth"

    # PHI (Protected Health Information)
    MEDICAL_RECORD_NUMBER = "medical_record_number"
    HEALTH_PLAN_NUMBER = "health_plan_number"
    DIAGNOSIS_CODE = "diagnosis_code"
    PRESCRIPTION = "prescription"

    # Secrets
    API_KEY = "api_key"
    PASSWORD = "password"
    JWT_TOKEN = "jwt_token"
    PRIVATE_KEY = "private_key"
    AWS_KEY = "aws_key"

    # Financial (Phase 1.7 expansion)
    IBAN = "iban"
    SWIFT_CODE = "swift_code"
    ROUTING_NUMBER = "routing_number"
    TAX_ID = "tax_id"
    VAT_NUMBER = "vat_number"

    # Network (Phase 1.7 expansion)
    IP_ADDRESS = "ip_address"
    MAC_ADDRESS = "mac_address"

    # Geographic (Phase 1.7 expansion)
    COORDINATES = "coordinates"


class InjectionType(str, Enum):
    """Types of prompt injection attacks"""
    DIRECT = "direct"                    # "Ignore previous instructions"
    INDIRECT = "indirect"                # Hidden in data
    JAILBREAK = "jailbreak"             # System override attempts
    SOCIAL_ENGINEERING = "social_engineering"
    ROLE_PLAY = "role_play"             # "Pretend you are..."
    ENCODING = "encoding"                # Base64, unicode tricks
    DELIMITER = "delimiter"              # Breaking prompt boundaries


class LoopType(str, Enum):
    """Types of detected loops"""
    EXACT = "exact"                     # Identical tool calls
    SEMANTIC = "semantic"               # Similar meaning
    CYCLIC = "cyclic"                   # A->B->A pattern
    PROGRESSIVE = "progressive"         # Slow progress with repetition


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks"""
    PCI_DSS = "pci_dss"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    CCPA = "ccpa"
    ISO27001 = "iso27001"


class EventType(str, Enum):
    """Audit event types"""
    USER_INPUT = "user_input"
    INPUT_VALIDATION = "input_validation"
    PII_DETECTION = "pii_detection"
    INJECTION_CHECK = "injection_check"
    AGENT_EXECUTION = "agent_execution"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    LOOP_DETECTION = "loop_detection"
    RED_TEAM_TEST = "red_team_test"
    OUTPUT_SANITIZATION = "output_sanitization"
    SECURITY_VIOLATION = "security_violation"
    COMPLIANCE_CHECK = "compliance_check"
    RISK_ASSESSMENT = "risk_assessment"
    SHADOW_AGENT_ANALYSIS = "shadow_agent_analysis"


class RiskLevel(str, Enum):
    """Risk level categories for escalation decisions"""
    NONE = "none"           # 0.0-0.2: No risk detected
    LOW = "low"             # 0.2-0.5: Minimal risk, fast path
    MEDIUM = "medium"       # 0.5-0.8: Moderate risk, may escalate
    HIGH = "high"           # 0.8-0.95: High risk, escalate to shadow agent
    CRITICAL = "critical"   # 0.95-1.0: Critical risk, immediate block


# ============================================================================
# CORE DATA MODELS
# ============================================================================

class RedactedEntity(BaseModel):
    """Represents a detected and redacted sensitive entity"""
    entity_type: EntityType
    original_value: Optional[str] = None  # Only stored if encrypted
    redacted_value: str
    redaction_strategy: RedactionStrategy
    start_position: int
    end_position: int
    confidence: float = Field(ge=0.0, le=1.0)
    token_id: str = Field(default_factory=lambda: f"REDACTED_{uuid.uuid4().hex[:8].upper()}")
    detection_method: str  # "regex", "ner", "ml_classifier"

    class Config:
        use_enum_values = True


class ToolCall(BaseModel):
    """Represents a tool invocation by the agent"""
    tool_id: str = Field(default_factory=lambda: f"tool_{uuid.uuid4().hex[:12]}")
    tool_name: str
    arguments: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # For loop detection
    arguments_hash: str = Field(default="")

    @validator('arguments_hash', always=True)
    def compute_hash(cls, v, values):
        """Compute hash of arguments for duplicate detection"""
        if 'arguments' in values:
            arg_str = str(sorted(values['arguments'].items()))
            return hashlib.sha256(arg_str.encode()).hexdigest()[:16]
        return v

    class Config:
        use_enum_values = True


class ToolResult(BaseModel):
    """Result from a tool execution"""
    tool_id: str
    tool_name: str
    result: Any
    success: bool
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    execution_time_ms: float


class SecurityThreat(BaseModel):
    """Detected security threat"""
    threat_id: str = Field(default_factory=lambda: f"threat_{uuid.uuid4().hex[:12]}")
    threat_type: str  # "injection", "data_leak", "tool_misuse"
    severity: ThreatLevel
    description: str
    detection_method: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    blocked: bool = False

    class Config:
        use_enum_values = True


class InjectionDetection(BaseModel):
    """Result of prompt injection analysis"""
    detected: bool
    injection_type: Optional[InjectionType] = None
    confidence: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    patterns_matched: List[str]
    explanation: str
    should_block: bool


class LoopDetection(BaseModel):
    """Result of loop detection analysis"""
    loop_detected: bool
    loop_type: Optional[LoopType] = None
    confidence: float = Field(ge=0.0, le=1.0)
    repetition_count: int
    tool_call_pattern: List[str]
    progress_made: bool
    suggested_action: str  # "continue", "warn", "block"

    class Config:
        use_enum_values = True


class ComplianceViolation(BaseModel):
    """Compliance framework violation"""
    violation_id: str = Field(default_factory=lambda: f"violation_{uuid.uuid4().hex[:12]}")
    framework: ComplianceFramework
    rule: str
    severity: ThreatLevel
    description: str
    evidence: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    remediation: str

    class Config:
        use_enum_values = True


class RedTeamTest(BaseModel):
    """Red team adversarial test result"""
    test_id: str = Field(default_factory=lambda: f"redteam_{uuid.uuid4().hex[:12]}")
    attack_vector: str
    payload: str
    agent_response: str
    vulnerability_found: bool
    severity: ThreatLevel
    description: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class AuditEvent(BaseModel):
    """Individual audit event"""
    event_id: str = Field(default_factory=lambda: f"event_{uuid.uuid4().hex[:12]}")
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any]
    user_input_hash: Optional[str] = None
    response_hash: Optional[str] = None

    class Config:
        use_enum_values = True


class AuditLog(BaseModel):
    """Complete audit log for a session"""
    session_id: str = Field(default_factory=lambda: f"session_{uuid.uuid4().hex}")
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    events: List[AuditEvent] = Field(default_factory=list)

    # Summary statistics
    total_events: int = 0
    pii_redactions: int = 0
    injection_attempts: int = 0
    loops_detected: int = 0
    compliance_violations: int = 0

    # Compliance
    frameworks: List[ComplianceFramework] = Field(default_factory=list)
    compliant: bool = True

    # Digital signature for tamper-proofing
    digital_signature: Optional[str] = None

    def add_event(self, event: AuditEvent):
        """Add an event and update statistics"""
        self.events.append(event)
        self.total_events += 1

    class Config:
        use_enum_values = True


class CostMetrics(BaseModel):
    """Cost and resource usage metrics"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    tool_calls_count: int = 0
    execution_time_ms: float = 0.0


class RiskScore(BaseModel):
    """Risk assessment for a specific security layer"""
    layer: str  # "input_guard", "state_monitor", "output_guard"
    risk_score: float = Field(ge=0.0, le=1.0, description="Normalized risk score 0.0-1.0")
    risk_level: RiskLevel
    risk_factors: Dict[str, float] = Field(default_factory=dict)  # Individual risk components
    explanation: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class AggregatedRiskScore(BaseModel):
    """Aggregated risk score across all security layers"""
    overall_risk_score: float = Field(ge=0.0, le=1.0)
    overall_risk_level: RiskLevel
    layer_scores: Dict[str, float] = Field(default_factory=dict)  # layer_name -> score
    risk_breakdown: Dict[str, Any] = Field(default_factory=dict)  # Detailed breakdown
    should_escalate: bool = False
    escalation_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class RequestContext(BaseModel):
    """Context information about the request and user"""
    user_id: Optional[str] = None
    user_role: Optional[str] = None  # "admin", "user", "guest"
    session_id: str
    trust_score: float = Field(default=0.5, ge=0.0, le=1.0, description="User trust score based on history")

    # Session history
    previous_requests_count: int = 0
    previous_violations_count: int = 0
    previous_escalations_count: int = 0

    # Request metadata
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Feature flags
    allow_shadow_agent_escalation: bool = True
    strict_mode: bool = False

    # Custom metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ShadowAgentAnalysis(BaseModel):
    """Result from shadow agent (LLM-powered) analysis"""
    agent_type: str  # "input_analyzer", "behavior_analyzer", "output_analyzer"
    analysis_performed: bool
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel

    # LLM analysis results
    intent_analysis: Optional[str] = None
    threat_assessment: Optional[str] = None
    recommendation: str  # "allow", "warn", "block"
    confidence: float = Field(ge=0.0, le=1.0)

    # Reasoning
    reasoning: str = ""
    evidence: Dict[str, Any] = Field(default_factory=dict)

    # Metadata
    llm_model: Optional[str] = None
    llm_provider: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


# ============================================================================
# LANGGRAPH STATE SCHEMA
# ============================================================================

class SentinelState(TypedDict):
    """
    Main state schema for LangGraph workflow
    Tracks all data through the Sentinel Control Plane
    """

    # ========================================================================
    # INPUT TRACKING
    # ========================================================================
    user_input: str
    """Original user input before any processing"""

    redacted_input: str
    """User input after PII/PCI/PHI redaction"""

    original_entities: List[Dict[str, Any]]
    """List of detected and redacted entities with metadata"""

    # ========================================================================
    # AGENT EXECUTION
    # ========================================================================
    agent_response: str
    """Raw response from the primary agent"""

    sanitized_response: str
    """Final response after output guard sanitization"""

    tool_calls: List[Dict[str, Any]]
    """List of all tool calls made by agent (for loop detection)"""

    tool_results: List[Dict[str, Any]]
    """Results from tool executions"""

    # ========================================================================
    # SECURITY ANALYSIS
    # ========================================================================
    security_threats: List[Dict[str, Any]]
    """Detected security threats and violations"""

    injection_detected: bool
    """Flag indicating if prompt injection was detected"""

    injection_details: Optional[Dict[str, Any]]
    """Details about detected injection attempt"""

    loop_detected: bool
    """Flag indicating if agent loop was detected"""

    loop_details: Optional[Dict[str, Any]]
    """Details about detected loop pattern"""

    red_team_results: List[Dict[str, Any]]
    """Results from red team adversarial testing"""

    # ========================================================================
    # RISK SCORING (Phase 1 Enhancement)
    # ========================================================================
    risk_scores: List[Dict[str, Any]]
    """Individual risk scores from each security layer"""

    aggregated_risk: Optional[Dict[str, Any]]
    """Aggregated risk assessment across all layers"""

    # ========================================================================
    # CONTEXT & SESSION (Phase 1 Enhancement)
    # ========================================================================
    request_context: Dict[str, Any]
    """Context about the request, user, and session"""

    # ========================================================================
    # SHADOW AGENT ANALYSIS (Phase 2 Enhancement)
    # ========================================================================
    shadow_agent_analyses: List[Dict[str, Any]]
    """Results from shadow agent (LLM-powered) analyses"""

    shadow_agent_escalated: bool
    """Flag indicating if request was escalated to shadow agents"""

    escalation_reason: Optional[str]
    """Reason for shadow agent escalation"""

    # ========================================================================
    # COMPLIANCE & AUDIT
    # ========================================================================
    audit_log: Dict[str, Any]
    """Complete audit trail for the session"""

    compliance_violations: List[Dict[str, Any]]
    """List of compliance framework violations"""

    compliance_frameworks: List[str]
    """Active compliance frameworks for this session"""

    # ========================================================================
    # METADATA
    # ========================================================================
    session_id: str
    """Unique session identifier"""

    timestamp: str
    """ISO-8601 timestamp of request"""

    cost_metrics: Dict[str, Any]
    """Token count and cost estimation"""

    # ========================================================================
    # CONTROL FLAGS
    # ========================================================================
    should_block: bool
    """Flag to block request from reaching agent"""

    block_reason: Optional[str]
    """Reason for blocking if should_block is True"""

    should_warn: bool
    """Flag to warn but allow request"""

    warning_message: Optional[str]
    """Warning message if should_warn is True"""

    # ========================================================================
    # ROUTING
    # ========================================================================
    next_node: Optional[str]
    """Next node to route to in LangGraph workflow"""


# ============================================================================
# CONFIGURATION SCHEMAS
# ============================================================================

class PIIDetectionConfig(BaseModel):
    """Configuration for PII detection"""
    enabled: bool = True
    entity_types: List[EntityType] = Field(
        default_factory=lambda: [
            EntityType.CREDIT_CARD,
            EntityType.SSN,
            EntityType.EMAIL,
            EntityType.PHONE,
            EntityType.PERSON_NAME,
        ]
    )
    redaction_strategy: RedactionStrategy = RedactionStrategy.TOKEN
    confidence_threshold: float = 0.7
    use_ner: bool = True
    use_regex: bool = True
    use_ml_classifier: bool = False

    class Config:
        use_enum_values = True


class InjectionDetectionConfig(BaseModel):
    """Configuration for injection detection"""
    enabled: bool = True
    detection_methods: List[str] = Field(
        default_factory=lambda: ["pattern", "semantic", "perplexity"]
    )
    confidence_threshold: float = 0.8
    block_threshold: float = 0.9
    check_embeddings: bool = True


class LoopDetectionConfig(BaseModel):
    """Configuration for loop detection"""
    enabled: bool = True
    max_identical_calls: int = 3
    semantic_similarity_threshold: float = 0.95
    window_size: int = 10  # Look back N tool calls
    warn_threshold: int = 2
    block_threshold: int = 4


class RedTeamConfig(BaseModel):
    """Configuration for red team testing"""
    enabled: bool = False  # Off by default (resource intensive)
    async_mode: bool = True
    attack_vectors: List[str] = Field(
        default_factory=lambda: ["jailbreak", "data_exfiltration", "prompt_leak"]
    )
    max_tests_per_session: int = 5


class ComplianceConfig(BaseModel):
    """Configuration for compliance frameworks"""
    frameworks: List[ComplianceFramework] = Field(default_factory=list)
    audit_all_events: bool = True
    generate_reports: bool = True
    sign_audit_logs: bool = True

    class Config:
        use_enum_values = True


class RiskScoringConfig(BaseModel):
    """Configuration for risk scoring and escalation (Phase 1)"""
    enabled: bool = True

    # Risk component weights (must sum to 1.0)
    pii_risk_weight: float = 0.4
    injection_risk_weight: float = 0.4
    loop_risk_weight: float = 0.1
    leak_risk_weight: float = 0.1

    # Escalation thresholds
    low_risk_threshold: float = 0.2  # 0.0-0.2: No risk
    medium_risk_threshold: float = 0.5  # 0.2-0.5: Low risk (fast path)
    high_risk_threshold: float = 0.8  # 0.5-0.8: Medium risk (may escalate)
    critical_risk_threshold: float = 0.95  # 0.8-0.95: High risk (escalate), 0.95+: Critical (block)

    # Shadow agent escalation (Phase 2)
    enable_shadow_agent_escalation: bool = False  # Off by default until Phase 2
    shadow_agent_threshold: float = 0.8  # Escalate to shadow agent if risk >= 0.8

    # Context-aware adjustments
    trust_score_modifier: bool = True  # Adjust risk based on user trust score
    strict_mode_multiplier: float = 1.2  # Increase risk scores in strict mode


class ShadowAgentEscalationConfig(BaseModel):
    """Configuration for shadow agent escalation (Phase 2)"""
    enabled: bool = False  # Disabled by default

    # Escalation thresholds
    low_risk_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    medium_risk_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    high_risk_threshold: float = Field(default=0.95, ge=0.0, le=1.0)

    # Which agents to enable
    enable_input_agent: bool = True
    enable_state_agent: bool = True
    enable_output_agent: bool = True

    # LLM Configuration
    llm_provider: str = "anthropic"  # "anthropic", "openai", "local"
    llm_model: str = "claude-3-5-haiku-20241022"  # Fast, cost-effective
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    max_tokens: int = 1024
    timeout_ms: int = 5000

    # Fallback and reliability
    fallback_to_rules: bool = True
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600

    # Circuit breaker
    circuit_breaker_enabled: bool = True
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_duration_seconds: int = 60


class SentinelConfig(BaseModel):
    """Complete Sentinel framework configuration"""
    pii_detection: PIIDetectionConfig = Field(default_factory=PIIDetectionConfig)
    injection_detection: InjectionDetectionConfig = Field(default_factory=InjectionDetectionConfig)
    loop_detection: LoopDetectionConfig = Field(default_factory=LoopDetectionConfig)
    red_team: RedTeamConfig = Field(default_factory=RedTeamConfig)
    compliance: ComplianceConfig = Field(default_factory=ComplianceConfig)
    risk_scoring: RiskScoringConfig = Field(default_factory=RiskScoringConfig)  # Phase 1 addition
    shadow_agents: ShadowAgentEscalationConfig = Field(default_factory=ShadowAgentEscalationConfig)  # Phase 2 addition

    # Global settings
    enable_input_guard: bool = True
    enable_output_guard: bool = True
    enable_state_monitor: bool = True

    # Performance
    max_execution_time_ms: int = 30000
    max_tokens_per_request: int = 100000

    class Config:
        use_enum_values = True


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_initial_state(
    user_input: str,
    config: SentinelConfig,
    user_id: Optional[str] = None,
    user_role: Optional[str] = None,
    ip_address: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> SentinelState:
    """
    Create initial state for LangGraph workflow

    Args:
        user_input: The user's input text
        config: Sentinel configuration
        user_id: Optional user identifier
        user_role: Optional user role (admin, user, guest)
        ip_address: Optional IP address
        metadata: Optional custom metadata
    """
    session_id = f"session_{uuid.uuid4().hex}"

    # Create request context
    request_context = RequestContext(
        user_id=user_id,
        user_role=user_role,
        session_id=session_id,
        trust_score=0.5,  # Default trust score, will be updated based on history
        ip_address=ip_address,
        metadata=metadata or {},
    )

    return SentinelState(
        # Input
        user_input=user_input,
        redacted_input=user_input,  # Will be updated by input guard
        original_entities=[],

        # Agent
        agent_response="",
        sanitized_response="",
        tool_calls=[],
        tool_results=[],

        # Security
        security_threats=[],
        injection_detected=False,
        injection_details=None,
        loop_detected=False,
        loop_details=None,
        red_team_results=[],

        # Risk scoring (Phase 1)
        risk_scores=[],
        aggregated_risk=None,

        # Context (Phase 1)
        request_context=request_context.dict(),

        # Shadow agents (Phase 2)
        shadow_agent_analyses=[],
        shadow_agent_escalated=False,
        escalation_reason=None,

        # Compliance
        audit_log=AuditLog(
            session_id=session_id,
            frameworks=config.compliance.frameworks
        ).dict(),
        compliance_violations=[],
        compliance_frameworks=[f.value for f in config.compliance.frameworks],

        # Metadata
        session_id=session_id,
        timestamp=datetime.utcnow().isoformat(),
        cost_metrics=CostMetrics().dict(),

        # Control
        should_block=False,
        block_reason=None,
        should_warn=False,
        warning_message=None,
        next_node=None,
    )


# Export all schemas
__all__ = [
    # Enums
    'ThreatLevel',
    'RedactionStrategy',
    'EntityType',
    'InjectionType',
    'LoopType',
    'ComplianceFramework',
    'EventType',
    'RiskLevel',  # Phase 1 addition

    # Core Models
    'RedactedEntity',
    'ToolCall',
    'ToolResult',
    'SecurityThreat',
    'InjectionDetection',
    'LoopDetection',
    'ComplianceViolation',
    'RedTeamTest',
    'AuditEvent',
    'AuditLog',
    'CostMetrics',

    # Phase 1 Models
    'RiskScore',
    'AggregatedRiskScore',
    'RequestContext',
    'ShadowAgentAnalysis',

    # State
    'SentinelState',

    # Configuration
    'PIIDetectionConfig',
    'InjectionDetectionConfig',
    'LoopDetectionConfig',
    'RedTeamConfig',
    'ComplianceConfig',
    'RiskScoringConfig',  # Phase 1 addition
    'SentinelConfig',

    # Helpers
    'create_initial_state',
]
