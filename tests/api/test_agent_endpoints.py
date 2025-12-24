"""
Agent API Endpoint Tests.

Tests the HTTP Contract for Agent endpoints:
- POST /agent/chat/{case_id} - Chat with AI assistant
- GET /agent/health - Health check

Focus: Router logic, status codes, JSON schemas, authentication.
NOT testing: AI response quality, RAG implementation (covered in integration tests).

NOTE: Agent chat endpoint tests that require full LLM provider mocking are skipped
in API contract tests. These are covered in integration tests instead.
"""

import pytest
from httpx import AsyncClient


# ==============================================================================
# Agent Chat - Basic Contract Tests
# ==============================================================================

@pytest.mark.api
class TestAgentChatEndpoint:
    """Test POST /agent/chat/{case_id} - Chat with AI assistant (basic HTTP contract)."""

    @pytest.mark.skip(reason="Agent service requires LLM provider mocking - covered in integration tests")
    async def test_chat_success(self, authenticated_client, db_session):
        """Test chat returns 200 with AI response."""
        # Skipped: Requires mocking LLM providers (OpenAI/Anthropic)
        # This is tested in integration tests with proper mocks
        pass

    @pytest.mark.skip(reason="Agent service requires LLM provider mocking - covered in integration tests")
    async def test_chat_without_rag(self, authenticated_client, db_session):
        """Test chat works without RAG."""
        # Skipped: Requires mocking LLM providers
        pass

    @pytest.mark.skip(reason="Agent service requires LLM provider mocking - covered in integration tests")
    async def test_chat_case_not_found(self, authenticated_client):
        """Test chat with non-existent case returns 404."""
        # Skipped: Requires mocking LLM providers
        pass

    @pytest.mark.skip(reason="Agent service requires LLM provider mocking - covered in integration tests")
    async def test_chat_unauthorized_case(self, authenticated_client, second_user_client, db_session):
        """Test chat with another user's case returns 404."""
        # Skipped: Requires mocking LLM providers
        pass

    async def test_chat_unauthenticated(self, unauthenticated_client):
        """Test chat without authentication returns 401."""
        client = unauthenticated_client

        response = await client.post(
            "/agent/chat/some-case-id",
            json={
                "message": "Hello",
                "stream": False
            }
        )

        assert response.status_code == 401

    @pytest.mark.skip(reason="Agent service requires LLM provider mocking - covered in integration tests")
    async def test_chat_streaming(self, authenticated_client, db_session):
        """Test chat with streaming returns streaming response."""
        # Skipped: Requires mocking LLM providers
        pass

    async def test_chat_validation_error(self, authenticated_client, db_session):
        """Test chat with missing message returns 422."""
        from tests.factories.case import CaseFactory

        client, user = authenticated_client

        case = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user.id
        )
        await db_session.commit()

        response = await client.post(
            f"/agent/chat/{case.id}",
            json={
                "stream": False
                # Missing required "message" field
            }
        )

        assert response.status_code == 422


# ==============================================================================
# Health Check
# ==============================================================================

@pytest.mark.api
class TestAgentHealthEndpoint:
    """Test GET /agent/health - Health check."""

    async def test_health_check_success(self, unauthenticated_client):
        """Test health check returns 200 without authentication."""
        client = unauthenticated_client

        response = await client.get("/agent/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "agent"
