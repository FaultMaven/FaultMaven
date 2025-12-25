"""
Authentication dependencies for FastAPI.

Provides reusable dependency functions for JWT validation and user extraction.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from faultmaven.modules.auth.service import AuthService
from faultmaven.dependencies import get_auth_service


# HTTP Bearer token scheme
security = HTTPBearer()


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> str:
    """
    Validate JWT token and return user ID.

    This dependency extracts the Bearer token from the Authorization header,
    validates it using the AuthService, and returns the user_id.

    Args:
        credentials: HTTP Bearer credentials from Authorization header
        auth_service: Injected AuthService instance

    Returns:
        user_id: ID of the authenticated user

    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    token = credentials.credentials

    try:
        # Validate token and extract user
        user = await auth_service.validate_token(token)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Return user ID string, not User object
        return str(user.id)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def optional_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    auth_service: AuthService = Depends(get_auth_service),
) -> str | None:
    """
    Optional authentication - returns user_id if token provided, None otherwise.

    This is useful for endpoints that work both authenticated and unauthenticated.

    Args:
        credentials: Optional HTTP Bearer credentials
        auth_service: Injected AuthService instance

    Returns:
        user_id if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        user = await auth_service.validate_token(credentials.credentials)
        return str(user.id) if user else None
    except Exception:
        return None


# Alias for backward compatibility
get_current_user = require_auth
