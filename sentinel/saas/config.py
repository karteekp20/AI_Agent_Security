"""
SaaS Platform Configuration
Centralized configuration for authentication, database, and services
"""

import os
from typing import Optional
from pydantic import BaseModel


class JWTConfig(BaseModel):
    """JWT Authentication Configuration"""
    secret_key: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    refresh_token_expire_days: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))


class DatabaseConfig(BaseModel):
    """Database Configuration"""
    url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://sentinel_user:sentinel_password@localhost/sentinel"
    )
    pool_size: int = int(os.getenv("DB_POOL_SIZE", "10"))
    max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    echo: bool = os.getenv("DB_ECHO", "false").lower() == "true"


class RedisConfig(BaseModel):
    """Redis Configuration"""
    url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    max_connections: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))


class APIConfig(BaseModel):
    """API Server Configuration"""
    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8000"))
    reload: bool = os.getenv("API_RELOAD", "false").lower() == "true"
    workers: int = int(os.getenv("API_WORKERS", "4"))


class CORSConfig(BaseModel):
    """CORS Configuration for Web Dashboard"""
    allowed_origins: list = [
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        os.getenv("FRONTEND_URL", "https://app.sentinel.ai"),
    ]
    allow_credentials: bool = True
    allow_methods: list = ["*"]
    allow_headers: list = ["*"]


class CeleryConfig(BaseModel):
    """Celery Task Queue Configuration"""
    broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    task_serializer: str = "json"
    result_serializer: str = "json"
    accept_content: list = ["json"]
    timezone: str = "UTC"
    enable_utc: bool = True


class SentinelSaaSConfig(BaseModel):
    """
    Main SaaS Platform Configuration

    Load configuration from environment variables with sensible defaults.
    In production, set environment variables in .env file or container config.
    """
    jwt: JWTConfig = JWTConfig()
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    api: APIConfig = APIConfig()
    cors: CORSConfig = CORSConfig()
    celery: CeleryConfig = CeleryConfig()

    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")  # development, staging, production
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Email Configuration (for invitations, reports)
    smtp_host: Optional[str] = os.getenv("SMTP_HOST")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: Optional[str] = os.getenv("SMTP_USER")
    smtp_password: Optional[str] = os.getenv("SMTP_PASSWORD")
    smtp_from_email: str = os.getenv("SMTP_FROM_EMAIL", "noreply@sentinel.ai")

    # Stripe Configuration (for billing)
    stripe_api_key: Optional[str] = os.getenv("STRIPE_API_KEY")
    stripe_webhook_secret: Optional[str] = os.getenv("STRIPE_WEBHOOK_SECRET")

    # AWS S3 Configuration (for report storage)
    aws_access_key_id: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    s3_bucket_name: str = os.getenv("S3_BUCKET_NAME", "sentinel-reports")

    class Config:
        case_sensitive = False


# Global configuration instance
config = SentinelSaaSConfig()


# Update JWT module to use config
def update_jwt_config():
    """Update JWT module with configuration values"""
    from . import auth
    auth.jwt.SECRET_KEY = config.jwt.secret_key
    auth.jwt.ALGORITHM = config.jwt.algorithm
    auth.jwt.ACCESS_TOKEN_EXPIRE_MINUTES = config.jwt.access_token_expire_minutes
    auth.jwt.REFRESH_TOKEN_EXPIRE_DAYS = config.jwt.refresh_token_expire_days


# Auto-update JWT config on import
update_jwt_config()
