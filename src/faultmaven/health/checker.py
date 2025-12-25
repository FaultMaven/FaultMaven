"""
Health check implementation.

Provides structured health checking for all system dependencies.
"""

import asyncio
import time
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel

from faultmaven.logging_config import get_logger

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """Health status for a single component."""
    name: str
    status: HealthStatus
    response_time_ms: float | None = None
    error: str | None = None
    metadata: dict[str, Any] = {}
    checked_at: datetime = datetime.utcnow()

    class Config:
        use_enum_values = True


class HealthReport(BaseModel):
    """Complete health report for all components."""
    status: HealthStatus
    components: list[ComponentHealth]
    timestamp: datetime = datetime.utcnow()
    version: str = "0.1.0"

    class Config:
        use_enum_values = True

    @property
    def is_healthy(self) -> bool:
        """Check if overall status is healthy."""
        return self.status == HealthStatus.HEALTHY


class HealthChecker:
    """
    Health checker for system dependencies.

    Performs async health checks on all configured components
    and returns a comprehensive health report.
    """

    def __init__(
        self,
        redis_client=None,
        data_provider=None,
        llm_provider=None,
        vector_provider=None,
    ):
        self.redis_client = redis_client
        self.data_provider = data_provider
        self.llm_provider = llm_provider
        self.vector_provider = vector_provider

    async def check_all(self, timeout: float = 5.0) -> HealthReport:
        """
        Check health of all components.

        Args:
            timeout: Maximum time to wait for each check

        Returns:
            Complete health report
        """
        checks = []

        # Build list of checks to run
        if self.redis_client:
            checks.append(self._check_redis())
        if self.data_provider:
            checks.append(self._check_database())
        if self.llm_provider:
            checks.append(self._check_llm())
        if self.vector_provider:
            checks.append(self._check_vector())

        # Run all checks concurrently with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*checks, return_exceptions=True),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("health_check_timeout", timeout=timeout)
            results = [
                ComponentHealth(
                    name="timeout",
                    status=HealthStatus.UNHEALTHY,
                    error=f"Health checks timed out after {timeout}s",
                )
            ]

        # Process results
        components = []
        for result in results:
            if isinstance(result, Exception):
                components.append(
                    ComponentHealth(
                        name="unknown",
                        status=HealthStatus.UNHEALTHY,
                        error=str(result),
                    )
                )
            else:
                components.append(result)

        # Determine overall status
        statuses = [c.status for c in components]
        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall = HealthStatus.UNHEALTHY
        else:
            overall = HealthStatus.DEGRADED

        return HealthReport(
            status=overall,
            components=components,
        )

    async def _check_redis(self) -> ComponentHealth:
        """Check Redis connectivity."""
        start = time.perf_counter()

        try:
            await self.redis_client.ping()
            elapsed = (time.perf_counter() - start) * 1000

            # Get Redis info for metadata
            info = await self.redis_client.info()

            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                response_time_ms=round(elapsed, 2),
                metadata={
                    "used_memory": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "uptime_days": info.get("uptime_in_days"),
                },
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("redis_health_check_failed", error=str(e))
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=round(elapsed, 2),
                error=str(e),
            )

    async def _check_database(self) -> ComponentHealth:
        """Check database connectivity."""
        start = time.perf_counter()

        try:
            # Execute a simple query
            async with self.data_provider.session_factory() as session:
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))

            elapsed = (time.perf_counter() - start) * 1000

            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                response_time_ms=round(elapsed, 2),
                metadata={
                    "driver": "asyncpg" if "postgresql" in str(
                        self.data_provider.connection_string
                    ) else "aiosqlite",
                },
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("database_health_check_failed", error=str(e))
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=round(elapsed, 2),
                error=str(e),
            )

    async def _check_llm(self) -> ComponentHealth:
        """Check LLM provider availability."""
        start = time.perf_counter()

        try:
            # LLM providers may not have a health check, so just verify configured
            models = getattr(self.llm_provider, "get_available_models", None)
            elapsed = (time.perf_counter() - start) * 1000

            if models:
                available = models()
                return ComponentHealth(
                    name="llm_provider",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=round(elapsed, 2),
                    metadata={"available_models": len(available)},
                )
            else:
                # Provider exists but no model list method
                return ComponentHealth(
                    name="llm_provider",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=round(elapsed, 2),
                    metadata={"note": "Provider configured"},
                )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.warning("llm_health_check_failed", error=str(e))
            # LLM is not critical, so degraded not unhealthy
            return ComponentHealth(
                name="llm_provider",
                status=HealthStatus.DEGRADED,
                response_time_ms=round(elapsed, 2),
                error=str(e),
            )

    async def _check_vector(self) -> ComponentHealth:
        """Check vector store availability."""
        start = time.perf_counter()

        try:
            # Check if we can list collections
            collections = getattr(
                self.vector_provider, "list_collections", None
            )
            elapsed = (time.perf_counter() - start) * 1000

            if collections:
                count = len(collections())
                return ComponentHealth(
                    name="vector_store",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=round(elapsed, 2),
                    metadata={"collections": count},
                )
            else:
                return ComponentHealth(
                    name="vector_store",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=round(elapsed, 2),
                    metadata={"note": "Store configured"},
                )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.warning("vector_health_check_failed", error=str(e))
            # Vector store is not critical
            return ComponentHealth(
                name="vector_store",
                status=HealthStatus.DEGRADED,
                response_time_ms=round(elapsed, 2),
                error=str(e),
            )
