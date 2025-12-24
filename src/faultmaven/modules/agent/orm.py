"""
Agent module ORM models.

Agent state is primarily in Redis/ResultStore.
These models are for audit/analytics purposes.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import String, DateTime, JSON, Text, Integer, Float, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from faultmaven.database import Base


class ChatSessionStatus(str, Enum):
    """Chat session status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ChatSession(Base):
    """
    Chat session audit log.

    Active sessions are in Redis via ResultStore.
    This is for historical tracking and analytics.
    """

    __tablename__ = "chat_sessions"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Session reference
    case_id: Mapped[str | None] = mapped_column(String(36), index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)

    # Session metadata
    status: Mapped[ChatSessionStatus] = mapped_column(
        SQLEnum(ChatSessionStatus),
        default=ChatSessionStatus.ACTIVE
    )

    # Message count
    message_count: Mapped[int] = mapped_column(Integer, default=0)

    # LLM usage
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost: Mapped[float | None] = mapped_column(Float)  # USD

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
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, status={self.status})>"


class LLMRequest(Base):
    """
    Individual LLM request log (for analytics and cost tracking).
    """

    __tablename__ = "llm_requests"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Session reference
    session_id: Mapped[str | None] = mapped_column(String(36), index=True)
    case_id: Mapped[str | None] = mapped_column(String(36), index=True)

    # Request data
    model: Mapped[str] = mapped_column(String(100))
    provider: Mapped[str] = mapped_column(String(50))  # "openai", "anthropic", "ollama"

    # Prompt (truncated)
    prompt_preview: Mapped[str | None] = mapped_column(Text)  # First 1000 chars
    response_preview: Mapped[str | None] = mapped_column(Text)  # First 1000 chars

    # Usage metrics
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # Performance
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    cost: Mapped[float | None] = mapped_column(Float)  # USD

    # Status
    success: Mapped[bool] = mapped_column(default=True)
    error_message: Mapped[str | None] = mapped_column(Text)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )

    def __repr__(self) -> str:
        return f"<LLMRequest(id={self.id}, model={self.model}, tokens={self.total_tokens})>"
