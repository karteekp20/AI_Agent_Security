# Phase 1: Multi-Tenant SaaS Foundation - COMPLETE ✅

**Status:** 13/13 tasks completed (100%)
**Duration:** Implemented in this session
**Last Updated:** December 27, 2025

---

## Quick Start

### 1. Install Dependencies
```bash
cd /home/karteek/Documents/Cloud_Workspace/ai_agent_security
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set Up Database
```bash
# Create PostgreSQL database
createdb sentinel
createuser sentinel_user --pwprompt

# Run migrations
alembic upgrade head
```

### 3. Start SaaS Server
```bash
python -m sentinel.saas.server
```

Server runs at: `http://localhost:8000`

### 4. Test the API
```bash
# Run tests
pytest tests/test_saas_multitenant.py -v

# Or use curl
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User",
    "org_name": "Test Organization"
  }'
```

---

## API Endpoints Reference

### Authentication
```
POST   /auth/register      - Create account + organization
POST   /auth/login         - Get JWT tokens
POST   /auth/refresh       - Refresh access token
GET    /auth/me            - Current user info
```

### Organization Management
```
GET    /orgs/me            - Organization details
PATCH  /orgs/me            - Update settings
GET    /orgs/me/stats      - Usage statistics
GET    /orgs/me/users      - List users
POST   /orgs/me/users/invite - Invite user (owner/admin)
PATCH  /orgs/me/users/{id} - Update user role
DELETE /orgs/me/users/{id} - Remove user
```

### Workspace Management
```
GET    /workspaces         - List workspaces
POST   /workspaces         - Create workspace (owner/admin)
GET    /workspaces/{id}    - Workspace details
PATCH  /workspaces/{id}    - Update workspace
DELETE /workspaces/{id}    - Delete workspace
```

### Security Processing
```
POST   /process            - AI security scan (requires X-API-Key header)
GET    /health             - Health check
GET    /metrics            - Prometheus metrics
```

---

## Database Schema

### Tables Created (8 total)

1. **organizations** - Core tenant entity
   - Subscription tier, billing, usage limits
   - Soft delete support

2. **users** - Platform users
   - RBAC (5 roles: owner, admin, member, viewer, auditor)
   - MFA support, SSO integration
   - Granular permissions

3. **workspaces** - Projects/environments
   - Separate data by project or environment
   - Per-workspace configuration overrides

4. **api_keys** - Authentication tokens
   - SHA-256 hashed (never store plain text)
   - Rate limits per key
   - Scopes: process, metrics, reports

5. **policies** - Custom security rules
   - Canary deployment support (0-100%)
   - Version control with parent_policy_id
   - Impact tracking (false positive rate)

6. **reports** - Compliance report metadata
   - PCI-DSS, GDPR, HIPAA, SOC2
   - S3 signed URLs for downloads
   - Background job tracking

7. **subscriptions** - Billing management
   - Stripe integration ready
   - Payment tracking, plan management

8. **audit_logs** (created by PostgreSQL adapter)
   - Multi-tenant with org_id/workspace_id
   - PII detection, injection attempts
   - Risk scoring, escalation tracking

### Row-Level Security (RLS)
All tables have RLS policies enabled:
```sql
-- Automatic filtering by organization
CREATE POLICY users_isolation_policy ON users
USING (org_id::text = current_setting('app.current_org_id', TRUE));
```

---

## Security Architecture

### 4-Layer Defense

**Layer 1: API Authentication**
- JWT tokens (Bearer authentication)
- API keys (X-API-Key header)
- Automatic org_id extraction

**Layer 2: Application RBAC**
- Role-based access control
- Granular permissions
- FastAPI dependencies enforce permissions

**Layer 3: Query Filtering**
- Manual org_id filtering in queries
- PostgreSQL adapter includes multi-tenant methods

**Layer 4: Database RLS**
- PostgreSQL Row-Level Security
- Automatic enforcement at DB level
- Defense in depth (even if app has bugs)

---

## Code Organization

```
sentinel/saas/
├── models/              # SQLAlchemy ORM (8 tables)
│   ├── organization.py
│   ├── user.py
│   ├── workspace.py
│   ├── api_key.py
│   ├── policy.py
│   ├── report.py
│   └── subscription.py
│
├── auth/                # Authentication
│   ├── jwt.py          # JWT tokens
│   ├── password.py     # bcrypt hashing
│   └── api_keys.py     # Key generation
│
├── routers/             # FastAPI endpoints
│   ├── auth.py         # /auth/*
│   ├── organizations.py # /orgs/*
│   └── workspaces.py   # /workspaces/*
│
├── schemas/             # Pydantic models
│   ├── auth.py
│   ├── organization.py
│   └── workspace.py
│
├── config.py           # Configuration
├── dependencies.py     # FastAPI deps (RBAC)
├── server.py           # Main server
└── rls.py              # RLS utilities

migrations/versions/
├── 900dc3026ec6_create_multi_tenant_schema_with_8_core_.py
└── 46dcb1d07b70_add_row_level_security_policies_for_.py

tests/
└── test_saas_multitenant.py  # E2E tests
```

---

## Usage Examples

### 1. Register New Organization
```python
import requests

response = requests.post("http://localhost:8000/auth/register", json={
    "email": "founder@acme.com",
    "password": "SecurePass123!",
    "full_name": "John Doe",
    "org_name": "Acme Corp"
})

data = response.json()
access_token = data["access_token"]
org_id = data["org_id"]
```

