# 📊 POST /process API - Complete Flow Documentation

## Overview

The `/process` endpoint is the main entry point for all security operations. It orchestrates a multi-layer security system that protects AI agents from threats.

---

## 🚀 QUICK REFERENCE - Starting Points

### Main Entry Point (HTTP Layer)
**File:** `sentinel/api/server.py`  
**Line:** 290-460  
**Endpoint:** `POST /process`  
**Handler Function:** `async def process_input(req: ProcessRequest, request: Request, ...)`

---

## 📍 COMPLETE REQUEST FLOW

### Step 1: HTTP Request Arrives
```
HTTP POST /process
├─ Headers:
│  ├─ X-API-Key: sk_live_xxxxx
│  ├─ Content-Type: application/json
│  └─ [Other headers]
└─ Body:
   {
     "user_input": "My credit card is 4532-1234-5678-9010",
     "user_id": "user_123",
     "session_id": "sess_abc",
     "ip_address": "192.168.1.1",
     "metadata": {}
   }
```

---

## 🔄 DETAILED REQUEST-RESPONSE FLOW

```
REQUEST ARRIVES
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Request Validation (server.py:291-356)            │
├─────────────────────────────────────────────────────────────┤
│ • Parse ProcessRequest model                               │
│ • Extract X-API-Key from headers (line 313)               │
│ • Validate API key against database (line 323-329)        │
│ • Extract org_id and workspace_id from key                │
│ • Get client IP address (line 334)                        │
│ • Log incoming request                                     │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Rate Limiting (server.py:331-345)                │
├─────────────────────────────────────────────────────────────┤
│ app.state.rate_limiter.check_rate_limit()                 │
│ • Check per-user rate limit                               │
│ • Check per-IP rate limit                                 │
│ • Return 429 if exceeded                                  │
│ Location: sentinel/resilience/rate_limiter.py             │
└─────────────────────────────────────────────────────────────┘
    ↓
    ALLOWED? ───NO──→ HTTPException(429) → Return to client
    │ YES
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Create Initial State (server.py:347-358)          │
├─────────────────────────────────────────────────────────────┤
│ create_initial_state(user_input, config, ...)             │
│ • Initialize empty security state                         │
│ • Generate or use provided session_id                     │
│ • Set request context (user_id, ip_address, etc)         │
│ • Create empty threat list                                │
│ • Initialize audit log                                    │
│ Location: sentinel/schemas.py:create_initial_state()      │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Initialize Demo Agent (server.py:360-379)         │
├─────────────────────────────────────────────────────────────┤
│ def demo_agent(redacted_input: str) -> str:              │
│ • This is the AI agent being protected                    │
│ • Takes redacted input (PII removed)                      │
│ • Returns response                                        │
│ • In production: Your real LLM/AI agent                   │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Start Tracing (server.py:381-396)                │
├─────────────────────────────────────────────────────────────┤
│ if app.state.tracer:                                      │
│   with app.state.tracer.trace_request(...):              │
│     result = app.state.gateway.invoke(...)               │
│                                                           │
│ Location: sentinel/observability/tracing.py               │
│ Exports to: OpenTelemetry (Jaeger, Zipkin, etc)          │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: Main Gateway Invocation (gateway.py:553-596)     │
├─────────────────────────────────────────────────────────────┤
│ app.state.gateway.invoke(user_input, agent_executor)     │
│                                                           │
│ Returns:                                                  │
│ {                                                         │
│   "response": "...",                                      │
│   "blocked": bool,                                        │
│   "threats": [...],                                       │
│   "audit_log": {...},                                     │
│   "risk_scores": [...],                                   │
│   "aggregated_risk": {...},                               │
│   "warnings": "..."                                       │
│ }                                                         │
└─────────────────────────────────────────────────────────────┘
    ↓
```

---

## 🔐 GATEWAY INVOKE - DETAILED LAYER BREAKDOWN

### Gateway Flow (gateway.py:553-596)

```
gateway.invoke(user_input, agent_executor)
    ↓
    Check if LangGraph available? (line 577)
    │
    ├─ YES → _invoke_with_langgraph()
    └─ NO  → _invoke_manual()
    ↓
```

### Scenario A: Using LangGraph (Lines 598-644)

```
_invoke_with_langgraph(state, agent_executor)
    ↓
    graph.invoke(state)  ← Executes LangGraph workflow
    ↓
    Returns modified state
```

### Scenario B: Manual Orchestration (Lines 646-700+)

This is the more common path. It runs through each security layer sequentially:

