"""
Test configuration and shared fixtures.

This file provides the core testing infrastructure:
- Event loop configuration for async tests
- Database fixtures with transaction rollback (fast & isolated)
- HTTP client fixtures for API testing
"""

import pytest
import asyncio
import os
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from faultmaven.app import create_app
from faultmaven.database import Base
from faultmaven.dependencies import get_cache

# ==========================================
# 0. Test Environment Setup
# ==========================================

# Set SECRET_KEY for JWT token validation in tests
# This must match the secret key used in tests/utils/auth.py
os.environ["SECRET_KEY"] = "test-secret-key"

# Set fake API keys for provider initialization (won't be used in API tests)
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"
os.environ["ANTHROPIC_API_KEY"] = "sk-test-fake-key-for-testing"

# ==========================================
# 1. Event Loop Configuration
# ==========================================

# Note: Using pytest-asyncio's default function-scoped event loop behavior
# Session-scoped loops cause "Task attached to different loop" errors with
# function-scoped database fixtures


# ==========================================
# 2. Database Engine (Function Scope)
# ==========================================

@pytest.fixture(scope="function")
async def test_engine():
    """
    Test database engine (PostgreSQL) with strict per-test isolation.

    CRITICAL: Uses scope="function" + NullPool to prevent asyncio issues.

    This ensures the engine is created and destroyed within the specific
    event loop of the running test, preventing 'Task attached to different loop' errors.

    NullPool prevents the engine from keeping connections open after the test ends,
    which would cause connections to be bound to a closed event loop.

    Ensures clean slate:
    - Drops all tables at start
    - Creates all tables from ORM models
    - Drops all tables at end
    """
    # Get database URL from environment or use default test database
    # Note: Using port 5433 for test database to avoid conflicts
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://test:test@localhost:5433/faultmaven_test"
    )

    # For tests, always use the test database
    if "faultmaven_test" not in db_url:
        db_url = db_url.rsplit("/", 1)[0] + "/faultmaven_test"

    # Create engine with NullPool for strict per-test isolation
    # This ensures connections don't leak across tests/event loops
    engine = create_async_engine(
        db_url,
        echo=False,  # Set to True for SQL debugging
        future=True,
        poolclass=NullPool,  # No connection pooling - fresh connection per test
    )

    # Drop existing tables and create fresh schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup: Drop all tables after test session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# ==========================================
# 3. Database Session (Function Scope)
# ==========================================

@pytest.fixture(scope="function")
async def db_session(test_engine):
    """
    Database session with automatic transaction rollback.

    This is the MAGIC that makes tests fast and isolated:
    - Each test gets a clean database state
    - Changes are rolled back after each test
    - No need to truncate/drop tables between tests
    - Real PostgreSQL (foreign keys, constraints, JSONB)

    Usage:
        async def test_create_user(db_session):
            user = User(email="test@example.com")
            db_session.add(user)
            await db_session.flush()
            # Changes are automatically rolled back after test
    """
    # Create connection with transaction
    connection = await test_engine.connect()
    transaction = await connection.begin()

    # Create session bound to the connection
    session_factory = async_sessionmaker(
        bind=connection,
        expire_on_commit=False,
        class_=AsyncSession
    )

    async with session_factory() as session:
        yield session
        await session.rollback()  # Rollback any uncommitted changes

    # Rollback outer transaction and close connection
    await transaction.rollback()
    await connection.close()


# ==========================================
# 4. Mock Cache (Function Scope)
# ==========================================

@pytest.fixture(autouse=True)
def cleanup_app_overrides():
    """
    Automatically clean up FastAPI dependency overrides after EVERY test.

    This prevents test pollution where one test's mocked dependencies
    leak into subsequent tests, causing "Task attached to different loop" errors.

    Uses autouse=True to run for every test automatically.

    NOTE: This fixture is now a no-op because each test creates its own app instance
    via the client fixtures, and those app instances are properly cleaned up when the
    AsyncClient context manager exits. Keeping this fixture for documentation purposes
    and to maintain the autouse pattern for any future cleanup needs.
    """
    yield  # Test runs here
    # No cleanup needed - app.dependency_overrides.clear() is called by each client fixture


@pytest.fixture
def mock_cache():
    """
    Create a mock Redis cache for testing.

    Returns a mock that simulates a clean Redis state:
    - exists() -> False (token not blacklisted)
    - get() -> None (key not found)
    - set() -> True (success)
    - delete() -> True (success)
    """
    mock = AsyncMock()
    mock.exists = AsyncMock(return_value=False)  # Token not blacklisted
    mock.get = AsyncMock(return_value=None)      # Key doesn't exist
    mock.set = AsyncMock(return_value=True)      # Set succeeds
    mock.delete = AsyncMock(return_value=True)   # Delete succeeds
    return mock


