"""
Base Shadow Agent: Foundation for all LLM-powered security agents
"""

from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
import json


class ShadowAgentConfig(BaseModel):
    """Configuration for shadow agents"""
    enabled: bool = True
    llm_provider: Literal["anthropic", "openai", "local"] = "anthropic"
    llm_model: str = "claude-3-5-haiku-20241022"  # Fast, cost-effective model
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)  # Low temp for consistency
    max_tokens: int = 1024
    timeout_ms: int = 5000  # 5 second timeout
    fallback_to_rules: bool = True  # Fall back to rule-based if LLM fails
    enable_caching: bool = True  # Cache LLM responses
    cache_ttl_seconds: int = 3600  # 1 hour cache

    # Circuit breaker settings
    circuit_breaker_enabled: bool = True
    failure_threshold: int = 5  # Open circuit after 5 failures
    success_threshold: int = 3  # Close circuit after 3 successes
    timeout_duration_seconds: int = 60  # Circuit open for 60 seconds


class ShadowAgentResponse(BaseModel):
    """Response from shadow agent analysis"""
    agent_type: str  # "input", "state", "output"
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: str  # "none", "low", "medium", "high", "critical"
    confidence: float = Field(ge=0.0, le=1.0)

    # Analysis results
    threats_detected: List[str] = Field(default_factory=list)
    reasoning: str = ""
    recommendations: List[str] = Field(default_factory=list)

    # Metadata
    llm_provider: str = ""
    llm_model: str = ""
    tokens_used: int = 0
    latency_ms: float = 0.0
    fallback_used: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def to_audit_event(self) -> Dict[str, Any]:
        """Convert to audit event format"""
        return {
            "event_type": "shadow_agent_analysis",
            "agent_type": self.agent_type,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "threats_detected": self.threats_detected,
            "reasoning": self.reasoning,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
            "fallback_used": self.fallback_used,
            "timestamp": self.timestamp.isoformat(),
        }


