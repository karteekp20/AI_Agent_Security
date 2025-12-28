"""
Redis Adapter: Distributed State and Caching
High-performance caching and session state management
"""

from typing import Dict, Any, Optional, List
from datetime import timedelta
import json
from pydantic import BaseModel

try:
    import redis
    from redis.sentinel import Sentinel
    from redis.exceptions import ConnectionError, TimeoutError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


class RedisConfig(BaseModel):
    """Redis configuration"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    max_connections: int = 50

    # Sentinel configuration (for HA)
    use_sentinel: bool = False
    sentinel_hosts: List[tuple] = []  # [(host, port), ...]
    sentinel_master: str = "mymaster"

    # Key prefixes
    key_prefix: str = "sentinel:"
    session_prefix: str = "session:"
    cache_prefix: str = "cache:"
    pattern_prefix: str = "pattern:"

    # TTLs
    default_ttl: int = 3600  # 1 hour
    session_ttl: int = 86400  # 24 hours
    cache_ttl: int = 1800  # 30 minutes


class RedisAdapter:
    """
    Redis adapter for distributed state management

    Features:
    - Session state caching
    - Pattern caching (regex compilation cache)
    - Distributed locking
    - Rate limiting counters
    - High availability via Sentinel
    """

    def __init__(self, config: RedisConfig):
        """
        Initialize Redis adapter

        Args:
            config: Redis configuration
        """
        self.config = config
        self.enabled = REDIS_AVAILABLE

        if not self.enabled:
            print("⚠️  Redis not installed. Caching disabled.")
            print("   Install: pip install redis")
            self.client = None
            return

        try:
            if config.use_sentinel:
                # Use Sentinel for HA
                sentinel = Sentinel(
                    config.sentinel_hosts,
                    socket_timeout=config.socket_timeout,
                )
                self.client = sentinel.master_for(
                    config.sentinel_master,
                    socket_timeout=config.socket_timeout,
                    password=config.password,
                    db=config.db,
                )
            else:
                # Direct connection
                self.client = redis.Redis(
                    host=config.host,
                    port=config.port,
                    db=config.db,
                    password=config.password,
                    socket_timeout=config.socket_timeout,
                    socket_connect_timeout=config.socket_connect_timeout,
                    max_connections=config.max_connections,
                    decode_responses=True,  # Auto-decode bytes to str
                )

            # Test connection
            self.client.ping()
            print(f"✓ Connected to Redis at {config.host}:{config.port}")

        except Exception as e:
            print(f"⚠️  Failed to connect to Redis: {e}")
            self.enabled = False
            self.client = None

    # =========================================================================
    # SESSION STATE MANAGEMENT
    # =========================================================================

    def save_session_state(
        self,
        session_id: str,
        state: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Save session state to Redis

        Args:
            session_id: Session ID
            state: Session state dictionary
            ttl: Time to live in seconds (default: config.session_ttl)

        Returns:
            Success status
        """
        if not self.enabled or self.client is None:
            return False

        try:
            key = self._make_key(self.config.session_prefix, session_id)
            ttl = ttl or self.config.session_ttl

            # Serialize state
            state_json = json.dumps(state, default=str)

            # Save with TTL
            self.client.setex(key, ttl, state_json)
            return True

        except Exception as e:
            print(f"Redis error saving session state: {e}")
            return False

    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session state from Redis

        Args:
            session_id: Session ID

        Returns:
            Session state or None if not found
        """
        if not self.enabled or self.client is None:
            return None

        try:
            key = self._make_key(self.config.session_prefix, session_id)
            state_json = self.client.get(key)

            if state_json:
                return json.loads(state_json)

            return None

        except Exception as e:
            print(f"Redis error getting session state: {e}")
            return None

    def delete_session_state(self, session_id: str) -> bool:
        """Delete session state"""
        if not self.enabled or self.client is None:
            return False

        try:
            key = self._make_key(self.config.session_prefix, session_id)
            self.client.delete(key)
            return True

        except Exception as e:
            print(f"Redis error deleting session state: {e}")
            return False

    # =========================================================================
    # CACHING
    # =========================================================================

    def cache_set(
        self,
        cache_key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set cache value

        Args:
            cache_key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (default: config.cache_ttl)

        Returns:
            Success status
        """
        if not self.enabled or self.client is None:
            return False

        try:
            key = self._make_key(self.config.cache_prefix, cache_key)
            ttl = ttl or self.config.cache_ttl

            # Serialize value
            value_json = json.dumps(value, default=str)

            # Cache with TTL
            self.client.setex(key, ttl, value_json)
            return True

        except Exception as e:
            print(f"Redis error setting cache: {e}")
            return False

    def cache_get(self, cache_key: str) -> Optional[Any]:
        """Get cache value"""
        if not self.enabled or self.client is None:
            return None

        try:
            key = self._make_key(self.config.cache_prefix, cache_key)
            value_json = self.client.get(key)

            if value_json:
                return json.loads(value_json)

            return None

        except Exception as e:
            print(f"Redis error getting cache: {e}")
            return None

    def cache_delete(self, cache_key: str) -> bool:
        """Delete cache value"""
        if not self.enabled or self.client is None:
            return False

        try:
            key = self._make_key(self.config.cache_prefix, cache_key)
            self.client.delete(key)
            return True

        except Exception as e:
            print(f"Redis error deleting cache: {e}")
            return False

    def cache_exists(self, cache_key: str) -> bool:
        """Check if cache key exists"""
        if not self.enabled or self.client is None:
            return False

        try:
            key = self._make_key(self.config.cache_prefix, cache_key)
            return bool(self.client.exists(key))

        except Exception as e:
            print(f"Redis error checking cache existence: {e}")
            return False

    # =========================================================================
    # PATTERN CACHING (for compiled regex patterns)
    # =========================================================================

    def cache_pattern(
        self,
        pattern_id: str,
        pattern_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache compiled pattern data

        Args:
            pattern_id: Pattern ID
            pattern_data: Pattern metadata (not the compiled regex itself)
            ttl: Time to live (default: 1 hour)

        Returns:
            Success status
        """
        if not self.enabled or self.client is None:
            return False

        try:
            key = self._make_key(self.config.pattern_prefix, pattern_id)
            ttl = ttl or 3600  # 1 hour default

            pattern_json = json.dumps(pattern_data, default=str)
            self.client.setex(key, ttl, pattern_json)
            return True

        except Exception as e:
            print(f"Redis error caching pattern: {e}")
            return False

    def get_cached_pattern(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """Get cached pattern data"""
        if not self.enabled or self.client is None:
            return None

        try:
            key = self._make_key(self.config.pattern_prefix, pattern_id)
            pattern_json = self.client.get(key)

            if pattern_json:
                return json.loads(pattern_json)

            return None

        except Exception as e:
            print(f"Redis error getting cached pattern: {e}")
            return None

    # =========================================================================
    # RATE LIMITING
    # =========================================================================

    def increment_rate_limit(
        self,
        identifier: str,  # user_id or ip_address
        window_seconds: int = 60,
        max_requests: int = 100
    ) -> tuple[int, bool]:
        """
        Increment rate limit counter

        Args:
            identifier: User ID or IP address
            window_seconds: Time window in seconds
            max_requests: Maximum requests allowed in window

        Returns:
            (current_count, is_allowed)
        """
        if not self.enabled or self.client is None:
            return (0, True)  # Allow if Redis unavailable

        try:
            key = f"{self.config.key_prefix}ratelimit:{identifier}"

            # Increment counter
            current = self.client.incr(key)

            # Set expiry on first increment
            if current == 1:
                self.client.expire(key, window_seconds)

            # Check if allowed
            is_allowed = current <= max_requests

            return (current, is_allowed)

        except Exception as e:
            print(f"Redis error in rate limiting: {e}")
            return (0, True)  # Allow on error

    def get_rate_limit(self, identifier: str) -> int:
        """Get current rate limit count"""
        if not self.enabled or self.client is None:
            return 0

        try:
            key = f"{self.config.key_prefix}ratelimit:{identifier}"
            count = self.client.get(key)
            return int(count) if count else 0

        except Exception as e:
            print(f"Redis error getting rate limit: {e}")
            return 0

    # =========================================================================
    # DISTRIBUTED LOCKING
    # =========================================================================

    def acquire_lock(
        self,
        lock_name: str,
        timeout: int = 10,
        blocking_timeout: Optional[int] = None
    ) -> bool:
        """
        Acquire distributed lock

        Args:
            lock_name: Lock identifier
            timeout: Lock expiration in seconds
            blocking_timeout: How long to wait for lock (None = don't wait)

        Returns:
            True if lock acquired
        """
        if not self.enabled or self.client is None:
            return True  # Assume success if Redis unavailable

        try:
            key = f"{self.config.key_prefix}lock:{lock_name}"

            if blocking_timeout is None:
                # Non-blocking
                return bool(self.client.set(key, "1", nx=True, ex=timeout))
            else:
                # Blocking with timeout
                import time
                start = time.time()
                while time.time() - start < blocking_timeout:
                    if self.client.set(key, "1", nx=True, ex=timeout):
                        return True
                    time.sleep(0.1)
                return False

        except Exception as e:
            print(f"Redis error acquiring lock: {e}")
            return False

    def release_lock(self, lock_name: str) -> bool:
        """Release distributed lock"""
        if not self.enabled or self.client is None:
            return True

        try:
            key = f"{self.config.key_prefix}lock:{lock_name}"
            self.client.delete(key)
            return True

        except Exception as e:
            print(f"Redis error releasing lock: {e}")
            return False

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def _make_key(self, prefix: str, key: str) -> str:
        """Construct full Redis key"""
        return f"{self.config.key_prefix}{prefix}{key}"

    def ping(self) -> bool:
        """Check Redis connection"""
        if not self.enabled or self.client is None:
            return False

        try:
            return self.client.ping()
        except Exception:
            return False

    def flush_all(self) -> bool:
        """Flush all keys (USE WITH CAUTION!)"""
        if not self.enabled or self.client is None:
            return False

        try:
            self.client.flushdb()
            return True
        except Exception as e:
            print(f"Redis error flushing database: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics"""
        if not self.enabled or self.client is None:
            return {"enabled": False}

        try:
            info = self.client.info()
            return {
                "enabled": True,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "N/A"),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
            }
        except Exception as e:
            return {"enabled": True, "error": str(e)}
