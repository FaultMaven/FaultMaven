# Business Logic Migration Plan

**From:** Legacy Implementation (`FaultMaven-Mono/faultmaven/`)
**To:** Modular Monolith (`faultmaven/src/faultmaven/`)
**Date:** December 24, 2025

## Executive Summary

This plan migrates business logic from the legacy implementation to the new modular monolith while preserving clean architecture principles. Each phase includes test validation to detect regressions.

---

## Migration Principles

1. **Preserve Module Boundaries** - New code goes into appropriate modules
2. **Adapt to SQLAlchemy ORM** - Convert Pydantic models to SQLAlchemy where persistence is needed
3. **Use Dependency Injection** - Wire services through `dependencies.py`
4. **Run Tests After Each Step** - Validate no regressions before proceeding
5. **Incremental Commits** - One logical change per commit for easy rollback

---

## Architecture Mapping

### Old → New Structure

```
OLD (faultmaven/)                    NEW (src/faultmaven/modules/)
──────────────────────────────────────────────────────────────────
models/case.py                   →   case/orm.py (extend existing)
models/investigation.py          →   case/investigation.py (NEW)
models/report.py                 →   report/ (NEW MODULE)
models/responses.py              →   agent/responses.py (NEW)
models/behavioral.py             →   agent/analytics.py (NEW)

services/domain/
├── case_status_manager.py       →   case/status_manager.py (NEW)
├── investigation_service.py     →   case/investigation_service.py (NEW)
├── report_generation_service.py →   report/service.py (NEW)
├── report_recommendation_service.py → report/recommendation.py (NEW)
└── planning_service.py          →   case/planning.py (NEW)

services/analytics/
├── confidence_service.py        →   agent/confidence.py (NEW)
└── dashboard_service.py         →   analytics/ (NEW MODULE - optional)
```

---

## Phase 1: Core Enums & Domain Models

**Goal:** Port foundational enums and domain models that other components depend on.

### Step 1.1: Extend Case Status Enum

**File:** `src/faultmaven/modules/case/orm.py`

Align `CaseStatus` with legacy (4 states with terminal logic):

```python
class CaseStatus(str, Enum):
    """Case investigation status aligned with SRS."""
    CONSULTING = "consulting"      # Pre-investigation
    INVESTIGATING = "investigating" # Active investigation
    RESOLVED = "resolved"          # Terminal - problem fixed
    CLOSED = "closed"              # Terminal - abandoned/escalated

    @property
    def is_terminal(self) -> bool:
        return self in (CaseStatus.RESOLVED, CaseStatus.CLOSED)
```

**Test:** `pytest tests/integration/modules/test_case_service.py -v`

### Step 1.2: Add Investigation Phase Enum

**File:** `src/faultmaven/modules/case/enums.py` (NEW)

```python
from enum import Enum

class InvestigationPhase(int, Enum):
    """Investigation phases from OODA-based methodology."""
    INTAKE = 0
    BLAST_RADIUS = 1
    TIMELINE = 2
    HYPOTHESIS = 3
    VALIDATION = 4
    SOLUTION = 5
    DOCUMENT = 6

class HypothesisStatus(str, Enum):
    """Hypothesis lifecycle states."""
    CAPTURED = "captured"
    ACTIVE = "active"
    VALIDATED = "validated"
    REFUTED = "refuted"
    RETIRED = "retired"
    SUPERSEDED = "superseded"

class ConfidenceLevel(str, Enum):
    """Investigation confidence levels."""
    SPECULATION = "speculation"
    PROBABLE = "probable"
    CONFIDENT = "confident"
    VERIFIED = "verified"

class DegradedModeType(str, Enum):
    """Types of investigation degradation."""
    CRITICAL_EVIDENCE_MISSING = "critical_evidence_missing"
    EXPERTISE_REQUIRED = "expertise_required"
    SYSTEMIC_ISSUE = "systemic_issue"
    HYPOTHESIS_SPACE_EXHAUSTED = "hypothesis_space_exhausted"
    GENERAL_LIMITATION = "general_limitation"

class EvidenceCategory(str, Enum):
    """Evidence classification by investigation phase."""
    SYMPTOM_EVIDENCE = "symptom_evidence"
    CAUSAL_EVIDENCE = "causal_evidence"
    RESOLUTION_EVIDENCE = "resolution_evidence"
    OTHER = "other"
```

