"""
Report module ORM models.

Ported from legacy: models/report.py

Provides persistent storage for generated case reports including:
- Incident reports
- Runbooks
- Post-mortems

Reports support versioning and are linked to case closure.
"""

from datetime import datetime
from typing import Optional
from enum import Enum
from sqlalchemy import String, DateTime, JSON, Text, ForeignKey, Integer, Boolean, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from faultmaven.database import Base


class ReportType(str, Enum):
    """
    Types of reports that can be generated.

    Each type serves a different documentation purpose:
    - INCIDENT_REPORT: Immediate incident documentation
    - RUNBOOK: Reusable troubleshooting guide
    - POST_MORTEM: Detailed retrospective analysis
    """
    INCIDENT_REPORT = "incident_report"
    RUNBOOK = "runbook"
    POST_MORTEM = "post_mortem"


class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "pending"       # Queued for generation
    GENERATING = "generating" # Currently being generated
    COMPLETED = "completed"   # Successfully generated
    FAILED = "failed"         # Generation failed


class RunbookSource(str, Enum):
    """
    Source of runbook content.

    Runbooks can be generated from:
    - INCIDENT_DRIVEN: Based on resolved case investigation
    - DOCUMENT_DRIVEN: Based on uploaded documentation
    """
    INCIDENT_DRIVEN = "incident_driven"
    DOCUMENT_DRIVEN = "document_driven"


class CaseReport(Base):
    """
    Generated case report/documentation.

    Stores the generated content along with metadata for
    versioning, closure linking, and retrieval.
    """

    __tablename__ = "case_reports"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Foreign key to Case
    case_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    # Report type and title
    report_type: Mapped[ReportType] = mapped_column(
        SQLEnum(ReportType),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    # Content (Markdown format)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    format: Mapped[str] = mapped_column(String(20), default="markdown")

    # Generation tracking
    status: Mapped[ReportStatus] = mapped_column(
        SQLEnum(ReportStatus),
        default=ReportStatus.PENDING,
        index=True
    )
    generation_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Versioning (max 5 versions per type per case)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Closure linking
    linked_to_closure: Mapped[bool] = mapped_column(Boolean, default=False)

    # Additional metadata (for runbook source, tags, etc.)
    report_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<CaseReport(id={self.id}, type={self.report_type.value}, case={self.case_id}, v{self.version})>"

    @property
    def is_complete(self) -> bool:
        """Check if report generation is complete."""
        return self.status == ReportStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if report generation failed."""
        return self.status == ReportStatus.FAILED
