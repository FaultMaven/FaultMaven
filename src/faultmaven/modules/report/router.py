"""
Report module API endpoints.

Provides REST API for report generation and management.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from faultmaven.modules.auth.dependencies import get_current_user
from faultmaven.modules.auth.orm import User
from faultmaven.modules.report.orm import ReportType, ReportStatus
from faultmaven.modules.report.service import ReportService
from faultmaven.dependencies import get_report_service


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


def _report_to_summary(report) -> dict:
    """Convert report ORM to summary dict."""
    return {
        "id": report.id,
        "case_id": report.case_id,
        "report_type": report.report_type.value,
        "title": report.title,
        "status": report.status.value,
        "version": report.version,
        "is_current": report.is_current,
        "created_at": report.created_at.isoformat(),
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "generation_time_ms": report.generation_time_ms or 0,
    }


def _report_to_detail(report) -> dict:
    """Convert report ORM to detail dict."""
    return {
        "id": report.id,
        "case_id": report.case_id,
        "report_type": report.report_type.value,
        "title": report.title,
        "content": report.content,
        "format": report.format,
        "status": report.status.value,
        "version": report.version,
        "is_current": report.is_current,
        "linked_to_closure": report.linked_to_closure,
        "created_at": report.created_at.isoformat(),
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "generation_time_ms": report.generation_time_ms or 0,
    }


# --- Endpoints ---

@router.get("/case/{case_id}", response_model=List[ReportSummary])
async def list_case_reports(
    case_id: str,
    report_type: Optional[str] = None,
    include_history: bool = False,
    current_user: User = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service),
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
    # Parse report type if provided
    type_filter = None
    if report_type:
        try:
            type_filter = ReportType(report_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid report type: {report_type}"
            )

    reports = await report_service.list_reports(
        case_id=case_id,
        report_type=type_filter,
        current_only=not include_history,
    )

    return [_report_to_summary(r) for r in reports]


@router.post("/case/{case_id}/generate", response_model=ReportSummary)
async def generate_report(
    case_id: str,
    request: GenerateReportRequest,
    current_user: User = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service),
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
    try:
        report = await report_service.generate_report(
            case_id=case_id,
            report_type=request.report_type,
            use_llm=request.use_llm,
        )
        return _report_to_summary(report)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}"
        )


@router.get("/case/{case_id}/recommendations")
async def get_recommendations(
    case_id: str,
    current_user: User = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service),
):
    """
    Get report generation recommendations for a case.

    Based on case status, suggests which reports should be generated.

    Args:
        case_id: Case ID

    Returns:
        Recommendations including available types and suggested actions
    """
    recommendations = await report_service.get_recommendations(case_id)
    return recommendations


@router.get("/{report_id}", response_model=ReportDetail)
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service),
):
    """
    Get a specific report with full content.

    Args:
        report_id: Report ID

    Returns:
        Full report with content
    """
    report = await report_service.get_report(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    return _report_to_detail(report)


@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service),
):
    """
    Delete a report.

    Cannot delete reports linked to case closure.

    Args:
        report_id: Report ID

    Returns:
        Success confirmation
    """
    success = await report_service.delete_report(report_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or cannot be deleted (linked to closure)"
        )
    return {"message": "Report deleted successfully"}


@router.post("/case/{case_id}/link-closure")
async def link_to_closure(
    case_id: str,
    request: LinkToClosureRequest,
    current_user: User = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service),
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
    try:
        count = await report_service.link_to_closure(
            case_id=case_id,
            report_ids=request.report_ids,
        )
        return {"linked_count": count, "report_ids": request.report_ids}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/case/{case_id}/download/{report_id}")
async def download_report(
    case_id: str,
    report_id: str,
    format: str = "markdown",
    current_user: User = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service),
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
    if format != "markdown":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only markdown format is currently supported"
        )

    report = await report_service.get_report(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    if report.case_id != case_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found for this case"
        )

    return PlainTextResponse(
        content=report.content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{report.title.replace(" ", "_")}.md"'
        }
    )