**Test:** Unit tests for enum properties

### Step 1.3: Add Response Types

**File:** `src/faultmaven/modules/agent/response_types.py` (NEW)

```python
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel

class ResponseType(str, Enum):
    """Agent response types per SRS FR-RT."""
    ANSWER = "answer"
    PLAN_PROPOSAL = "plan_proposal"
    CLARIFICATION_REQUEST = "clarification_request"
    CONFIRMATION_REQUEST = "confirmation_request"
    SOLUTION_READY = "solution_ready"
    NEEDS_MORE_DATA = "needs_more_data"
    ESCALATION_REQUIRED = "escalation_required"
    VISUAL_DIAGRAM = "visual_diagram"
    COMPARISON_TABLE = "comparison_table"

class SuggestedAction(BaseModel):
    """UI action suggestion."""
    action_type: str
    label: str
    description: Optional[str] = None
    data: Optional[dict] = None

class CommandSuggestion(BaseModel):
    """Diagnostic command suggestion."""
    command: str
    description: str
    safety_level: str  # "safe", "read_only", "caution"

class AgentResponse(BaseModel):
    """Structured agent response with type classification."""
    response_type: ResponseType
    content: str
    suggested_actions: List[SuggestedAction] = []
    commands: List[CommandSuggestion] = []
    confidence: Optional[float] = None
    metadata: dict = {}
```

**Test:** `pytest tests/unit/modules/agent/test_response_types.py -v`

---

## Phase 2: Case Status Manager

**Goal:** Implement state machine with validated transitions.

### Step 2.1: Create Status Manager

**File:** `src/faultmaven/modules/case/status_manager.py` (NEW)

```python
"""
Case status manager with state machine validation.

Ported from legacy: services/domain/case_status_manager.py
"""

from datetime import datetime
from typing import Optional, Tuple, Dict, List
from faultmaven.modules.case.orm import CaseStatus

# Valid state transitions
ALLOWED_TRANSITIONS: Dict[CaseStatus, List[CaseStatus]] = {
    CaseStatus.CONSULTING: [CaseStatus.INVESTIGATING, CaseStatus.CLOSED],
    CaseStatus.INVESTIGATING: [CaseStatus.RESOLVED, CaseStatus.CLOSED],
    CaseStatus.RESOLVED: [],  # Terminal
    CaseStatus.CLOSED: [],    # Terminal
}

# Messages sent to agent on status change
STATUS_CHANGE_MESSAGES: Dict[Tuple[CaseStatus, CaseStatus], str] = {
    (CaseStatus.CONSULTING, CaseStatus.INVESTIGATING):
        "The user has confirmed the problem. Begin formal investigation.",
    (CaseStatus.INVESTIGATING, CaseStatus.RESOLVED):
        "The solution has been verified. Document the resolution.",
    (CaseStatus.INVESTIGATING, CaseStatus.CLOSED):
        "The investigation has been closed without resolution.",
}


class CaseStatusManager:
    """Static utility class for case status transitions."""

    @staticmethod
    def is_terminal(status: CaseStatus) -> bool:
        """Check if status is terminal (no further transitions allowed)."""
        return status in (CaseStatus.RESOLVED, CaseStatus.CLOSED)

    @staticmethod
    def validate_transition(
        current: CaseStatus,
        target: CaseStatus
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a status transition.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if CaseStatusManager.is_terminal(current):
            return False, f"Cannot transition from terminal state: {current.value}"

        allowed = ALLOWED_TRANSITIONS.get(current, [])
        if target not in allowed:
            return False, f"Invalid transition: {current.value} → {target.value}"

        return True, None

    @staticmethod
    def get_allowed_transitions(current: CaseStatus) -> List[CaseStatus]:
        """Get list of valid target states from current state."""
        return ALLOWED_TRANSITIONS.get(current, [])

    @staticmethod
    def get_agent_message(
        old_status: CaseStatus,
        new_status: CaseStatus
    ) -> Optional[str]:
        """Get message to send to agent for this transition."""
        return STATUS_CHANGE_MESSAGES.get((old_status, new_status))

    @staticmethod
    def get_terminal_fields(
        new_status: CaseStatus,
        user_id: str
    ) -> Dict:
        """Get fields to update when entering terminal state."""
        now = datetime.utcnow()

        if new_status == CaseStatus.RESOLVED:
            return {"resolved_at": now, "resolved_by": user_id}
        elif new_status == CaseStatus.CLOSED:
            return {"closed_at": now, "closed_by": user_id}

        return {}

    @staticmethod
    def build_audit_record(
        old_status: CaseStatus,
        new_status: CaseStatus,
        user_id: str,
        auto: bool = False,
        reason: Optional[str] = None
    ) -> Dict:
        """Build audit trail entry for status change."""
        return {
            "from_status": old_status.value,
            "to_status": new_status.value,
            "changed_at": datetime.utcnow().isoformat(),
            "changed_by": user_id,
            "auto": auto,
            "reason": reason,
        }
```

