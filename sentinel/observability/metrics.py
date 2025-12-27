"""
Prometheus Metrics Integration
Real-time monitoring and alerting for Sentinel
"""

from typing import Dict, Any, Optional, Callable
from functools import wraps
import time
from contextlib import contextmanager

try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        Summary,
        CollectorRegistry,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Mock classes for when Prometheus is not installed
    class Counter:
        def __init__(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self

    class Histogram:
        def __init__(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        def time(self): return contextmanager(lambda: (yield))()

    class Gauge:
        def __init__(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def dec(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self

    class Summary:
        def __init__(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self

    class CollectorRegistry:
        def __init__(self): pass

    def generate_latest(registry): return b""
    CONTENT_TYPE_LATEST = "text/plain"


class SentinelMetrics:
    """
    Prometheus metrics for Sentinel Security System

    Metrics Categories:
    1. Request Metrics - Total requests, latency, throughput
    2. Security Metrics - Blocks, detections, risk scores
    3. Pattern Discovery - Discovered patterns, approvals, deployments
    4. Performance - Component latency, cache hits, errors
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize metrics collector

        Args:
            registry: Prometheus registry (default: new registry)
        """
        self.registry = registry or CollectorRegistry()
        self.enabled = PROMETHEUS_AVAILABLE

        if not self.enabled:
            print("⚠️  Prometheus not installed. Metrics collection disabled.")
            print("   Install: pip install prometheus-client")

        # =================================================================
        # REQUEST METRICS
        # =================================================================

        self.requests_total = Counter(
            'sentinel_requests_total',
            'Total number of requests processed',
            ['layer', 'status'],
            registry=self.registry,
        )

        self.request_duration = Histogram(
            'sentinel_request_duration_seconds',
            'Request processing duration',
            ['layer'],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry,
        )

        self.requests_in_progress = Gauge(
            'sentinel_requests_in_progress',
            'Number of requests currently being processed',
            ['layer'],
            registry=self.registry,
        )

        # =================================================================
        # SECURITY METRICS
        # =================================================================

        self.blocks_total = Counter(
            'sentinel_blocks_total',
            'Total number of blocked requests',
            ['layer', 'reason'],
            registry=self.registry,
        )

        self.pii_detections = Counter(
            'sentinel_pii_detections_total',
            'Total PII detections',
            ['entity_type'],
            registry=self.registry,
        )

        self.injection_attempts = Counter(
            'sentinel_injection_attempts_total',
            'Total prompt injection attempts detected',
            ['injection_type'],
            registry=self.registry,
        )

        self.risk_scores = Histogram(
            'sentinel_risk_scores',
            'Distribution of risk scores',
            ['layer'],
            buckets=(0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 1.0),
            registry=self.registry,
        )

        self.escalations_total = Counter(
            'sentinel_escalations_total',
            'Total escalations to shadow agents',
            ['agent_type'],
            registry=self.registry,
        )

        # =================================================================
        # PATTERN DISCOVERY METRICS
        # =================================================================

        self.patterns_discovered = Counter(
            'sentinel_patterns_discovered_total',
            'Total patterns discovered',
            ['pattern_type'],
            registry=self.registry,
        )

        self.patterns_deployed = Counter(
            'sentinel_patterns_deployed_total',
            'Total patterns deployed',
            ['deployment_type'],
            registry=self.registry,
        )

        self.rule_versions = Gauge(
            'sentinel_rule_version_info',
            'Current rule version',
            ['version', 'status'],
            registry=self.registry,
        )

        self.canary_percentage = Gauge(
            'sentinel_canary_percentage',
            'Current canary deployment percentage',
            registry=self.registry,
        )

        self.rollbacks_total = Counter(
            'sentinel_rollbacks_total',
            'Total automatic rollbacks',
            ['reason'],
            registry=self.registry,
        )

        # =================================================================
        # PERFORMANCE METRICS
        # =================================================================

        self.component_latency = Histogram(
            'sentinel_component_latency_seconds',
            'Component processing latency',
            ['component'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
            registry=self.registry,
        )

        self.cache_operations = Counter(
            'sentinel_cache_operations_total',
            'Cache operations',
            ['operation', 'result'],
            registry=self.registry,
        )

        self.llm_calls = Counter(
            'sentinel_llm_calls_total',
            'LLM API calls',
            ['provider', 'model', 'status'],
            registry=self.registry,
        )

        self.llm_tokens = Counter(
            'sentinel_llm_tokens_total',
            'LLM tokens consumed',
            ['provider', 'model', 'type'],
            registry=self.registry,
        )

        self.errors_total = Counter(
            'sentinel_errors_total',
            'Total errors',
            ['component', 'error_type'],
            registry=self.registry,
        )

        # =================================================================
        # THREAT INTELLIGENCE METRICS
        # =================================================================

        self.threat_feeds_updated = Counter(
            'sentinel_threat_feeds_updated_total',
            'Threat feed updates',
            ['feed_name', 'status'],
            registry=self.registry,
        )

        self.threats_detected = Counter(
            'sentinel_threats_detected_total',
            'Threats matched from feeds',
            ['severity', 'feed_name'],
            registry=self.registry,
        )

        # =================================================================
        # APPROVAL WORKFLOW METRICS
        # =================================================================

        self.reviews_pending = Gauge(
            'sentinel_reviews_pending',
            'Number of pending pattern reviews',
            ['priority'],
            registry=self.registry,
        )

        self.reviews_completed = Counter(
            'sentinel_reviews_completed_total',
            'Completed pattern reviews',
            ['action', 'reviewer'],
            registry=self.registry,
        )

    def export_metrics(self) -> bytes:
        """
        Export metrics in Prometheus format

        Returns:
            Prometheus-formatted metrics
        """
        if not self.enabled:
            return b""

        return generate_latest(self.registry)

    def get_content_type(self) -> str:
        """Get Prometheus content type for HTTP response"""
        return CONTENT_TYPE_LATEST


class MetricsCollector:
    """
    Helper class for collecting metrics during request processing

    Usage:
        collector = MetricsCollector(metrics)
        collector.start_request("input_guard")
        # ... process request ...
        collector.record_pii_detection("email")
        collector.record_risk_score("input_guard", 0.85)
        collector.end_request("input_guard", "allowed")
    """

    def __init__(self, metrics: SentinelMetrics):
        self.metrics = metrics
        self._start_times: Dict[str, float] = {}

    def start_request(self, layer: str):
        """Start tracking a request"""
        self._start_times[layer] = time.time()
        self.metrics.requests_in_progress.labels(layer=layer).inc()

    def end_request(self, layer: str, status: str):
        """End request tracking"""
        if layer in self._start_times:
            duration = time.time() - self._start_times[layer]
            self.metrics.request_duration.labels(layer=layer).observe(duration)
            del self._start_times[layer]

        self.metrics.requests_total.labels(layer=layer, status=status).inc()
        self.metrics.requests_in_progress.labels(layer=layer).dec()

    def record_block(self, layer: str, reason: str):
        """Record a blocked request"""
        self.metrics.blocks_total.labels(layer=layer, reason=reason).inc()

    def record_pii_detection(self, entity_type: str):
        """Record PII detection"""
        self.metrics.pii_detections.labels(entity_type=entity_type).inc()

    def record_injection_attempt(self, injection_type: str):
        """Record injection attempt"""
        self.metrics.injection_attempts.labels(injection_type=injection_type).inc()

    def record_risk_score(self, layer: str, score: float):
        """Record risk score"""
        self.metrics.risk_scores.labels(layer=layer).observe(score)

    def record_escalation(self, agent_type: str):
        """Record escalation to shadow agent"""
        self.metrics.escalations_total.labels(agent_type=agent_type).inc()

    def record_pattern_discovery(self, pattern_type: str):
        """Record pattern discovery"""
        self.metrics.patterns_discovered.labels(pattern_type=pattern_type).inc()

    def record_deployment(self, deployment_type: str):
        """Record pattern deployment"""
        self.metrics.patterns_deployed.labels(deployment_type=deployment_type).inc()

    def record_rollback(self, reason: str):
        """Record automatic rollback"""
        self.metrics.rollbacks_total.labels(reason=reason).inc()

    def record_error(self, component: str, error_type: str):
        """Record error"""
        self.metrics.errors_total.labels(component=component, error_type=error_type).inc()

    def record_llm_call(self, provider: str, model: str, status: str, tokens: int, token_type: str = "total"):
        """Record LLM API call"""
        self.metrics.llm_calls.labels(provider=provider, model=model, status=status).inc()
        self.metrics.llm_tokens.labels(provider=provider, model=model, type=token_type).inc(tokens)

    @contextmanager
    def track_component(self, component: str):
        """Context manager to track component latency"""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            self.metrics.component_latency.labels(component=component).observe(duration)


# =============================================================================
# DECORATORS
# =============================================================================

def track_request(layer: str, metrics: Optional[SentinelMetrics] = None):
    """
    Decorator to track request metrics

    Usage:
        @track_request("input_guard", metrics)
        def process_input(self, state):
            # ... processing ...
            return state
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if metrics is None or not metrics.enabled:
                return func(*args, **kwargs)

            collector = MetricsCollector(metrics)
            collector.start_request(layer)

            try:
                result = func(*args, **kwargs)
                collector.end_request(layer, "success")
                return result
            except Exception as e:
                collector.end_request(layer, "error")
                collector.record_error(layer, type(e).__name__)
                raise

        return wrapper
    return decorator


def track_pattern_discovery(metrics: SentinelMetrics):
    """
    Decorator to track pattern discovery metrics

    Usage:
        @track_pattern_discovery(metrics)
        def analyze_audit_logs(self, logs):
            # ... analysis ...
            return patterns
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not metrics.enabled:
                return func(*args, **kwargs)

            start = time.time()

            try:
                result = func(*args, **kwargs)

                # Record discovered patterns
                if isinstance(result, list):
                    for pattern in result:
                        if hasattr(pattern, 'pattern_type'):
                            metrics.patterns_discovered.labels(
                                pattern_type=pattern.pattern_type
                            ).inc()

                return result
            finally:
                duration = time.time() - start
                metrics.component_latency.labels(component="pattern_discovery").observe(duration)

        return wrapper
    return decorator


def track_deployment(metrics: SentinelMetrics):
    """
    Decorator to track deployment metrics

    Usage:
        @track_deployment(metrics)
        def deploy_canary(self, version, percentage):
            # ... deployment ...
            return version
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not metrics.enabled:
                return func(*args, **kwargs)

            result = func(*args, **kwargs)

            # Update deployment metrics
            if hasattr(result, 'deployment_status'):
                metrics.rule_versions.labels(
                    version=result.version,
                    status=result.deployment_status
                ).set(1)

                if hasattr(result, 'deployment_percentage'):
                    metrics.canary_percentage.set(result.deployment_percentage)

            return result

        return wrapper
    return decorator


# =============================================================================
# GLOBAL METRICS INSTANCE (Optional)
# =============================================================================

# Global instance for convenience (can also create your own)
_global_metrics: Optional[SentinelMetrics] = None


def get_metrics() -> SentinelMetrics:
    """Get or create global metrics instance"""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = SentinelMetrics()
    return _global_metrics
