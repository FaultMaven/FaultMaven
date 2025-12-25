"""Redis settings."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseSettings):
    """
    Redis configuration for caching and session storage.

    Supports both URL-based and component-based configuration.
    """

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    # Connection (URL takes precedence)
    url: str | None = Field(
        default=None,
        description="Redis connection URL (overrides host/port/db)",
    )
    host: str = Field(default="localhost")
    port: int = Field(default=6379, ge=1, le=65535)
    db: int = Field(default=0, ge=0, le=15)
    password: SecretStr | None = Field(default=None)

    # Connection pool
    max_connections: int = Field(default=10, ge=1, le=100)
    socket_timeout: float = Field(default=5.0, ge=0.1, le=60.0)
    socket_connect_timeout: float = Field(default=5.0, ge=0.1, le=60.0)

    # Retry settings
    retry_on_timeout: bool = Field(default=True)

    @property
    def connection_url(self) -> str:
        """Get connection URL (constructed if not provided)."""
        if self.url:
            return self.url

        if self.password:
            return f"redis://:{self.password.get_secret_value()}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"
