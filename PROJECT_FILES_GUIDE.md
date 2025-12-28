# 📁 Project Files Guide

**Quick reference to understand what each file does and where to look.**

---

## 🎯 Start Here

| File | Purpose | When to Use |
|------|---------|-------------|
| **[HOW_TO_RUN.md](HOW_TO_RUN.md)** | **Complete setup guide** | First time setup, running the project |
| **[README.md](README.md)** | Project overview | Understanding what Sentinel does |
| **[.env.example](.env.example)** | Environment template | Configure database, API keys, ports |

---

## 📚 Documentation Files

### Quick Start Guides
- **[HOW_TO_RUN.md](HOW_TO_RUN.md)** - Main guide (start here!)
  - Prerequisites
  - Docker setup (recommended)
  - Local development setup
  - First-time user registration
  - API testing examples
  - Common commands
  - Troubleshooting

- **[DOCKER_QUICK_START.md](DOCKER_QUICK_START.md)** - Docker-specific guide
  - Docker Compose services
  - Container management
  - Volume and network info
  - Development workflow with Docker

- **[POETRY_SETUP.md](POETRY_SETUP.md)** - Poetry dependency manager guide
  - Why Poetry vs pip
  - Installation instructions
  - Daily workflow commands
  - Adding/removing packages
  - Lock file management

### Detailed Guides
- **[DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)** - Full development guide
  - Local setup (PostgreSQL, Redis, etc.)
  - Testing (pytest, Jest, Playwright)
  - Database migrations
  - Debugging
  - Performance optimization
  - Security best practices
  - Code style and linting

- **[COMPLETE_PROJECT_SUMMARY.md](COMPLETE_PROJECT_SUMMARY.md)** - Architecture overview
  - Project statistics (LOC, files, etc.)
  - System architecture diagrams
  - Database schema
  - API endpoints reference
  - Technology stack
  - Feature list

### Implementation Guides
- **[QUICK_START.md](QUICK_START.md)** - Library usage guide
  - Using Sentinel as a Python library
  - Integration with LangChain
  - Configuration examples
  - Code examples

- **[ARCHITECTURE_ENHANCED.md](ARCHITECTURE_ENHANCED.md)** - System architecture
  - 6-layer security design
  - Component diagrams
  - Data flow
  - Security model

- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Deep implementation details
  - Internal architecture
  - Design patterns
  - Extension points

---

## 🐳 Docker & Deployment Files

| File | Purpose |
|------|---------|
| **docker-compose.yml** | Orchestrates all services (PostgreSQL, Redis, API, Celery, Frontend) |
| **docker/Dockerfile** | Backend Python API image with Poetry |
| **docker/init-db.sql** | Database initialization script |
| **.env** | Your local environment variables (create from .env.example) |
| **.env.example** | Environment template with all options |

### Docker Services
```yaml
docker-compose.yml defines:
  - postgres        # PostgreSQL 15 database
  - redis           # Redis 7 cache + message broker
  - sentinel-api    # FastAPI backend (port 8000)
  - celery-worker   # Background job processor
  - frontend        # React dev server (port 5173)
  - pgadmin         # Optional PostgreSQL UI (port 5050)
  - redis-commander # Optional Redis UI (port 8081)
```

---

## 🐍 Python Configuration Files

| File | Purpose | Tools |
|------|---------|-------|
| **pyproject.toml** | Poetry config, dependencies, tool settings | Poetry |
| **poetry.lock** | Locked dependency versions | Poetry |
| **requirements.txt** | Legacy pip requirements (auto-generated from Poetry) | pip |
| **setup.py** | Package setup (legacy, use Poetry instead) | setuptools |
| **alembic.ini** | Database migration config | Alembic |

### Key Sections in pyproject.toml
```toml
[tool.poetry.dependencies]        # Production dependencies
[tool.poetry.group.dev.dependencies]  # Dev dependencies
[tool.black]                       # Code formatter config
[tool.isort]                       # Import sorter config
[tool.mypy]                        # Type checker config
[tool.pytest.ini_options]          # Test runner config
```

---

