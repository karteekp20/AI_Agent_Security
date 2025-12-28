"""
API Key Management - Generation and Validation
Secure API key generation with SHA-256 hashing
"""

import hashlib
import secrets
from datetime import datetime
from typing import Tuple, Optional
from uuid import UUID


def generate_api_key(prefix: str = "sk_live") -> Tuple[str, str, str]:
    """
    Generate a secure API key with SHA-256 hash

    Creates a cryptographically secure random API key with format:
    {prefix}_{random_string}

    Args:
        prefix: Key prefix (default: "sk_live" for production, use "sk_test" for test mode)

    Returns:
        Tuple of (full_api_key, key_hash, key_prefix)
        - full_api_key: Complete API key to show user ONCE (never stored)
        - key_hash: SHA-256 hash to store in database
        - key_prefix: First 12 characters for UI display (e.g., "sk_live_abc")

    Example:
        >>> api_key, key_hash, key_prefix = generate_api_key()
        >>> print(f"Prefix: {key_prefix}")
        sk_live_abc1

    Security Notes:
        - Full API key is 64 characters (prefix + _ + 56 random chars)
        - Random portion uses secrets.token_urlsafe() for cryptographic strength
        - Only hash is stored in database (SHA-256)
        - Key prefix allows UI to display partial key for identification
    """
    # Generate 42 bytes of random data -> ~56 URL-safe characters
    random_part = secrets.token_urlsafe(42)

    # Create full API key
    full_api_key = f"{prefix}_{random_part}"

    # Generate SHA-256 hash for database storage
    key_hash = hashlib.sha256(full_api_key.encode()).hexdigest()

    # Extract prefix for UI display (first 12 characters)
    key_prefix = full_api_key[:12] + "..."

    return full_api_key, key_hash, key_prefix


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256

    Used to hash incoming API keys for database lookup.

    Args:
        api_key: Full API key string

    Returns:
        SHA-256 hex digest

    Example:
        >>> key_hash = hash_api_key("sk_live_abc123...")
        >>> print(key_hash)
        a3f2b1c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7a8b9c0
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key_format(api_key: str) -> bool:
    """
    Verify API key has correct format

    Validates:
    - Starts with valid prefix (sk_live_ or sk_test_)
    - Has minimum length
    - Contains only URL-safe characters

    Args:
        api_key: API key to validate

    Returns:
        True if format is valid, False otherwise

    Example:
        >>> verify_api_key_format("sk_live_abc123...")
        True
        >>> verify_api_key_format("invalid_key")
        False
    """
    # Check prefix
    valid_prefixes = ["sk_live_", "sk_test_"]
    if not any(api_key.startswith(prefix) for prefix in valid_prefixes):
        return False

    # Check minimum length (prefix + at least 40 characters)
    if len(api_key) < 50:
        return False

    # Check characters (alphanumeric, underscore, hyphen)
    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    if not all(c in allowed_chars for c in api_key):
        return False

    return True


class APIKeyValidator:
    """
    API Key validation with database lookups

    Validates API keys against database records, checking:
    - Key hash matches
    - Key is active
    - Key is not revoked
    - Key is not expired
    - Organization is active
    """

    def __init__(self, db_session):
        """
        Initialize validator with database session

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def validate_api_key(self, api_key: str) -> Optional[dict]:
        """
        Validate API key and return key metadata

        Args:
            api_key: Full API key string

        Returns:
            Dictionary with key metadata if valid, None if invalid:
            {
                "key_id": UUID,
                "org_id": UUID,
                "workspace_id": UUID | None,
                "scopes": list,
                "rate_limit_per_minute": int,
                "rate_limit_per_hour": int,
            }

        Example:
            >>> validator = APIKeyValidator(db_session)
            >>> key_data = validator.validate_api_key(api_key)
            >>> if key_data:
            ...     print(f"Org ID: {key_data['org_id']}")
            ... else:
            ...     print("Invalid API key")
        """
        # Validate format first
        if not verify_api_key_format(api_key):
            return None

        # Hash the API key
        key_hash = hash_api_key(api_key)

        # Look up in database
        from ..models import APIKey, Organization

        api_key_record = (
            self.db.query(APIKey)
            .filter(APIKey.key_hash == key_hash)
            .first()
        )

        if not api_key_record:
            return None

        # Check if key is valid
        if not api_key_record.is_valid:
            return None

        # Check if organization is active
        org = (
            self.db.query(Organization)
            .filter(Organization.org_id == api_key_record.org_id)
            .first()
        )

        if not org or not org.is_active:
            return None

        # Update last_used_at timestamp
        api_key_record.last_used_at = datetime.utcnow()
        self.db.commit()

        # Return key metadata
        return {
            "key_id": api_key_record.key_id,
            "org_id": api_key_record.org_id,
            "workspace_id": api_key_record.workspace_id,
            "scopes": api_key_record.scopes,
            "rate_limit_per_minute": api_key_record.rate_limit_per_minute,
            "rate_limit_per_hour": api_key_record.rate_limit_per_hour,
        }

    def revoke_api_key(self, key_id: UUID) -> bool:
        """
        Revoke an API key

        Args:
            key_id: UUID of the API key to revoke

        Returns:
            True if successfully revoked, False otherwise

        Example:
            >>> validator.revoke_api_key(key_id)
            True
        """
        from ..models import APIKey

        api_key_record = (
            self.db.query(APIKey)
            .filter(APIKey.key_id == key_id)
            .first()
        )

        if not api_key_record:
            return False

        api_key_record.revoked_at = datetime.utcnow()
        api_key_record.is_active = False
        self.db.commit()

        return True
