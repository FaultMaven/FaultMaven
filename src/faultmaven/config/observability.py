"""Observability settings (logging, metrics, tracing)."""

from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(env_prefix="LOG_")

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )
    format: Literal["json", "text"] = Field(
        default="json",
        description="Log format (json for production, text for development)",
    )
    include_request_id: bool = Field(default=True)
    include_user_id: bool = Field(default=True)
    redact_sensitive: bool = Field(default=True)

    # File logging (optional)
    file_path: str | None = Field(default=None)
    file_max_bytes: int = Field(default=10_000_000)  # 10MB
    file_backup_count: int = Field(default=5)


class MetricsSettings(BaseSettings):
    """Prometheus metrics configuration."""

    model_config = SettingsConfigDict(env_prefix="METRICS_")

    enabled: bool = Field(default=True)
    port: int = Field(default=9090, ge=1, le=65535)
    path: str = Field(default="/metrics")

    # Custom metrics
    track_llm_latency: bool = Field(default=True)
    track_db_latency: bool = Field(default=True)
    track_request_size: bool = Field(default=True)


class TracingSettings(BaseSettings):
    """Distributed tracing configuration (Opik/OpenTelemetry)."""

    model_config = SettingsConfigDict(env_prefix="TRACING_")

    enabled: bool = Field(default=False)
    provider: Literal["opik", "otlp", "none"] = Field(default="none")

    # Opik settings
    opik_api_key: str | None = Field(default=None)
    opik_project: str = Field(default="faultmaven")

    # OTLP settings
    otlp_endpoint: str | None = Field(default=None)
    otlp_insecure: bool = Field(default=False)

    # Sampling
    sample_rate: float = Field(default=1.0, ge=0.0, le=1.0)


class ObservabilitySettings(BaseSettings):
    """Combined observability settings."""

    model_config = SettingsConfigDict(env_prefix="")

    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
    tracing: TracingSettings = Field(default_factory=TracingSettings)
