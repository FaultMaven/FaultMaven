"""
Evidence module ORM models.

Evidence metadata is stored in database, files in FileProvider (local/S3).
"""

from datetime import datetime
from typing import TYPE_CHECKING
from enum import Enum
from sqlalchemy import String, DateTime, JSON, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from faultmaven.database import Base

if TYPE_CHECKING:
    from faultmaven.modules.auth.orm import User
    from faultmaven.modules.case.orm import Case


class EvidenceType(str, Enum):
    """Type of evidence."""
    LOG = "log"
    SCREENSHOT = "screenshot"
    DOCUMENT = "document"
    METRIC = "metric"
    CODE = "code"
    CONFIGURATION = "configuration"
    OTHER = "other"


class Evidence(Base):
    """Evidence file metadata."""

    __tablename__ = "evidence"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Foreign keys (PROPER RELATIONSHIPS!)
    case_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    uploaded_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True  # Can be null if user is deleted
    )

    # File metadata
    filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(100))  # MIME type
    file_size: Mapped[int] = mapped_column(Integer)  # bytes

    # Storage reference
    storage_path: Mapped[str] = mapped_column(String(512))  # FileProvider key

    # Evidence categorization
    evidence_type: Mapped[EvidenceType] = mapped_column(
        SQLEnum(EvidenceType),
        default=EvidenceType.OTHER
    )
    description: Mapped[str | None] = mapped_column(String(500))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Additional metadata (renamed to avoid SQLAlchemy conflict)
    evidence_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    # Relationships
    case: Mapped["Case"] = relationship("Case", back_populates="evidence")
    uploaded_by_user: Mapped["User | None"] = relationship(
        "User",
        back_populates="evidence"
    )

    def __repr__(self) -> str:
        return f"<Evidence(id={self.id}, filename={self.filename})>"
