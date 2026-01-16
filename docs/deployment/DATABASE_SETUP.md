# Database Setup Guide - Sentinel AI Security

This guide covers setting up PostgreSQL and Redis for audit logging and session management.

## Quick Start (Docker - Recommended)

### Option 1: Databases Only

```bash
# Start PostgreSQL + Redis
docker-compose up -d postgres redis

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

**Access:**
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

### Option 2: Full Stack with Management UIs

```bash
# Start databases + pgAdmin + Redis Commander
docker-compose --profile tools up -d

# Access web interfaces:
# - pgAdmin: http://localhost:5050 (admin@sentinel.local / admin)
# - Redis Commander: http://localhost:8081 (admin / admin)
```

### Option 3: Complete Application Stack

```bash
# Start everything (API + Databases + UIs)
docker-compose --profile app up -d

# Access:
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - Health: http://localhost:8000/health
```

---

## Manual Setup (Without Docker)

### Step 1: Install Database Servers

**PostgreSQL:**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql

# Start service
sudo systemctl start postgresql  # Linux
brew services start postgresql   # macOS
```

**Redis:**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Start service
sudo systemctl start redis  # Linux
brew services start redis   # macOS
```

### Step 2: Install Python Drivers

```bash
# PostgreSQL driver
pip install psycopg2-binary

# Redis client
pip install redis
```

### Step 3: Create PostgreSQL Database

```bash
# Connect as postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE sentinel;
CREATE USER sentinel_user WITH PASSWORD 'sentinel_password';
GRANT ALL PRIVILEGES ON DATABASE sentinel TO sentinel_user;

# Exit
\q
```

### Step 4: Configure Environment

Create `.env` file:
```bash
# Copy example
cp .env.example .env

# Edit with your values
nano .env
```

Update database settings:
```bash
# PostgreSQL
POSTGRES_ENABLED=true
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=sentinel
POSTGRES_USER=sentinel_user
POSTGRES_PASSWORD=your_password_here

# Redis
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
```

### Step 5: Verify Connection

```python
from sentinel.storage.postgres_adapter import PostgreSQLAdapter, PostgreSQLConfig
from sentinel.storage.redis_adapter import RedisAdapter, RedisConfig

# Test PostgreSQL
pg_config = PostgreSQLConfig(
    host="localhost",
    database="sentinel",
    user="sentinel_user",
    password="your_password_here"
)
pg = PostgreSQLAdapter(pg_config)
print(f"PostgreSQL: {pg.ping()}")  # Should print True

# Test Redis
redis_config = RedisConfig(host="localhost", port=6379)
redis = RedisAdapter(redis_config)
print(f"Redis: {redis.ping()}")  # Should print True
```

---

## Database Schema

### Tables Created Automatically

The PostgreSQL adapter creates these tables on first connection:

#### 1. `audit_logs` - Main audit trail
```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    user_role VARCHAR(100),
    ip_address VARCHAR(45),

    -- Input
    user_input TEXT,
    input_length INTEGER,

    -- Detection Results
    blocked BOOLEAN DEFAULT FALSE,
    risk_score FLOAT,
    risk_level VARCHAR(50),

    -- PII
    pii_detected BOOLEAN,
    pii_entities JSONB,
    redacted_count INTEGER,

    -- Injection
    injection_detected BOOLEAN,
    injection_type VARCHAR(100),
    injection_confidence FLOAT,

    -- Metadata
    metadata JSONB
);
```

**Indexes:**
- `timestamp` (time-range queries)
- `session_id` (session tracking)
- `blocked` (security events)
- `user_id` (user queries)

#### 2. `discovered_patterns` - Meta-learning
```sql
CREATE TABLE discovered_patterns (
    pattern_id VARCHAR(255) PRIMARY KEY,
    pattern_type VARCHAR(100),
    pattern_value TEXT,
    discovered_at TIMESTAMP,
    confidence FLOAT,
    occurrence_count INTEGER,
    example_inputs JSONB,
    status VARCHAR(50)  -- 'discovered', 'reviewed', 'deployed'
);
```

#### 3. `deployments` - Rule versioning
```sql
CREATE TABLE deployments (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50),
    deployed_at TIMESTAMP,
    deployment_type VARCHAR(50),
    patterns_added INTEGER,
    detection_rate FLOAT,
    false_positive_rate FLOAT
);
```

---

## Usage Examples

### 1. Query Audit Logs

```python
from sentinel.storage.postgres_adapter import PostgreSQLAdapter, PostgreSQLConfig
from datetime import datetime, timedelta

