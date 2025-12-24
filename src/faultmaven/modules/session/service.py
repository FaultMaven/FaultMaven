"""
Session module service layer.

Handles session lifecycle management with Redis for active sessions
and PostgreSQL for audit/persistence.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from faultmaven.modules.session.orm import SessionAudit
from faultmaven.infrastructure.interfaces import SessionStore


class SessionService:
    """
    Service for session management.

    Manages both active sessions (Redis) and audit records (PostgreSQL).
    """

    def __init__(
        self,
        db_session: AsyncSession,
        session_store: SessionStore,
        default_ttl_hours: int = 24,
        max_sessions_per_user: int = 10,
    ):
        """
        Initialize session service.

        Args:
            db_session: Database session for audit records
            session_store: Redis session store for active sessions
            default_ttl_hours: Default session TTL in hours
            max_sessions_per_user: Maximum active sessions per user
        """
        self.db = db_session
        self.store = session_store
        self.default_ttl = timedelta(hours=default_ttl_hours)
        self.max_sessions = max_sessions_per_user

    async def create_session(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_data: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Create a new session.

        Args:
            user_id: User ID
            ip_address: Client IP address
            user_agent: Client user agent
            session_data: Initial session data

        Returns:
            Session ID
        """
        # Generate session ID
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        expires_at = now + self.default_ttl

        # Create session data
        data = session_data or {}
        data.update({
            "user_id": user_id,
            "created_at": now.isoformat(),
            "last_accessed_at": now.isoformat(),
        })

        # Store in Redis
        await self.store.set(
            session_id=session_id,
            data=data,
            ttl=self.default_ttl,
        )

        # Create audit record in PostgreSQL
        audit = SessionAudit(
            id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            data=data,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
            last_accessed_at=now,
            expires_at=expires_at,
        )
        self.db.add(audit)
        await self.db.commit()

        # Enforce session limit
        await self._enforce_session_limit(user_id)

        return session_id

    async def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """
        Get session data.

        Args:
            session_id: Session ID

        Returns:
            Session data if exists, None otherwise
        """
        data = await self.store.get(session_id)
        if data:
            # Update last accessed time
            data["last_accessed_at"] = datetime.utcnow().isoformat()
            await self.store.set(session_id, data, ttl=self.default_ttl)

            # Update audit record
            result = await self.db.execute(
                select(SessionAudit).where(SessionAudit.session_id == session_id)
            )
            audit = result.scalar_one_or_none()
            if audit:
                audit.last_accessed_at = datetime.utcnow()
                audit.data = data
                await self.db.commit()

        return data

    async def update_session(
        self,
        session_id: str,
        updates: dict[str, Any]
    ) -> bool:
        """
        Update session data.

        Args:
            session_id: Session ID
            updates: Data to update

        Returns:
            True if session was updated, False if not found
        """
        data = await self.store.get(session_id)
        if not data:
            return False

        # Merge updates
        data.update(updates)
        data["last_accessed_at"] = datetime.utcnow().isoformat()

        # Update Redis
        await self.store.set(session_id, data, ttl=self.default_ttl)

        # Update audit record
        result = await self.db.execute(
            select(SessionAudit).where(SessionAudit.session_id == session_id)
        )
        audit = result.scalar_one_or_none()
        if audit:
            audit.data = data
            audit.last_accessed_at = datetime.utcnow()
            await self.db.commit()

        return True

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete/revoke a session.

        Args:
            session_id: Session ID

        Returns:
            True if session was deleted, False if not found
        """
        # Delete from Redis
        deleted = await self.store.delete(session_id)

        # Mark as destroyed in audit record
        if deleted:
            result = await self.db.execute(
                select(SessionAudit).where(SessionAudit.session_id == session_id)
            )
            audit = result.scalar_one_or_none()
            if audit:
                audit.destroyed_at = datetime.utcnow()
                await self.db.commit()

        return deleted

    async def list_user_sessions(self, user_id: str) -> list[dict[str, Any]]:
        """
        List all active sessions for a user.

        Args:
            user_id: User ID

        Returns:
            List of session data
        """
        # Query audit records for user
        result = await self.db.execute(
            select(SessionAudit).where(
                SessionAudit.user_id == user_id,
                SessionAudit.destroyed_at == None,
                SessionAudit.expires_at > datetime.utcnow(),
            ).order_by(SessionAudit.last_accessed_at.desc())
        )
        audits = result.scalars().all()

        # Check which sessions still exist in Redis
        active_sessions = []
        for audit in audits:
            data = await self.store.get(audit.session_id)
            if data:
                active_sessions.append({
                    "session_id": audit.session_id,
                    "created_at": audit.created_at.isoformat(),
                    "last_accessed_at": audit.last_accessed_at.isoformat(),
                    "expires_at": audit.expires_at.isoformat(),
                    "ip_address": audit.ip_address,
                    "user_agent": audit.user_agent,
                    "data": data,
                })

        return active_sessions

    async def extend_session(self, session_id: str, ttl: Optional[timedelta] = None) -> bool:
        """
        Extend session TTL.

        Args:
            session_id: Session ID
            ttl: New TTL (default: use default_ttl)

        Returns:
            True if session was extended, False if not found
        """
        ttl = ttl or self.default_ttl
        extended = await self.store.extend_ttl(session_id, ttl)

        if extended:
            # Update audit record expiration
            result = await self.db.execute(
                select(SessionAudit).where(SessionAudit.session_id == session_id)
            )
            audit = result.scalar_one_or_none()
            if audit:
                audit.expires_at = datetime.utcnow() + ttl
                await self.db.commit()

        return extended

    async def delete_user_sessions(self, user_id: str, except_session_id: Optional[str] = None) -> int:
        """
        Delete all sessions for a user (except optionally one).

        Args:
            user_id: User ID
            except_session_id: Session ID to keep (e.g., current session)

        Returns:
            Number of sessions deleted
        """
        # Get all user sessions
        result = await self.db.execute(
            select(SessionAudit).where(
                SessionAudit.user_id == user_id,
                SessionAudit.destroyed_at == None,
            )
        )
        audits = result.scalars().all()

        deleted_count = 0
        for audit in audits:
            if except_session_id and audit.session_id == except_session_id:
                continue

            # Delete from Redis
            await self.store.delete(audit.session_id)

            # Mark as destroyed
            audit.destroyed_at = datetime.utcnow()
            deleted_count += 1

        await self.db.commit()
        return deleted_count

    async def _enforce_session_limit(self, user_id: str) -> None:
        """Enforce maximum sessions per user by deleting oldest sessions."""
        sessions = await self.list_user_sessions(user_id)

        if len(sessions) > self.max_sessions:
            # Sort by last accessed (oldest first)
            sessions_to_delete = sorted(
                sessions,
                key=lambda s: s["last_accessed_at"]
            )[: len(sessions) - self.max_sessions]

            for session in sessions_to_delete:
                await self.delete_session(session["session_id"])
