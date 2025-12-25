"""
Case API endpoint tests.

Tests HTTP layer behavior through FastAPI routers:
- Status codes (201, 200, 404, 401, 422)
- JSON response shapes
- Authentication/Authorization
- Request validation
"""

import pytest
from httpx import AsyncClient

from faultmaven.modules.case.orm import CaseStatus, CasePriority
from tests.factories.case import CaseFactory


@pytest.mark.api
class TestCaseCreateEndpoint:
    """Test POST /cases - Create case."""

    async def test_create_case_success(self, authenticated_client):
        """Test creating a case returns 201 with correct schema."""
        client, user = authenticated_client

        response = await client.post(
            "/cases",
            json={
                "title": "Payment Gateway Timeout",
                "description": "Users experiencing 30s timeout on checkout",
                "priority": "high",
                "tags": ["payment", "timeout"],
                "category": "infrastructure",
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response shape
        assert data["title"] == "Payment Gateway Timeout"
        assert data["description"] == "Users experiencing 30s timeout on checkout"
        assert data["priority"] == "high"
        assert data["status"] == "consulting"  # Initial status
        assert data["owner_id"] == user.id
        assert data["tags"] == ["payment", "timeout"]
        assert data["category"] == "infrastructure"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_case_minimal_fields(self, authenticated_client):
        """Test creating case with only required fields."""
        client, user = authenticated_client

        response = await client.post(
            "/cases",
            json={
                "title": "Bug Report",
                "description": "Something is broken",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Bug Report"
        assert data["priority"] == "medium"  # Default priority
        assert data["tags"] == []  # Default empty list

    async def test_create_case_unauthenticated(self, unauthenticated_client):
        """Test creating case without auth returns 401."""
        client = unauthenticated_client

        response = await client.post(
            "/cases",
            json={
                "title": "Test Case",
                "description": "Test description",
            },
        )

        assert response.status_code == 401

    async def test_create_case_validation_error(self, authenticated_client):
        """Test creating case with invalid data returns 422."""
        client, user = authenticated_client

        response = await client.post(
            "/cases",
            json={
                "title": "Test",
                # Missing required 'description' field
            },
        )

        assert response.status_code == 422


@pytest.mark.api
class TestCaseListEndpoint:
    """Test GET /cases - List cases."""

    async def test_list_cases_success(self, authenticated_client, db_session):
        """Test listing cases returns 200 with array of cases."""
        client, user = authenticated_client

        # Create test cases
        case1 = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user.id,
            title="First Case",
            status=CaseStatus.CONSULTING,
        )
        case2 = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user.id,
            title="Second Case",
            status=CaseStatus.INVESTIGATING,
        )
        await db_session.commit()

        response = await client.get("/cases")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 2

        # Verify cases are in response
        titles = [c["title"] for c in data]
        assert "First Case" in titles
        assert "Second Case" in titles

    async def test_list_cases_empty(self, authenticated_client):
        """Test listing cases when user has no cases."""
        client, user = authenticated_client

        response = await client.get("/cases")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_list_cases_status_filter(self, authenticated_client, db_session):
        """Test listing cases with status filter."""
        client, user = authenticated_client

        # Create cases with different statuses
        case1 = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user.id,
            title="Consulting Case",
            status=CaseStatus.CONSULTING,
        )
        case2 = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user.id,
            title="In Progress Case",
            status=CaseStatus.INVESTIGATING,
        )
        await db_session.commit()

        response = await client.get("/cases?status_filter=investigating")

        assert response.status_code == 200
        data = response.json()

        # Should only return INVESTIGATING cases
        assert len(data) >= 1
        for case in data:
            assert case["status"] == "investigating"

    async def test_list_cases_pagination(self, authenticated_client, db_session):
        """Test listing cases with pagination."""
        client, user = authenticated_client

        # Create multiple cases
        for i in range(5):
            await CaseFactory.create_async(
                _session=db_session,
                owner_id=user.id,
                title=f"Case {i}",
            )
        await db_session.commit()

        response = await client.get("/cases?limit=3&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 3

    async def test_list_cases_isolation(self, authenticated_client, second_user_client, db_session):
        """Test users can only see their own cases."""
        client1, user1 = authenticated_client
        client2, user2 = second_user_client

        # Create case for user1
        case1 = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user1.id,
            title="User 1 Case",
        )
        await db_session.commit()

        # User2 should not see User1's case
        response = await client2.get("/cases")
        assert response.status_code == 200
        data = response.json()

        titles = [c["title"] for c in data]
        assert "User 1 Case" not in titles

    async def test_list_cases_unauthenticated(self, unauthenticated_client):
        """Test listing cases without auth returns 401."""
        client = unauthenticated_client

        response = await client.get("/cases")

        assert response.status_code == 401


