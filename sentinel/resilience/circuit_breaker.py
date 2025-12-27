"""
Circuit Breaker Pattern
Prevents cascading failures by stopping calls to failing services
"""

from enum import Enum
from typing import Callable, Optional, Any
from datetime import datetime, timedelta
from functools import wraps
import time


class CircuitBreakerState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject all calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation

    States:
    - CLOSED: Normal operation. Failures are counted.
    - OPEN: Too many failures. All calls rejected immediately.
    - HALF_OPEN: Testing recovery. Limited calls allowed.

    State transitions:
    - CLOSED → OPEN: After failure_threshold failures in window
    - OPEN → HALF_OPEN: After recovery_timeout seconds
    - HALF_OPEN → CLOSED: After success_threshold successful calls
    - HALF_OPEN → OPEN: If any call fails

    Usage:
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

        @cb.protected
        def call_external_api():
            # ... API call ...

        # Or use as context manager:
        with cb:
            # ... protected code ...
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
        timeout: int = 10,
        expected_exceptions: tuple = (Exception,),
    ):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again (OPEN → HALF_OPEN)
            success_threshold: Successes needed to close circuit (HALF_OPEN → CLOSED)
            timeout: Maximum time (seconds) for protected calls
            expected_exceptions: Exceptions to count as failures
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.expected_exceptions = expected_exceptions

        # State
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._opened_at: Optional[datetime] = None

        # Stats
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._total_rejected = 0

    @property
    def state(self) -> CircuitBreakerState:
        """Get current state (may transition from OPEN to HALF_OPEN)"""
        if self._state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitBreakerState.HALF_OPEN
                self._success_count = 0

        return self._state

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try recovery"""
        if self._opened_at is None:
            return False

        elapsed = (datetime.utcnow() - self._opened_at).total_seconds()
        return elapsed >= self.recovery_timeout

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call a function with circuit breaker protection

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
        """
        self._total_calls += 1

        # Check if we should reject the call
        if self.state == CircuitBreakerState.OPEN:
            self._total_rejected += 1
            raise CircuitBreakerError(
                f"Circuit breaker is OPEN. Service unavailable. "
                f"Will retry after {self.recovery_timeout}s."
            )

        # Try the call
        start_time = time.time()

        try:
            # Call with timeout (if supported)
            result = func(*args, **kwargs)

            # Check if call took too long
            elapsed = time.time() - start_time
            if elapsed > self.timeout:
                raise TimeoutError(f"Call took {elapsed:.2f}s (timeout: {self.timeout}s)")

            # Success!
            self._on_success()
            return result

        except self.expected_exceptions as e:
            # Expected failure
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call"""
        self._total_successes += 1

        if self._state == CircuitBreakerState.HALF_OPEN:
            # Count successes in half-open state
            self._success_count += 1

            if self._success_count >= self.success_threshold:
                # Enough successes → close circuit
                self._reset()

        elif self._state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0

    def _on_failure(self):
        """Handle failed call"""
        self._total_failures += 1
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow()

        if self._state == CircuitBreakerState.HALF_OPEN:
            # Any failure in half-open → open circuit again
            self._open_circuit()

        elif self._state == CircuitBreakerState.CLOSED:
            # Check if threshold exceeded
            if self._failure_count >= self.failure_threshold:
                self._open_circuit()

    def _open_circuit(self):
        """Transition to OPEN state"""
        self._state = CircuitBreakerState.OPEN
        self._opened_at = datetime.utcnow()
        self._failure_count = 0

    def _reset(self):
        """Reset to CLOSED state"""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._opened_at = None

    # =========================================================================
    # DECORATOR AND CONTEXT MANAGER
    # =========================================================================

    def protected(self, func: Callable) -> Callable:
        """
        Decorator to protect a function with circuit breaker

        Usage:
            @circuit_breaker.protected
            def my_function():
                # ... code ...
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)

        return wrapper

    def __enter__(self):
        """Context manager entry"""
        if self.state == CircuitBreakerState.OPEN:
            raise CircuitBreakerError("Circuit breaker is OPEN")

        self._context_start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        elapsed = time.time() - self._context_start

        if elapsed > self.timeout:
            self._on_failure()
            return False

        if exc_type is None:
            # Success
            self._on_success()
        elif issubclass(exc_type, self.expected_exceptions):
            # Expected failure
            self._on_failure()

        # Don't suppress exception
        return False

    # =========================================================================
    # STATS AND MONITORING
    # =========================================================================

    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        return {
            "state": self.state,
            "total_calls": self._total_calls,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "total_rejected": self._total_rejected,
            "failure_rate": (
                self._total_failures / self._total_calls
                if self._total_calls > 0
                else 0.0
            ),
            "current_failure_count": self._failure_count,
            "last_failure_time": (
                self._last_failure_time.isoformat()
                if self._last_failure_time
                else None
            ),
            "opened_at": (
                self._opened_at.isoformat()
                if self._opened_at
                else None
            ),
        }

    def reset_stats(self):
        """Reset statistics (but keep circuit state)"""
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._total_rejected = 0

    def force_open(self):
        """Force circuit to OPEN state (for testing/maintenance)"""
        self._open_circuit()

    def force_closed(self):
        """Force circuit to CLOSED state (for testing/recovery)"""
        self._reset()


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    import random

    # Create circuit breaker
    cb = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=5,
        success_threshold=2,
    )

    # Simulated unreliable service
    def unreliable_service(fail_rate=0.5):
        """Service that fails randomly"""
        if random.random() < fail_rate:
            raise Exception("Service temporarily unavailable")
        return "Success!"

    # Test circuit breaker
    print("Testing Circuit Breaker\n" + "=" * 50)

    for i in range(20):
        try:
            # High failure rate initially
            fail_rate = 0.8 if i < 10 else 0.1

            result = cb.call(unreliable_service, fail_rate=fail_rate)
            print(f"Call {i+1}: ✓ {result} (state: {cb.state})")

        except CircuitBreakerError as e:
            print(f"Call {i+1}: ⊗ Circuit OPEN - rejected")

        except Exception as e:
            print(f"Call {i+1}: ✗ {e} (state: {cb.state})")

        time.sleep(0.5)

    # Print stats
    print("\n" + "=" * 50)
    print("Final Statistics:")
    stats = cb.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
