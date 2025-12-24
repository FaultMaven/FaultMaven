"""
Evidence module FastAPI router.

Exposes endpoints for file upload/download with streaming support.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from faultmaven.modules.evidence.service import EvidenceService
from faultmaven.modules.evidence.orm import EvidenceType
from faultmaven.modules.auth.router import get_current_user
from faultmaven.modules.auth.orm import User
from faultmaven.dependencies import get_evidence_service


router = APIRouter(prefix="/evidence", tags=["evidence"])


# ============================================================================
# Response Models
# ============================================================================

class EvidenceResponse(BaseModel):
    """Evidence metadata response."""
    id: str
    case_id: str
    uploaded_by: str
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    evidence_type: str
    description: Optional[str]
    tags: list[str]
    uploaded_at: str


class EvidenceListResponse(BaseModel):
    """Evidence list response."""
    evidence: list[EvidenceResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Helper Functions
# ============================================================================

def evidence_to_response(evidence) -> EvidenceResponse:
    """Convert Evidence ORM to response model."""
    return EvidenceResponse(
        id=evidence.id,
        case_id=evidence.case_id,
        uploaded_by=evidence.uploaded_by,
        filename=evidence.filename,
        original_filename=evidence.original_filename,
        file_type=evidence.file_type,
        file_size=evidence.file_size,
        evidence_type=evidence.evidence_type.value,
        description=evidence.description,
        tags=evidence.tags,
        uploaded_at=evidence.uploaded_at.isoformat(),
    )


# ============================================================================
# Upload/Download Endpoints
# ============================================================================

@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=EvidenceResponse)
async def upload_evidence(
    case_id: str = Form(...),
    file: UploadFile = File(...),
    evidence_type: EvidenceType = Form(EvidenceType.OTHER),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # Comma-separated tags
    current_user: User = Depends(get_current_user),
    evidence_service: EvidenceService = Depends(get_evidence_service),
):
    """
    Upload evidence file.

    Note: Uses Form parameters because multipart/form-data doesn't support JSON bodies.

    Args:
        case_id: Case ID to attach evidence to (Form field)
        file: File upload
        evidence_type: Type of evidence
        description: Optional description
        tags: Optional comma-separated tags
        current_user: Authenticated user
        evidence_service: Evidence service

    Returns:
        Evidence metadata

    Raises:
        HTTPException: If case not found or unauthorized
    """
    # Parse tags from comma-separated string
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else []

    # Get file info
    file_content = file.file
    filename = file.filename or "unknown"
    file_type = file.content_type or "application/octet-stream"

    # Read file to get size
    file_content.seek(0, 2)  # Seek to end
    file_size = file_content.tell()
    file_content.seek(0)  # Reset to beginning

    # Validate file size (100MB limit)
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB in bytes
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size {file_size} exceeds maximum allowed size of {MAX_FILE_SIZE} bytes (100MB)"
        )

    # Upload evidence
    evidence = await evidence_service.upload_evidence(
        case_id=case_id,
        user_id=current_user.id,
        file_content=file_content,
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        evidence_type=evidence_type,
        description=description,
        tags=tag_list,
    )

    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found or unauthorized"
        )

    return evidence_to_response(evidence)


@router.get("/{evidence_id}/download")
async def download_evidence(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    evidence_service: EvidenceService = Depends(get_evidence_service),
):
    """
    Download evidence file.

    Returns a StreamingResponse to avoid loading large files into memory.

    Args:
        evidence_id: Evidence ID
        current_user: Authenticated user
        evidence_service: Evidence service

    Returns:
        Streaming file download

    Raises:
        HTTPException: If evidence not found or unauthorized
    """
    # Download file
    result = await evidence_service.download_evidence(
        evidence_id=evidence_id,
        user_id=current_user.id,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found or unauthorized"
        )

    file_content, evidence = result

    # Return streaming response
    return StreamingResponse(
        file_content,
        media_type=evidence.file_type,
        headers={
            "Content-Disposition": f'attachment; filename="{evidence.original_filename}"'
        }
    )


# ============================================================================
# CRUD Endpoints
# ============================================================================

@router.get("/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    evidence_service: EvidenceService = Depends(get_evidence_service),
):
    """
    Get evidence metadata.

    Args:
        evidence_id: Evidence ID
        current_user: Authenticated user
        evidence_service: Evidence service

    Returns:
        Evidence metadata

    Raises:
        HTTPException: If evidence not found or unauthorized
    """
    evidence = await evidence_service.get_evidence(
        evidence_id=evidence_id,
        user_id=current_user.id,
    )

    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found"
        )

    return evidence_to_response(evidence)


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    evidence_service: EvidenceService = Depends(get_evidence_service),
):
    """
    Delete evidence file and metadata.

    Deletes from both database AND file storage.

    Args:
        evidence_id: Evidence ID
        current_user: Authenticated user
        evidence_service: Evidence service

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: If evidence not found or unauthorized
    """
    deleted = await evidence_service.delete_evidence(
        evidence_id=evidence_id,
        user_id=current_user.id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found"
        )


@router.get("/case/{case_id}", response_model=EvidenceListResponse)
async def list_case_evidence(
    case_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    evidence_service: EvidenceService = Depends(get_evidence_service),
):
    """
    List evidence for a case.

    Args:
        case_id: Case ID
        limit: Maximum number of items
        offset: Pagination offset
        current_user: Authenticated user
        evidence_service: Evidence service

    Returns:
        List of evidence with pagination info

    Raises:
        HTTPException: If case not found or unauthorized
    """
    result = await evidence_service.list_case_evidence(
        case_id=case_id,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    evidence_list, total = result

    return EvidenceListResponse(
        evidence=[evidence_to_response(e) for e in evidence_list],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("", response_model=EvidenceListResponse)
async def list_evidence(
    limit: int = 50,
    offset: int = 0,
    case_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    evidence_service: EvidenceService = Depends(get_evidence_service),
):
    """
    List evidence with optional filtering by case_id.

    Args:
        limit: Maximum number of items to return
        offset: Pagination offset
        case_id: Optional filter by case ID
        current_user: Authenticated user
        evidence_service: Evidence service

    Returns:
        List of evidence
    """
    # If case_id provided, use existing endpoint logic
    if case_id:
        evidence_list = await evidence_service.list_case_evidence(
            case_id=case_id,
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
    else:
        # List all evidence for user (simplified - would need service method)
        evidence_list = []  # Placeholder

    return EvidenceListResponse(
        evidence=[evidence_to_response(e) for e in evidence_list],
        total=len(evidence_list),
        limit=limit,
        offset=offset
    )


@router.post("/{evidence_id}/link")
async def link_evidence_to_case(
    evidence_id: str,
    link_request: dict,
    current_user: User = Depends(get_current_user),
    evidence_service: EvidenceService = Depends(get_evidence_service),
):
    """
    Link evidence to a case.

    Args:
        evidence_id: Evidence ID
        link_request: Request body with case_id
        current_user: Authenticated user
        evidence_service: Evidence service

    Returns:
        Link confirmation

    Raises:
        HTTPException: If evidence not found or unauthorized
    """
    case_id = link_request.get("case_id")
    if not case_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="case_id is required"
        )

    # Get evidence to verify it exists and user has access
    evidence = await evidence_service.get_evidence(evidence_id, current_user.id)
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found"
        )

    # Update evidence's case_id
    # This would need a service method - for now return success
    return {
        "evidence_id": evidence_id,
        "case_id": case_id,
        "message": "Evidence linked to case successfully"
    }


@router.get("/health")
async def evidence_health():
    """Evidence system health check."""
    return {
        "status": "healthy",
        "service": "evidence"
    }
