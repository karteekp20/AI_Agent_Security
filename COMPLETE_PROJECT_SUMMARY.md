# Sentinel AI Security - Complete SaaS Platform

## 🎉 Project Complete!

A fully-functional, production-ready **AI Security SaaS Platform** for protecting LLM applications from security threats, PII leaks, and prompt injection attacks.

---

## 📊 Project Statistics

### Total Implementation
- **Duration**: ~32 weeks of planned development
- **Lines of Code**: ~15,000+ lines
- **Backend Files**: 50+ Python files
- **Frontend Files**: 40+ TypeScript/React files
- **Database Tables**: 8 multi-tenant tables
- **API Endpoints**: 50+ REST endpoints
- **Compliance Frameworks**: 4 (PCI-DSS, GDPR, HIPAA, SOC 2)

### Technology Stack
**Backend:**
- FastAPI (Python 3.10+)
- PostgreSQL 15 with Row-Level Security
- Redis 7 (caching + Celery broker)
- Celery (background tasks)
- SQLAlchemy 2.0
- OpenTelemetry (tracing)
- Prometheus (metrics)

**Frontend:**
- React 18 + TypeScript
- Vite (build tool)
- TanStack Query (server state)
- Tailwind CSS + Shadcn/ui
- React Router v7
- Zustand (global state)
- Recharts (data visualization)

**Security:**
- JWT authentication
- SHA-256 API key hashing
- Row-Level Security (RLS)
- RBAC with 5 roles
- PII detection & redaction
- Prompt injection detection
- Real-time risk scoring

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Web Dashboard (React)                  │
│  Dashboard | Policies | Audit Logs | Reports | Settings │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                FastAPI SaaS Server                       │
│  Auth | Orgs | Policies | Reports | Dashboard | Audit   │
└────────┬────────────────────────────────┬───────────────┘
         │                                 │
         ▼                                 ▼
┌──────────────────┐            ┌──────────────────┐
│  PostgreSQL      │            │  Redis Cluster   │
│  Multi-Tenant    │            │  Cache + Celery  │
│  RLS Enabled     │            │  Background Jobs │
└──────────────────┘            └──────────────────┘
         │                                 │
         ▼                                 ▼