### Step 2.2: Integrate into CaseService

**File:** `src/faultmaven/modules/case/service.py` (MODIFY)

Add status transition validation:

```python
from faultmaven.modules.case.status_manager import CaseStatusManager

async def update_case_status(
    self,
    case_id: str,
    user_id: str,
    new_status: CaseStatus,
    reason: Optional[str] = None,
) -> Tuple[Optional[Case], Optional[str]]:
    """
    Update case status with state machine validation.

    Returns:
        Tuple of (updated_case, error_message)
    """
    case = await self.get_case(case_id, user_id)
    if not case:
        return None, "Case not found or unauthorized"

    # Validate transition
    valid, error = CaseStatusManager.validate_transition(case.status, new_status)
    if not valid:
        return None, error

    old_status = case.status
    case.status = new_status
    case.updated_at = datetime.utcnow()

    # Apply terminal state fields
    terminal_fields = CaseStatusManager.get_terminal_fields(new_status, user_id)
    for field, value in terminal_fields.items():
        setattr(case, field, value)

    # Build audit record
    audit = CaseStatusManager.build_audit_record(
        old_status, new_status, user_id, reason=reason
    )

    # Store audit in case_metadata
    if "status_history" not in case.case_metadata:
        case.case_metadata["status_history"] = []
    case.case_metadata["status_history"].append(audit)

    await self.db.commit()
    await self.db.refresh(case)

    return case, None
```

**Test:** `pytest tests/integration/modules/test_case_service.py -v`

---

## Phase 3: Investigation State Models

**Goal:** Add investigation tracking without breaking existing case structure.

### Step 3.1: Create Investigation State Model

**File:** `src/faultmaven/modules/case/investigation.py` (NEW)

```python
"""
Investigation state models for milestone-based tracking.

Ported from legacy: models/investigation.py
Adapted to work with SQLAlchemy ORM.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from faultmaven.modules.case.enums import (
    InvestigationPhase,
    HypothesisStatus,
    ConfidenceLevel,
    DegradedModeType,
)


class AnomalyFrame(BaseModel):
    """Problem statement with scope assessment."""
    statement: str
    affected_components: List[str] = []
    affected_scope: str = ""
    started_at: Optional[datetime] = None
    severity: str = "unknown"
    confidence: float = 0.0
    framed_at_turn: int = 0


class TemporalFrame(BaseModel):
    """Timeline information for the investigation."""
    first_noticed_at: Optional[datetime] = None
    actually_started_at: Optional[datetime] = None
    temporal_pattern: str = ""
    recent_changes: List[str] = []
    change_correlation: Optional[str] = None
    confidence: float = 0.0
    established_at_turn: int = 0


class HypothesisModel(BaseModel):
    """Root cause hypothesis with validation tracking."""
    hypothesis_id: str
    statement: str
    category: str = ""
    status: HypothesisStatus = HypothesisStatus.CAPTURED
    likelihood: float = 0.5
    confidence_level: ConfidenceLevel = ConfidenceLevel.SPECULATION
    supporting_evidence: List[str] = []
    refuting_evidence: List[str] = []
    test_plan: Optional[str] = None
    captured_at_turn: int = 0


class ProgressMetrics(BaseModel):
    """Investigation progress tracking."""
    evidence_completeness: float = 0.0
    evidence_blocked_count: int = 0
    active_hypotheses_count: int = 0
    completed_milestones: List[str] = []
    pending_milestones: List[str] = []
    next_steps: List[str] = []
    blocked_reasons: List[str] = []

    @property
    def completion_percentage(self) -> float:
        total = len(self.completed_milestones) + len(self.pending_milestones)
        if total == 0:
            return 0.0
        return len(self.completed_milestones) / total * 100


class EscalationState(BaseModel):
    """Escalation tracking for degraded investigations."""
    escalation_suggested: bool = False
    escalation_reason: Optional[str] = None
    degraded_mode: bool = False
    degraded_mode_type: Optional[DegradedModeType] = None
    user_acknowledged: bool = False


class InvestigationState(BaseModel):
    """
    Complete investigation state stored in case.case_metadata.

    This is a Pydantic model stored as JSON in the Case ORM model,
    enabling rich investigation tracking without schema migrations.
    """
    # Metadata
    current_phase: InvestigationPhase = InvestigationPhase.INTAKE
    current_turn: int = 0
    started_at: datetime = Field(default_factory=datetime.utcnow)

    # Problem framing
    anomaly_frame: Optional[AnomalyFrame] = None
    temporal_frame: Optional[TemporalFrame] = None

    # Hypotheses
    hypotheses: List[HypothesisModel] = []

    # Progress
    progress: ProgressMetrics = Field(default_factory=ProgressMetrics)

    # Escalation
    escalation: EscalationState = Field(default_factory=EscalationState)

    # Working conclusion
    working_conclusion: Optional[str] = None
    conclusion_confidence: ConfidenceLevel = ConfidenceLevel.SPECULATION

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage in case_metadata."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvestigationState":
        """Deserialize from case_metadata."""
        return cls.model_validate(data)
```

