#!/usr/bin/env python3
"""
Test the full gateway flow like the API server
"""

from sentinel import SentinelConfig, SentinelGateway

# Demo agent (same as in server.py)
def demo_agent(redacted_input: str) -> str:
    """Demo AI agent that the security system protects"""
    responses = {
        "weather": "The weather is sunny and 72°F today.",
        "hello": "Hello! How can I assist you today!",
        "default": f"I've processed your request: '{redacted_input[:50]}...' - This is a demo response from the protected AI agent."
    }

    lower_input = redacted_input.lower()
    if "weather" in lower_input:
        return responses["weather"]
    elif "hello" in lower_input or "hi" in lower_input:
        return responses["hello"]
    else:
        return responses["default"]

# Initialize gateway
print("Initializing Sentinel Gateway...")
sentinel_config = SentinelConfig()
print(f"Config - enable_input_guard: {sentinel_config.enable_input_guard}")
print(f"Config - PII detection enabled: {sentinel_config.pii_detection.enabled}")
print(f"Config - PII use_regex: {sentinel_config.pii_detection.use_regex}")
print(f"Config - PII use_ner: {sentinel_config.pii_detection.use_ner}")

gateway = SentinelGateway(sentinel_config)
print("Gateway initialized\n")

# Test with PII
test_input = "Call me at 555-123-4567 or my SSN is 123-45-6789"
print(f"Test input: {test_input}\n")

print("Invoking gateway with demo agent...")
result = gateway.invoke(
    user_input=test_input,
    agent_executor=demo_agent
)

print("\n" + "=" * 70)
print("RESULT:")
print("=" * 70)
print(f"Blocked: {result['blocked']}")
print(f"Response: {result['response']}")
print(f"Threats: {len(result['threats'])}")

# Check audit log for PII
audit_log = result.get('audit_log', {})
print(f"\nAudit Log:")
print(f"  - PII redactions: {audit_log.get('pii_redactions', 0)}")
print(f"  - Injection attempts: {audit_log.get('injection_attempts', 0)}")
print(f"  - Events: {len(audit_log.get('events', []))}")

# Print audit events
for i, event in enumerate(audit_log.get('events', [])[:5]):
    print(f"\n  Event {i+1}:")
    print(f"    Type: {event.get('event_type')}")
    print(f"    Data: {event.get('data')}")

print("\n" + "=" * 70)