@pytest.mark.api
class TestCaseGetEndpoint:
    """Test GET /cases/{case_id} - Get case."""

    async def test_get_case_success(self, authenticated_client, db_session):
        """Test getting a case returns 200 with case details."""
        client, user = authenticated_client

        case = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user.id,
            title="Test Case",
            description="Test description",
            priority=CasePriority.HIGH,
        )
        await db_session.commit()

        response = await client.get(f"/cases/{case.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == case.id
        assert data["title"] == "Test Case"
        assert data["description"] == "Test description"
        assert data["priority"] == "high"
        assert data["owner_id"] == user.id

    async def test_get_case_not_found(self, authenticated_client):
        """Test getting non-existent case returns 404."""
        client, user = authenticated_client

        response = await client.get("/cases/non-existent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_get_case_unauthorized(self, authenticated_client, second_user_client, db_session):
        """Test getting another user's case returns 404."""
        client1, user1 = authenticated_client
        client2, user2 = second_user_client

        # Create case for user1
        case = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user1.id,
            title="User 1 Case",
        )
        await db_session.commit()

        # User2 tries to access User1's case
        response = await client2.get(f"/cases/{case.id}")

        assert response.status_code == 404  # Authorization treated as not found

    async def test_get_case_unauthenticated(self, unauthenticated_client):
        """Test getting case without auth returns 401."""
        client = unauthenticated_client

        response = await client.get("/cases/some-id")

        assert response.status_code == 401


@pytest.mark.api
class TestCaseUpdateEndpoint:
    """Test PATCH /cases/{case_id} - Update case."""

    async def test_update_case_success(self, authenticated_client, db_session):
        """Test updating a case returns 200 with updated data."""
        client, user = authenticated_client

        case = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user.id,
            title="Original Title",
            description="Original description",
            priority=CasePriority.MEDIUM,
        )
        await db_session.commit()

        response = await client.patch(
            f"/cases/{case.id}",
            json={
                "title": "Updated Title",
                "priority": "high",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["title"] == "Updated Title"
        assert data["priority"] == "high"
        assert data["description"] == "Original description"  # Unchanged

    async def test_update_case_status(self, authenticated_client, db_session):
        """Test updating case status."""
        client, user = authenticated_client

        case = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user.id,
            status=CaseStatus.CONSULTING,
        )
        await db_session.commit()

        response = await client.patch(
            f"/cases/{case.id}",
            json={"status": "investigating"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "investigating"

    async def test_update_case_not_found(self, authenticated_client):
        """Test updating non-existent case returns 404."""
        client, user = authenticated_client

        response = await client.patch(
            "/cases/non-existent-id",
            json={"title": "New Title"},
        )

        assert response.status_code == 404

    async def test_update_case_unauthorized(self, authenticated_client, second_user_client, db_session):
        """Test updating another user's case returns 404."""
        client1, user1 = authenticated_client
        client2, user2 = second_user_client

        # Create case for user1
        case = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user1.id,
            title="User 1 Case",
        )
        await db_session.commit()

        # User2 tries to update User1's case
        response = await client2.patch(
            f"/cases/{case.id}",
            json={"title": "Hacked"},
        )

        assert response.status_code == 404

    async def test_update_case_unauthenticated(self, unauthenticated_client):
        """Test updating case without auth returns 401."""
        client = unauthenticated_client

        response = await client.patch(
            "/cases/some-id",
            json={"title": "New Title"},
        )

        assert response.status_code == 401


@pytest.mark.api
class TestCaseDeleteEndpoint:
    """Test DELETE /cases/{case_id} - Delete case."""

    async def test_delete_case_success(self, authenticated_client, db_session):
        """Test deleting a case returns 204."""
        client, user = authenticated_client

        case = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user.id,
            title="Case to Delete",
        )
        await db_session.commit()

        response = await client.delete(f"/cases/{case.id}")

        assert response.status_code == 204

        # Verify case is gone
        get_response = await client.get(f"/cases/{case.id}")
        assert get_response.status_code == 404

    async def test_delete_case_not_found(self, authenticated_client):
        """Test deleting non-existent case returns 404."""
        client, user = authenticated_client

        response = await client.delete("/cases/non-existent-id")

        assert response.status_code == 404

    async def test_delete_case_unauthorized(self, authenticated_client, second_user_client, db_session):
        """Test deleting another user's case returns 404."""
        client1, user1 = authenticated_client
        client2, user2 = second_user_client

        # Create case for user1
        case = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user1.id,
            title="User 1 Case",
        )
        await db_session.commit()

        # User2 tries to delete User1's case
        response = await client2.delete(f"/cases/{case.id}")

        assert response.status_code == 404

        # Verify case still exists
        verify_response = await client1.get(f"/cases/{case.id}")
        assert verify_response.status_code == 200

    async def test_delete_case_unauthenticated(self, unauthenticated_client):
        """Test deleting case without auth returns 401."""
        client = unauthenticated_client

        response = await client.delete("/cases/some-id")

        assert response.status_code == 401


