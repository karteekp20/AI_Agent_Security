# How to Run & Validate Phase 1 & Phase 2

## Quick Start (3 Commands)

```bash
# 1. Install dependencies (one-time)
pip install --user pydantic anthropic openai

# 2. Run quick validation
python3 quick_test.py

# 3. Run full demos
python3 examples/demo_phase1.py
python3 examples/demo_phase2.py
```

---

## Detailed Setup

### Option 1: User Install (Simplest)

```bash
# Install dependencies to user directory
pip install --user pydantic anthropic openai

# Verify
python3 -c "import pydantic; print('✓ pydantic installed')"

# Run validation
python3 quick_test.py
```

### Option 2: Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install pydantic anthropic openai

# Run validation
python3 quick_test.py
```

### Option 3: System-Wide (Requires sudo)

```bash
# Install system-wide
sudo apt install python3-pydantic  # Or use pip with --break-system-packages

# Run validation
python3 quick_test.py
```

---

## What Gets Validated

### `quick_test.py` validates:

1. ✅ **Imports** - All modules load correctly
2. ✅ **Phase 1 Basic** - Clean input processing
3. ✅ **Phase 1 PII** - Email/SSN detection
4. ✅ **Phase 1 Injection** - Prompt injection detection
5. ✅ **Phase 2 Shadow** - Shadow agent configuration

### `examples/demo_phase1.py` demonstrates:

1. Basic usage
2. PII detection & redaction
3. Prompt injection detection
4. Multiple PII types
5. Risk aggregation
6. Context-aware adjustment
7. Audit trail

### `examples/demo_phase2.py` demonstrates:

1. Shadow agents disabled by default
2. Shadow agent escalation
3. Low-risk no escalation
4. Threshold configuration
5. Fallback mechanism
6. Circuit breaker
7. Selective agents
8. Hybrid architecture

---

## Expected Output

### `quick_test.py` - SUCCESS:

```
======================================================================
QUICK VALIDATION - PHASE 1 & PHASE 2
======================================================================

[1/5] Testing imports...
✓ All imports successful

[2/5] Testing Phase 1 - Clean Input...
✓ Risk Score: 0.05
✓ Blocked: False
✓ Phase 1 working!

[3/5] Testing Phase 1 - PII Detection...
✓ PII Detected: 1 entities
✓ Risk Score: 0.65
✓ PII detection working!

[4/5] Testing Phase 1 - Prompt Injection Detection...
✓ Injection Detected: True
✓ Risk Score: 0.85
✓ Injection detection working!

[5/5] Testing Phase 2 - Shadow Agents...
✓ Shadow Agents Enabled (default): False
✓ Shadow Agents Enabled: True
✓ Shadow Escalated: True
✓ Phase 2 working! (using fallback without API key)

======================================================================
VALIDATION COMPLETE
======================================================================

✅ Phase 1: Risk Scoring - WORKING
✅ Phase 2: Shadow Agents - WORKING

Your system is ready to use!
```

---

## Manual Testing (No Scripts)

### Test 1: Phase 1 - Basic

```python
python3
>>> import sys
>>> sys.path.insert(0, '/home/karteek/Documents/Cloud_Workspace/ai_agent_security')
>>> from sentinel import SentinelConfig, SentinelGateway
>>> config = SentinelConfig()
>>> gateway = SentinelGateway(config)
>>> result = gateway.invoke("Hello", lambda x: "Hi")
>>> print(f"Risk: {result['aggregated_risk']['overall_risk_score']:.2f}")
Risk: 0.05
>>> print("✓ Working!")
✓ Working!
```

### Test 2: Phase 1 - PII Detection

```python
>>> result = gateway.invoke("My email is john@example.com", lambda x: "Got it")
>>> print(f"PII Count: {len(result['audit_log']['original_entities'])}")
PII Count: 1
>>> print(f"Risk: {result['aggregated_risk']['overall_risk_score']:.2f}")
Risk: 0.65
>>> print("✓ PII Detection Working!")
✓ PII Detection Working!
```

### Test 3: Phase 2 - Shadow Agents

```python
>>> from sentinel.schemas import ShadowAgentEscalationConfig
>>> config2 = SentinelConfig(
...     shadow_agents=ShadowAgentEscalationConfig(enabled=True, medium_risk_threshold=0.5)
... )
>>> gateway2 = SentinelGateway(config2)
>>> result = gateway2.invoke("My SSN is 123-45-6789", lambda x: "OK")
>>> print(f"Escalated: {result['shadow_agent_escalated']}")
Escalated: True
>>> print("✓ Shadow Agents Working!")
✓ Shadow Agents Working!
```

---

## Troubleshooting

### Issue: "No module named 'pydantic'"

```bash
# Solution: Install dependencies
pip install --user pydantic anthropic openai
```

### Issue: "externally-managed-environment"

```bash
# Solution 1: Use --user flag
pip install --user pydantic

# Solution 2: Use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install pydantic
```

### Issue: "ImportError" or "ModuleNotFoundError"

```bash
# Solution: Add to PYTHONPATH
export PYTHONPATH=/home/karteek/Documents/Cloud_Workspace/ai_agent_security:$PYTHONPATH
python3 quick_test.py
```

---

## Summary

**To validate Phase 1 & Phase 2:**

```bash
# Install (one-time)
pip install --user pydantic anthropic openai

# Run validation
python3 quick_test.py

# Expected: All 5 tests pass ✓
```

**To use in your code:**

```python
from sentinel import SentinelConfig, SentinelGateway

config = SentinelConfig()
gateway = SentinelGateway(config)

result = gateway.invoke(
    user_input="Your input here",
    agent_executor=your_agent_function
)

print(f"Risk: {result['aggregated_risk']['overall_risk_score']:.2f}")
print(f"Blocked: {result['blocked']}")
```

---

## Next Steps

1. ✅ Run `python3 quick_test.py` to validate
2. ✅ Try `python3 examples/demo_phase1.py` for detailed demo
3. ✅ Try `python3 examples/demo_phase2.py` for shadow agents
4. ✅ Integrate into your application
5. ✅ Deploy to production!
