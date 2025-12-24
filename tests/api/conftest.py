"""
Shared fixtures for API endpoint tests.

Adds additional fixtures beyond the root conftest.py for API-specific testing needs.
"""

import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport
from faultmaven.app import create_app
from faultmaven.dependencies import get_cache
from tests.utils.auth import create_access_token
from tests.factories.user import UserFactory


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
async def unauthenticated_client(db_session, mock_cache, mock_session_store, mock_file_provider, mock_vector_provider, mock_llm_provider, mock_knowledge_service_class):
    """
    Create HTTP client without authentication.

    Returns:
        AsyncClient without Authorization header
    """
    from tests.conftest import setup_test_app_state, setup_test_dependency_overrides

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


@pytest.fixture
async def second_user_client(db_session, mock_cache, mock_session_store, mock_file_provider, mock_vector_provider, mock_llm_provider, mock_knowledge_service_class):
    """
    Create HTTP client for a second user (for testing authorization).

    Returns:
        Tuple of (AsyncClient, User) - different user than authenticated_client
    """
    from tests.conftest import setup_test_app_state, setup_test_dependency_overrides

    # Create second test user
    user2 = await UserFactory.create_async(_session=db_session)
    await db_session.commit()

    # Generate JWT token
    token = create_access_token(user2.id)

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
        yield ac, user2

    # Clean up override
    app.dependency_overrides.clear()
