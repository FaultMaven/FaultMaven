"""
Auth module FastAPI router.

Exposes endpoints for authentication and user management.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, EmailStr
from typing import Optional

from faultmaven.modules.auth.service import AuthService, AuthenticationError
from faultmaven.modules.auth.orm import User
from faultmaven.dependencies import get_auth_service


router = APIRouter(prefix="/auth", tags=["authentication"])


# ============================================================================
# Request/Response Models
# ============================================================================

class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Successful login response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class UserResponse(BaseModel):
    """User information response."""
    user_id: str
    email: str
    username: str
    full_name: Optional[str]
    roles: list[str]
    is_active: bool
    is_verified: bool


# ============================================================================
# Helper Functions
# ============================================================================

async def extract_bearer_token(
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> Optional[str]:
    """Extract Bearer token from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:].strip()


async def get_current_user(
    token: Optional[str] = Depends(extract_bearer_token),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """Get current authenticated user from token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return await auth_service.validate_token(token)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user.

    Creates a new user account with email and password.

    Args:
        request: Registration details

    Returns:
        Created user information

    Raises:
        HTTPException: If email or username already exists
    """
    try:
        user = await auth_service.register_user(
            email=request.email,
            username=request.username,
            password=request.password,
            full_name=request.full_name,
        )

        return UserResponse(
            user_id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            roles=user.roles,
            is_active=user.is_active,
            is_verified=user.is_verified,
        )

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Authenticate user and return JWT tokens.

    Args:
        request: Login credentials

    Returns:
        Access token, refresh token, and user information

    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        access_token, refresh_token, user = await auth_service.authenticate_user(
            email=request.email,
            password=request.password
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(auth_service.access_token_expire.total_seconds()),
            user={
                "user_id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "roles": user.roles,
                "is_active": user.is_active,
            }
        )

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh")
async def refresh_tokens(
    request: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh access token using refresh token.

    Args:
        request: Refresh token

    Returns:
        New access token and refresh token

    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        new_access_token, new_refresh_token = await auth_service.refresh_access_token(
            refresh_token=request.refresh_token
        )

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/logout")
async def logout(
    token: str = Depends(extract_bearer_token),
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Logout user and revoke their access token.

    Args:
        token: Current access token
        current_user: Current authenticated user

    Returns:
        Logout confirmation
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )

    await auth_service.logout(token)

    return {
        "message": "Logged out successfully",
        "revoked": True
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.

    Requires valid access token in Authorization header.

    Returns:
        User profile information
    """
    return UserResponse(
        user_id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        roles=current_user.roles,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
    )


@router.get("/health")
async def auth_health():
    """Authentication system health check."""
    return {
        "status": "healthy",
        "service": "authentication"
    }


@router.get("/.well-known/jwks.json")
async def jwks(auth_service: AuthService = Depends(get_auth_service)):
    """
    Get JSON Web Key Set (JWKS).

    Returns the public keys used to verify JWT signatures.
    For HS256, this is informational only as verification requires the secret key.

    Returns:
        JWKS document with key information
    """
    # For HS256 (symmetric), we can't expose the secret key
    # Return minimal JWKS indicating HS256 is used
    return {
        "keys": [
            {
                "kty": "oct",  # Octet sequence (symmetric key)
                "alg": auth_service.algorithm,
                "use": "sig",
                "kid": "default-key"
            }
        ]
    }


@router.get("/.well-known/openid-configuration")
async def openid_configuration(auth_service: AuthService = Depends(get_auth_service)):
    """
    Get OpenID Connect configuration.

    Returns the OIDC discovery document with supported endpoints and features.

    Returns:
        OIDC configuration document
    """
    # Get base URL from request context would be ideal, but for now use relative paths
    base_url = "/auth"

    return {
        "issuer": "faultmaven-auth",
        "authorization_endpoint": f"{base_url}/login",
        "token_endpoint": f"{base_url}/login",
        "userinfo_endpoint": f"{base_url}/me",
        "jwks_uri": f"{base_url}/.well-known/jwks.json",
        "response_types_supported": ["token"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": [auth_service.algorithm],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "claims_supported": [
            "sub",
            "email",
            "username",
            "roles"
        ],
        "grant_types_supported": ["password", "refresh_token"]
    }