### Step 3.2: Add Investigation Service

**File:** `src/faultmaven/modules/case/investigation_service.py` (NEW)

```python
"""
Investigation service for milestone-based progress tracking.

Ported from legacy: services/domain/investigation_service.py
"""

from typing import Optional, Tuple
from datetime import datetime

from faultmaven.modules.case.orm import Case, CaseStatus
from faultmaven.modules.case.service import CaseService
from faultmaven.modules.case.status_manager import CaseStatusManager
from faultmaven.modules.case.investigation import (
    InvestigationState,
    HypothesisModel,
    ProgressMetrics,
)
from faultmaven.modules.case.enums import (
    InvestigationPhase,
    HypothesisStatus,
    DegradedModeType,
)


class InvestigationService:
    """
    Service for managing investigation state within cases.

    The investigation state is stored in case.case_metadata["investigation"]
    as a JSON blob, allowing rich tracking without schema changes.
    """

    INVESTIGATION_KEY = "investigation"

    def __init__(self, case_service: CaseService):
        self.case_service = case_service

    async def get_investigation_state(
        self,
        case_id: str,
        user_id: str
    ) -> Optional[InvestigationState]:
        """Get investigation state for a case."""
        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return None

        data = case.case_metadata.get(self.INVESTIGATION_KEY)
        if not data:
            return None

        return InvestigationState.from_dict(data)

    async def initialize_investigation(
        self,
        case_id: str,
        user_id: str,
    ) -> Tuple[Optional[InvestigationState], Optional[str]]:
        """
        Initialize investigation state when transitioning to INVESTIGATING.
        """
        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return None, "Case not found"

        if case.status != CaseStatus.CONSULTING:
            return None, "Can only start investigation from CONSULTING status"

        # Initialize investigation state
        state = InvestigationState(
            current_phase=InvestigationPhase.INTAKE,
            current_turn=0,
            started_at=datetime.utcnow(),
            progress=ProgressMetrics(
                pending_milestones=[
                    "symptom_verified",
                    "scope_assessed",
                    "timeline_established",
                    "changes_identified",
                    "root_cause_identified",
                    "solution_proposed",
                    "solution_applied",
                    "solution_verified",
                ]
            ),
        )

        # Store in case metadata
        case.case_metadata[self.INVESTIGATION_KEY] = state.to_dict()

        # Transition status
        case.status = CaseStatus.INVESTIGATING
        case.updated_at = datetime.utcnow()

        await self.case_service.db.commit()
        await self.case_service.db.refresh(case)

        return state, None

    async def advance_turn(
        self,
        case_id: str,
        user_id: str,
        milestones_completed: list[str] = None,
        phase_transition: Optional[InvestigationPhase] = None,
    ) -> Tuple[Optional[InvestigationState], Optional[str]]:
        """
        Advance investigation by one turn, optionally completing milestones.
        """
        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return None, "Case not found"

        data = case.case_metadata.get(self.INVESTIGATION_KEY)
        if not data:
            return None, "Investigation not initialized"

        state = InvestigationState.from_dict(data)
        state.current_turn += 1

        # Complete milestones
        if milestones_completed:
            for milestone in milestones_completed:
                if milestone in state.progress.pending_milestones:
                    state.progress.pending_milestones.remove(milestone)
                    state.progress.completed_milestones.append(milestone)

        # Phase transition
        if phase_transition:
            state.current_phase = phase_transition

        # Check for degraded mode (3+ turns without progress)
        # This implements FR-CNV circular dialogue detection
        if state.current_turn > 3 and not state.progress.completed_milestones:
            state.escalation.degraded_mode = True
            state.escalation.degraded_mode_type = DegradedModeType.GENERAL_LIMITATION

        # Update case
        case.case_metadata[self.INVESTIGATION_KEY] = state.to_dict()
        case.updated_at = datetime.utcnow()

        await self.case_service.db.commit()
        await self.case_service.db.refresh(case)

        return state, None

    async def add_hypothesis(
        self,
        case_id: str,
        user_id: str,
        statement: str,
        category: str = "",
        likelihood: float = 0.5,
    ) -> Tuple[Optional[HypothesisModel], Optional[str]]:
        """Add a hypothesis to the investigation."""
        import uuid

        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return None, "Case not found"

        data = case.case_metadata.get(self.INVESTIGATION_KEY)
        if not data:
            return None, "Investigation not initialized"

        state = InvestigationState.from_dict(data)

        hypothesis = HypothesisModel(
            hypothesis_id=str(uuid.uuid4()),
            statement=statement,
            category=category,
            likelihood=likelihood,
            captured_at_turn=state.current_turn,
        )

        state.hypotheses.append(hypothesis)
        state.progress.active_hypotheses_count = len([
            h for h in state.hypotheses
            if h.status == HypothesisStatus.ACTIVE
        ])

        case.case_metadata[self.INVESTIGATION_KEY] = state.to_dict()
        await self.case_service.db.commit()

        return hypothesis, None

    async def get_progress(
        self,
        case_id: str,
        user_id: str,
    ) -> Optional[dict]:
        """Get investigation progress summary."""
        state = await self.get_investigation_state(case_id, user_id)
        if not state:
            return None

        return {
            "current_phase": state.current_phase.name,
            "current_turn": state.current_turn,
            "completion_percentage": state.progress.completion_percentage,
            "completed_milestones": state.progress.completed_milestones,
            "pending_milestones": state.progress.pending_milestones,
            "active_hypotheses": state.progress.active_hypotheses_count,
            "degraded_mode": state.escalation.degraded_mode,
            "degraded_reason": (
                state.escalation.degraded_mode_type.value
                if state.escalation.degraded_mode_type else None
            ),
        }
```

