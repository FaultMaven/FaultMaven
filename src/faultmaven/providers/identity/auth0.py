"""Auth0 identity provider for Enterprise profile."""

from typing import Optional

from faultmaven.providers.interfaces import IdentityProvider, User, TokenPair


class Auth0IdentityProvider(IdentityProvider):
    """
    Auth0 implementation of IdentityProvider.

    Note: This is a stub implementation. Implement when Enterprise profile is needed.
    """

    def __init__(
        self,
        domain: str,
        client_id: str,
        client_secret: str,
    ):
        """
        Initialize Auth0 provider.

        Args:
            domain: Auth0 domain (e.g., 'myapp.auth0.com')
            client_id: Auth0 application client ID
            client_secret: Auth0 application client secret
        """
        self.domain = domain
        self.client_id = client_id
        self.client_secret = client_secret

    async def validate_token(self, token: str) -> Optional[User]:
        """Validate access token and return user info."""
        raise NotImplementedError("Auth0 provider not yet implemented")

    async def create_token(
        self,
        user: User,
        expires_in: Optional[int] = None,
    ) -> TokenPair:
        """Create access and refresh tokens for user."""
        raise NotImplementedError("Auth0 provider not yet implemented")

    async def refresh_token(self, refresh_token: str) -> TokenPair:
        """Exchange refresh token for new access token."""
        raise NotImplementedError("Auth0 provider not yet implemented")

    async def revoke_token(self, token: str) -> None:
        """Revoke a token."""
        raise NotImplementedError("Auth0 provider not yet implemented")