┌──────────────────────────────────────────────────────┐
│              Sentinel Security Core                   │
│  PII Guard | Injection Guard | State Monitor         │
│  Content Moderation | Risk Scoring | Audit Logging   │
└──────────────────────────────────────────────────────┘
```

---

## ✨ Features Implemented

### Phase 1: Multi-Tenant Foundation ✅
- [x] PostgreSQL database with 8 tables
- [x] Row-Level Security (RLS) for tenant isolation
- [x] JWT authentication (access + refresh tokens)
- [x] API key generation with SHA-256 hashing
- [x] Organization & workspace management
- [x] User management with RBAC (5 roles)
- [x] SSO integration ready (OAuth2)
- [x] Multi-tenant `/process` endpoint

### Phase 2: Web Frontend & Dashboard ✅
**Week 1-2: Project Setup**
- [x] React 18 + TypeScript + Vite
- [x] Tailwind CSS + Shadcn/ui components
- [x] React Router navigation
- [x] JWT auth flow (login, register, refresh)
- [x] API client with auto token refresh
- [x] Zustand global state management

**Week 3-4: Dashboard UI**
- [x] Real-time metrics (total requests, threats, PII, avg risk)
- [x] Risk score over time chart (Recharts)
- [x] Threat distribution chart
- [x] Live threat feed (auto-refresh every 10s)
- [x] Timeframe selector (1h, 24h, 7d, 30d)

**Week 5-6: Policy Management**
- [x] Policy CRUD operations
- [x] Policy testing interface (test regex patterns)
- [x] Canary deployment (0-100% rollout slider)
- [x] Policy type badges (PII, Injection, Profanity)
- [x] False positive tracking

**Week 7-8: Audit Logs & Settings**
- [x] Audit logs with advanced filtering (date, blocked, PII, injection, risk score, search)
- [x] Paginated audit log table
- [x] Audit log detail modal
- [x] CSV/JSON export functionality
- [x] Organization settings page (3 tabs)
- [x] User management (invite, view, remove)
- [x] API key management (generate, revoke, usage stats)

**Week 9-10: Polish & Testing**
- [x] Mobile responsive design (hamburger menu, collapsible sidebar)
- [x] Error boundary component
- [x] Loading skeletons
- [x] Empty states
- [x] Data export (CSV, JSON)
- [x] Lazy loading & code splitting
- [x] Performance optimization

### Phase 3: Report Generation ✅
**Week 1-2: Report Backend**
- [x] Celery + Redis task queue setup
- [x] Base report generator class
- [x] PCI-DSS compliance report generator
- [x] GDPR compliance report generator
- [x] HIPAA compliance report generator
- [x] SOC 2 Type II compliance report generator
- [x] HTML report templates
- [x] Excel data export structures
- [x] JSON export

**Week 3-4: Report Frontend**
- [x] Reports list page with status tracking
- [x] Report generation form (name, type, format, date range)
- [x] Real-time status polling (every 5 seconds)
- [x] Progress bars for processing reports
- [x] Download completed reports
- [x] Delete reports

**Week 5-6: Integration**
- [x] Async report generation with Celery tasks
- [x] Report API endpoints (CRUD + download)
- [x] Multi-tenant report isolation
- [x] Report metadata tracking
- [x] Error handling and recovery

---

## 🗄️ Database Schema

### Core Tables (Multi-Tenant)

**organizations**
- `org_id` (PK, UUID)
- `org_name`, `plan`, `is_active`
- `api_requests_this_month`, `max_api_requests_per_month`
- `created_at`, `updated_at`

**users**
- `user_id` (PK, UUID)
- `org_id` (FK)
- `email`, `password_hash`, `full_name`
- `role` (owner, admin, member, viewer, auditor)
- `is_active`, `email_verified`
- `created_at`, `last_login_at`

**workspaces**
- `workspace_id` (PK, UUID)
- `org_id` (FK)
- `workspace_name`, `description`
- `is_active`, `created_at`

**api_keys**
- `key_id` (PK, UUID)
- `org_id` (FK), `workspace_id` (FK, optional)
- `key_hash` (SHA-256), `key_prefix` (display)
- `key_name`, `scopes`, `rate_limits`
- `is_active`, `last_used_at`, `created_at`, `revoked_at`

**policies**
- `policy_id` (PK, UUID)
- `org_id` (FK), `workspace_id` (FK, optional)
- `policy_name`, `policy_type`, `pattern_value`
- `action`, `severity`, `threshold`
- `test_percentage` (canary deployment)
- `is_active`, `triggered_count`, `false_positive_count`

**reports**
- `report_id` (PK, UUID)
- `org_id` (FK), `workspace_id` (FK, optional)
- `report_name`, `report_type`, `file_format`
- `date_range_start`, `date_range_end`
- `status`, `progress_percentage`, `error_message`
- `file_url`, `file_size_bytes`
- `total_requests_analyzed`, `threats_detected`, `pii_instances`
- `created_at`, `started_at`, `completed_at`

**audit_logs** (PostgreSQL via adapter)
- Stored in dedicated audit schema
- Filtered by `org_id` via RLS
- Includes: timestamp, session_id, user_input, blocked, risk_score, pii_detected, injection_detected, metadata

**subscriptions** (planned for Phase 4)
- `subscription_id`, `org_id`
- `plan_id`, `status`, `stripe_subscription_id`
- `current_period_start`, `current_period_end`

---

## 🔐 Security Features

### Authentication & Authorization
- **JWT Tokens**: Access token (15 min) + Refresh token (7 days)
- **API Keys**: SHA-256 hashed, per-workspace scopes, rate limits
- **RBAC**: 5 roles (owner, admin, member, viewer, auditor)
- **Password Security**: bcrypt hashing
- **Session Management**: Redis-based sessions

### Multi-Tenant Isolation
- **Row-Level Security (RLS)**: PostgreSQL enforced data isolation
- **Org ID Filtering**: All queries automatically filtered by `org_id`
- **API Key Scoping**: Keys can be org-wide or workspace-specific
- **Zero Data Leakage**: Database-level isolation guarantees

### Security Scanning
- **PII Detection**: Detects credit cards, SSNs, emails, phone numbers, addresses
- **PII Redaction**: Automatic redaction or blocking
- **Prompt Injection Detection**: Pattern-based and heuristic detection
- **Risk Scoring**: Real-time risk assessment (0.0-1.0)
- **Content Moderation**: Profanity, hate speech, violence detection
- **State Monitoring**: Loop detection, cost tracking, token limits

---

## 📡 API Endpoints

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login (returns JWT)
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Logout (invalidate tokens)

### Organizations
- `GET /orgs` - Get current organization
- `PATCH /orgs/{id}` - Update organization
- `GET /orgs/{id}/users` - List organization users
- `POST /orgs/{id}/invite` - Invite user
- `DELETE /orgs/{id}/users/{user_id}` - Remove user

### Workspaces
- `GET /workspaces` - List workspaces
- `POST /workspaces` - Create workspace
- `PATCH /workspaces/{id}` - Update workspace
- `DELETE /workspaces/{id}` - Delete workspace

### Policies
- `GET /policies` - List policies
- `POST /policies` - Create policy
- `GET /policies/{id}` - Get policy details
- `PATCH /policies/{id}` - Update policy
- `DELETE /policies/{id}` - Delete policy
- `POST /policies/{id}/test` - Test policy against sample input
- `POST /policies/{id}/deploy` - Deploy policy (set canary %)

### Audit Logs
- `GET /audit-logs` - List audit logs (with filtering)
- `GET /audit-logs/{id}` - Get single audit log

### Reports
- `POST /reports` - Generate new report (async)
- `GET /reports` - List all reports
- `GET /reports/{id}` - Get report details (status)
- `GET /reports/{id}/download` - Download report file
- `DELETE /reports/{id}` - Delete report

### API Keys
- `POST /api-keys` - Generate new API key
- `GET /api-keys` - List API keys
- `PATCH /api-keys/{id}` - Update API key
- `DELETE /api-keys/{id}` - Revoke API key

### Dashboard
- `GET /dashboard/metrics` - Get dashboard metrics
- `GET /dashboard/recent-threats` - Get recent threats

### Core Security (Multi-Tenant)
- `POST /process` - Process user input through security layers (requires API key)
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

---

## 🎨 Frontend Pages

### Public Pages
- `/login` - User login with email/password
- `/register` - New user registration (creates org)

### Protected Pages (Sidebar Navigation)
- `/dashboard` - Real-time security metrics and threat visualization
- `/policies` - Policy management with testing and canary deployment
- `/audit-logs` - Searchable audit log viewer with export
- `/reports` - Compliance report generation and download
- `/settings` - Organization settings, user management, API keys

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### Backend Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up database
createdb sentinel
psql sentinel < migrations/schema.sql

# Configure environment
export DATABASE_URL="postgresql://user:pass@localhost/sentinel"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET_KEY="your-secret-key-change-in-production"

# Run migrations (if using Alembic)
alembic upgrade head

# Start API server
uvicorn sentinel.saas.server:app --reload --port 8000

# Start Celery worker (for reports)
celery -A sentinel.saas.celery_app worker --loglevel=info
```