```
_invoke_manual(state, agent_executor)
    ↓
    ┌─────────────────────────────────────────────┐
    │ LAYER 1: INPUT GUARD (Line 160-175)        │
    ├─────────────────────────────────────────────┤
    │ state = self.input_guard.process(state)    │
    │                                             │
    │ What it does:                              │
    │ • PII Detection                            │
    │ • Redaction (credit cards, SSN, etc)      │
    │ • Prompt Injection Detection               │
    │ • Content Moderation (toxicity)            │
    │ • Risk Scoring                             │
    │ • Audit Event Creation                     │
    │                                             │
    │ Location: sentinel/input_guard.py:757      │
    │ Time: ~50-100ms (with spaCy)              │
    │                                             │
    │ Output State Updates:                       │
    │ ├─ redacted_input (PII removed)            │
    │ ├─ original_entities (found PII)           │
    │ ├─ injection_detected                      │
    │ ├─ should_block (if threats)              │
    │ ├─ security_threats[]                      │
    │ └─ risk_scores[]                           │
    └─────────────────────────────────────────────┘
    ↓
    ┌─────────────────────────────────────────────┐
    │ DECISION: Should Block? (Check routing)    │
    ├─────────────────────────────────────────────┤
    │ if state["should_block"]:                  │
    │   → Jump to STEP 10 (Return blocked)       │
    │ else:                                       │
    │   → Continue to next layer                 │
    └─────────────────────────────────────────────┘
    ↓
    ┌─────────────────────────────────────────────┐
    │ LAYER 2: STATE MONITOR (Line 208-213)      │
    ├─────────────────────────────────────────────┤
    │ state = self.state_monitor.process(state)  │
    │                                             │
    │ What it does:                              │
    │ • Loop Detection (semantic similarity)     │
    │ • Cost Tracking (tokens used)              │
    │ • Resource Monitoring                      │
    │ • Budget Enforcement                       │
    │                                             │
    │ Location: sentinel/state_monitor.py        │
    │ Time: ~10ms                                │
    │                                             │
    │ Output State Updates:                       │
    │ ├─ loop_detected                           │
    │ ├─ cost_metrics                            │
    │ └─ risk_scores[] (adds state monitor risk) │
    └─────────────────────────────────────────────┘
    ↓
    ┌─────────────────────────────────────────────┐
    │ LAYER 3: AGENT EXECUTION (Line 177-206)   │
    ├─────────────────────────────────────────────┤
    │ def _agent_execution_node(state):           │
    │   response = agent_executor(state["redacted_input"])
    │                                             │
    │ What it does:                              │
    │ • Calls your AI agent with redacted input │
    │ • Agent never sees original PII            │
    │ • Captures response                        │
    │ • Records execution in audit log           │
    │                                             │
    │ Location: sentinel/gateway.py:177          │
    │ Time: Variable (depends on your agent)     │
    │                                             │
    │ Output State Updates:                       │
    │ ├─ agent_response                          │
    │ ├─ tool_calls[]                            │
    │ └─ audit_log events                        │
    └─────────────────────────────────────────────┘
    ↓
    ┌─────────────────────────────────────────────┐
    │ LAYER 4: OUTPUT GUARD (Line 215-221)      │
    ├─────────────────────────────────────────────┤
    │ state = self.output_guard.process(state)   │
    │                                             │
    │ What it does:                              │
    │ • Re-check for PII in response             │
    │ • Detect data leaks                        │
    │ • Check for injected code                  │
    │ • Sanitize response                        │
    │ • Risk scoring                             │
    │                                             │
    │ Location: sentinel/output_guard.py:233     │
    │ Time: ~30-50ms                             │
    │                                             │
    │ Output State Updates:                       │
    │ ├─ sanitized_response                      │
    │ ├─ response_pii_detected                   │
    │ └─ risk_scores[] (adds output guard risk) │
    └─────────────────────────────────────────────┘
    ↓
    ┌─────────────────────────────────────────────┐
    │ AGGREGATION: Risk Scoring (Line 427-547)  │
    ├─────────────────────────────────────────────┤
    │ state = self._aggregate_risk_scores(state) │
    │                                             │
    │ What it does:                              │
    │ • Combines risk scores from all layers     │
    │ • Weighted calculation:                    │
    │   ├─ Input guard risk (40%)                │
    │   ├─ State monitor risk (30%)              │
    │   └─ Output guard risk (30%)               │
    │ • Determines overall risk level            │
    │ • Decides if shadow agents escalate       │
    │                                             │
    │ Location: sentinel/gateway.py:427          │
    │                                             │
    │ Output State Updates:                       │
    │ ├─ aggregated_risk {}                      │
    │ ├─ overall_risk_score (0.0-1.0)           │
    │ ├─ overall_risk_level                      │
    │ └─ shadow_agent_escalated                  │
    └─────────────────────────────────────────────┘
    ↓
    ┌─────────────────────────────────────────────┐
    │ PHASE 2: SHADOW AGENTS (If escalated)     │
    ├─────────────────────────────────────────────┤
    │ if state["shadow_agent_escalated"]:       │
    │                                             │
    │   → Shadow Input Analysis (Line 284-331)  │
    │     _shadow_input_analysis_node(state)    │
    │     • Deep intent analysis                 │
    │     • LLM-based threat detection           │
    │                                             │
    │   → Shadow State Analysis (Line 333-380)  │
    │     _shadow_state_analysis_node(state)    │
    │     • Behavioral analysis                  │
    │     • Execution pattern detection          │
    │                                             │
    │   → Shadow Output Analysis (Line 382-421) │
    │     _shadow_output_analysis_node(state)   │
    │     • Response content analysis            │
    │     • Data leak detection                  │
    │                                             │
    │ Location: sentinel/shadow_agents/         │
    │ Time: ~500ms-2s (LLM-based, can be async) │
    └─────────────────────────────────────────────┘
    ↓
    ┌─────────────────────────────────────────────┐
    │ LAYER 5: RED TEAM (Optional/Async)        │
    ├─────────────────────────────────────────────┤
    │ state = self.red_team.process(state)      │
    │                                             │
    │ What it does:                              │
    │ • Adversarial testing                      │
    │ • Jailbreak attempts                       │
    │ • Vulnerability scanning                   │
    │ • Normally runs async                      │
    │                                             │
    │ Location: sentinel/red_team.py             │
    │ Time: Variable (typically async)           │
    └─────────────────────────────────────────────┘
    ↓
    ┌─────────────────────────────────────────────┐
    │ LAYER 6: AUDIT FINALIZATION (Line 232-234)│
    ├─────────────────────────────────────────────┤
    │ state = self.audit_manager.finalize_audit  │
    │                                             │
    │ What it does:                              │
    │ • Complete audit log                       │
    │ • Digital signature (HMAC-SHA256)          │
    │ • Tamper-proof evidence                    │
    │ • Compliance report generation             │
    │                                             │
    │ Location: sentinel/audit.py                │
    │ Time: ~5ms                                 │
    │                                             │
    │ Output State Updates:                       │
    │ └─ audit_log (complete & signed)           │
    └─────────────────────────────────────────────┘
    ↓
    Return modified state
```