@pytest.fixture
def mock_session_store():
    """
    Create an in-memory session store for testing.

    Returns a shared MemorySessionStore instance that persists
    across multiple API calls within the same test.
    """
    from faultmaven.infrastructure.memory_impl import MemorySessionStore
    return MemorySessionStore()


@pytest.fixture(scope="session")
def mock_file_provider_storage():
    """Shared storage dict for mock file provider (session-scoped)."""
    return {}


@pytest.fixture
def mock_file_provider(mock_file_provider_storage):
    """
    Mock file provider for storage operations.

    Prevents actual file I/O during API tests.
    Stores uploaded files in memory so they can be downloaded back.
    """
    from io import BytesIO

    # Clear storage for this test
    mock_file_provider_storage.clear()

    async def mock_upload(file_content, path):
        """Store file content in memory."""
        content = file_content.read()
        mock_file_provider_storage[path] = content
        return None

    async def mock_download(path):
        """Retrieve file content from memory."""
        content = mock_file_provider_storage.get(path, b"test content")  # Default if not found
        return BytesIO(content)

    async def mock_delete(path):
        """Remove file from memory."""
        mock_file_provider_storage.pop(path, None)
        return None

    mock = AsyncMock()
    mock.upload = AsyncMock(side_effect=mock_upload)
    mock.download = AsyncMock(side_effect=mock_download)
    mock.delete = AsyncMock(side_effect=mock_delete)
    return mock


@pytest.fixture
def mock_vector_provider():
    """
    Mock vector store for ChromaDB operations.

    Prevents real ChromaDB initialization which is slow (~5-10 seconds per test).
    """
    mock = AsyncMock()
    mock.add = AsyncMock(return_value=["vec_1", "vec_2"])
    mock.delete = AsyncMock(return_value=True)
    mock.search = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_llm_provider():
    """
    Mock LLM provider for embeddings and completions.

    Prevents real API calls to OpenAI/Anthropic.
    """
    mock = AsyncMock()
    # Return a fake 1536-dim vector (OpenAI ada-002 size)
    fake_embedding = [0.1] * 1536
    mock.embed = AsyncMock(return_value=fake_embedding)
    mock.complete = AsyncMock(return_value="Mock LLM response")
    return mock


@pytest.fixture
def mock_knowledge_service_class():
    """
    Create a test-aware KnowledgeService class that processes documents synchronously.

    This prevents background task cleanup issues during test teardown.
    """
    from faultmaven.modules.knowledge.service import KnowledgeService
    from typing import BinaryIO, Optional, Any
    from faultmaven.modules.knowledge.orm import DocumentType, Document

    class TestKnowledgeService(KnowledgeService):
        """Test version of KnowledgeService that always processes synchronously."""

        async def add_document(
            self,
            user_id: str,
            file_content: BinaryIO,
            filename: str,
            file_size: int,
            document_type: DocumentType = DocumentType.OTHER,
            title: Optional[str] = None,
            tags: Optional[list[str]] = None,
            metadata: Optional[dict[str, Any]] = None,
            process_sync: bool = True,  # Force sync in tests
        ) -> Document:
            """Override to force synchronous processing in tests."""
            return await super().add_document(
                user_id=user_id,
                file_content=file_content,
                filename=filename,
                file_size=file_size,
                document_type=document_type,
                title=title,
                tags=tags,
                metadata=metadata,
                process_sync=True,  # Always True for tests
            )

    return TestKnowledgeService


# ==========================================
# 5. HTTP Client (Function Scope)
# ==========================================

def setup_test_app_state(app, mock_cache, mock_file_provider, mock_vector_provider, mock_llm_provider, db_session):
    """
    Helper to populate app.state with test providers.

    Since tests don't go through the lifespan startup, we need to manually
    populate app.state with mock providers so that dependency functions
    can retrieve them from app.state.
    """
    from faultmaven.providers.core import CoreDataProvider
    from unittest.mock import Mock

    # Create a mock Redis client
    mock_redis = Mock()
    app.state.redis_client = mock_redis

    # Create a minimal DataProvider for tests (doesn't need real DB connection)
    # We override get_db_session anyway, but dependency functions expect this
    app.state.data_provider = Mock(spec=CoreDataProvider)
    app.state.data_provider.session_factory = lambda: db_session

    # Set mock providers
    app.state.file_provider = mock_file_provider
    app.state.vector_provider = mock_vector_provider
    app.state.llm_provider = mock_llm_provider


