"""
Shadow State Agent: LLM-Powered Behavioral Analysis
Detects goal drift, anomalous behavior, and resource abuse
"""

from typing import Dict, Any, List
from .base import ShadowAgentBase, ShadowAgentResponse, ShadowAgentConfig
from .prompts import (
    BEHAVIOR_ANALYSIS_PROMPT,
    GOAL_DRIFT_ANALYSIS_PROMPT,
    META_SECURITY_PROMPT,
    format_tool_calls,
)


class ShadowStateAgent(ShadowAgentBase):
    """
    Shadow State Agent for behavioral analysis

    Capabilities:
    1. Goal drift detection - detect when agent deviates from user intent
    2. Behavioral anomaly detection - identify unusual execution patterns
    3. Resource abuse detection - detect excessive token/API usage
    4. Tool misuse detection - identify suspicious tool call patterns
    """

    def __init__(self, config: ShadowAgentConfig):
        super().__init__(config, agent_type="shadow_state")

    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """Build analysis prompt for behavioral analysis"""
        execution_trace = context.get("execution_trace", [])
        tool_calls = context.get("tool_calls", [])
        loop_detection = context.get("loop_detection", {})
        cost_metrics = context.get("cost_metrics", {})
        user_intent = context.get("user_intent", "")
        expected_behavior = context.get("expected_behavior", "Normal agent execution")

        # Format execution trace
        trace_formatted = "\n".join([
            f"{i+1}. {step}" for i, step in enumerate(execution_trace[-10:])  # Last 10 steps
        ]) if execution_trace else "No execution trace available"

        return BEHAVIOR_ANALYSIS_PROMPT.format(
            meta_prompt=META_SECURITY_PROMPT,
            execution_trace=trace_formatted,
            tool_calls=format_tool_calls(tool_calls),
            loop_detection=str(loop_detection),
            total_tokens=cost_metrics.get("total_tokens", 0),
            api_calls=cost_metrics.get("total_api_calls", 0),
            execution_time_ms=cost_metrics.get("total_duration_ms", 0),
            user_intent=user_intent,
            expected_behavior=expected_behavior,
        )

    def _fallback_analysis(self, context: Dict[str, Any]) -> ShadowAgentResponse:
        """
        Fallback rule-based analysis if LLM fails

        Uses heuristics:
        - Loop detection results
        - Token usage thresholds
        - Tool call patterns
        """
        loop_detection = context.get("loop_detection", {})
        cost_metrics = context.get("cost_metrics", {})
        tool_calls = context.get("tool_calls", [])

        risk_score = 0.0
        threats = []

        # Loop detection risk
        if loop_detection.get("loop_detected", False):
            loop_confidence = loop_detection.get("confidence", 0.0)
            risk_score = max(risk_score, loop_confidence)
            threats.append(f"Loop detected: {loop_detection.get('loop_type', 'unknown')}")

        # Cost-based risk
        total_tokens = cost_metrics.get("total_tokens", 0)
        if total_tokens > 100000:  # > 100k tokens
            cost_risk = min((total_tokens - 100000) / 100000, 1.0)
            risk_score = max(risk_score, cost_risk)
            threats.append(f"High token usage: {total_tokens}")

        # API call frequency
        api_calls = cost_metrics.get("total_api_calls", 0)
        if api_calls > 50:
            api_risk = min((api_calls - 50) / 50, 0.8)
            risk_score = max(risk_score, api_risk)
            threats.append(f"High API call count: {api_calls}")

        # Tool call patterns
        if tool_calls:
            # Check for repetitive tool calls
            tool_names = [call.get("tool", "") for call in tool_calls]
            if len(tool_names) > 5:
                unique_tools = len(set(tool_names))
                if unique_tools < len(tool_names) * 0.3:  # < 30% unique
                    risk_score = max(risk_score, 0.6)
                    threats.append("Repetitive tool call pattern detected")

        # Determine risk level
        if risk_score >= 0.95:
            risk_level = "critical"
        elif risk_score >= 0.8:
            risk_level = "high"
        elif risk_score >= 0.5:
            risk_level = "medium"
        elif risk_score >= 0.2:
            risk_level = "low"
        else:
            risk_level = "none"

        return ShadowAgentResponse(
            agent_type="shadow_state",
            risk_score=risk_score,
            risk_level=risk_level,
            confidence=0.6,
            threats_detected=threats if threats else ["No threats detected"],
            reasoning="Fallback rule-based behavioral analysis (LLM unavailable)",
            recommendations=[
                "Monitor agent execution" if risk_score > 0.5 else "Continue normal operation",
                "Review execution logs if issues persist",
            ],
            llm_provider="fallback",
            llm_model="rule-based",
            tokens_used=0,
            latency_ms=0.0,
            fallback_used=True,
        )

    def detect_goal_drift(
        self,
        original_intent: str,
        agent_actions: List[str],
        current_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Detect if agent has drifted from original user intent

        Args:
            original_intent: User's original goal
            agent_actions: List of actions taken by agent
            current_state: Current agent state

        Returns:
            Goal drift analysis
        """
        prompt = GOAL_DRIFT_ANALYSIS_PROMPT.format(
            meta_prompt=META_SECURITY_PROMPT,
            original_intent=original_intent,
            agent_actions="\n".join([f"{i+1}. {action}" for i, action in enumerate(agent_actions)]),
            current_state=str(current_state),
        )

        try:
            llm_response = self._call_llm(prompt)
            result = llm_response["result"]

            return {
                "goal_drift_detected": result.get("goal_drift_detected", False),
                "drift_severity": result.get("drift_severity", 0.0),
                "alignment_score": result.get("original_goal_alignment", 1.0),
                "evidence": result.get("evidence", []),
                "risk_score": result.get("risk_score", 0.0),
            }

        except Exception:
            # Fallback: simple heuristic
            # If agent has taken many actions but current state doesn't reflect progress
            action_count = len(agent_actions)
            if action_count > 10:
                return {
                    "goal_drift_detected": True,
                    "drift_severity": 0.5,
                    "alignment_score": 0.5,
                    "evidence": ["High action count with unclear progress"],
                    "risk_score": 0.5,
                }

            return {
                "goal_drift_detected": False,
                "drift_severity": 0.0,
                "alignment_score": 1.0,
                "evidence": [],
                "risk_score": 0.0,
            }

    def analyze_tool_usage_pattern(
        self,
        tool_calls: List[Dict[str, Any]],
        expected_tools: List[str],
    ) -> Dict[str, Any]:
        """
        Analyze tool usage for suspicious patterns

        Args:
            tool_calls: List of tool calls made
            expected_tools: List of expected tools for this task

        Returns:
            Tool usage analysis
        """
        if not tool_calls:
            return {
                "suspicious_pattern": False,
                "anomaly_score": 0.0,
                "findings": [],
            }

        tool_names = [call.get("tool", "") for call in tool_calls]
        unexpected_tools = [t for t in tool_names if t not in expected_tools]

        # Calculate anomaly metrics
        repetition_score = 0.0
        if len(tool_names) > 3:
            unique_ratio = len(set(tool_names)) / len(tool_names)
            if unique_ratio < 0.4:  # High repetition
                repetition_score = 1.0 - unique_ratio

        unexpected_score = len(unexpected_tools) / max(len(tool_names), 1)

        anomaly_score = (repetition_score * 0.6) + (unexpected_score * 0.4)

        findings = []
        if repetition_score > 0.5:
            findings.append(f"High tool repetition detected ({repetition_score:.2f})")
        if unexpected_tools:
            findings.append(f"Unexpected tools used: {set(unexpected_tools)}")

        return {
            "suspicious_pattern": anomaly_score > 0.5,
            "anomaly_score": anomaly_score,
            "findings": findings,
            "repetition_score": repetition_score,
            "unexpected_tool_ratio": unexpected_score,
        }

    def detect_resource_abuse(
        self,
        cost_metrics: Dict[str, Any],
        time_window_seconds: int = 60,
    ) -> Dict[str, Any]:
        """
        Detect excessive resource consumption

        Args:
            cost_metrics: Current cost metrics
            time_window_seconds: Time window for rate calculation

        Returns:
            Resource abuse analysis
        """
        total_tokens = cost_metrics.get("total_tokens", 0)
        api_calls = cost_metrics.get("total_api_calls", 0)
        duration_ms = cost_metrics.get("total_duration_ms", 1)

        # Calculate rates
        tokens_per_second = (total_tokens / duration_ms) * 1000 if duration_ms > 0 else 0
        calls_per_second = (api_calls / duration_ms) * 1000 if duration_ms > 0 else 0

        # Thresholds (configurable)
        token_threshold = 1000  # tokens/sec
        call_threshold = 5      # calls/sec

        abuse_detected = (
            tokens_per_second > token_threshold or
            calls_per_second > call_threshold
        )

        severity = 0.0
        if tokens_per_second > token_threshold:
            severity = max(severity, min(tokens_per_second / token_threshold, 1.0))
        if calls_per_second > call_threshold:
            severity = max(severity, min(calls_per_second / call_threshold, 1.0))

        return {
            "abuse_detected": abuse_detected,
            "severity": severity,
            "metrics": {
                "tokens_per_second": tokens_per_second,
                "calls_per_second": calls_per_second,
                "total_tokens": total_tokens,
                "total_api_calls": api_calls,
            },
            "recommendations": [
                "Implement rate limiting" if abuse_detected else "Continue monitoring",
                "Review agent execution logic" if severity > 0.7 else "Normal operation",
            ],
        }
