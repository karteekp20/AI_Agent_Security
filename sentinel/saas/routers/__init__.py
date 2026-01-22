"""
API Routers - FastAPI Endpoint Collections
Authentication, organizations, workspaces, policies, reports, dashboard
"""

from .auth import router as auth_router
from .organizations import router as organizations_router
from .workspaces import router as workspaces_router
from .dashboard import router as dashboard_router
from .policies import router as policies_router
from .audit import router as audit_router
from .api_keys import router as api_keys_router
from .reports import router as reports_router

# NEW ROUTERS - Month 3-4 Features
from .ml import router as ml_router
from .webhooks import router as webhooks_router
from .integrations import router as integrations_router
from .ab_tests import router as ab_tests_router

__all__ = [
    "auth_router",
    "organizations_router",
    "workspaces_router",
    "dashboard_router",
    "policies_router",
    "audit_router",
    "api_keys_router",
    "reports_router",
    # NEW
    "ml_router",
    "webhooks_router",
    "integrations_router",
    "ab_tests_router",
]
