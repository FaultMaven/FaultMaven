"""Database settings."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """
    Database configuration.

    Supports PostgreSQL (production) and SQLite (development).
    Connection pooling is configured for async SQLAlchemy.
    """

    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    # Connection
    url: str = Field(
        default="sqlite+aiosqlite:///data/faultmaven.db",
        description="Database connection URL (async driver required)",
    )

    # Connection pool settings
    pool_size: int = Field(default=5, ge=1, le=50)
    max_overflow: int = Field(default=10, ge=0, le=100)
    pool_timeout: int = Field(default=30, ge=5, le=300)
    pool_recycle: int = Field(default=1800, ge=60, le=7200)

    # Echo SQL (debug only)
    echo: bool = Field(default=False)

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure async driver is used."""
        if v and "sqlite:" in v and "aiosqlite" not in v:
            # Auto-convert to async driver
            return v.replace("sqlite:", "sqlite+aiosqlite:")
        if v and "postgresql:" in v and "asyncpg" not in v:
            return v.replace("postgresql:", "postgresql+asyncpg:")
        return v

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite."""
        return "sqlite" in self.url.lower()

    @property
    def is_postgres(self) -> bool:
        """Check if using PostgreSQL."""
        return "postgresql" in self.url.lower()
