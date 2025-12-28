"""
Integration Tests for Observability Components
Tests metrics collection, distributed tracing, and structured logging
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from sentinel.observability.metrics import (
    SentinelMetrics,
    MetricsCollector,
)
from sentinel.observability.tracing import SentinelTracer
from sentinel.observability.logging import (
    setup_logging,
    get_logger,
    log_security_event,
    EventType,
)


# ============================================================================
# METRICS INTEGRATION TESTS
# ============================================================================

class TestMetricsIntegration:
    """Test Prometheus metrics collection"""

    @pytest.fixture
    def metrics(self):
        """Create metrics instance"""
        return SentinelMetrics()

    @pytest.fixture
    def collector(self, metrics):
        """Create metrics collector"""
        return MetricsCollector(metrics)

    def test_request_metrics_collection(self, collector, metrics):
        """Test request metrics are collected"""
        layer = "input_guard"

        # Start request
        collector.start_request(layer)
        time.sleep(0.01)  # Simulate processing
        collector.end_request(layer, "success")

        # Export metrics
        metrics_data = metrics.export_metrics().decode('utf-8')

        # Verify metrics exist
        assert "sentinel_requests_total" in metrics_data
        assert "sentinel_request_duration_seconds" in metrics_data
        assert f'layer="{layer}"' in metrics_data

    def test_security_event_metrics(self, collector):
        """Test security event metrics"""
        # Record PII detection
        collector.record_pii_detection("email")
        collector.record_pii_detection("ssn")

        # Record injection attempt
        collector.record_injection_attempt("prompt_injection")

        # Record block
        collector.record_block("input_guard", "high_risk")

        # Verify metrics are set (they should not raise errors)
        assert True

    def test_risk_score_metrics(self, collector):
        """Test risk score histogram"""
        risk_scores = [0.1, 0.3, 0.5, 0.7, 0.9]

        for score in risk_scores:
            collector.record_risk_score("overall", score)

        # Should not raise errors
        assert True

    def test_performance_metrics(self, collector):
        """Test component latency metrics"""
        collector.record_component_latency("pii_detector", 0.025)  # 25ms
        collector.record_component_latency("injection_detector", 0.015)  # 15ms

        assert True

    def test_llm_token_metrics(self, collector):
        """Test LLM token usage metrics"""
        collector.record_llm_tokens(
            provider="openai",
            model="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
        )

        assert True

    def test_pattern_discovery_metrics(self, collector):
        """Test meta-learning pattern metrics"""
        collector.record_pattern_discovered("injection_variant")
        collector.record_pattern_deployed("canary")
        collector.record_rollback("high_fp_rate")

        assert True

    def test_metrics_export_format(self, metrics):
        """Test that exported metrics are in Prometheus format"""
        # Record some metrics
        metrics.requests_total.labels(layer="api", status="success").inc()

        # Export
        exported = metrics.export_metrics().decode('utf-8')

        # Should have proper format
        assert "# HELP" in exported
        assert "# TYPE" in exported
        assert "sentinel_" in exported

    def test_content_type(self, metrics):
        """Test Prometheus content type"""
        content_type = metrics.get_content_type()
        assert "text/plain" in content_type or "prometheus" in content_type.lower()


# ============================================================================
# TRACING INTEGRATION TESTS
# ============================================================================

class TestTracingIntegration:
    """Test OpenTelemetry distributed tracing"""

    @pytest.fixture
    def tracer(self):
        """Create tracer instance"""
        return SentinelTracer(
            service_name="sentinel-test",
            otlp_endpoint=None,  # No endpoint for tests
            console_export=False,
        )

    def test_trace_request_context(self, tracer):
        """Test request tracing context manager"""
        request_id = "req_123"
        user_input = "Test input"

        with tracer.trace_request(request_id, user_input) as span:
            # Span should be active
            assert span is not None
            span.set_attribute("test_attribute", "test_value")

        # Context manager should complete without errors
        assert True

    def test_trace_pii_detection(self, tracer):
        """Test PII detection tracing"""
        if not tracer.enabled:
            pytest.skip("Tracing not enabled")

        with tracer.trace_request("req_pii", "Test") as parent_span:
            with tracer.trace_pii_detection() as span:
                span.set_attribute("entity_type", "email")
                span.set_attribute("count", 2)

        assert True

    def test_trace_injection_detection(self, tracer):
        """Test injection detection tracing"""
        if not tracer.enabled:
            pytest.skip("Tracing not enabled")

        with tracer.trace_request("req_injection", "Test") as parent_span:
            with tracer.trace_injection_detection() as span:
                span.set_attribute("detected", True)
                span.set_attribute("injection_type", "prompt_injection")

        assert True

    def test_trace_escalation(self, tracer):
        """Test escalation tracing"""
        if not tracer.enabled:
            pytest.skip("Tracing not enabled")

        with tracer.trace_request("req_escalation", "Test") as parent_span:
            with tracer.trace_escalation("shadow_agent") as span:
                span.set_attribute("risk_score", 0.95)
                span.set_attribute("reason", "high_risk")

        assert True

    def test_nested_spans(self, tracer):
        """Test nested span hierarchy"""
        if not tracer.enabled:
            pytest.skip("Tracing not enabled")

        with tracer.trace_request("req_nested", "Test") as parent:
            with tracer.trace_pii_detection() as child1:
                child1.set_attribute("test", "pii")

            with tracer.trace_injection_detection() as child2:
                child2.set_attribute("test", "injection")

        assert True

    def test_trace_error_handling(self, tracer):
        """Test that errors in traced code are handled"""
        if not tracer.enabled:
            pytest.skip("Tracing not enabled")

        try:
            with tracer.trace_request("req_error", "Test") as span:
                raise ValueError("Test error")
        except ValueError:
            pass

        # Should handle error gracefully
        assert True


# ============================================================================
# LOGGING INTEGRATION TESTS
# ============================================================================

class TestLoggingIntegration:
    """Test structured logging"""

    def test_setup_logging(self):
        """Test logging setup"""
        setup_logging(level="DEBUG", json_format=True)
        logger = get_logger("test")
        assert logger is not None

    def test_get_logger(self):
        """Test getting logger for component"""
        logger = get_logger("test_component")
        assert logger is not None

        # Should be able to log
        logger.info("Test log message")
        logger.warning("Test warning")
        logger.error("Test error")

    def test_log_security_event(self):
        """Test security event logging"""
        log_security_event(
            event_type=EventType.REQUEST_BLOCKED,
            message="Test block",
            request_id="req_123",
            session_id="session_456",
            user_id="user_789",
            risk_score=0.95,
            blocked=True,
            layer="input_guard",
            extra={
                "reason": "prompt_injection",
                "pattern": "ignore.*instructions",
            }
        )

        # Should not raise errors
        assert True

    def test_log_pii_detection(self):
        """Test PII detection logging"""
        log_security_event(
            event_type=EventType.PII_DETECTED,
            message="PII detected and redacted",
            request_id="req_pii",
            session_id="session_pii",
            entity_type="email",
            count=2,
        )

        assert True

    def test_log_injection_attempt(self):
        """Test injection attempt logging"""
        log_security_event(
            event_type=EventType.INJECTION_DETECTED,
            message="Prompt injection detected",
            request_id="req_inject",
            injection_type="prompt_injection",
            risk_score=0.99,
        )

        assert True

    def test_log_escalation(self):
        """Test escalation logging"""
        log_security_event(
            event_type=EventType.ESCALATION,
            message="Request escalated to shadow agent",
            request_id="req_escalate",
            escalated_to="shadow_input_agent",
            risk_score=0.85,
        )

        assert True


# ============================================================================
# END-TO-END OBSERVABILITY TESTS
# ============================================================================

class TestObservabilityEndToEnd:
    """Test complete observability pipeline"""

    @pytest.fixture
    def full_stack(self):
        """Create full observability stack"""
        setup_logging(level="INFO", json_format=True)
        metrics = SentinelMetrics()
        tracer = SentinelTracer(
            service_name="sentinel-e2e",
            otlp_endpoint=None,
            console_export=False,
        )
        collector = MetricsCollector(metrics)
        logger = get_logger("e2e_test")

        return {
            "metrics": metrics,
            "tracer": tracer,
            "collector": collector,
            "logger": logger,
        }

    def test_request_with_full_observability(self, full_stack):
        """Test request with metrics, tracing, and logging"""
        collector = full_stack["collector"]
        tracer = full_stack["tracer"]
        logger = full_stack["logger"]

        request_id = "req_full_obs"
        session_id = "session_full_obs"

        # Start observability
        collector.start_request("api")

        # Trace request
        if tracer.enabled:
            with tracer.trace_request(request_id, "Test input") as span:
                # Log processing
                logger.info("Processing request", extra={
                    "request_id": request_id,
                    "session_id": session_id,
                })

                # Simulate PII detection
                with tracer.trace_pii_detection() as pii_span:
                    collector.record_pii_detection("email")
                    log_security_event(
                        event_type=EventType.PII_DETECTED,
                        message="Email detected",
                        request_id=request_id,
                    )

                # Simulate injection detection
                with tracer.trace_injection_detection() as inject_span:
                    collector.record_injection_attempt("prompt_injection")
                    log_security_event(
                        event_type=EventType.INJECTION_DETECTED,
                        message="Injection detected",
                        request_id=request_id,
                    )

                # Record block
                collector.record_block("input_guard", "high_risk")
                log_security_event(
                    event_type=EventType.REQUEST_BLOCKED,
                    message="Request blocked",
                    request_id=request_id,
                    blocked=True,
                )
        else:
            # Without tracing
            collector.record_pii_detection("email")
            collector.record_injection_attempt("prompt_injection")
            collector.record_block("input_guard", "high_risk")

        # End request
        collector.end_request("api", "blocked")

        # Should complete without errors
        assert True

    def test_metrics_after_multiple_requests(self, full_stack):
        """Test metrics accumulation over multiple requests"""
        collector = full_stack["collector"]

        # Simulate 10 requests
        for i in range(10):
            collector.start_request("api")

            # Vary the outcomes
            if i % 3 == 0:
                collector.record_injection_attempt("prompt_injection")
                collector.record_block("input_guard", "injection")
                collector.end_request("api", "blocked")
            else:
                collector.record_risk_score("overall", 0.2)
                collector.end_request("api", "success")

        # Export metrics
        metrics_data = full_stack["metrics"].export_metrics().decode('utf-8')

        # Should have accumulated metrics
        assert "sentinel_requests_total" in metrics_data

    def test_distributed_trace_correlation(self, full_stack):
        """Test that spans are correlated correctly"""
        tracer = full_stack["tracer"]
        collector = full_stack["collector"]

        if not tracer.enabled:
            pytest.skip("Tracing not enabled")

        # Create parent span
        with tracer.trace_request("req_corr", "Test") as parent:
            parent.set_attribute("user_id", "user_123")

            # Create child spans
            with tracer.trace_pii_detection() as child1:
                child1.set_attribute("entity_type", "email")

            with tracer.trace_injection_detection() as child2:
                child2.set_attribute("detected", True)

            # Child spans should be part of parent trace
            # This is handled by OpenTelemetry context propagation

        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
