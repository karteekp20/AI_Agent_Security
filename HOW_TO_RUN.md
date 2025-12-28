# 🚀 How to Run Sentinel AI Security Platform

**Complete step-by-step guide to get the entire SaaS platform running in 5 minutes.**

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Docker - Recommended)](#quick-start-docker---recommended)
3. [Alternative: Local Development](#alternative-local-development)
4. [Verify Installation](#verify-installation)
5. [First-Time Setup](#first-time-setup)
6. [Common Commands](#common-commands)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Option 1: Docker (Recommended) ✅

**Only need:**
- Docker Desktop (macOS/Windows) OR Docker Engine (Linux)
- Docker Compose v2.0+

**Check if installed:**
```bash
docker --version
docker-compose --version
```

**Don't have Docker?**
- macOS/Windows: [Download Docker Desktop](https://www.docker.com/products/docker-desktop)
- Linux: `curl -fsSL https://get.docker.com | sh`

### Option 2: Local Development

**Need:**
- Python 3.10+ (`python --version`)
- Node.js 18+ (`node --version`)
- PostgreSQL 15+ (`psql --version`)
- Redis 7+ (`redis-cli --version`)
- Poetry (`curl -sSL https://install.python-poetry.org | python3 -`)

---

## Quick Start (Docker - Recommended)

### Step 1: Clone Repository
```bash
git clone <repository-url>
cd ai_agent_security
```

### Step 2: Create Environment File
```bash
cp .env.example .env
```

**Optional:** Edit `.env` to customize passwords, ports, or JWT secrets
```bash
nano .env  # or use any text editor
```

### Step 3: Generate Poetry Lock File (First Time Only)

**Option A: Let Docker handle it (easiest)**
```bash
# Docker will generate lock file automatically
docker-compose up -d
```

**Option B: Generate locally (if you have Poetry installed)**
```bash
# Install Poetry first
curl -sSL https://install.python-poetry.org | python3 -

# Generate lock file
poetry lock

# Now build Docker
docker-compose up -d
```

### Step 4: Start All Services
```bash
docker-compose up -d
```

**What this does:**
- ✅ Builds Docker images (first time: ~5-10 minutes)
- ✅ Starts PostgreSQL database
- ✅ Starts Redis cache
- ✅ Starts FastAPI backend server
- ✅ Starts Celery worker (for background jobs)
- ✅ Starts React frontend (development server)
- ✅ Creates Docker networks and volumes
- ✅ Runs database migrations

### Step 5: Wait for Services to Start
```bash
# Check status (wait until all are "healthy" or "running")
docker-compose ps
```

**Expected output:**
```
NAME                   STATUS         PORTS
sentinel-api           Up (healthy)   0.0.0.0:8000->8000/tcp
sentinel-celery        Up             
sentinel-frontend      Up             0.0.0.0:5173->5173/tcp
sentinel-postgres      Up (healthy)   0.0.0.0:5432->5432/tcp
sentinel-redis         Up (healthy)   0.0.0.0:6379->6379/tcp
```

### Step 6: Access the Platform

**🎨 Frontend Dashboard:**
```
http://localhost:5173
```
- Modern React web interface
- User registration and login
- Real-time security monitoring
- Policy management
- Compliance reports

**📚 Backend API Documentation:**
```
http://localhost:8000/docs
```
- Interactive Swagger UI
- Test all endpoints
- View schemas

**📖 Alternative API Docs:**
```
http://localhost:8000/redoc
```

---

## Alternative: Local Development

If you prefer running services locally without Docker:

### Step 1: Install Poetry
```bash
curl -sSL https://install.python-poetry.org | python3 -
poetry --version
```

### Step 2: Install Python Dependencies
```bash
poetry lock  # Generate lock file (first time)
poetry install  # Install all dependencies
```

### Step 3: Start PostgreSQL
```bash
# Create database
createdb sentinel

# Create user
psql -c "CREATE USER sentinel_user WITH PASSWORD 'sentinel_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE sentinel TO sentinel_user;"
```

### Step 4: Start Redis
```bash
redis-server
```

### Step 5: Configure Environment
```bash
cp .env.example .env
# Edit .env to set local connection strings
```

### Step 6: Run Database Migrations
```bash
poetry run alembic upgrade head
```

### Step 7: Start Backend Services

**Terminal 1 - API Server:**
```bash
poetry run uvicorn sentinel.saas.server:app --reload --port 8000
```

**Terminal 2 - Celery Worker:**
```bash
poetry run celery -A sentinel.saas.celery_app worker --loglevel=info
```

### Step 8: Start Frontend

**Terminal 3 - React App:**
```bash
cd web
npm install
npm run dev
```

**Access:** http://localhost:5173

---

## Verify Installation

### 1. Check All Services are Running

**Docker:**
```bash
docker-compose ps
```

**Local:**
```bash
# Check PostgreSQL
psql -U sentinel_user -d sentinel -c "SELECT 1;"

# Check Redis
redis-cli ping

# Check API (in browser or curl)
curl http://localhost:8000/health
```

### 2. View Logs

**Docker - All services:**
```bash
docker-compose logs -f
```

**Docker - Specific service:**
```bash
docker-compose logs -f sentinel-api
docker-compose logs -f celery-worker
docker-compose logs -f frontend
```

**Local:**
Check terminal windows where services are running

---

## First-Time Setup

### 1. Register Your First User

**Go to:** http://localhost:5173/register

**Fill in:**
- **Email:** test@example.com
- **Password:** TestPass123!
- **Full Name:** Test User
- **Organization Name:** Test Corp

**Click:** "Create Account"

### 2. Login

**Go to:** http://localhost:5173/login

**Use credentials from step 1**

### 3. Generate API Key

1. Navigate to **Settings** → **API Keys**
2. Click **"Generate API Key"**
3. Give it a name: "Test API Key"
4. Click **"Generate"**
5. **Copy the key** (starts with `sk_live_...`)
   - ⚠️ **Important:** Save this key - it's only shown once!

### 4. Test API Security Scanning

```bash
# Replace YOUR_API_KEY with the key from step 3
curl -X POST http://localhost:8000/process \
  -H "X-API-Key: sk_live_YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "My credit card number is 4532-1234-5678-9010",
    "user_id": "test_user_123"
  }'
```

**Expected response:**
```json
{
  "blocked": true,
  "block_reason": "PII detected: credit_card",
  "pii_detected": true,
  "pii_count": 1,
  "redacted_input": "My credit card number is [CREDIT_CARD_REDACTED]"
}
```

### 5. Explore the Dashboard

**Navigate to:** http://localhost:5173/dashboard

**You'll see:**
- 📊 **Metrics Cards:** Total requests, threats blocked, PII detections
- 📈 **Risk Score Chart:** Security trends over time
- 🔴 **Live Threat Feed:** Real-time security events
- 🛡️ **Recent Activity:** Latest scans and blocks

### 6. Create a Security Policy

1. Navigate to **Policies**
2. Click **"Create Policy"**
3. Fill in:
   - **Name:** Block SSN Detection
   - **Type:** pii_detection
   - **Entity Type:** ssn
   - **Action:** block
   - **Threshold:** 0.7
4. Click **"Create Policy"**
5. Click **"Deploy"** to activate

### 7. Generate a Compliance Report

1. Navigate to **Reports**
2. Click **"Generate Report"**
3. Fill in:
   - **Report Name:** Q1 2024 PCI-DSS Report
   - **Report Type:** PCI-DSS
   - **Start Date:** 2024-01-01
   - **End Date:** 2024-03-31
   - **Format:** PDF
4. Click **"Generate Report"**
5. Wait for processing (check progress bar)
6. Click **"Download"** when status = "Completed"

---

## Common Commands

### Docker Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# View logs (all services)
docker-compose logs -f

# View logs (specific service)
docker-compose logs -f sentinel-api

# Restart a service
docker-compose restart sentinel-api

# Stop and remove everything (including volumes)
docker-compose down -v

# Check service status
docker-compose ps

# Execute command in container
docker exec -it sentinel-api bash

# Run database migrations
docker exec -it sentinel-api alembic upgrade head

# Create new migration
docker exec -it sentinel-api alembic revision --autogenerate -m "Description"

# Run backend tests
docker exec -it sentinel-api pytest tests/ -v

# Access PostgreSQL CLI
docker exec -it sentinel-postgres psql -U sentinel_user -d sentinel

# Access Redis CLI
docker exec -it sentinel-redis redis-cli
```

### Poetry Commands (Local Development)

```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Add new dependency
poetry add package-name

# Add dev dependency
poetry add --group dev pytest-mock

# Remove dependency
poetry remove package-name

# Update all dependencies
poetry update

# Update specific package
poetry update fastapi

# Show installed packages
poetry show

# Show dependency tree
poetry show --tree

# Run command
poetry run python script.py
poetry run uvicorn sentinel.saas.server:app --reload

# Export to requirements.txt
poetry export -f requirements.txt --output requirements.txt --without-hashes

# Check for security vulnerabilities
poetry show --outdated
```

### Database Commands

```bash
# Create new migration
docker exec -it sentinel-api alembic revision --autogenerate -m "Add users table"

# Apply migrations
docker exec -it sentinel-api alembic upgrade head

# Rollback one migration
docker exec -it sentinel-api alembic downgrade -1

# View migration history
docker exec -it sentinel-api alembic history

# View current version
docker exec -it sentinel-api alembic current
```

---

## Troubleshooting

### ❌ Problem: Port Already in Use

**Error:**
```
Error: bind: address already in use
```

**Solution:**
```bash
# Option 1: Change ports in .env
nano .env
# Change:
API_PORT=8001
POSTGRES_PORT=5433
REDIS_PORT=6380
FRONTEND_PORT=5174

# Option 2: Stop conflicting service
sudo lsof -i :8000  # Find process using port
kill -9 <PID>  # Kill the process
```

### ❌ Problem: Frontend Not Loading

**Symptoms:**
- http://localhost:5173 doesn't load
- "Connection refused" error

**Solution:**
```bash
# Check frontend logs
docker-compose logs -f frontend

# Wait for npm install to complete (takes 2-3 minutes first time)
# Look for: "VITE v5.x.x ready in XXX ms"

# If stuck, restart frontend
docker-compose restart frontend
```

### ❌ Problem: Database Connection Error

**Error:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solution:**
```bash
# Check PostgreSQL is healthy
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres

# If still fails, recreate database
docker-compose down -v
docker-compose up -d
```

### ❌ Problem: Celery Worker Not Processing Reports

**Symptoms:**
- Reports stuck in "processing" status
- Reports never complete

**Solution:**
```bash
# Check Celery logs
docker-compose logs -f celery-worker

# Look for connection errors to Redis or PostgreSQL

# Restart Celery worker
docker-compose restart celery-worker

# Check Redis is running
docker exec -it sentinel-redis redis-cli ping
# Should return: PONG
```

### ❌ Problem: "poetry.lock not found" During Docker Build

**Error:**
```
ERROR: poetry.lock not found
```

**Solution:**
```bash
# Option 1: Let Docker generate it
docker-compose up -d
# (Dockerfile will create lock file automatically)

# Option 2: Generate locally
curl -sSL https://install.python-poetry.org | python3 -
poetry lock
docker-compose build
```

### ❌ Problem: API Returns 401 Unauthorized

**Error:**
```json
{"detail": "Not authenticated"}
```

**Solution:**
```bash
# Check you're using the correct API key
# API key should start with: sk_live_

# Check X-API-Key header is set
curl -X POST http://localhost:8000/process \
  -H "X-API-Key: sk_live_YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "test"}'

# Regenerate API key if lost
# Go to: Settings → API Keys → Generate New Key
```

### ❌ Problem: Frontend Shows CORS Error

**Error:**
```
Access to XMLHttpRequest blocked by CORS policy
```

**Solution:**
```bash
# Check FRONTEND_URL in .env matches
cat .env | grep FRONTEND_URL
# Should be: FRONTEND_URL=http://localhost:5173

# Restart API server
docker-compose restart sentinel-api
```

### ❌ Problem: Docker Build Fails

**Error:**
```
ERROR: failed to solve: process "/bin/sh -c poetry install" did not complete successfully
```

**Solution:**
```bash
# Clear Docker cache and rebuild
docker-compose down
docker system prune -a
docker-compose build --no-cache
docker-compose up -d
```

---

## Quick Reference

### Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:5173 | React dashboard |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **ReDoc** | http://localhost:8000/redoc | Alternative docs |
| **API Endpoint** | http://localhost:8000/process | Security scanning |
| **Health Check** | http://localhost:8000/health | API health status |

### Default Credentials (Development)

| Service | Username | Password |
|---------|----------|----------|
| PostgreSQL | sentinel_user | sentinel_password |
| pgAdmin | admin@sentinel.local | admin |
| Redis Commander | admin | admin |

**⚠️ Change these in production!**

### File Structure

```
ai_agent_security/
├── .env                    ← Your environment variables
├── docker-compose.yml      ← Docker services configuration
├── pyproject.toml          ← Python dependencies (Poetry)
├── poetry.lock            ← Locked dependency versions
├── HOW_TO_RUN.md          ← This file
├── DOCKER_QUICK_START.md  ← Docker guide
├── POETRY_SETUP.md        ← Poetry guide
├── DEVELOPMENT_GUIDE.md   ← Full development guide
├── sentinel/              ← Backend Python code
│   ├── saas/             ← SaaS platform code
│   │   ├── server.py     ← FastAPI app
│   │   ├── routers/      ← API endpoints
│   │   ├── models/       ← Database models
│   │   ├── tasks/        ← Celery tasks
│   │   └── reports/      ← Report generators
│   └── ...
├── web/                   ← Frontend React code
│   ├── src/
│   │   ├── pages/        ← React pages
│   │   ├── components/   ← React components
│   │   └── api/          ← API client
│   └── package.json
├── docker/
│   └── Dockerfile        ← Backend Docker image
└── tests/                ← Test files
```

---

## 🎉 Success!

If you've completed all steps, you now have:

✅ **Multi-tenant SaaS platform running**
- PostgreSQL database with Row-Level Security
- Redis cache and message broker
- FastAPI backend with JWT authentication
- Celery background job processing
- React frontend with modern UI

✅ **Security features active:**
- PII detection (credit cards, SSN, emails, etc.)
- Prompt injection detection
- Content moderation
- Output leak prevention
- State monitoring

✅ **Compliance ready:**
- PCI-DSS reports
- GDPR reports
- HIPAA reports
- SOC 2 reports

✅ **Development ready:**
- Hot reload for backend and frontend
- Database migrations with Alembic
- Automated testing with pytest
- Code formatting with Black
- Type checking with mypy

---

## Need More Help?

📖 **Read the guides:**
- `DOCKER_QUICK_START.md` - Docker tips and tricks
- `POETRY_SETUP.md` - Poetry dependency management
- `DEVELOPMENT_GUIDE.md` - Full development workflow
- `COMPLETE_PROJECT_SUMMARY.md` - Architecture overview

🐛 **Found a bug?**
- Check logs: `docker-compose logs -f`
- Check Troubleshooting section above
- Create GitHub issue with logs and steps to reproduce

💡 **Want to contribute?**
- Read `DEVELOPMENT_GUIDE.md`
- Fork repository
- Create feature branch
- Submit pull request

---

**Happy Securing! 🚀🔒**
