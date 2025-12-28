# Sentinel AI Security - Docker Deployment Guide

## Quick Start

### 1. Start Database Services Only

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Check status
docker-compose ps

# View logs
docker-compose logs -f postgres redis
```

### 2. Start with Management UIs (pgAdmin + Redis Commander)

```bash
# Start databases + web UIs
docker-compose --profile tools up -d

# Access UIs:
# - pgAdmin: http://localhost:5050
#   Login: admin@sentinel.local / admin
# - Redis Commander: http://localhost:8081
#   Login: admin / admin
```

### 3. Start Full Stack (API + Databases)

```bash
# Start everything including Sentinel API
docker-compose --profile app up -d

# Access API:
# - API Server: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Health Check: http://localhost:8000/health
```

---

## Configuration

### Environment Variables

1. Copy example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and update values:
```bash
# Required: Update database password
POSTGRES_PASSWORD=your_secure_password_here

# Optional: Update Redis password
REDIS_PASSWORD=your_redis_password

# Optional: Update ports if defaults conflict
POSTGRES_PORT=5432
REDIS_PORT=6379
API_PORT=8000
```

---

## Database Access

### PostgreSQL

**Connection String:**
```
postgresql://sentinel_user:sentinel_password@localhost:5432/sentinel
```

**Using psql CLI:**
```bash
# Connect to PostgreSQL container
docker exec -it sentinel-postgres psql -U sentinel_user -d sentinel

# Run queries
\dt                           # List tables
\d audit_logs                 # Describe audit_logs table
SELECT COUNT(*) FROM audit_logs;
```

**Using pgAdmin (Web UI):**
1. Open http://localhost:5050
2. Login: `admin@sentinel.local` / `admin`
3. Add Server:
   - Name: Sentinel
   - Host: postgres
   - Port: 5432
   - Database: sentinel
   - Username: sentinel_user
   - Password: sentinel_password

### Redis

**Using redis-cli:**
```bash
# Connect to Redis container
docker exec -it sentinel-redis redis-cli

# Commands
PING                          # Test connection
KEYS sentinel:*              # List all Sentinel keys
GET sentinel:session:abc123  # Get session data
DBSIZE                       # Total keys
INFO                         # Server info
```

**Using Redis Commander (Web UI):**
1. Open http://localhost:8081
2. Login: `admin` / `admin`
3. Browse keys and values

---

## Useful Commands

### Service Management

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f [service_name]

# Check service health
docker-compose ps
```

### Database Operations

```bash
# Backup PostgreSQL
docker exec sentinel-postgres pg_dump -U sentinel_user sentinel > backup.sql

# Restore PostgreSQL
docker exec -i sentinel-postgres psql -U sentinel_user sentinel < backup.sql

# Backup Redis
docker exec sentinel-redis redis-cli SAVE
docker cp sentinel-redis:/data/dump.rdb ./redis-backup.rdb

# Clean all data (WARNING: Deletes everything!)
docker-compose down -v
```

### Development

```bash
# Rebuild images
docker-compose build

# View container stats
docker stats

# Shell into container
docker exec -it sentinel-api bash
docker exec -it sentinel-postgres bash
docker exec -it sentinel-redis sh
```

---

## Production Deployment

### 1. Update Passwords

Edit `.env` with strong passwords:
```bash
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
PGADMIN_PASSWORD=$(openssl rand -base64 32)
```

### 2. Enable Persistence

Ensure volumes are backed up:
```bash
# Backup volumes
docker run --rm -v ai_agent_security_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres-data.tar.gz -C /data .

docker run --rm -v ai_agent_security_redis_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/redis-data.tar.gz -C /data .
```

### 3. Configure Health Checks

Health checks are already configured in `docker-compose.yml`:
- PostgreSQL: `pg_isready` every 10s
- Redis: `redis-cli ping` every 10s
- API: HTTP GET `/health` every 30s

### 4. Resource Limits

Add resource limits to `docker-compose.yml`:
```yaml
services:
  postgres:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

---

## Monitoring

### PostgreSQL Metrics

```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity;

-- Database size
SELECT pg_size_pretty(pg_database_size('sentinel'));

-- Table sizes
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Recent audit logs
SELECT timestamp, user_id, blocked, risk_score
FROM audit_logs
ORDER BY timestamp DESC
LIMIT 10;
```

### Redis Metrics

```bash
# Get Redis info
docker exec sentinel-redis redis-cli INFO stats

# Monitor commands in real-time
docker exec sentinel-redis redis-cli MONITOR

# Memory usage
docker exec sentinel-redis redis-cli INFO memory
```

---

## Troubleshooting

### PostgreSQL won't start

```bash
# Check logs
docker-compose logs postgres

# Common issues:
# 1. Port 5432 already in use
#    Solution: Change POSTGRES_PORT in .env

# 2. Permission denied
#    Solution: Fix volume permissions
#    docker-compose down -v
#    docker volume rm ai_agent_security_postgres_data
```

### Redis won't start

```bash
# Check logs
docker-compose logs redis

# Common issues:
# 1. Port 6379 already in use
#    Solution: Change REDIS_PORT in .env

# 2. Memory issues
#    Solution: Increase Docker memory limit
```

### API can't connect to databases

```bash
# Check network connectivity
docker-compose exec sentinel-api ping postgres
docker-compose exec sentinel-api ping redis

# Verify environment variables
docker-compose exec sentinel-api env | grep POSTGRES
docker-compose exec sentinel-api env | grep REDIS
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │              │  │              │  │              │     │
│  │  Sentinel    │──│  PostgreSQL  │  │    Redis     │     │
│  │  API Server  │  │  (Audit DB)  │  │   (Cache)    │     │
│  │  Port 8000   │  │  Port 5432   │  │  Port 6379   │     │
│  │              │  │              │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │            │
│         │          ┌───────┴──────┐          │            │
│         │          │              │          │            │
│         │          │   pgAdmin    │          │            │
│         │          │   Port 5050  │          │            │
│         │          │              │          │            │
│         │          └──────────────┘          │            │
│         │                          ┌─────────┴────────┐   │
│         │                          │ Redis Commander  │   │
│         │                          │   Port 8081      │   │
│         │                          └──────────────────┘   │
└─────────┴──────────────────────────────────────────────────┘
          │
    [Host Machine]
    - API: localhost:8000
    - pgAdmin: localhost:5050
    - Redis UI: localhost:8081
```

---

## Security Best Practices

1. **Change default passwords** in `.env`
2. **Disable management UIs** in production (remove `--profile tools`)
3. **Use secrets management** (Docker secrets, Vault)
4. **Enable SSL/TLS** for database connections
5. **Restrict network access** (firewall rules)
6. **Regular backups** (automated daily backups)
7. **Monitor audit logs** (alerting on suspicious activity)
8. **Keep images updated** (`docker-compose pull`)

---

## Support

For issues, see:
- Main README: `/README.md`
- Architecture docs: `/ARCHITECTURE_ENHANCED.md`
- Implementation guide: `/IMPLEMENTATION_GUIDE.md`
