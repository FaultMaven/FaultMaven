"""
Case module ORM models.

These models represent the investigation domain with proper foreign keys.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from enum import Enum
from sqlalchemy import String, DateTime, JSON, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from faultmaven.database import Base

if TYPE_CHECKING:
    from faultmaven.modules.auth.orm import User
    from faultmaven.modules.evidence.orm import Evidence


class CaseStatus(str, Enum):
    """Case investigation status."""
    CONSULTING = "consulting"
    VERIFYING = "verifying"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CasePriority(str, Enum):
    """Case priority level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Case(Base):
    """Investigation case."""

    __tablename__ = "cases"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Ownership (FOREIGN KEY to User)
    owner_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    # Basic info
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)

    # Status tracking
    status: Mapped[CaseStatus] = mapped_column(
        SQLEnum(CaseStatus),
        default=CaseStatus.CONSULTING,
        index=True
    )
    priority: Mapped[CasePriority] = mapped_column(
        SQLEnum(CasePriority),
        default=CasePriority.MEDIUM
    )

    # Investigation data
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    case_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # Tags and categorization
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    category: Mapped[str | None] = mapped_column(String(100))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="cases")

    hypotheses: Mapped[list["Hypothesis"]] = relationship(
        "Hypothesis",
        back_populates="case",
        cascade="all, delete-orphan"
    )

    solutions: Mapped[list["Solution"]] = relationship(
        "Solution",
        back_populates="case",
        cascade="all, delete-orphan"
    )

    messages: Mapped[list["CaseMessage"]] = relationship(
        "CaseMessage",
        back_populates="case",
        cascade="all, delete-orphan"
    )

    evidence: Mapped[list["Evidence"]] = relationship(
        "Evidence",
        back_populates="case",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Case(id={self.id}, title={self.title}, status={self.status})>"


class Hypothesis(Base):
    """Investigation hypothesis."""

    __tablename__ = "hypotheses"

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

    # Hypothesis content
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)

    # Validation
    confidence: Mapped[float | None] = mapped_column()  # 0.0 to 1.0
    validated: Mapped[bool] = mapped_column(default=False)
    validation_notes: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationship
    case: Mapped["Case"] = relationship("Case", back_populates="hypotheses")

    def __repr__(self) -> str:
        return f"<Hypothesis(id={self.id}, title={self.title})>"


class Solution(Base):
    """Proposed or implemented solution."""

    __tablename__ = "solutions"

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

    # Solution content
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    implementation_steps: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Effectiveness tracking
    implemented: Mapped[bool] = mapped_column(default=False)
    effectiveness: Mapped[float | None] = mapped_column()  # 0.0 to 1.0
    notes: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    implemented_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationship
    case: Mapped["Case"] = relationship("Case", back_populates="solutions")

    def __repr__(self) -> str:
        return f"<Solution(id={self.id}, title={self.title})>"


class CaseMessage(Base):
    """Chat message in case investigation."""

    __tablename__ = "case_messages"

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

    # Message data
    role: Mapped[str] = mapped_column(String(20))  # "user", "assistant", "system"
    content: Mapped[str] = mapped_column(Text)
    message_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    # Relationship
    case: Mapped["Case"] = relationship("Case", back_populates="messages")

    def __repr__(self) -> str:
        return f"<CaseMessage(id={self.id}, role={self.role})>"
