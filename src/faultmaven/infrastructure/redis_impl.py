"""Redis implementations of infrastructure interfaces."""

import json
from datetime import timedelta
from typing import Any, Optional
from redis.asyncio import Redis, ConnectionPool

from faultmaven.infrastructure.interfaces import (
    SessionStore,
    JobQueue,
    JobStatus,
    Cache,
    ResultStore,
    RateLimiter,
)


class RedisSessionStore(SessionStore):
    """Redis-backed session storage."""

    def __init__(self, redis: Redis, prefix: str = "session:"):
        """
        Initialize Redis session store.

        Args:
            redis: Redis client
            prefix: Key prefix for sessions
        """
        self.redis = redis
        self.prefix = prefix

    def _make_key(self, session_id: str) -> str:
        """Create Redis key for session."""
        return f"{self.prefix}{session_id}"

    async def get(self, session_id: str) -> Optional[dict[str, Any]]:
        """Retrieve session data."""
        data = await self.redis.get(self._make_key(session_id))
        if data:
            return json.loads(data)
        return None

    async def set(
        self,
        session_id: str,
        data: dict[str, Any],
        ttl: Optional[timedelta] = None,
    ) -> None:
        """Store session data."""
        key = self._make_key(session_id)
        value = json.dumps(data)

        if ttl:
            await self.redis.setex(key, int(ttl.total_seconds()), value)
        else:
            await self.redis.set(key, value)

    async def delete(self, session_id: str) -> bool:
        """Delete session."""
        result = await self.redis.delete(self._make_key(session_id))
        return result > 0

    async def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        return await self.redis.exists(self._make_key(session_id)) > 0

    async def extend_ttl(self, session_id: str, ttl: timedelta) -> bool:
        """Extend session TTL."""
        result = await self.redis.expire(
            self._make_key(session_id),
            int(ttl.total_seconds())
        )
        return result


class RedisJobQueue(JobQueue):
    """
    Redis-backed job queue using Celery-style task management.

    Note: This is a simplified implementation. In production, use Celery or RQ.
    """

    def __init__(self, redis: Redis, prefix: str = "job:"):
        """
        Initialize Redis job queue.

        Args:
            redis: Redis client
            prefix: Key prefix for jobs
        """
        self.redis = redis
        self.prefix = prefix

    def _make_status_key(self, job_id: str) -> str:
        """Create Redis key for job status."""
        return f"{self.prefix}status:{job_id}"

    def _make_result_key(self, job_id: str) -> str:
        """Create Redis key for job result."""
        return f"{self.prefix}result:{job_id}"

    def _make_queue_key(self, queue: str) -> str:
        """Create Redis key for queue."""
        return f"{self.prefix}queue:{queue}"

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

        # Store job metadata
        job_data = {
            "job_id": job_id,
            "job_type": job_type,
            "payload": payload,
            "priority": priority,
            **options,
        }

        # Set initial status
        await self.redis.setex(
            self._make_status_key(job_id),
            3600,  # 1 hour TTL
            JobStatus.PENDING.value,
        )

        # Add to queue (using sorted set with priority)
        await self.redis.zadd(
            self._make_queue_key(queue),
            {json.dumps(job_data): priority},
        )

        return job_id

    async def get_status(self, job_id: str) -> Optional[JobStatus]:
        """Get job status."""
        status = await self.redis.get(self._make_status_key(job_id))
        if status:
            return JobStatus(status.decode())
        return None

    async def get_result(self, job_id: str) -> Optional[Any]:
        """Get job result."""
        data = await self.redis.get(self._make_result_key(job_id))
        if data:
            return json.loads(data)
        return None

    async def cancel(self, job_id: str) -> bool:
        """Cancel a pending job."""
        # Set status to failed
        result = await self.redis.setex(
            self._make_status_key(job_id),
            3600,
            JobStatus.FAILED.value,
        )
        return bool(result)


class CeleryJobQueue(JobQueue):
    """
    Production implementation of JobQueue using Celery.
    Decouples the domain from the task runner.
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
        Enqueue a job using Celery.

        Args:
            job_type: Job type identifier (e.g. "knowledge.generate_embeddings")
            payload: Job payload data
            queue: Queue name (unused in Celery implementation)
            priority: Priority (unused in Celery implementation)
            **options: Additional options

        Returns:
            Job ID (Celery task ID)
        """
        # Import tasks dynamically to avoid circular imports
        from faultmaven.modules.knowledge.tasks import generate_embeddings_task

        if job_type == "knowledge.generate_embeddings":
            # .delay() is the standard Celery async trigger
            task = generate_embeddings_task.delay(payload["document_id"])
            return str(task.id)

        # We will add more job types here as we build them (e.g. "agent.run_investigation")
        raise ValueError(f"Unknown job type: {job_type}")

    async def get_status(self, job_id: str) -> Optional[JobStatus]:
        """Get job status from Celery."""
        from celery.result import AsyncResult
        from faultmaven.worker import celery_app

        result = AsyncResult(job_id, app=celery_app)

        if result.state == "PENDING":
            return JobStatus.PENDING
        elif result.state == "STARTED":
            return JobStatus.RUNNING
        elif result.state == "SUCCESS":
            return JobStatus.COMPLETED
        elif result.state in ("FAILURE", "REVOKED"):
            return JobStatus.FAILED
        return None

    async def get_result(self, job_id: str) -> Optional[Any]:
        """Get job result from Celery."""
        from celery.result import AsyncResult
        from faultmaven.worker import celery_app

        result = AsyncResult(job_id, app=celery_app)

        if result.ready():
            return result.result
        return None

    async def cancel(self, job_id: str) -> bool:
        """Cancel a Celery job."""
        from celery.result import AsyncResult
        from faultmaven.worker import celery_app

        result = AsyncResult(job_id, app=celery_app)
        result.revoke(terminate=True)
        return True