def setup_test_dependency_overrides(app, db_session, mock_cache, mock_session_store, mock_file_provider, mock_vector_provider, mock_llm_provider, mock_knowledge_service_class):
    """
    Helper to set up all FastAPI dependency overrides for tests.

    This ensures tests use mock providers and test-aware services.
    """
    from faultmaven.dependencies import (
        get_db_session, get_cache, get_session_store,
        get_file_provider, get_vector_provider, get_llm_provider, get_knowledge_service
    )

    # Override database session dependency to use test session
    async def override_get_db_session():
        yield db_session

    # Override cache dependency to use mock
    async def override_get_cache():
        return mock_cache

    # Override session store to use in-memory implementation
    def override_get_session_store():
        return mock_session_store

    # Override file provider to prevent real file I/O
    def override_get_file_provider():
        return mock_file_provider

    # Override vector provider to prevent real ChromaDB initialization
    def override_get_vector_provider():
        return mock_vector_provider

    # Override LLM provider to prevent real API calls
    def override_get_llm_provider():
        return mock_llm_provider

    # Override knowledge service to use test version (synchronous processing)
    def override_get_knowledge_service():
        return mock_knowledge_service_class(
            db_session=db_session,
            file_provider=mock_file_provider,
            vector_provider=mock_vector_provider,
            llm_provider=mock_llm_provider,
        )

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_cache] = override_get_cache
    app.dependency_overrides[get_session_store] = override_get_session_store
    app.dependency_overrides[get_file_provider] = override_get_file_provider
    app.dependency_overrides[get_vector_provider] = override_get_vector_provider
    app.dependency_overrides[get_llm_provider] = override_get_llm_provider
    app.dependency_overrides[get_knowledge_service] = override_get_knowledge_service


@pytest.fixture(scope="function")
async def client(db_session, mock_cache, mock_session_store, mock_file_provider, mock_vector_provider, mock_llm_provider, mock_knowledge_service_class):
    """
    HTTP client for testing FastAPI endpoints.

    Hits the FastAPI app in-memory (no network calls).
    Uses ASGI transport for direct app communication.

    IMPORTANT: Overrides get_db_session to use test database session.
    This ensures the client sees data created in tests.

    Usage:
        async def test_health_endpoint(client):
            response = await client.get("/health")
            assert response.status_code == 200
    """
    # Create app without lifespan to prevent Redis/ChromaDB initialization
    app = create_app(enable_lifespan=False)

    # Populate app.state with test providers (bypasses lifespan startup)
    setup_test_app_state(app, mock_cache, mock_file_provider, mock_vector_provider, mock_llm_provider, db_session)

    # Set up all dependency overrides (including test-aware knowledge service)
    setup_test_dependency_overrides(app, db_session, mock_cache, mock_session_store, mock_file_provider, mock_vector_provider, mock_llm_provider, mock_knowledge_service_class)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    # Clean up override
    app.dependency_overrides.clear()


# ==========================================
# 6. Authenticated Client (Function Scope)
# ==========================================

@pytest.fixture(scope="function")
async def authenticated_client(db_session, mock_cache, mock_session_store, mock_file_provider, mock_vector_provider, mock_llm_provider, mock_knowledge_service_class):
    """
    HTTP client with authenticated user.

    Creates a test user and provides both:
    - Authenticated client with Authorization header
    - The user object for test assertions

    Usage:
        async def test_create_case(authenticated_client):
            client, user = authenticated_client
            response = await client.post("/api/v1/cases", json={"title": "Test"})
            assert response.status_code == 201
    """
    from tests.factories.user import UserFactory
    from tests.utils.auth import create_access_token

    # Create test user
    user = await UserFactory.create_async(
        _session=db_session,
        email="testuser@faultmaven.com",
        username="testuser"
    )
    await db_session.commit()

    # Generate JWT token
    token = create_access_token(user.id)

    # Create app without lifespan to prevent Redis/ChromaDB initialization
    app = create_app(enable_lifespan=False)

    # Populate app.state with test providers (bypasses lifespan startup)
    setup_test_app_state(app, mock_cache, mock_file_provider, mock_vector_provider, mock_llm_provider, db_session)

    # Set up all dependency overrides (including test-aware knowledge service)
    setup_test_dependency_overrides(app, db_session, mock_cache, mock_session_store, mock_file_provider, mock_vector_provider, mock_llm_provider, mock_knowledge_service_class)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac, user

    # Clean up override
    app.dependency_overrides.clear()
