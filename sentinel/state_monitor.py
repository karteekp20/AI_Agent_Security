"""
State Monitor: Loop Detection and Cost Control
- Detects infinite loops and circular reasoning
- Monitors token consumption and cost
- Prevents agent runaway behavior
"""

import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import Counter, deque

from .schemas import (
    SentinelState,
    ToolCall,
    LoopDetection,
    LoopType,
    SecurityThreat,
    ThreatLevel,
    LoopDetectionConfig,
    AuditEvent,
    EventType,
    CostMetrics,
    RiskScore,  # Phase 1 addition
    RiskLevel,  # Phase 1 addition
)


# ============================================================================
# LOOP DETECTION
# ============================================================================

class LoopDetector:
    """Detects loops in agent behavior"""

    def __init__(self, config: LoopDetectionConfig):
        self.config = config
        self.call_history = deque(maxlen=config.window_size)

    def detect_loop(self, tool_calls: List[Dict[str, Any]]) -> LoopDetection:
        """
        Detect if agent is stuck in a loop
        Returns LoopDetection with analysis
        """
        if not self.config.enabled or len(tool_calls) < 2:
            return LoopDetection(
                loop_detected=False,
                confidence=0.0,
                repetition_count=0,
                tool_call_pattern=[],
                progress_made=True,
                suggested_action="continue",
            )

        # Convert dicts to ToolCall objects
        tool_call_objects = [ToolCall(**tc) for tc in tool_calls]

        # Update history
        for tc in tool_call_objects:
            self.call_history.append(tc)

        # Detection strategies
        exact_loop = self._detect_exact_loop(tool_call_objects)
        semantic_loop = self._detect_semantic_loop(tool_call_objects)
        cyclic_loop = self._detect_cyclic_pattern(tool_call_objects)

        # Determine best match
        detections = [
            (exact_loop, LoopType.EXACT),
            (semantic_loop, LoopType.SEMANTIC),
            (cyclic_loop, LoopType.CYCLIC),
        ]

        best_detection = max(detections, key=lambda x: x[0]["confidence"])

        if best_detection[0]["detected"]:
            loop_type = best_detection[1]
            confidence = best_detection[0]["confidence"]
            repetition_count = best_detection[0]["repetition_count"]
            pattern = best_detection[0]["pattern"]

            # Determine action
            suggested_action = self._determine_action(repetition_count)

            return LoopDetection(
                loop_detected=True,
                loop_type=loop_type,
                confidence=confidence,
                repetition_count=repetition_count,
                tool_call_pattern=pattern,
                progress_made=False,
                suggested_action=suggested_action,
            )

        return LoopDetection(
            loop_detected=False,
            confidence=0.0,
            repetition_count=0,
            tool_call_pattern=[],
            progress_made=True,
            suggested_action="continue",
        )

    def _detect_exact_loop(self, tool_calls: List[ToolCall]) -> Dict[str, Any]:
        """Detect exact duplicate tool calls"""
        if len(tool_calls) < 2:
            return {"detected": False, "confidence": 0.0, "repetition_count": 0, "pattern": []}

        # Check last few calls
        recent_calls = tool_calls[-self.config.max_identical_calls :]

        # Count by hash
        hash_counts = Counter([tc.arguments_hash for tc in recent_calls])

        max_count = max(hash_counts.values())

        if max_count >= self.config.max_identical_calls:
            # Found exact loop
            most_common_hash = hash_counts.most_common(1)[0][0]
            pattern = [
                tc.tool_name for tc in recent_calls
                if tc.arguments_hash == most_common_hash
            ]

            return {
                "detected": True,
                "confidence": 1.0,
                "repetition_count": max_count,
                "pattern": pattern,
            }

        return {"detected": False, "confidence": 0.0, "repetition_count": 0, "pattern": []}

    def _detect_semantic_loop(self, tool_calls: List[ToolCall]) -> Dict[str, Any]:
        """Detect semantically similar tool calls"""
        if len(tool_calls) < 3:
            return {"detected": False, "confidence": 0.0, "repetition_count": 0, "pattern": []}

        # Simple heuristic: Same tool name, similar arguments
        recent_calls = tool_calls[-self.config.window_size :]

        tool_name_counts = Counter([tc.tool_name for tc in recent_calls])

        for tool_name, count in tool_name_counts.items():
            if count >= 3:
                # Same tool called multiple times
                # Check if arguments are similar (simplified check)
                same_tool_calls = [tc for tc in recent_calls if tc.tool_name == tool_name]

                # Calculate semantic similarity (placeholder)
                similarity = self._calculate_semantic_similarity(same_tool_calls)

                if similarity >= self.config.semantic_similarity_threshold:
                    return {
                        "detected": True,
                        "confidence": similarity,
                        "repetition_count": count,
                        "pattern": [tool_name] * count,
                    }

        return {"detected": False, "confidence": 0.0, "repetition_count": 0, "pattern": []}

    def _detect_cyclic_pattern(self, tool_calls: List[ToolCall]) -> Dict[str, Any]:
        """Detect cyclic patterns like A->B->A->B"""
        if len(tool_calls) < 4:
            return {"detected": False, "confidence": 0.0, "repetition_count": 0, "pattern": []}

        recent_calls = tool_calls[-self.config.window_size :]
        pattern = [tc.tool_name for tc in recent_calls]

        # Look for repeating subsequences
        for cycle_length in range(2, len(pattern) // 2 + 1):
            cycle = pattern[:cycle_length]
            matches = 0

            for i in range(0, len(pattern) - cycle_length + 1, cycle_length):
                if pattern[i : i + cycle_length] == cycle:
                    matches += 1

            if matches >= 2:
                return {
                    "detected": True,
                    "confidence": 0.9,
                    "repetition_count": matches,
                    "pattern": cycle,
                }

        return {"detected": False, "confidence": 0.0, "repetition_count": 0, "pattern": []}

    def _calculate_semantic_similarity(self, tool_calls: List[ToolCall]) -> float:
        """Calculate semantic similarity between tool calls"""
        # Placeholder: Real implementation would use embeddings

        if len(tool_calls) < 2:
            return 0.0

        # Simple heuristic: Compare argument keys
        arg_keys_list = [set(tc.arguments.keys()) for tc in tool_calls]

        # Calculate Jaccard similarity between consecutive calls
        similarities = []
        for i in range(len(arg_keys_list) - 1):
            intersection = len(arg_keys_list[i] & arg_keys_list[i + 1])
            union = len(arg_keys_list[i] | arg_keys_list[i + 1])
            if union > 0:
                similarities.append(intersection / union)

        return sum(similarities) / len(similarities) if similarities else 0.0

    def _determine_action(self, repetition_count: int) -> str:
        """Determine what action to take based on repetition count"""
        if repetition_count >= self.config.block_threshold:
            return "block"
        elif repetition_count >= self.config.warn_threshold:
            return "warn"
        else:
            return "continue"


# ============================================================================
# COST MONITOR
# ============================================================================

class CostMonitor:
    """Monitors token usage and cost"""

    # Pricing per 1K tokens (example rates)
    PRICING = {
        "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
    }

    def __init__(self, model_name: str = "claude-3-5-sonnet"):
        self.model_name = model_name
        self.pricing = self.PRICING.get(model_name, {"input": 0.003, "output": 0.015})

    def calculate_cost(
        self, input_tokens: int, output_tokens: int
    ) -> CostMetrics:
        """Calculate cost metrics"""
        total_tokens = input_tokens + output_tokens

        input_cost = (input_tokens / 1000) * self.pricing["input"]
        output_cost = (output_tokens / 1000) * self.pricing["output"]
        total_cost = input_cost + output_cost

        return CostMetrics(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=total_cost,
        )

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        # Rough estimate: ~4 characters per token
        return len(text) // 4


# ============================================================================
# PROGRESS TRACKER
# ============================================================================

class ProgressTracker:
    """Tracks if agent is making progress"""

    def __init__(self):
        self.state_hashes = []

    def track_progress(self, state: SentinelState) -> bool:
        """
        Determine if agent is making progress
        Returns True if progress is being made
        """
        # Hash relevant parts of state
        state_snapshot = {
            "tool_calls": state["tool_calls"],
            "agent_response": state["agent_response"],
        }

        state_hash = hashlib.sha256(
            str(state_snapshot).encode()
        ).hexdigest()

        # Check if we've seen this state before
        if state_hash in self.state_hashes[-5:]:
            # No progress - same state
            return False

        self.state_hashes.append(state_hash)
        return True


# ============================================================================
# STATE MONITOR AGENT
# ============================================================================

class StateMonitorAgent:
    """
    State Monitor Agent: Prevents loops and monitors costs
    Tracks agent behavior over time
    """

    def __init__(self, loop_config: LoopDetectionConfig, model_name: str = "claude-3-5-sonnet"):
        self.loop_detector = LoopDetector(loop_config)
        self.cost_monitor = CostMonitor(model_name)
        self.progress_tracker = ProgressTracker()

    def calculate_risk_score(
        self,
        loop_detection: LoopDetection,
        cost_metrics: CostMetrics,
        progress_made: bool
    ) -> RiskScore:
        """
        Calculate risk score for state monitor layer (Phase 1)

        Risk factors:
        - Loop detection confidence
        - Cost/token consumption
        - Progress tracking
        """
        risk_factors = {}

        # 1. Loop Risk (0.0-1.0)
        loop_risk = 0.0
        if loop_detection.loop_detected:
            # Base risk from loop detection confidence
            loop_risk = loop_detection.confidence

            # Increase risk based on repetition count
            repetition_multiplier = min(loop_detection.repetition_count / 5.0, 1.5)
            loop_risk = min(loop_risk * repetition_multiplier, 1.0)

        risk_factors["loop_risk"] = loop_risk

        # 2. Cost Risk (0.0-1.0)
        cost_risk = 0.0
        if cost_metrics.total_tokens > 0:
            # Normalize based on reasonable thresholds
            # 10k tokens = low risk (0.2)
            # 50k tokens = medium risk (0.5)
            # 100k+ tokens = high risk (1.0)
            if cost_metrics.total_tokens >= 100000:
                cost_risk = 1.0
            elif cost_metrics.total_tokens >= 50000:
                cost_risk = 0.5 + ((cost_metrics.total_tokens - 50000) / 50000) * 0.5
            elif cost_metrics.total_tokens >= 10000:
                cost_risk = 0.2 + ((cost_metrics.total_tokens - 10000) / 40000) * 0.3
            else:
                cost_risk = (cost_metrics.total_tokens / 10000) * 0.2

        risk_factors["cost_risk"] = cost_risk

        # 3. Progress Risk (0.0-1.0)
        progress_risk = 0.0 if progress_made else 0.3  # Lack of progress is a warning sign

        risk_factors["progress_risk"] = progress_risk

        # 4. Combined Risk (weighted average)
        # Weight: 60% loop, 30% cost, 10% progress
        combined_risk = (loop_risk * 0.6) + (cost_risk * 0.3) + (progress_risk * 0.1)

        # 5. Determine risk level
        if combined_risk >= 0.95:
            risk_level = RiskLevel.CRITICAL
        elif combined_risk >= 0.8:
            risk_level = RiskLevel.HIGH
        elif combined_risk >= 0.5:
            risk_level = RiskLevel.MEDIUM
        elif combined_risk >= 0.2:
            risk_level = RiskLevel.LOW
        else:
            risk_level = RiskLevel.NONE

        # 6. Build explanation
        explanation_parts = []
        if loop_risk > 0:
            explanation_parts.append(
                f"Loop detected ({loop_detection.loop_type}, "
                f"{loop_detection.repetition_count} reps, risk={loop_risk:.2f})"
            )
        if cost_risk > 0.3:
            explanation_parts.append(
                f"High token usage ({cost_metrics.total_tokens} tokens, risk={cost_risk:.2f})"
            )
        if not progress_made:
            explanation_parts.append(f"No progress detected (risk={progress_risk:.2f})")

        explanation = "; ".join(explanation_parts) if explanation_parts else "No significant risks detected"

        return RiskScore(
            layer="state_monitor",
            risk_score=combined_risk,
            risk_level=risk_level,
            risk_factors=risk_factors,
            explanation=explanation,
        )

    def process(self, state: SentinelState) -> SentinelState:
        """
        Monitor agent state for loops and costs
        Returns updated state
        """

        # 1. Detect loops in tool calls
        loop_detection = self.loop_detector.detect_loop(state["tool_calls"])

        state["loop_detected"] = loop_detection.loop_detected
        state["loop_details"] = loop_detection.dict()

        # 2. Handle loop detection
        if loop_detection.loop_detected:
            severity = self._determine_severity(loop_detection)

            threat = SecurityThreat(
                threat_type="infinite_loop",
                severity=severity,
                description=f"Loop detected: {loop_detection.loop_type} "
                f"(repeated {loop_detection.repetition_count} times)",
                detection_method="state_monitor",
                confidence=loop_detection.confidence,
                evidence={
                    "loop_type": loop_detection.loop_type,
                    "pattern": loop_detection.tool_call_pattern,
                    "repetition_count": loop_detection.repetition_count,
                },
                blocked=loop_detection.suggested_action == "block",
            )

            state["security_threats"].append(threat.dict())
            state["audit_log"]["loops_detected"] += 1

            # Set control flags
            if loop_detection.suggested_action == "block":
                state["should_block"] = True
                state["block_reason"] = f"Infinite loop detected: {loop_detection.loop_type}"

            elif loop_detection.suggested_action == "warn":
                state["should_warn"] = True
                state["warning_message"] = "Agent may be repeating actions"

        # 3. Track progress
        progress_made = self.progress_tracker.track_progress(state)
        if not progress_made and len(state["tool_calls"]) > 3:
            state["should_warn"] = True
            state["warning_message"] = "Agent does not appear to be making progress"

        # 4. Calculate costs
        input_text = state["user_input"] + state["redacted_input"]
        output_text = state["agent_response"]

        input_tokens = self.cost_monitor.estimate_tokens(input_text)
        output_tokens = self.cost_monitor.estimate_tokens(output_text)

        cost_metrics = self.cost_monitor.calculate_cost(input_tokens, output_tokens)
        cost_metrics.tool_calls_count = len(state["tool_calls"])

        state["cost_metrics"] = cost_metrics.dict()

        # 5. Check for excessive costs
        if cost_metrics.total_tokens > 50000:
            threat = SecurityThreat(
                threat_type="excessive_cost",
                severity=ThreatLevel.MEDIUM,
                description=f"High token usage: {cost_metrics.total_tokens} tokens",
                detection_method="state_monitor",
                confidence=1.0,
                evidence={
                    "total_tokens": cost_metrics.total_tokens,
                    "estimated_cost": cost_metrics.estimated_cost_usd,
                },
                blocked=False,
            )
            state["security_threats"].append(threat.dict())

        # 6. Calculate risk score (Phase 1 enhancement)
        risk_score = self.calculate_risk_score(loop_detection, cost_metrics, progress_made)
        state["risk_scores"].append(risk_score.dict())

        # 7. Add audit events
        event = AuditEvent(
            event_type=EventType.LOOP_DETECTION,
            data={
                "loop_detected": loop_detection.loop_detected,
                "loop_type": str(loop_detection.loop_type) if loop_detection.loop_type else None,
                "repetition_count": loop_detection.repetition_count,
                "progress_made": progress_made,
                "total_tokens": cost_metrics.total_tokens,
                "estimated_cost": cost_metrics.estimated_cost_usd,
            },
        )

        state["audit_log"]["events"].append(event.dict())

        # Add risk assessment audit event
        risk_event = AuditEvent(
            event_type=EventType.RISK_ASSESSMENT,
            data={
                "layer": "state_monitor",
                "risk_score": risk_score.risk_score,
                "risk_level": risk_score.risk_level,
                "risk_factors": risk_score.risk_factors,
                "explanation": risk_score.explanation,
            },
        )
        state["audit_log"]["events"].append(risk_event.dict())

        return state

    def _determine_severity(self, loop_detection: LoopDetection) -> ThreatLevel:
        """Determine threat severity based on loop detection"""
        if loop_detection.suggested_action == "block":
            return ThreatLevel.HIGH
        elif loop_detection.suggested_action == "warn":
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW


# Export
__all__ = [
    'LoopDetector',
    'CostMonitor',
    'ProgressTracker',
    'StateMonitorAgent',
]
