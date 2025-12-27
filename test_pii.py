#!/usr/bin/env python3
"""
Quick test to verify PII detection is working
"""

from sentinel.input_guard import PIIDetector, InputGuardAgent
from sentinel.schemas import PIIDetectionConfig, InjectionDetectionConfig, create_initial_state, SentinelConfig

# Test direct PII detector
print("=" * 70)
print("TEST 1: Direct PII Detector")
print("=" * 70)

config = PIIDetectionConfig()
detector = PIIDetector(config)

test_text = "Call me at 555-123-4567 or my SSN is 123-45-6789"
print(f"\nTest text: {test_text}")
print(f"\nPII Config:")
print(f"  - enabled: {config.enabled}")
print(f"  - use_regex: {config.use_regex}")
print(f"  - use_ner: {config.use_ner}")
print(f"  - entity_types: {config.entity_types}")

entities = detector.detect_pii(test_text)
print(f"\nDetected {len(entities)} PII entities:")
for entity in entities:
    print(f"  - {entity.entity_type}: '{entity.original_value}' -> '{entity.redacted_value}'")

redacted = detector.redact_text(test_text, entities)
print(f"\nRedacted text: {redacted}")

# Test via InputGuardAgent
print("\n" + "=" * 70)
print("TEST 2: InputGuardAgent")
print("=" * 70)

pii_config = PIIDetectionConfig()
injection_config = InjectionDetectionConfig()
guard = InputGuardAgent(pii_config, injection_config)

sentinel_config = SentinelConfig()
state = create_initial_state(test_text, sentinel_config)

print(f"\nInitial state:")
print(f"  - user_input: {state['user_input']}")
print(f"  - original_entities: {len(state.get('original_entities', []))}")

processed_state = guard.process(state)

print(f"\nProcessed state:")
print(f"  - redacted_input: {processed_state['redacted_input']}")
print(f"  - original_entities: {len(processed_state.get('original_entities', []))}")
print(f"  - injection_detected: {processed_state.get('injection_detected')}")

for entity in processed_state.get('original_entities', []):
    print(f"  - Entity: {entity}")

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)
