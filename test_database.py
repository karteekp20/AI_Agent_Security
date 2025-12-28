#!/usr/bin/env python3
"""
Database Connection Test Script
Tests PostgreSQL and Redis connectivity and basic operations
"""

import os
import sys
from datetime import datetime, timedelta

def test_postgresql():
    """Test PostgreSQL connection and operations"""
    print("\n" + "="*60)
    print("TESTING POSTGRESQL")
    print("="*60)

    try:
        from sentinel.storage.postgres_adapter import PostgreSQLAdapter, PostgreSQLConfig

        # Get config from environment or use defaults
        config = PostgreSQLConfig(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "sentinel"),
            user=os.getenv("POSTGRES_USER", "sentinel_user"),
            password=os.getenv("POSTGRES_PASSWORD", "sentinel_password"),
        )

        print(f"Connecting to PostgreSQL at {config.host}:{config.port}/{config.database}...")

        # Initialize adapter
        db = PostgreSQLAdapter(config)

        if not db.enabled:
            print("❌ PostgreSQL adapter is disabled")
            return False

        # Test connection
        if db.ping():
            print("✅ PostgreSQL connection successful!")
        else:
            print("❌ PostgreSQL ping failed")
            return False

        # Test saving audit log
        print("\nTesting audit log save...")
        test_log = {
            "timestamp": datetime.utcnow(),
            "session_id": "test_session_123",
            "request_id": "test_request_123",
            "request_context": {
                "user_id": "test_user",
                "user_role": "admin",
                "ip_address": "127.0.0.1"
            },
            "user_input": "Test input for database verification",
            "blocked": False,
            "aggregated_risk": {
                "overall_risk_score": 0.2,
                "overall_risk_level": "low"
            },
            "pii_detected": False,
            "redacted_entities": [],
            "injection_detected": False,
            "injection_details": {},
            "metadata": {"test": True}
        }

        if db.save_audit_log(test_log):
            print("✅ Audit log saved successfully!")
        else:
            print("❌ Failed to save audit log")
            return False

        # Test querying audit logs
        print("\nTesting audit log query...")
        logs = db.get_audit_logs(
            start_time=datetime.utcnow() - timedelta(minutes=5),
            limit=5
        )
        print(f"✅ Retrieved {len(logs)} audit logs")

        if logs:
            print("\nMost recent audit log:")
            recent = logs[0]
            print(f"  Session ID: {recent.get('session_id')}")
            print(f"  User ID: {recent.get('user_id')}")
            print(f"  Timestamp: {recent.get('timestamp')}")
            print(f"  Blocked: {recent.get('blocked')}")

        # Test compliance stats
        print("\nTesting compliance statistics...")
        stats = db.get_compliance_stats(
            datetime.utcnow() - timedelta(days=7),
            datetime.utcnow()
        )

        if stats:
            print("✅ Compliance stats retrieved:")
            print(f"  Total requests: {stats.get('total_requests', 0)}")
            print(f"  Blocked requests: {stats.get('blocked_requests', 0)}")
            print(f"  PII detections: {stats.get('pii_detections', 0)}")
            print(f"  Injection attempts: {stats.get('injection_attempts', 0)}")

        print("\n✅ PostgreSQL: All tests passed!")
        return True

    except ImportError:
        print("❌ psycopg2 not installed. Install: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ PostgreSQL test failed: {e}")
        return False


