"""
API Configuration
Environment-based configuration for production deployment
"""

import os
from pydantic import BaseModel
from typing import Optional


class APIConfig(BaseModel):
    """API server configuration"""

    # Server
    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8000"))
    workers: int = int(os.getenv("API_WORKERS", "4"))

    # Observability
    enable_metrics: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    enable_tracing: bool = os.getenv("ENABLE_TRACING", "true").lower() == "true"
    enable_logging: bool = os.getenv("ENABLE_LOGGING", "true").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    otlp_endpoint: Optional[str] = os.getenv("OTLP_ENDPOINT")

    # Storage
    redis_enabled: bool = os.getenv("REDIS_ENABLED", "true").lower() == "true"
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_password: Optional[str] = os.getenv("REDIS_PASSWORD")

    postgres_enabled: bool = os.getenv("POSTGRES_ENABLED", "true").lower() == "true"
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "sentinel")
    postgres_user: str = os.getenv("POSTGRES_USER", "sentinel_user")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "sentinel_password")

    # Rate Limiting
    rate_limit_enabled: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    requests_per_second: int = int(os.getenv("REQUESTS_PER_SECOND", "10"))
    requests_per_minute: int = int(os.getenv("REQUESTS_PER_MINUTE", "100"))
    requests_per_hour: int = int(os.getenv("REQUESTS_PER_HOUR", "1000"))

    # Circuit Breaker
    circuit_breaker_enabled: bool = os.getenv("CIRCUIT_BREAKER_ENABLED", "true").lower() == "true"
    circuit_breaker_threshold: int = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
    circuit_breaker_timeout: int = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60"))

    # CORS
    cors_enabled: bool = os.getenv("CORS_ENABLED", "true").lower() == "true"
    cors_origins: list = os.getenv("CORS_ORIGINS", "*").split(",")

    # Security
    api_key_required: bool = os.getenv("API_KEY_REQUIRED", "false").lower() == "true"
    api_keys: list = os.getenv("API_KEYS", "").split(",") if os.getenv("API_KEYS") else []


def get_config() -> APIConfig:
    """Get API configuration from environment"""
    return APIConfig()
