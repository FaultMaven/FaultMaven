"""
Structured logging configuration with JSON output and correlation IDs.

Usage:
    from faultmaven.logging_config import configure_logging, get_logger

    configure_logging()  # Call once at startup
    logger = get_logger(__name__)
    logger.info("request_processed", user_id="123", latency_ms=45)
"""

import logging
import sys
from typing import Any

import structlog
from pythonjsonlogger import jsonlogger

from faultmaven.config import get_settings


def configure_logging() -> None:
    """
    Configure structured logging for the application.

    Sets up structlog with JSON output for production and
    human-readable output for development.
    """
    settings = get_settings()
    log_config = settings.observability.logging

    # Determine log level
    level = getattr(logging, log_config.level, logging.INFO)

    # Configure stdlib logging first
    logging.basicConfig(
        format="%(message)s",
        level=level,
        stream=sys.stdout,
    )

    # Set up processors based on environment
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if log_config.format == "json":
        # JSON format for production
        log_handler = logging.StreamHandler(sys.stdout)
        log_handler.setFormatter(
            jsonlogger.JsonFormatter(
                fmt="%(timestamp)s %(level)s %(name)s %(message)s",
                rename_fields={"levelname": "level", "name": "logger"},
            )
        )
        logging.root.handlers = [log_handler]

        structlog.configure(
            processors=shared_processors
            + [
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    else:
        # Human-readable format for development
        structlog.configure(
            processors=shared_processors
            + [
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger for the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """
    Bind context variables that will be included in all subsequent logs.

    Args:
        **kwargs: Key-value pairs to add to log context
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()