class RedisCache(Cache):
    """Redis-backed cache."""

    def __init__(self, redis: Redis, prefix: str = "cache:"):
        """
        Initialize Redis cache.

        Args:
            redis: Redis client
            prefix: Key prefix for cache entries
        """
        self.redis = redis
        self.prefix = prefix

    def _make_key(self, key: str) -> str:
        """Create Redis key."""
        return f"{self.prefix}{key}"

    async def get(self, key: str) -> Optional[bytes]:
        """Retrieve cached value."""
        return await self.redis.get(self._make_key(key))

    async def set(
        self,
        key: str,
        value: bytes,
        ttl: Optional[timedelta] = None,
    ) -> None:
        """Cache value."""
        redis_key = self._make_key(key)

        if ttl:
            await self.redis.setex(redis_key, int(ttl.total_seconds()), value)
        else:
            await self.redis.set(redis_key, value)

    async def delete(self, key: str) -> bool:
        """Delete cached value."""
        result = await self.redis.delete(self._make_key(key))
        return result > 0

    async def invalidate(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        # Note: SCAN is more efficient than KEYS for production
        cursor = 0
        deleted = 0

        while True:
            cursor, keys = await self.redis.scan(
                cursor,
                match=self._make_key(pattern),
                count=100,
            )

            if keys:
                deleted += await self.redis.delete(*keys)

            if cursor == 0:
                break

        return deleted

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return await self.redis.exists(self._make_key(key)) > 0


class RedisResultStore(ResultStore):
    """Redis-backed result storage for async operations."""

    def __init__(self, redis: Redis, prefix: str = "result:", default_ttl: int = 3600):
        """
        Initialize Redis result store.

        Args:
            redis: Redis client
            prefix: Key prefix for results
            default_ttl: Default TTL in seconds (1 hour)
        """
        self.redis = redis
        self.prefix = prefix
        self.default_ttl = default_ttl

    def _make_key(self, job_id: str) -> str:
        """Create Redis key for result."""
        return f"{self.prefix}{job_id}"

    async def get(self, job_id: str) -> Optional[Any]:
        """Retrieve result."""
        data = await self.redis.get(self._make_key(job_id))
        if data:
            return json.loads(data)
        return None

    async def set(
        self,
        job_id: str,
        result: Any,
        ttl: Optional[timedelta] = None,
    ) -> None:
        """Store result."""
        key = self._make_key(job_id)
        value = json.dumps(result)
        ttl_seconds = int(ttl.total_seconds()) if ttl else self.default_ttl

        await self.redis.setex(key, ttl_seconds, value)

    async def delete(self, job_id: str) -> bool:
        """Delete result."""
        result = await self.redis.delete(self._make_key(job_id))
        return result > 0


class RedisRateLimiter(RateLimiter):
    """Redis-backed rate limiter using sliding window."""

    def __init__(self, redis: Redis, prefix: str = "ratelimit:"):
        """
        Initialize Redis rate limiter.

        Args:
            redis: Redis client
            prefix: Key prefix for rate limit counters
        """
        self.redis = redis
        self.prefix = prefix

    def _make_key(self, key: str) -> str:
        """Create Redis key for rate limit."""
        return f"{self.prefix}{key}"

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: timedelta,
    ) -> bool:
        """Check if action is allowed."""
        import time

        redis_key = self._make_key(key)
        now = time.time()
        window_start = now - window.total_seconds()

        # Use sorted set for sliding window
        async with self.redis.pipeline(transaction=True) as pipe:
            # Remove old entries
            pipe.zremrangebyscore(redis_key, 0, window_start)
            # Count current entries
            pipe.zcard(redis_key)
            # Add current request
            pipe.zadd(redis_key, {str(now): now})
            # Set expiration
            pipe.expire(redis_key, int(window.total_seconds()))

            results = await pipe.execute()
            current_count = results[1]

        return current_count < limit

    async def get_remaining(
        self,
        key: str,
        limit: int,
        window: timedelta,
    ) -> int:
        """Get remaining requests."""
        import time

        redis_key = self._make_key(key)
        now = time.time()
        window_start = now - window.total_seconds()

        # Count entries in current window
        count = await self.redis.zcount(redis_key, window_start, now)
        return max(0, limit - count)

    async def reset(self, key: str) -> None:
        """Reset rate limit."""
        await self.redis.delete(self._make_key(key))


# Utility function to create Redis client
async def create_redis_client(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None,
    max_connections: int = 10,
) -> Redis:
    """
    Create Redis client with connection pooling.

    Args:
        host: Redis host
        port: Redis port
        db: Redis database number
        password: Redis password (optional)
        max_connections: Maximum connections in pool

    Returns:
        Redis client
    """
    pool = ConnectionPool(
        host=host,
        port=port,
        db=db,
        password=password,
        max_connections=max_connections,
        decode_responses=False,
    )

    return Redis(connection_pool=pool)
