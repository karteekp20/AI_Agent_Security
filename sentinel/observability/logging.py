"""
Structured JSON Logging
Production-grade logging with structured fields for easy parsing
"""

import logging
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum


class LogLevel(str, Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EventType(str, Enum):
    """Security event types"""
    SECURITY_VIOLATION = "security_violation"
    PII_DETECTION = "pii_detection"
    INJECTION_ATTEMPT = "injection_attempt"
    REQUEST_BLOCKED = "request_blocked"
    ESCALATION = "escalation"
    PATTERN_DISCOVERED = "pattern_discovered"
    PATTERN_DEPLOYED = "pattern_deployed"
    ROLLBACK = "rollback"
    THREAT_DETECTED = "threat_detected"
    AUDIT = "audit"


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging

    Outputs logs in JSON format for easy parsing by log aggregators
    (ELK, Splunk, Datadog, etc.)
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        if hasattr(record, "event_type"):
            log_data["event_type"] = record.event_type

        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id

        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        if hasattr(record, "risk_score"):
            log_data["risk_score"] = record.risk_score

        if hasattr(record, "blocked"):
            log_data["blocked"] = record.blocked

        if hasattr(record, "layer"):
            log_data["layer"] = record.layer

        if hasattr(record, "component"):
            log_data["component"] = record.component

        # Add exception info
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add custom extra fields
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra

        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable log formatter for development

    Outputs logs in a colorized, easy-to-read format
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors"""
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']

        # Base format
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        message = f"{color}[{record.levelname}]{reset} {timestamp} - {record.getMessage()}"

        # Add context
        context_parts = []

        if hasattr(record, "request_id"):
            context_parts.append(f"request_id={record.request_id}")

        if hasattr(record, "layer"):
            context_parts.append(f"layer={record.layer}")

        if hasattr(record, "risk_score"):
            context_parts.append(f"risk={record.risk_score:.2f}")

        if hasattr(record, "blocked"):
            context_parts.append(f"blocked={record.blocked}")

        if context_parts:
            message += f" ({', '.join(context_parts)})"

        # Add exception
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return message


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    Setup structured logging for Sentinel

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON formatting (True for production, False for dev)
        log_file: Optional log file path

    Returns:
        Configured root logger
    """
    # Get root logger
    logger = logging.getLogger("sentinel")
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Choose formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = HumanReadableFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter())  # Always use JSON for files
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific component

    Args:
        name: Logger name (e.g., "sentinel.input_guard")

    Returns:
        Logger instance
    """
    return logging.getLogger(f"sentinel.{name}")


# =============================================================================
# HELPER FUNCTIONS FOR SECURITY LOGGING
# =============================================================================

def log_security_event(
    event_type: EventType,
    message: str,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    risk_score: Optional[float] = None,
    blocked: Optional[bool] = None,
    layer: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
):
    """
    Log a security event

    Args:
        event_type: Type of security event
        message: Event description
        request_id: Request ID
        session_id: Session ID
        user_id: User ID
        risk_score: Risk score (0.0-1.0)
        blocked: Whether request was blocked
        layer: Security layer that triggered event
        extra: Additional context
    """
    logger = get_logger("security")

    log_kwargs = {
        "extra": {
            "event_type": event_type,
            "request_id": request_id,
            "session_id": session_id,
            "user_id": user_id,
            "risk_score": risk_score,
            "blocked": blocked,
            "layer": layer,
            "extra": extra or {},
        }
    }

    # Determine log level based on event type
    if event_type in [EventType.SECURITY_VIOLATION, EventType.REQUEST_BLOCKED]:
        logger.warning(message, **log_kwargs)
    elif event_type in [EventType.INJECTION_ATTEMPT, EventType.THREAT_DETECTED]:
        logger.error(message, **log_kwargs)
    else:
        logger.info(message, **log_kwargs)


def log_audit_event(
    action: str,
    user_id: str,
    resource: str,
    result: str,
    details: Optional[Dict[str, Any]] = None,
):
    """
    Log an audit event (for compliance tracking)

    Args:
        action: Action performed (e.g., "pattern_approved", "deployment_created")
        user_id: User who performed action
        resource: Resource affected (e.g., "pattern_abc123")
        result: Result of action (success, failure, etc.)
        details: Additional audit details
    """
    logger = get_logger("audit")

    logger.info(
        f"Audit: {action}",
        extra={
            "event_type": EventType.AUDIT,
            "action": action,
            "user_id": user_id,
            "resource": resource,
            "result": result,
            "details": details or {},
        }
    )


def log_pattern_discovery(
    patterns_count: int,
    high_confidence_count: int,
    time_window_hours: int,
    discovery_method: str,
):
    """Log pattern discovery event"""
    log_security_event(
        event_type=EventType.PATTERN_DISCOVERED,
        message=f"Discovered {patterns_count} patterns ({high_confidence_count} high confidence)",
        extra={
            "patterns_count": patterns_count,
            "high_confidence_count": high_confidence_count,
            "time_window_hours": time_window_hours,
            "discovery_method": discovery_method,
        }
    )


def log_deployment(
    version: str,
    deployment_type: str,
    percentage: int,
    patterns_added: int,
):
    """Log deployment event"""
    log_security_event(
        event_type=EventType.PATTERN_DEPLOYED,
        message=f"Deployed version {version} ({deployment_type}, {percentage}%)",
        extra={
            "version": version,
            "deployment_type": deployment_type,
            "percentage": percentage,
            "patterns_added": patterns_added,
        }
    )


def log_rollback(
    version_from: str,
    version_to: str,
    reason: str,
):
    """Log rollback event"""
    log_security_event(
        event_type=EventType.ROLLBACK,
        message=f"Rollback: {version_from} → {version_to}",
        extra={
            "version_from": version_from,
            "version_to": version_to,
            "reason": reason,
        }
    )


def log_pii_detection(
    entity_type: str,
    count: int,
    request_id: str,
    redacted: bool = True,
):
    """Log PII detection"""
    log_security_event(
        event_type=EventType.PII_DETECTION,
        message=f"Detected {count} {entity_type} entities",
        request_id=request_id,
        extra={
            "entity_type": entity_type,
            "count": count,
            "redacted": redacted,
        }
    )


def log_injection_attempt(
    injection_type: str,
    confidence: float,
    request_id: str,
    blocked: bool = True,
    user_input_preview: str = "",
):
    """Log injection attempt"""
    log_security_event(
        event_type=EventType.INJECTION_ATTEMPT,
        message=f"Injection attempt detected: {injection_type} (confidence: {confidence:.2%})",
        request_id=request_id,
        blocked=blocked,
        risk_score=confidence,
        extra={
            "injection_type": injection_type,
            "confidence": confidence,
            "user_input_preview": user_input_preview[:100],
        }
    )


def log_escalation(
    agent_type: str,
    risk_score: float,
    request_id: str,
    reason: str,
):
    """Log escalation to shadow agent"""
    log_security_event(
        event_type=EventType.ESCALATION,
        message=f"Escalated to {agent_type} (risk: {risk_score:.2f})",
        request_id=request_id,
        risk_score=risk_score,
        extra={
            "agent_type": agent_type,
            "reason": reason,
        }
    )


def log_request_blocked(
    reason: str,
    risk_score: float,
    request_id: str,
    layer: str,
    user_input_preview: str = "",
):
    """Log blocked request"""
    log_security_event(
        event_type=EventType.REQUEST_BLOCKED,
        message=f"Request blocked: {reason}",
        request_id=request_id,
        risk_score=risk_score,
        blocked=True,
        layer=layer,
        extra={
            "reason": reason,
            "user_input_preview": user_input_preview[:100],
        }
    )


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Setup logging (dev mode with colors)
    setup_logging(level="INFO", json_format=False)

    logger = get_logger("example")

    # Regular logs
    logger.info("System started")
    logger.debug("Debug information")
    logger.warning("Warning message")

    # Security events
    log_pii_detection(
        entity_type="email",
        count=2,
        request_id="req_123",
    )

    log_injection_attempt(
        injection_type="direct",
        confidence=0.92,
        request_id="req_124",
        blocked=True,
        user_input_preview="ignore all previous instructions",
    )

    log_escalation(
        agent_type="shadow_input_agent",
        risk_score=0.85,
        request_id="req_125",
        reason="high_risk_threshold_exceeded",
    )

    # Audit events
    log_audit_event(
        action="pattern_approved",
        user_id="security-team@example.com",
        resource="pattern_abc123",
        result="success",
        details={"confidence": 0.95, "pattern_type": "injection_variant"},
    )

    print("\n" + "=" * 70)
    print("Switch to JSON format for production:")
    print("=" * 70 + "\n")

    # Setup logging (production mode with JSON)
    setup_logging(level="INFO", json_format=True)

    logger.info("Production mode enabled")
    log_pii_detection("credit_card", 1, "req_126")