**Test:** `pytest tests/integration/modules/test_investigation_service.py -v`

---

## Phase 4: Report Module

**Goal:** Create new report module with full generation capability.

### Step 4.1: Create Report Module Structure

```bash
mkdir -p src/faultmaven/modules/report
touch src/faultmaven/modules/report/__init__.py
```

### Step 4.2: Report ORM Models

**File:** `src/faultmaven/modules/report/orm.py` (NEW)

```python
"""
Report module ORM models.

Ported from legacy: models/report.py
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from sqlalchemy import String, DateTime, JSON, Text, ForeignKey, Integer, Boolean, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from faultmaven.database import Base


class ReportType(str, Enum):
    """Types of reports that can be generated."""
    INCIDENT_REPORT = "incident_report"
    RUNBOOK = "runbook"
    POST_MORTEM = "post_mortem"


class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class CaseReport(Base):
    """Generated case report/documentation."""

    __tablename__ = "case_reports"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Foreign key to Case
    case_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    # Report metadata
    report_type: Mapped[ReportType] = mapped_column(
        SQLEnum(ReportType),
        nullable=False
    )
    title: Mapped[str] = mapped_column(String(200))

    # Content
    content: Mapped[str] = mapped_column(Text)  # Markdown format
    format: Mapped[str] = mapped_column(String(20), default="markdown")

    # Generation tracking
    status: Mapped[ReportStatus] = mapped_column(
        SQLEnum(ReportStatus),
        default=ReportStatus.PENDING
    )
    generation_time_ms: Mapped[int] = mapped_column(Integer, default=0)

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)

    # Closure linking
    linked_to_closure: Mapped[bool] = mapped_column(Boolean, default=False)

    # Additional metadata
    report_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    def __repr__(self) -> str:
        return f"<CaseReport(id={self.id}, type={self.report_type}, case={self.case_id})>"
```

