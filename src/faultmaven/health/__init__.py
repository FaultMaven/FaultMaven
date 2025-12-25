"""
Health check system for FaultMaven.

Provides comprehensive dependency health monitoring including:
- Database connectivity
- Redis connectivity
- LLM provider availability
- Vector store status

Usage:
    from faultmaven.health import HealthChecker, HealthStatus

    checker = HealthChecker(db, redis, llm_provider)
    report = await checker.check_all()
"""

from faultmaven.health.checker import (
    HealthChecker,
    HealthStatus,
    ComponentHealth,
)

__all__ = [
    "HealthChecker",
    "HealthStatus",
    "ComponentHealth",
]
