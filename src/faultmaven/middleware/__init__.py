"""
FaultMaven middleware components.

Provides request processing middleware for:
- Request logging with correlation IDs
- (Future) RBAC permission checking
- (Future) Opik LLM tracing
"""

from faultmaven.middleware.logging import (
    RequestLoggingMiddleware,
    get_request_id,
)

__all__ = [
    "RequestLoggingMiddleware",
    "get_request_id",
]
