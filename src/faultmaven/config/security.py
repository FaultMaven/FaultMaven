"""Security settings."""

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecuritySettings(BaseSettings):
    """
    Security configuration.

    Manages JWT secrets, CORS, rate limiting, and PII handling.
    """

    model_config = SettingsConfigDict(env_prefix="SECURITY_")

    # JWT Configuration
    secret_key: SecretStr = Field(
        default=SecretStr("dev-secret-change-in-production"),
        description="Secret key for JWT signing (MUST change in production)",
    )
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=90)

    # Password hashing
    bcrypt_rounds: int = Field(default=12, ge=4, le=31)

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_requests: int = Field(default=100, ge=1, le=10000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)

    # PII Redaction (Phase 3)
    pii_redaction_enabled: bool = Field(default=False)
    pii_redaction_strict: bool = Field(default=False)

    # CORS (also configured in ServerSettings, but security-specific here)
    allowed_hosts: list[str] = Field(default=["*"])

    @field_validator("secret_key", mode="after")
    @classmethod
    def warn_default_secret(cls, v: SecretStr) -> SecretStr:
        """Warn if using default secret key."""
        # In production, this should raise an error
        # For now, just return the value
        return v

    @property
    def is_production_ready(self) -> bool:
        """Check if security settings are production-ready."""
        secret = self.secret_key.get_secret_value()
        return (
            secret != "dev-secret-change-in-production"
            and len(secret) >= 32
        )
