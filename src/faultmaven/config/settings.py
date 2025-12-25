"""
Unified settings system with validation.

This module provides the root Settings class that aggregates all
subsystem configurations with Pydantic validation.

Usage:
    from faultmaven.config import get_settings

    settings = get_settings()
    print(settings.server.environment)
    print(settings.database.url)
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from faultmaven.config.database import DatabaseSettings
from faultmaven.config.redis import RedisSettings
from faultmaven.config.llm import LLMSettings
from faultmaven.config.storage import FileStorageSettings, VectorStoreSettings
from faultmaven.config.security import SecuritySettings
from faultmaven.config.observability import ObservabilitySettings


class ServerSettings(BaseSettings):
    """Server and deployment configuration."""

    model_config = SettingsConfigDict(env_prefix="SERVER_")

    # Server binding
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)

    # Environment
    environment: Literal["development", "staging", "production"] = Field(
        default="development"
    )
    debug: bool = Field(default=False)
    reload: bool = Field(default=False)
    workers: int = Field(default=1, ge=1, le=32)

    # Deployment profile
    profile: Literal["core", "team", "enterprise"] = Field(
        default="core",
        description="Feature profile (core/team/enterprise)",
    )

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"]
    )
    cors_allow_credentials: bool = Field(default=True)

    # Request limits
    max_request_size_mb: int = Field(default=100, ge=1, le=1000)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse comma-separated string to list."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v or []

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"


class Settings(BaseSettings):
    """
    Root settings object with all subsystems.

    This is the main configuration class that aggregates all settings.
    Use get_settings() to obtain a cached instance.

    Environment variables are loaded with the following patterns:
    - SERVER_PORT=8000 -> settings.server.port
    - DATABASE_URL=... -> settings.database.url
    - OPENAI_API_KEY=... -> settings.llm.openai.api_key
    - REDIS_HOST=... -> settings.redis.host
    """

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Subsystem settings
    server: ServerSettings = Field(default_factory=ServerSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    file_storage: FileStorageSettings = Field(default_factory=FileStorageSettings)
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    def validate_for_environment(self) -> list[str]:
        """
        Validate settings for current environment.

        Returns list of warnings/errors for production deployment.
        """
        issues = []

        if self.server.is_production:
            # Production-specific validations
            if not self.security.is_production_ready:
                issues.append(
                    "CRITICAL: Security secret_key is not production-ready"
                )

            if self.database.is_sqlite:
                issues.append(
                    "WARNING: SQLite is not recommended for production"
                )

            if self.server.debug:
                issues.append(
                    "WARNING: Debug mode should be disabled in production"
                )

            if not self.llm.get_configured_providers():
                issues.append(
                    "WARNING: No LLM providers configured"
                )

        return issues

    def get_feature_flags(self) -> dict[str, bool]:
        """Get feature flags based on deployment profile."""
        profile = self.server.profile

        return {
            # Core features (all profiles)
            "case_management": True,
            "knowledge_base": True,
            "agent_chat": True,

            # Team features
            "team_collaboration": profile in ("team", "enterprise"),
            "shared_knowledge_bases": profile in ("team", "enterprise"),
            "audit_logs": profile in ("team", "enterprise"),

            # Enterprise features
            "rbac": profile == "enterprise",
            "pii_redaction": profile == "enterprise",
            "sso_integration": profile == "enterprise",
            "advanced_analytics": profile == "enterprise",
        }


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Settings are loaded once and cached. To reload settings
    (e.g., after environment changes), call get_settings.cache_clear().

    Returns:
        Validated Settings instance
    """
    return Settings()


def clear_settings_cache() -> None:
    """Clear the settings cache to force reload."""
    get_settings.cache_clear()
