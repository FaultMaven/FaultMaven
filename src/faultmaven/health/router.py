"""
Enhanced health check endpoints.

Provides Kubernetes-compatible health probes and detailed
dependency health information.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request

from faultmaven.config import get_settings
from faultmaven.health.checker import HealthChecker, HealthStatus
from faultmaven.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """
    Basic health check.

    Returns 200 if the service is running.
    """
    return {"status": "healthy"}


@router.get("/live")
async def liveness_check():
    """
    Kubernetes liveness probe.

    Returns 200 if the application process is running.
    This should NOT check dependencies - only app process health.
    """
    return {
        "status": "alive",
        "service": "faultmaven",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/ready")
async def readiness_check(request: Request):
    """
    Kubernetes readiness probe.

    Returns 200 if the service is ready to receive traffic.
    Checks critical dependencies (database, cache).
    """
    # Get providers from app state
    redis_client = getattr(request.app.state, "redis_client", None)
    data_provider = getattr(request.app.state, "data_provider", None)

    checker = HealthChecker(
        redis_client=redis_client,
        data_provider=data_provider,
    )

    report = await checker.check_all(timeout=3.0)

    if report.is_healthy:
        return {
            "status": "ready",
            "service": "faultmaven",
            "checks": {c.name: c.status for c in report.components},
        }
    else:
        # Return 503 for not ready
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": "faultmaven",
                "checks": {c.name: c.status for c in report.components},
            },
        )


@router.get("/dependencies")
async def dependency_health(request: Request):
    """
    Detailed health check for all dependencies.

    Returns comprehensive health information including:
    - Database connectivity and latency
    - Redis connectivity and memory usage
    - LLM provider availability
    - Vector store status
    """
    # Get all providers from app state
    redis_client = getattr(request.app.state, "redis_client", None)
    data_provider = getattr(request.app.state, "data_provider", None)
    llm_provider = getattr(request.app.state, "llm_provider", None)
    vector_provider = getattr(request.app.state, "vector_provider", None)

    checker = HealthChecker(
        redis_client=redis_client,
        data_provider=data_provider,
        llm_provider=llm_provider,
        vector_provider=vector_provider,
    )

    report = await checker.check_all()

    logger.info(
        "dependency_health_check",
        status=report.status,
        component_count=len(report.components),
    )

    return {
        "status": report.status,
        "version": report.version,
        "timestamp": report.timestamp.isoformat(),
        "components": [
            {
                "name": c.name,
                "status": c.status,
                "response_time_ms": c.response_time_ms,
                "error": c.error,
                "metadata": c.metadata,
                "checked_at": c.checked_at.isoformat(),
            }
            for c in report.components
        ],
    }


@router.get("/config")
async def config_info(request: Request):
    """
    Configuration health check.

    Returns deployment configuration and feature flags.
    Does NOT expose secrets.
    """
    settings = get_settings()

    # Get validation issues
    issues = settings.validate_for_environment()

    return {
        "environment": settings.server.environment,
        "profile": settings.server.profile,
        "debug": settings.server.debug,
        "database_type": "postgresql" if settings.database.is_postgres else "sqlite",
        "llm_provider": settings.llm.provider,
        "configured_providers": settings.llm.get_configured_providers(),
        "feature_flags": settings.get_feature_flags(),
        "validation_issues": issues,
        "production_ready": len([i for i in issues if "CRITICAL" in i]) == 0,
    }


@router.get("/metrics")
async def metrics_summary(request: Request):
    """
    Basic metrics summary.

    For full Prometheus metrics, see /metrics endpoint (Phase 3).
    """
    # Get settings for uptime calculation
    settings = getattr(request.app.state, "settings", None)

    return {
        "service": "faultmaven",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": len(request.app.routes),
        "note": "Full Prometheus metrics available in Phase 3 (Observability)",
    }