---

## 📤 RESPONSE BUILDING (server.py:398-440)

```
After gateway.invoke() returns:
    ↓
    Collect Metrics (if enabled)
    ├─ Total requests processed
    ├─ Blocks by layer
    ├─ PII detections
    ├─ Processing time
    └─ Location: sentinel/observability/metrics.py
    ↓
    Build ProcessResponse object:
    {
      "allowed": !state["should_block"],
      "redacted_input": state["redacted_input"],
      "risk_score": state["aggregated_risk"]["overall_risk_score"],
      "risk_level": state["aggregated_risk"]["overall_risk_level"],
      "blocked": state["should_block"],
      "block_reason": state["block_reason"] if blocked else None,
      "pii_detected": len(state["original_entities"]) > 0,
      "pii_count": len(state["original_entities"]),
      "injection_detected": state["injection_detected"],
      "escalated": state["shadow_agent_escalated"],
      "processing_time_ms": (time.time() - start_time) * 1000,
      "session_id": session_id
    }
    ↓
    Return JSON Response (200 OK)
```

---

## 📍 FILE STRUCTURE & KEY LOCATIONS

### API Layer
```
sentinel/api/
├── server.py (Lines 290-460)     ← Entry point
├── config.py                       ← Configuration
└── dependencies.py                 ← Authentication
```

### Gateway & Orchestration
```
sentinel/
├── gateway.py (Lines 553-700+)     ← Main orchestration
└── schemas.py                      ← State definitions
```

### Security Layers
```
sentinel/
├── input_guard.py (Lines 757-880)  ← Layer 1
├── state_monitor.py                 ← Layer 2
├── output_guard.py (Lines 233+)    ← Layer 4
├── red_team.py                      ← Layer 5
└── audit.py                         ← Layer 6
```

### Advanced Features
```
sentinel/
├── shadow_agents/                   ← Phase 2
│   ├── input_analyzer.py
│   ├── state_analyzer.py
│   └── output_analyzer.py
├── meta_learning/                   ← Phase 3
└── observability/                   ← Phase 4
    ├── metrics.py
    ├── tracing.py
    └── logging.py
```

---

## 🔑 KEY VARIABLES & STATE

