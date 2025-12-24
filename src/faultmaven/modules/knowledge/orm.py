"""
Knowledge module ORM models.

Document metadata is stored here, vectors in VectorProvider (ChromaDB/Pinecone).
"""

from datetime import datetime
from typing import TYPE_CHECKING
from enum import Enum
from sqlalchemy import String, DateTime, JSON, Text, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from faultmaven.database import Base

if TYPE_CHECKING:
    from faultmaven.modules.auth.orm import User


class DocumentType(str, Enum):
    """Type of document."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MARKDOWN = "markdown"
    HTML = "html"
    CODE = "code"
    OTHER = "other"


class DocumentStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class Document(Base):
    """Knowledge base document metadata."""

    __tablename__ = "documents"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Foreign key to User
    uploaded_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )

    # Document info
    title: Mapped[str] = mapped_column(String(500))
    filename: Mapped[str] = mapped_column(String(255))
    document_type: Mapped[DocumentType] = mapped_column(
        SQLEnum(DocumentType),
        default=DocumentType.OTHER
    )

    # Content (extracted text)
    content: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64))  # SHA256 for deduplication

    # Processing status
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus),
        default=DocumentStatus.PENDING,
        index=True
    )

    # File reference
    storage_path: Mapped[str] = mapped_column(String(512))  # FileProvider key
    file_size: Mapped[int] = mapped_column(Integer)

    # Embedding tracking
    embedding_ids: Mapped[list[str]] = mapped_column(JSON, default=list)  # Vector DB IDs
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    # Metadata (renamed to avoid SQLAlchemy conflict)
    document_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationship
    uploaded_by_user: Mapped["User | None"] = relationship(
        "User",
        back_populates="documents"
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title={self.title}, status={self.status})>"


class SearchQuery(Base):
    """
    Search query analytics (optional).

    Track what users search for to improve relevance.
    """

    __tablename__ = "search_queries"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Query data
    query_text: Mapped[str] = mapped_column(Text)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)

    # Results
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    top_result_ids: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Performance
    latency_ms: Mapped[int | None] = mapped_column(Integer)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )

    def __repr__(self) -> str:
        return f"<SearchQuery(id={self.id}, query={self.query_text[:50]})>"