### Step 4.3: Report Service

**File:** `src/faultmaven/modules/report/service.py` (NEW)

```python
"""
Report generation service.

Ported from legacy: services/domain/report_generation_service.py
"""

from datetime import datetime
from typing import Optional, List, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from faultmaven.modules.report.orm import CaseReport, ReportType, ReportStatus
from faultmaven.modules.case.service import CaseService
from faultmaven.modules.case.orm import Case, CaseStatus


class ReportService:
    """Service for generating and managing case reports."""

    MAX_VERSIONS_PER_TYPE = 5

    def __init__(
        self,
        db_session: AsyncSession,
        case_service: CaseService,
        llm_provider=None,  # Optional for generation
    ):
        self.db = db_session
        self.case_service = case_service
        self.llm = llm_provider

    async def get_report(
        self,
        report_id: str,
        user_id: str
    ) -> Optional[CaseReport]:
        """Get a report by ID with ownership verification."""
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
        """List reports for a case."""
        # Verify ownership
        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return []

        query = select(CaseReport).where(CaseReport.case_id == case_id)

        if report_type:
            query = query.where(CaseReport.report_type == report_type)

        if not include_history:
            query = query.where(CaseReport.is_current == True)

        query = query.order_by(CaseReport.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def generate_report(
        self,
        case_id: str,
        user_id: str,
        report_type: ReportType,
    ) -> Tuple[Optional[CaseReport], Optional[str]]:
        """
        Generate a report for a case.

        Returns:
            Tuple of (report, error_message)
        """
        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return None, "Case not found or unauthorized"

        # Check regeneration limit
        existing = await self.list_reports(
            case_id, user_id, report_type, include_history=True
        )
        if len(existing) >= self.MAX_VERSIONS_PER_TYPE:
            return None, f"Maximum {self.MAX_VERSIONS_PER_TYPE} versions allowed"

        start_time = datetime.utcnow()

        # Mark previous versions as not current
        for old_report in existing:
            if old_report.is_current:
                old_report.is_current = False

        # Generate content
        content = await self._generate_content(case, report_type)

        end_time = datetime.utcnow()
        generation_time = int((end_time - start_time).total_seconds() * 1000)

        # Create report
        report = CaseReport(
            id=str(uuid.uuid4()),
            case_id=case_id,
            report_type=report_type,
            title=self._generate_title(case, report_type),
            content=content,
            status=ReportStatus.COMPLETED,
            generation_time_ms=generation_time,
            version=len(existing) + 1,
            is_current=True,
            generated_at=end_time,
        )

        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        return report, None

    async def _generate_content(
        self,
        case: Case,
        report_type: ReportType
    ) -> str:
        """Generate report content using LLM or templates."""
        if self.llm:
            # Use LLM for generation
            return await self._llm_generate(case, report_type)
        else:
            # Use template fallback
            return self._template_generate(case, report_type)

    def _template_generate(self, case: Case, report_type: ReportType) -> str:
        """Generate report using templates (no LLM)."""
        if report_type == ReportType.INCIDENT_REPORT:
            return f"""# Incident Report: {case.title}

## Summary
{case.description}

## Timeline
- Created: {case.created_at}
- Status: {case.status.value}

## Resolution
{"Resolved at: " + str(case.resolved_at) if case.resolved_at else "Pending"}
"""
        elif report_type == ReportType.RUNBOOK:
            return f"""# Runbook: {case.title}

## Problem Description
{case.description}

## Diagnostic Steps
1. Verify symptoms
2. Check affected components
3. Review recent changes

## Resolution Steps
(To be completed based on investigation)
"""
        else:  # POST_MORTEM
            return f"""# Post-Mortem: {case.title}

## Incident Summary
{case.description}

## Root Cause
(Identified through investigation)

## Lessons Learned
(To be documented)

## Action Items
- [ ] Preventive measures
- [ ] Monitoring improvements
"""

    async def _llm_generate(self, case: Case, report_type: ReportType) -> str:
        """Generate report content using LLM."""
        # Implementation would call self.llm.complete() with appropriate prompts
        # For now, fall back to template
        return self._template_generate(case, report_type)

    def _generate_title(self, case: Case, report_type: ReportType) -> str:
        """Generate report title."""
        prefix = {
            ReportType.INCIDENT_REPORT: "Incident Report",
            ReportType.RUNBOOK: "Runbook",
            ReportType.POST_MORTEM: "Post-Mortem",
        }
        return f"{prefix[report_type]}: {case.title[:100]}"

    async def get_recommendations(
        self,
        case_id: str,
        user_id: str,
    ) -> dict:
        """Get report generation recommendations for a case."""
        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return {"error": "Case not found"}

        existing = await self.list_reports(case_id, user_id)
        existing_types = {r.report_type for r in existing}

        available = []
        for rt in ReportType:
            if rt not in existing_types:
                available.append(rt.value)

        return {
            "case_id": case_id,
            "case_status": case.status.value,
            "available_for_generation": available,
            "existing_reports": [
                {"type": r.report_type.value, "version": r.version}
                for r in existing
            ],
        }
```

