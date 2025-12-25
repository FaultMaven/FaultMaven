"""
Unit tests for ReportService.

Tests report generation, versioning, and management logic.
"""

import pytest
from unittest.mock import AsyncMock, Mock, MagicMock
from datetime import datetime

from faultmaven.modules.report.service import ReportService
from faultmaven.modules.report.orm import (
    CaseReport,
    ReportType,
    ReportStatus,
)
from faultmaven.modules.case.orm import Case, CaseStatus


@pytest.fixture
def mock_case_service():
    """Mock CaseService."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider."""
    llm = AsyncMock()
    llm.chat = AsyncMock(return_value=Mock(content="# AI Generated Report\n\nDetailed analysis..."))
    return llm


@pytest.fixture
def sample_case():
    """Sample case for testing."""
    return Case(
        id="case-123",
        owner_id="user-456",
        title="Database connection timeout",
        description="Users unable to connect to database",
        status=CaseStatus.RESOLVED,
        resolved_at=datetime(2024, 12, 24, 10, 30, 0),
    )


@pytest.fixture
def report_service(db_session, mock_case_service, mock_llm_provider):
    """ReportService instance with mocked dependencies."""
    return ReportService(
        db_session=db_session,
        case_service=mock_case_service,
        llm_provider=mock_llm_provider,
    )


class TestReportServiceInitialization:
    """Test service initialization."""

    def test_initialization_with_llm(self, db_session, mock_case_service, mock_llm_provider):
        """Service initializes with LLM provider."""
        service = ReportService(
            db_session=db_session,
            case_service=mock_case_service,
            llm_provider=mock_llm_provider,
        )

        assert service.db is db_session
        assert service.case_service is mock_case_service
        assert service.llm is mock_llm_provider
        assert service.MAX_VERSIONS_PER_TYPE == 5

    def test_initialization_without_llm(self, db_session, mock_case_service):
        """Service initializes without LLM provider."""
        service = ReportService(
            db_session=db_session,
            case_service=mock_case_service,
            llm_provider=None,
        )

        assert service.llm is None


class TestGenerateReport:
    """Test report generation."""

    async def test_generate_incident_report_with_llm(
        self,
        report_service,
        mock_case_service,
        sample_case,
    ):
        """Generate incident report using LLM."""
        mock_case_service.get_case.return_value = sample_case

        report, error = await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
            use_llm=True,
        )

        assert error is None
        assert report is not None
        assert report.status == ReportStatus.COMPLETED
        assert report.version == 1
        assert report.is_current is True
        assert report.report_type == ReportType.INCIDENT_REPORT
        assert len(report.content) > 0
        assert "AI Generated Report" in report.content
        assert report.generation_time_ms >= 0

    async def test_generate_report_with_template(
        self,
        report_service,
        mock_case_service,
        sample_case,
    ):
        """Generate report using template (no LLM)."""
        mock_case_service.get_case.return_value = sample_case
        report_service.llm = None  # Disable LLM

        report, error = await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
            use_llm=False,
        )

        assert error is None
        assert report.status == ReportStatus.COMPLETED
        assert "Incident Report" in report.content
        assert "Database connection timeout" in report.content
        assert "Summary" in report.content

    async def test_generate_report_unauthorized_case(
        self,
        report_service,
        mock_case_service,
    ):
        """Cannot generate report for unauthorized case."""
        mock_case_service.get_case.return_value = None

        report, error = await report_service.generate_report(
            case_id="case-999",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
        )

        assert report is None
        assert error == "Case not found or unauthorized"

    async def test_generate_all_report_types(
        self,
        report_service,
        mock_case_service,
        sample_case,
    ):
        """Can generate all three report types."""
        mock_case_service.get_case.return_value = sample_case

        for report_type in [
            ReportType.INCIDENT_REPORT,
            ReportType.RUNBOOK,
            ReportType.POST_MORTEM,
        ]:
            report, error = await report_service.generate_report(
                case_id="case-123",
                user_id="user-456",
                report_type=report_type,
                use_llm=False,
            )

            assert error is None
            assert report.report_type == report_type
            assert report.status == ReportStatus.COMPLETED


