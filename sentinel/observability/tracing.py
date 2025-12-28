"""
OpenTelemetry Distributed Tracing
End-to-end request tracing across all security layers
"""

from typing import Dict, Any, Optional, Callable
from functools import wraps
from contextlib import contextmanager
import time

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    # Mock classes
    class MockSpan:
        def set_attribute(self, *args, **kwargs): pass
        def set_status(self, *args, **kwargs): pass
        def add_event(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass

    class MockTracer:
        def start_as_current_span(self, *args, **kwargs):
            return contextmanager(lambda: (yield MockSpan()))()

    trace = type('trace', (), {
        'get_tracer': lambda *args, **kwargs: MockTracer(),
        'Status': type('Status', (), {}),
        'StatusCode': type('StatusCode', (), {'OK': 'OK', 'ERROR': 'ERROR'}),
    })()


class SentinelTracer:
    """
    OpenTelemetry tracer for Sentinel Security System

    Provides distributed tracing across:
    - Input Guard
    - State Monitor
    - Output Guard
    - Shadow Agents
    - Meta-Learning Components
    """

    def __init__(
        self,
        service_name: str = "sentinel-security",
        otlp_endpoint: Optional[str] = None,
        console_export: bool = False,
    ):
        """
        Initialize tracer

        Args:
            service_name: Name of the service
            otlp_endpoint: OTLP collector endpoint (e.g., "http://localhost:4317")
            console_export: Export traces to console (for debugging)
        """
        self.service_name = service_name
        self.enabled = OPENTELEMETRY_AVAILABLE

        if not self.enabled:
            print("⚠️  OpenTelemetry not installed. Tracing disabled.")
            print("   Install: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp")
            self.tracer = trace.get_tracer(service_name)
            return

        # Create resource
        resource = Resource(attributes={
            "service.name": service_name,
            "service.version": "1.0.0",
        })

        # Set up tracer provider
        provider = TracerProvider(resource=resource)

        # Add exporters
        if console_export:
            console_exporter = ConsoleSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(console_exporter))

        if otlp_endpoint:
            try:
                otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
                provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            except Exception as e:
                print(f"⚠️  Failed to configure OTLP exporter: {e}")

        # Set global provider
        trace.set_tracer_provider(provider)

        # Get tracer
        self.tracer = trace.get_tracer(service_name)

    @contextmanager
    def trace_request(
        self,
        request_id: str,
        user_input: str,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Trace entire request lifecycle

        Usage:
            with tracer.trace_request(request_id, user_input):
                # ... process request ...
        """
        with self.tracer.start_as_current_span(
            "sentinel.request",
            attributes={
                "request.id": request_id,
                "request.input_length": len(user_input),
                **(attributes or {}),
            },
        ) as span:
            start_time = time.time()

            try:
                yield span
            except Exception as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                raise
            finally:
                duration = time.time() - start_time
                span.set_attribute("request.duration_ms", duration * 1000)

    @contextmanager
    def trace_layer(
        self,
        layer_name: str,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Trace processing in a specific security layer

        Usage:
            with tracer.trace_layer("input_guard", {"pii_enabled": True}):
                # ... process in input guard ...
        """
        with self.tracer.start_as_current_span(
            f"sentinel.layer.{layer_name}",
            attributes=attributes or {},
        ) as span:
            start_time = time.time()

            try:
                yield span
            except Exception as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.add_event("exception", {
                    "exception.type": type(e).__name__,
                    "exception.message": str(e),
                })
                raise
            finally:
                duration = time.time() - start_time
                span.set_attribute("layer.duration_ms", duration * 1000)

    @contextmanager
    def trace_component(
        self,
        component_name: str,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Trace a specific component operation

        Usage:
            with tracer.trace_component("pii_detector", {"entity_types": ["email", "phone"]}):
                # ... detect PII ...
        """
        with self.tracer.start_as_current_span(
            f"sentinel.component.{component_name}",
            attributes=attributes or {},
        ) as span:
            try:
                yield span
            except Exception as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise

    def record_pii_detection(self, span, entity_type: str, count: int):
        """Record PII detection in current span"""
        if not self.enabled:
            return

        span.add_event("pii_detected", {
            "pii.entity_type": entity_type,
            "pii.count": count,
        })

    def record_injection_detection(self, span, injection_type: str, confidence: float):
        """Record injection detection in current span"""
        if not self.enabled:
            return

        span.add_event("injection_detected", {
            "injection.type": injection_type,
            "injection.confidence": confidence,
        })

    def record_escalation(self, span, agent_type: str, risk_score: float):
        """Record shadow agent escalation"""
        if not self.enabled:
            return

        span.add_event("escalation", {
            "escalation.agent_type": agent_type,
            "escalation.risk_score": risk_score,
        })

    def record_block(self, span, reason: str, risk_score: float):
        """Record request block"""
        if not self.enabled:
            return

        span.add_event("request_blocked", {
            "block.reason": reason,
            "block.risk_score": risk_score,
        })
        span.set_attribute("request.blocked", True)


# =============================================================================
# DECORATORS
# =============================================================================

def trace_request(tracer: Optional[SentinelTracer] = None):
    """
    Decorator to trace request processing

    Usage:
        @trace_request(tracer)
        def process(self, state):
            # ... processing ...
            return state
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if tracer is None or not tracer.enabled:
                return func(*args, **kwargs)

            # Extract request ID and input from state (if available)
            state = kwargs.get('state') or (args[1] if len(args) > 1 else {})
            request_id = state.get('session_id', 'unknown')
            user_input = state.get('user_input', '')

            with tracer.trace_request(request_id, user_input):
                return func(*args, **kwargs)

        return wrapper
    return decorator


def trace_pattern_analysis(tracer: SentinelTracer):
    """
    Decorator to trace pattern analysis

    Usage:
        @trace_pattern_analysis(tracer)
        def analyze_audit_logs(self, logs):
            # ... analysis ...
            return patterns
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not tracer.enabled:
                return func(*args, **kwargs)

            with tracer.trace_component(
                "pattern_analysis",
                {"log_count": len(kwargs.get('audit_logs', []))}
            ) as span:
                result = func(*args, **kwargs)

                # Record results
                if isinstance(result, list):
                    span.set_attribute("patterns.discovered", len(result))

                return result

        return wrapper
    return decorator


@contextmanager
def create_span(
    tracer: SentinelTracer,
    name: str,
    attributes: Optional[Dict[str, Any]] = None
):
    """
    Context manager to create a custom span

    Usage:
        with create_span(tracer, "custom_operation", {"key": "value"}):
            # ... custom operation ...
    """
    if not tracer.enabled:
        yield None
        return

    with tracer.tracer.start_as_current_span(
        f"sentinel.{name}",
        attributes=attributes or {},
    ) as span:
        yield span


# =============================================================================
# GLOBAL TRACER INSTANCE (Optional)
# =============================================================================

_global_tracer: Optional[SentinelTracer] = None


def get_tracer(
    service_name: str = "sentinel-security",
    otlp_endpoint: Optional[str] = None,
    console_export: bool = False,
) -> SentinelTracer:
    """Get or create global tracer instance"""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = SentinelTracer(
            service_name=service_name,
            otlp_endpoint=otlp_endpoint,
            console_export=console_export,
        )
    return _global_tracer
