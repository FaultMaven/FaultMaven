"""JWT-based identity provider for Core profile."""

from datetime import datetime, timedelta
from typing import Any, Optional
import jwt
from jwt.exceptions import InvalidTokenError

from faultmaven.providers.interfaces import IdentityProvider, User, TokenPair


class JWTIdentityProvider(IdentityProvider):
    """
    JWT-based identity provider using HS256 algorithm.

    For Core/Team profiles - local token management.
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        """
        Initialize JWT provider.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT signing algorithm (HS256, RS256, etc.)
            access_token_expire_minutes: Access token TTL in minutes
            refresh_token_expire_days: Refresh token TTL in days
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

        # Simple in-memory blacklist (in production, use Redis)
        self._blacklist: set[str] = set()

    async def validate_token(self, token: str) -> Optional[User]:
        """Validate access token and return user info."""
        # Check blacklist
        if token in self._blacklist:
            return None

        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )

            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                return None

            # Extract user info
            user = User()
            user.id = payload.get("sub", "")
            user.email = payload.get("email", "")
            user.roles = payload.get("roles", [])
            user.email_verified = payload.get("email_verified", False)
            user.metadata = payload.get("metadata", {})

            return user

        except InvalidTokenError:
            return None

    async def create_token(
        self,
        user: User,
        expires_in: Optional[int] = None,
    ) -> TokenPair:
        """Create access and refresh tokens for user."""
        access_expires = timedelta(
            minutes=expires_in or self.access_token_expire_minutes
        )
        refresh_expires = timedelta(days=self.refresh_token_expire_days)

        # Access token payload
        access_payload = {
            "sub": user.id,
            "email": user.email,
            "roles": user.roles,
            "email_verified": user.email_verified,
            "metadata": user.metadata,
            "exp": datetime.utcnow() + access_expires,
            "iat": datetime.utcnow(),
            "type": "access",
        }

        # Refresh token payload (minimal)
        refresh_payload = {
            "sub": user.id,
            "exp": datetime.utcnow() + refresh_expires,
            "iat": datetime.utcnow(),
            "type": "refresh",
        }

        access_token = jwt.encode(
            access_payload,
            self.secret_key,
            algorithm=self.algorithm,
        )

        refresh_token = jwt.encode(
            refresh_payload,
            self.secret_key,
            algorithm=self.algorithm,
        )

        token_pair = TokenPair()
        token_pair.access_token = access_token
        token_pair.refresh_token = refresh_token
        token_pair.expires_in = int(access_expires.total_seconds())

        return token_pair

    async def refresh_token(self, refresh_token: str) -> TokenPair:
        """Exchange refresh token for new access token."""
        try:
            payload = jwt.decode(
                refresh_token,
                self.secret_key,
                algorithms=[self.algorithm],
            )

            # Verify it's a refresh token
            if payload.get("type") != "refresh":
                raise ValueError("Invalid token type")

            # Create minimal user object
            user = User()
            user.id = payload["sub"]
            user.email = ""  # Not stored in refresh token
            user.roles = []
            user.email_verified = False
            user.metadata = {}

            # TODO: In production, fetch full user details from database
            # For now, create new token with minimal info

            return await self.create_token(user)

        except InvalidTokenError as e:
            raise ValueError(f"Invalid refresh token: {e}")

    async def revoke_token(self, token: str) -> None:
        """Revoke a token (add to blacklist)."""
        self._blacklist.add(token)
        # TODO: In production, store in Redis with TTL matching token expiration