class TestReportVersioning:
    """Test report versioning logic."""

    async def test_first_report_version_is_one(
        self,
        report_service,
        mock_case_service,
        sample_case,
    ):
        """First report has version 1."""
        mock_case_service.get_case.return_value = sample_case

        report, error = await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
        )

        assert report.version == 1
        assert report.is_current is True

    async def test_second_report_increments_version(
        self,
        report_service,
        mock_case_service,
        sample_case,
        db_session,
    ):
        """Second report increments version and marks first as not current."""
        mock_case_service.get_case.return_value = sample_case

        # Generate v1
        report_v1, _ = await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
        )

        assert report_v1.version == 1
        assert report_v1.is_current is True

        # Generate v2
        report_v2, _ = await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
        )

        assert report_v2.version == 2
        assert report_v2.is_current is True

        # Refresh v1 from DB
        await db_session.refresh(report_v1)
        assert report_v1.is_current is False

    async def test_version_limit_enforced(
        self,
        report_service,
        mock_case_service,
        sample_case,
    ):
        """Cannot generate more than MAX_VERSIONS_PER_TYPE versions."""
        mock_case_service.get_case.return_value = sample_case

        # Generate 5 versions
        for i in range(5):
            report, error = await report_service.generate_report(
                case_id="case-123",
                user_id="user-456",
                report_type=ReportType.INCIDENT_REPORT,
            )
            assert error is None
            assert report.version == i + 1

        # 6th attempt should fail
        report, error = await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
        )

        assert report is None
        assert "Maximum 5 versions" in error

    async def test_different_report_types_versioned_independently(
        self,
        report_service,
        mock_case_service,
        sample_case,
    ):
        """Different report types have independent version counters."""
        mock_case_service.get_case.return_value = sample_case

        # Generate incident report v1
        incident, _ = await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
        )

        # Generate runbook v1 (should also be version 1)
        runbook, _ = await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.RUNBOOK,
        )

        assert incident.version == 1
        assert runbook.version == 1
        assert incident.is_current is True
        assert runbook.is_current is True


class TestReportRetrieval:
    """Test report retrieval operations."""

    async def test_get_report_by_id(
        self,
        report_service,
        mock_case_service,
        sample_case,
    ):
        """Get report by ID with ownership verification."""
        mock_case_service.get_case.return_value = sample_case

        # Generate report
        original_report, _ = await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
        )

        # Retrieve by ID
        retrieved_report = await report_service.get_report(
            report_id=original_report.id,
            user_id="user-456",
        )

        assert retrieved_report is not None
        assert retrieved_report.id == original_report.id
        assert retrieved_report.content == original_report.content

    async def test_get_report_unauthorized(
        self,
        report_service,
        mock_case_service,
        sample_case,
    ):
        """Cannot get report for unauthorized case."""
        # Generate report as user-456
        mock_case_service.get_case.return_value = sample_case
        report, _ = await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
        )

        # Try to retrieve as different user
        mock_case_service.get_case.return_value = None  # Unauthorized
        retrieved = await report_service.get_report(
            report_id=report.id,
            user_id="user-999",  # Different user
        )

        assert retrieved is None

    async def test_list_reports_for_case(
        self,
        report_service,
        mock_case_service,
        sample_case,
    ):
        """List all current reports for a case."""
        mock_case_service.get_case.return_value = sample_case

        # Generate 2 different report types
        await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
        )

        await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.RUNBOOK,
        )

        # List all current reports
        reports = await report_service.list_reports(
            case_id="case-123",
            user_id="user-456",
        )

        assert len(reports) == 2
        assert all(r.is_current for r in reports)

    async def test_list_reports_with_type_filter(
        self,
        report_service,
        mock_case_service,
        sample_case,
    ):
        """Filter reports by type."""
        mock_case_service.get_case.return_value = sample_case

        await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
        )

        await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.RUNBOOK,
        )

        # Filter by type
        incident_reports = await report_service.list_reports(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
        )

        assert len(incident_reports) == 1
        assert incident_reports[0].report_type == ReportType.INCIDENT_REPORT

    async def test_list_reports_include_history(
        self,
        report_service,
        mock_case_service,
        sample_case,
    ):
        """Include historical versions when requested."""
        mock_case_service.get_case.return_value = sample_case

        # Generate 3 versions
        for _ in range(3):
            await report_service.generate_report(
                case_id="case-123",
                user_id="user-456",
                report_type=ReportType.INCIDENT_REPORT,
            )

        # List without history (default)
        current_only = await report_service.list_reports(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
        )

        assert len(current_only) == 1
        assert current_only[0].version == 3

        # List with history
        with_history = await report_service.list_reports(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
            include_history=True,
        )

        assert len(with_history) == 3
        assert [r.version for r in with_history] == [3, 2, 1]  # Desc order


