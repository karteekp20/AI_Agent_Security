"""
Integration Tests for Storage Components (Redis + PostgreSQL)
Tests data persistence, caching, and audit logging
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
import redis as redis_lib
import psycopg2

from sentinel.storage.redis_adapter import RedisAdapter, RedisConfig
from sentinel.storage.postgres_adapter import PostgreSQLAdapter, PostgreSQLConfig


# ============================================================================
# REDIS INTEGRATION TESTS
# ============================================================================

class TestRedisIntegration:
    """Test Redis adapter with mock Redis"""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client"""
        mock = MagicMock()
        mock.ping.return_value = True
        mock.info.return_value = {
            "connected_clients": 5,
            "used_memory_human": "1.5M",
            "total_commands_processed": 1000,
        }
        return mock

    @pytest.fixture
    def redis_adapter(self, mock_redis):
        """Create Redis adapter with mock"""
        config = RedisConfig(
            host="localhost",
            port=6379,
            db=0,
        )
        adapter = RedisAdapter(config)
        adapter.client = mock_redis
        adapter.enabled = True
        return adapter

    def test_ping(self, redis_adapter, mock_redis):
        """Test Redis ping"""
        assert redis_adapter.ping() is True
        mock_redis.ping.assert_called_once()

    def test_save_and_get_session_state(self, redis_adapter, mock_redis):
        """Test saving and retrieving session state"""
        session_id = "session_123"
        state = {
            "user_id": "user_001",
            "risk_score": 0.75,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Mock setex
        mock_redis.setex.return_value = True
        result = redis_adapter.save_session_state(session_id, state, ttl=3600)
        assert result is True
        mock_redis.setex.assert_called_once()

        # Mock get
        import json
        mock_redis.get.return_value = json.dumps(state)
        retrieved = redis_adapter.get_session_state(session_id)
        assert retrieved == state

    def test_cache_pattern(self, redis_adapter, mock_redis):
        """Test pattern caching"""
        pattern_id = "pattern_001"
        pattern_data = {
            "pattern_type": "injection",
            "regex": "ignore.*instructions",
            "confidence": 0.95,
        }

        # Cache pattern
        import json
        mock_redis.setex.return_value = True
        result = redis_adapter.cache_pattern(pattern_id, pattern_data)
        assert result is True

        # Get cached pattern
        mock_redis.get.return_value = json.dumps(pattern_data)
        cached = redis_adapter.get_cached_pattern(pattern_id)
        assert cached == pattern_data

    def test_increment_rate_limit(self, redis_adapter, mock_redis):
        """Test rate limit increment"""
        key = "rate:user_001:second"

        mock_redis.incr.return_value = 5
        mock_redis.ttl.return_value = -1

        count = redis_adapter.increment_rate_limit(key, window=1)
        assert count == 5
        mock_redis.incr.assert_called_once_with(key)

    def test_get_stats(self, redis_adapter, mock_redis):
        """Test getting Redis stats"""
        stats = redis_adapter.get_stats()
        assert stats["enabled"] is True
        assert "connected_clients" in stats
        assert stats["connected_clients"] == 5

    def test_connection_failure_handling(self):
        """Test graceful handling when Redis unavailable"""
        config = RedisConfig(
            host="invalid_host",
            port=9999,
        )
        adapter = RedisAdapter(config)

        # Should be disabled due to connection failure
        assert adapter.enabled is False

        # Operations should fail gracefully
        assert adapter.ping() is False
        assert adapter.save_session_state("test", {}) is False


# ============================================================================
# POSTGRESQL INTEGRATION TESTS
# ============================================================================

class TestPostgreSQLIntegration:
    """Test PostgreSQL adapter with mock connection"""

    @pytest.fixture
    def mock_connection(self):
        """Create mock PostgreSQL connection"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (True,)
        mock_cursor.fetchall.return_value = []
        return mock_conn, mock_cursor

    @pytest.fixture
    def postgres_adapter(self, mock_connection):
        """Create PostgreSQL adapter with mock"""
        config = PostgreSQLConfig(
            host="localhost",
            port=5432,
            database="sentinel_test",
            user="test_user",
            password="test_password",
        )
        adapter = PostgreSQLAdapter(config)
        mock_conn, _ = mock_connection
        adapter.connection = mock_conn
        adapter.enabled = True
        return adapter

    def test_ping(self, postgres_adapter, mock_connection):
        """Test PostgreSQL ping"""
        assert postgres_adapter.ping() is True

    def test_save_audit_log(self, postgres_adapter, mock_connection):
        """Test saving audit log"""
        mock_conn, mock_cursor = mock_connection

        audit_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": "session_123",
            "request_id": "req_456",
            "user_input": "Test input",
            "blocked": False,
            "risk_score": 0.25,
            "pii_detected": False,
            "injection_detected": False,
            "metadata": {"tenant_id": "tenant_001"},
        }

        result = postgres_adapter.save_audit_log(audit_log)
        assert result is True

        # Verify SQL was executed
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()

    def test_get_audit_logs(self, postgres_adapter, mock_connection):
        """Test retrieving audit logs"""
        mock_conn, mock_cursor = mock_connection

        # Mock return data
        mock_cursor.fetchall.return_value = [
            (
                1,
                datetime.utcnow(),
                "session_123",
                "req_456",
                {},
                "Test input",
                False,
                {},
                False,
                [],
                False,
                {},
                False,
                None,
                {},
            )
        ]

        logs = postgres_adapter.get_audit_logs(limit=10)
        assert isinstance(logs, list)
        mock_cursor.execute.assert_called()

    def test_query_blocked_requests(self, postgres_adapter, mock_connection):
        """Test querying blocked requests"""
        mock_conn, mock_cursor = mock_connection
        mock_cursor.fetchall.return_value = []

        start_time = datetime.utcnow() - timedelta(hours=24)
        end_time = datetime.utcnow()

        blocked = postgres_adapter.query_blocked_requests(start_time, end_time)
        assert isinstance(blocked, list)
        mock_cursor.execute.assert_called()

    def test_query_pii_detections(self, postgres_adapter, mock_connection):
        """Test querying PII detections"""
        mock_conn, mock_cursor = mock_connection
        mock_cursor.fetchall.return_value = []

        start_time = datetime.utcnow() - timedelta(hours=24)
        end_time = datetime.utcnow()

        pii = postgres_adapter.query_pii_detections(start_time, end_time)
        assert isinstance(pii, list)

    def test_save_pattern_version(self, postgres_adapter, mock_connection):
        """Test saving pattern version"""
        mock_conn, mock_cursor = mock_connection

        pattern_version = {
            "version": "1.2.0",
            "patterns": [
                {"type": "injection", "regex": "test.*pattern"}
            ],
            "deployed_at": datetime.utcnow().isoformat(),
            "deployed_by": "admin",
        }

        result = postgres_adapter.save_pattern_version(pattern_version)
        assert result is True
        mock_cursor.execute.assert_called()

    def test_connection_failure_handling(self):
        """Test graceful handling when PostgreSQL unavailable"""
        config = PostgreSQLConfig(
            host="invalid_host",
            port=9999,
            database="invalid",
            user="invalid",
            password="invalid",
        )
        adapter = PostgreSQLAdapter(config)

        # Should be disabled due to connection failure
        assert adapter.enabled is False

        # Operations should fail gracefully
        assert adapter.ping() is False
        assert adapter.save_audit_log({}) is False


# ============================================================================
# INTEGRATION TESTS (Real Storage if Available)
# ============================================================================

@pytest.mark.integration
class TestRealStorageIntegration:
    """
    Integration tests with real Redis/PostgreSQL
    Only runs if services are available
    Marked with @pytest.mark.integration - run with: pytest -m integration
    """

    @pytest.fixture
    def real_redis_adapter(self):
        """Create adapter with real Redis (if available)"""
        config = RedisConfig(
            host="localhost",
            port=6379,
            db=15,  # Use separate DB for testing
        )
        adapter = RedisAdapter(config)
        if not adapter.enabled:
            pytest.skip("Redis not available")

        yield adapter

        # Cleanup
        try:
            adapter.client.flushdb()
        except:
            pass

    @pytest.fixture
    def real_postgres_adapter(self):
        """Create adapter with real PostgreSQL (if available)"""
        config = PostgreSQLConfig(
            host="localhost",
            port=5432,
            database="sentinel_test",
            user="sentinel_user",
            password="sentinel_password",
        )
        adapter = PostgreSQLAdapter(config)
        if not adapter.enabled:
            pytest.skip("PostgreSQL not available")

        yield adapter

        # Cleanup
        try:
            if adapter.connection:
                cursor = adapter.connection.cursor()
                cursor.execute(f"TRUNCATE TABLE {adapter.config.schema}.{adapter.config.audit_table}")
                adapter.connection.commit()
        except:
            pass

    def test_redis_roundtrip(self, real_redis_adapter):
        """Test complete Redis save/retrieve cycle"""
        session_id = f"test_session_{int(time.time())}"
        state = {
            "user_id": "test_user",
            "risk_score": 0.85,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Save
        assert real_redis_adapter.save_session_state(session_id, state, ttl=60)

        # Retrieve
        retrieved = real_redis_adapter.get_session_state(session_id)
        assert retrieved is not None
        assert retrieved["user_id"] == state["user_id"]
        assert retrieved["risk_score"] == state["risk_score"]

        # Delete
        real_redis_adapter.delete_session_state(session_id)
        assert real_redis_adapter.get_session_state(session_id) is None

    def test_redis_pattern_cache(self, real_redis_adapter):
        """Test pattern caching"""
        pattern_id = f"test_pattern_{int(time.time())}"
        pattern_data = {
            "regex": "test.*pattern",
            "confidence": 0.95,
        }

        # Cache
        assert real_redis_adapter.cache_pattern(pattern_id, pattern_data, ttl=60)

        # Retrieve
        cached = real_redis_adapter.get_cached_pattern(pattern_id)
        assert cached is not None
        assert cached["regex"] == pattern_data["regex"]

    def test_postgres_audit_log_roundtrip(self, real_postgres_adapter):
        """Test complete PostgreSQL audit log cycle"""
        audit_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": f"session_{int(time.time())}",
            "request_id": f"req_{int(time.time())}",
            "request_context": {"ip": "192.168.1.1"},
            "user_input": "Test audit log",
            "blocked": True,
            "aggregated_risk": {"overall_risk_score": 0.95},
            "pii_detected": False,
            "redacted_entities": [],
            "injection_detected": True,
            "injection_details": {"type": "prompt_injection"},
            "escalated": False,
            "escalated_to": None,
            "metadata": {"test": True},
        }

        # Save
        assert real_postgres_adapter.save_audit_log(audit_log)

        # Query recent logs
        logs = real_postgres_adapter.get_audit_logs(limit=10)
        assert len(logs) > 0

        # Find our log
        found = False
        for log in logs:
            if log.get("session_id") == audit_log["session_id"]:
                found = True
                assert log["blocked"] is True
                assert log["injection_detected"] is True
                break

        assert found, "Saved audit log not found in query results"

    def test_postgres_query_blocked_requests(self, real_postgres_adapter):
        """Test querying blocked requests"""
        # Save a blocked request
        audit_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": f"blocked_session_{int(time.time())}",
            "user_input": "Malicious input",
            "blocked": True,
            "aggregated_risk": {"overall_risk_score": 0.99},
        }
        real_postgres_adapter.save_audit_log(audit_log)

        # Query blocked requests
        start_time = datetime.utcnow() - timedelta(minutes=5)
        end_time = datetime.utcnow() + timedelta(minutes=1)

        blocked = real_postgres_adapter.query_blocked_requests(start_time, end_time)
        assert len(blocked) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
