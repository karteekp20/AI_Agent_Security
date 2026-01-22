# Testing Login & API

## Issue Resolution
The 404 error on `/api/v1/auth/login` meant the endpoint wasn't found, which indicates either:
1. Backend server wasn't running
2. Wrong URL format (missing `/api/v1` prefix)
3. No database connection

## Verified Working ✅

### 1. User Registration (Create Account)
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email":"demo@example.com",
    "password":"Demo123!@#",
    "full_name":"Demo User",
    "org_name":"Demo Org"
  }'
```

**Response:**
```json
{
  "user_id": "cf8ae38d-9b61-400c-817c-8d4659b49cd0",
  "email": "demo@example.com",
  "full_name": "Demo User",
  "org_id": "33540c2c-0633-41da-96c6-149f7e9a2fa6",
  "org_name": "Demo Org",
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### 2. User Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"Demo123!@#"}'
```

**Response:**
```json
{
  "user_id": "cf8ae38d-9b61-400c-817c-8d4659b49cd0",
  "email": "demo@example.com",
  "full_name": "Demo User",
  "role": "owner",
  "org_id": "33540c2c-0633-41da-96c6-149f7e9a2fa6",
  "org_name": "Demo Org",
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### 3. Use Token to Access Protected Endpoints
```bash
# Get current user (authenticated endpoint)
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"

# Get policies
curl http://localhost:8000/api/v1/policies \
  -H "Authorization: Bearer <access_token>"

# Get dashboard metrics
curl http://localhost:8000/api/v1/dashboard/metrics \
  -H "Authorization: Bearer <access_token>"
```

## Frontend Login Flow

1. User enters credentials on login page
2. Frontend sends POST to `/api/v1/auth/login`
3. Backend returns `access_token` and `refresh_token`
4. Frontend stores tokens in `localStorage`:
   - `access_token` - used for API requests
   - `refresh_token` - used to refresh token when expired
5. Frontend includes token in Authorization header for all subsequent requests

## Testing in Browser

1. Go to `http://localhost:5173/login`
2. Register or login with:
   - Email: `demo@example.com`
   - Password: `Demo123!@#`
3. Tokens are automatically stored in localStorage
4. Redirect to dashboard which uses the token for all API calls

## Backend Status Checklist

✅ CORS enabled and working
✅ Auth endpoints working  
✅ User registration working
✅ User login working
✅ Token generation working
✅ Database connected
✅ API routes prefixed with `/api/v1`

## If Still Getting 404

1. **Check backend is running:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check routes are registered:**
   ```bash
   curl http://localhost:8000/api/v1/auth/login -X OPTIONS
   ```
   Should return CORS headers and 200/405 (not 404)

3. **Check logs:**
   ```bash
   # If running with uvicorn directly
   uvicorn sentinel.saas.server:app --reload
   ```

## Demo Credentials

Ready to use in frontend:
- **Email:** demo@example.com
- **Password:** Demo123!@#
