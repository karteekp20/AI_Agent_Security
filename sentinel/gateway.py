"""
Sentinel Gateway: Main LangGraph Orchestration
Coordinates all security layers (Input Guard, Output Guard, State Monitor, Red Team, Audit)
"""

from typing import Callable, Dict, Any, Optional, Literal
from datetime import datetime

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("Warning: LangGraph not installed. Install with: pip install langgraph")

from .schemas import (
    SentinelState,
    SentinelConfig,
    create_initial_state,
    AuditEvent,
    EventType,
    AggregatedRiskScore,  # Phase 1 addition
    RiskScore,  # Phase 1 addition
    RiskLevel,  # Phase 1 addition
)
from .input_guard import InputGuardAgent
from .output_guard import OutputGuardAgent
from .state_monitor import StateMonitorAgent
from .red_team import RedTeamAgent
from .audit import AuditManager

# Phase 2: Shadow Agent Integration
try:
    from .shadow_agents import (
        ShadowInputAgent,
        ShadowStateAgent,
        ShadowOutputAgent,
        ShadowAgentConfig,
    )
    SHADOW_AGENTS_AVAILABLE = True
except ImportError:
    SHADOW_AGENTS_AVAILABLE = False
    print("Warning: Shadow agents not available. Run with Phase 1 rule-based security only.")


# ============================================================================
# SENTINEL GATEWAY
# ============================================================================

