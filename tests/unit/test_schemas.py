"""
Unit tests for Pydantic schemas
Tests data models and validation
"""

import pytest
from datetime import datetime
from sentinel.schemas import (
    RedactedEntity,
    EntityType,
    RedactionStrategy,
    RiskScore,
    RiskLevel,
    AggregatedRiskScore,
    RequestContext,
    InjectionDetection,
    InjectionType,
    LoopDetection,
    LoopType,
    SentinelConfig,
    create_initial_state,
)


class TestRedactedEntity:
    """Unit tests for RedactedEntity model"""

    def test_valid_entity_creation(self):
        """Test creating a valid redacted entity"""
        entity = RedactedEntity(
            entity_type=EntityType.EMAIL,
            original_value="john@example.com",
            redacted_value="[REDACTED_EMAIL_001]",
            start_pos=10,
            end_pos=27,
            confidence=0.95,
            redaction_strategy=RedactionStrategy.TOKEN
        )

        assert entity.entity_type == EntityType.EMAIL
        assert entity.confidence == 0.95

    def test_confidence_validation(self):
        """Test confidence must be between 0 and 1"""
        with pytest.raises(ValueError):
            RedactedEntity(
                entity_type=EntityType.EMAIL,
                original_value="test",
                redacted_value="[REDACTED]",
                start_pos=0,
                end_pos=4,
                confidence=1.5  # Invalid
            )


class TestRiskScore:
    """Unit tests for RiskScore model"""

    def test_valid_risk_score(self):
        """Test creating valid risk score"""
        risk = RiskScore(
            layer="input_guard",
            risk_score=0.75,
            risk_level=RiskLevel.HIGH,
            risk_factors={"pii_detected": 0.8, "injection_risk": 0.7},
            explanation="Multiple PII detected"
        )

        assert risk.layer == "input_guard"
        assert risk.risk_score == 0.75
        assert risk.risk_level == RiskLevel.HIGH

    def test_risk_score_bounds(self):
        """Test risk score must be 0.0-1.0"""
        with pytest.raises(ValueError):
            RiskScore(
                layer="test",
                risk_score=1.5,  # Invalid
                risk_level=RiskLevel.HIGH,
                risk_factors={}
            )

    def test_timestamp_auto_generated(self):
        """Test timestamp is auto-generated"""
        risk = RiskScore(
            layer="test",
            risk_score=0.5,
            risk_level=RiskLevel.MEDIUM,
            risk_factors={}
        )

        assert isinstance(risk.timestamp, datetime)


class TestAggregatedRiskScore:
    """Unit tests for AggregatedRiskScore model"""

    def test_aggregated_risk_creation(self):
        """Test creating aggregated risk score"""
        agg_risk = AggregatedRiskScore(
            overall_risk_score=0.82,
            overall_risk_level=RiskLevel.HIGH,
            layer_scores={
                "input_guard": 0.8,
                "state_monitor": 0.6,
                "output_guard": 0.9
            },
            risk_breakdown={},
            should_escalate=True,
            escalation_reason="High risk detected"
        )

        assert agg_risk.overall_risk_score == 0.82
        assert agg_risk.should_escalate
        assert agg_risk.escalation_reason == "High risk detected"


class TestRequestContext:
    """Unit tests for RequestContext model"""

    def test_default_context(self):
        """Test default request context"""
        import uuid
        session_id = f"session_{uuid.uuid4().hex}"

        context = RequestContext(session_id=session_id)

        assert context.trust_score == 0.5  # Default
        assert context.previous_requests_count == 0
        assert context.user_id is None

    def test_trust_score_bounds(self):
        """Test trust score must be 0.0-1.0"""
        import uuid
        session_id = f"session_{uuid.uuid4().hex}"

        with pytest.raises(ValueError):
            RequestContext(
                session_id=session_id,
                trust_score=1.2  # Invalid
            )

    def test_context_with_metadata(self):
        """Test context with custom metadata"""
        import uuid
        session_id = f"session_{uuid.uuid4().hex}"

        context = RequestContext(
            session_id=session_id,
            user_id="user123",
            user_role="admin",
            metadata={"custom_field": "value"}
        )

        assert context.user_id == "user123"
        assert context.metadata["custom_field"] == "value"


class TestInjectionDetection:
    """Unit tests for InjectionDetection model"""

    def test_injection_detected(self):
        """Test injection detection model"""
        detection = InjectionDetection(
            injection_detected=True,
            injection_types=[InjectionType.DIRECT, InjectionType.JAILBREAK],
            confidence=0.92,
            matched_patterns=["ignore previous", "bypass"],
            risk_score=0.95
        )

        assert detection.injection_detected
        assert len(detection.injection_types) == 2
        assert detection.risk_score == 0.95


class TestLoopDetection:
    """Unit tests for LoopDetection model"""

    def test_loop_detection(self):
        """Test loop detection model"""
        detection = LoopDetection(
            loop_detected=True,
            loop_type=LoopType.EXACT,
            confidence=0.98,
            repetition_count=10,
            repeated_sequence=["search", "search"],
            explanation="Exact tool call repeated 10 times"
        )

        assert detection.loop_detected
        assert detection.loop_type == LoopType.EXACT
        assert detection.repetition_count == 10


class TestSentinelConfig:
    """Unit tests for SentinelConfig"""

    def test_default_config(self):
        """Test default configuration"""
        config = SentinelConfig()

        assert config.enable_input_guard
        assert config.enable_output_guard
        assert config.enable_state_monitor
        assert config.risk_scoring.enabled
        assert not config.shadow_agents.enabled  # Disabled by default

    def test_custom_config(self):
        """Test custom configuration"""
        from sentinel.schemas import RiskScoringConfig

        config = SentinelConfig(
            enable_input_guard=False,
            risk_scoring=RiskScoringConfig(
                enabled=True,
                pii_risk_weight=0.5
            )
        )

        assert not config.enable_input_guard
        assert config.risk_scoring.pii_risk_weight == 0.5


class TestCreateInitialState:
    """Unit tests for create_initial_state helper"""

    def test_initial_state_creation(self):
        """Test creating initial state"""
        config = SentinelConfig()
        state = create_initial_state("test input", config)

        assert state["user_input"] == "test input"
        assert state["redacted_input"] == "test input"  # Not yet redacted
        assert state["blocked"] == False
        assert state["should_block"] == False
        assert isinstance(state["session_id"], str)
        assert len(state["risk_scores"]) == 0

    def test_initial_state_with_context(self):
        """Test creating initial state with context"""
        config = SentinelConfig()
        state = create_initial_state(
            "test input",
            config,
            user_id="user123",
            user_role="admin",
            ip_address="192.168.1.1"
        )

        assert state["request_context"]["user_id"] == "user123"
        assert state["request_context"]["user_role"] == "admin"
        assert state["request_context"]["ip_address"] == "192.168.1.1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
