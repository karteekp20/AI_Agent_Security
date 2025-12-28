"""
Shadow Input Agent: LLM-Powered Intent Analysis
Provides deep intent analysis beyond pattern matching
"""

from typing import Dict, Any, List
from .base import ShadowAgentBase, ShadowAgentResponse, ShadowAgentConfig
from .prompts import (
    INPUT_ANALYSIS_PROMPT,
    META_SECURITY_PROMPT,
    format_conversation_history,
    format_threats,
)


class ShadowInputAgent(ShadowAgentBase):
    """
    Shadow Input Agent for deep intent analysis

    Capabilities:
    1. Intent analysis - understand what the user is really trying to do
    2. Social engineering detection - detect manipulation attempts
    3. Context-aware injection detection - understand semantic injection
    4. Multi-turn attack detection - detect attacks spanning conversation
    """

    def __init__(self, config: ShadowAgentConfig):
        super().__init__(config, agent_type="shadow_input")

    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """Build analysis prompt for input validation"""
        user_input = context.get("user_input", "")
        conversation_history = context.get("conversation_history", [])
        existing_threats = context.get("existing_threats", [])
        request_context = context.get("request_context", {})

        return INPUT_ANALYSIS_PROMPT.format(
            meta_prompt=META_SECURITY_PROMPT,
            user_input=user_input,
            conversation_history=format_conversation_history(conversation_history),
            existing_threats=format_threats(existing_threats),
            user_role=request_context.get("user_role", "unknown"),
            trust_score=request_context.get("trust_score", 0.5),
            previous_violations=request_context.get("previous_violations_count", 0),
        )

    def _fallback_analysis(self, context: Dict[str, Any]) -> ShadowAgentResponse:
        """
        Fallback rule-based analysis if LLM fails

        Uses simple heuristics:
        - If existing threats detected, use high risk
        - If low trust score, increase risk
        - If previous violations, increase risk
        """
        existing_threats = context.get("existing_threats", [])
        request_context = context.get("request_context", {})
        user_input = context.get("user_input", "")

        # Calculate fallback risk score
        risk_score = 0.0

        # Existing threats contribute to risk
        if existing_threats:
            severity_map = {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.3}
            max_severity = max(
                [severity_map.get(t.get("severity", "low"), 0.3) for t in existing_threats],
                default=0.0
            )
            risk_score = max(risk_score, max_severity)

        # Trust score modifier
        trust_score = request_context.get("trust_score", 0.5)
        if trust_score < 0.3:
            risk_score = min(risk_score + 0.2, 1.0)

        # Previous violations modifier
        violations = request_context.get("previous_violations_count", 0)
        if violations > 0:
            risk_score = min(risk_score + (violations * 0.1), 1.0)

        # Simple keyword-based detection for common attacks
        dangerous_keywords = [
            "ignore previous",
            "disregard",
            "system prompt",
            "training data",
            "bypass",
            "jailbreak",
            "pretend you are",
        ]

        user_input_lower = user_input.lower()
        keyword_matches = [kw for kw in dangerous_keywords if kw in user_input_lower]

        if keyword_matches:
            risk_score = min(risk_score + (len(keyword_matches) * 0.15), 1.0)

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

        threats = []
        if existing_threats:
            threats.append("Threats detected by rule-based analysis")
        if keyword_matches:
            threats.append(f"Suspicious keywords: {', '.join(keyword_matches)}")
        if trust_score < 0.3:
            threats.append("Low trust score")
        if violations > 0:
            threats.append(f"Previous violations: {violations}")

        return ShadowAgentResponse(
            agent_type="shadow_input",
            risk_score=risk_score,
            risk_level=risk_level,
            confidence=0.6,  # Lower confidence for fallback
            threats_detected=threats,
            reasoning="Fallback rule-based analysis (LLM unavailable)",
            recommendations=[
                "Review user input manually" if risk_score > 0.7 else "Proceed with caution",
                "Monitor subsequent requests from this user",
            ],
            llm_provider="fallback",
            llm_model="rule-based",
            tokens_used=0,
            latency_ms=0.0,
            fallback_used=True,
        )

    def analyze_intent(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Specialized intent analysis

        Args:
            user_input: User's input message
            context: Additional context (history, user info, etc.)

        Returns:
            Intent analysis results
        """
        analysis_context = {
            "user_input": user_input,
            "conversation_history": context.get("conversation_history", []),
            "request_context": context.get("request_context", {}),
            "existing_threats": context.get("existing_threats", []),
        }

        response = self.analyze(analysis_context)

        return {
            "malicious_intent_detected": response.risk_score > 0.7,
            "intent_confidence": response.confidence,
            "risk_score": response.risk_score,
            "threats": response.threats_detected,
            "reasoning": response.reasoning,
        }

    def detect_social_engineering(
        self,
        user_input: str,
        conversation_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Detect social engineering attacks across conversation

        Args:
            user_input: Current user input
            conversation_history: Previous messages

        Returns:
            Social engineering analysis
        """
        # Look for patterns across conversation
        # E.g., building trust then making malicious request

        context = {
            "user_input": user_input,
            "conversation_history": conversation_history,
            "request_context": {},
            "existing_threats": [],
        }

        response = self.analyze(context)

        # Extract social engineering specific signals
        social_engineering_indicators = [
            "trust building",
            "authority impersonation",
            "urgency creation",
            "emotional manipulation",
            "information gathering",
        ]

        detected_techniques = [
            indicator for indicator in social_engineering_indicators
            if indicator in response.reasoning.lower()
        ]

        return {
            "social_engineering_detected": len(detected_techniques) > 0,
            "techniques_detected": detected_techniques,
            "risk_score": response.risk_score,
            "confidence": response.confidence,
            "reasoning": response.reasoning,
        }
