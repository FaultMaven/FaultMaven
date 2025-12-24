"""
Evidence module service layer.

Handles evidence file upload/download with dual storage:
- Metadata in PostgreSQL
- Files in FileProvider (local disk / S3)
"""

import uuid
import os
from datetime import datetime
from typing import Optional, BinaryIO

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from faultmaven.modules.evidence.orm import Evidence, EvidenceType
from faultmaven.modules.case.orm import Case
from faultmaven.providers.interfaces import FileProvider


class EvidenceService:
    """
    Service for evidence management.

    Manages both file storage (via FileProvider) and metadata (via PostgreSQL).
    """

    def __init__(
        self,
        db_session: AsyncSession,
        file_provider: FileProvider,
    ):
        """
        Initialize evidence service.

        Args:
            db_session: Database session for metadata
            file_provider: File storage provider (local/S3)
        """
        self.db = db_session
        self.file_provider = file_provider

    async def upload_evidence(
        self,
        case_id: str,
        user_id: str,
        file_content: BinaryIO,
        filename: str,
        file_type: str,
        file_size: int,
        evidence_type: EvidenceType = EvidenceType.OTHER,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Optional[Evidence]:
        """
        Upload evidence file.

        Args:
            case_id: Case ID to attach evidence to
            user_id: User ID uploading the evidence
            file_content: Binary file content
            filename: Original filename
            file_type: MIME type
            file_size: File size in bytes
            evidence_type: Type of evidence
            description: Optional description
            tags: Optional tags

        Returns:
            Evidence metadata or None if case not found/unauthorized
        """
        # Verify case exists and user owns it (gatekeeper check)
        result = await self.db.execute(
            select(Case).where(Case.id == case_id)
        )
        case = result.scalar_one_or_none()

        if not case or case.owner_id != user_id:
            return None

        # Generate unique storage path
        evidence_id = str(uuid.uuid4())
        file_ext = os.path.splitext(filename)[1]
        storage_filename = f"{evidence_id}{file_ext}"
        storage_path = f"evidence/{case_id}/{storage_filename}"

        # Upload file to storage provider
        await self.file_provider.upload(
            file_content=file_content,
            path=storage_path,
        )

        # Create evidence metadata in database
        evidence = Evidence(
            id=evidence_id,
            case_id=case_id,
            uploaded_by=user_id,
            filename=storage_filename,
            original_filename=filename,
            file_type=file_type,
            file_size=file_size,
            storage_path=storage_path,
            evidence_type=evidence_type,
            description=description,
            tags=tags or [],
            evidence_metadata={},
            uploaded_at=datetime.utcnow(),
        )

        try:
            self.db.add(evidence)
            await self.db.commit()
            await self.db.refresh(evidence)
        except Exception:
            # CLEANUP: Database failed, remove physical file to prevent orphans
            await self.file_provider.delete(storage_path)
            raise  # Re-raise so API knows it failed

        return evidence

    async def get_evidence(
        self,
        evidence_id: str,
        user_id: str,
    ) -> Optional[Evidence]:
        """
        Get evidence metadata.

        Args:
            evidence_id: Evidence ID
            user_id: User ID for ownership verification

        Returns:
            Evidence metadata or None if not found/unauthorized
        """
        # Get evidence with case join for ownership check
        result = await self.db.execute(
            select(Evidence)
            .join(Case, Evidence.case_id == Case.id)
            .where(
                Evidence.id == evidence_id,
                Case.owner_id == user_id,
            )
        )
        evidence = result.scalar_one_or_none()

        return evidence

    async def download_evidence(
        self,
        evidence_id: str,
        user_id: str,
    ) -> Optional[tuple[BinaryIO, Evidence]]:
        """
        Download evidence file.

        Args:
            evidence_id: Evidence ID
            user_id: User ID for ownership verification

        Returns:
            Tuple of (file_content, evidence_metadata) or None if not found/unauthorized
        """
        # Get evidence metadata with ownership check
        evidence = await self.get_evidence(evidence_id, user_id)

        if not evidence:
            return None

        # Download file from storage provider
        file_content = await self.file_provider.download(evidence.storage_path)

        if not file_content:
            return None

        return file_content, evidence

    async def delete_evidence(
        self,
        evidence_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete evidence file and metadata.

        CRITICAL: Deletes from both database AND file storage to prevent orphans.

        Args:
            evidence_id: Evidence ID
            user_id: User ID for ownership verification

        Returns:
            True if deleted, False if not found/unauthorized
        """
        # Get evidence with ownership check
        evidence = await self.get_evidence(evidence_id, user_id)

        if not evidence:
            return False

        # Delete from file storage FIRST (if DB delete fails, we can retry)
        await self.file_provider.delete(evidence.storage_path)

        # Delete from database
        await self.db.delete(evidence)
        await self.db.commit()

        return True

    async def list_case_evidence(
        self,
        case_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Optional[tuple[list[Evidence], int]]:
        """
        List evidence for a case.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification
            limit: Maximum number of items
            offset: Pagination offset

        Returns:
            Tuple of (evidence_list, total_count) or None if case not found/unauthorized
        """
        # Verify case exists and user owns it
        result = await self.db.execute(
            select(Case).where(Case.id == case_id)
        )
        case = result.scalar_one_or_none()

        if not case or case.owner_id != user_id:
            return None

        # Get total count
        count_query = (
            select(func.count())
            .select_from(Evidence)
            .where(Evidence.case_id == case_id)
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Get paginated evidence
        query = (
            select(Evidence)
            .where(Evidence.case_id == case_id)
            .order_by(Evidence.uploaded_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        evidence_list = result.scalars().all()

        return list(evidence_list), total
