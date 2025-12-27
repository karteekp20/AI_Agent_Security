#!/usr/bin/env python3
"""
Check what the gateway.invoke() returns
"""

from sentinel import SentinelConfig, SentinelGateway
import json

# Demo agent
def demo_agent(redacted_input: str) -> str:
    return f"Processed: {redacted_input}"

# Initialize gateway
gateway = SentinelGateway(SentinelConfig())

# Test with PII
result = gateway.invoke(
    user_input="Call me at 555-123-4567 or my SSN is 123-45-6789",
    agent_executor=demo_agent
)

print("Keys in result:")
for key in result.keys():
    print(f"  - {key}")

print("\n" + "=" * 70)
print("audit_log structure:")
print("=" * 70)
audit_log = result.get('audit_log', {})
for key, value in audit_log.items():
    if key == 'events':
        print(f"\n{key}: {len(value)} events")
        for i, event in enumerate(value[:3]):
            print(f"  Event {i+1}: {event.get('event_type')}")
            print(f"    Data: {json.dumps(event.get('data', {}), indent=6)}")
    else:
        print(f"{key}: {value}")
