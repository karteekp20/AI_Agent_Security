"""
Sentinel Agentic Framework
Zero-Trust AI Security Control Plane

A comprehensive security middleware for LLM-based agents that provides:
- PII/PCI/PHI Detection and Redaction
- Prompt Injection Detection
- Loop Detection and Cost Monitoring
- Adversarial Red Team Testing
- Compliance Auditing (PCI-DSS, GDPR, HIPAA, SOC2)
- Tamper-proof Audit Logs

Usage:
    from sentinel import SentinelGateway, SentinelConfig

    # Configure
    config = SentinelConfig()

    # Create gateway
    gateway = SentinelGateway(config)

    # Protect your agent
    result = gateway.invoke(
        user_input="Hello, my SSN is 123-45-6789",
        agent_executor=my_agent_function
    )

    print(result["response"])  # Sanitized response
    print(result["audit_log"])  # Complete audit trail
"""

__version__ = "0.1.0"
__author__ = "Sentinel Security Team"

# Core components
from .gateway import SentinelGateway, SentinelMiddleware
from .schemas import (
    SentinelState,
    SentinelConfig,
    PIIDetectionConfig,
    InjectionDetectionConfig,
    LoopDetectionConfig,
    RedTeamConfig,
    ComplianceConfig,
    create_initial_state,
    # Enums
    EntityType,
    RedactionStrategy,
    ThreatLevel,
    InjectionType,
    LoopType,
    ComplianceFramework,
    EventType,
    # Models
    RedactedEntity,
    ToolCall,
    SecurityThreat,
    InjectionDetection,
    LoopDetection,
    ComplianceViolation,
    AuditLog,
    CostMetrics,
)

# Agents
from .input_guard import InputGuardAgent, PIIDetector, InjectionDetector
from .output_guard import OutputGuardAgent, DataLeakDetector, ResponseValidator
from .state_monitor import StateMonitorAgent, LoopDetector, CostMonitor
from .red_team import RedTeamAgent, AttackSimulator
from .audit import AuditManager, ComplianceChecker, ReportGenerator

__all__ = [
    # Version
    "__version__",

    # Main Gateway
    "SentinelGateway",
    "SentinelMiddleware",

    # Configuration
    "SentinelConfig",
    "PIIDetectionConfig",
    "InjectionDetectionConfig",
    "LoopDetectionConfig",
    "RedTeamConfig",
    "ComplianceConfig",

    # State
    "SentinelState",
    "create_initial_state",

    # Enums
    "EntityType",
    "RedactionStrategy",
    "ThreatLevel",
    "InjectionType",
    "LoopType",
    "ComplianceFramework",
    "EventType",

    # Data Models
    "RedactedEntity",
    "ToolCall",
    "SecurityThreat",
    "InjectionDetection",
    "LoopDetection",
    "ComplianceViolation",
    "AuditLog",
    "CostMetrics",

    # Agents
    "InputGuardAgent",
    "OutputGuardAgent",
    "StateMonitorAgent",
    "RedTeamAgent",
    "AuditManager",

    # Detectors
    "PIIDetector",
    "InjectionDetector",
    "DataLeakDetector",
    "ResponseValidator",
    "LoopDetector",
    "CostMonitor",
    "ComplianceChecker",
    "ReportGenerator",
    "AttackSimulator",
]
