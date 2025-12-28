"""
Shadow Output Agent: LLM-Powered Semantic Validation
Detects inference-based leaks and semantic policy violations
"""

from typing import Dict, Any, List
from .base import ShadowAgentBase, ShadowAgentResponse, ShadowAgentConfig
from .prompts import (
    OUTPUT_ANALYSIS_PROMPT,
    SEMANTIC_LEAK_DETECTION_PROMPT,
    META_SECURITY_PROMPT,
    format_threats,
)


class ShadowOutputAgent(ShadowAgentBase):
    """
    Shadow Output Agent for semantic output validation

    Capabilities:
    1. Semantic leak detection - detect inference-based data leaks
    2. Policy violation detection - identify unsafe recommendations
    3. Injection success detection - determine if injection bypassed guards
    4. Context-aware validation - validate based on user authorization level
    """

    def __init__(self, config: ShadowAgentConfig):
        super().__init__(config, agent_type="shadow_output")

    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """Build analysis prompt for output validation"""
        agent_response = context.get("agent_response", "")
        user_input = context.get("user_input", "")
        context_info = context.get("context_info", {})
        existing_threats = context.get("existing_threats", [])

        # Format context information
        context_formatted = "\n".join([
            f"- {key}: {value}" for key, value in context_info.items()
        ]) if context_info else "No context information available"

        return OUTPUT_ANALYSIS_PROMPT.format(
            meta_prompt=META_SECURITY_PROMPT,
            agent_response=agent_response,
            user_input=user_input,
            context_info=context_formatted,
            existing_threats=format_threats(existing_threats),
        )

    def _fallback_analysis(self, context: Dict[str, Any]) -> ShadowAgentResponse:
        """
        Fallback rule-based analysis if LLM fails

        Uses simple heuristics:
        - Existing threats from output guard
        - Keyword-based leak detection
        - Response length anomalies
        """
        agent_response = context.get("agent_response", "")
        existing_threats = context.get("existing_threats", [])
        user_input = context.get("user_input", "")

        risk_score = 0.0
        threats = []

        # Existing threats from rule-based output guard
        if existing_threats:
            severity_map = {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.3}
            max_severity = max(
                [severity_map.get(t.get("severity", "low"), 0.3) for t in existing_threats],
                default=0.0
            )
            risk_score = max(risk_score, max_severity)
            threats.append("Threats detected by rule-based output guard")

        # Keyword-based detection for common leaks
        leak_indicators = [
            "system prompt",
            "training data",
            "internal instruction",
            "confidential",
            "api key",
            "password",
            "secret",
        ]

        response_lower = agent_response.lower()
        detected_indicators = [ind for ind in leak_indicators if ind in response_lower]

        if detected_indicators:
            leak_risk = min(len(detected_indicators) * 0.2, 0.8)
            risk_score = max(risk_score, leak_risk)
            threats.append(f"Potential leak indicators: {', '.join(detected_indicators)}")

        # Check if response is suspiciously long (might be dumping data)
        if len(agent_response) > 5000:  # > 5k chars
            length_risk = min((len(agent_response) - 5000) / 10000, 0.5)
            risk_score = max(risk_score, length_risk)
            threats.append(f"Unusually long response: {len(agent_response)} chars")

        # Check if response repeats user input verbatim (possible injection success)
        if user_input and user_input.lower() in response_lower:
            # If response contains large portions of user input, might be reflection attack
            if len(user_input) > 100 and user_input.lower()[:100] in response_lower:
                risk_score = max(risk_score, 0.6)
                threats.append("Response reflects large portion of user input")

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
            agent_type="shadow_output",
            risk_score=risk_score,
            risk_level=risk_level,
            confidence=0.6,
            threats_detected=threats if threats else ["No threats detected"],
            reasoning="Fallback rule-based output analysis (LLM unavailable)",
            recommendations=[
                "Review output manually" if risk_score > 0.7 else "Output appears safe",
                "Consider additional redaction" if detected_indicators else "Proceed with output",
            ],
            llm_provider="fallback",
            llm_model="rule-based",
            tokens_used=0,
            latency_ms=0.0,
            fallback_used=True,
        )

    def detect_semantic_leak(
        self,
        response: str,
        sensitive_context: Dict[str, Any],
        user_role: str = "user",
    ) -> Dict[str, Any]:
        """
        Detect inference-based information leaks

        Args:
            response: Agent's response to analyze
            sensitive_context: Information that should NOT be revealed
            user_role: User's authorization level

        Returns:
            Semantic leak analysis
        """
        prompt = SEMANTIC_LEAK_DETECTION_PROMPT.format(
            meta_prompt=META_SECURITY_PROMPT,
            response=response,
            sensitive_context=str(sensitive_context),
            user_role=user_role,
        )

        try:
            llm_response = self._call_llm(prompt)
            result = llm_response["result"]

            return {
                "leak_detected": result.get("leak_detected", False),
                "leak_severity": result.get("leak_severity", 0.0),
                "leaked_types": result.get("leaked_information_types", []),
                "evidence": result.get("evidence", []),
                "risk_score": result.get("risk_score", 0.0),
            }

        except Exception:
            # Fallback: simple keyword matching
            sensitive_str = str(sensitive_context).lower()
            response_lower = response.lower()

            # Extract potential sensitive keywords from context
            sensitive_words = [
                word for word in sensitive_str.split()
                if len(word) > 5  # Only meaningful words
            ]

            leaked_words = [
                word for word in sensitive_words[:20]  # Check top 20 words
                if word in response_lower
            ]

            leak_detected = len(leaked_words) > 2  # More than 2 matches
            leak_severity = min(len(leaked_words) / 10, 1.0)

            return {
                "leak_detected": leak_detected,
                "leak_severity": leak_severity,
                "leaked_types": ["potential_context_leak"] if leak_detected else [],
                "evidence": [f"Matched words: {leaked_words[:5]}"] if leaked_words else [],
                "risk_score": leak_severity,
            }

    def validate_policy_compliance(
        self,
        response: str,
        policies: List[str],
    ) -> Dict[str, Any]:
        """
        Validate response against security policies

        Args:
            response: Agent's response
            policies: List of security policies to enforce

        Returns:
            Policy compliance analysis
        """
        violations = []
        risk_score = 0.0

        # Basic policy checks
        response_lower = response.lower()

        for policy in policies:
            policy_lower = policy.lower()

            # Simple rule-based checks
            if "never disclose" in policy_lower and "password" in policy_lower:
                if any(word in response_lower for word in ["password", "passwd", "pwd"]):
                    violations.append("Password disclosure policy violated")
                    risk_score = max(risk_score, 0.8)

            if "never reveal" in policy_lower and "system prompt" in policy_lower:
                if any(phrase in response_lower for phrase in ["system prompt", "instructions", "you are a"]):
                    violations.append("System prompt disclosure policy violated")
                    risk_score = max(risk_score, 0.9)

            if "illegal" in policy_lower:
                illegal_keywords = ["hack", "exploit", "bypass security", "crack"]
                if any(kw in response_lower for kw in illegal_keywords):
                    violations.append("Illegal activity policy violated")
                    risk_score = max(risk_score, 1.0)

        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "risk_score": risk_score,
            "policies_checked": len(policies),
        }

    def detect_injection_success(
        self,
        user_input: str,
        agent_response: str,
        injection_detected: bool,
    ) -> Dict[str, Any]:
        """
        Determine if a detected injection attempt succeeded

        Args:
            user_input: Original user input (potentially malicious)
            agent_response: Agent's response
            injection_detected: Whether input guard detected injection

        Returns:
            Injection success analysis
        """
        if not injection_detected:
            return {
                "injection_succeeded": False,
                "confidence": 1.0,
                "evidence": [],
                "risk_score": 0.0,
            }

        # Look for signs that injection succeeded
        success_indicators = []
        risk_score = 0.0

        response_lower = agent_response.lower()
        input_lower = user_input.lower()

        # Check if response follows injected instructions
        injection_phrases = [
            "ignore previous",
            "disregard above",
            "new instructions",
            "forget everything",
            "pretend you are",
        ]

        detected_phrases = [phrase for phrase in injection_phrases if phrase in input_lower]

        # If injection attempted to change behavior
        if "ignore" in input_lower or "disregard" in input_lower:
            # Check if response shows changed behavior
            if "i cannot" not in response_lower and "i should not" not in response_lower:
                success_indicators.append("Response does not show safety refusal")
                risk_score = max(risk_score, 0.7)

        # If injection attempted to extract system prompt
        if "system prompt" in input_lower or "instructions" in input_lower:
            if any(phrase in response_lower for phrase in ["you are a", "your role is", "you must"]):
                success_indicators.append("Response potentially reveals system instructions")
                risk_score = max(risk_score, 0.9)

        # If injection attempted to bypass filters
        if "bypass" in input_lower or "jailbreak" in input_lower:
            if len(agent_response) > 200:  # Long response might indicate successful bypass
                success_indicators.append("Unusually long response to bypass attempt")
                risk_score = max(risk_score, 0.6)

        injection_succeeded = len(success_indicators) > 0

        return {
            "injection_succeeded": injection_succeeded,
            "confidence": 0.7 if injection_succeeded else 0.9,
            "evidence": success_indicators,
            "risk_score": risk_score,
            "detected_injection_phrases": detected_phrases,
        }
