"""
Authentication utilities for testing.
"""

from datetime import datetime, timezone, timedelta
from jose import jwt


def create_access_token(user_id: str, secret_key: str = "test-secret-key") -> str:
    """
    Create JWT access token for testing.

    Args:
        user_id: User ID to include in token
        secret_key: Secret key for signing (default test key)

    Returns:
        JWT access token string

    Usage:
        token = create_access_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")
