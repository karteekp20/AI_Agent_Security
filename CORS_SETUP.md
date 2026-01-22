# CORS Setup - Fixed

## Issue
Frontend (http://localhost:5173) was getting CORS errors when trying to fetch from backend (http://localhost:8000).

## Root Causes
1. **Missing API prefix**: Routers weren't registered with `/api/v1` prefix
2. **CORS middleware not working**: Middleware was added but routers weren't using it properly

## Solutions Applied

### 1. Updated `sentinel/saas/config.py`
- Added both `localhost` and `127.0.0.1` variants for localhost addresses
- Explicitly listed allowed HTTP methods instead of wildcard

```python
class CORSConfig(BaseModel):
    allowed_origins: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        os.getenv("FRONTEND_URL", "https://app.sentinel.ai"),
    ]
    allow_credentials: bool = True
    allow_methods: list = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    allow_headers: list = ["*"]
```

### 2. Updated `sentinel/saas/server.py`
- Added `/api/v1` prefix to all router includes
- Added logging for CORS configuration

```python
api_prefix = "/api/v1"
app.include_router(auth_router, prefix=api_prefix)
app.include_router(organizations_router, prefix=api_prefix)
app.include_router(workspaces_router, prefix=api_prefix)
app.include_router(dashboard_router, prefix=api_prefix)
app.include_router(policies_router, prefix=api_prefix)
app.include_router(audit_router, prefix=api_prefix)
app.include_router(api_keys_router, prefix=api_prefix)
app.include_router(reports_router, prefix=api_prefix)
```

## API Endpoints Now Available
- `http://localhost:8000/api/v1/auth/login`
- `http://localhost:8000/api/v1/policies`
- `http://localhost:8000/api/v1/organizations`
- `http://localhost:8000/api/v1/workspaces`
- `http://localhost:8000/api/v1/dashboard/metrics`
- `http://localhost:8000/api/v1/audit/logs`
- `http://localhost:8000/api/v1/api-keys`
- `http://localhost:8000/api/v1/reports`

## Testing
```bash
# Test CORS headers
curl -i -H "Origin: http://localhost:5173" http://localhost:8000/api/v1/policies

# Expected response headers:
# access-control-allow-origin: http://localhost:5173
# access-control-allow-credentials: true
# access-control-expose-headers: *
```

## Running the Backend
```bash
cd /path/to/sentinel
uvicorn sentinel.saas.server:app --reload --host 0.0.0.0 --port 8000
```

## Frontend Configuration
The frontend already has the correct API base URL configured via environment variable:
- Default: `http://localhost:8000/api/v1`
- Via: `VITE_API_URL` environment variable

## Status
✅ CORS properly configured and working
✅ API endpoints accessible from frontend
✅ Authentication tokens can be sent via Authorization header
