"""
Authentication Module - JWT, Password, and API Key Management
Handles user authentication, token generation, password security, and API keys
"""

from .jwt import (
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token,
    refresh_access_token,
    TokenData,
)
from .password import (
    hash_password,
    verify_password,
)
from .api_keys import (
    generate_api_key,
    hash_api_key,
    verify_api_key_format,
    APIKeyValidator,
)

__all__ = [
    # JWT
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "decode_token",
    "refresh_access_token",
    "TokenData",
    # Password
    "hash_password",
    "verify_password",
    # API Keys
    "generate_api_key",
    "hash_api_key",
    "verify_api_key_format",
    "APIKeyValidator",
]