def test_redis():
    """Test Redis connection and operations"""
    print("\n" + "="*60)
    print("TESTING REDIS")
    print("="*60)

    try:
        from sentinel.storage.redis_adapter import RedisAdapter, RedisConfig

        # Get config from environment or use defaults
        config = RedisConfig(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD") or None,
            db=int(os.getenv("REDIS_DB", "0")),
        )

        print(f"Connecting to Redis at {config.host}:{config.port}...")

        # Initialize adapter
        cache = RedisAdapter(config)

        if not cache.enabled:
            print("❌ Redis adapter is disabled")
            return False

        # Test connection
        if cache.ping():
            print("✅ Redis connection successful!")
        else:
            print("❌ Redis ping failed")
            return False

        # Test session state
        print("\nTesting session state management...")
        test_session_id = "test_session_123"
        test_state = {
            "user_id": "test_user",
            "conversation_turns": 5,
            "total_cost": 0.0023,
            "context": {"last_query": "Test query"}
        }

        if cache.save_session_state(test_session_id, test_state, ttl=60):
            print("✅ Session state saved")
        else:
            print("❌ Failed to save session state")
            return False

        # Retrieve session state
        retrieved = cache.get_session_state(test_session_id)
        if retrieved:
            print("✅ Session state retrieved")
            print(f"  User ID: {retrieved.get('user_id')}")
            print(f"  Turns: {retrieved.get('conversation_turns')}")
        else:
            print("❌ Failed to retrieve session state")
            return False

        # Test caching
        print("\nTesting cache operations...")
        if cache.cache_set("test_key", {"value": "test_data"}, ttl=60):
            print("✅ Cache value set")
        else:
            print("❌ Failed to set cache value")
            return False

        cached_value = cache.cache_get("test_key")
        if cached_value:
            print(f"✅ Cache value retrieved: {cached_value}")
        else:
            print("❌ Failed to retrieve cache value")
            return False

        # Test rate limiting
        print("\nTesting rate limiting...")
        count, is_allowed = cache.increment_rate_limit(
            identifier="test_user",
            window_seconds=60,
            max_requests=100
        )
        print(f"✅ Rate limit check: {count} requests, allowed={is_allowed}")

        # Test distributed locking
        print("\nTesting distributed locking...")
        lock_acquired = cache.acquire_lock("test_lock", timeout=10)
        if lock_acquired:
            print("✅ Lock acquired")
            cache.release_lock("test_lock")
            print("✅ Lock released")
        else:
            print("⚠️  Failed to acquire lock (may already exist)")

        # Get Redis stats
        print("\nRedis statistics:")
        stats = cache.get_stats()
        if stats.get("enabled"):
            print(f"  Connected clients: {stats.get('connected_clients', 'N/A')}")
            print(f"  Memory usage: {stats.get('used_memory_human', 'N/A')}")
            print(f"  Uptime: {stats.get('uptime_in_seconds', 0)} seconds")

        print("\n✅ Redis: All tests passed!")
        return True

    except ImportError:
        print("❌ redis not installed. Install: pip install redis")
        return False
    except Exception as e:
        print(f"❌ Redis test failed: {e}")
        return False


def main():
    """Run all database tests"""
    print("\n" + "="*60)
    print("SENTINEL DATABASE CONNECTION TEST")
    print("="*60)
    print("\nThis script tests connectivity to PostgreSQL and Redis")
    print("Make sure databases are running before executing this test.")

    # Check environment
    print("\nEnvironment Configuration:")
    print(f"  POSTGRES_HOST: {os.getenv('POSTGRES_HOST', 'localhost')}")
    print(f"  POSTGRES_PORT: {os.getenv('POSTGRES_PORT', '5432')}")
    print(f"  POSTGRES_DB: {os.getenv('POSTGRES_DB', 'sentinel')}")
    print(f"  POSTGRES_USER: {os.getenv('POSTGRES_USER', 'sentinel_user')}")
    print(f"  REDIS_HOST: {os.getenv('REDIS_HOST', 'localhost')}")
    print(f"  REDIS_PORT: {os.getenv('REDIS_PORT', '6379')}")

    # Run tests
    pg_success = test_postgresql()
    redis_success = test_redis()

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"PostgreSQL: {'✅ PASSED' if pg_success else '❌ FAILED'}")
    print(f"Redis:      {'✅ PASSED' if redis_success else '❌ FAILED'}")

    if pg_success and redis_success:
        print("\n🎉 All database tests passed!")
        print("\nYour Sentinel instance is ready to store audit logs and session state.")
        print("\nNext steps:")
        print("  1. Start the API server: python -m uvicorn sentinel.api.server:app")
        print("  2. Make requests to: http://localhost:8000/process")
        print("  3. View audit logs in PostgreSQL")
        print("  4. Monitor session state in Redis")
        return 0
    else:
        print("\n⚠️  Some database tests failed.")
        print("\nTroubleshooting:")
        if not pg_success:
            print("  PostgreSQL:")
            print("    - Check if PostgreSQL is running: sudo systemctl status postgresql")
            print("    - Verify credentials in .env file")
            print("    - Install driver: pip install psycopg2-binary")
        if not redis_success:
            print("  Redis:")
            print("    - Check if Redis is running: sudo systemctl status redis")
            print("    - Verify host/port in .env file")
            print("    - Install client: pip install redis")

        print("\nFor Docker setup: docker-compose up -d postgres redis")
        return 1


if __name__ == "__main__":
    sys.exit(main())
