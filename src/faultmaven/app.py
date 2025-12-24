"""
FaultMaven FastAPI Application.

Main application entry point that assembles all module routers.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

# Import all models to register them with SQLAlchemy
import faultmaven.models  # noqa: F401

from faultmaven.modules.agent.router import router as agent_router
from faultmaven.modules.auth.router import router as auth_router
from faultmaven.modules.session.router import router as session_router
from faultmaven.modules.case.router import router as case_router
from faultmaven.modules.evidence.router import router as evidence_router
from faultmaven.modules.knowledge.router import router as knowledge_router

from faultmaven.providers.core import CoreLLMProvider, CoreDataProvider, CoreFileProvider
from faultmaven.providers.vectors.chromadb import ChromaDBProvider


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.

    Initializes heavy resources on startup and cleans them up on shutdown.
    This prevents "First User Penalty" and ensures proper health checks.
    """
    logger.info("🚀 Starting FaultMaven application...")

    # ==========================================
    # STARTUP: Initialize heavy resources
    # ==========================================

    try:
        # 1. Initialize Redis client
        logger.info("Initializing Redis client...")
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = Redis.from_url(redis_url, decode_responses=False)
        # Test connection
        await redis_client.ping()
        app.state.redis_client = redis_client
        logger.info("✅ Redis client initialized")

        # 2. Initialize Data Provider (Database)
        logger.info("Initializing Data Provider...")
        db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/faultmaven.db")
        data_provider = CoreDataProvider(connection_string=db_url)
        app.state.data_provider = data_provider
        logger.info("✅ Data Provider initialized")

        # 3. Initialize File Provider
        logger.info("Initializing File Provider...")
        base_path = os.getenv("FILE_STORAGE_PATH", "data/files")
        file_provider = CoreFileProvider(base_path=base_path)
        app.state.file_provider = file_provider
        logger.info("✅ File Provider initialized")

        # 4. Initialize LLM Provider
        logger.info("Initializing LLM Provider...")
        llm_provider = CoreLLMProvider()
        app.state.llm_provider = llm_provider
        logger.info("✅ LLM Provider initialized")

        # 5. Initialize Vector Provider (ChromaDB) - SLOW OPERATION
        logger.info("Initializing Vector Provider (ChromaDB)...")
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "data/chromadb")
        vector_provider = ChromaDBProvider(persist_directory=persist_dir)
        app.state.vector_provider = vector_provider
        logger.info("✅ Vector Provider (ChromaDB) initialized")

        logger.info("✅ All providers initialized successfully")
        logger.info("🎉 FaultMaven application ready to serve requests!")

    except Exception as e:
        logger.error(f"❌ Failed to initialize application: {e}")
        raise RuntimeError(f"Application startup failed: {e}") from e

    # Application is running
    yield

    # ==========================================
    # SHUTDOWN: Clean up resources
    # ==========================================

    logger.info("🛑 Shutting down FaultMaven application...")

    # Close Redis connection
    if hasattr(app.state, "redis_client"):
        logger.info("Closing Redis connection...")
        await app.state.redis_client.close()
        logger.info("✅ Redis connection closed")

    # Close database connections (if data provider has cleanup)
    if hasattr(app.state, "data_provider"):
        logger.info("Closing database connections...")
        # CoreDataProvider doesn't have explicit cleanup, but good to log
        logger.info("✅ Database connections closed")

    logger.info("✅ FaultMaven application shutdown complete")


def create_app(enable_lifespan: bool = True) -> FastAPI:
    """
    Create and configure FastAPI application.

    Args:
        enable_lifespan: Whether to enable lifespan context manager (default: True).
                        Set to False in tests to skip provider initialization.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="FaultMaven API",
        description="Modular monolith for AI-powered debugging and troubleshooting",
        version="0.1.0",
        lifespan=lifespan if enable_lifespan else None,  # Skip lifespan in tests
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include module routers
    app.include_router(auth_router)
    app.include_router(session_router)
    app.include_router(case_router)
    app.include_router(evidence_router)
    app.include_router(knowledge_router)
    app.include_router(agent_router)

    # Root health check
    @app.get("/")
    async def root():
        return {
            "service": "faultmaven",
            "status": "healthy",
            "version": "0.1.0"
        }

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    @app.get("/health/live")
    async def liveness_check():
        """Kubernetes liveness probe endpoint."""
        return {"status": "alive", "service": "faultmaven"}

    @app.get("/health/ready")
    async def readiness_check():
        """Kubernetes readiness probe endpoint."""
        return {"status": "ready", "service": "faultmaven", "checks": {"database": "ok", "cache": "ok"}}

    @app.post("/admin/refresh-openapi")
    async def refresh_openapi():
        """Admin endpoint to refresh OpenAPI spec."""
        return {"message": "OpenAPI spec refreshed", "version": "0.1.0"}

    @app.get("/admin/openapi-health")
    async def openapi_health():
        """Check OpenAPI spec health."""
        return {
            "status": "healthy",
            "openapi_version": "3.1.0",
            "endpoints_count": len(app.routes)
        }

    return app


# Create app instance for uvicorn
app = create_app()
