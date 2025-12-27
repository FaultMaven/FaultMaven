"""
Session API Endpoint Tests.

Tests the HTTP Contract for Session endpoints:
- POST /sessions - Create session
- GET /sessions - List sessions
- GET /sessions/{session_id} - Get session
- PATCH /sessions/{session_id} - Update session
- DELETE /sessions/{session_id} - Delete session
- DELETE /sessions - Delete all sessions
- POST /sessions/{session_id}/heartbeat - Session heartbeat
- POST /sessions/{session_id}/messages - Add message
- GET /sessions/{session_id}/messages - Get messages
- GET /sessions/{session_id}/cases - Get cases
- GET /sessions/{session_id}/stats - Get stats
- POST /sessions/search - Search sessions
- POST /sessions/{session_id}/archive - Archive session
- POST /sessions/{session_id}/restore - Restore session
- POST /sessions/cleanup - Cleanup sessions
- GET /sessions/{session_id}/recovery-info - Recovery info
- GET /sessions/health - Health check

Focus: Router logic, status codes, JSON schemas, authentication.
NOT testing: Redis session storage internals (covered in integration tests).
"""

import pytest
from httpx import AsyncClient


# ==============================================================================
# Create Session
# ==============================================================================

@pytest.mark.api
class TestSessionCreateEndpoint:
    """Test POST /sessions - Create session."""

    async def test_create_session_success(self, authenticated_client):
        """Test creating session returns 201 with session ID."""
        client, user = authenticated_client

        response = await client.post(
            "/sessions",
            json={"session_data": {"context": "test"}}
        )

        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert "message" in data
        assert "created" in data["message"].lower()

    async def test_create_session_minimal(self, authenticated_client):
        """Test creating session without session_data."""
        client, user = authenticated_client

        response = await client.post("/sessions", json={})

        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data

    async def test_create_session_unauthenticated(self, unauthenticated_client):
        """Test creating session without authentication returns 401."""
        client = unauthenticated_client

        response = await client.post("/sessions", json={})

        assert response.status_code == 401


# ==============================================================================
# List Sessions
# ==============================================================================

