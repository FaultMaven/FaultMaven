"""
Celery background tasks.

Provides async-safe task implementations for long-running operations.
"""

import asyncio
from typing import Any

from celery import Task

from faultmaven.workers.celery_app import celery_app
from faultmaven.config import get_settings
from faultmaven.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseTask(Task):
    """
    Base task class with database session management.

    Provides lazy-loaded database connection for task execution.
    """

    _db_provider = None
    _settings = None

    @property
    def settings(self):
        """Get cached settings."""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    @property
    def db_provider(self):
        """Get lazy-loaded database provider."""
        if self._db_provider is None:
            from faultmaven.providers.core import CoreDataProvider
            self._db_provider = CoreDataProvider(
                connection_string=self.settings.database.url
            )
        return self._db_provider

    def get_session(self):
        """Get async database session."""
        return self.db_provider.session_factory()


def run_async(coro):
    """Run async coroutine in sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    base=DatabaseTask,
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
)
def process_document_task(
    self,
    document_id: str,
    user_id: str,
) -> dict[str, Any]:
    """
    Process an uploaded document in the background.

    Steps:
    1. Extract text content
    2. Generate embeddings
    3. Store in vector database
    4. Update document status

    Args:
        document_id: Document ID to process
        user_id: User who uploaded the document

    Returns:
        Processing result with status and metadata
    """
    logger.info(
        "document_processing_started",
        document_id=document_id,
        user_id=user_id,
        task_id=self.request.id,
    )

    try:
        result = run_async(
            _process_document_async(self, document_id, user_id)
        )

        logger.info(
            "document_processing_completed",
            document_id=document_id,
            chunks=result.get("chunk_count", 0),
        )

        return result

    except Exception as e:
        logger.error(
            "document_processing_failed",
            document_id=document_id,
            error=str(e),
            retry_count=self.request.retries,
        )
        raise


async def _process_document_async(
    task: DatabaseTask,
    document_id: str,
    user_id: str,
) -> dict[str, Any]:
    """Async implementation of document processing."""
    from faultmaven.modules.knowledge.orm import Document, DocumentStatus
    from sqlalchemy import select

    async with task.get_session() as session:
        # Get document
        result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            return {"status": "error", "error": "Document not found"}

        # Update status to processing
        document.status = DocumentStatus.PROCESSING
        await session.commit()

        try:
            # TODO: Implement actual processing
            # 1. Read file content
            # 2. Extract text (depends on file type)
            # 3. Chunk text
            # 4. Generate embeddings
            # 5. Store in vector DB

            # For now, mark as indexed with placeholder
            document.status = DocumentStatus.INDEXED
            document.chunk_count = 0
            await session.commit()

            return {
                "status": "success",
                "document_id": document_id,
                "chunk_count": 0,
            }

        except Exception as e:
            document.status = DocumentStatus.FAILED
            await session.commit()
            raise


@celery_app.task(
    base=DatabaseTask,
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def generate_report_task(
    self,
    case_id: str,
    report_type: str,
    user_id: str,
) -> dict[str, Any]:
    """
    Generate a report in the background.

    For long-running LLM-based report generation.

    Args:
        case_id: Case ID to generate report for
        report_type: Type of report (incident_report, runbook, post_mortem)
        user_id: User requesting the report

    Returns:
        Generation result with report ID
    """
    logger.info(
        "report_generation_started",
        case_id=case_id,
        report_type=report_type,
        task_id=self.request.id,
    )

    try:
        result = run_async(
            _generate_report_async(self, case_id, report_type, user_id)
        )

        logger.info(
            "report_generation_completed",
            case_id=case_id,
            report_id=result.get("report_id"),
        )

        return result

    except Exception as e:
        logger.error(
            "report_generation_failed",
            case_id=case_id,
            error=str(e),
        )
        raise


async def _generate_report_async(
    task: DatabaseTask,
    case_id: str,
    report_type: str,
    user_id: str,
) -> dict[str, Any]:
    """Async implementation of report generation."""
    from faultmaven.modules.report.orm import ReportType
    from faultmaven.modules.report.service import ReportService
    from faultmaven.modules.case.service import CaseService

    async with task.get_session() as session:
        case_service = CaseService(db_session=session)
        report_service = ReportService(
            db_session=session,
            case_service=case_service,
            llm_provider=None,  # TODO: Initialize LLM provider
        )

        report_type_enum = ReportType(report_type)
        report, error = await report_service.generate_report(
            case_id=case_id,
            user_id=user_id,
            report_type=report_type_enum,
        )

        if error:
            return {"status": "error", "error": error}

        return {
            "status": "success",
            "report_id": report.id,
            "report_type": report_type,
        }


@celery_app.task(bind=True)
def health_check_task(self) -> dict[str, Any]:
    """
    Simple health check task.

    Used to verify Celery worker is running.
    """
    return {
        "status": "healthy",
        "task_id": self.request.id,
        "worker": self.request.hostname,
    }
