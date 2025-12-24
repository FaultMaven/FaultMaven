"""
Integration tests for EvidenceService.

Tests the actual EvidenceService business logic without hitting HTTP endpoints.
Verifies file upload metadata, retrieval, listing, and deletion.
"""

import pytest
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock
from faultmaven.modules.evidence.service import EvidenceService
from faultmaven.modules.evidence.orm import EvidenceType
from tests.factories.user import UserFactory
from tests.factories.case import CaseFactory
from tests.factories.evidence import EvidenceFactory


@pytest.mark.asyncio
@pytest.mark.integration
async def test_upload_evidence_metadata(db_session):
    """Test that uploading evidence creates correct DB record."""
    # Create user and case
    user = await UserFactory.create_async(_session=db_session)
    case = await CaseFactory.create_async(
        _session=db_session,
        owner_id=user.id
    )
    await db_session.commit()

    # Create mock file provider
    mock_file_provider = AsyncMock()
    mock_file_provider.upload = AsyncMock(return_value=None)

    service = EvidenceService(
        db_session=db_session,
        file_provider=mock_file_provider
    )

    # Create mock file content
    file_content = BytesIO(b"This is a test log file\nError occurred at line 42\n")

    # Upload evidence
    evidence = await service.upload_evidence(
        case_id=case.id,
        user_id=user.id,
        file_content=file_content,
        filename="db_crash.log",
        file_type="text/plain",
        file_size=2048,
        evidence_type=EvidenceType.LOG,
        description="Critical Database Log",
        tags=["database", "production"]
    )

    # Verify evidence was created
    assert evidence is not None
    assert evidence.id is not None
    assert evidence.case_id == case.id
    assert evidence.uploaded_by == user.id
    assert evidence.original_filename == "db_crash.log"
    assert evidence.file_type == "text/plain"
    assert evidence.file_size == 2048
    assert evidence.evidence_type == EvidenceType.LOG
    assert evidence.description == "Critical Database Log"
    assert evidence.tags == ["database", "production"]

    # Verify storage path was generated correctly
    assert evidence.storage_path.startswith(f"evidence/{case.id}/")
    assert evidence.storage_path.endswith(".log")

    # Verify file provider was called
    mock_file_provider.upload.assert_called_once()

    print("✅ Evidence upload metadata creation works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_upload_evidence_authorization(db_session):
    """Test that users can only upload evidence to their own cases."""
    # Create two users and cases
    user1 = await UserFactory.create_async(_session=db_session)
    user2 = await UserFactory.create_async(_session=db_session)
    case1 = await CaseFactory.create_async(
        _session=db_session,
        owner_id=user1.id
    )
    await db_session.commit()

    # Create mock file provider
    mock_file_provider = AsyncMock()

    service = EvidenceService(
        db_session=db_session,
        file_provider=mock_file_provider
    )

    file_content = BytesIO(b"test")

    # Try to upload evidence as user2 to user1's case (should fail)
    evidence = await service.upload_evidence(
        case_id=case1.id,
        user_id=user2.id,  # Different user
        file_content=file_content,
        filename="unauthorized.log",
        file_type="text/plain",
        file_size=100,
    )

    # Should return None (unauthorized)
    assert evidence is None

    # File provider should NOT have been called
    mock_file_provider.upload.assert_not_called()

    print("✅ Evidence upload authorization works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_case_evidence(db_session):
    """Verify we can retrieve evidence for a specific case."""
    user = await UserFactory.create_async(_session=db_session)
    case1 = await CaseFactory.create_async(
        _session=db_session,
        owner_id=user.id
    )
    case2 = await CaseFactory.create_async(
        _session=db_session,
        owner_id=user.id
    )
    await db_session.commit()

    # Create 2 files for Case 1, 1 file for Case 2
    await EvidenceFactory.create_async(
        _session=db_session,
        case_id=case1.id,
        uploaded_by=user.id
    )
    await EvidenceFactory.create_async(
        _session=db_session,
        case_id=case1.id,
        uploaded_by=user.id
    )
    await EvidenceFactory.create_async(
        _session=db_session,
        case_id=case2.id,
        uploaded_by=user.id
    )
    await db_session.commit()

    # Create mock file provider
    mock_file_provider = AsyncMock()

    service = EvidenceService(
        db_session=db_session,
        file_provider=mock_file_provider
    )

    # List evidence for case1
    results_c1 = await service.list_case_evidence(case1.id, user.id)
    assert results_c1 is not None
    evidence_list, total = results_c1
    assert len(evidence_list) == 2
    assert total == 2

    # List evidence for case2
    results_c2 = await service.list_case_evidence(case2.id, user.id)
    assert results_c2 is not None
    evidence_list, total = results_c2
    assert len(evidence_list) == 1
    assert total == 1

    print("✅ Case evidence listing works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_case_evidence_pagination(db_session):
    """Test evidence listing pagination."""
    user = await UserFactory.create_async(_session=db_session)
    case = await CaseFactory.create_async(
        _session=db_session,
        owner_id=user.id
    )
    await db_session.commit()

    # Create 5 evidence files
    for i in range(5):
        await EvidenceFactory.create_async(
            _session=db_session,
            case_id=case.id,
            uploaded_by=user.id,
            filename=f"file_{i}.log"
        )
    await db_session.commit()

    mock_file_provider = AsyncMock()
    service = EvidenceService(
        db_session=db_session,
        file_provider=mock_file_provider
    )

    # Get first page (limit 2)
    page1 = await service.list_case_evidence(case.id, user.id, limit=2, offset=0)
    assert page1 is not None
    evidence_list, total = page1
    assert len(evidence_list) == 2
    assert total == 5

    # Get second page
    page2 = await service.list_case_evidence(case.id, user.id, limit=2, offset=2)
    assert page2 is not None
    evidence_list, total = page2
    assert len(evidence_list) == 2
    assert total == 5

    print("✅ Evidence pagination works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_case_evidence_authorization(db_session):
    """Test that users can only list evidence for their own cases."""
    user1 = await UserFactory.create_async(_session=db_session)
    user2 = await UserFactory.create_async(_session=db_session)
    case1 = await CaseFactory.create_async(
        _session=db_session,
        owner_id=user1.id
    )
    await db_session.commit()

    await EvidenceFactory.create_async(
        _session=db_session,
        case_id=case1.id,
        uploaded_by=user1.id
    )
    await db_session.commit()

    mock_file_provider = AsyncMock()
    service = EvidenceService(
        db_session=db_session,
        file_provider=mock_file_provider
    )

    # Try to list evidence as user2 (should fail)
    result = await service.list_case_evidence(case1.id, user2.id)

    # Should return None (unauthorized)
    assert result is None

    print("✅ Evidence listing authorization works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_evidence(db_session):
    """Test retrieving single evidence by ID."""
    user = await UserFactory.create_async(_session=db_session)
    case = await CaseFactory.create_async(
        _session=db_session,
        owner_id=user.id
    )
    await db_session.commit()

    evidence = await EvidenceFactory.create_async(
        _session=db_session,
        case_id=case.id,
        uploaded_by=user.id,
        filename="important.log"
    )
    await db_session.commit()

    mock_file_provider = AsyncMock()
    service = EvidenceService(
        db_session=db_session,
        file_provider=mock_file_provider
    )

    # Get evidence by ID
    retrieved = await service.get_evidence(evidence.id, user.id)

    assert retrieved is not None
    assert retrieved.id == evidence.id
    assert retrieved.filename == "important.log"

    # Get non-existent evidence
    not_found = await service.get_evidence("non-existent-id", user.id)
    assert not_found is None

    print("✅ Get evidence by ID works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_evidence_authorization(db_session):
    """Test that users can only get evidence from their own cases."""
    user1 = await UserFactory.create_async(_session=db_session)
    user2 = await UserFactory.create_async(_session=db_session)
    case1 = await CaseFactory.create_async(
        _session=db_session,
        owner_id=user1.id
    )
    await db_session.commit()

    evidence = await EvidenceFactory.create_async(
        _session=db_session,
        case_id=case1.id,
        uploaded_by=user1.id
    )
    await db_session.commit()

    mock_file_provider = AsyncMock()
    service = EvidenceService(
        db_session=db_session,
        file_provider=mock_file_provider
    )

    # Owner can get evidence
    retrieved = await service.get_evidence(evidence.id, user1.id)
    assert retrieved is not None

    # Non-owner cannot get evidence
    not_authorized = await service.get_evidence(evidence.id, user2.id)
    assert not_authorized is None

    print("✅ Get evidence authorization works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_delete_evidence(db_session):
    """Test evidence deletion."""
    user = await UserFactory.create_async(_session=db_session)
    case = await CaseFactory.create_async(
        _session=db_session,
        owner_id=user.id
    )
    await db_session.commit()

    evidence = await EvidenceFactory.create_async(
        _session=db_session,
        case_id=case.id,
        uploaded_by=user.id
    )
    await db_session.commit()

    evidence_id = evidence.id
    storage_path = evidence.storage_path

    # Create mock file provider
    mock_file_provider = AsyncMock()
    mock_file_provider.delete = AsyncMock(return_value=None)

    service = EvidenceService(
        db_session=db_session,
        file_provider=mock_file_provider
    )

    # Delete evidence
    result = await service.delete_evidence(evidence_id, user.id)

    assert result is True

    # Verify file provider was called to delete file
    mock_file_provider.delete.assert_called_once_with(storage_path)

    # Verify evidence is gone from database
    found = await service.get_evidence(evidence_id, user.id)
    assert found is None

    print("✅ Evidence deletion works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_delete_evidence_authorization(db_session):
    """Test that users can only delete evidence from their own cases."""
    user1 = await UserFactory.create_async(_session=db_session)
    user2 = await UserFactory.create_async(_session=db_session)
    case1 = await CaseFactory.create_async(
        _session=db_session,
        owner_id=user1.id
    )
    await db_session.commit()

    evidence = await EvidenceFactory.create_async(
        _session=db_session,
        case_id=case1.id,
        uploaded_by=user1.id
    )
    await db_session.commit()

    mock_file_provider = AsyncMock()
    service = EvidenceService(
        db_session=db_session,
        file_provider=mock_file_provider
    )

    # Try to delete as user2 (should fail)
    result = await service.delete_evidence(evidence.id, user2.id)

    assert result is False

    # File provider should NOT have been called
    mock_file_provider.delete.assert_not_called()

    # Evidence should still exist
    found = await service.get_evidence(evidence.id, user1.id)
    assert found is not None

    print("✅ Evidence deletion authorization works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_download_evidence(db_session):
    """Test evidence file download."""
    user = await UserFactory.create_async(_session=db_session)
    case = await CaseFactory.create_async(
        _session=db_session,
        owner_id=user.id
    )
    await db_session.commit()

    evidence = await EvidenceFactory.create_async(
        _session=db_session,
        case_id=case.id,
        uploaded_by=user.id,
        filename="download_test.log"
    )
    await db_session.commit()

    # Create mock file provider that returns file content
    mock_file_content = BytesIO(b"Test file content")
    mock_file_provider = AsyncMock()
    mock_file_provider.download = AsyncMock(return_value=mock_file_content)

    service = EvidenceService(
        db_session=db_session,
        file_provider=mock_file_provider
    )

    # Download evidence
    result = await service.download_evidence(evidence.id, user.id)

    assert result is not None
    file_content, evidence_metadata = result

    # Verify file content
    assert file_content == mock_file_content

    # Verify metadata
    assert evidence_metadata.id == evidence.id
    assert evidence_metadata.filename == "download_test.log"

    # Verify file provider was called
    mock_file_provider.download.assert_called_once_with(evidence.storage_path)

    print("✅ Evidence download works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_evidence_type_categorization(db_session):
    """Test different evidence types are stored correctly."""
    user = await UserFactory.create_async(_session=db_session)
    case = await CaseFactory.create_async(
        _session=db_session,
        owner_id=user.id
    )
    await db_session.commit()

    # Create evidence of different types
    log_evidence = await EvidenceFactory.create_async(
        _session=db_session,
        case_id=case.id,
        uploaded_by=user.id,
        evidence_type=EvidenceType.LOG,
        filename="error.log"
    )

    screenshot_evidence = await EvidenceFactory.create_async(
        _session=db_session,
        case_id=case.id,
        uploaded_by=user.id,
        evidence_type=EvidenceType.SCREENSHOT,
        filename="error_screen.png",
        file_type="image/png"
    )

    config_evidence = await EvidenceFactory.create_async(
        _session=db_session,
        case_id=case.id,
        uploaded_by=user.id,
        evidence_type=EvidenceType.CONFIGURATION,
        filename="nginx.conf",
        file_type="text/plain"
    )

    await db_session.commit()

    # Verify types are correct
    assert log_evidence.evidence_type == EvidenceType.LOG
    assert screenshot_evidence.evidence_type == EvidenceType.SCREENSHOT
    assert config_evidence.evidence_type == EvidenceType.CONFIGURATION

    print("✅ Evidence type categorization works")
