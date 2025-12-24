"""
Integration tests for KnowledgeService.

Tests the actual KnowledgeService business logic without hitting HTTP endpoints.
Verifies document ingestion, search, and deletion with mocked vector store and LLM provider.
"""

import pytest
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock
from faultmaven.modules.knowledge.service import KnowledgeService
from faultmaven.modules.knowledge.orm import DocumentType, DocumentStatus
from tests.factories.user import UserFactory
from tests.factories.document import DocumentFactory


@pytest.fixture
def mock_file_provider():
    """Mock file provider for storage operations."""
    provider = AsyncMock()
    provider.upload = AsyncMock(return_value=None)
    provider.delete = AsyncMock(return_value=None)
    provider.download = AsyncMock(return_value=BytesIO(b"test content"))
    return provider


@pytest.fixture
def mock_vector_provider():
    """Mock vector store for ChromaDB/Pinecone operations."""
    provider = AsyncMock()
    # Async methods need AsyncMock
    provider.add = AsyncMock(return_value=["vec_1", "vec_2"])
    provider.delete = AsyncMock(return_value=True)
    provider.search = AsyncMock(return_value=[])
    return provider


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for embeddings."""
    provider = AsyncMock()
    # Return a fake 1536-dim vector (OpenAI ada-002 size)
    fake_embedding = [0.1] * 1536
    provider.embed = AsyncMock(return_value=fake_embedding)
    return provider


@pytest.mark.asyncio
@pytest.mark.integration
async def test_add_document_flow(
    db_session,
    mock_file_provider,
    mock_vector_provider,
    mock_llm_provider,
    monkeypatch
):
    """Test that adding a document creates DB record and uploads file."""
    user = await UserFactory.create_async(_session=db_session)
    await db_session.commit()

    # Mock asyncio.create_task to prevent background processing during test
    mock_create_task = MagicMock()
    monkeypatch.setattr("asyncio.create_task", mock_create_task)

    # Initialize Service with Mocks
    service = KnowledgeService(
        db_session=db_session,
        file_provider=mock_file_provider,
        vector_provider=mock_vector_provider,
        llm_provider=mock_llm_provider
    )

    # Create mock file content
    file_content = BytesIO(b"Step 1: Run docker-compose up\nStep 2: Check logs")

    # Act
    doc = await service.add_document(
        user_id=user.id,
        file_content=file_content,
        filename="deployment.txt",
        file_size=50,
        document_type=DocumentType.TXT,
        title="Deployment Runbook",
        tags=["deployment", "docker"]
    )

    # Assert - Database Side
    assert doc.id is not None
    assert doc.title == "Deployment Runbook"
    assert doc.filename == "deployment.txt"
    assert doc.status == DocumentStatus.PENDING  # Starts as PENDING
    assert doc.uploaded_by == user.id
    assert doc.tags == ["deployment", "docker"]

    # Assert - File Provider Side
    mock_file_provider.upload.assert_called_once()
    upload_call = mock_file_provider.upload.call_args
    assert upload_call.kwargs["path"].startswith(f"documents/{user.id}/")

    # Assert - Background Task Side (asyncio.create_task called)
    mock_create_task.assert_called_once()
    # Verify the coroutine passed to create_task is process_document
    call_args = mock_create_task.call_args[0][0]
    assert hasattr(call_args, '__name__') or str(call_args).startswith('<coroutine')

    print("✅ Document ingestion flow works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_knowledge_logic(
    db_session,
    mock_file_provider,
    mock_vector_provider,
    mock_llm_provider
):
    """Test that searching converts query to vector and queries Vector Store."""
    service = KnowledgeService(
        db_session=db_session,
        file_provider=mock_file_provider,
        vector_provider=mock_vector_provider,
        llm_provider=mock_llm_provider
    )

    # Setup Mock Search Result
    # The VectorStore usually returns a list of dicts with id, score, content
    mock_vector_provider.search.return_value = [
        {"id": "doc_1", "score": 0.9, "content": "Run docker-compose up", "metadata": {}},
        {"id": "doc_2", "score": 0.7, "content": "Check application logs", "metadata": {}}
    ]

    # Act
    results = await service.search_knowledge("How do I deploy?")

    # Verify flow
    mock_llm_provider.embed.assert_called_once_with("How do I deploy?")
    mock_vector_provider.search.assert_called_once()

    # Check search was called with correct parameters
    search_call = mock_vector_provider.search.call_args
    assert search_call.kwargs["collection"] == "knowledge"
    assert search_call.kwargs["top_k"] == 10  # default limit
    assert len(search_call.kwargs["vector"]) == 1536  # embedding size

    # Verify results
    assert results["query"] == "How do I deploy?"
    assert len(results["results"]) == 2
    assert results["results"][0]["content"] == "Run docker-compose up"
    assert results["total"] == 2
    assert "latency_ms" in results

    print("✅ Knowledge search logic works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_knowledge_with_filters(
    db_session,
    mock_file_provider,
    mock_vector_provider,
    mock_llm_provider
):
    """Test that search applies filters correctly."""
    user = await UserFactory.create_async(_session=db_session)
    await db_session.commit()

    service = KnowledgeService(
        db_session=db_session,
        file_provider=mock_file_provider,
        vector_provider=mock_vector_provider,
        llm_provider=mock_llm_provider
    )

    mock_vector_provider.search.return_value = []

    # Search with user filter
    await service.search_knowledge(
        "deployment guide",
        user_id=user.id,
        filters={"case_id": "case_123"},
        limit=5
    )

    # Verify filters were passed correctly
    search_call = mock_vector_provider.search.call_args
    filters = search_call.kwargs["filter"]
    assert filters["user_id"] == user.id
    assert filters["case_id"] == "case_123"
    assert search_call.kwargs["top_k"] == 5

    print("✅ Search filtering works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_document(
    db_session,
    mock_file_provider,
    mock_vector_provider,
    mock_llm_provider
):
    """Test retrieving a document by ID."""
    user = await UserFactory.create_async(_session=db_session)
    await db_session.commit()

    document = await DocumentFactory.create_async(
        _session=db_session,
        uploaded_by=user.id,
        title="Architecture Guide"
    )
    await db_session.commit()

    service = KnowledgeService(
        db_session=db_session,
        file_provider=mock_file_provider,
        vector_provider=mock_vector_provider,
        llm_provider=mock_llm_provider
    )

    # Get document
    retrieved = await service.get_document(document.id)

    assert retrieved is not None
    assert retrieved.id == document.id
    assert retrieved.title == "Architecture Guide"

    # Verify last_accessed_at was updated
    assert retrieved.last_accessed_at is not None

    # Get non-existent document
    not_found = await service.get_document("non-existent-id")
    assert not_found is None

    print("✅ Get document works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_document_with_authorization(
    db_session,
    mock_file_provider,
    mock_vector_provider,
    mock_llm_provider
):
    """Test that get_document enforces ownership when user_id provided."""
    user1 = await UserFactory.create_async(_session=db_session)
    user2 = await UserFactory.create_async(_session=db_session)
    await db_session.commit()

    document = await DocumentFactory.create_async(
        _session=db_session,
        uploaded_by=user1.id
    )
    await db_session.commit()

    service = KnowledgeService(
        db_session=db_session,
        file_provider=mock_file_provider,
        vector_provider=mock_vector_provider,
        llm_provider=mock_llm_provider
    )

    # Owner can get document
    retrieved = await service.get_document(document.id, user_id=user1.id)
    assert retrieved is not None

    # Non-owner cannot get document when user_id filter applied
    not_authorized = await service.get_document(document.id, user_id=user2.id)
    assert not_authorized is None

    print("✅ Get document authorization works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_documents(
    db_session,
    mock_file_provider,
    mock_vector_provider,
    mock_llm_provider
):
    """Test listing documents with filtering."""
    user = await UserFactory.create_async(_session=db_session)
    await db_session.commit()

    # Create documents with different statuses
    await DocumentFactory.create_async(
        _session=db_session,
        uploaded_by=user.id,
        status=DocumentStatus.INDEXED
    )
    await DocumentFactory.create_async(
        _session=db_session,
        uploaded_by=user.id,
        status=DocumentStatus.INDEXED
    )
    await DocumentFactory.create_async(
        _session=db_session,
        uploaded_by=user.id,
        status=DocumentStatus.PENDING
    )
    await db_session.commit()

    service = KnowledgeService(
        db_session=db_session,
        file_provider=mock_file_provider,
        vector_provider=mock_vector_provider,
        llm_provider=mock_llm_provider
    )

    # List all documents for user
    all_docs, total = await service.list_documents(user_id=user.id)
    assert len(all_docs) == 3
    assert total == 3

    # Filter by INDEXED status
    indexed_docs, indexed_total = await service.list_documents(
        user_id=user.id,
        status=DocumentStatus.INDEXED
    )
    assert len(indexed_docs) == 2
    assert indexed_total == 2

    # Filter by PENDING status
    pending_docs, pending_total = await service.list_documents(
        user_id=user.id,
        status=DocumentStatus.PENDING
    )
    assert len(pending_docs) == 1
    assert pending_total == 1

    print("✅ List documents with filtering works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_list_documents_pagination(
    db_session,
    mock_file_provider,
    mock_vector_provider,
    mock_llm_provider
):
    """Test document listing pagination."""
    user = await UserFactory.create_async(_session=db_session)
    await db_session.commit()

    # Create 5 documents
    for i in range(5):
        await DocumentFactory.create_async(
            _session=db_session,
            uploaded_by=user.id,
            title=f"Document {i}"
        )
    await db_session.commit()

    service = KnowledgeService(
        db_session=db_session,
        file_provider=mock_file_provider,
        vector_provider=mock_vector_provider,
        llm_provider=mock_llm_provider
    )

    # Get first page
    page1, total = await service.list_documents(
        user_id=user.id,
        limit=2,
        offset=0
    )
    assert len(page1) == 2
    assert total == 5

    # Get second page
    page2, total = await service.list_documents(
        user_id=user.id,
        limit=2,
        offset=2
    )
    assert len(page2) == 2
    assert total == 5

    print("✅ Document pagination works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_delete_document_cleanup(
    db_session,
    mock_file_provider,
    mock_vector_provider,
    mock_llm_provider
):
    """Test that deleting a doc removes it from DB, file storage, and Vector Store."""
    user = await UserFactory.create_async(_session=db_session)
    await db_session.commit()

    doc = await DocumentFactory.create_async(
        _session=db_session,
        uploaded_by=user.id,
        embedding_ids=["vec_1", "vec_2"]
    )
    await db_session.commit()

    doc_id = doc.id
    storage_path = doc.storage_path

    service = KnowledgeService(
        db_session=db_session,
        file_provider=mock_file_provider,
        vector_provider=mock_vector_provider,
        llm_provider=mock_llm_provider
    )

    # Delete document
    result = await service.delete_document(doc_id, user.id)

    assert result is True

    # Verify DB deletion
    found = await service.get_document(doc_id, user.id)
    assert found is None

    # Verify file provider was called to delete file
    mock_file_provider.delete.assert_called_once_with(storage_path)

    # Verify vector provider was called to delete embeddings
    assert mock_vector_provider.delete.call_count == 2  # 2 embedding_ids
    delete_calls = mock_vector_provider.delete.call_args_list
    assert delete_calls[0].kwargs["collection"] == "knowledge"
    assert delete_calls[0].kwargs["id"] == "vec_1"
    assert delete_calls[1].kwargs["id"] == "vec_2"

    print("✅ Document deletion cleanup works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_delete_document_authorization(
    db_session,
    mock_file_provider,
    mock_vector_provider,
    mock_llm_provider
):
    """Test that users can only delete their own documents."""
    user1 = await UserFactory.create_async(_session=db_session)
    user2 = await UserFactory.create_async(_session=db_session)
    await db_session.commit()

    doc = await DocumentFactory.create_async(
        _session=db_session,
        uploaded_by=user1.id
    )
    await db_session.commit()

    service = KnowledgeService(
        db_session=db_session,
        file_provider=mock_file_provider,
        vector_provider=mock_vector_provider,
        llm_provider=mock_llm_provider
    )

    # Try to delete as user2 (should fail)
    result = await service.delete_document(doc.id, user2.id)

    assert result is False

    # File provider should NOT have been called
    mock_file_provider.delete.assert_not_called()

    # Vector provider should NOT have been called
    mock_vector_provider.delete.assert_not_called()

    # Document should still exist
    found = await service.get_document(doc.id, user1.id)
    assert found is not None

    print("✅ Document deletion authorization works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_document_stats(
    db_session,
    mock_file_provider,
    mock_vector_provider,
    mock_llm_provider
):
    """Test document statistics calculation."""
    user = await UserFactory.create_async(_session=db_session)
    await db_session.commit()

    # Create documents with different statuses
    await DocumentFactory.create_async(
        _session=db_session,
        uploaded_by=user.id,
        status=DocumentStatus.INDEXED,
        chunk_count=5
    )
    await DocumentFactory.create_async(
        _session=db_session,
        uploaded_by=user.id,
        status=DocumentStatus.INDEXED,
        chunk_count=3
    )
    await DocumentFactory.create_async(
        _session=db_session,
        uploaded_by=user.id,
        status=DocumentStatus.PENDING,
        chunk_count=0
    )
    await DocumentFactory.create_async(
        _session=db_session,
        uploaded_by=user.id,
        status=DocumentStatus.FAILED,
        chunk_count=0
    )
    await db_session.commit()

    service = KnowledgeService(
        db_session=db_session,
        file_provider=mock_file_provider,
        vector_provider=mock_vector_provider,
        llm_provider=mock_llm_provider
    )

    # Get stats
    stats = await service.get_document_stats(user_id=user.id)

    assert stats["total_documents"] == 4
    assert stats["indexed_documents"] == 2
    assert stats["pending_documents"] == 1
    assert stats["failed_documents"] == 1
    assert stats["total_chunks"] == 8  # 5 + 3 + 0 + 0

    print("✅ Document statistics works")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_process_document_flow(
    db_session,
    mock_file_provider,
    mock_vector_provider,
    mock_llm_provider
):
    """Test document processing pipeline (chunking, embedding, indexing)."""
    user = await UserFactory.create_async(_session=db_session)
    await db_session.commit()

    # Create a document in PENDING status
    document = await DocumentFactory.create_async(
        _session=db_session,
        uploaded_by=user.id,
        status=DocumentStatus.PENDING,
        filename="test_doc.txt",
        storage_path="documents/test/test_doc.txt",
        title="Test Document"
    )
    await db_session.commit()

    # Mock file provider to return test content
    test_content = "This is a test document.\n" * 100  # 2500 chars
    mock_file_provider.download = AsyncMock(return_value=BytesIO(test_content.encode()))

    # Mock vector provider upsert
    mock_vector_provider.upsert = AsyncMock(return_value=None)

    # Initialize service
    service = KnowledgeService(
        db_session=db_session,
        file_provider=mock_file_provider,
        vector_provider=mock_vector_provider,
        llm_provider=mock_llm_provider
    )

    # Process the document
    result = await service.process_document(document.id)

    # Verify processing result
    assert result["status"] == "success"
    assert result["document_id"] == document.id
    assert result["chunks_processed"] > 0

    # Verify document was updated in database
    await db_session.refresh(document)
    assert document.status == DocumentStatus.INDEXED
    assert document.chunk_count > 0
    assert len(document.embedding_ids) > 0
    assert document.content_hash is not None
    assert document.indexed_at is not None

    # Verify LLM provider was called for each chunk
    assert mock_llm_provider.embed.call_count == document.chunk_count

    # Verify vector provider was called for each chunk
    assert mock_vector_provider.upsert.call_count == document.chunk_count

    # Verify vector provider calls had correct metadata
    upsert_calls = mock_vector_provider.upsert.call_args_list
    for i, call in enumerate(upsert_calls):
        assert call.kwargs["collection"] == "knowledge"
        assert call.kwargs["id"] == f"{document.id}_chunk_{i}"
        assert "document_id" in call.kwargs["metadata"]
        assert call.kwargs["metadata"]["document_id"] == document.id
        assert call.kwargs["metadata"]["user_id"] == user.id

    print("✅ Document processing pipeline works")
