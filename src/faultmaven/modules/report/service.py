"""
Report generation service.

Ported from legacy: services/domain/report_generation_service.py

Provides report generation and management for cases:
- Generate incident reports, runbooks, and post-mortems
- Version management (max 5 versions per type)
- Template-based and LLM-based generation
- Recommendations for report generation
"""

from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from faultmaven.modules.report.orm import (
    CaseReport,
    ReportType,
    ReportStatus,
    RunbookSource,
)
from faultmaven.modules.case.service import CaseService
from faultmaven.modules.case.orm import Case, CaseStatus


class ReportService:
    """
    Service for generating and managing case reports.

    Supports three report types with versioning and template/LLM generation.
    """

    MAX_VERSIONS_PER_TYPE = 5

    def __init__(
        self,
        db_session: AsyncSession,
        case_service: CaseService,
        llm_provider=None,
    ):
        """
        Initialize report service.

        Args:
            db_session: Database session
            case_service: CaseService for case access
            llm_provider: Optional LLM provider for AI generation
        """
        self.db = db_session
        self.case_service = case_service
        self.llm = llm_provider

    async def get_report(
        self,
        report_id: str,
        user_id: str
    ) -> Optional[CaseReport]:
        """
        Get a report by ID with ownership verification.

        Args:
            report_id: Report ID
            user_id: User ID for ownership verification

        Returns:
            CaseReport if found and authorized, None otherwise
        """
        result = await self.db.execute(
            select(CaseReport).where(CaseReport.id == report_id)
        )
        report = result.scalar_one_or_none()

        if not report:
            return None

        # Verify case ownership
        case = await self.case_service.get_case(report.case_id, user_id)
        if not case:
            return None

        return report

    async def list_reports(
        self,
        case_id: str,
        user_id: str,
        report_type: Optional[ReportType] = None,
        include_history: bool = False,
    ) -> List[CaseReport]:
        """
        List reports for a case.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification
            report_type: Optional filter by type
            include_history: Include non-current versions

        Returns:
            List of CaseReport objects
        """
        # Verify ownership
        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return []

        # Build query
        conditions = [CaseReport.case_id == case_id]

        if report_type:
            conditions.append(CaseReport.report_type == report_type)

        if not include_history:
            conditions.append(CaseReport.is_current == True)

        query = (
            select(CaseReport)
            .where(and_(*conditions))
            .order_by(CaseReport.report_type, CaseReport.version.desc())
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def generate_report(
        self,
        case_id: str,
        user_id: str,
        report_type: ReportType,
        use_llm: bool = True,
    ) -> Tuple[Optional[CaseReport], Optional[str]]:
        """
        Generate a report for a case.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification
            report_type: Type of report to generate
            use_llm: Whether to use LLM for generation (if available)

        Returns:
            Tuple of (CaseReport, error_message)
        """
        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return None, "Case not found or unauthorized"

        # Check regeneration limit
        existing = await self.list_reports(
            case_id, user_id, report_type, include_history=True
        )
        if len(existing) >= self.MAX_VERSIONS_PER_TYPE:
            return None, f"Maximum {self.MAX_VERSIONS_PER_TYPE} versions allowed per report type"

        # Determine version number
        current_version = len(existing) + 1

        # Mark previous versions as not current
        for old_report in existing:
            if old_report.is_current:
                old_report.is_current = False

        # Create report record
        report = CaseReport(
            id=str(uuid.uuid4()),
            case_id=case_id,
            report_type=report_type,
            title=self._generate_title(case, report_type),
            content="",
            status=ReportStatus.GENERATING,
            version=current_version,
            is_current=True,
            created_at=datetime.utcnow(),
        )

        self.db.add(report)
        await self.db.commit()

        # Generate content
        start_time = datetime.utcnow()

        try:
            if use_llm and self.llm:
                content = await self._llm_generate(case, report_type)
            else:
                content = self._template_generate(case, report_type)

            end_time = datetime.utcnow()
            generation_time = int((end_time - start_time).total_seconds() * 1000)

            # Update report with content
            report.content = content
            report.status = ReportStatus.COMPLETED
            report.generation_time_ms = generation_time
            report.generated_at = end_time

        except Exception as e:
            report.status = ReportStatus.FAILED
            report.error_message = str(e)

        await self.db.commit()
        await self.db.refresh(report)

        if report.is_failed:
            return None, f"Report generation failed: {report.error_message}"

        return report, None

    def _generate_title(self, case: Case, report_type: ReportType) -> str:
        """Generate report title based on case and type."""
        prefix = {
            ReportType.INCIDENT_REPORT: "Incident Report",
            ReportType.RUNBOOK: "Runbook",
            ReportType.POST_MORTEM: "Post-Mortem",
        }
        # Truncate case title if too long
        case_title = case.title[:100] if len(case.title) > 100 else case.title
        return f"{prefix[report_type]}: {case_title}"

    def _template_generate(self, case: Case, report_type: ReportType) -> str:
        """
        Generate report content using templates.

        Provides basic structure when LLM is not available.
        """
        templates = {
            ReportType.INCIDENT_REPORT: self._incident_report_template,
            ReportType.RUNBOOK: self._runbook_template,
            ReportType.POST_MORTEM: self._post_mortem_template,
        }

        template_fn = templates.get(report_type, self._incident_report_template)
        return template_fn(case)

    def _incident_report_template(self, case: Case) -> str:
        """Generate incident report template."""
        resolved_info = ""
        if case.resolved_at:
            resolved_info = f"- **Resolved:** {case.resolved_at.strftime('%Y-%m-%d %H:%M UTC')}"

        return f"""# Incident Report: {case.title}

## Summary

{case.description}

## Timeline

- **Created:** {case.created_at.strftime('%Y-%m-%d %H:%M UTC')}
- **Status:** {case.status.value.replace('_', ' ').title()}
{resolved_info}

## Impact Assessment

*To be completed based on investigation findings.*

## Root Cause

*Identified through investigation process.*

## Resolution

*Actions taken to resolve the incident.*

## Follow-up Actions

- [ ] Update monitoring and alerting
- [ ] Review and update runbooks
- [ ] Schedule post-mortem if needed

---
*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*
"""

    def _runbook_template(self, case: Case) -> str:
        """Generate runbook template."""
        return f"""# Runbook: {case.title}

## Overview

This runbook provides step-by-step guidance for troubleshooting and resolving issues similar to:

> {case.description}

## Prerequisites

- Access to relevant systems and logs
- Appropriate permissions for diagnostic commands
- Understanding of system architecture

## Diagnostic Steps

### Step 1: Verify Symptoms

1. Confirm the reported symptoms
2. Check affected scope (users, regions, services)
3. Note the exact time of first occurrence

### Step 2: Gather Initial Data

1. Collect relevant logs
2. Check recent deployments or changes
3. Review monitoring dashboards

### Step 3: Identify Root Cause

1. Form hypotheses based on symptoms
2. Test each hypothesis systematically
3. Correlate findings with timeline

## Resolution Steps

*To be completed based on validated root cause.*

### Immediate Mitigation

1. *Steps for immediate relief*

### Permanent Fix

1. *Steps for permanent resolution*

## Verification

1. Confirm symptoms are resolved
2. Verify system health metrics
3. Monitor for recurrence

## Escalation

If this runbook does not resolve the issue:
- Escalate to: *Team/Individual*
- Include: Diagnostic findings, steps attempted

---
*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*
*Source Case: {case.id}*
"""

    def _post_mortem_template(self, case: Case) -> str:
        """Generate post-mortem template."""
        return f"""# Post-Mortem: {case.title}

## Incident Summary

| Field | Value |
|-------|-------|
| **Incident ID** | {case.id} |
| **Date** | {case.created_at.strftime('%Y-%m-%d')} |
| **Duration** | *Calculate from timeline* |
| **Severity** | {case.priority.value.title()} |
| **Status** | {case.status.value.replace('_', ' ').title()} |

## Description

{case.description}

## Timeline

| Time | Event |
|------|-------|
| {case.created_at.strftime('%H:%M')} | Issue first reported |
| *TBD* | Investigation started |
| *TBD* | Root cause identified |
| *TBD* | Resolution implemented |
| *TBD* | Issue verified resolved |

## Root Cause Analysis

### What Happened

*Detailed description of the incident.*

### Why It Happened

*Root cause explanation with contributing factors.*

### 5 Whys Analysis

1. **Why?** *First level*
2. **Why?** *Second level*
3. **Why?** *Third level*
4. **Why?** *Fourth level*
5. **Why?** *Root cause*

## Impact

- **Users Affected:** *Number/percentage*
- **Duration:** *Time period*
- **Business Impact:** *Revenue, reputation, etc.*

## What Went Well

- *Positive aspects of incident response*

## What Could Be Improved

- *Areas for improvement*

## Action Items

| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| *Action 1* | *Owner* | *Date* | ⬜ |
| *Action 2* | *Owner* | *Date* | ⬜ |

## Lessons Learned

1. *Key takeaway 1*
2. *Key takeaway 2*

---
*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*
"""

    async def _llm_generate(self, case: Case, report_type: ReportType) -> str:
        """
        Generate report content using LLM.

        Enhances template with AI-generated insights when available.
        """
        # Get base template
        base_content = self._template_generate(case, report_type)

        if not self.llm:
            return base_content

        # Build prompt for LLM enhancement
        prompt = self._build_generation_prompt(case, report_type, base_content)

        try:
            from faultmaven.providers.interfaces import Message, MessageRole

            messages = [
                Message(
                    role=MessageRole.SYSTEM,
                    content="You are a technical writer creating incident documentation. "
                            "Enhance the provided template with relevant details based on the case information. "
                            "Maintain the markdown structure. Be concise and technical."
                ),
                Message(
                    role=MessageRole.USER,
                    content=prompt
                )
            ]

            response = await self.llm.complete(
                messages=messages,
                max_tokens=2000,
                temperature=0.3,  # Lower temperature for more consistent output
            )

            return response

        except Exception:
            # Fall back to template on LLM failure
            return base_content

    def _build_generation_prompt(
        self,
        case: Case,
        report_type: ReportType,
        template: str
    ) -> str:
        """Build prompt for LLM report generation."""
        type_instructions = {
            ReportType.INCIDENT_REPORT: (
                "Generate a concise incident report. Focus on timeline, impact, and resolution."
            ),
            ReportType.RUNBOOK: (
                "Generate a practical runbook with clear diagnostic and resolution steps. "
                "Make it reusable for similar future incidents."
            ),
            ReportType.POST_MORTEM: (
                "Generate a thorough post-mortem. Include root cause analysis, timeline, "
                "and actionable lessons learned."
            ),
        }

        return f"""Case Information:
- Title: {case.title}
- Description: {case.description}
- Status: {case.status.value}
- Priority: {case.priority.value}
- Created: {case.created_at.isoformat()}

Instructions: {type_instructions.get(report_type, '')}

Base Template:
{template}

Please enhance this template with specific details from the case information.
Maintain the markdown structure and fill in the placeholder sections where possible.
"""

    async def get_recommendations(
        self,
        case_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Get report generation recommendations for a case.

        Suggests which reports can/should be generated based on case state.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification

        Returns:
            Recommendations dict
        """
        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return {"error": "Case not found"}

        existing = await self.list_reports(case_id, user_id)
        existing_types = {r.report_type for r in existing}

        # Determine available report types
        available = []
        for rt in ReportType:
            type_reports = await self.list_reports(
                case_id, user_id, rt, include_history=True
            )
            if len(type_reports) < self.MAX_VERSIONS_PER_TYPE:
                available.append(rt.value)

        # Recommendations based on case status
        recommended = []
        if case.status == CaseStatus.RESOLVED:
            if ReportType.INCIDENT_REPORT not in existing_types:
                recommended.append("incident_report")
            if ReportType.RUNBOOK not in existing_types:
                recommended.append("runbook")
            if ReportType.POST_MORTEM not in existing_types:
                recommended.append("post_mortem")
        elif case.status == CaseStatus.INVESTIGATING:
            if ReportType.INCIDENT_REPORT not in existing_types:
                recommended.append("incident_report")
        elif case.status == CaseStatus.CLOSED:
            if ReportType.POST_MORTEM not in existing_types:
                recommended.append("post_mortem")

        return {
            "case_id": case_id,
            "case_status": case.status.value,
            "available_for_generation": available,
            "recommended": recommended,
            "existing_reports": [
                {
                    "id": r.id,
                    "type": r.report_type.value,
                    "version": r.version,
                    "status": r.status.value,
                    "is_current": r.is_current,
                }
                for r in existing
            ],
            "versions_remaining": {
                rt.value: self.MAX_VERSIONS_PER_TYPE - len([
                    r for r in existing if r.report_type == rt
                ])
                for rt in ReportType
            },
        }

    async def link_to_closure(
        self,
        case_id: str,
        user_id: str,
        report_ids: List[str],
    ) -> Tuple[int, Optional[str]]:
        """
        Link reports to case closure.

        Marks specified reports as linked to closure for archival.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification
            report_ids: List of report IDs to link

        Returns:
            Tuple of (count linked, error_message)
        """
        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return 0, "Case not found"

        if not case.status.is_terminal:
            return 0, "Can only link reports to closed/resolved cases"

        linked_count = 0
        for report_id in report_ids:
            report = await self.get_report(report_id, user_id)
            if report and report.case_id == case_id:
                report.linked_to_closure = True
                linked_count += 1

        await self.db.commit()
        return linked_count, None

    async def delete_report(
        self,
        report_id: str,
        user_id: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Delete a report.

        Args:
            report_id: Report ID
            user_id: User ID for ownership verification

        Returns:
            Tuple of (success, error_message)
        """
        report = await self.get_report(report_id, user_id)
        if not report:
            return False, "Report not found"

        if report.linked_to_closure:
            return False, "Cannot delete report linked to case closure"

        await self.db.delete(report)
        await self.db.commit()

        return True, None
