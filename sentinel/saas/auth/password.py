"""
Password Management - Secure Hashing and Verification
Uses bcrypt for password hashing with salt
"""

import bcrypt


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt

    Args:
        password: Plain text password string

    Returns:
        Hashed password string (bcrypt hash with salt)

    Example:
        >>> hashed = hash_password("my_secure_password")
        >>> print(hashed)
        $2b$12$KIXqXqXqXqXqXqXqXqXqXuE...

    Note:
        Bcrypt automatically generates a salt and includes it in the hash.
        Each call to hash_password() with the same input will produce
        a different hash due to random salt generation.
    """
    # Convert password to bytes and hash with bcrypt
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise

    Example:
        >>> hashed = hash_password("my_password")
        >>> verify_password("my_password", hashed)
        True
        >>> verify_password("wrong_password", hashed)
        False

    Note:
        This function is resistant to timing attacks as bcrypt
        comparison is constant-time.
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        # If verification fails due to malformed hash, return False
        return False