## 🎨 Frontend Files

| File/Directory | Purpose |
|----------------|---------|
| **web/package.json** | Node.js dependencies |
| **web/vite.config.ts** | Vite build configuration |
| **web/tsconfig.json** | TypeScript configuration |
| **web/.env.example** | Frontend environment template |
| **web/src/App.tsx** | React root component |
| **web/src/pages/** | Page components |
| **web/src/components/** | Reusable UI components |
| **web/src/api/** | API client functions |
| **web/src/hooks/** | Custom React hooks |

---

## 🗂️ Backend Code Structure

```
sentinel/
├── __init__.py           # Package exports
├── gateway.py            # Main SentinelGateway class
├── schemas.py            # Pydantic models
├── input_guard.py        # PII & injection detection
├── output_guard.py       # Output leak prevention
├── state_monitor.py      # Loop & cost monitoring
├── content_moderator.py  # Toxicity detection
│
├── saas/                 # SaaS Platform (Phase 1-3)
│   ├── server.py         # FastAPI app
│   ├── config.py         # Configuration
│   ├── database.py       # Database connection
│   ├── celery_app.py     # Celery configuration
│   │
│   ├── auth/             # Authentication
│   │   ├── jwt.py        # JWT token handling
│   │   └── api_keys.py   # API key management
│   │
│   ├── models/           # SQLAlchemy ORM models
│   │   ├── organization.py
│   │   ├── user.py
│   │   ├── workspace.py
│   │   ├── api_key.py
│   │   ├── policy.py
│   │   ├── audit_log.py
│   │   └── report.py
│   │
│   ├── routers/          # API endpoints
│   │   ├── auth.py       # /auth/login, /auth/register
│   │   ├── organizations.py  # /orgs
│   │   ├── workspaces.py     # /workspaces
│   │   ├── api_keys.py       # /api-keys
│   │   ├── policies.py       # /policies
│   │   ├── audit_logs.py     # /audit-logs
│   │   ├── dashboard.py      # /dashboard
│   │   └── reports.py        # /reports
│   │
│   ├── tasks/            # Celery background jobs
│   │   └── report_tasks.py
│   │
│   └── reports/          # Report generation
│       ├── base.py       # Base generator
│       ├── pci_dss.py    # PCI-DSS reports
│       ├── gdpr.py       # GDPR reports
│       ├── hipaa.py      # HIPAA reports
│       └── soc2.py       # SOC 2 reports
│
├── storage/              # Data persistence
│   ├── postgres_adapter.py
│   └── redis_adapter.py
│
└── api/                  # Legacy API (Phase 0)
    └── server.py
```

---

## 🧪 Test Files

```
tests/
├── __init__.py
├── conftest.py           # Pytest fixtures
├── test_*.py             # Unit tests
├── integration/          # Integration tests
│   └── test_*.py
└── security/             # Security tests
    └── test_*.py
```

---

## 📝 Configuration Priority

When you run the project, configuration is loaded in this order (later overrides earlier):

1. **Default values** in code
2. **.env.example** (template)
3. **.env** (your local overrides) ← **This is what you edit**
4. **Environment variables** (shell exports)
5. **Docker Compose environment** (docker-compose.yml)

**Example:**
```bash
# 1. Default in code
DATABASE_URL = "sqlite:///sentinel.db"

# 2. .env.example
DATABASE_URL=postgresql://sentinel_user:sentinel_password@localhost/sentinel

# 3. .env (you create this)
DATABASE_URL=postgresql://myuser:mypass@localhost:5432/mydb

# 4. Shell export
export DATABASE_URL=postgresql://other:pass@host/db

# 5. Docker Compose
environment:
  DATABASE_URL: postgresql://docker_user:pass@postgres/sentinel
```

---

## 🔧 Important Files to Edit

### For Configuration
- **`.env`** - All your environment variables
  - Database passwords
  - JWT secrets
  - API keys
  - Port numbers

### For Backend Development
- **`sentinel/saas/routers/`** - Add new API endpoints
- **`sentinel/saas/models/`** - Add new database tables
- **`sentinel/saas/tasks/`** - Add new background jobs
- **`pyproject.toml`** - Add Python dependencies

### For Frontend Development
- **`web/src/pages/`** - Add new pages
- **`web/src/components/`** - Add new UI components
- **`web/src/api/`** - Add API client functions
- **`web/package.json`** - Add Node.js dependencies

### For Database Changes
- **Create migration:** `docker exec -it sentinel-api alembic revision --autogenerate -m "Description"`
- **Apply migration:** `docker exec -it sentinel-api alembic upgrade head`

---

## 📊 File Size Reference

| Category | Files | Total Lines |
|----------|-------|-------------|
| **Backend Python** | ~50 | ~12,000 |
| **Frontend React** | ~30 | ~4,000 |
| **Tests** | ~20 | ~2,000 |
| **Documentation** | ~15 | ~5,000 |
| **Config Files** | ~10 | ~500 |

---

## 🎯 Quick Task Guide

### I want to...

**Run the project for the first time**
→ Read [HOW_TO_RUN.md](HOW_TO_RUN.md)

**Understand the architecture**
→ Read [COMPLETE_PROJECT_SUMMARY.md](COMPLETE_PROJECT_SUMMARY.md)

**Set up Docker**
→ Read [DOCKER_QUICK_START.md](DOCKER_QUICK_START.md)

**Use Poetry for dependencies**
→ Read [POETRY_SETUP.md](POETRY_SETUP.md)

**Develop locally without Docker**
→ Read [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)

**Add a new API endpoint**
→ Create file in `sentinel/saas/routers/`
→ Register in `sentinel/saas/server.py`

**Add a new frontend page**
→ Create component in `web/src/pages/`
→ Add route in `web/src/App.tsx`
→ Add navigation in `web/src/components/AppLayout.tsx`

**Change database schema**
→ Edit model in `sentinel/saas/models/`
→ Run `docker exec -it sentinel-api alembic revision --autogenerate -m "Change"`
→ Run `docker exec -it sentinel-api alembic upgrade head`

**Add Python package**
→ Run `poetry add package-name`
→ Rebuild Docker: `docker-compose up -d --build`

**Add JavaScript package**
→ Run `docker exec -it sentinel-frontend npm install package-name`

**See logs**
→ Run `docker-compose logs -f`

**Run tests**
→ Backend: `docker exec -it sentinel-api pytest tests/ -v`
→ Frontend: `docker exec -it sentinel-frontend npm test`

**Reset database**
→ Run `docker-compose down -v && docker-compose up -d`

---

## 📌 File Relationships

```
.env.example → .env (you copy and edit)
    ↓
docker-compose.yml (reads .env)
    ↓
docker/Dockerfile (builds image)
    ↓
pyproject.toml (Poetry installs deps)
    ↓
sentinel/saas/server.py (FastAPI app runs)
```

```
web/package.json (frontend deps)
    ↓
web/src/App.tsx (React router)
    ↓
web/src/pages/*.tsx (page components)
    ↓
web/src/api/*.ts (calls backend API)
    ↓
sentinel/saas/routers/*.py (API endpoints)
```

---

## 🚀 TL;DR - Files You'll Use Most

### Day 1 (Setup)
1. **[HOW_TO_RUN.md](HOW_TO_RUN.md)** - Read this first
2. **`.env`** - Copy from .env.example and edit
3. **`docker-compose.yml`** - Run with `docker-compose up -d`

### Day 2+ (Development)
1. **`sentinel/saas/routers/`** - Backend API code
2. **`web/src/`** - Frontend React code
3. **`pyproject.toml`** - Python dependencies
4. **`web/package.json`** - JavaScript dependencies

### When Things Break
1. **`docker-compose logs -f`** - View logs
2. **[HOW_TO_RUN.md](HOW_TO_RUN.md)** - Check Troubleshooting section
3. **`.env`** - Verify configuration

---

**That's it!** You now know what every important file does. Start with [HOW_TO_RUN.md](HOW_TO_RUN.md) and you'll be up and running in 5 minutes! 🚀
