"""
Unified settings system with Pydantic validation.

This package provides type-safe, validated configuration management
using pydantic-settings. All settings are loaded from environment
variables with sensible defaults for development.

Usage:
    from faultmaven.config import get_settings

    settings = get_settings()
    db_url = settings.database.url
    llm_key = settings.llm.openai.api_key.get_secret_value()
"""

from faultmaven.config.settings import Settings, get_settings

__all__ = [
    "Settings",
    "get_settings",
]