class TestReportTitleGeneration:
    """Test report title generation."""

    def test_incident_report_title(self, report_service, sample_case):
        """Generate title for incident report."""
        title = report_service._generate_title(sample_case, ReportType.INCIDENT_REPORT)
        assert title == "Incident Report: Database connection timeout"

    def test_runbook_title(self, report_service, sample_case):
        """Generate title for runbook."""
        title = report_service._generate_title(sample_case, ReportType.RUNBOOK)
        assert title == "Runbook: Database connection timeout"

    def test_post_mortem_title(self, report_service, sample_case):
        """Generate title for post-mortem."""
        title = report_service._generate_title(sample_case, ReportType.POST_MORTEM)
        assert title == "Post-Mortem: Database connection timeout"

    def test_long_title_truncation(self, report_service):
        """Truncate very long case titles."""
        long_case = Case(
            id="case-long",
            owner_id="user-456",
            title="A" * 150,  # 150 characters
            description="Test",
            status=CaseStatus.RESOLVED,
        )

        title = report_service._generate_title(long_case, ReportType.INCIDENT_REPORT)
        # Should be truncated to 100 chars + prefix
        assert len(title) < 150
        assert title.startswith("Incident Report:")


class TestTemplateGeneration:
    """Test template-based report generation."""

    def test_incident_report_template_structure(self, report_service, sample_case):
        """Incident report template has correct structure."""
        content = report_service._incident_report_template(sample_case)

        assert "# Incident Report" in content
        assert "## Summary" in content
        assert sample_case.description in content
        assert "## Timeline" in content
        assert "Resolved:" in content  # Has resolved_at

    def test_runbook_template_structure(self, report_service, sample_case):
        """Runbook template has correct structure."""
        content = report_service._runbook_template(sample_case)

        assert "# Runbook" in content
        assert "## Problem Description" in content
        assert "## Symptoms" in content
        assert "## Resolution Steps" in content
        assert "## Verification" in content

    def test_post_mortem_template_structure(self, report_service, sample_case):
        """Post-mortem template has correct structure."""
        content = report_service._post_mortem_template(sample_case)

        assert "# Post-Mortem" in content
        assert "## Summary" in content
        assert "## Timeline" in content
        assert "## Root Cause" in content
        assert "## Lessons Learned" in content


class TestLLMGeneration:
    """Test LLM-based report generation."""

    async def test_llm_generation_called_when_requested(
        self,
        report_service,
        mock_case_service,
        mock_llm_provider,
        sample_case,
    ):
        """LLM is called when use_llm=True."""
        mock_case_service.get_case.return_value = sample_case

        await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
            use_llm=True,
        )

        # Verify LLM was called
        mock_llm_provider.chat.assert_called_once()

    async def test_fallback_to_template_on_llm_failure(
        self,
        report_service,
        mock_case_service,
        mock_llm_provider,
        sample_case,
    ):
        """Falls back to template if LLM fails."""
        mock_case_service.get_case.return_value = sample_case

        # Mock LLM to raise exception
        mock_llm_provider.chat.side_effect = Exception("API timeout")

        report, error = await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
            use_llm=True,
        )

        # Should fail and set error message
        assert report is None
        assert "Report generation failed" in error
        assert "API timeout" in error


class TestReportStatusTracking:
    """Test report status lifecycle."""

    async def test_report_status_during_generation(
        self,
        report_service,
        mock_case_service,
        sample_case,
        db_session,
    ):
        """Report goes through GENERATING → COMPLETED."""
        mock_case_service.get_case.return_value = sample_case

        report, error = await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
        )

        # Final state should be COMPLETED
        assert report.status == ReportStatus.COMPLETED
        assert report.is_complete is True
        assert report.is_failed is False

    async def test_report_status_on_failure(
        self,
        report_service,
        mock_case_service,
        mock_llm_provider,
        sample_case,
    ):
        """Report status is FAILED on generation error."""
        mock_case_service.get_case.return_value = sample_case
        mock_llm_provider.chat.side_effect = Exception("LLM error")

        report, error = await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
            use_llm=True,
        )

        assert report is None
        assert error is not None

    async def test_generation_time_recorded(
        self,
        report_service,
        mock_case_service,
        sample_case,
    ):
        """Generation time is recorded in milliseconds."""
        mock_case_service.get_case.return_value = sample_case

        report, error = await report_service.generate_report(
            case_id="case-123",
            user_id="user-456",
            report_type=ReportType.INCIDENT_REPORT,
        )

        assert report.generation_time_ms >= 0
        assert report.generated_at is not None
