"""
Infrastructure interfaces for FaultMaven.

These abstract interfaces decouple modules from Redis and other infrastructure.
"""

from datetime import timedelta
from typing import Any, Optional, Protocol
from enum import Enum


class SessionStore(Protocol):
    """
    Abstract session storage interface.

    Implementations:
    - RedisSessionStore (production)
    - MemorySessionStore (testing)
    """

    async def get(self, session_id: str) -> Optional[dict[str, Any]]:
        """Retrieve session data by ID."""
        ...

    async def set(
        self,
        session_id: str,
        data: dict[str, Any],
        ttl: Optional[timedelta] = None,
    ) -> None:
        """
        Store session data with optional TTL.

        Args:
            session_id: Session identifier
            data: Session data to store
            ttl: Time-to-live (expiration)
        """
        ...

    async def delete(self, session_id: str) -> bool:
        """
        Delete session. Returns True if deleted, False if not found.
        """
        ...

    async def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        ...

    async def extend_ttl(self, session_id: str, ttl: timedelta) -> bool:
        """
        Extend session TTL. Returns True if extended, False if not found.
        """
        ...


class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobQueue(Protocol):
    """
    Abstract job queue interface.

    Implementations:
    - RedisJobQueue (using Celery/RQ)
    - MemoryJobQueue (testing)
    """

    async def enqueue(
        self,
        job_type: str,
        payload: dict[str, Any],
        queue: str = "default",
        priority: int = 5,
        **options: Any,
    ) -> str:
        """
        Enqueue a background job.

        Args:
            job_type: Job type identifier (e.g., "embedding_generation")
            payload: Job parameters
            queue: Queue name
            priority: Priority (0=highest, 9=lowest)
            **options: Queue-specific options

        Returns:
            Job ID
        """
        ...

    async def get_status(self, job_id: str) -> Optional[JobStatus]:
        """Get job execution status."""
        ...

    async def get_result(self, job_id: str) -> Optional[Any]:
        """Get job result (if completed)."""
        ...

    async def cancel(self, job_id: str) -> bool:
        """Cancel a pending job."""
        ...


class Cache(Protocol):
    """
    Abstract cache interface.

    Implementations:
    - RedisCache (production)
    - MemoryCache (testing)
    """

    async def get(self, key: str) -> Optional[bytes]:
        """Retrieve cached value."""
        ...

    async def set(
        self,
        key: str,
        value: bytes,
        ttl: Optional[timedelta] = None,
    ) -> None:
        """
        Cache value with optional TTL.

        Args:
            key: Cache key
            value: Value to cache (bytes)
            ttl: Time-to-live
        """
        ...

    async def delete(self, key: str) -> bool:
        """Delete cached value."""
        ...

    async def invalidate(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        ...


class ResultStore(Protocol):
    """
    Abstract result storage for async operations (LLM responses, job results).

    Implementations:
    - RedisResultStore (production)
    - MemoryResultStore (testing)
    """

    async def get(self, job_id: str) -> Optional[Any]:
        """Retrieve result by job ID."""
        ...

    async def set(
        self,
        job_id: str,
        result: Any,
        ttl: Optional[timedelta] = None,
    ) -> None:
        """
        Store result with optional TTL.

        Args:
            job_id: Job/operation identifier
            result: Result data (will be JSON-serialized)
            ttl: Time-to-live (default: 1 hour)
        """
        ...

    async def delete(self, job_id: str) -> bool:
        """Delete result."""
        ...


class RateLimiter(Protocol):
    """
    Abstract rate limiter interface.

    Implementations:
    - RedisRateLimiter (production)
    - MemoryRateLimiter (testing)
    """

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: timedelta,
    ) -> bool:
        """
        Check if action is allowed within rate limit.

        Args:
            key: Rate limit key (e.g., "api:user:123")
            limit: Max requests in window
            window: Time window

        Returns:
            True if allowed, False if rate limited
        """
        ...

    async def get_remaining(
        self,
        key: str,
        limit: int,
        window: timedelta,
    ) -> int:
        """Get remaining requests in current window."""
        ...

    async def reset(self, key: str) -> None:
        """Reset rate limit for key."""
        ...
