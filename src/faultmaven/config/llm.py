"""LLM provider settings with multi-provider support."""

from typing import Literal
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAISettings(BaseSettings):
    """OpenAI configuration."""

    model_config = SettingsConfigDict(env_prefix="OPENAI_")

    api_key: SecretStr | None = Field(default=None)
    base_url: str | None = Field(default=None, description="Custom API endpoint")
    organization: str | None = Field(default=None)

    # Models
    chat_model: str = Field(default="gpt-4o-mini")
    embedding_model: str = Field(default="text-embedding-3-small")

    # Generation defaults
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    @property
    def is_configured(self) -> bool:
        """Check if API key is set."""
        return self.api_key is not None


class AnthropicSettings(BaseSettings):
    """Anthropic Claude configuration."""

    model_config = SettingsConfigDict(env_prefix="ANTHROPIC_")

    api_key: SecretStr | None = Field(default=None)
    base_url: str | None = Field(default=None)

    # Models
    chat_model: str = Field(default="claude-3-5-sonnet-20241022")

    # Generation defaults
    max_tokens: int = Field(default=4096, ge=1, le=200000)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)

    @property
    def is_configured(self) -> bool:
        """Check if API key is set."""
        return self.api_key is not None


class FireworksSettings(BaseSettings):
    """Fireworks AI configuration."""

    model_config = SettingsConfigDict(env_prefix="FIREWORKS_")

    api_key: SecretStr | None = Field(default=None)
    base_url: str = Field(default="https://api.fireworks.ai/inference/v1")

    # Models
    chat_model: str = Field(default="accounts/fireworks/models/llama-v3p1-70b-instruct")

    # Generation defaults
    max_tokens: int = Field(default=4096, ge=1, le=32000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    @property
    def is_configured(self) -> bool:
        """Check if API key is set."""
        return self.api_key is not None


class LLMSettings(BaseSettings):
    """
    LLM provider settings with multi-provider support and fallback.

    Supports automatic failover between providers when the primary fails.
    """

    model_config = SettingsConfigDict(env_prefix="LLM_")

    # Primary provider selection
    provider: Literal["openai", "anthropic", "fireworks"] = Field(
        default="openai",
        description="Primary LLM provider",
    )

    # Fallback chain (order matters)
    fallback_providers: list[str] = Field(
        default=["openai", "anthropic"],
        description="Fallback provider order when primary fails",
    )

    # Provider-specific settings
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    anthropic: AnthropicSettings = Field(default_factory=AnthropicSettings)
    fireworks: FireworksSettings = Field(default_factory=FireworksSettings)

    # Request configuration
    timeout: int = Field(default=30, ge=5, le=300)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay: float = Field(default=1.0, ge=0.1, le=10.0)

    # Task-specific provider overrides
    multimodal_provider: str | None = Field(
        default=None,
        description="Provider for multimodal tasks (vision)",
    )
    embedding_provider: str = Field(
        default="openai",
        description="Provider for embeddings",
    )

    @field_validator("fallback_providers", mode="before")
    @classmethod
    def parse_fallback_providers(cls, v):
        """Parse comma-separated string to list."""
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v or []

    def get_configured_providers(self) -> list[str]:
        """Get list of providers with API keys configured."""
        configured = []
        if self.openai.is_configured:
            configured.append("openai")
        if self.anthropic.is_configured:
            configured.append("anthropic")
        if self.fireworks.is_configured:
            configured.append("fireworks")
        return configured
