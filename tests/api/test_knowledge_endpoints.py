"""
Knowledge API Endpoint Tests.

Tests the HTTP Contract for Knowledge endpoints:
- POST /knowledge/ingest - Upload and ingest document
- POST /knowledge/search - Semantic search
- GET /knowledge/documents - List documents
- GET /knowledge/documents/{id} - Get document metadata
- DELETE /knowledge/documents/{id} - Delete document
- GET /knowledge/stats - Get knowledge base stats

Focus: Router logic, status codes, JSON schemas, authentication.
NOT testing: Vector search implementation, document processing (covered in integration tests).
"""

import pytest
from io import BytesIO
from httpx import AsyncClient


# ==============================================================================
# Ingest Document
# ==============================================================================

@pytest.mark.api
class TestKnowledgeIngestEndpoint:
    """Test POST /knowledge/ingest - Upload and ingest document."""

    async def test_ingest_document_success(self, authenticated_client):
        """Test ingesting document returns 200 with correct schema."""
        client, user = authenticated_client

        # Create test document
        file_content = b"This is a test documentation file with useful information."
        file = ("test_doc.txt", BytesIO(file_content), "text/plain")

        response = await client.post(
            "/knowledge/ingest",
            data={
                "title": "Test Documentation",
                "document_type": "markdown",
                "tags": "test,documentation,api",
            },
            files={"file": file}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Documentation"
        assert data["filename"] == "test_doc.txt"
        assert data["document_type"] == "markdown"
        # In tests, processing is synchronous, so document is already indexed
        assert data["status"] in ("pending", "indexed")
        assert data["file_size"] == len(file_content)
        assert data["tags"] == ["test", "documentation", "api"]
        assert "id" in data
        assert "uploaded_at" in data

    async def test_ingest_document_without_title(self, authenticated_client):
        """Test ingesting document without title uses filename."""
        client, user = authenticated_client

        file = ("readme.md", BytesIO(b"# README"), "text/markdown")

        response = await client.post(
            "/knowledge/ingest",
            data={"document_type": "markdown"},
            files={"file": file}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "readme.md"
        assert data["title"] == "readme.md"  # Defaults to filename

    async def test_ingest_document_file_too_large(self, authenticated_client):
        """Test uploading file larger than 50MB returns 400."""
        client, user = authenticated_client

        # Create 51MB file
        large_content = b"x" * (51 * 1024 * 1024)
        file = ("large.txt", BytesIO(large_content), "text/plain")

        response = await client.post(
            "/knowledge/ingest",
            data={"document_type": "other"},
            files={"file": file}
        )

        assert response.status_code == 400
        assert "too large" in response.json()["detail"].lower()

    async def test_ingest_document_unauthenticated(self, unauthenticated_client):
        """Test ingesting without authentication returns 401."""
        client = unauthenticated_client

        file = ("test.txt", BytesIO(b"content"), "text/plain")

        response = await client.post(
            "/knowledge/ingest",
            data={"document_type": "other"},
            files={"file": file}
        )

        assert response.status_code == 401


# ==============================================================================
# Search Knowledge Base
# ==============================================================================

@pytest.mark.api
class TestKnowledgeSearchEndpoint:
    """Test POST /knowledge/search - Semantic search."""

    async def test_search_knowledge_success(self, authenticated_client):
        """Test searching knowledge base returns results with correct schema."""
        client, user = authenticated_client

        # First ingest a document
        file = ("test.txt", BytesIO(b"FastAPI is a modern web framework"), "text/plain")
        await client.post(
            "/knowledge/ingest",
            data={"title": "FastAPI Guide", "document_type": "txt"},
            files={"file": file}
        )

        # Search for it
        response = await client.post(
            "/knowledge/search",
            json={
                "query_text": "web framework",
                "limit": 10
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data
        assert "total" in data
        assert "latency_ms" in data
        assert isinstance(data["results"], list)

    async def test_search_with_filters(self, authenticated_client):
        """Test searching with filters."""
        client, user = authenticated_client

        response = await client.post(
            "/knowledge/search",
            json={
                "query_text": "authentication",
                "filters": {"document_type": "txt"},
                "limit": 5
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "authentication"

    async def test_search_unauthenticated(self, unauthenticated_client):
        """Test searching without authentication returns 401."""
        client = unauthenticated_client

        response = await client.post(
            "/knowledge/search",
            json={"query_text": "test"}
        )

        assert response.status_code == 401


# ==============================================================================
# List Documents
# ==============================================================================

@pytest.mark.api
class TestKnowledgeListDocumentsEndpoint:
    """Test GET /knowledge/documents - List documents."""

    async def test_list_documents_success(self, authenticated_client):
        """Test listing documents returns 200 with pagination."""
        client, user = authenticated_client

        # Ingest multiple documents
        for i in range(3):
            file = (f"doc{i}.txt", BytesIO(b"content"), "text/plain")
            await client.post(
                "/knowledge/ingest",
                data={"title": f"Document {i}", "document_type": "other"},
                files={"file": file}
            )

        # List documents
        response = await client.get("/knowledge/documents")

        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert len(data["documents"]) == 3
        assert data["total"] == 3
        assert data["limit"] == 50  # Default
        assert data["offset"] == 0

    async def test_list_documents_pagination(self, authenticated_client):
        """Test listing with limit and offset."""
        client, user = authenticated_client

        # Ingest 5 documents
        for i in range(5):
            file = (f"doc{i}.txt", BytesIO(b"content"), "text/plain")
            await client.post(
                "/knowledge/ingest",
                data={"title": f"Document {i}", "document_type": "other"},
                files={"file": file}
            )

        # Get first 2
        response = await client.get("/knowledge/documents?limit=2&offset=0")
        data = response.json()
        assert len(data["documents"]) == 2
        assert data["total"] == 5

        # Get next 2
        response = await client.get("/knowledge/documents?limit=2&offset=2")
        data = response.json()
        assert len(data["documents"]) == 2
        assert data["total"] == 5

    async def test_list_documents_filter_by_status(self, authenticated_client):
        """Test filtering by document status."""
        client, user = authenticated_client

        response = await client.get("/knowledge/documents?status=pending")

        assert response.status_code == 200
        data = response.json()
        assert "documents" in data

    async def test_list_documents_empty(self, authenticated_client):
        """Test listing when no documents exist."""
        client, user = authenticated_client

        response = await client.get("/knowledge/documents")

        assert response.status_code == 200
        data = response.json()
        assert len(data["documents"]) == 0
        assert data["total"] == 0

    async def test_list_documents_unauthenticated(self, unauthenticated_client):
        """Test listing without authentication returns 401."""
        client = unauthenticated_client

        response = await client.get("/knowledge/documents")

        assert response.status_code == 401


# ==============================================================================
# Get Document
# ==============================================================================

@pytest.mark.api
class TestKnowledgeGetDocumentEndpoint:
    """Test GET /knowledge/documents/{id} - Get document metadata."""

    async def test_get_document_success(self, authenticated_client):
        """Test getting document returns 200 with metadata."""
        client, user = authenticated_client

        # Ingest document
        file = ("test.txt", BytesIO(b"content"), "text/plain")
        ingest_response = await client.post(
            "/knowledge/ingest",
            data={"title": "Test Doc", "document_type": "other"},
            files={"file": file}
        )
        document_id = ingest_response.json()["id"]

        # Get document
        response = await client.get(f"/knowledge/documents/{document_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == document_id
        assert data["title"] == "Test Doc"
        assert data["filename"] == "test.txt"

    async def test_get_document_not_found(self, authenticated_client):
        """Test getting non-existent document returns 404."""
        client, user = authenticated_client

        response = await client.get("/knowledge/documents/non-existent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_get_document_unauthenticated(self, unauthenticated_client):
        """Test getting document without authentication returns 401."""
        client = unauthenticated_client

        response = await client.get("/knowledge/documents/some-id")

        assert response.status_code == 401

    async def test_get_document_unauthorized(self, authenticated_client, second_user_client):
        """Test getting another user's document returns 404."""
        client, user = authenticated_client
        second_client, user2 = second_user_client

        # User 2 ingests document
        file = ("test.txt", BytesIO(b"content"), "text/plain")
        ingest_response = await second_client.post(
            "/knowledge/ingest",
            data={"title": "User 2 Doc", "document_type": "other"},
            files={"file": file}
        )
        document_id = ingest_response.json()["id"]

        # User 1 tries to access user 2's document
        response = await client.get(f"/knowledge/documents/{document_id}")

        assert response.status_code == 404


# ==============================================================================
# Delete Document
# ==============================================================================

@pytest.mark.api
class TestKnowledgeDeleteDocumentEndpoint:
    """Test DELETE /knowledge/documents/{id} - Delete document."""

    async def test_delete_document_success(self, authenticated_client):
        """Test deleting document returns 200 with success message."""
        client, user = authenticated_client

        # Ingest document
        file = ("test.txt", BytesIO(b"content"), "text/plain")
        ingest_response = await client.post(
            "/knowledge/ingest",
            data={"title": "To Delete", "document_type": "other"},
            files={"file": file}
        )
        document_id = ingest_response.json()["id"]

        # Delete document
        response = await client.delete(f"/knowledge/documents/{document_id}")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "deleted" in data["message"].lower()

        # Verify it's deleted
        get_response = await client.get(f"/knowledge/documents/{document_id}")
        assert get_response.status_code == 404

    async def test_delete_document_not_found(self, authenticated_client):
        """Test deleting non-existent document returns 404."""
        client, user = authenticated_client

        response = await client.delete("/knowledge/documents/non-existent-id")

        assert response.status_code == 404

    async def test_delete_document_unauthenticated(self, unauthenticated_client):
        """Test deleting without authentication returns 401."""
        client = unauthenticated_client

        response = await client.delete("/knowledge/documents/some-id")

        assert response.status_code == 401

    async def test_delete_document_unauthorized(self, authenticated_client, second_user_client):
        """Test deleting another user's document returns 404."""
        client, user = authenticated_client
        second_client, user2 = second_user_client

        # User 2 ingests document
        file = ("test.txt", BytesIO(b"content"), "text/plain")
        ingest_response = await second_client.post(
            "/knowledge/ingest",
            data={"title": "User 2 Doc", "document_type": "other"},
            files={"file": file}
        )
        document_id = ingest_response.json()["id"]

        # User 1 tries to delete user 2's document
        response = await client.delete(f"/knowledge/documents/{document_id}")

        assert response.status_code == 404


# ==============================================================================
# Get Stats
# ==============================================================================

@pytest.mark.api
class TestKnowledgeStatsEndpoint:
    """Test GET /knowledge/stats - Get knowledge base stats."""

    async def test_get_stats_success(self, authenticated_client):
        """Test getting stats returns 200 with stats schema."""
        client, user = authenticated_client

        response = await client.get("/knowledge/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_documents" in data
        assert "indexed_documents" in data
        assert "pending_documents" in data
        assert "failed_documents" in data
        assert "total_chunks" in data

    async def test_get_stats_unauthenticated(self, unauthenticated_client):
        """Test getting stats without authentication returns 401."""
        client = unauthenticated_client

        response = await client.get("/knowledge/stats")

        assert response.status_code == 401