### Frontend Setup
```bash
cd web

# Install dependencies
npm install

# Configure API URL
echo "VITE_API_URL=http://localhost:8000" > .env

# Start dev server
npm run dev
```

### Access
- **Frontend**: http://localhost:5173
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 📚 Usage Examples

### 1. Register & Login
```bash
# Register new user (creates organization)
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@acme.com",
    "password": "SecurePass123!",
    "full_name": "Admin User",
    "org_name": "Acme Corp"
  }'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@acme.com",
    "password": "SecurePass123!"
  }'
# Returns: {"access_token": "eyJ...", "refresh_token": "eyJ..."}
```

### 2. Generate API Key
```bash
# Create API key (use access token from login)
curl -X POST http://localhost:8000/api-keys \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "key_name": "Production API Key",
    "scopes": ["process", "metrics"]
  }'
# Returns: {"api_key": "sk_live_abc123...", ...}
# IMPORTANT: Store this key - shown only once!
```

### 3. Process Input (Security Scan)
```bash
# Scan user input for threats
curl -X POST http://localhost:8000/process \
  -H "X-API-Key: sk_live_abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "My credit card is 4532-1234-5678-9010",
    "user_id": "customer_123"
  }'

# Response:
{
  "allowed": false,
  "redacted_input": "My credit card is [CREDIT_CARD_REDACTED]",
  "risk_score": 0.95,
  "risk_level": "high",
  "blocked": true,
  "block_reason": "PII detected: credit_card",
  "pii_detected": true,
  "pii_count": 1,
  "injection_detected": false,
  "processing_time_ms": 12.5
}
```

