"""
Integration tests for CaseService.

Tests the actual CaseService business logic without hitting HTTP endpoints.
Verifies case creation, updates, filtering, and status transitions.
"""

import pytest
from faultmaven.modules.case.service import CaseService
from faultmaven.modules.case.orm import CaseStatus, CasePriority
from tests.factories.user import UserFactory
from tests.factories.case import CaseFactory


@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_case_logic(db_session):
    """Test standard case creation through service layer."""
    # Create owner
    owner = await UserFactory.create_async(_session=db_session)
    await db_session.commit()

    # Create service
    service = CaseService(db_session=db_session)

    # Create case via service
    case = await service.create_case(
        owner_id=owner.id,
        title="Integration Test Case",
        description="Testing service layer case creation",
        priority=CasePriority.MEDIUM
    )

    # Verify case was created correctly
    assert case.id is not None
    assert case.title == "Integration Test Case"
    assert case.description == "Testing service layer case creation"
    assert case.status == CaseStatus.CONSULTING  # Initial status
    assert case.priority == CasePriority.MEDIUM
    assert case.owner_id == owner.id

    # Verify timestamps
    assert case.created_at is not None
    assert case.updated_at is not None
    assert case.resolved_at is None
    assert case.closed_at is None

    print("✅ Case creation logic works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_case_with_tags_and_category(db_session):
    """Test case creation with optional fields."""
    owner = await UserFactory.create_async(_session=db_session)
    await db_session.commit()

    service = CaseService(db_session=db_session)

    case = await service.create_case(
        owner_id=owner.id,
        title="Tagged Case",
        description="Case with metadata",
        priority=CasePriority.HIGH,
        tags=["production", "database", "performance"],
        category="infrastructure",
        context={"environment": "production", "region": "us-east-1"}
    )

    assert case.tags == ["production", "database", "performance"]
    assert case.category == "infrastructure"
    assert case.context == {"environment": "production", "region": "us-east-1"}
    assert case.priority == CasePriority.HIGH

    print("✅ Case creation with metadata works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_update_case_status_to_resolved(db_session):
    """Test status transition to RESOLVED sets resolved_at timestamp."""
    # Create case with factory
    case = await CaseFactory.create_with_owner(_session=db_session)
    await db_session.commit()

    service = CaseService(db_session=db_session)

    # Update status to RESOLVED
    updated_case = await service.update_case(
        case_id=case.id,
        user_id=case.owner_id,
        status=CaseStatus.RESOLVED
    )

    # Verify status changed
    assert updated_case is not None
    assert updated_case.status == CaseStatus.RESOLVED

    # Verify resolved_at timestamp was set
    assert updated_case.resolved_at is not None

    # Verify updated_at timestamp changed
    assert updated_case.updated_at > case.created_at

    print("✅ Status transition to RESOLVED works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_update_case_status_to_closed(db_session):
    """Test status transition to CLOSED sets closed_at timestamp."""
    case = await CaseFactory.create_with_owner(_session=db_session)
    await db_session.commit()

    service = CaseService(db_session=db_session)

    # Update status to CLOSED
    updated_case = await service.update_case(
        case_id=case.id,
        user_id=case.owner_id,
        status=CaseStatus.CLOSED
    )

    # Verify status changed
    assert updated_case.status == CaseStatus.CLOSED

    # Verify closed_at timestamp was set
    assert updated_case.closed_at is not None

    print("✅ Status transition to CLOSED works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_update_case_fields(db_session):
    """Test updating case title, description, priority."""
    case = await CaseFactory.create_with_owner(_session=db_session)
    await db_session.commit()

    service = CaseService(db_session=db_session)

    # Update multiple fields
    updated_case = await service.update_case(
        case_id=case.id,
        user_id=case.owner_id,
        title="Updated Title",
        description="Updated description",
        priority=CasePriority.CRITICAL,
        tags=["urgent", "production"],
        category="bug"
    )

    assert updated_case.title == "Updated Title"
    assert updated_case.description == "Updated description"
    assert updated_case.priority == CasePriority.CRITICAL
    assert updated_case.tags == ["urgent", "production"]
    assert updated_case.category == "bug"

    print("✅ Case field updates work")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_update_case_authorization(db_session):
    """Test that users can only update their own cases."""
    # Create case owned by user1
    case = await CaseFactory.create_with_owner(_session=db_session)
    await db_session.commit()

    # Create different user (user2)
    user2 = await UserFactory.create_async(_session=db_session)
    await db_session.commit()

    service = CaseService(db_session=db_session)

    # Try to update case as user2 (should fail)
    result = await service.update_case(
        case_id=case.id,
        user_id=user2.id,  # Different user
        title="Hacked Title"
    )

    # Should return None (unauthorized)
    assert result is None

    # Verify original case unchanged
    original = await service.get_case(case.id)
    assert original.title == case.title  # Not changed

    print("✅ Case update authorization works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_cases_filtering_by_status(db_session):
    """Test list filtering by status."""
    owner = await UserFactory.create_async(_session=db_session)
    await db_session.commit()

    # Create cases with different statuses
    await CaseFactory.create_with_owner(
        _session=db_session,
        owner=owner,
        status=CaseStatus.CONSULTING
    )
    await CaseFactory.create_with_owner(
        _session=db_session,
        owner=owner,
        status=CaseStatus.CONSULTING
    )
    await CaseFactory.create_with_owner(
        _session=db_session,
        owner=owner,
        status=CaseStatus.RESOLVED
    )
    await db_session.commit()

    service = CaseService(db_session=db_session)

    # Filter by CONSULTING
    consulting_cases, consulting_total = await service.list_cases(
        owner_id=owner.id,
        status=CaseStatus.CONSULTING
    )
    assert len(consulting_cases) == 2
    assert consulting_total == 2

    # Filter by RESOLVED
    resolved_cases, resolved_total = await service.list_cases(
        owner_id=owner.id,
        status=CaseStatus.RESOLVED
    )
    assert len(resolved_cases) == 1
    assert resolved_total == 1

    # No filter (all cases)
    all_cases, all_total = await service.list_cases(
        owner_id=owner.id
    )
    assert len(all_cases) == 3
    assert all_total == 3

    print("✅ Case filtering by status works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_cases_pagination(db_session):
    """Test list pagination."""
    owner = await UserFactory.create_async(_session=db_session)
    await db_session.commit()

    # Create 5 cases
    for i in range(5):
        await CaseFactory.create_with_owner(_session=db_session, owner=owner)
    await db_session.commit()

    service = CaseService(db_session=db_session)

    # Get first page (limit 2)
    page1, total = await service.list_cases(
        owner_id=owner.id,
        limit=2,
        offset=0
    )
    assert len(page1) == 2
    assert total == 5

    # Get second page (limit 2, offset 2)
    page2, total = await service.list_cases(
        owner_id=owner.id,
        limit=2,
        offset=2
    )
    assert len(page2) == 2
    assert total == 5

    # Get third page (limit 2, offset 4)
    page3, total = await service.list_cases(
        owner_id=owner.id,
        limit=2,
        offset=4
    )
    assert len(page3) == 1  # Only 1 remaining
    assert total == 5

    # Verify pages don't overlap
    page1_ids = {c.id for c in page1}
    page2_ids = {c.id for c in page2}
    page3_ids = {c.id for c in page3}

    assert len(page1_ids & page2_ids) == 0  # No overlap
    assert len(page2_ids & page3_ids) == 0  # No overlap

    print("✅ Case pagination works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_cases_owner_isolation(db_session):
    """Test that users only see their own cases."""
    user1 = await UserFactory.create_async(_session=db_session)
    user2 = await UserFactory.create_async(_session=db_session)
    await db_session.commit()

    # Create 2 cases for user1
    await CaseFactory.create_with_owner(_session=db_session, owner=user1)
    await CaseFactory.create_with_owner(_session=db_session, owner=user1)

    # Create 1 case for user2
    await CaseFactory.create_with_owner(_session=db_session, owner=user2)
    await db_session.commit()

    service = CaseService(db_session=db_session)

    # User1 should see only their 2 cases
    user1_cases, user1_total = await service.list_cases(owner_id=user1.id)
    assert len(user1_cases) == 2
    assert user1_total == 2

    # User2 should see only their 1 case
    user2_cases, user2_total = await service.list_cases(owner_id=user2.id)
    assert len(user2_cases) == 1
    assert user2_total == 1

    print("✅ Case owner isolation works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_case_by_id(db_session):
    """Test retrieving a single case by ID."""
    case = await CaseFactory.create_with_owner(_session=db_session)
    await db_session.commit()

    service = CaseService(db_session=db_session)

    # Get case by ID
    retrieved = await service.get_case(case.id)

    assert retrieved is not None
    assert retrieved.id == case.id
    assert retrieved.title == case.title

    # Get non-existent case
    not_found = await service.get_case("non-existent-id")
    assert not_found is None

    print("✅ Get case by ID works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_case_authorization(db_session):
    """Test that get_case enforces ownership when user_id provided."""
    case = await CaseFactory.create_with_owner(_session=db_session)
    user2 = await UserFactory.create_async(_session=db_session)
    await db_session.commit()

    service = CaseService(db_session=db_session)

    # Owner can get their case
    retrieved = await service.get_case(case.id, user_id=case.owner_id)
    assert retrieved is not None

    # Non-owner cannot get the case
    not_authorized = await service.get_case(case.id, user_id=user2.id)
    assert not_authorized is None

    print("✅ Get case authorization works")
