"""
Task status API endpoints.

Provides REST API for checking background task status.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from faultmaven.workers.celery_app import celery_app
from faultmaven.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskStatusResponse(BaseModel):
    """Task status response."""
    task_id: str
    status: str
    result: dict | None = None
    error: str | None = None


class EnqueueDocumentRequest(BaseModel):
    """Request to enqueue document processing."""
    document_id: str
    user_id: str


class EnqueueReportRequest(BaseModel):
    """Request to enqueue report generation."""
    case_id: str
    report_type: str
    user_id: str


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get status of a background task.

    Args:
        task_id: Celery task ID

    Returns:
        Task status and result if complete
    """
    result = celery_app.AsyncResult(task_id)

    response = TaskStatusResponse(
        task_id=task_id,
        status=result.status,
    )

    if result.successful():
        response.result = result.result
    elif result.failed():
        response.error = str(result.result)

    return response


@router.post("/documents/process")
async def enqueue_document_processing(request: EnqueueDocumentRequest):
    """
    Enqueue a document for background processing.

    Args:
        request: Document processing request

    Returns:
        Task ID for status tracking
    """
    from faultmaven.workers.tasks import process_document_task

    task = process_document_task.delay(
        document_id=request.document_id,
        user_id=request.user_id,
    )

    logger.info(
        "document_task_enqueued",
        document_id=request.document_id,
        task_id=task.id,
    )

    return {
        "task_id": task.id,
        "status": "queued",
        "document_id": request.document_id,
    }


@router.post("/reports/generate")
async def enqueue_report_generation(request: EnqueueReportRequest):
    """
    Enqueue a report for background generation.

    Args:
        request: Report generation request

    Returns:
        Task ID for status tracking
    """
    from faultmaven.workers.tasks import generate_report_task

    task = generate_report_task.delay(
        case_id=request.case_id,
        report_type=request.report_type,
        user_id=request.user_id,
    )

    logger.info(
        "report_task_enqueued",
        case_id=request.case_id,
        report_type=request.report_type,
        task_id=task.id,
    )

    return {
        "task_id": task.id,
        "status": "queued",
        "case_id": request.case_id,
        "report_type": request.report_type,
    }


@router.post("/health-check")
async def enqueue_health_check():
    """
    Enqueue a health check task.

    Used to verify Celery worker is running.

    Returns:
        Task ID for status tracking
    """
    from faultmaven.workers.tasks import health_check_task

    task = health_check_task.delay()

    return {
        "task_id": task.id,
        "status": "queued",
    }


@router.delete("/{task_id}")
async def revoke_task(task_id: str, terminate: bool = False):
    """
    Revoke (cancel) a pending task.

    Args:
        task_id: Celery task ID
        terminate: If True, terminate running task (SIGTERM)

    Returns:
        Revocation confirmation
    """
    celery_app.control.revoke(task_id, terminate=terminate)

    logger.info(
        "task_revoked",
        task_id=task_id,
        terminated=terminate,
    )

    return {
        "task_id": task_id,
        "status": "revoked",
        "terminated": terminate,
    }
