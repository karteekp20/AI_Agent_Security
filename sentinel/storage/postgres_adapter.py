"""
PostgreSQL Adapter: Audit Log Persistence
Long-term storage and querying of security audit logs
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel
import json

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, execute_values
    from psycopg2.pool import ThreadedConnectionPool
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    psycopg2 = None


class PostgreSQLConfig(BaseModel):
    """PostgreSQL configuration"""
    host: str = "localhost"
    port: int = 5432
    database: str = "sentinel"
    user: str = "sentinel_user"
    password: str = "sentinel_password"

    # Connection pool
    min_connections: int = 2
    max_connections: int = 20

    # Schema
    schema: str = "public"
    audit_table: str = "audit_logs"
    patterns_table: str = "discovered_patterns"
    deployments_table: str = "deployments"


class PostgreSQLAdapter:
    """
    PostgreSQL adapter for audit log persistence

    Features:
    - Persistent audit log storage
    - Pattern discovery history
    - Deployment tracking
    - Compliance reporting queries
    - Connection pooling for performance
    """

    def __init__(self, config: PostgreSQLConfig):
        """
        Initialize PostgreSQL adapter

        Args:
            config: PostgreSQL configuration
        """
        self.config = config
        self.enabled = POSTGRESQL_AVAILABLE

        if not self.enabled:
            print("⚠️  psycopg2 not installed. PostgreSQL disabled.")
            print("   Install: pip install psycopg2-binary")
            self.pool = None
            return

        try:
            # Create connection pool
            self.pool = ThreadedConnectionPool(
                config.min_connections,
                config.max_connections,
                host=config.host,
                port=config.port,
                database=config.database,
                user=config.user,
                password=config.password,
            )

            # Test connection
            conn = self.pool.getconn()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                print(f"✓ Connected to PostgreSQL: {version[:50]}...")
                cursor.close()
            finally:
                self.pool.putconn(conn)

            # Create tables if they don't exist
            self._create_tables()

        except Exception as e:
            print(f"⚠️  Failed to connect to PostgreSQL: {e}")
            self.enabled = False
            self.pool = None

    # =========================================================================
    # TABLE CREATION
    # =========================================================================

    def _create_tables(self):
        """Create tables if they don't exist"""
        if not self.enabled or self.pool is None:
            return

        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()

            # Audit logs table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.config.schema}.{self.config.audit_table} (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    session_id VARCHAR(255) NOT NULL,
                    request_id VARCHAR(255),
                    user_id VARCHAR(255),
                    user_role VARCHAR(100),
                    ip_address VARCHAR(45),

                    -- Input
                    user_input TEXT,
                    input_length INTEGER,

                    -- Processing
                    blocked BOOLEAN DEFAULT FALSE,
                    risk_score FLOAT,
                    risk_level VARCHAR(50),

                    -- PII Detection
                    pii_detected BOOLEAN DEFAULT FALSE,
                    pii_entities JSONB,
                    redacted_count INTEGER DEFAULT 0,

                    -- Injection Detection
                    injection_detected BOOLEAN DEFAULT FALSE,
                    injection_type VARCHAR(100),
                    injection_confidence FLOAT,

                    -- Escalation
                    escalated BOOLEAN DEFAULT FALSE,
                    escalated_to VARCHAR(100),

                    -- Metadata
                    metadata JSONB,

                    -- Indexing
                    CONSTRAINT audit_logs_pkey PRIMARY KEY (id)
                );

                CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                    ON {self.config.schema}.{self.config.audit_table}(timestamp);
                CREATE INDEX IF NOT EXISTS idx_audit_session
                    ON {self.config.schema}.{self.config.audit_table}(session_id);
                CREATE INDEX IF NOT EXISTS idx_audit_blocked
                    ON {self.config.schema}.{self.config.audit_table}(blocked);
                CREATE INDEX IF NOT EXISTS idx_audit_user_id
                    ON {self.config.schema}.{self.config.audit_table}(user_id);
            """)

            # Discovered patterns table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.config.schema}.{self.config.patterns_table} (
                    pattern_id VARCHAR(255) PRIMARY KEY,
                    pattern_type VARCHAR(100) NOT NULL,
                    pattern_value TEXT NOT NULL,

                    discovered_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    discovery_method VARCHAR(100),
                    confidence FLOAT,

                    occurrence_count INTEGER DEFAULT 0,
                    example_inputs JSONB,

                    status VARCHAR(50) DEFAULT 'discovered',
                    reviewed_by VARCHAR(255),
                    reviewed_at TIMESTAMP WITH TIME ZONE,

                    deployed_at TIMESTAMP WITH TIME ZONE,
                    deployment_version VARCHAR(50)
                );

                CREATE INDEX IF NOT EXISTS idx_patterns_type
                    ON {self.config.schema}.{self.config.patterns_table}(pattern_type);
                CREATE INDEX IF NOT EXISTS idx_patterns_status
                    ON {self.config.schema}.{self.config.patterns_table}(status);
            """)

            # Deployments table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.config.schema}.{self.config.deployments_table} (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(50) NOT NULL,
                    deployed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    deployed_by VARCHAR(255),

                    deployment_type VARCHAR(50),  -- canary, stable, rollback
                    deployment_percentage INTEGER,

                    patterns_added INTEGER DEFAULT 0,
                    patterns_removed INTEGER DEFAULT 0,

                    status VARCHAR(50) DEFAULT 'active',  -- active, deprecated

                    -- Performance metrics
                    detection_rate FLOAT,
                    false_positive_rate FLOAT,
                    average_latency_ms FLOAT,

                    changelog TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_deployments_version
                    ON {self.config.schema}.{self.config.deployments_table}(version);
            """)

            conn.commit()
            cursor.close()

        except Exception as e:
            print(f"Error creating tables: {e}")
            conn.rollback()
        finally:
            self.pool.putconn(conn)

    # =========================================================================
    # AUDIT LOG OPERATIONS
    # =========================================================================

    def save_audit_log(self, audit_log: Dict[str, Any]) -> bool:
        """
        Save audit log to PostgreSQL

        Args:
            audit_log: Audit log dictionary

        Returns:
            Success status
        """
        if not self.enabled or self.pool is None:
            return False

        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()

            # Extract fields
            cursor.execute(f"""
                INSERT INTO {self.config.schema}.{self.config.audit_table} (
                    timestamp, session_id, request_id, user_id, user_role, ip_address,
                    user_input, input_length,
                    blocked, risk_score, risk_level,
                    pii_detected, pii_entities, redacted_count,
                    injection_detected, injection_type, injection_confidence,
                    escalated, escalated_to,
                    metadata
                ) VALUES (
                    %(timestamp)s, %(session_id)s, %(request_id)s, %(user_id)s, %(user_role)s, %(ip_address)s,
                    %(user_input)s, %(input_length)s,
                    %(blocked)s, %(risk_score)s, %(risk_level)s,
                    %(pii_detected)s, %(pii_entities)s, %(redacted_count)s,
                    %(injection_detected)s, %(injection_type)s, %(injection_confidence)s,
                    %(escalated)s, %(escalated_to)s,
                    %(metadata)s
                )
            """, {
                "timestamp": audit_log.get("timestamp", datetime.utcnow()),
                "session_id": audit_log.get("session_id"),
                "request_id": audit_log.get("request_id"),
                "user_id": audit_log.get("request_context", {}).get("user_id"),
                "user_role": audit_log.get("request_context", {}).get("user_role"),
                "ip_address": audit_log.get("request_context", {}).get("ip_address"),
                "user_input": audit_log.get("user_input"),
                "input_length": len(audit_log.get("user_input", "")),
                "blocked": audit_log.get("blocked", False),
                "risk_score": audit_log.get("aggregated_risk", {}).get("overall_risk_score"),
                "risk_level": audit_log.get("aggregated_risk", {}).get("overall_risk_level"),
                "pii_detected": audit_log.get("pii_detected", False),
                "pii_entities": json.dumps(audit_log.get("redacted_entities", [])),
                "redacted_count": len(audit_log.get("redacted_entities", [])),
                "injection_detected": audit_log.get("injection_detected", False),
                "injection_type": audit_log.get("injection_details", {}).get("injection_type"),
                "injection_confidence": audit_log.get("injection_details", {}).get("confidence"),
                "escalated": audit_log.get("escalated", False),
                "escalated_to": audit_log.get("escalated_to"),
                "metadata": json.dumps(audit_log.get("metadata", {})),
            })

            conn.commit()
            cursor.close()
            return True

        except Exception as e:
            print(f"Error saving audit log: {e}")
            conn.rollback()
            return False
        finally:
            self.pool.putconn(conn)

    def get_audit_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        blocked_only: bool = False,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Query audit logs

        Args:
            start_time: Start of time range
            end_time: End of time range
            session_id: Filter by session ID
            user_id: Filter by user ID
            blocked_only: Only return blocked requests
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of audit log dictionaries
        """
        if not self.enabled or self.pool is None:
            return []

        conn = self.pool.getconn()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Build query
            query = f"SELECT * FROM {self.config.schema}.{self.config.audit_table} WHERE 1=1"
            params = {}

            if start_time:
                query += " AND timestamp >= %(start_time)s"
                params["start_time"] = start_time

            if end_time:
                query += " AND timestamp <= %(end_time)s"
                params["end_time"] = end_time

            if session_id:
                query += " AND session_id = %(session_id)s"
                params["session_id"] = session_id

            if user_id:
                query += " AND user_id = %(user_id)s"
                params["user_id"] = user_id

            if blocked_only:
                query += " AND blocked = TRUE"

            query += " ORDER BY timestamp DESC LIMIT %(limit)s OFFSET %(offset)s"
            params["limit"] = limit
            params["offset"] = offset

            cursor.execute(query, params)
            results = cursor.fetchall()

            cursor.close()
            return [dict(row) for row in results]

        except Exception as e:
            print(f"Error querying audit logs: {e}")
            return []
        finally:
            self.pool.putconn(conn)

    # =========================================================================
    # PATTERN OPERATIONS
    # =========================================================================

    def save_discovered_pattern(self, pattern: Dict[str, Any]) -> bool:
        """Save discovered pattern"""
        if not self.enabled or self.pool is None:
            return False

        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()

            cursor.execute(f"""
                INSERT INTO {self.config.schema}.{self.config.patterns_table} (
                    pattern_id, pattern_type, pattern_value,
                    discovered_at, discovery_method, confidence,
                    occurrence_count, example_inputs,
                    status
                ) VALUES (
                    %(pattern_id)s, %(pattern_type)s, %(pattern_value)s,
                    %(discovered_at)s, %(discovery_method)s, %(confidence)s,
                    %(occurrence_count)s, %(example_inputs)s,
                    %(status)s
                )
                ON CONFLICT (pattern_id) DO UPDATE SET
                    occurrence_count = %(occurrence_count)s,
                    confidence = %(confidence)s
            """, {
                "pattern_id": pattern.get("pattern_id"),
                "pattern_type": pattern.get("pattern_type"),
                "pattern_value": pattern.get("pattern_value"),
                "discovered_at": pattern.get("discovered_at", datetime.utcnow()),
                "discovery_method": pattern.get("discovery_method"),
                "confidence": pattern.get("confidence"),
                "occurrence_count": pattern.get("occurrence_count", 0),
                "example_inputs": json.dumps(pattern.get("example_inputs", [])),
                "status": pattern.get("status", "discovered"),
            })

            conn.commit()
            cursor.close()
            return True

        except Exception as e:
            print(f"Error saving pattern: {e}")
            conn.rollback()
            return False
        finally:
            self.pool.putconn(conn)

    # =========================================================================
    # COMPLIANCE QUERIES
    # =========================================================================

    def get_compliance_stats(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get compliance statistics for a time period

        Args:
            start_date: Start of period
            end_date: End of period

        Returns:
            Compliance statistics
        """
        if not self.enabled or self.pool is None:
            return {}

        conn = self.pool.getconn()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(f"""
                SELECT
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN blocked THEN 1 ELSE 0 END) as blocked_requests,
                    SUM(CASE WHEN pii_detected THEN 1 ELSE 0 END) as pii_detections,
                    SUM(CASE WHEN injection_detected THEN 1 ELSE 0 END) as injection_attempts,
                    AVG(risk_score) as avg_risk_score,
                    SUM(redacted_count) as total_pii_redacted
                FROM {self.config.schema}.{self.config.audit_table}
                WHERE timestamp BETWEEN %(start_date)s AND %(end_date)s
            """, {"start_date": start_date, "end_date": end_date})

            result = cursor.fetchone()
            cursor.close()

            return dict(result) if result else {}

        except Exception as e:
            print(f"Error getting compliance stats: {e}")
            return {}
        finally:
            self.pool.putconn(conn)

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def ping(self) -> bool:
        """Test database connection"""
        if not self.enabled or self.pool is None:
            return False

        conn = self.pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except Exception:
            return False
        finally:
            self.pool.putconn(conn)

    def close(self):
        """Close all connections"""
        if self.pool:
            self.pool.closeall()