### 2. Invite Team Member
```python
response = requests.post(
    "http://localhost:8000/orgs/me/users/invite",
    headers={"Authorization": f"Bearer {access_token}"},
    json={
        "email": "engineer@acme.com",
        "full_name": "Jane Smith",
        "role": "member",
        "permissions": ["policies:write"]
    }
)

temp_password = response.json()["temporary_password"]
# Send temp_password to new user via email
```

### 3. Generate API Key (Manual)
```python
from sentinel.saas.auth import generate_api_key
from sentinel.saas.models import APIKey
from sentinel.saas.dependencies import get_db

api_key_full, key_hash, key_prefix = generate_api_key()

db = next(get_db())
api_key = APIKey(
    org_id=org_id,
    workspace_id=workspace_id,
    key_hash=key_hash,
    key_prefix=key_prefix,
    key_name="Production API Key"
)
db.add(api_key)
db.commit()

# Show api_key_full to user ONCE (never stored)
print(f"API Key: {api_key_full}")
```

### 4. Use API Key for Security Scan
```python
response = requests.post(
    "http://localhost:8000/process",
    headers={"X-API-Key": api_key_full},
    json={
        "user_input": "My credit card is 4532-1234-5678-9010",
        "user_id": "customer_123"
    }
)

result = response.json()
print(f"Blocked: {result['blocked']}")
print(f"Risk Score: {result['risk_score']}")
print(f"PII Detected: {result['pii_detected']}")
```

### 5. Set Row-Level Security Context
```python
from sentinel.saas.dependencies import get_db
from sentinel.saas.rls import set_org_context, org_context
from sentinel.saas.models import User

db = next(get_db())

# Method 1: Manual
set_org_context(db, org_id)
users = db.query(User).all()  # Automatically filtered!

# Method 2: Context manager
with org_context(db, org_id):
    users = db.query(User).all()  # Filtered by org_id
# Context auto-cleared
```

---

## Configuration

### Environment Variables

Create `.env` file:
```bash
# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=postgresql://sentinel_user:password@localhost/sentinel

# Redis
REDIS_URL=redis://localhost:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Environment
ENVIRONMENT=development  # development, staging, production
DEBUG=true
```

Load in code:
```python
from sentinel.saas.config import config

print(config.jwt.secret_key)
print(config.database.url)
```

---

## Testing

### Run All Tests
```bash
pytest tests/test_saas_multitenant.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_saas_multitenant.py::TestTenantIsolation -v
```

### Test Coverage
```bash
pytest --cov=sentinel.saas --cov-report=html
```

---

## Migrations

### Create New Migration
```bash
alembic revision -m "Add new column to users"
```

### Apply Migrations
```bash
alembic upgrade head
```

### Rollback Migration
```bash
alembic downgrade -1
```

### View Current Version
```bash
alembic current
```

### View Migration History
```bash
alembic history
```

---

## Multi-Tenant Best Practices

### 1. Always Set Organization Context
```python
# In FastAPI dependencies
from sentinel.saas.rls import set_org_context

@router.get("/data")
def get_data(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    set_org_context(db, current_user.org_id)
    return db.query(Model).all()  # RLS enforced
```

### 2. Use RBAC Dependencies
```python
from sentinel.saas.dependencies import require_role, require_permission

# Require specific role
@router.delete("/users/{id}", dependencies=[Depends(require_role("owner", "admin"))])
def delete_user(id: UUID):
    ...

# Require specific permission
@router.post("/policies", dependencies=[Depends(require_permission("policies:write"))])
def create_policy():
    ...
```

### 3. Extract Org Context from API Key
```python
from sentinel.saas.dependencies import get_api_key_user

@router.post("/process")
def process(api_key_data: dict = Depends(get_api_key_user)):
    org_id = api_key_data["org_id"]
    workspace_id = api_key_data["workspace_id"]
    # Use for audit logging
```

---

## Troubleshooting

### Issue: RLS Blocking All Queries
**Solution:** Ensure org context is set before queries
```python
set_org_context(db, org_id)
```

### Issue: API Key Not Working
**Check:**
1. Key is active: `is_active = True`
2. Key not expired: `expires_at > now()`
3. Key not revoked: `revoked_at IS NULL`
4. Organization active: `org.is_active = True`

### Issue: Permission Denied
**Check:**
1. User role: `user.role` (owner, admin, member, viewer, auditor)
2. Specific permissions: `user.permissions` array
3. RBAC dependency: `require_role()` or `require_permission()`

---

## Next Steps

### Phase 2: Web Dashboard (8-10 weeks)
- [ ] React 18 + TypeScript + Vite
- [ ] Real-time threat monitoring (WebSocket)
- [ ] Policy management UI
- [ ] Audit log viewer
- [ ] Shadcn/ui components

### Phase 3: Report Generation (4-6 weeks)
- [ ] Celery background jobs
- [ ] PDF/Excel compliance reports
- [ ] S3 storage with signed URLs
- [ ] Email notifications

### Phase 4: Production Deployment (6-8 weeks)
- [ ] Terraform AWS infrastructure
- [ ] Kubernetes deployment
- [ ] Stripe billing integration
- [ ] CI/CD pipeline
- [ ] Monitoring & alerting

---

## Support & Documentation

**API Documentation:** http://localhost:8000/docs (Swagger UI)
**Health Check:** http://localhost:8000/health
**Metrics:** http://localhost:8000/metrics

**Key Files:**
- Plan: `/home/karteek/.claude/plans/temporal-wobbling-blum.md`
- This Summary: `/home/karteek/Documents/Cloud_Workspace/ai_agent_security/PHASE_1_COMPLETE.md`

---

**Phase 1 Complete:** Enterprise-grade multi-tenant SaaS API with 4-layer security! ✅
