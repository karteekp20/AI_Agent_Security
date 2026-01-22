"""
SQLAlchemy ORM Models for Multi-Tenant SaaS Platform
"""

from sqlalchemy.ext.declarative import declarative_base

# Base class for all ORM models
Base = declarative_base()

# Import all models so Alembic can detect them
from .organization import Organization
from .user import User
from .workspace import Workspace
from .api_key import APIKey
from .policy import Policy
from .report import Report
from .subscription import Subscription
from .email_log import EmailLog
from .ml_model import MLModel
from .user_baseline import UserBaseline
from .webhook import Webhook
from .webhook_delivery import WebhookDelivery
from .integration import Integration

__all__ = [
    "Base",
    "Organization",
    "User",
    "Workspace",
    "APIKey",
    "Policy",
    "Report",
    "Subscription",
    "EmailLog",
    "MLModel",
    "UserBaseline",
    "Webhook",
    "WebhookDelivery",
    "Integration",
]