class SentinelGateway:
    """
    Main Sentinel Security Control Plane
    Orchestrates all security layers using LangGraph
    """

    def __init__(self, config: SentinelConfig, secret_key: Optional[str] = None):
        """
        Initialize Sentinel Gateway

        Args:
            config: Sentinel configuration
            secret_key: Secret key for audit log signing
        """
        self.config = config

        # Initialize agents
        self.input_guard = InputGuardAgent(
            config.pii_detection,
            config.injection_detection,
            config.content_moderation if config.enable_content_moderation else None,
        )

        self.output_guard = OutputGuardAgent(config.pii_detection)

        self.state_monitor = StateMonitorAgent(
            config.loop_detection,
            model_name="claude-3-5-sonnet",
        )

        self.red_team = RedTeamAgent(config.red_team)

        self.audit_manager = AuditManager(
            compliance_frameworks=config.compliance.frameworks,
            secret_key=secret_key,
        )

        # Phase 2: Initialize shadow agents
        self.shadow_agents_enabled = (
            SHADOW_AGENTS_AVAILABLE and
            config.shadow_agents.enabled
        )

        if self.shadow_agents_enabled:
            shadow_config = ShadowAgentConfig(
                enabled=True,
                llm_provider=config.shadow_agents.llm_provider,
                llm_model=config.shadow_agents.llm_model,
                temperature=config.shadow_agents.temperature,
                max_tokens=config.shadow_agents.max_tokens,
                timeout_ms=config.shadow_agents.timeout_ms,
                fallback_to_rules=config.shadow_agents.fallback_to_rules,
                enable_caching=config.shadow_agents.enable_caching,
                cache_ttl_seconds=config.shadow_agents.cache_ttl_seconds,
                circuit_breaker_enabled=config.shadow_agents.circuit_breaker_enabled,
                failure_threshold=config.shadow_agents.failure_threshold,
                success_threshold=config.shadow_agents.success_threshold,
                timeout_duration_seconds=config.shadow_agents.timeout_duration_seconds,
            )

            self.shadow_input = ShadowInputAgent(shadow_config) if config.shadow_agents.enable_input_agent else None
            self.shadow_state = ShadowStateAgent(shadow_config) if config.shadow_agents.enable_state_agent else None
            self.shadow_output = ShadowOutputAgent(shadow_config) if config.shadow_agents.enable_output_agent else None
        else:
            self.shadow_input = None
            self.shadow_state = None
            self.shadow_output = None

        # Build LangGraph workflow
        if LANGGRAPH_AVAILABLE:
            self.graph = self._build_graph()
        else:
            self.graph = None

    def _build_graph(self) -> "StateGraph":
        """Build LangGraph state machine"""
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph not installed")

        # Create graph
        workflow = StateGraph(SentinelState)

        # Add nodes
        workflow.add_node("input_guard", self._input_guard_node)
        workflow.add_node("agent_execution", self._agent_execution_node)
        workflow.add_node("state_monitor", self._state_monitor_node)
        workflow.add_node("output_guard", self._output_guard_node)
        workflow.add_node("red_team", self._red_team_node)
        workflow.add_node("audit_finalize", self._audit_finalize_node)

        # Set entry point
        workflow.set_entry_point("input_guard")

        # Add conditional edges
        workflow.add_conditional_edges(
            "input_guard",
            self._route_after_input_guard,
            {
                "block": "audit_finalize",
                "continue": "agent_execution",
            },
        )

        workflow.add_edge("agent_execution", "state_monitor")

        workflow.add_conditional_edges(
            "state_monitor",
            self._route_after_state_monitor,
            {
                "block": "audit_finalize",
                "continue": "output_guard",
            },
        )

        workflow.add_edge("output_guard", "red_team")

        workflow.add_edge("red_team", "audit_finalize")

        # Set exit
        workflow.add_edge("audit_finalize", END)

        return workflow.compile()

    # ========================================================================
    # NODE FUNCTIONS
    # ========================================================================

    def _input_guard_node(self, state: SentinelState) -> SentinelState:
        """Input Guard: PII detection and injection checking"""
        if not self.config.enable_input_guard:
            return state

        return self.input_guard.process(state)

    def _agent_execution_node(self, state: SentinelState) -> SentinelState:
        """
        Agent Execution: Call the main LLM agent
        This is a placeholder - will be replaced by actual agent
        """
        # This will be overridden when invoking with agent_executor
        # For now, just add audit event

        event = AuditEvent(
            event_type=EventType.AGENT_EXECUTION,
            data={
                "input_redacted": state["redacted_input"] != state["user_input"],
                "injection_detected": state["injection_detected"],
            },
        )

        state["audit_log"]["events"].append(event.dict())

        # Placeholder response
        if "agent_response" not in state or not state["agent_response"]:
            state["agent_response"] = "[Agent response placeholder]"

        return state

    def _state_monitor_node(self, state: SentinelState) -> SentinelState:
        """State Monitor: Loop detection and cost monitoring"""
        if not self.config.enable_state_monitor:
            return state

        return self.state_monitor.process(state)

    def _output_guard_node(self, state: SentinelState) -> SentinelState:
        """Output Guard: Response sanitization and leak detection"""
        if not self.config.enable_output_guard:
            state["sanitized_response"] = state["agent_response"]
            return state

        return self.output_guard.process(state)

    def _red_team_node(self, state: SentinelState) -> SentinelState:
        """Red Team: Adversarial testing (optional)"""
        if not self.config.red_team.enabled:
            return state

        # In async mode, this would run in background
        # For now, run sync
        return self.red_team.process(state)

    def _audit_finalize_node(self, state: SentinelState) -> SentinelState:
        """Audit Finalize: Complete audit log and sign"""
        return self.audit_manager.finalize_audit_log(state)

    # ========================================================================
    # ROUTING FUNCTIONS
    # ========================================================================

    def _route_after_input_guard(
        self, state: SentinelState
    ) -> Literal["block", "continue"]:
        """Route after input guard based on threats detected"""
        if state["should_block"]:
            return "block"
        return "continue"

    def _route_after_state_monitor(
        self, state: SentinelState
    ) -> Literal["block", "continue"]:
        """Route after state monitor based on loop detection"""
        if state["should_block"]:
            return "block"
        return "continue"

    # ========================================================================
    # SHADOW AGENT NODES (Phase 2)
    # ========================================================================

    def _should_escalate_to_shadow_agents(self, state: SentinelState) -> bool:
        """
        Determine if request should be escalated to shadow agents

        Escalation criteria:
        - Shadow agents are enabled
        - Risk score exceeds configured threshold
        - Not already escalated (avoid double escalation)
        """
        if not self.shadow_agents_enabled:
            return False

        if state.get("shadow_agent_escalated", False):
            return False  # Already escalated

        aggregated_risk = state.get("aggregated_risk")
        if not aggregated_risk:
            return False

        overall_risk = aggregated_risk.get("overall_risk_score", 0.0)
        threshold = self.config.shadow_agents.medium_risk_threshold

        return overall_risk >= threshold

    def _shadow_input_analysis_node(self, state: SentinelState) -> SentinelState:
        """Shadow Input Agent: Deep intent analysis"""
        if not self.shadow_input or not self._should_escalate_to_shadow_agents(state):
            return state

        try:
            # Prepare context for shadow agent
            context = {
                "user_input": state["user_input"],
                "conversation_history": [],  # TODO: Add conversation tracking
                "existing_threats": state["security_threats"],
                "request_context": state["request_context"],
            }

            # Run shadow agent analysis
            response = self.shadow_input.analyze(context)

            # Add to shadow agent analyses
            state["shadow_agent_analyses"].append(response.dict())

            # Update risk if shadow agent found higher risk
            if response.risk_score > state.get("aggregated_risk", {}).get("overall_risk_score", 0.0):
                # Shadow agent detected higher risk
                state["should_warn"] = True
                state["warning_message"] = f"Shadow agent detected: {', '.join(response.threats_detected)}"

                # If critical risk, block
                if response.risk_level == "critical":
                    state["should_block"] = True
                    state["block_reason"] = f"Critical security threat detected by shadow input agent: {response.reasoning}"

            # Mark as escalated
            state["shadow_agent_escalated"] = True
            state["escalation_reason"] = "High risk input detected"

            # Add audit event
            audit_event = AuditEvent(
                event_type=EventType.RISK_ASSESSMENT,
                data=response.to_audit_event(),
            )
            state["audit_log"]["events"].append(audit_event.dict())

        except Exception as e:
            # Shadow agent failed, log but continue with rule-based results
            state["warning_message"] = f"Shadow input agent failed: {str(e)}"
            state["should_warn"] = True

        return state

    def _shadow_state_analysis_node(self, state: SentinelState) -> SentinelState:
        """Shadow State Agent: Behavioral analysis"""
        if not self.shadow_state or not self._should_escalate_to_shadow_agents(state):
            return state

        try:
            # Prepare context for shadow agent
            context = {
                "execution_trace": [],  # TODO: Track execution trace
                "tool_calls": state["tool_calls"],
                "loop_detection": state.get("loop_details", {}),
                "cost_metrics": state["cost_metrics"],
                "user_intent": state["user_input"],
                "expected_behavior": "Normal agent execution",
            }

            # Run shadow agent analysis
            response = self.shadow_state.analyze(context)

            # Add to shadow agent analyses
            state["shadow_agent_analyses"].append(response.dict())

            # Update state based on analysis
            if response.risk_score > 0.8:
                state["should_warn"] = True
                state["warning_message"] = f"Behavioral anomaly: {response.reasoning}"

                if response.risk_level == "critical":
                    state["should_block"] = True
                    state["block_reason"] = f"Critical behavioral anomaly: {response.reasoning}"

            # Add audit event
            audit_event = AuditEvent(
                event_type=EventType.RISK_ASSESSMENT,
                data=response.to_audit_event(),
            )
            state["audit_log"]["events"].append(audit_event.dict())

        except Exception as e:
            state["warning_message"] = f"Shadow state agent failed: {str(e)}"
            state["should_warn"] = True

        return state

    def _shadow_output_analysis_node(self, state: SentinelState) -> SentinelState:
        """Shadow Output Agent: Semantic leak detection"""
        if not self.shadow_output or not self._should_escalate_to_shadow_agents(state):
            return state

        try:
            # Prepare context for shadow agent
            context = {
                "agent_response": state["agent_response"],
                "user_input": state["user_input"],
                "context_info": state["request_context"],
                "existing_threats": [
                    t for t in state["security_threats"]
                    if t.get("layer") == "output_guard"
                ],
            }

            # Run shadow agent analysis
            response = self.shadow_output.analyze(context)

            # Add to shadow agent analyses
            state["shadow_agent_analyses"].append(response.dict())

            # Update state based on analysis
            if response.risk_score > 0.8:
                state["should_warn"] = True
                state["warning_message"] = f"Output security risk: {response.reasoning}"

                # Apply additional sanitization if needed
                if response.risk_level in ["high", "critical"]:
                    # Block output
                    state["sanitized_response"] = "[BLOCKED: Response contains potential security violations]"

            # Add audit event
            audit_event = AuditEvent(
                event_type=EventType.RISK_ASSESSMENT,
                data=response.to_audit_event(),
            )
            state["audit_log"]["events"].append(audit_event.dict())

        except Exception as e:
            state["warning_message"] = f"Shadow output agent failed: {str(e)}"
            state["should_warn"] = True

        return state

    # ========================================================================
    # RISK AGGREGATION (Phase 1)
    # ========================================================================

    def _aggregate_risk_scores(self, state: SentinelState) -> SentinelState:
        """
        Aggregate risk scores from all security layers (Phase 1)

        Combines risk scores using configured weights and determines
        if escalation to shadow agents is needed (Phase 2)
        """
        risk_scores = state["risk_scores"]

        if not risk_scores:
            # No risk scores yet - return state unchanged
            return state

        # Get configuration
        config = self.config.risk_scoring
        context = state.get("request_context", {})

        # 1. Extract scores by layer
        layer_scores = {}
        risk_breakdown = {}

        for risk_dict in risk_scores:
            layer = risk_dict["layer"]
            score = risk_dict["risk_score"]
            layer_scores[layer] = score
            risk_breakdown[layer] = {
                "score": score,
                "level": risk_dict["risk_level"],
                "factors": risk_dict["risk_factors"],
                "explanation": risk_dict["explanation"],
            }

        # 2. Calculate weighted overall risk score
        # Default weights if layers are missing
        input_score = layer_scores.get("input_guard", 0.0)
        state_score = layer_scores.get("state_monitor", 0.0)
        output_score = layer_scores.get("output_guard", 0.0)

        # Weighted combination based on config
        overall_risk = (
            (input_score * config.pii_risk_weight) +
            (input_score * config.injection_risk_weight) +  # Input guard handles both PII and injection
            (state_score * config.loop_risk_weight) +
            (output_score * config.leak_risk_weight)
        )

        # Normalize to 0.0-1.0
        total_weight = (
            config.pii_risk_weight +
            config.injection_risk_weight +
            config.loop_risk_weight +
            config.leak_risk_weight
        )
        overall_risk = overall_risk / total_weight if total_weight > 0 else 0.0

        # 3. Apply context-aware adjustments
        if config.trust_score_modifier and context:
            trust_score = context.get("trust_score", 0.5)
            # Lower trust = higher risk
            trust_multiplier = 1.0 + (1.0 - trust_score) * 0.2  # Up to 20% increase
            overall_risk = min(overall_risk * trust_multiplier, 1.0)

            # Strict mode increases risk
            if context.get("strict_mode", False):
                overall_risk = min(overall_risk * config.strict_mode_multiplier, 1.0)

        # 4. Determine overall risk level
        if overall_risk >= config.critical_risk_threshold:
            risk_level = RiskLevel.CRITICAL
        elif overall_risk >= config.high_risk_threshold:
            risk_level = RiskLevel.HIGH
        elif overall_risk >= config.medium_risk_threshold:
            risk_level = RiskLevel.MEDIUM
        elif overall_risk >= config.low_risk_threshold:
            risk_level = RiskLevel.LOW
        else:
            risk_level = RiskLevel.NONE

        # 5. Determine if shadow agent escalation is needed (Phase 2)
        should_escalate = False
        escalation_reason = None

        if config.enable_shadow_agent_escalation and overall_risk >= config.shadow_agent_threshold:
            should_escalate = True
            escalation_reason = (
                f"Risk score {overall_risk:.2f} exceeds shadow agent threshold "
                f"{config.shadow_agent_threshold:.2f}"
            )

        # 6. Create aggregated risk score
        aggregated_risk = AggregatedRiskScore(
            overall_risk_score=overall_risk,
            overall_risk_level=risk_level,
            layer_scores=layer_scores,
            risk_breakdown=risk_breakdown,
            should_escalate=should_escalate,
            escalation_reason=escalation_reason,
        )

        # 7. Update state
        state["aggregated_risk"] = aggregated_risk.dict()

        if should_escalate and not state["shadow_agent_escalated"]:
            state["shadow_agent_escalated"] = True
            state["escalation_reason"] = escalation_reason

        # 8. Add audit event
        risk_audit = AuditEvent(
            event_type=EventType.RISK_ASSESSMENT,
            data={
                "layer": "aggregated",
                "overall_risk_score": overall_risk,
                "overall_risk_level": risk_level,
                "layer_scores": layer_scores,
                "should_escalate": should_escalate,
                "escalation_reason": escalation_reason,
            },
        )
        state["audit_log"]["events"].append(risk_audit.dict())

        return state

    # ========================================================================
    # INVOKE METHODS
    # ========================================================================

    def invoke(
        self,
        user_input: str,
        agent_executor: Optional[Callable[[str], str]] = None,
    ) -> Dict[str, Any]:
        """
        Invoke Sentinel Gateway with user input

        Args:
            user_input: User's input message
            agent_executor: Optional function to execute the main agent
                           Should take redacted_input and return agent_response

        Returns:
            Dictionary with:
                - response: Final sanitized response
                - blocked: Whether request was blocked
                - threats: List of security threats
                - audit_log: Complete audit log
        """

        # Create initial state
        state = create_initial_state(user_input, self.config)

        if LANGGRAPH_AVAILABLE and self.graph:
            # Use LangGraph workflow
            state = self._invoke_with_langgraph(state, agent_executor)
        else:
            # Fallback: Manual orchestration
            state = self._invoke_manual(state, agent_executor)

        # Return result
        return {
            "response": state["sanitized_response"] if not state["should_block"] else state["block_reason"],
            "blocked": state["should_block"],
            "threats": state["security_threats"],
            "violations": state["compliance_violations"],
            "audit_log": state["audit_log"],
            "cost_metrics": state["cost_metrics"],
            "warnings": state["warning_message"] if state["should_warn"] else None,
            "risk_scores": state.get("risk_scores", []),  # Phase 1 addition
            "aggregated_risk": state.get("aggregated_risk"),  # Phase 1 addition
            "shadow_agent_escalated": state.get("shadow_agent_escalated", False),  # Phase 1/2 addition
            "redacted_input": state.get("redacted_input"),  # PII redaction - entity-specific tokens
            "original_entities": state.get("original_entities", []),  # Original PII entities detected
            "pii_detected": state.get("audit_log", {}).get("pii_redactions", 0) > 0,
        }

    def _invoke_with_langgraph(
        self,
        state: SentinelState,
        agent_executor: Optional[Callable[[str], str]],
    ) -> SentinelState:
        """Invoke using LangGraph workflow"""

        # If agent_executor provided, inject it
        if agent_executor:
            # Override agent execution node
            def agent_execution_with_executor(s: SentinelState) -> SentinelState:
                if s["should_block"]:
                    return s

                # Call agent with redacted input
                try:
                    response = agent_executor(s["redacted_input"])
                    s["agent_response"] = response
                except Exception as e:
                    s["agent_response"] = f"Error executing agent: {str(e)}"
                    s["should_warn"] = True
                    s["warning_message"] = f"Agent execution error: {str(e)}"

                # Log tool calls if agent provides them
                # (This would need to be extended based on your agent framework)

                event = AuditEvent(
                    event_type=EventType.AGENT_EXECUTION,
                    data={
                        "success": "Error" not in s["agent_response"],
                        "response_length": len(s["agent_response"]),
                    },
                )

                s["audit_log"]["events"].append(event.dict())

                return s

            # Update graph node
            # Note: In production, you'd rebuild the graph or use a different approach
            # For now, we'll manually call
            state = self._invoke_manual(state, agent_executor)
        else:
            # Run graph as-is
            state = self.graph.invoke(state)

        return state

    def _invoke_manual(
        self,
        state: SentinelState,
        agent_executor: Optional[Callable[[str], str]],
    ) -> SentinelState:
        """Manual orchestration without LangGraph"""

        # 1. Input Guard
        if self.config.enable_input_guard:
            state = self.input_guard.process(state)

        if state["should_block"]:
            return self.audit_manager.finalize_audit_log(state)

        # 2. Agent Execution
        if agent_executor:
            try:
                response = agent_executor(state["redacted_input"])
                state["agent_response"] = response
            except Exception as e:
                state["agent_response"] = f"Error: {str(e)}"
                state["should_warn"] = True

        # 3. State Monitor
        if self.config.enable_state_monitor:
            state = self.state_monitor.process(state)

        if state["should_block"]:
            return self.audit_manager.finalize_audit_log(state)

        # 4. Output Guard
        if self.config.enable_output_guard:
            state = self.output_guard.process(state)

        # 5. Red Team (optional)
        if self.config.red_team.enabled and not self.config.red_team.async_mode:
            state = self.red_team.process(state, agent_executor)

        # 6. Aggregate Risk Scores (Phase 1)
        if self.config.risk_scoring.enabled:
            state = self._aggregate_risk_scores(state)

        # 7. Shadow Agent Escalation (Phase 2)
        if self.shadow_agents_enabled and self._should_escalate_to_shadow_agents(state):
            # Run shadow input analysis
            if self.shadow_input:
                state = self._shadow_input_analysis_node(state)

            # Check if blocked after shadow input analysis
            if state["should_block"]:
                return self.audit_manager.finalize_audit_log(state)

            # Run shadow state analysis
            if self.shadow_state:
                state = self._shadow_state_analysis_node(state)

            # Check if blocked after shadow state analysis
            if state["should_block"]:
                return self.audit_manager.finalize_audit_log(state)

            # Run shadow output analysis
            if self.shadow_output:
                state = self._shadow_output_analysis_node(state)

        # 8. Audit Finalize
        state = self.audit_manager.finalize_audit_log(state)

        return state

    def generate_report(
        self, state: Dict[str, Any], format: str = "json"
    ) -> str:
        """Generate audit report from state"""
        audit_log = state.get("audit_log")
        if not audit_log:
            raise ValueError("No audit log in state")

        return self.audit_manager.generate_report(state, format)


# ============================================================================
# CONVENIENCE WRAPPER
# ============================================================================

class SentinelMiddleware:
    """
    Convenience middleware wrapper for easy integration
    Can be used as a decorator or context manager
    """

    def __init__(self, config: SentinelConfig, secret_key: Optional[str] = None):
        self.gateway = SentinelGateway(config, secret_key)

    def __call__(self, agent_func: Callable[[str], str]) -> Callable[[str], Dict[str, Any]]:
        """Use as decorator"""

        def wrapped(user_input: str) -> Dict[str, Any]:
            return self.gateway.invoke(user_input, agent_func)

        return wrapped

    def protect(self, user_input: str, agent_func: Callable[[str], str]) -> Dict[str, Any]:
        """Direct protection method"""
        return self.gateway.invoke(user_input, agent_func)


# Export
__all__ = [
    'SentinelGateway',
    'SentinelMiddleware',
]
