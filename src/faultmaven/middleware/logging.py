"""
Request logging middleware with correlation IDs.

Adds request ID tracking and structured logging for all HTTP requests.
"""

import time
import uuid
from contextvars import ContextVar
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from faultmaven.logging_config import get_logger, bind_context, clear_context


# Context variable to store request ID
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

logger = get_logger(__name__)


def get_request_id() -> str | None:
    """Get the current request ID from context."""
    return request_id_var.get()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request logging with correlation IDs.

    Features:
    - Generates or extracts request ID from X-Request-ID header
    - Binds request ID to all logs within the request
    - Logs request start and completion with timing
    - Adds X-Request-ID header to response
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_var.set(request_id)

        # Bind context for all logs in this request
        bind_context(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        # Extract client info
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")[:100]

        # Log request start
        logger.info(
            "request_started",
            client_ip=client_ip,
            user_agent=user_agent,
            query_params=str(request.query_params) if request.query_params else None,
        )

        start_time = time.perf_counter()

        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log successful response
            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log failed request
            logger.error(
                "request_failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2),
                exc_info=True,
            )
            raise

        finally:
            # Clear context after request
            clear_context()
            request_id_var.set(None)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, handling proxy headers."""
        # Check for forwarded headers (reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get first IP in chain (original client)
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct connection
        if request.client:
            return request.client.host

        return "unknown"
