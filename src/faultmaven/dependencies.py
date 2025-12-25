"""
FastAPI dependency injection setup.

Provides centralized dependency management for services and providers.
"""

import os
from typing import AsyncGenerator

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from faultmaven.providers.core import CoreLLMProvider, CoreDataProvider, CoreFileProvider
from faultmaven.providers.vectors.chromadb import ChromaDBProvider
from faultmaven.infrastructure.redis_impl import RedisCache, RedisSessionStore, create_redis_client
from faultmaven.modules.agent.service import AgentService
from faultmaven.modules.auth.service import AuthService
from faultmaven.modules.session.service import SessionService
from faultmaven.modules.case.service import CaseService
from faultmaven.modules.case.investigation_service import InvestigationService
from faultmaven.modules.evidence.service import EvidenceService
from faultmaven.modules.knowledge.service import KnowledgeService
from faultmaven.modules.report.service import ReportService


# --- Redis (from app.state) ---

def get_redis_client(request: Request) -> Redis:
    """Get Redis client from app.state."""
    return request.app.state.redis_client


# --- Providers (from app.state) ---
# These are initialized during app startup via lifespan context manager

def get_llm_provider(request) -> CoreLLMProvider:
    """Get LLM provider from app.state."""
    return request.app.state.llm_provider


def get_data_provider(request) -> CoreDataProvider:
    """Get data provider from app.state."""
    return request.app.state.data_provider


def get_file_provider(request) -> CoreFileProvider:
    """Get file provider from app.state."""
    return request.app.state.file_provider


def get_vector_provider(request) -> ChromaDBProvider:
    """Get vector provider from app.state."""
    return request.app.state.vector_provider


# --- Infrastructure ---

async def get_cache(
    redis: Redis = Depends(get_redis_client)
) -> RedisCache:
    """Get cache (depends on Redis client)."""
    return RedisCache(redis=redis, prefix="cache:")


async def get_session_store(
    redis: Redis = Depends(get_redis_client)
) -> RedisSessionStore:
    """Get session store (depends on Redis client)."""
    return RedisSessionStore(redis=redis, prefix="session:")


# --- Database Session ---

async def get_db_session(
    data_provider: CoreDataProvider = Depends(get_data_provider),
) -> AsyncGenerator[AsyncSession, None]:
    """Get database session from data provider."""
    session = data_provider.session_factory()
    try:
        yield session
    finally:
        await session.close()


# --- Services ---

def get_auth_service(
    db_session: AsyncSession = Depends(get_db_session),
    cache: RedisCache = Depends(get_cache),
) -> AuthService:
    """
    Get auth service.

    FastAPI automatically resolves db_session and cache before calling this.
    """
    secret_key = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    return AuthService(
        db_session=db_session,
        cache=cache,
        secret_key=secret_key,
    )


def get_session_service(
    db_session: AsyncSession = Depends(get_db_session),
    session_store: RedisSessionStore = Depends(get_session_store),
) -> SessionService:
    """Get session service."""
    return SessionService(
        db_session=db_session,
        session_store=session_store,
    )


def get_case_service(
    db_session: AsyncSession = Depends(get_db_session),
) -> CaseService:
    """Get case service."""
    return CaseService(
        db_session=db_session,
    )


def get_evidence_service(
    db_session: AsyncSession = Depends(get_db_session),
    file_provider: CoreFileProvider = Depends(get_file_provider),
) -> EvidenceService:
    """Get evidence service."""
    return EvidenceService(
        db_session=db_session,
        file_provider=file_provider,
    )


def get_knowledge_service(
    db_session: AsyncSession = Depends(get_db_session),
    file_provider: CoreFileProvider = Depends(get_file_provider),
    vector_provider: ChromaDBProvider = Depends(get_vector_provider),
    llm_provider: CoreLLMProvider = Depends(get_llm_provider),
) -> KnowledgeService:
    """Get knowledge service."""
    return KnowledgeService(
        db_session=db_session,
        file_provider=file_provider,
        vector_provider=vector_provider,
        llm_provider=llm_provider,
    )


def get_investigation_service(
    db_session: AsyncSession = Depends(get_db_session),
    case_service: CaseService = Depends(get_case_service),
) -> InvestigationService:
    """Get investigation service for milestone-based tracking."""
    return InvestigationService(
        db_session=db_session,
        case_service=case_service,
    )


def get_report_service(
    db_session: AsyncSession = Depends(get_db_session),
    case_service: CaseService = Depends(get_case_service),
    llm_provider: CoreLLMProvider = Depends(get_llm_provider),
) -> ReportService:
    """Get report service for generation and management."""
    return ReportService(
        db_session=db_session,
        case_service=case_service,
        llm_provider=llm_provider,
    )


def get_agent_service(
    llm_provider: CoreLLMProvider = Depends(get_llm_provider),
    case_service: CaseService = Depends(get_case_service),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> AgentService:
    """Get agent service."""
    return AgentService(
        llm_provider=llm_provider,
        case_service=case_service,
        knowledge_service=knowledge_service,
    )