### Initial State (schemas.py)
```python
{
    "user_input": str,              # Original input
    "user_id": str,                 # User identifier
    "session_id": str,              # Unique session
    "request_context": dict,        # IP, metadata, etc
    
    # Layers' outputs
    "redacted_input": str,          # PII removed
    "original_entities": list,      # PII found
    "injection_detected": bool,
    "agent_response": str,          # Agent's output
    "sanitized_response": str,      # Final response
    
    # Threats & scoring
    "should_block": bool,           # Block request?
    "block_reason": str,
    "security_threats": list,       # All threats
    "risk_scores": list,            # Per-layer scores
    "aggregated_risk": dict,        # Combined risk
    
    # Audit
    "audit_log": {
        "events": list,
        "pii_redactions": int,
        "injection_attempts": int
    },
    
    # Advanced
    "shadow_agent_escalated": bool,
    "shadow_agent_analyses": list
}
```

---

## ⚡ PERFORMANCE BREAKDOWN

```
Layer 1 (Input Guard):    50-100ms   (regex + spaCy NER)
Layer 2 (State Monitor):   ~10ms     (fast checks)
Layer 3 (Agent Exec):      Variable  (your agent)
Layer 4 (Output Guard):    30-50ms   (regex + NER)
Aggregation:               ~5ms      (calculations)
Shadow Agents (async):     500ms-2s  (LLM-based, optional)
Layer 6 (Audit):           ~5ms      (signing)
─────────────────────────────────────
TOTAL SYNCHRONOUS:         95-165ms  (typical)
WITH SHADOW AGENTS:        500ms-2s+ (if escalated)
```

---

## 🚨 ERROR HANDLING

```
Rate Limit Exceeded
    ↓
    HTTPException(429) → Client
    
API Key Invalid
    ↓
    Logged but continues (treats as anonymous)
    
Agent Execution Error (Line 616-619)
    ↓
    state["agent_response"] = "Error executing agent: ..."
    state["should_warn"] = True
    Continue to output guard
    
Shadow Agent Failure (Line 326-329)
    ↓
    Logged as warning
    Continue with rule-based results
    
Any Exception
    ↓
    HTTPException(500) → Server error
    Logged for debugging
```

---

## 📊 REQUEST EXAMPLE

### Input
```bash
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_live_abc123" \
  -d '{
    "user_input": "My credit card is 4532-1234-5678-9010",
    "user_id": "user_123",
    "session_id": "sess_abc"
  }'
```

### Processing Flow Through Layers
```
1. Input Guard:
   Input: "My credit card is 4532-1234-5678-9010"
   Detection: Credit card found at position 17
   Redaction: "My credit card is [CREDIT_CARD_REDACTED]"
   Risk: HIGH (0.95)
   Decision: BLOCK (dangerous)

2. Since blocked, skip remaining layers

3. Output: Return block_reason to client
```

### Output Response
```json
{
  "allowed": false,
  "redacted_input": "My credit card is [CREDIT_CARD_REDACTED]",
  "risk_score": 0.95,
  "risk_level": "high",
  "blocked": true,
  "block_reason": "PII detected: credit_card",
  "pii_detected": true,
  "pii_count": 1,
  "injection_detected": false,
  "escalated": false,
  "processing_time_ms": 87.5,
  "session_id": "sess_abc"
}
```

---

## 🔍 DEBUGGING TIPS

### Enable Detailed Logging
```python
# In config.py
config.log_level = "DEBUG"
config.enable_logging = True
```

### Check Audit Trail
```python
# In response:
response["audit_log"]["events"]  # All events
response["audit_log"]["pii_redactions"]  # Count
```

### Monitor Metrics
```
GET http://localhost:8000/metrics

# Prometheus format:
sentinel_requests_total{status="blocked"}
sentinel_pii_detections_total{entity_type="credit_card"}
sentinel_request_duration_seconds{endpoint="/process"}
```

### Trace With Jaeger
```
# If OpenTelemetry enabled:
http://localhost:16686  # Jaeger UI
```

---

## 📚 REFERENCES

| Component | File | Lines | Function |
|-----------|------|-------|----------|
| Entry Point | server.py | 290-460 | process_input |
| Gateway | gateway.py | 553-596 | invoke |
| Manual Flow | gateway.py | 646-700+ | _invoke_manual |
| Input Guard | input_guard.py | 757-880 | InputGuardAgent.process |
| State Monitor | state_monitor.py | - | StateMonitorAgent.process |
| Output Guard | output_guard.py | 233+ | OutputGuardAgent.process |
| Risk Aggregation | gateway.py | 427-547 | _aggregate_risk_scores |
| Shadow Agents | shadow_agents/ | - | Multiple analyzers |
| Audit | audit.py | - | AuditManager |

---

**Version:** 1.0  
**Last Updated:** January 2025  
**Status:** ✅ Complete API Flow Documentation

