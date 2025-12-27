"""
Rate Limiter: Token Bucket and Sliding Window
Protect against abuse and DDoS attacks
"""

from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import time


class RateLimitConfig(BaseModel):
    """Rate limit configuration"""
    requests_per_second: int = 10
    requests_per_minute: int = 100
    requests_per_hour: int = 1000
    burst_size: int = 20  # Allow bursts up to this size


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    pass


class TokenBucket:
    """
    Token bucket rate limiter

    Allows bursts while enforcing average rate
    """

    def __init__(self, rate: float, capacity: int):
        """
        Initialize token bucket

        Args:
            rate: Tokens per second
            capacity: Maximum tokens (burst size)
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()
        elapsed = now - self.last_update

        # Add tokens based on time elapsed
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.rate
        )

        self.last_update = now

        # Check if enough tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def get_tokens(self) -> float:
        """Get current token count"""
        now = time.time()
        elapsed = now - self.last_update

        return min(
            self.capacity,
            self.tokens + elapsed * self.rate
        )


class SlidingWindow:
    """
    Sliding window rate limiter

    More accurate than fixed windows, prevents burst at window boundaries
    """

    def __init__(self, limit: int, window_seconds: int):
        """
        Initialize sliding window

        Args:
            limit: Maximum requests in window
            window_seconds: Window size in seconds
        """
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests: list = []  # List of (timestamp, count) tuples

    def is_allowed(self) -> bool:
        """Check if request is allowed"""
        now = time.time()
        cutoff = now - self.window_seconds

        # Remove old requests
        self.requests = [
            (ts, count) for ts, count in self.requests
            if ts > cutoff
        ]

        # Count requests in window
        total = sum(count for ts, count in self.requests)

        if total < self.limit:
            # Allow request
            self.requests.append((now, 1))
            return True

        return False

    def get_count(self) -> int:
        """Get current request count in window"""
        now = time.time()
        cutoff = now - self.window_seconds

        return sum(
            count for ts, count in self.requests
            if ts > cutoff
        )


class RateLimiter:
    """
    Multi-tier rate limiter with per-user and per-IP limits

    Features:
    - Per-second, per-minute, per-hour limits
    - Per-user and per-IP tracking
    - Burst allowance
    - Graceful degradation (warn before block)
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limiter

        Args:
            config: Rate limit configuration
        """
        self.config = config

        # Per-identifier buckets
        self._user_buckets: Dict[str, TokenBucket] = {}
        self._ip_buckets: Dict[str, TokenBucket] = {}

        # Sliding windows for longer periods
        self._user_windows: Dict[str, Dict[str, SlidingWindow]] = {}
        self._ip_windows: Dict[str, Dict[str, SlidingWindow]] = {}

    def check_rate_limit(
        self,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        cost: int = 1,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if request is within rate limits

        Args:
            user_id: User identifier
            ip_address: IP address
            cost: Request cost (default: 1 token)

        Returns:
            (is_allowed: bool, reason: Optional[str])
        """
        # Check user limits
        if user_id:
            allowed, reason = self._check_limits(
                user_id,
                self._user_buckets,
                self._user_windows,
                cost,
            )

            if not allowed:
                return False, f"User rate limit exceeded: {reason}"

        # Check IP limits
        if ip_address:
            allowed, reason = self._check_limits(
                ip_address,
                self._ip_buckets,
                self._ip_windows,
                cost,
            )

            if not allowed:
                return False, f"IP rate limit exceeded: {reason}"

        return True, None

    def _check_limits(
        self,
        identifier: str,
        buckets: Dict[str, TokenBucket],
        windows: Dict[str, Dict[str, SlidingWindow]],
        cost: int,
    ) -> tuple[bool, Optional[str]]:
        """Check limits for a specific identifier"""
        # Get or create token bucket (per-second limit with burst)
        if identifier not in buckets:
            buckets[identifier] = TokenBucket(
                rate=self.config.requests_per_second,
                capacity=self.config.burst_size,
            )

        bucket = buckets[identifier]

        # Check token bucket (handles per-second + burst)
        if not bucket.consume(cost):
            return False, "per-second limit"

        # Get or create sliding windows
        if identifier not in windows:
            windows[identifier] = {
                "minute": SlidingWindow(
                    limit=self.config.requests_per_minute,
                    window_seconds=60,
                ),
                "hour": SlidingWindow(
                    limit=self.config.requests_per_hour,
                    window_seconds=3600,
                ),
            }

        # Check minute window
        if not windows[identifier]["minute"].is_allowed():
            return False, "per-minute limit"

        # Check hour window
        if not windows[identifier]["hour"].is_allowed():
            return False, "per-hour limit"

        return True, None

    def get_limits_info(
        self,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get current rate limit status

        Args:
            user_id: User identifier
            ip_address: IP address

        Returns:
            Rate limit information
        """
        info = {}

        if user_id and user_id in self._user_buckets:
            bucket = self._user_buckets[user_id]
            windows = self._user_windows.get(user_id, {})

            info["user"] = {
                "user_id": user_id,
                "tokens_remaining": int(bucket.get_tokens()),
                "requests_per_minute": (
                    self.config.requests_per_minute - windows["minute"].get_count()
                    if "minute" in windows
                    else self.config.requests_per_minute
                ),
                "requests_per_hour": (
                    self.config.requests_per_hour - windows["hour"].get_count()
                    if "hour" in windows
                    else self.config.requests_per_hour
                ),
            }

        if ip_address and ip_address in self._ip_buckets:
            bucket = self._ip_buckets[ip_address]
            windows = self._ip_windows.get(ip_address, {})

            info["ip"] = {
                "ip_address": ip_address,
                "tokens_remaining": int(bucket.get_tokens()),
                "requests_per_minute": (
                    self.config.requests_per_minute - windows["minute"].get_count()
                    if "minute" in windows
                    else self.config.requests_per_minute
                ),
                "requests_per_hour": (
                    self.config.requests_per_hour - windows["hour"].get_count()
                    if "hour" in windows
                    else self.config.requests_per_hour
                ),
            }

        return info

    def reset_limits(self, user_id: Optional[str] = None, ip_address: Optional[str] = None):
        """Reset rate limits for user or IP"""
        if user_id:
            self._user_buckets.pop(user_id, None)
            self._user_windows.pop(user_id, None)

        if ip_address:
            self._ip_buckets.pop(ip_address, None)
            self._ip_windows.pop(ip_address, None)


# Create retry decorator
from .retry import retry_with_backoff, RetryConfig

__all__ = [
    'RateLimiter',
    'RateLimitConfig',
    'RateLimitExceeded',
    'retry_with_backoff',
    'RetryConfig',
]
