"""
FaultMaven background workers package.

Provides Celery-based background task processing for:
- Document processing and indexing
- Report generation
- Long-running operations

Usage:
    # Start worker
    celery -A faultmaven.workers.celery_app worker --loglevel=info

    # Enqueue task
    from faultmaven.workers.tasks import process_document_task
    process_document_task.delay(document_id="123")
"""

from faultmaven.workers.celery_app import celery_app

__all__ = ["celery_app"]
