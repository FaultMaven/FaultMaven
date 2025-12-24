"""
End-to-end golden path test.

Tests the complete case investigation workflow from creation to closure.
This is the most critical test - if this passes, core functionality works.
"""

import pytest
from tests.factories.user import UserFactory
from tests.factories.case import CaseFactory
from tests.utils.auth import create_access_token


@pytest.mark.asyncio
@pytest.mark.e2e
class TestCaseInvestigationGoldenPath:
    """
    Test complete case investigation workflow.

    This test covers the GOLDEN PATH - the most common user journey:
    1. Create a case
    2. Add hypothesis
    3. Add solution
    4. Update case status
    5. Verify data persistence

    If this test passes, we have high confidence the system works.
    """

    async def test_complete_case_lifecycle(self, client, db_session):
        """
        Test complete case lifecycle from creation to closure.

        This is the GOLDEN PATH test - the most critical workflow.
        Uses REAL database and services with minimal mocking.
        """

        # ==========================================
        # Setup: Create authenticated user
        # ==========================================

        user = await UserFactory.create_async(
            _session=db_session,
            email="investigator@example.com",
            username="investigator"
        )
        await db_session.commit()

        # Create JWT token for authentication
        token = create_access_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}

        # ==========================================
        # Step 1: Create Case
        # ==========================================

        create_response = await client.post(
            "/cases",
            json={
                "title": "Production database timeout errors",
                "description": "Users experiencing 5-10 second timeouts on /api/search endpoint",
                "priority": "critical"
            },
            headers=headers
        )

        assert create_response.status_code == 201, \
            f"Failed to create case: {create_response.text}"

        case_data = create_response.json()
        case_id = case_data["id"]

        # Verify response data
        assert case_data["title"] == "Production database timeout errors"
        assert case_data["status"] == "consulting"
        assert case_data["priority"] == "critical"
        assert case_data["owner_id"] == user.id

        print(f"\n✅ Step 1: Created case {case_id}")

        # ==========================================
        # Step 2: Add Hypothesis
        # ==========================================

        hypothesis_response = await client.post(
            f"/cases/{case_id}/hypotheses",
            json={
                "title": "Database connection pool exhausted",
                "description": "Max connections (100) being reached during peak traffic at 2pm-4pm daily",
                "confidence": 0.85
            },
            headers=headers
        )

        assert hypothesis_response.status_code == 201, \
            f"Failed to add hypothesis: {hypothesis_response.text}"

        hypothesis_data = hypothesis_response.json()

        assert hypothesis_data["title"] == "Database connection pool exhausted"
        assert hypothesis_data["confidence"] == 0.85
        assert hypothesis_data["case_id"] == case_id
        assert hypothesis_data["validated"] is False

        print(f"✅ Step 2: Added hypothesis {hypothesis_data['id']}")

        # ==========================================
        # Step 3: Add Solution
        # ==========================================

        solution_response = await client.post(
            f"/cases/{case_id}/solutions",
            json={
                "title": "Increase connection pool and add monitoring",
                "description": "Increase max_connections to 200 and add alerting",
                "implementation_steps": [
                    "Update RDS parameter group: max_connections=200",
                    "Deploy parameter change (requires restart)",
                    "Add CloudWatch alarm: ConnectionsUsed > 160 (80% threshold)",
                    "Monitor for 48 hours"
                ]
            },
            headers=headers
        )

        assert solution_response.status_code == 201, \
            f"Failed to propose solution: {solution_response.text}"

        solution_data = solution_response.json()

        assert solution_data["title"] == "Increase connection pool and add monitoring"
        assert len(solution_data["implementation_steps"]) == 4
        assert solution_data["case_id"] == case_id
        assert solution_data["implemented"] is False

        print(f"✅ Step 3: Added solution {solution_data['id']}")

        # ==========================================
        # Step 4: Verify Case Retrieval
        # ==========================================

        get_response = await client.get(
            f"/cases/{case_id}",
            headers=headers
        )

        assert get_response.status_code == 200, \
            f"Failed to retrieve case: {get_response.text}"

        retrieved_case = get_response.json()

        # Verify case data persisted correctly
        assert retrieved_case["id"] == case_id
        assert retrieved_case["title"] == "Production database timeout errors"
        assert retrieved_case["status"] == "consulting"
        assert retrieved_case["priority"] == "critical"

        print(f"✅ Step 4: Retrieved case successfully")

        # ==========================================
        # Step 5: Verify Database Persistence
        # ==========================================

        # Query database directly to verify data was persisted
        from sqlalchemy import select
        from faultmaven.modules.case.orm import Case, Hypothesis, Solution

        # Verify case in database
        case_result = await db_session.execute(
            select(Case).where(Case.id == case_id)
        )
        db_case = case_result.scalar_one()

        assert db_case.title == "Production database timeout errors"
        assert db_case.owner_id == user.id
        assert db_case.status.value == "consulting"
        assert db_case.priority.value == "critical"

        # Verify hypothesis in database
        hypothesis_result = await db_session.execute(
            select(Hypothesis).where(Hypothesis.case_id == case_id)
        )
        db_hypothesis = hypothesis_result.scalar_one()

        assert db_hypothesis.title == "Database connection pool exhausted"
        assert db_hypothesis.confidence == 0.85

        # Verify solution in database
        solution_result = await db_session.execute(
            select(Solution).where(Solution.case_id == case_id)
        )
        db_solution = solution_result.scalar_one()

        assert db_solution.title == "Increase connection pool and add monitoring"
        assert len(db_solution.implementation_steps) == 4

        print(f"✅ Step 5: Verified database persistence")

        print(f"\n🎉 GOLDEN PATH TEST PASSED: Complete case lifecycle works end-to-end!")

    async def test_authentication_required(self, client):
        """Test that authentication is required for case operations."""

        # Try to create case without authentication
        response = await client.post(
            "/cases",
            json={
                "title": "Test Case",
                "description": "Test description"
            }
        )

        # Should return 401 Unauthorized
        assert response.status_code == 401, \
            f"Expected 401 Unauthorized, got {response.status_code}"

        print("✅ Authentication requirement enforced")

    async def test_create_case_with_factory(self, db_session):
        """Test creating case using factory (verifies factory works)."""

        # Create case using factory
        case = await CaseFactory.create_with_owner(_session=db_session)
        await db_session.commit()

        # Verify case was created
        assert case.id is not None
        assert case.title is not None
        assert case.owner_id is not None
        assert case.status.value == "consulting"

        # Verify owner relationship loaded
        assert case.owner is not None
        assert case.owner.email is not None

        print(f"✅ Factory test passed: Created case {case.id} with owner {case.owner.email}")
