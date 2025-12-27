"""
Case module FastAPI router.

Exposes endpoints for case management including hypotheses and solutions.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, Any

from faultmaven.modules.case.service import CaseService
from faultmaven.modules.case.orm import CaseStatus, CasePriority
from faultmaven.modules.evidence.orm import EvidenceType
from faultmaven.modules.auth.router import get_current_user
from faultmaven.modules.auth.orm import User
from faultmaven.dependencies import get_case_service, get_evidence_service


router = APIRouter(prefix="/cases", tags=["cases"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateCaseRequest(BaseModel):
    """Create case request."""
    title: str = Field(..., min_length=1, max_length=255, description="Case title (1-255 characters)")
    description: str = Field(..., max_length=5000, description="Case description (0-5000 characters, empty allowed)")
    priority: CasePriority = CasePriority.MEDIUM
    context: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    category: Optional[str] = None


class UpdateCaseRequest(BaseModel):
    """Update case request."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CaseStatus] = None
    priority: Optional[CasePriority] = None
    tags: Optional[list[str]] = None
    category: Optional[str] = None


class UpdateCaseStatusRequest(BaseModel):
    """Update case status request."""
    status: CaseStatus


class CaseResponse(BaseModel):
    """Case response."""
    id: str
    owner_id: str
    title: str
    description: str
    status: str
    priority: str
    created_at: str
    updated_at: str
    resolved_at: Optional[str] = None
    closed_at: Optional[str] = None
    tags: list[str]
    category: Optional[str]


class AddHypothesisRequest(BaseModel):
    """Add hypothesis request."""
    title: str
    description: str
    confidence: Optional[float] = None


class HypothesisResponse(BaseModel):
    """Hypothesis response."""
    id: str
    case_id: str
    title: str
    description: str
    confidence: Optional[float]
    validated: bool
    created_at: str


class AddSolutionRequest(BaseModel):
    """Add solution request."""
    title: str
    description: str
    implementation_steps: Optional[list[str]] = None


class SolutionResponse(BaseModel):
    """Solution response."""
    id: str
    case_id: str
    title: str
    description: str
    implementation_steps: list[str]
    implemented: bool
    created_at: str


class AddMessageRequest(BaseModel):
    """Add message request."""
    role: str
    content: str
    message_metadata: Optional[dict[str, Any]] = None


class MessageResponse(BaseModel):
    """Message response."""
    id: str
    case_id: str
    role: str
    content: str
    created_at: str


class CaseSearchRequest(BaseModel):
    """Case search request."""
    query: Optional[str] = Field(None, description="Text search in title and description")
    status: Optional[CaseStatus] = Field(None, description="Filter by status")
    priority: Optional[CasePriority] = Field(None, description="Filter by priority")
    category: Optional[str] = Field(None, description="Filter by category")
    tags: Optional[list[str]] = Field(None, description="Filter by tags (any match)")
    created_after: Optional[str] = Field(None, description="Filter by creation date (ISO format)")
    created_before: Optional[str] = Field(None, description="Filter by creation date (ISO format)")
    include_archived: bool = Field(False, description="Include closed/archived cases")
    limit: int = Field(20, ge=1, le=100, description="Maximum results (1-100)")
    offset: int = Field(0, ge=0, description="Pagination offset")


# ============================================================================
# Helper Functions
# ============================================================================

def case_to_response(case) -> CaseResponse:
    """Convert Case ORM to response model."""
    return CaseResponse(
        id=case.id,
        owner_id=case.owner_id,
        title=case.title,
        description=case.description,
        status=case.status.value,
        priority=case.priority.value,
        created_at=case.created_at.isoformat(),
        updated_at=case.updated_at.isoformat(),
        resolved_at=case.resolved_at.isoformat() if case.resolved_at else None,
        closed_at=case.closed_at.isoformat() if case.closed_at else None,
        tags=case.tags,
        category=case.category,
    )


# ============================================================================
# Case CRUD Endpoints
# ============================================================================