# Initialize
config = PostgreSQLConfig(
    host="localhost",
    database="sentinel",
    user="sentinel_user",
    password="your_password"
)
db = PostgreSQLAdapter(config)

# Get last 24 hours of logs
logs = db.get_audit_logs(
    start_time=datetime.utcnow() - timedelta(days=1),
    limit=100
)

# Get blocked requests only
blocked = db.get_audit_logs(
    start_time=datetime.utcnow() - timedelta(hours=1),
    blocked_only=True
)

# Get logs for specific user
user_logs = db.get_audit_logs(
    user_id="user_123",
    limit=50
)

# Get logs for specific session
session_logs = db.get_audit_logs(
    session_id="session_abc123"
)
```

### 2. Compliance Reports

```python
# Get compliance stats for last 30 days
from datetime import datetime, timedelta

start = datetime.utcnow() - timedelta(days=30)
end = datetime.utcnow()

stats = db.get_compliance_stats(start, end)

print(f"Total requests: {stats['total_requests']}")
print(f"Blocked: {stats['blocked_requests']}")
print(f"PII detections: {stats['pii_detections']}")
print(f"Injection attempts: {stats['injection_attempts']}")
print(f"Avg risk score: {stats['avg_risk_score']:.3f}")
```

### 3. Session State Caching (Redis)

```python
from sentinel.storage.redis_adapter import RedisAdapter, RedisConfig

# Initialize
redis_config = RedisConfig(host="localhost", port=6379)
cache = RedisAdapter(redis_config)

# Save session state
cache.save_session_state(
    session_id="session_abc123",
    state={
        "user_id": "user_123",
        "conversation_turns": 5,
        "total_cost": 0.0023,
        "context": {"last_query": "What is PII?"}
    },
    ttl=86400  # 24 hours
)

# Retrieve session state
state = cache.get_session_state("session_abc123")
print(state)

# Delete session
cache.delete_session_state("session_abc123")
```

### 4. Rate Limiting (Redis)

```python
# Check rate limit
count, is_allowed = cache.increment_rate_limit(
    identifier="user_123",
    window_seconds=60,
    max_requests=100
)

if not is_allowed:
    print(f"Rate limit exceeded: {count} requests")
else:
    print(f"Request allowed: {count}/100")
```

---

## Direct Database Queries

### PostgreSQL Queries

```sql
-- Recent audit logs
SELECT timestamp, user_id, user_input, blocked, risk_score
FROM audit_logs
ORDER BY timestamp DESC
LIMIT 20;

-- Blocked requests summary
SELECT
    DATE(timestamp) as date,
    COUNT(*) as total_blocked,
    COUNT(DISTINCT user_id) as unique_users
FROM audit_logs
WHERE blocked = TRUE
GROUP BY DATE(timestamp)
ORDER BY date DESC;

-- PII detection stats
SELECT
    pii_detected,
    COUNT(*) as count,
    AVG(risk_score) as avg_risk
FROM audit_logs
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY pii_detected;

-- Top injection types
SELECT
    injection_type,
    COUNT(*) as count,
    AVG(injection_confidence) as avg_confidence
FROM audit_logs
WHERE injection_detected = TRUE
GROUP BY injection_type
ORDER BY count DESC;

