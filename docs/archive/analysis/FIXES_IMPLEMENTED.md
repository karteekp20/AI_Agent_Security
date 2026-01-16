# PII Redaction Fixes - Implementation Complete

## Summary
All 4 critical issues from ISSUE_ANALYSIS_AND_FIXES.md have been successfully fixed and verified.

## Issues Fixed

### ✅ ISSUE #1: Generic Redaction Token → Entity-Specific Tokens
**Status**: FIXED

**Change**: `sentinel/input_guard.py` line 367-392
- Modified `_redact_value()` method to return `[ENTITY_TYPE_REDACTED]` instead of `[REDACTED]`
- Examples:
  - `555-123-4567` → `[PHONE_REDACTED]`
  - `123-45-6789` → `[SSN_REDACTED]`
  - `4532-1234-5678-9010` → `[CREDIT_CARD_REDACTED]`

**Before**:
```python
elif strategy == RedactionStrategy.TOKEN:
    return "[REDACTED]"
```

**After**:
```python
elif strategy == RedactionStrategy.TOKEN:
    token = entity_type.value.upper() if isinstance(entity_type, EntityType) else str(entity_type).upper()
    return f"[{token}_REDACTED]"
```

---

### ✅ ISSUE #2: Zero Risk Score → Proper Risk Calculation
**Status**: FIXED

**Changes**: 
1. `sentinel/schemas.py` line 540 - Changed default redaction strategy to TOKEN
2. `sentinel/api/server.py` line 491-505 - Updated risk score extraction with priority logic

The risk score is now correctly extracted from the input_guard layer:
- **Before**: `risk_score: 0`
- **After**: `risk_score: 0.237` (or higher for riskier inputs)

**Priority**: input_guard risk scores > aggregated_risk > threats

---

### ✅ ISSUE #3: Duplicate PII Count → Proper Deduplication
**Status**: FIXED

**Change**: `sentinel/input_guard.py` line 219-240
- Implemented `_deduplicate_entities()` method to remove overlapping detections
- Prevents the same PII from being counted multiple times by regex and NER

**Before**: `pii_count: 3` (duplicate detections)
**After**: `pii_count: 2` (2 unique entities: phone + SSN)

---

### ✅ ISSUE #4: Missing Redacted Input → Proper State Export
**Status**: FIXED

**Change**: `sentinel/gateway.py` line 595-597
- Added `redacted_input` to the invoke() return dictionary
- Added `original_entities` for entity tracking
- Added `pii_detected` boolean flag

The API now properly returns the redacted input with entity-specific tokens.

---

## Test Results

### Test Input
```
"Call me at 555-123-4567 or my SSN is 123-45-6789"
```

### Expected Output
```json
{
  "allowed": true,
  "redacted_input": "Call me at [PHONE_REDACTED] or my SSN is [SSN_REDACTED]",
  "risk_score": 0.237,
  "risk_level": "low",
  "blocked": false,
  "block_reason": null,
  "pii_detected": true,
  "pii_count": 2,
  "injection_detected": false,
  "escalated": false,
  "processing_time_ms": 87.5,
  "session_id": "session_xxx"
}
```

### Actual Output ✅
```
✅ ISSUE #1 - Entity-specific tokens: True
   redacted_input: Call me at [PHONE_REDACTED] or my SSN is [SSN_REDACTED]

✅ ISSUE #2 - Risk score: True
   risk_score: 0.237, risk_level: low

✅ ISSUE #3 - PII count (no duplicates): True
   pii_count: 2
      - phone: 555-123-4567 -> [PHONE_REDACTED]
      - ssn: 123-45-6789 -> [SSN_REDACTED]

✅ ISSUE #4 - Allowed after redaction: True
   allowed: True, blocked: False

✅ ALL ISSUES FIXED
```

---

## Files Modified

| File | Lines | Change |
|------|-------|--------|
| `sentinel/input_guard.py` | 219-240, 367-392 | Deduplication logic + entity-specific tokens |
| `sentinel/schemas.py` | 540 | Default strategy TOKEN instead of MASK |
| `sentinel/gateway.py` | 595-597 | Export redacted_input, entities, pii_detected |
| `sentinel/api/server.py` | 491-505 | Proper risk score extraction |

---

## Code Changes Summary

### 1. input_guard.py - Redaction Strategy
```python
# Entity-specific token: [ENTITY_TYPE_REDACTED]
token = entity_type.value.upper() if isinstance(entity_type, EntityType) else str(entity_type).upper()
return f"[{token}_REDACTED]"
```

### 2. input_guard.py - Deduplication
```python
def _deduplicate_entities(self, entities: List[RedactedEntity]) -> List[RedactedEntity]:
    """Remove overlapping duplicate entities, keeping highest confidence"""
    # Prevents same PII from being detected twice by regex + NER
```

### 3. schemas.py - Default Strategy
```python
redaction_strategy: RedactionStrategy = RedactionStrategy.TOKEN
```

### 4. gateway.py - State Export
```python
return {
    # ... existing fields ...
    "redacted_input": state.get("redacted_input"),
    "original_entities": state.get("original_entities", []),
    "pii_detected": state.get("audit_log", {}).get("pii_redactions", 0) > 0,
}
```

### 5. server.py - Risk Score Extraction
```python
# Priority: input_guard risk scores > aggregated_risk > threats
risk_scores = result_state.get("risk_scores", [])
for risk_score in risk_scores:
    if risk_score.get("layer") == "input_guard":
        final_risk_score = risk_score.get("risk_score", 0.0)
        break
```

---

## Verification
All fixes have been tested and verified to work correctly. The API now returns proper responses with:
- Entity-specific redaction tokens
- Correct risk scores from the input guard layer
- Deduplicated PII counts
- Properly exported redacted input

Status: **✅ READY FOR PRODUCTION**
