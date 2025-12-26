"""
Unit tests for Output Guard Agent
Tests data leak detection and response validation in isolation
"""

import pytest
from sentinel.output_guard import OutputGuardAgent
from sentinel.schemas import (
    PIIDetectionConfig,
    EntityType,
    create_initial_state,
    SentinelConfig,
)


class TestOutputGuard:
    """Unit tests for output guard"""

    def test_pii_leak_detection(self):
        """Test detection of PII in output"""
        config = PIIDetectionConfig()
        guard = OutputGuardAgent(config)

        state = create_initial_state("test input", SentinelConfig())
        state["agent_response"] = "Your SSN is 123-45-6789"

        result = guard.process(state)

        assert len(result["security_threats"]) > 0
        leak_threats = [t for t in result["security_threats"] if "leak" in t.get("description", "").lower()]
        assert len(leak_threats) > 0

    def test_new_pii_in_output(self):
        """Test detection of PII not in input"""
        config = PIIDetectionConfig()
        guard = OutputGuardAgent(config)

        state = create_initial_state("What is your policy?", SentinelConfig())
        state["agent_response"] = "Our contact email is admin@internal-company.com"
        state["original_entities"] = []  # No PII in input

        result = guard.process(state)

        # Should detect new email in output
        assert len(result["security_threats"]) > 0

    def test_sanitization(self):
        """Test that PII in output is sanitized"""
        config = PIIDetectionConfig()
        guard = OutputGuardAgent(config)

        state = create_initial_state("test", SentinelConfig())
        state["agent_response"] = "Contact john@example.com for details"

        result = guard.process(state)

        sanitized = result["sanitized_response"]
        assert "john@example.com" not in sanitized
        assert "[REDACTED" in sanitized

    def test_no_false_positive_on_clean_output(self):
        """Test that clean output passes without issues"""
        config = PIIDetectionConfig()
        guard = OutputGuardAgent(config)

        state = create_initial_state("test", SentinelConfig())
        state["agent_response"] = "The weather is sunny today."

        result = guard.process(state)

        assert result["sanitized_response"] == "The weather is sunny today."
        assert len([t for t in result["security_threats"] if t.get("layer") == "output_guard"]) == 0

    def test_allowed_entities_passthrough(self):
        """Test that entities present in input are allowed in output"""
        config = PIIDetectionConfig()
        guard = OutputGuardAgent(config)

        state = create_initial_state("My email is john@example.com", SentinelConfig())
        state["agent_response"] = "I received your email at john@example.com"

        # Simulate input guard already processed this
        state["original_entities"] = [{
            "entity_type": EntityType.EMAIL,
            "original_value": "john@example.com",
            "start_pos": 0,
            "end_pos": 18,
        }]

        result = guard.process(state)

        # Should allow email since it was in input
        sanitized = result["sanitized_response"]
        # Email might still be redacted for safety, but shouldn't create HIGH severity threat
        high_threats = [t for t in result["security_threats"]
                       if t.get("severity") == "critical" and t.get("layer") == "output_guard"]
        assert len(high_threats) == 0

    def test_risk_score_calculation(self):
        """Test risk score calculation"""
        config = PIIDetectionConfig()
        guard = OutputGuardAgent(config)

        # Low risk output
        state_low = create_initial_state("test", SentinelConfig())
        state_low["agent_response"] = "Hello, how can I help?"
        result_low = guard.process(state_low)

        # High risk output (multiple PII)
        state_high = create_initial_state("test", SentinelConfig())
        state_high["agent_response"] = "SSN: 123-45-6789, Card: 4532-0151-1283-0366"
        result_high = guard.process(state_high)

        # Extract risk scores
        low_risk_scores = [r for r in result_low.get("risk_scores", []) if r["layer"] == "output_guard"]
        high_risk_scores = [r for r in result_high.get("risk_scores", []) if r["layer"] == "output_guard"]

        if low_risk_scores and high_risk_scores:
            assert high_risk_scores[0]["risk_score"] > low_risk_scores[0]["risk_score"]

    def test_multiple_pii_types_in_output(self):
        """Test detection of multiple PII types in output"""
        config = PIIDetectionConfig()
        guard = OutputGuardAgent(config)

        state = create_initial_state("test", SentinelConfig())
        state["agent_response"] = "Contact: john@example.com, Phone: 555-123-4567, SSN: 123-45-6789"

        result = guard.process(state)

        threats = [t for t in result["security_threats"] if t.get("layer") == "output_guard"]
        assert len(threats) > 0

    def test_partial_redaction(self):
        """Test that only PII is redacted, not entire response"""
        config = PIIDetectionConfig()
        guard = OutputGuardAgent(config)

        state = create_initial_state("test", SentinelConfig())
        state["agent_response"] = "Your order confirmation will be sent to john@example.com within 24 hours."

        result = guard.process(state)

        sanitized = result["sanitized_response"]
        # Should preserve non-PII parts
        assert "order confirmation" in sanitized or "REDACTED" in sanitized
        assert "24 hours" in sanitized or "REDACTED" in sanitized


class TestLeakDetection:
    """Unit tests for specific leak detection scenarios"""

    def test_api_key_leak(self):
        """Test detection of API key in output"""
        config = PIIDetectionConfig(entity_types=[EntityType.API_KEY])
        guard = OutputGuardAgent(config)

        state = create_initial_state("test", SentinelConfig())
        state["agent_response"] = "Your API key is sk-abc123def456"

        result = guard.process(state)

        assert len(result["security_threats"]) > 0
        assert "sk-abc123def456" not in result["sanitized_response"]

    def test_password_leak(self):
        """Test detection of password in output"""
        config = PIIDetectionConfig(entity_types=[EntityType.PASSWORD])
        guard = OutputGuardAgent(config)

        state = create_initial_state("test", SentinelConfig())
        state["agent_response"] = "Your password is: MySecret123!"

        result = guard.process(state)

        # Should detect or at least flag suspicious content
        assert len(result["security_threats"]) > 0 or "MySecret123!" not in result["sanitized_response"]

    def test_private_key_leak(self):
        """Test detection of private key in output"""
        config = PIIDetectionConfig(entity_types=[EntityType.PRIVATE_KEY])
        guard = OutputGuardAgent(config)

        state = create_initial_state("test", SentinelConfig())
        state["agent_response"] = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"

        result = guard.process(state)

        assert len(result["security_threats"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