@pytest.mark.api
class TestSessionListEndpoint:
    """Test GET /sessions - List sessions."""

    async def test_list_sessions_success(self, authenticated_client):
        """Test listing sessions returns array."""
        client, user = authenticated_client

        # Create a session first
        await client.post("/sessions", json={})

        response = await client.get("/sessions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Check session structure
        if len(data) > 0:
            session = data[0]
            assert "session_id" in session
            assert "created_at" in session
            assert "last_accessed_at" in session
            assert "expires_at" in session

    async def test_list_sessions_empty(self, authenticated_client):
        """Test listing sessions when none exist returns empty array."""
        client, user = authenticated_client

        response = await client.get("/sessions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_list_sessions_unauthenticated(self, unauthenticated_client):
        """Test listing sessions without authentication returns 401."""
        client = unauthenticated_client

        response = await client.get("/sessions")

        assert response.status_code == 401


# ==============================================================================
# Get Session
# ==============================================================================

@pytest.mark.api
class TestSessionGetEndpoint:
    """Test GET /sessions/{session_id} - Get session."""

    async def test_get_session_success(self, authenticated_client):
        """Test getting session returns session data."""
        client, user = authenticated_client

        # Create session
        create_response = await client.post(
            "/sessions",
            json={"session_data": {"key": "value"}}
        )
        session_id = create_response.json()["session_id"]

        # Get session
        response = await client.get(f"/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data or "user_id" in data

    async def test_get_session_not_found(self, authenticated_client):
        """Test getting non-existent session returns 404."""
        client, user = authenticated_client

        response = await client.get("/sessions/non-existent-session-id")

        assert response.status_code == 404

    async def test_get_session_unauthorized(self, authenticated_client, second_user_client):
        """Test getting another user's session returns 403."""
        client, user1 = authenticated_client
        second_client, user2 = second_user_client

        # User 2 creates session
        create_response = await second_client.post("/sessions", json={})
        session_id = create_response.json()["session_id"]

        # User 1 tries to access it
        response = await client.get(f"/sessions/{session_id}")

        assert response.status_code in [403, 404]

    async def test_get_session_unauthenticated(self, unauthenticated_client):
        """Test getting session without authentication returns 401."""
        client = unauthenticated_client

        response = await client.get("/sessions/some-session-id")

        assert response.status_code == 401


# ==============================================================================
# Update Session
# ==============================================================================

@pytest.mark.api
class TestSessionUpdateEndpoint:
    """Test PATCH /sessions/{session_id} - Update session."""

    async def test_update_session_success(self, authenticated_client):
        """Test updating session returns success."""
        client, user = authenticated_client

        # Create session
        create_response = await client.post("/sessions", json={})
        session_id = create_response.json()["session_id"]

        # Update session
        response = await client.patch(
            f"/sessions/{session_id}",
            json={"updates": {"status": "active"}}
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "updated" in data["message"].lower()

    async def test_update_session_not_found(self, authenticated_client):
        """Test updating non-existent session returns 404."""
        client, user = authenticated_client

        response = await client.patch(
            "/sessions/non-existent-id",
            json={"updates": {"status": "active"}}
        )

        assert response.status_code == 404

    async def test_update_session_unauthorized(self, authenticated_client, second_user_client):
        """Test updating another user's session returns 403."""
        client, user1 = authenticated_client
        second_client, user2 = second_user_client

        # User 2 creates session
        create_response = await second_client.post("/sessions", json={})
        session_id = create_response.json()["session_id"]

        # User 1 tries to update it
        response = await client.patch(
            f"/sessions/{session_id}",
            json={"updates": {"status": "archived"}}
        )

        assert response.status_code in [403, 404]

    async def test_update_session_unauthenticated(self, unauthenticated_client):
        """Test updating session without authentication returns 401."""
        client = unauthenticated_client

        response = await client.patch(
            "/sessions/some-id",
            json={"updates": {}}
        )

        assert response.status_code == 401


# ==============================================================================
# Delete Session
# ==============================================================================

@pytest.mark.api
class TestSessionDeleteEndpoint:
    """Test DELETE /sessions/{session_id} - Delete session."""

    async def test_delete_session_success(self, authenticated_client):
        """Test deleting session returns success."""
        client, user = authenticated_client

        # Create session
        create_response = await client.post("/sessions", json={})
        session_id = create_response.json()["session_id"]

        # Delete session
        response = await client.delete(f"/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "deleted" in data["message"].lower()

        # Verify it's deleted
        get_response = await client.get(f"/sessions/{session_id}")
        assert get_response.status_code == 404

    async def test_delete_session_not_found(self, authenticated_client):
        """Test deleting non-existent session returns 404."""
        client, user = authenticated_client

        response = await client.delete("/sessions/non-existent-id")

        assert response.status_code == 404

    async def test_delete_session_unauthenticated(self, unauthenticated_client):
        """Test deleting session without authentication returns 401."""
        client = unauthenticated_client

        response = await client.delete("/sessions/some-id")

        assert response.status_code == 401


# ==============================================================================
# Delete All Sessions
# ==============================================================================

@pytest.mark.api
class TestSessionDeleteAllEndpoint:
    """Test DELETE /sessions - Delete all sessions."""

    async def test_delete_all_sessions_success(self, authenticated_client):
        """Test deleting all sessions returns count."""
        client, user = authenticated_client

        # Create multiple sessions
        await client.post("/sessions", json={})
        await client.post("/sessions", json={})

        # Delete all
        response = await client.delete("/sessions")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "count" in data

    async def test_delete_all_sessions_unauthenticated(self, unauthenticated_client):
        """Test deleting all sessions without authentication returns 401."""
        client = unauthenticated_client

        response = await client.delete("/sessions")

        assert response.status_code == 401


# ==============================================================================
# Session Heartbeat
# ==============================================================================

@pytest.mark.api
class TestSessionHeartbeatEndpoint:
    """Test POST /sessions/{session_id}/heartbeat - Session heartbeat."""

    async def test_heartbeat_success(self, authenticated_client):
        """Test heartbeat updates last activity."""
        client, user = authenticated_client

        # Create session
        create_response = await client.post("/sessions", json={})
        session_id = create_response.json()["session_id"]

        # Send heartbeat
        response = await client.post(f"/sessions/{session_id}/heartbeat")

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "last_activity_at" in data or "last_accessed_at" in data

    async def test_heartbeat_not_found(self, authenticated_client):
        """Test heartbeat for non-existent session returns 404."""
        client, user = authenticated_client

        response = await client.post("/sessions/non-existent-id/heartbeat")

        assert response.status_code == 404

    async def test_heartbeat_unauthenticated(self, unauthenticated_client):
        """Test heartbeat without authentication returns 401."""
        client = unauthenticated_client

        response = await client.post("/sessions/some-id/heartbeat")

        assert response.status_code == 401


# ==============================================================================
# Session Messages
# ==============================================================================

@pytest.mark.api
class TestSessionMessagesEndpoint:
    """Test session message endpoints."""

    async def test_add_message_success(self, authenticated_client):
        """Test adding message to session."""
        client, user = authenticated_client

        # Create session
        create_response = await client.post("/sessions", json={})
        session_id = create_response.json()["session_id"]

        # Add message
        response = await client.post(
            f"/sessions/{session_id}/messages",
            json={"role": "user", "content": "Hello"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "message" in data
        assert data["message"]["role"] == "user"
        assert data["message"]["content"] == "Hello"

    async def test_get_messages_success(self, authenticated_client):
        """Test getting session messages."""
        client, user = authenticated_client

        # Create session and add message
        create_response = await client.post("/sessions", json={})
        session_id = create_response.json()["session_id"]
        await client.post(
            f"/sessions/{session_id}/messages",
            json={"role": "user", "content": "Test message"}
        )

        # Get messages
        response = await client.get(f"/sessions/{session_id}/messages")

        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert "session_id" in data
        assert isinstance(data["messages"], list)

    async def test_get_messages_with_limit(self, authenticated_client):
        """Test getting messages with limit parameter."""
        client, user = authenticated_client

        # Create session
        create_response = await client.post("/sessions", json={})
        session_id = create_response.json()["session_id"]

        # Get messages with limit
        response = await client.get(f"/sessions/{session_id}/messages?limit=10")

        assert response.status_code == 200

    async def test_add_message_unauthenticated(self, unauthenticated_client):
        """Test adding message without authentication returns 401."""
        client = unauthenticated_client

        response = await client.post(
            "/sessions/some-id/messages",
            json={"role": "user", "content": "Hello"}
        )

        assert response.status_code == 401


# ==============================================================================
# Session Cases
# ==============================================================================

@pytest.mark.api
class TestSessionCasesEndpoint:
    """Test GET /sessions/{session_id}/cases - Get session cases."""

    async def test_get_session_cases_success(self, authenticated_client):
        """Test getting session cases returns array."""
        client, user = authenticated_client

        # Create session
        create_response = await client.post("/sessions", json={})
        session_id = create_response.json()["session_id"]

        # Get cases
        response = await client.get(f"/sessions/{session_id}/cases")

        assert response.status_code == 200
        data = response.json()
        assert "cases" in data
        assert "session_id" in data
        assert isinstance(data["cases"], list)

    async def test_get_session_cases_not_found(self, authenticated_client):
        """Test getting cases for non-existent session returns 404."""
        client, user = authenticated_client

        response = await client.get("/sessions/non-existent-id/cases")

        assert response.status_code == 404

    async def test_get_session_cases_unauthenticated(self, unauthenticated_client):
        """Test getting cases without authentication returns 401."""
        client = unauthenticated_client

        response = await client.get("/sessions/some-id/cases")

        assert response.status_code == 401


# ==============================================================================
# Session Stats
# ==============================================================================

@pytest.mark.api
class TestSessionStatsEndpoint:
    """Test GET /sessions/{session_id}/stats - Get session stats."""

    async def test_get_session_stats_success(self, authenticated_client):
        """Test getting session stats returns statistics."""
        client, user = authenticated_client

        # Create session
        create_response = await client.post("/sessions", json={})
        session_id = create_response.json()["session_id"]

        # Get stats
        response = await client.get(f"/sessions/{session_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "message_count" in data or "case_count" in data

    async def test_get_session_stats_not_found(self, authenticated_client):
        """Test getting stats for non-existent session returns 404."""
        client, user = authenticated_client

        response = await client.get("/sessions/non-existent-id/stats")

        assert response.status_code == 404

    async def test_get_session_stats_unauthenticated(self, unauthenticated_client):
        """Test getting stats without authentication returns 401."""
        client = unauthenticated_client

        response = await client.get("/sessions/some-id/stats")

        assert response.status_code == 401


# ==============================================================================
# Search Sessions
# ==============================================================================

@pytest.mark.api
class TestSessionSearchEndpoint:
    """Test POST /sessions/search - Search sessions."""

    async def test_search_sessions_success(self, authenticated_client):
        """Test searching sessions returns results."""
        client, user = authenticated_client

        response = await client.post(
            "/sessions/search",
            json={"status": "active"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data
        assert isinstance(data["sessions"], list)

    async def test_search_sessions_empty_query(self, authenticated_client):
        """Test searching with empty query."""
        client, user = authenticated_client

        response = await client.post("/sessions/search", json={})

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data

    async def test_search_sessions_with_pagination(self, authenticated_client):
        """Test searching with pagination parameters."""
        client, user = authenticated_client

        # Create some sessions first
        await client.post("/sessions", json={})
        await client.post("/sessions", json={})

        response = await client.post(
            "/sessions/search",
            json={"limit": 1, "offset": 0}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) <= 1

    async def test_search_sessions_invalid_status(self, authenticated_client):
        """Test searching with invalid status returns 422."""
        client, user = authenticated_client

        response = await client.post(
            "/sessions/search",
            json={"status": "invalid_status"}  # Not active/archived/expired
        )

        assert response.status_code == 422

    async def test_search_sessions_invalid_limit(self, authenticated_client):
        """Test searching with invalid limit returns 422."""
        client, user = authenticated_client

        response = await client.post(
            "/sessions/search",
            json={"limit": 1000}  # Max is 100
        )

        assert response.status_code == 422

    async def test_search_sessions_unauthenticated(self, unauthenticated_client):
        """Test searching without authentication returns 401."""
        client = unauthenticated_client

        response = await client.post("/sessions/search", json={})

        assert response.status_code == 401


# ==============================================================================
# Archive/Restore Session
# ==============================================================================

@pytest.mark.api
class TestSessionArchiveRestoreEndpoint:
    """Test archive and restore session endpoints."""

    async def test_archive_session_success(self, authenticated_client):
        """Test archiving session."""
        client, user = authenticated_client

        # Create session
        create_response = await client.post("/sessions", json={})
        session_id = create_response.json()["session_id"]

        # Archive it
        response = await client.post(f"/sessions/{session_id}/archive")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "archived"

    async def test_restore_session_success(self, authenticated_client):
        """Test restoring archived session."""
        client, user = authenticated_client

        # Create and archive session
        create_response = await client.post("/sessions", json={})
        session_id = create_response.json()["session_id"]
        await client.post(f"/sessions/{session_id}/archive")

        # Restore it
        response = await client.post(f"/sessions/{session_id}/restore")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

    async def test_archive_session_not_found(self, authenticated_client):
        """Test archiving non-existent session returns 404."""
        client, user = authenticated_client

        response = await client.post("/sessions/non-existent-id/archive")

        assert response.status_code == 404

    async def test_archive_session_unauthenticated(self, unauthenticated_client):
        """Test archiving without authentication returns 401."""
        client = unauthenticated_client

        response = await client.post("/sessions/some-id/archive")

        assert response.status_code == 401


# ==============================================================================
# Cleanup Sessions
# ==============================================================================

@pytest.mark.api
class TestSessionCleanupEndpoint:
    """Test POST /sessions/cleanup - Cleanup sessions."""

    async def test_cleanup_sessions_success(self, authenticated_client):
        """Test cleanup returns count of cleaned sessions."""
        client, user = authenticated_client

        response = await client.post("/sessions/cleanup")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "count" in data

    async def test_cleanup_sessions_unauthenticated(self, unauthenticated_client):
        """Test cleanup without authentication returns 401."""
        client = unauthenticated_client

        response = await client.post("/sessions/cleanup")

        assert response.status_code == 401


# ==============================================================================
# Recovery Info
# ==============================================================================

@pytest.mark.api
class TestSessionRecoveryInfoEndpoint:
    """Test GET /sessions/{session_id}/recovery-info - Get recovery info."""

    async def test_get_recovery_info_success(self, authenticated_client):
        """Test getting recovery info."""
        client, user = authenticated_client

        # Create session
        create_response = await client.post("/sessions", json={})
        session_id = create_response.json()["session_id"]

        # Get recovery info
        response = await client.get(f"/sessions/{session_id}/recovery-info")

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "can_recover" in data

    async def test_get_recovery_info_not_found(self, authenticated_client):
        """Test getting recovery info for non-existent session returns 404."""
        client, user = authenticated_client

        response = await client.get("/sessions/non-existent-id/recovery-info")

        assert response.status_code == 404

    async def test_get_recovery_info_unauthenticated(self, unauthenticated_client):
        """Test getting recovery info without authentication returns 401."""
        client = unauthenticated_client

        response = await client.get("/sessions/some-id/recovery-info")

        assert response.status_code == 401


# ==============================================================================
# Health Check
# ==============================================================================

@pytest.mark.api
class TestSessionHealthEndpoint:
    """Test GET /sessions/health - Health check."""

    async def test_health_check_success(self, unauthenticated_client):
        """Test health check returns 200 without authentication."""
        client = unauthenticated_client

        response = await client.get("/sessions/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "sessions"