@pytest.mark.api
class TestCaseHypothesisEndpoint:
    """Test POST /cases/{case_id}/hypotheses - Add hypothesis."""

    async def test_add_hypothesis_success(self, authenticated_client, db_session):
        """Test adding hypothesis to case returns 201."""
        client, user = authenticated_client

        case = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user.id,
            title="Test Case",
        )
        await db_session.commit()

        response = await client.post(
            f"/cases/{case.id}/hypotheses",
            json={
                "title": "Database Connection Pool Exhausted",
                "description": "Application is running out of DB connections",
                "confidence": 0.75,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["title"] == "Database Connection Pool Exhausted"
        assert data["description"] == "Application is running out of DB connections"
        assert data["confidence"] == 0.75
        assert data["case_id"] == case.id
        assert data["validated"] is False
        assert "id" in data
        assert "created_at" in data

    async def test_add_hypothesis_case_not_found(self, authenticated_client):
        """Test adding hypothesis to non-existent case returns 404."""
        client, user = authenticated_client

        response = await client.post(
            "/cases/non-existent-id/hypotheses",
            json={
                "title": "Test Hypothesis",
                "description": "Test description",
            },
        )

        assert response.status_code == 404

    async def test_add_hypothesis_unauthorized(self, authenticated_client, second_user_client, db_session):
        """Test adding hypothesis to another user's case returns 404."""
        client1, user1 = authenticated_client
        client2, user2 = second_user_client

        # Create case for user1
        case = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user1.id,
            title="User 1 Case",
        )
        await db_session.commit()

        # User2 tries to add hypothesis
        response = await client2.post(
            f"/cases/{case.id}/hypotheses",
            json={
                "title": "Test Hypothesis",
                "description": "Test description",
            },
        )

        assert response.status_code == 404


@pytest.mark.api
class TestCaseSolutionEndpoint:
    """Test POST /cases/{case_id}/solutions - Add solution."""

    async def test_add_solution_success(self, authenticated_client, db_session):
        """Test adding solution to case returns 201."""
        client, user = authenticated_client

        case = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user.id,
            title="Test Case",
        )
        await db_session.commit()

        response = await client.post(
            f"/cases/{case.id}/solutions",
            json={
                "title": "Increase Connection Pool Size",
                "description": "Increase max_connections from 100 to 500",
                "implementation_steps": [
                    "Update database.yml",
                    "Deploy to staging",
                    "Monitor for 24h",
                    "Deploy to production",
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["title"] == "Increase Connection Pool Size"
        assert data["description"] == "Increase max_connections from 100 to 500"
        assert len(data["implementation_steps"]) == 4
        assert data["case_id"] == case.id
        assert data["implemented"] is False
        assert "id" in data

    async def test_add_solution_case_not_found(self, authenticated_client):
        """Test adding solution to non-existent case returns 404."""
        client, user = authenticated_client

        response = await client.post(
            "/cases/non-existent-id/solutions",
            json={
                "title": "Test Solution",
                "description": "Test description",
            },
        )

        assert response.status_code == 404


@pytest.mark.api
class TestCaseMessageEndpoint:
    """Test POST /cases/{case_id}/messages - Add message."""

    async def test_add_message_success(self, authenticated_client, db_session):
        """Test adding message to case returns 201."""
        client, user = authenticated_client

        case = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user.id,
            title="Test Case",
        )
        await db_session.commit()

        response = await client.post(
            f"/cases/{case.id}/messages",
            json={
                "role": "user",
                "content": "What could be causing the timeout?",
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["role"] == "user"
        assert data["content"] == "What could be causing the timeout?"
        assert data["case_id"] == case.id
        assert "id" in data
        assert "created_at" in data

    async def test_list_messages_success(self, authenticated_client, db_session):
        """Test listing messages returns 200 with array."""
        client, user = authenticated_client

        case = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user.id,
            title="Test Case",
        )
        await db_session.commit()

        # Add messages
        await client.post(
            f"/cases/{case.id}/messages",
            json={"role": "user", "content": "First message"},
        )
        await client.post(
            f"/cases/{case.id}/messages",
            json={"role": "assistant", "content": "Second message"},
        )

        # List messages
        response = await client.get(f"/cases/{case.id}/messages")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 2

    async def test_list_messages_case_not_found(self, authenticated_client):
        """Test listing messages for non-existent case returns 404."""
        client, user = authenticated_client

        response = await client.get("/cases/non-existent-id/messages")

        assert response.status_code == 404