class CircuitBreaker:
    """Circuit breaker for shadow agent fault tolerance"""

    def __init__(self, config: ShadowAgentConfig):
        self.config = config
        self.failure_count = 0
        self.success_count = 0
        self.state: Literal["closed", "open", "half_open"] = "closed"
        self.opened_at: Optional[datetime] = None

    def is_open(self) -> bool:
        """Check if circuit is open"""
        if not self.config.circuit_breaker_enabled:
            return False

        if self.state == "closed":
            return False

        if self.state == "open":
            # Check if timeout has elapsed
            if self.opened_at:
                elapsed = (datetime.utcnow() - self.opened_at).total_seconds()
                if elapsed >= self.config.timeout_duration_seconds:
                    self.state = "half_open"
                    return False
            return True

        return False  # half_open allows requests through

    def record_success(self):
        """Record successful call"""
        if self.state == "half_open":
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = "closed"
                self.failure_count = 0
                self.success_count = 0
        elif self.state == "closed":
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record failed call"""
        if self.state == "half_open":
            self.state = "open"
            self.opened_at = datetime.utcnow()
            self.success_count = 0
        elif self.state == "closed":
            self.failure_count += 1
            if self.failure_count >= self.config.failure_threshold:
                self.state = "open"
                self.opened_at = datetime.utcnow()


class ShadowAgentBase(ABC):
    """
    Base class for all shadow agents

    Shadow agents use LLMs to provide intelligent security analysis
    beyond rule-based pattern matching. They are invoked only for
    high-risk requests to minimize cost and latency.
    """

    def __init__(self, config: ShadowAgentConfig, agent_type: str):
        self.config = config
        self.agent_type = agent_type
        self.circuit_breaker = CircuitBreaker(config)
        self._llm_client = None  # Lazy-loaded
        self._cache: Dict[str, ShadowAgentResponse] = {}

    @property
    def llm_client(self):
        """Lazy-load LLM client"""
        if self._llm_client is None and self.config.enabled:
            self._llm_client = self._initialize_llm_client()
        return self._llm_client

    def _initialize_llm_client(self):
        """Initialize LLM client based on provider"""
        if self.config.llm_provider == "anthropic":
            try:
                from anthropic import Anthropic
                import os
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY not set")
                return Anthropic(api_key=api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Install with: pip install anthropic")

        elif self.config.llm_provider == "openai":
            try:
                from openai import OpenAI
                import os
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not set")
                return OpenAI(api_key=api_key)
            except ImportError:
                raise ImportError("openai package not installed. Install with: pip install openai")

        elif self.config.llm_provider == "local":
            # For local models (e.g., via Ollama, LM Studio)
            try:
                from openai import OpenAI
                return OpenAI(base_url="http://localhost:11434/v1", api_key="local")
            except ImportError:
                raise ImportError("openai package required for local models")

        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.llm_provider}")

    def _get_cache_key(self, context: Dict[str, Any]) -> str:
        """Generate cache key from context"""
        # Use relevant fields for caching (avoid timestamp, session_id, etc.)
        cache_data = {
            "agent_type": self.agent_type,
            "input": context.get("input", ""),
            "threats": str(context.get("threats", [])),
        }
        return json.dumps(cache_data, sort_keys=True)

    def _check_cache(self, context: Dict[str, Any]) -> Optional[ShadowAgentResponse]:
        """Check if response is cached"""
        if not self.config.enable_caching:
            return None

        cache_key = self._get_cache_key(context)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            # Check if cache is still valid
            age = (datetime.utcnow() - cached.timestamp).total_seconds()
            if age < self.config.cache_ttl_seconds:
                return cached
            else:
                del self._cache[cache_key]

        return None

    def _store_cache(self, context: Dict[str, Any], response: ShadowAgentResponse):
        """Store response in cache"""
        if self.config.enable_caching:
            cache_key = self._get_cache_key(context)
            self._cache[cache_key] = response

    @abstractmethod
    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """Build LLM prompt for analysis (implemented by subclasses)"""
        pass

    @abstractmethod
    def _fallback_analysis(self, context: Dict[str, Any]) -> ShadowAgentResponse:
        """Fallback rule-based analysis if LLM fails (implemented by subclasses)"""
        pass

    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """Call LLM with prompt and parse JSON response"""
        start_time = datetime.utcnow()

        try:
            if self.config.llm_provider == "anthropic":
                response = self.llm_client.messages.create(
                    model=self.config.llm_model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    messages=[{"role": "user", "content": prompt}],
                )
                content = response.content[0].text
                tokens_used = response.usage.input_tokens + response.usage.output_tokens

            elif self.config.llm_provider in ["openai", "local"]:
                response = self.llm_client.chat.completions.create(
                    model=self.config.llm_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                content = response.choices[0].message.content
                tokens_used = response.usage.total_tokens

            else:
                raise ValueError(f"Unsupported provider: {self.config.llm_provider}")

            # Parse JSON response
            # Extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)

            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            return {
                "result": result,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
            }

        except Exception as e:
            raise Exception(f"LLM call failed: {str(e)}")

    def analyze(self, context: Dict[str, Any]) -> ShadowAgentResponse:
        """
        Main analysis method

        Args:
            context: Analysis context (varies by agent type)

        Returns:
            ShadowAgentResponse with risk assessment
        """
        # Check cache first
        cached = self._check_cache(context)
        if cached:
            return cached

        # Check circuit breaker
        if self.circuit_breaker.is_open():
            if self.config.fallback_to_rules:
                return self._fallback_analysis(context)
            else:
                raise Exception("Shadow agent circuit breaker is open")

        # Try LLM analysis
        try:
            prompt = self._build_prompt(context)
            llm_response = self._call_llm(prompt)

            result = llm_response["result"]

            response = ShadowAgentResponse(
                agent_type=self.agent_type,
                risk_score=result.get("risk_score", 0.0),
                risk_level=result.get("risk_level", "none"),
                confidence=result.get("confidence", 0.0),
                threats_detected=result.get("threats_detected", []),
                reasoning=result.get("reasoning", ""),
                recommendations=result.get("recommendations", []),
                llm_provider=self.config.llm_provider,
                llm_model=self.config.llm_model,
                tokens_used=llm_response["tokens_used"],
                latency_ms=llm_response["latency_ms"],
                fallback_used=False,
            )

            self.circuit_breaker.record_success()
            self._store_cache(context, response)

            return response

        except Exception as e:
            self.circuit_breaker.record_failure()

            if self.config.fallback_to_rules:
                fallback = self._fallback_analysis(context)
                fallback.fallback_used = True
                return fallback
            else:
                raise Exception(f"Shadow agent analysis failed: {str(e)}")
