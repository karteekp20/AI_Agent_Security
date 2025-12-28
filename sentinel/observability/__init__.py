"""
Observability Module: Metrics, Tracing, and Logging
Production-grade monitoring and observability for Sentinel
"""

from .metrics import (
    SentinelMetrics,
    MetricsCollector,
    track_request,
    track_pattern_discovery,
    track_deployment,
)
from .tracing import (
    SentinelTracer,
    trace_request,
    trace_pattern_analysis,
    create_span,
)
from .logging import (
    setup_logging,
    get_logger,
    log_security_event,
    log_audit_event,
)

__all__ = [
    # Metrics
    'SentinelMetrics',
    'MetricsCollector',
    'track_request',
    'track_pattern_discovery',
    'track_deployment',

    # Tracing
    'SentinelTracer',
    'trace_request',
    'trace_pattern_analysis',
    'create_span',

    # Logging
    'setup_logging',
    'get_logger',
    'log_security_event',
    'log_audit_event',
]
