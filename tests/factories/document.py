"""
Document factory for creating test documents.
"""

import factory
import uuid
from datetime import datetime

from faultmaven.modules.knowledge.orm import Document, DocumentStatus, DocumentType
from tests.factories import AsyncSQLAlchemyFactory
from tests.factories.user import UserFactory


class DocumentFactory(AsyncSQLAlchemyFactory):
    """
    Factory for creating test documents.

    Default values:
    - System Architecture Guide title
    - INDEXED status
    - TEXT type
    - Mock storage path

    Usage:
        # Create document for a specific user
        user = await UserFactory.create_async(_session=db_session)
        document = await DocumentFactory.create_async(
            _session=db_session,
            uploaded_by=user.id
        )

        # Create document with custom content
        document = await DocumentFactory.create_async(
            _session=db_session,
            uploaded_by=user.id,
            title="Deployment Guide",
            content="Step 1: Run docker-compose up"
        )
    """

    class Meta:
        model = Document

    # Primary key
    id = factory.LazyFunction(lambda: str(uuid.uuid4()))

    # Document info
    title = "System Architecture Guide"
    filename = "architecture.txt"
    document_type = DocumentType.TXT

    # Content
    content = "This is a comprehensive guide to the system architecture."
    content_hash = factory.LazyFunction(lambda: str(uuid.uuid4()))

    # Processing status
    status = DocumentStatus.INDEXED

    # File reference
    storage_path = factory.LazyAttribute(lambda o: f"documents/{o.uploaded_by}/{o.filename}")
    file_size = 100

    # Embedding tracking
    embedding_ids = []
    chunk_count = 1

    # Metadata
    document_metadata = {}
    tags = []

    # Timestamps (timezone-naive to match ORM models)
    uploaded_at = factory.LazyFunction(datetime.utcnow)
    indexed_at = factory.LazyFunction(datetime.utcnow)
    last_accessed_at = None

    # Relationships - uploaded_by must be provided
    uploaded_by = None  # Must be provided
