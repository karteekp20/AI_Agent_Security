# Sentinel AI Security - Docker Quick Start Guide

Get the entire Sentinel SaaS platform running in under 5 minutes with Docker Compose!

---

## Prerequisites

Only **Docker** and **Docker Compose** are required:

- **Docker Desktop** (macOS/Windows) or **Docker Engine** (Linux)
- **Docker Compose** v2.0 or higher

Check if you have them installed:
```bash
docker --version
docker-compose --version
```

**Note:** This project uses **Poetry** for Python dependency management. The Docker build automatically installs Poetry and all dependencies - you don't need to install Poetry locally unless you want to develop outside Docker.

---

## One-Command Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd ai_agent_security
```

### 2. Create Environment File
```bash
cp .env.example .env
```

**Optional:** Edit `.env` to customize configuration (database passwords, JWT secrets, etc.)

### 3. Start All Services
```bash
docker-compose up -d
```

That's it! Docker Compose will automatically:
- ✅ Build the backend API image
- ✅ Start PostgreSQL database
- ✅ Start Redis cache
- ✅ Start Celery worker for background jobs
- ✅ Start React frontend development server
- ✅ Create network and volumes
- ✅ Run database migrations

---

## Access the Platform

After ~2-3 minutes (first build takes longer), access:

### **Frontend Dashboard**
```
http://localhost:5173
```
- Modern React web interface
- User registration and login
- Real-time threat monitoring
- Policy management UI
- Audit logs viewer
- Compliance report generator

### **Backend API Docs**
```
http://localhost:8000/docs
```
- Interactive Swagger UI
- Test all API endpoints
- View request/response schemas

### **ReDoc API Documentation**
```
http://localhost:8000/redoc
```
- Alternative documentation UI
- Better for reading/printing

---

## Quick Test

### 1. Register a User
Open http://localhost:5173/register and create an account:
- Email: `test@example.com`
- Password: `TestPass123!`
- Organization Name: `Test Corp`
- Full Name: `Test User`

### 2. Login
Use the credentials you just created at http://localhost:5173/login

### 3. Generate API Key
1. Navigate to **Settings** → **API Keys**
2. Click **Generate API Key**
3. Copy the key (starts with `sk_live_...`)

### 4. Test Security Scanning
```bash
# Test PII detection
curl -X POST http://localhost:8000/process \
  -H "X-API-Key: sk_live_YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "My credit card is 4532-1234-5678-9010",
    "user_id": "test_user_123"
  }'

# Response should show blocked=true with PII detected
```

### 5. View Dashboard
Navigate to **Dashboard** in the web UI to see:
- Total requests processed
- Threats blocked
- PII detections
- Risk score trends
- Live threat feed

---

## Service Overview

Docker Compose runs these services:

| Service | Container Name | Port | Description |
|---------|---------------|------|-------------|
| **PostgreSQL** | sentinel-postgres | 5432 | Database with multi-tenant isolation |
| **Redis** | sentinel-redis | 6379 | Cache + Celery message broker |
| **API Server** | sentinel-api | 8000 | FastAPI backend with security scanning |
| **Celery Worker** | sentinel-celery | - | Background jobs (report generation) |
| **Frontend** | sentinel-frontend | 5173 | React dashboard (Vite dev server) |

---

## Useful Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f sentinel-api
docker-compose logs -f celery-worker
docker-compose logs -f frontend
```

### Stop All Services
```bash
docker-compose down
```

### Stop and Remove Volumes (Clean Slate)
```bash
docker-compose down -v
```

### Restart a Service
```bash
docker-compose restart sentinel-api
```

### Rebuild After Code Changes
```bash
docker-compose up -d --build
```

### Access Database Directly
```bash
docker exec -it sentinel-postgres psql -U sentinel_user -d sentinel
```

### Access Redis CLI
```bash
docker exec -it sentinel-redis redis-cli
```

---

## Troubleshooting

### Issue: Port Already in Use
```
Error: bind: address already in use
```

**Solution:** Change ports in `.env`:
```bash
API_PORT=8001
POSTGRES_PORT=5433
REDIS_PORT=6380
FRONTEND_PORT=5174
```

### Issue: Frontend Not Loading
**Solution:** Wait 2-3 minutes for `npm install` to complete, then check logs:
```bash
docker-compose logs -f frontend
```

### Issue: Database Connection Error
**Solution:** Ensure PostgreSQL is healthy:
```bash
docker-compose ps
docker-compose logs postgres
```

### Issue: Celery Worker Not Processing Reports
**Solution:** Check Celery logs:
```bash
docker-compose logs -f celery-worker
```

---

## Optional: Database Admin Tools

Start pgAdmin and Redis Commander:
```bash
docker-compose --profile tools up -d
```

Access:
- **pgAdmin** (PostgreSQL UI): http://localhost:5050
  - Email: `admin@sentinel.local`
  - Password: `admin`

- **Redis Commander** (Redis UI): http://localhost:8081
  - User: `admin`
  - Password: `admin`

---

## Development Workflow

### 1. Code Changes (Hot Reload Enabled)

**Backend:** Edit files in `sentinel/` - API auto-reloads
**Frontend:** Edit files in `web/src/` - React auto-reloads

### 2. Database Migrations

Create migration after model changes:
```bash
docker exec -it sentinel-api alembic revision --autogenerate -m "Add new table"
docker exec -it sentinel-api alembic upgrade head
```

### 3. Run Tests

**Backend:**
```bash
docker exec -it sentinel-api pytest tests/ -v
```

**Frontend:**
```bash
docker exec -it sentinel-frontend npm test
```

### 4. Local Development with Poetry (Optional)

If you prefer to develop outside Docker:

**Install Poetry:**
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

**Install dependencies:**
```bash
poetry install
```

**Activate virtual environment:**
```bash
poetry shell
```

**Run API server locally:**
```bash
poetry run uvicorn sentinel.saas.server:app --reload
```

**Add new dependency:**
```bash
poetry add package-name
```

**Update lock file:**
```bash
poetry lock
```

**Generate requirements.txt (if needed):**
```bash
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

---

## Production Deployment

For production, update:

1. **Environment Variables** (`.env`):
   ```bash
   ENVIRONMENT=production
   DEBUG=false
   JWT_SECRET_KEY=<generate-with-openssl-rand>
   POSTGRES_PASSWORD=<strong-password>
   ```

2. **Disable Hot Reload:**
   ```bash
   RELOAD=false
   ```

3. **Use Production Build** for frontend:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

See `DEVELOPMENT_GUIDE.md` for full production deployment instructions.

---

## Next Steps

- 📖 Read `COMPLETE_PROJECT_SUMMARY.md` for architecture overview
- 🛠️ Read `DEVELOPMENT_GUIDE.md` for detailed setup instructions
- 📋 Check Phase 4 implementation plan for production features
- 🔒 Review security best practices in `DEVELOPMENT_GUIDE.md`

---

**Need Help?**
- Check logs: `docker-compose logs -f`
- Restart services: `docker-compose restart`
- Clean slate: `docker-compose down -v && docker-compose up -d`

**Happy Securing! 🚀🔒**