### Step 4.4: Report Router

**File:** `src/faultmaven/modules/report/router.py` (NEW)

```python
"""Report module API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from faultmaven.modules.auth.dependencies import get_current_user
from faultmaven.modules.auth.orm import User
from faultmaven.modules.report.orm import ReportType
from faultmaven.modules.report.service import ReportService
from faultmaven.dependencies import get_report_service

router = APIRouter(prefix="/reports", tags=["reports"])


class GenerateReportRequest(BaseModel):
    report_type: ReportType


@router.get("/{case_id}")
async def list_case_reports(
    case_id: str,
    report_type: Optional[str] = None,
    include_history: bool = False,
    current_user: User = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service),
):
    """List reports for a case."""
    rt = ReportType(report_type) if report_type else None
    reports = await report_service.list_reports(
        case_id, current_user.id, rt, include_history
    )
    return {
        "case_id": case_id,
        "reports": [
            {
                "id": r.id,
                "type": r.report_type.value,
                "title": r.title,
                "version": r.version,
                "status": r.status.value,
                "created_at": r.created_at.isoformat(),
            }
            for r in reports
        ],
    }


@router.post("/{case_id}/generate")
async def generate_report(
    case_id: str,
    request: GenerateReportRequest,
    current_user: User = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service),
):
    """Generate a new report for a case."""
    report, error = await report_service.generate_report(
        case_id, current_user.id, request.report_type
    )

    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return {
        "id": report.id,
        "type": report.report_type.value,
        "title": report.title,
        "status": report.status.value,
        "generation_time_ms": report.generation_time_ms,
    }


@router.get("/{case_id}/recommendations")
async def get_recommendations(
    case_id: str,
    current_user: User = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service),
):
    """Get report generation recommendations."""
    return await report_service.get_recommendations(case_id, current_user.id)


@router.get("/{case_id}/{report_id}")
async def get_report(
    case_id: str,
    report_id: str,
    current_user: User = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service),
):
    """Get a specific report with content."""
    report = await report_service.get_report(report_id, current_user.id)

    if not report or report.case_id != case_id:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "id": report.id,
        "case_id": report.case_id,
        "type": report.report_type.value,
        "title": report.title,
        "content": report.content,
        "format": report.format,
        "version": report.version,
        "status": report.status.value,
        "created_at": report.created_at.isoformat(),
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
    }
```

**Test:** `pytest tests/integration/modules/test_report_service.py -v`

---

## Phase 5: Wire Dependencies & Database Migration

### Step 5.1: Update Dependencies

**File:** `src/faultmaven/dependencies.py` (MODIFY)

Add new service dependencies:

```python
from faultmaven.modules.case.investigation_service import InvestigationService
from faultmaven.modules.report.service import ReportService

def get_investigation_service(
    case_service: CaseService = Depends(get_case_service),
) -> InvestigationService:
    """Get investigation service."""
    return InvestigationService(case_service=case_service)

def get_report_service(
    db_session: AsyncSession = Depends(get_db_session),
    case_service: CaseService = Depends(get_case_service),
    llm_provider: CoreLLMProvider = Depends(get_llm_provider),
) -> ReportService:
    """Get report service."""
    return ReportService(
        db_session=db_session,
        case_service=case_service,
        llm_provider=llm_provider,
    )
```

### Step 5.2: Update App Router Registration

**File:** `src/faultmaven/app.py` (MODIFY)

```python
from faultmaven.modules.report.router import router as report_router

# Add after other router includes
app.include_router(report_router)
```

### Step 5.3: Create Database Migration

**File:** `alembic/versions/20241224_add_reports.py` (NEW)

```python
"""Add case_reports table.

Revision ID: 20241224_add_reports
Revises: 20241221_0000_initial_schema
Create Date: 2024-12-24
"""

from alembic import op
import sqlalchemy as sa

revision = '20241224_add_reports'
down_revision = '20241221_0000_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'case_reports',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('case_id', sa.String(36), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('report_type', sa.Enum('incident_report', 'runbook', 'post_mortem', name='reporttype'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('format', sa.String(20), default='markdown'),
        sa.Column('status', sa.Enum('pending', 'generating', 'completed', 'failed', name='reportstatus'), default='pending'),
        sa.Column('generation_time_ms', sa.Integer, default=0),
        sa.Column('version', sa.Integer, default=1),
        sa.Column('is_current', sa.Boolean, default=True),
        sa.Column('linked_to_closure', sa.Boolean, default=False),
        sa.Column('report_metadata', sa.JSON, default=dict),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('generated_at', sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table('case_reports')
```

### Step 5.4: Update Central ORM Registration

**File:** `src/faultmaven/models.py` (MODIFY)

```python
# Add report models
from faultmaven.modules.report.orm import CaseReport
```

---

## Test Validation Strategy

After each phase, run:

```bash
# Unit tests for new code
pytest tests/unit/modules/<module>/ -v

# Integration tests for module interactions
pytest tests/integration/modules/ -v

# Full regression test
pytest tests/ -v --tb=short

# Type checking
mypy src/faultmaven/

# Import linting (module boundaries)
lint-imports
```

---

## Migration Checklist

### Phase 1: Core Enums & Models
- [ ] Update CaseStatus enum with terminal property
- [ ] Create `case/enums.py` with investigation enums
- [ ] Create `agent/response_types.py`
- [ ] Run tests: `pytest tests/integration/modules/test_case_service.py`

### Phase 2: Case Status Manager
- [ ] Create `case/status_manager.py`
- [ ] Integrate into CaseService
- [ ] Run tests: `pytest tests/integration/modules/test_case_service.py`

### Phase 3: Investigation State
- [ ] Create `case/investigation.py` models
- [ ] Create `case/investigation_service.py`
- [ ] Create tests for investigation service
- [ ] Run tests: `pytest tests/integration/modules/`

### Phase 4: Report Module
- [ ] Create `report/` module directory
- [ ] Create `report/orm.py`
- [ ] Create `report/service.py`
- [ ] Create `report/router.py`
- [ ] Run tests: `pytest tests/integration/modules/test_report_service.py`

### Phase 5: Integration
- [ ] Update `dependencies.py`
- [ ] Update `app.py` router registration
- [ ] Create database migration
- [ ] Update `models.py` registration
- [ ] Run full test suite: `pytest tests/`
- [ ] Run type checking: `mypy src/faultmaven/`
- [ ] Run import linting: `lint-imports`

---

## Estimated Effort

| Phase | Complexity | Estimated Time |
|-------|------------|----------------|
| Phase 1 | Low | 1-2 hours |
| Phase 2 | Medium | 2-3 hours |
| Phase 3 | High | 3-4 hours |
| Phase 4 | High | 4-5 hours |
| Phase 5 | Medium | 2-3 hours |
| **Total** | | **12-17 hours** |

---

## Success Criteria

1. All existing tests pass
2. New tests for migrated components pass
3. Import linting passes (module boundaries maintained)
4. Type checking passes
5. Case status transitions are validated
6. Investigation progress is tracked
7. Reports can be generated and retrieved
