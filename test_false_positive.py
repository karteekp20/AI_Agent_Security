#!/usr/bin/env python3
"""
Debug which pattern is matching the false positive
"""

from sentinel.input_guard import InjectionDetector
from sentinel.schemas import InjectionDetectionConfig

# Initialize detector
config = InjectionDetectionConfig()
detector = InjectionDetector(config)

# Test the benign input
test_input = "you are very good person"
print(f"Testing: '{test_input}'\n")

# Get detection result
result = detector.detect_injection(test_input)

print(f"Detected: {result.detected}")
print(f"Confidence: {result.confidence}")
print(f"Risk Score: {result.risk_score}")
print(f"Should Block: {result.should_block}")
print(f"Patterns Matched: {result.patterns_matched}")
print(f"Explanation: {result.explanation}")

# Manually check each pattern category
print("\n" + "=" * 70)
print("Manual Pattern Matching:")
print("=" * 70)

for category, patterns in detector.patterns.items():
    matches = []
    for pattern in patterns:
        if pattern.search(test_input):
            matches.append(pattern.pattern)

    if matches:
        print(f"\n{category.upper()}:")
        for match in matches:
            print(f"  ✗ MATCHED: {match}")