-- Session analysis
SELECT
    session_id,
    user_id,
    COUNT(*) as request_count,
    SUM(CASE WHEN blocked THEN 1 ELSE 0 END) as blocked_count,
    AVG(risk_score) as avg_risk
FROM audit_logs
GROUP BY session_id, user_id
HAVING COUNT(*) > 5
ORDER BY avg_risk DESC;
```

### Redis Queries

```bash
# Connect to Redis
redis-cli

# List all Sentinel keys
KEYS sentinel:*

# Get session data
GET sentinel:session:abc123

# Check rate limit
GET sentinel:ratelimit:user_123

# Get cache statistics
INFO stats

# Monitor commands (real-time)
MONITOR

# Check memory usage
INFO memory
```

---

## Backup & Restore

### PostgreSQL Backup

```bash
# Backup database
pg_dump -U sentinel_user -d sentinel -F c -f sentinel_backup.dump

# With Docker
docker exec sentinel-postgres pg_dump -U sentinel_user sentinel > sentinel_backup.sql

# Restore
pg_restore -U sentinel_user -d sentinel sentinel_backup.dump

# With Docker
docker exec -i sentinel-postgres psql -U sentinel_user sentinel < sentinel_backup.sql
```

### Redis Backup

```bash
# Create snapshot
redis-cli SAVE
# Or background save
redis-cli BGSAVE

# Backup file location
cp /var/lib/redis/dump.rdb ./redis_backup.rdb

# With Docker
docker exec sentinel-redis redis-cli SAVE
docker cp sentinel-redis:/data/dump.rdb ./redis_backup.rdb

# Restore: Copy dump.rdb to data directory and restart Redis
```

---

## Production Considerations

### 1. Connection Pooling

Both adapters use connection pooling:
- **PostgreSQL**: ThreadedConnectionPool (2-20 connections)
- **Redis**: redis-py connection pool (max 50 connections)

### 2. High Availability

**PostgreSQL:**
- Use replication (primary + replicas)
- Enable WAL archiving
- Configure automated backups

**Redis:**
- Use Redis Sentinel for automatic failover
- Enable AOF persistence (append-only file)
- Configure Redis Cluster for horizontal scaling

### 3. Monitoring

**PostgreSQL:**
```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity;

-- Slow queries
SELECT pid, now() - query_start as duration, query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;

-- Database size
SELECT pg_size_pretty(pg_database_size('sentinel'));
```

**Redis:**
```bash
# Server info
redis-cli INFO

# Connected clients
redis-cli CLIENT LIST

# Memory usage
redis-cli INFO memory
```

### 4. Security

- Use strong passwords (32+ characters)
- Enable SSL/TLS for connections
- Restrict network access (firewall rules)
- Regular security updates
- Enable audit logging
- Implement backup encryption

---

## Troubleshooting

### PostgreSQL Issues

**Can't connect:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check port
sudo netstat -tlnp | grep 5432

# Check pg_hba.conf for authentication settings
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

**Permission denied:**
```sql
-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE sentinel TO sentinel_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sentinel_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sentinel_user;
```

### Redis Issues

**Can't connect:**
```bash
# Check if Redis is running
sudo systemctl status redis

# Check port
sudo netstat -tlnp | grep 6379

# Test connection
redis-cli ping
```

**Memory issues:**
```bash
# Check memory usage
redis-cli INFO memory

# Clear all data (WARNING: Deletes everything!)
redis-cli FLUSHALL
```

---

## Next Steps

1. ✅ Setup databases (PostgreSQL + Redis)
2. ✅ Configure environment variables
3. ✅ Verify connections
4. 🔄 Start API server with database enabled
5. 📊 Monitor audit logs
6. 🔐 Configure backups
7. 📈 Setup monitoring dashboards

For more information:
- See `docker/README.md` for Docker deployment
- See `README.md` for API usage
- See `ARCHITECTURE_ENHANCED.md` for system design