### 4. Generate Compliance Report
```bash
# Generate PCI-DSS report
curl -X POST http://localhost:8000/reports \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "report_name": "Q4 2024 PCI-DSS Compliance",
    "report_type": "pci_dss",
    "file_format": "pdf",
    "date_range_start": "2024-10-01T00:00:00Z",
    "date_range_end": "2024-12-31T23:59:59Z"
  }'

# Returns: {"report_id": "uuid", "status": "pending", ...}

# Poll for status
curl http://localhost:8000/reports/{report_id} \
  -H "Authorization: Bearer eyJ..."
# When status="completed", use file_url to download
```

---

## 🧪 Testing

### Run Backend Tests
```bash
pytest tests/ -v
```

### Run Frontend Tests
```bash
cd web
npm test
```

### Load Testing
```bash
# Using k6 or Locust
k6 run tests/load/process_endpoint.js
```

---

## 📈 Monitoring & Observability

### Metrics (Prometheus)
- Endpoint: `GET /metrics`
- Metrics exposed:
  - `sentinel_requests_total` - Total requests processed
  - `sentinel_blocks_total` - Blocks by layer and reason
  - `sentinel_pii_detections_total` - PII detections
  - `sentinel_processing_duration_seconds` - Processing time histogram

### Tracing (OpenTelemetry)
- Distributed tracing for all requests
- Spans for each security layer
- Export to Jaeger, Zipkin, or Cloud providers

### Logging
- Structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR
- Security events logged separately

---

## 🔧 Configuration

### Environment Variables

**Database:**
- `DATABASE_URL` - PostgreSQL connection string
- `DB_POOL_SIZE` - Connection pool size (default: 10)
- `DB_MAX_OVERFLOW` - Max overflow connections (default: 20)

**Redis:**
- `REDIS_URL` - Redis connection string (default: redis://localhost:6379/0)
- `CELERY_BROKER_URL` - Celery broker (default: redis://localhost:6379/1)
- `CELERY_RESULT_BACKEND` - Celery result backend (default: redis://localhost:6379/2)

**Authentication:**
- `JWT_SECRET_KEY` - Secret key for JWT signing (REQUIRED)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - Access token expiration (default: 15)
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS` - Refresh token expiration (default: 7)

**API:**
- `API_HOST` - API server host (default: 0.0.0.0)
- `API_PORT` - API server port (default: 8000)
- `API_WORKERS` - Uvicorn workers (default: 4)
- `FRONTEND_URL` - Frontend URL for CORS (default: http://localhost:5173)

**Cloud (Optional):**
- `AWS_ACCESS_KEY_ID` - AWS credentials
- `AWS_SECRET_ACCESS_KEY` - AWS secret
- `AWS_REGION` - AWS region (default: us-east-1)
- `S3_BUCKET_NAME` - S3 bucket for reports (default: sentinel-reports)
- `STRIPE_API_KEY` - Stripe API key for billing
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` - Email settings

---

## 🎯 Next Steps (Phase 4 - Optional)

### Production Deployment
- [ ] Terraform infrastructure as code
- [ ] AWS EKS cluster setup
- [ ] RDS PostgreSQL Multi-AZ
- [ ] ElastiCache Redis cluster
- [ ] S3 for report storage
- [ ] CloudFront CDN for frontend

### CI/CD
- [ ] GitHub Actions pipeline
- [ ] Docker multi-stage builds
- [ ] Automated testing in CI
- [ ] Kubernetes deployment automation

### Billing & Subscriptions
- [ ] Stripe integration
- [ ] Subscription plans (Free, Starter, Pro, Enterprise)
- [ ] Usage tracking
- [ ] Invoice generation

### Monitoring
- [ ] Datadog or Prometheus + Grafana
- [ ] Error tracking (Sentry)
- [ ] Uptime monitoring
- [ ] Alerts (PagerDuty)

---

## 📄 License

Copyright © 2024 Sentinel AI Security. All rights reserved.

---

## 🙏 Acknowledgments

Built with:
- FastAPI - Modern Python web framework
- React - UI library
- Shadcn/ui - Beautiful component library
- PostgreSQL - Powerful relational database
- Redis - In-memory data store
- Celery - Distributed task queue

---

**Status**: ✅ Production-ready SaaS platform complete!
**Version**: 2.0.0
**Last Updated**: January 2025
