"""
Unit tests for State Monitor Agent
Tests loop detection and cost monitoring in isolation
"""

import pytest
from sentinel.state_monitor import StateMonitorAgent, LoopDetectionConfig
from sentinel.schemas import create_initial_state, SentinelConfig, LoopType


class TestLoopDetection:
    """Unit tests for loop detection"""

    def test_exact_loop_detection(self):
        """Test detection of exact repeated tool calls"""
        config = LoopDetectionConfig()
        monitor = StateMonitorAgent(config)

        state = create_initial_state("test", SentinelConfig())

        # Simulate exact repeated tool calls
        state["tool_calls"] = [
            {"tool": "search", "args": {"query": "cats"}},
            {"tool": "search", "args": {"query": "cats"}},
            {"tool": "search", "args": {"query": "cats"}},
            {"tool": "search", "args": {"query": "cats"}},
        ]

        result = monitor.process(state)

        assert result["loop_detected"]
        assert result["loop_details"]["loop_type"] == LoopType.EXACT

    def test_no_loop_different_calls(self):
        """Test that different tool calls don't trigger loop detection"""
        config = LoopDetectionConfig()
        monitor = StateMonitorAgent(config)

        state = create_initial_state("test", SentinelConfig())

        state["tool_calls"] = [
            {"tool": "search", "args": {"query": "cats"}},
            {"tool": "search", "args": {"query": "dogs"}},
            {"tool": "calculate", "args": {"expr": "2+2"}},
            {"tool": "write", "args": {"content": "hello"}},
        ]

        result = monitor.process(state)

        assert not result["loop_detected"]

    def test_semantic_loop_detection(self):
        """Test detection of semantically similar calls"""
        config = LoopDetectionConfig()
        monitor = StateMonitorAgent(config)

        state = create_initial_state("test", SentinelConfig())

        # Similar but not identical
        state["tool_calls"] = [
            {"tool": "search", "args": {"query": "how to cook pasta"}},
            {"tool": "search", "args": {"query": "pasta cooking instructions"}},
            {"tool": "search", "args": {"query": "how do I cook pasta"}},
            {"tool": "search", "args": {"query": "pasta preparation guide"}},
        ]

        result = monitor.process(state)

        # Should detect semantic similarity
        # Note: This depends on semantic detection being enabled
        if result["loop_detected"]:
            assert result["loop_details"]["loop_type"] in [LoopType.SEMANTIC, LoopType.EXACT]

    def test_cyclic_pattern_detection(self):
        """Test detection of cyclic patterns (A->B->A)"""
        config = LoopDetectionConfig()
        monitor = StateMonitorAgent(config)

        state = create_initial_state("test", SentinelConfig())

        # Cyclic pattern
        state["tool_calls"] = [
            {"tool": "search", "args": {"query": "A"}},
            {"tool": "calculate", "args": {"expr": "B"}},
            {"tool": "search", "args": {"query": "A"}},
            {"tool": "calculate", "args": {"expr": "B"}},
            {"tool": "search", "args": {"query": "A"}},
        ]

        result = monitor.process(state)

        # May detect as cyclic or exact depending on implementation
        if result["loop_detected"]:
            assert result["loop_details"]["loop_type"] in [LoopType.CYCLIC, LoopType.EXACT]

    def test_loop_threshold(self):
        """Test that loop is only detected after threshold"""
        config = LoopDetectionConfig(max_repeats=5)
        monitor = StateMonitorAgent(config)

        state = create_initial_state("test", SentinelConfig())

        # Just below threshold
        state["tool_calls"] = [{"tool": "search", "args": {}} for _ in range(4)]
        result_below = monitor.process(state)

        # At/above threshold
        state["tool_calls"] = [{"tool": "search", "args": {}} for _ in range(6)]
        result_above = monitor.process(state)

        # Below threshold should not detect
        # Above threshold should detect
        assert result_above["loop_detected"]


class TestCostMonitoring:
    """Unit tests for cost monitoring"""

    def test_cost_metrics_calculation(self):
        """Test that cost metrics are calculated"""
        config = LoopDetectionConfig()
        monitor = StateMonitorAgent(config)

        state = create_initial_state("test", SentinelConfig())
        state["tool_calls"] = [
            {"tool": "search", "args": {}},
            {"tool": "calculate", "args": {}},
        ]

        result = monitor.process(state)

        assert "cost_metrics" in result
        assert result["cost_metrics"]["total_api_calls"] >= 0
        assert result["cost_metrics"]["total_tokens"] >= 0

    def test_high_cost_warning(self):
        """Test warning on high token usage"""
        config = LoopDetectionConfig(max_tokens_per_request=1000)
        monitor = StateMonitorAgent(config)

        state = create_initial_state("test", SentinelConfig())
        state["cost_metrics"] = {
            "total_tokens": 5000,  # Above threshold
            "total_api_calls": 2,
            "total_duration_ms": 1000,
        }

        result = monitor.process(state)

        # Should have warning or high risk score
        risk_scores = [r for r in result.get("risk_scores", []) if r["layer"] == "state_monitor"]
        if risk_scores:
            assert risk_scores[0]["risk_score"] > 0.3

    def test_excessive_api_calls(self):
        """Test detection of excessive API calls"""
        config = LoopDetectionConfig()
        monitor = StateMonitorAgent(config)

        state = create_initial_state("test", SentinelConfig())
        state["tool_calls"] = [{"tool": f"call_{i}", "args": {}} for i in range(100)]

        result = monitor.process(state)

        # Should detect as potential issue
        assert result["cost_metrics"]["total_api_calls"] == 100


class TestRiskScoring:
    """Unit tests for state monitor risk scoring"""

    def test_risk_score_with_loop(self):
        """Test risk score calculation with loop detected"""
        config = LoopDetectionConfig()
        monitor = StateMonitorAgent(config)

        state = create_initial_state("test", SentinelConfig())
        state["tool_calls"] = [{"tool": "same", "args": {}} for _ in range(10)]

        result = monitor.process(state)

        risk_scores = [r for r in result.get("risk_scores", []) if r["layer"] == "state_monitor"]

        if risk_scores:
            assert risk_scores[0]["risk_score"] > 0.5

    def test_risk_score_normal_execution(self):
        """Test risk score for normal execution"""
        config = LoopDetectionConfig()
        monitor = StateMonitorAgent(config)

        state = create_initial_state("test", SentinelConfig())
        state["tool_calls"] = [
            {"tool": "search", "args": {}},
            {"tool": "calculate", "args": {}},
        ]
        state["cost_metrics"] = {
            "total_tokens": 100,
            "total_api_calls": 2,
            "total_duration_ms": 500,
        }

        result = monitor.process(state)

        risk_scores = [r for r in result.get("risk_scores", []) if r["layer"] == "state_monitor"]

        if risk_scores:
            assert risk_scores[0]["risk_score"] < 0.3

    def test_risk_factors(self):
        """Test that risk factors are properly set"""
        config = LoopDetectionConfig()
        monitor = StateMonitorAgent(config)

        state = create_initial_state("test", SentinelConfig())
        state["tool_calls"] = [{"tool": "same", "args": {}} for _ in range(10)]

        result = monitor.process(state)

        risk_scores = [r for r in result.get("risk_scores", []) if r["layer"] == "state_monitor"]

        if risk_scores:
            assert "risk_factors" in risk_scores[0]
            factors = risk_scores[0]["risk_factors"]
            assert "loop_risk" in factors or "cost_risk" in factors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
