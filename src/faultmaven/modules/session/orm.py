"""
Session module ORM models.

Note: Sessions are primarily stored in Redis for performance.
This ORM model is for audit/persistence purposes only.
"""

from datetime import datetime
from sqlalchemy import String, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from faultmaven.database import Base


class SessionAudit(Base):
    """
    Session audit log (optional - mainly stored in Redis).

    This tracks session creation/destruction for audit purposes.
    Active session data is in Redis via SessionStore.
    """

    __tablename__ = "session_audits"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Session identifier (matches Redis key)
    session_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # User reference (not a FK - user might be deleted)
    user_id: Mapped[str] = mapped_column(String(36), index=True)

    # Session data snapshot
    data: Mapped[dict] = mapped_column(JSON, default=dict)

    # Client info
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    destroyed_at: Mapped[datetime | None] = mapped_column(DateTime)

    def __repr__(self) -> str:
        return f"<SessionAudit(id={self.id}, session_id={self.session_id})>"