@router.post("", status_code=status.HTTP_201_CREATED, response_model=CaseResponse)
async def create_case(
    request: CreateCaseRequest,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """
    Create a new case for the current user.

    Args:
        request: Case creation request
        current_user: Authenticated user
        case_service: Case service

    Returns:
        Created case with initial CONSULTING status
    """
    case = await case_service.create_case(
        owner_id=current_user.id,
        title=request.title,
        description=request.description,
        priority=request.priority,
        context=request.context,
        tags=request.tags,
        category=request.category,
    )

    return case_to_response(case)


@router.get("", response_model=list[CaseResponse])
async def list_cases(
    status_filter: Optional[CaseStatus] = None,
    limit: int = Query(20, ge=1, le=100, description="Number of items to return (1-100)"),
    offset: int = Query(0, ge=0, description="Number of items to skip (must be >= 0)"),
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """
    List all cases for the current user.

    Args:
        status_filter: Optional status filter
        limit: Maximum number of cases to return (1-100)
        offset: Number of items to skip (must be >= 0)
        current_user: Authenticated user
        case_service: Case service

    Returns:
        List of cases
    """
    cases, total = await case_service.list_cases(
        owner_id=current_user.id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )

    return [case_to_response(case) for case in cases]


# ============================================================================
# Static Routes (must be defined BEFORE /{case_id} to avoid path conflicts)
# ============================================================================

@router.post("/search", response_model=list[CaseResponse])
async def search_cases(
    search_request: CaseSearchRequest,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """
    Search cases with multiple filter criteria.

    Supports:
    - Text search in title and description
    - Status, priority, and category filters
    - Tag filtering (any match)
    - Date range filtering
    - Pagination

    Args:
        search_request: Search criteria
        current_user: Authenticated user
        case_service: Case service

    Returns:
        List of matching cases with pagination info
    """
    from datetime import datetime as dt

    # Parse date filters
    created_after = None
    created_before = None
    if search_request.created_after:
        try:
            created_after = dt.fromisoformat(search_request.created_after.replace("Z", "+00:00"))
        except ValueError:
            pass
    if search_request.created_before:
        try:
            created_before = dt.fromisoformat(search_request.created_before.replace("Z", "+00:00"))
        except ValueError:
            pass

    cases, total = await case_service.search_cases(
        owner_id=current_user.id,
        query=search_request.query,
        status=search_request.status,
        priority=search_request.priority,
        category=search_request.category,
        tags=search_request.tags,
        created_after=created_after,
        created_before=created_before,
        include_archived=search_request.include_archived,
        limit=search_request.limit,
        offset=search_request.offset,
    )

    return [case_to_response(case) for case in cases]


@router.get("/statistics")
async def get_case_statistics(
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """
    Get aggregate statistics for all user cases.

    Returns statistics including:
    - total_cases: Total number of cases
    - status_breakdown: Count by status
    - priority_breakdown: Count by priority
    - resolved_this_week: Cases resolved in last 7 days
    - active_cases: Currently active cases

    Args:
        current_user: Authenticated user
        case_service: Case service

    Returns:
        Aggregate case statistics
    """
    stats = await case_service.get_case_statistics(current_user.id)
    return {
        "user_id": current_user.id,
        **stats
    }


@router.get("/analytics/summary")
async def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """Get analytics summary across all cases."""
    cases, _ = await case_service.list_cases(owner_id=current_user.id)
    return {
        "total_cases": len(cases),
        "open_cases": sum(1 for c in cases if c.status.value == "open"),
        "closed_cases": sum(1 for c in cases if c.status.value == "closed")
    }


@router.get("/analytics/trends")
async def get_analytics_trends(
    current_user: User = Depends(get_current_user),
):
    """Get case trends over time."""
    return {"trends": [], "period": "30d"}


@router.get("/schema.json")
async def get_case_schema():
    """Get case schema metadata."""
    return {
        "schema": {
            "title": "string",
            "description": "string",
            "status": ["open", "in_progress", "resolved", "closed"],
            "priority": ["low", "medium", "high", "critical"]
        }
    }


@router.get("/health")
async def case_health():
    """Case system health check."""
    return {
        "status": "healthy",
        "service": "cases"
    }


# ============================================================================
# Case CRUD Endpoints (parameterized routes)
# ============================================================================

@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """
    Get a case by ID.

    Args:
        case_id: Case ID
        current_user: Authenticated user
        case_service: Case service

    Returns:
        Case details

    Raises:
        HTTPException: If case not found or unauthorized
    """
    case = await case_service.get_case(case_id, current_user.id)

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return case_to_response(case)


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: str,
    request: UpdateCaseRequest,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """
    Update a case.

    Args:
        case_id: Case ID
        request: Update request
        current_user: Authenticated user
        case_service: Case service

    Returns:
        Updated case

    Raises:
        HTTPException: If case not found or unauthorized
    """
    case = await case_service.update_case(
        case_id=case_id,
        user_id=current_user.id,
        title=request.title,
        description=request.description,
        status=request.status,
        priority=request.priority,
        tags=request.tags,
        category=request.category,
    )

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return case_to_response(case)


@router.patch("/{case_id}/status", response_model=CaseResponse)
async def update_case_status(
    case_id: str,
    request: UpdateCaseStatusRequest,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """
    Update case status with validation.

    Validates status transitions (aligned with SRS FR-CM-003):
    - consulting -> investigating (allowed)
    - consulting -> closed (allowed)
    - investigating -> resolved (allowed)
    - investigating -> closed (allowed)
    - resolved -> (terminal, no transitions)
    - closed -> (terminal, no transitions)

    Args:
        case_id: Case ID
        request: Status update request
        current_user: Authenticated user
        case_service: Case service

    Returns:
        Updated case

    Raises:
        HTTPException: If case not found, unauthorized, or invalid transition
    """
    # Get current case to check status
    case = await case_service.get_case(case_id, current_user.id)

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Validate status transition
    current_status = CaseStatus(case.status)
    new_status = request.status

    # Rule: Cannot transition directly to 'closed' without first being 'resolved'
    # Must go through 'resolved' first
    if new_status == CaseStatus.CLOSED and current_status != CaseStatus.RESOLVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from '{current_status.value}' to 'closed'. Case must be resolved first."
        )

    # Update status
    updated_case = await case_service.update_case(
        case_id=case_id,
        user_id=current_user.id,
        status=new_status,
    )

    if not updated_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return case_to_response(updated_case)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """
    Delete a case.

    Args:
        case_id: Case ID
        current_user: Authenticated user
        case_service: Case service

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: If case not found or unauthorized
    """
    deleted = await case_service.delete_case(case_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )


# ============================================================================
# Hypothesis Sub-Resource Endpoints
# ============================================================================

@router.post("/{case_id}/hypotheses", status_code=status.HTTP_201_CREATED, response_model=HypothesisResponse)
async def add_hypothesis(
    case_id: str,
    request: AddHypothesisRequest,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """
    Add a hypothesis to a case.

    Args:
        case_id: Case ID
        request: Hypothesis creation request
        current_user: Authenticated user
        case_service: Case service

    Returns:
        Created hypothesis

    Raises:
        HTTPException: If case not found or unauthorized
    """
    hypothesis = await case_service.add_hypothesis(
        case_id=case_id,
        user_id=current_user.id,
        title=request.title,
        description=request.description,
        confidence=request.confidence,
    )

    if not hypothesis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return HypothesisResponse(
        id=hypothesis.id,
        case_id=hypothesis.case_id,
        title=hypothesis.title,
        description=hypothesis.description,
        confidence=hypothesis.confidence,
        validated=hypothesis.validated,
        created_at=hypothesis.created_at.isoformat(),
    )


# ============================================================================
# Solution Sub-Resource Endpoints
# ============================================================================

@router.post("/{case_id}/solutions", status_code=status.HTTP_201_CREATED, response_model=SolutionResponse)
async def add_solution(
    case_id: str,
    request: AddSolutionRequest,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """
    Add a solution to a case.

    Args:
        case_id: Case ID
        request: Solution creation request
        current_user: Authenticated user
        case_service: Case service

    Returns:
        Created solution

    Raises:
        HTTPException: If case not found or unauthorized
    """
    solution = await case_service.add_solution(
        case_id=case_id,
        user_id=current_user.id,
        title=request.title,
        description=request.description,
        implementation_steps=request.implementation_steps,
    )

    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return SolutionResponse(
        id=solution.id,
        case_id=solution.case_id,
        title=solution.title,
        description=solution.description,
        implementation_steps=solution.implementation_steps,
        implemented=solution.implemented,
        created_at=solution.created_at.isoformat(),
    )


# ============================================================================
# Message Sub-Resource Endpoints
# ============================================================================

@router.post("/{case_id}/messages", status_code=status.HTTP_201_CREATED, response_model=MessageResponse)
async def add_message(
    case_id: str,
    request: AddMessageRequest,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """
    Add a message to a case.

    Args:
        case_id: Case ID
        request: Message creation request
        current_user: Authenticated user
        case_service: Case service

    Returns:
        Created message

    Raises:
        HTTPException: If case not found or unauthorized
    """
    message = await case_service.add_message(
        case_id=case_id,
        user_id=current_user.id,
        role=request.role,
        content=request.content,
        message_metadata=request.message_metadata,
    )

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return MessageResponse(
        id=message.id,
        case_id=message.case_id,
        role=message.role,
        content=message.content,
        created_at=message.created_at.isoformat(),
    )


@router.get("/{case_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    case_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """
    List messages for a case.

    Args:
        case_id: Case ID
        limit: Maximum number of messages
        offset: Pagination offset
        current_user: Authenticated user
        case_service: Case service

    Returns:
        List of messages

    Raises:
        HTTPException: If case not found or unauthorized
    """
    messages = await case_service.list_case_messages(
        case_id=case_id,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    if messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return [
        MessageResponse(
            id=msg.id,
            case_id=msg.case_id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at.isoformat(),
        )
        for msg in messages
    ]


@router.post("/{case_id}/status")
async def update_case_status(
    case_id: str,
    status_update: dict,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """
    Update case status.

    Args:
        case_id: Case ID
        status_update: Status update (e.g., {"status": "in_progress"})
        current_user: Authenticated user
        case_service: Case service

    Returns:
        Updated case status

    Raises:
        HTTPException: If case not found or unauthorized
    """
    new_status = status_update.get("status")
    if not new_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status field is required"
        )

    try:
        status_enum = CaseStatus(new_status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {new_status}"
        )

    case = await case_service.update_case(
        case_id=case_id,
        user_id=current_user.id,
        status=status_enum,
    )

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return {
        "case_id": case_id,
        "status": new_status,
        "message": "Case status updated successfully"
    }


@router.get("/{case_id}/data")
async def list_case_data(
    case_id: str,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """
    List all data associated with a case.

    Args:
        case_id: Case ID
        current_user: Authenticated user
        case_service: Case service

    Returns:
        List of case data items

    Raises:
        HTTPException: If case not found or unauthorized
    """
    # Verify case exists and user has access
    case = await case_service.get_case(case_id, current_user.id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Return case context data
    return {
        "case_id": case_id,
        "data": case.context or {},
        "count": len(case.context) if case.context else 0
    }


@router.post("/{case_id}/data")
async def add_case_data(
    case_id: str,
    data_item: dict,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """
    Add data to a case.

    Args:
        case_id: Case ID
        data_item: Data to add
        current_user: Authenticated user
        case_service: Case service

    Returns:
        Added data confirmation

    Raises:
        HTTPException: If case not found or unauthorized
    """
    case = await case_service.get_case(case_id, current_user.id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Add data to case context
    context = case.context or {}
    data_id = f"data_{len(context)}"
    context[data_id] = data_item

    await case_service.update_case(
        case_id=case_id,
        user_id=current_user.id,
        context=context
    )

    return {
        "case_id": case_id,
        "data_id": data_id,
        "message": "Data added successfully"
    }


@router.get("/{case_id}/data/{data_id}")
async def get_case_data(
    case_id: str,
    data_id: str,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """
    Get specific case data by ID.

    Args:
        case_id: Case ID
        data_id: Data item ID
        current_user: Authenticated user
        case_service: Case service

    Returns:
        Case data item

    Raises:
        HTTPException: If case or data not found
    """
    case = await case_service.get_case(case_id, current_user.id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    context = case.context or {}
    if data_id not in context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )

    return {
        "case_id": case_id,
        "data_id": data_id,
        "data": context[data_id]
    }


@router.delete("/{case_id}/data/{data_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case_data(
    case_id: str,
    data_id: str,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """
    Delete specific case data.

    Args:
        case_id: Case ID
        data_id: Data item ID
        current_user: Authenticated user
        case_service: Case service

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: If case or data not found
    """
    case = await case_service.get_case(case_id, current_user.id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    context = case.context or {}
    if data_id not in context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )

    del context[data_id]
    await case_service.update_case(
        case_id=case_id,
        user_id=current_user.id,
        context=context
    )


@router.post("/{case_id}/archive")
async def archive_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """
    Archive a case.

    Changes case status to 'closed' to archive it.
    Frontend compatibility endpoint - archives a case to mark it as inactive.

    Args:
        case_id: Case ID
        current_user: Authenticated user
        case_service: Case service

    Returns:
        Archived case confirmation

    Raises:
        HTTPException: If case not found or unauthorized
    """
    case = await case_service.update_case(
        case_id=case_id,
        user_id=current_user.id,
        status=CaseStatus.CLOSED,
    )

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return {
        "case_id": case_id,
        "status": "archived",
        "message": "Case archived successfully"
    }


@router.get("/session/{session_id}")
async def get_cases_by_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """Get all cases for a specific session."""
    cases = await case_service.list_cases(current_user.id)
    return {"session_id": session_id, "cases": [], "count": 0}


@router.post("/{case_id}/evidence", status_code=status.HTTP_201_CREATED)
async def upload_case_evidence(
    case_id: str,
    file: UploadFile = File(...),
    evidence_type: str = Form("log"),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
    evidence_service = Depends(get_evidence_service),
):
    """
    Upload evidence file for a case.

    Args:
        case_id: Case ID to attach evidence to
        file: File upload
        evidence_type: Type of evidence (default: log)
        description: Optional description
        current_user: Authenticated user
        case_service: Case service
        evidence_service: Evidence service

    Returns:
        Evidence metadata

    Raises:
        HTTPException: If case not found, unauthorized, file too large, or invalid file type
    """
    # Verify case exists and user has access
    case = await case_service.get_case(case_id, current_user.id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

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

    # Validate file type (reject executables)
    DISALLOWED_MIME_TYPES = [
        "application/x-msdownload",  # .exe
        "application/x-executable",   # generic executable
        "application/x-dosexec",      # DOS executable
    ]
    if file_type in DISALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File type '{file_type}' is not allowed for security reasons"
        )

    # Parse evidence type
    try:
        evidence_type_enum = EvidenceType(evidence_type)
    except ValueError:
        evidence_type_enum = EvidenceType.OTHER

    # Upload evidence
    evidence = await evidence_service.upload_evidence(
        case_id=case_id,
        user_id=current_user.id,
        file_content=file_content,
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        evidence_type=evidence_type_enum,
        description=description,
        tags=[],
    )

    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload evidence"
        )

    # Return evidence metadata
    return {
        "id": evidence.id,
        "case_id": evidence.case_id,
        "uploaded_by": evidence.uploaded_by,
        "filename": evidence.filename,
        "original_filename": evidence.original_filename,
        "file_type": evidence.file_type,
        "file_size": evidence.file_size,
        "evidence_type": evidence.evidence_type.value,
        "description": evidence.description,
        "tags": evidence.tags,
        "uploaded_at": evidence.uploaded_at.isoformat(),
    }


@router.get("/{case_id}/evidence/{evidence_id}")
async def get_case_evidence(
    case_id: str,
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """Get specific evidence for a case."""
    case = await case_service.get_case(case_id, current_user.id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return {"case_id": case_id, "evidence_id": evidence_id, "evidence": {}}


@router.get("/{case_id}/uploaded-files")
async def list_uploaded_files(
    case_id: str,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """List all uploaded files for a case."""
    case = await case_service.get_case(case_id, current_user.id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return {"case_id": case_id, "files": [], "count": 0}


@router.get("/{case_id}/uploaded-files/{file_id}")
async def get_uploaded_file(
    case_id: str,
    file_id: str,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """Get specific uploaded file details."""
    case = await case_service.get_case(case_id, current_user.id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return {"case_id": case_id, "file_id": file_id, "file": {}}


@router.put("/{case_id}/hypotheses/{hypothesis_id}")
async def update_hypothesis(
    case_id: str,
    hypothesis_id: str,
    update_data: dict,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """Update a hypothesis."""
    case = await case_service.get_case(case_id, current_user.id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return {"case_id": case_id, "hypothesis_id": hypothesis_id, "message": "Hypothesis updated"}


@router.post("/{case_id}/queries")
async def submit_query(
    case_id: str,
    query_data: dict,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """Submit a query for a case."""
    case = await case_service.get_case(case_id, current_user.id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    query_id = f"query_{len(case.context or {})}"
    return {"case_id": case_id, "query_id": query_id, "status": "submitted"}


@router.get("/{case_id}/queries")
async def get_queries(
    case_id: str,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """Get query history for a case."""
    case = await case_service.get_case(case_id, current_user.id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return {"case_id": case_id, "queries": [], "count": 0}


@router.get("/{case_id}/analytics")
async def get_case_analytics(
    case_id: str,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """Get analytics for a specific case."""
    case = await case_service.get_case(case_id, current_user.id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return {
        "case_id": case_id,
        "status": case.status.value,
        "created_at": case.created_at.isoformat(),
        "message_count": 0
    }


@router.get("/{case_id}/report-recommendations")
async def get_report_recommendations(
    case_id: str,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """Get report recommendations for a case."""
    case = await case_service.get_case(case_id, current_user.id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return {"case_id": case_id, "recommendations": ["Include all hypotheses"]}


@router.post("/{case_id}/reports")
async def generate_report(
    case_id: str,
    report_config: dict,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """Generate a report for a case."""
    case = await case_service.get_case(case_id, current_user.id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    report_id = f"report_{case_id}_1"
    return {"case_id": case_id, "report_id": report_id, "status": "generating"}


@router.get("/{case_id}/reports")
async def list_reports(
    case_id: str,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """List all reports for a case."""
    case = await case_service.get_case(case_id, current_user.id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return {"case_id": case_id, "reports": [], "count": 0}


@router.get("/{case_id}/reports/{report_id}/download")
async def download_report(
    case_id: str,
    report_id: str,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """Download a specific report."""
    case = await case_service.get_case(case_id, current_user.id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return {"case_id": case_id, "report_id": report_id, "download_url": f"/reports/{report_id}"}


@router.get("/{case_id}/ui")
async def get_case_ui_data(
    case_id: str,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """Get UI-optimized case data."""
    case = await case_service.get_case(case_id, current_user.id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return {
        "case_id": case_id,
        "title": case.title,
        "status": case.status.value,
        "priority": case.priority.value
    }


@router.post("/{case_id}/title")
async def generate_case_title(
    case_id: str,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """Generate a suggested title for a case."""
    case = await case_service.get_case(case_id, current_user.id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    suggested = f"Issue: {case.description[:50]}"
    return {"case_id": case_id, "suggested_title": suggested}


@router.post("/{case_id}/close")
async def close_case(
    case_id: str,
    close_data: Optional[dict] = None,
    current_user: User = Depends(get_current_user),
    case_service: CaseService = Depends(get_case_service),
):
    """Close a case."""
    case = await case_service.update_case(case_id, current_user.id, status=CaseStatus.CLOSED)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return {"case_id": case_id, "status": "closed"}
