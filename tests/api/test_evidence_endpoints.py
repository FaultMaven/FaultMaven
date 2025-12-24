"""
Evidence API Endpoint Tests.

Tests the HTTP Contract for Evidence endpoints:
- POST /evidence/upload - Upload file
- GET /evidence/{evidence_id} - Get metadata
- DELETE /evidence/{evidence_id} - Delete file
- GET /evidence/{evidence_id}/download - Download file
- GET /evidence/case/{case_id} - List evidence by case
- GET /evidence - List all evidence

Focus: Router logic, status codes, JSON schemas, authentication.
NOT testing: File storage implementation, business logic (covered in integration tests).
"""

import pytest
from io import BytesIO
from httpx import AsyncClient
from tests.factories.case import CaseFactory


# ==============================================================================
# Upload Evidence
# ==============================================================================

@pytest.mark.api
class TestEvidenceUploadEndpoint:
    """Test POST /evidence/upload - Upload evidence file."""

    async def test_upload_evidence_success(self, authenticated_client, db_session):
        """Test uploading evidence returns 201 with correct schema."""
        client, user = authenticated_client

        # Create a case first
        case = await CaseFactory.create_async(
            _session=db_session,
            owner_id=user.id,
            title="Test Case"
        )
        await db_session.commit()

        # Create a test file
        file_content = b"This is a test log file"
        file = ("test.log", BytesIO(file_content), "text/plain")

        response = await client.post(
            "/evidence/upload",
            data={
                "case_id": case.id,
                "evidence_type": "log",
                "description": "Application error log",
                "tags": "error,backend,production",
            },
            files={"file": file}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["case_id"] == case.id
        assert data["uploaded_by"] == user.id
        assert data["original_filename"] == "test.log"
        assert data["file_type"] == "text/plain"
        assert data["file_size"] == len(file_content)
        assert data["evidence_type"] == "log"
        assert data["description"] == "Application error log"
        assert data["tags"] == ["error", "backend", "production"]
        assert "id" in data
        assert "filename" in data  # Storage filename
        assert "uploaded_at" in data

    async def test_upload_evidence_without_tags(self, authenticated_client, db_session):
        """Test uploading evidence without tags succeeds."""
        client, user = authenticated_client

        case = await CaseFactory.create_async(_session=db_session, owner_id=user.id)
        await db_session.commit()

        file = ("screenshot.png", BytesIO(b"fake-png-data"), "image/png")

        response = await client.post(
            "/evidence/upload",
            data={
                "case_id": case.id,
                "evidence_type": "screenshot",
            },
            files={"file": file}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tags"] == []

    async def test_upload_evidence_case_not_found(self, authenticated_client):
        """Test uploading to non-existent case returns 404."""
        client, _ = authenticated_client

        file = ("test.log", BytesIO(b"content"), "text/plain")

        response = await client.post(
            "/evidence/upload",
            data={
                "case_id": "non-existent-case-id",
                "evidence_type": "log",
            },
            files={"file": file}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_upload_evidence_unauthenticated(self, unauthenticated_client):
        """Test uploading without authentication returns 401."""
        client = unauthenticated_client

        file = ("test.log", BytesIO(b"content"), "text/plain")

        response = await client.post(
            "/evidence/upload",
            data={
                "case_id": "some-case-id",
                "evidence_type": "log",
            },
            files={"file": file}
        )

        assert response.status_code == 401

    async def test_upload_evidence_unauthorized_case(self, authenticated_client, second_user_client, db_session):
        """Test uploading to another user's case returns 404."""
        client, user = authenticated_client
        second_client, user2 = second_user_client

        # User 2 creates a case
        case = await CaseFactory.create_async(_session=db_session, owner_id=user2.id)
        await db_session.commit()

        # User 1 tries to upload evidence to user 2's case
        file = ("test.log", BytesIO(b"content"), "text/plain")

        response = await client.post(
            "/evidence/upload",
            data={
                "case_id": case.id,
                "evidence_type": "log",
            },
            files={"file": file}
        )

        assert response.status_code == 404  # Service returns None for unauthorized


# ==============================================================================
# Get Evidence Metadata
# ==============================================================================

@pytest.mark.api
class TestEvidenceGetEndpoint:
    """Test GET /evidence/{evidence_id} - Get evidence metadata."""

    async def test_get_evidence_success(self, authenticated_client, db_session):
        """Test getting evidence metadata returns 200 with correct schema."""
        client, user = authenticated_client

        # Create case and upload evidence
        case = await CaseFactory.create_async(_session=db_session, owner_id=user.id)
        await db_session.commit()

        file = ("test.log", BytesIO(b"content"), "text/plain")
        upload_response = await client.post(
            "/evidence/upload",
            data={"case_id": case.id, "evidence_type": "log"},
            files={"file": file}
        )
        evidence_id = upload_response.json()["id"]

        # Get evidence metadata
        response = await client.get(f"/evidence/{evidence_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == evidence_id
        assert data["case_id"] == case.id
        assert data["uploaded_by"] == user.id

    async def test_get_evidence_not_found(self, authenticated_client):
        """Test getting non-existent evidence returns 404."""
        client, _ = authenticated_client

        response = await client.get("/evidence/non-existent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_get_evidence_unauthenticated(self, unauthenticated_client):
        """Test getting evidence without authentication returns 401."""
        client = unauthenticated_client

        response = await client.get("/evidence/some-id")

        assert response.status_code == 401

    async def test_get_evidence_unauthorized(self, authenticated_client, second_user_client, db_session):
        """Test getting another user's evidence returns 404."""
        client, user = authenticated_client
        second_client, user2 = second_user_client

        # User 2 uploads evidence
        case = await CaseFactory.create_async(_session=db_session, owner_id=user2.id)
        await db_session.commit()

        file = ("test.log", BytesIO(b"content"), "text/plain")
        upload_response = await second_client.post(
            "/evidence/upload",
            data={"case_id": case.id, "evidence_type": "log"},
            files={"file": file}
        )
        evidence_id = upload_response.json()["id"]

        # User 1 tries to access user 2's evidence
        response = await client.get(f"/evidence/{evidence_id}")

        assert response.status_code == 404


# ==============================================================================
# Delete Evidence
# ==============================================================================

@pytest.mark.api
class TestEvidenceDeleteEndpoint:
    """Test DELETE /evidence/{evidence_id} - Delete evidence."""

    async def test_delete_evidence_success(self, authenticated_client, db_session):
        """Test deleting evidence returns 204."""
        client, user = authenticated_client

        # Create and upload evidence
        case = await CaseFactory.create_async(_session=db_session, owner_id=user.id)
        await db_session.commit()

        file = ("test.log", BytesIO(b"content"), "text/plain")
        upload_response = await client.post(
            "/evidence/upload",
            data={"case_id": case.id, "evidence_type": "log"},
            files={"file": file}
        )
        evidence_id = upload_response.json()["id"]

        # Delete evidence
        response = await client.delete(f"/evidence/{evidence_id}")

        assert response.status_code == 204
        assert response.content == b""  # No content

        # Verify it's deleted (should return 404)
        get_response = await client.get(f"/evidence/{evidence_id}")
        assert get_response.status_code == 404

    async def test_delete_evidence_not_found(self, authenticated_client):
        """Test deleting non-existent evidence returns 404."""
        client, _ = authenticated_client

        response = await client.delete("/evidence/non-existent-id")

        assert response.status_code == 404

    async def test_delete_evidence_unauthenticated(self, unauthenticated_client):
        """Test deleting without authentication returns 401."""
        client = unauthenticated_client

        response = await client.delete("/evidence/some-id")

        assert response.status_code == 401

    async def test_delete_evidence_unauthorized(self, authenticated_client, second_user_client, db_session):
        """Test deleting another user's evidence returns 404."""
        client, user = authenticated_client
        second_client, user2 = second_user_client

        # User 2 uploads evidence
        case = await CaseFactory.create_async(_session=db_session, owner_id=user2.id)
        await db_session.commit()

        file = ("test.log", BytesIO(b"content"), "text/plain")
        upload_response = await second_client.post(
            "/evidence/upload",
            data={"case_id": case.id, "evidence_type": "log"},
            files={"file": file}
        )
        evidence_id = upload_response.json()["id"]

        # User 1 tries to delete user 2's evidence
        response = await client.delete(f"/evidence/{evidence_id}")

        assert response.status_code == 404


# ==============================================================================
# Download Evidence
# ==============================================================================

@pytest.mark.api
class TestEvidenceDownloadEndpoint:
    """Test GET /evidence/{evidence_id}/download - Download file."""

    async def test_download_evidence_success(self, authenticated_client, db_session):
        """Test downloading evidence returns file with correct headers."""
        client, user = authenticated_client

        # Upload evidence
        case = await CaseFactory.create_async(_session=db_session, owner_id=user.id)
        await db_session.commit()

        file_content = b"This is test content"
        file = ("test.log", BytesIO(file_content), "text/plain")
        upload_response = await client.post(
            "/evidence/upload",
            data={"case_id": case.id, "evidence_type": "log"},
            files={"file": file}
        )
        evidence_id = upload_response.json()["id"]

        # Download evidence
        response = await client.get(f"/evidence/{evidence_id}/download")

        assert response.status_code == 200
        assert response.content == file_content
        assert "text/plain" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        assert "test.log" in response.headers["content-disposition"]

    async def test_download_evidence_not_found(self, authenticated_client):
        """Test downloading non-existent evidence returns 404."""
        client, _ = authenticated_client

        response = await client.get("/evidence/non-existent-id/download")

        assert response.status_code == 404

    async def test_download_evidence_unauthenticated(self, unauthenticated_client):
        """Test downloading without authentication returns 401."""
        client = unauthenticated_client

        response = await client.get("/evidence/some-id/download")

        assert response.status_code == 401

    async def test_download_evidence_unauthorized(self, authenticated_client, second_user_client, db_session):
        """Test downloading another user's evidence returns 404."""
        client, user = authenticated_client
        second_client, user2 = second_user_client

        # User 2 uploads evidence
        case = await CaseFactory.create_async(_session=db_session, owner_id=user2.id)
        await db_session.commit()

        file = ("test.log", BytesIO(b"content"), "text/plain")
        upload_response = await second_client.post(
            "/evidence/upload",
            data={"case_id": case.id, "evidence_type": "log"},
            files={"file": file}
        )
        evidence_id = upload_response.json()["id"]

        # User 1 tries to download user 2's evidence
        response = await client.get(f"/evidence/{evidence_id}/download")

        assert response.status_code == 404


# ==============================================================================
# List Evidence by Case
# ==============================================================================

@pytest.mark.api
class TestListCaseEvidenceEndpoint:
    """Test GET /evidence/case/{case_id} - List evidence for a case."""

    async def test_list_case_evidence_success(self, authenticated_client, db_session):
        """Test listing case evidence returns 200 with pagination."""
        client, user = authenticated_client

        # Create case and upload multiple evidence files
        case = await CaseFactory.create_async(_session=db_session, owner_id=user.id)
        await db_session.commit()

        # Upload 3 evidence files
        for i in range(3):
            file = (f"test{i}.log", BytesIO(b"content"), "text/plain")
            await client.post(
                "/evidence/upload",
                data={"case_id": case.id, "evidence_type": "log"},
                files={"file": file}
            )

        # List evidence
        response = await client.get(f"/evidence/case/{case.id}")

        assert response.status_code == 200
        data = response.json()
        assert "evidence" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert len(data["evidence"]) == 3
        assert data["total"] == 3
        assert data["limit"] == 50  # Default
        assert data["offset"] == 0

    async def test_list_case_evidence_pagination(self, authenticated_client, db_session):
        """Test listing with limit and offset."""
        client, user = authenticated_client

        case = await CaseFactory.create_async(_session=db_session, owner_id=user.id)
        await db_session.commit()

        # Upload 5 evidence files
        for i in range(5):
            file = (f"test{i}.log", BytesIO(b"content"), "text/plain")
            await client.post(
                "/evidence/upload",
                data={"case_id": case.id, "evidence_type": "log"},
                files={"file": file}
            )

        # Get first 2
        response = await client.get(f"/evidence/case/{case.id}?limit=2&offset=0")
        data = response.json()
        assert len(data["evidence"]) == 2
        assert data["total"] == 5

        # Get next 2
        response = await client.get(f"/evidence/case/{case.id}?limit=2&offset=2")
        data = response.json()
        assert len(data["evidence"]) == 2
        assert data["total"] == 5

    async def test_list_case_evidence_empty(self, authenticated_client, db_session):
        """Test listing evidence for case with no evidence."""
        client, user = authenticated_client

        case = await CaseFactory.create_async(_session=db_session, owner_id=user.id)
        await db_session.commit()

        response = await client.get(f"/evidence/case/{case.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["evidence"]) == 0
        assert data["total"] == 0

    async def test_list_case_evidence_case_not_found(self, authenticated_client):
        """Test listing evidence for non-existent case returns 404."""
        client, _ = authenticated_client

        response = await client.get("/evidence/case/non-existent-id")

        assert response.status_code == 404

    async def test_list_case_evidence_unauthenticated(self, unauthenticated_client):
        """Test listing without authentication returns 401."""
        client = unauthenticated_client

        response = await client.get("/evidence/case/some-id")

        assert response.status_code == 401

    async def test_list_case_evidence_unauthorized(self, authenticated_client, second_user_client, db_session):
        """Test listing another user's case evidence returns 404."""
        client, user = authenticated_client
        second_client, user2 = second_user_client

        # User 2 creates case with evidence
        case = await CaseFactory.create_async(_session=db_session, owner_id=user2.id)
        await db_session.commit()

        file = ("test.log", BytesIO(b"content"), "text/plain")
        await second_client.post(
            "/evidence/upload",
            data={"case_id": case.id, "evidence_type": "log"},
            files={"file": file}
        )

        # User 1 tries to list user 2's case evidence
        response = await client.get(f"/evidence/case/{case.id}")

        assert response.status_code == 404
