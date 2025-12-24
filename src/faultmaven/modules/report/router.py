"""
Report module API endpoints.

Provides REST API for report generation and management.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from faultmaven.modules.auth.dependencies import get_current_user
from faultmaven.modules.auth.orm import User
from faultmaven.modules.report.orm import ReportType, ReportStatus


router = APIRouter(prefix="/reports", tags=["reports"])


# --- Request/Response Models ---

class GenerateReportRequest(BaseModel):
    """Request to generate a report."""
    report_type: ReportType = Field(..., description="Type of report to generate")
    use_llm: bool = Field(True, description="Use LLM for enhanced generation")


class LinkToClosureRequest(BaseModel):
    """Request to link reports to case closure."""
    report_ids: List[str] = Field(..., description="Report IDs to link")


class ReportSummary(BaseModel):
    """Summary of a report (without content)."""
    id: str
    case_id: str
    report_type: str
    title: str
    status: str
    version: int
    is_current: bool
    created_at: str
    generated_at: Optional[str] = None
    generation_time_ms: int = 0


class ReportDetail(BaseModel):
    """Full report with content."""
    id: str
    case_id: str
    report_type: str
    title: str
    content: str
    format: str
    status: str
    version: int
    is_current: bool
    linked_to_closure: bool
    created_at: str
    generated_at: Optional[str] = None
    generation_time_ms: int = 0


# --- Helper to get service ---
# Note: This will be properly wired in Phase 5

async def get_report_service(request):
    """Get report service from request state."""
    # This is a placeholder - will be wired in dependencies.py
    from faultmaven.modules.report.service import ReportService
    from faultmaven.modules.case.service import CaseService

    # Get from request.app.state (set during startup)
    db_session = request.state.db_session
    case_service = CaseService(db_session)
    llm_provider = getattr(request.app.state, 'llm_provider', None)

    return ReportService(
        db_session=db_session,
        case_service=case_service,
        llm_provider=llm_provider,
    )


# --- Endpoints ---

@router.get("/case/{case_id}", response_model=List[ReportSummary])
async def list_case_reports(
    case_id: str,
    report_type: Optional[str] = None,
    include_history: bool = False,
    current_user: User = Depends(get_current_user),
    # report_service will be injected via Depends in Phase 5
):
    """
    List reports for a case.

    Args:
        case_id: Case ID
        report_type: Optional filter by type (incident_report, runbook, post_mortem)
        include_history: Include non-current versions (default: False)

    Returns:
        List of report summaries
    """
    # Placeholder - will use injected service in Phase 5
    from fastapi import Request
    # For now, return empty list until properly wired
    return []


@router.post("/case/{case_id}/generate")
async def generate_report(
    case_id: str,
    request: GenerateReportRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generate a new report for a case.

    Supports up to 5 versions per report type per case.

    Args:
        case_id: Case ID
        request: Generation request with report type

    Returns:
        Generated report summary
    """
    # Placeholder - will use injected service in Phase 5
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Report generation will be available after dependency wiring"
    )


@router.get("/case/{case_id}/recommendations")
async def get_recommendations(
    case_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get report generation recommendations for a case.

    Based on case status, suggests which reports should be generated.

    Args:
        case_id: Case ID

    Returns:
        Recommendations including available types and suggested actions
    """
    # Placeholder - will use injected service in Phase 5
    return {
        "case_id": case_id,
        "case_status": "unknown",
        "available_for_generation": [],
        "recommended": [],
        "existing_reports": [],
        "message": "Recommendations will be available after dependency wiring"
    }


@router.get("/{report_id}", response_model=ReportDetail)
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific report with full content.

    Args:
        report_id: Report ID

    Returns:
        Full report with content
    """
    # Placeholder - will use injected service in Phase 5
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Report not found"
    )


@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a report.

    Cannot delete reports linked to case closure.

    Args:
        report_id: Report ID

    Returns:
        Success confirmation
    """
    # Placeholder - will use injected service in Phase 5
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Report not found"
    )


@router.post("/case/{case_id}/link-closure")
async def link_to_closure(
    case_id: str,
    request: LinkToClosureRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Link reports to case closure.

    Marks specified reports as archived with the case.
    Only works for resolved/closed cases.

    Args:
        case_id: Case ID
        request: Report IDs to link

    Returns:
        Number of reports linked
    """
    # Placeholder - will use injected service in Phase 5
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Closure linking will be available after dependency wiring"
    )


@router.get("/case/{case_id}/download/{report_id}")
async def download_report(
    case_id: str,
    report_id: str,
    format: str = "markdown",
    current_user: User = Depends(get_current_user),
):
    """
    Download a report in specified format.

    Currently supports markdown format only.

    Args:
        case_id: Case ID
        report_id: Report ID
        format: Output format (markdown)

    Returns:
        Report content for download
    """
    # Placeholder - will use injected service in Phase 5
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Report not found"
    )
