"""In-memory implementations of infrastructure interfaces for testing."""

import time
from datetime import timedelta
from typing import Any, Optional
from collections import defaultdict

from faultmaven.infrastructure.interfaces import (
    SessionStore,
    JobQueue,
    JobStatus,
    Cache,
    ResultStore,
    RateLimiter,
)


class MemorySessionStore(SessionStore):
    """In-memory session storage for testing."""

    def __init__(self):
        self._sessions: dict[str, tuple[dict[str, Any], Optional[float]]] = {}

    def _is_expired(self, session_id: str) -> bool:
        """Check if session is expired."""
        if session_id not in self._sessions:
            return True

        _, expiry = self._sessions[session_id]
        if expiry and time.time() > expiry:
            del self._sessions[session_id]
            return True

        return False

    async def get(self, session_id: str) -> Optional[dict[str, Any]]:
        """Retrieve session data."""
        if self._is_expired(session_id):
            return None

        data, _ = self._sessions.get(session_id, (None, None))
        return data

    async def set(
        self,
        session_id: str,
        data: dict[str, Any],
        ttl: Optional[timedelta] = None,
    ) -> None:
        """Store session data."""
        expiry = None
        if ttl:
            expiry = time.time() + ttl.total_seconds()

        self._sessions[session_id] = (data.copy(), expiry)

    async def delete(self, session_id: str) -> bool:
        """Delete session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    async def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        return not self._is_expired(session_id)

    async def extend_ttl(self, session_id: str, ttl: timedelta) -> bool:
        """Extend session TTL."""
        if self._is_expired(session_id):
            return False

        data, _ = self._sessions[session_id]
        expiry = time.time() + ttl.total_seconds()
        self._sessions[session_id] = (data, expiry)
        return True


class MemoryJobQueue(JobQueue):
    """In-memory job queue for testing."""

    def __init__(self):
        self._jobs: dict[str, dict[str, Any]] = {}
        self._statuses: dict[str, JobStatus] = {}
        self._results: dict[str, Any] = {}

    async def enqueue(
        self,
        job_type: str,
        payload: dict[str, Any],
        queue: str = "default",
        priority: int = 5,
        **options: Any,
    ) -> str:
        """Enqueue a job."""
        import uuid
        job_id = str(uuid.uuid4())

        self._jobs[job_id] = {
            "job_type": job_type,
            "payload": payload,
            "queue": queue,
            "priority": priority,
            **options,
        }
        self._statuses[job_id] = JobStatus.PENDING

        return job_id

    async def get_status(self, job_id: str) -> Optional[JobStatus]:
        """Get job status."""
        return self._statuses.get(job_id)

    async def get_result(self, job_id: str) -> Optional[Any]:
        """Get job result."""
        return self._results.get(job_id)

    async def cancel(self, job_id: str) -> bool:
        """Cancel a pending job."""
        if job_id in self._statuses:
            self._statuses[job_id] = JobStatus.FAILED
            return True
        return False

    # Test helper methods
    def set_status(self, job_id: str, status: JobStatus) -> None:
        """Test helper: Set job status."""
        self._statuses[job_id] = status

    def set_result(self, job_id: str, result: Any) -> None:
        """Test helper: Set job result."""
        self._results[job_id] = result
        self._statuses[job_id] = JobStatus.COMPLETED


class MemoryCache(Cache):
    """In-memory cache for testing."""

    def __init__(self):
        self._cache: dict[str, tuple[bytes, Optional[float]]] = {}

    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired."""
        if key not in self._cache:
            return True

        _, expiry = self._cache[key]
        if expiry and time.time() > expiry:
            del self._cache[key]
            return True

        return False

    async def get(self, key: str) -> Optional[bytes]:
        """Retrieve cached value."""
        if self._is_expired(key):
            return None

        data, _ = self._cache.get(key, (None, None))
        return data

    async def set(
        self,
        key: str,
        value: bytes,
        ttl: Optional[timedelta] = None,
    ) -> None:
        """Cache value."""
        expiry = None
        if ttl:
            expiry = time.time() + ttl.total_seconds()

        self._cache[key] = (value, expiry)

    async def delete(self, key: str) -> bool:
        """Delete cached value."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    async def invalidate(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        import fnmatch

        keys_to_delete = [
            k for k in self._cache.keys()
            if fnmatch.fnmatch(k, pattern)
        ]

        for key in keys_to_delete:
            del self._cache[key]

        return len(keys_to_delete)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return not self._is_expired(key)


class MemoryResultStore(ResultStore):
    """In-memory result storage for testing."""

    def __init__(self, default_ttl: int = 3600):
        self._results: dict[str, tuple[Any, Optional[float]]] = {}
        self.default_ttl = default_ttl

    def _is_expired(self, job_id: str) -> bool:
        """Check if result is expired."""
        if job_id not in self._results:
            return True

        _, expiry = self._results[job_id]
        if expiry and time.time() > expiry:
            del self._results[job_id]
            return True

        return False

    async def get(self, job_id: str) -> Optional[Any]:
        """Retrieve result."""
        if self._is_expired(job_id):
            return None

        data, _ = self._results.get(job_id, (None, None))
        return data

    async def set(
        self,
        job_id: str,
        result: Any,
        ttl: Optional[timedelta] = None,
    ) -> None:
        """Store result."""
        ttl_seconds = ttl.total_seconds() if ttl else self.default_ttl
        expiry = time.time() + ttl_seconds

        self._results[job_id] = (result, expiry)

    async def delete(self, job_id: str) -> bool:
        """Delete result."""
        if job_id in self._results:
            del self._results[job_id]
            return True
        return False


class MemoryRateLimiter(RateLimiter):
    """In-memory rate limiter for testing."""

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: timedelta,
    ) -> bool:
        """Check if action is allowed."""
        now = time.time()
        window_start = now - window.total_seconds()

        # Remove old requests
        self._requests[key] = [
            t for t in self._requests[key]
            if t > window_start
        ]

        # Check limit
        if len(self._requests[key]) < limit:
            self._requests[key].append(now)
            return True

        return False

    async def get_remaining(
        self,
        key: str,
        limit: int,
        window: timedelta,
    ) -> int:
        """Get remaining requests."""
        now = time.time()
        window_start = now - window.total_seconds()

        # Count requests in window
        count = sum(1 for t in self._requests.get(key, []) if t > window_start)
        return max(0, limit - count)

    async def reset(self, key: str) -> None:
        """Reset rate limit."""
        if key in self._requests:
            del self._requests[key]
