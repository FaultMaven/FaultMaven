"""
Investigation state models for milestone-based tracking.

Ported from legacy: models/investigation.py
Adapted to work with SQLAlchemy ORM via JSON storage in case.case_metadata.

These Pydantic models provide rich investigation tracking without requiring
database schema changes - the entire state is serialized to JSON.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from faultmaven.modules.case.enums import (
    InvestigationPhase,
    HypothesisStatus,
    ConfidenceLevel,
    DegradedModeType,
    EvidenceCategory,
    InvestigationMomentum,
    InvestigationStrategy,
    TemporalState,
    UrgencyLevel,
)


class AnomalyFrame(BaseModel):
    """
    Problem statement with scope assessment.

    Captures the "what" and "where" of the problem during initial framing.
    """
    statement: str = Field(..., description="Clear problem statement")
    affected_components: List[str] = Field(
        default_factory=list,
        description="List of affected system components"
    )
    affected_scope: str = Field(
        default="",
        description="Description of blast radius"
    )
    started_at: Optional[datetime] = Field(
        None,
        description="When the problem started"
    )
    severity: str = Field(
        default="unknown",
        description="Impact severity assessment"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in this framing"
    )
    framed_at_turn: int = Field(
        default=0,
        description="Turn number when this was framed"
    )
    revision_count: int = Field(
        default=0,
        description="Number of times this was revised"
    )


class TemporalFrame(BaseModel):
    """
    Timeline information for the investigation.

    Captures the "when" of the problem and correlates with recent changes.
    """
    first_noticed_at: Optional[datetime] = Field(
        None,
        description="When the user first noticed the problem"
    )
    actually_started_at: Optional[datetime] = Field(
        None,
        description="Actual problem start time (may differ from noticed)"
    )
    temporal_pattern: str = Field(
        default="",
        description="Pattern description (constant, intermittent, etc.)"
    )
    recent_changes: List[str] = Field(
        default_factory=list,
        description="Recent changes that may correlate"
    )
    change_correlation: Optional[str] = Field(
        None,
        description="Identified correlation with a change"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in timeline accuracy"
    )
    completeness: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How complete is our timeline understanding"
    )
    established_at_turn: int = Field(
        default=0,
        description="Turn when timeline was established"
    )


class HypothesisModel(BaseModel):
    """
    Root cause hypothesis with validation tracking.

    Tracks hypothesis lifecycle from capture through validation/refutation.
    Enhanced with confidence trajectory and stagnation tracking.
    """
    hypothesis_id: str = Field(..., description="Unique identifier")
    statement: str = Field(..., description="Hypothesis statement")
    category: str = Field(
        default="",
        description="Category (e.g., 'infrastructure', 'code', 'config')"
    )
    status: HypothesisStatus = Field(
        default=HypothesisStatus.CAPTURED,
        description="Current lifecycle status"
    )
    likelihood: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Current likelihood of being root cause"
    )
    initial_likelihood: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Initial likelihood when hypothesis was created"
    )
    confidence_trajectory: List[tuple[int, float]] = Field(
        default_factory=list,
        description="History of confidence changes: [(turn, confidence), ...]"
    )
    confidence_level: ConfidenceLevel = Field(
        default=ConfidenceLevel.SPECULATION,
        description="Confidence in this hypothesis"
    )
    supporting_evidence: List[str] = Field(
        default_factory=list,
        description="Evidence IDs supporting this hypothesis"
    )
    refuting_evidence: List[str] = Field(
        default_factory=list,
        description="Evidence IDs refuting this hypothesis"
    )
    test_plan: Optional[str] = Field(
        None,
        description="Plan to test this hypothesis"
    )
    test_results: List[str] = Field(
        default_factory=list,
        description="Results of hypothesis tests"
    )

    # Lifecycle tracking
    captured_at_turn: int = Field(
        default=0,
        description="Turn when hypothesis was captured"
    )
    validated_at_turn: Optional[int] = Field(
        None,
        description="Turn when hypothesis was validated/refuted"
    )
    last_progress_at_turn: int = Field(
        default=0,
        description="Last turn when this hypothesis made progress"
    )
    promoted_to_active_at_turn: Optional[int] = Field(
        None,
        description="Turn when promoted from CAPTURED to ACTIVE"
    )

    # Stagnation tracking
    iterations_without_progress: int = Field(
        default=0,
        description="Number of iterations without confidence improvement"
    )

    # Generation metadata
    generation_mode: str = Field(
        default="systematic",
        description="How hypothesis was generated: 'opportunistic' or 'systematic'"
    )
    triggering_observation: Optional[str] = Field(
        None,
        description="What triggered this hypothesis (for opportunistic generation)"
    )


class EvidenceItem(BaseModel):
    """
    Evidence collected during investigation.

    Categorized by which phase/milestone it helps advance.
    Enhanced with form and source type classification.
    """
    evidence_id: str = Field(..., description="Unique identifier")
    description: str = Field(..., description="What this evidence shows")
    category: EvidenceCategory = Field(
        default=EvidenceCategory.OTHER,
        description="Evidence classification (logs, metrics, config, etc.)"
    )
    form: str = Field(
        default="direct_observation",
        description="Evidence form: 'direct_observation', 'symptom', 'metric', 'log_entry', 'config_value', 'test_result'"
    )
    source_type: str = Field(
        default="user_provided",
        description="Source type: 'user_provided', 'system_query', 'log_analysis', 'metric_query', 'code_inspection'"
    )
    source: str = Field(
        default="",
        description="Where this evidence came from (specific source name)"
    )
    content_summary: str = Field(
        default="",
        description="Summary of evidence content"
    )
    collected_at_turn: int = Field(
        default=0,
        description="Turn when evidence was collected"
    )
    supports_hypotheses: List[str] = Field(
        default_factory=list,
        description="Hypothesis IDs this evidence supports"
    )
    refutes_hypotheses: List[str] = Field(
        default_factory=list,
        description="Hypothesis IDs this evidence refutes"
    )


class ProgressMetrics(BaseModel):
    """
    Investigation progress tracking.

    Tracks milestone completion and provides progress indicators.
    """
    # Milestone tracking
    completed_milestones: List[str] = Field(
        default_factory=list,
        description="List of completed milestone IDs"
    )
    pending_milestones: List[str] = Field(
        default_factory=lambda: [
            "symptom_verified",
            "scope_assessed",
            "timeline_established",
            "changes_identified",
            "root_cause_identified",
            "solution_proposed",
            "solution_applied",
            "solution_verified",
        ],
        description="List of pending milestone IDs"
    )

    # Progress indicators
    evidence_completeness: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How complete is our evidence"
    )
    evidence_blocked_count: int = Field(
        default=0,
        description="Number of blocked evidence requests"
    )
    active_hypotheses_count: int = Field(
        default=0,
        description="Number of active hypotheses"
    )

    # Momentum tracking
    momentum: InvestigationMomentum = Field(
        default=InvestigationMomentum.MODERATE,
        description="Current investigation momentum"
    )
    turns_without_progress: int = Field(
        default=0,
        description="Consecutive turns without milestone progress"
    )

    # Next steps
    next_steps: List[str] = Field(
        default_factory=list,
        description="Recommended next actions"
    )
    blocked_reasons: List[str] = Field(
        default_factory=list,
        description="Reasons for any blockages"
    )

    @property
    def completion_percentage(self) -> float:
        """Calculate overall completion percentage."""
        total = len(self.completed_milestones) + len(self.pending_milestones)
        if total == 0:
            return 0.0
        return len(self.completed_milestones) / total * 100

    @property
    def is_stalled(self) -> bool:
        """Check if investigation is stalled (3+ turns without progress)."""
        return self.turns_without_progress >= 3


class EscalationState(BaseModel):
    """
    Escalation tracking for degraded investigations.

    Implements FR-CNV circular dialogue detection via stall detection.
    """
    escalation_suggested: bool = Field(
        default=False,
        description="Whether escalation has been suggested"
    )
    escalation_reason: Optional[str] = Field(
        None,
        description="Reason for escalation suggestion"
    )
    degraded_mode: bool = Field(
        default=False,
        description="Whether operating in degraded mode"
    )
    degraded_mode_type: Optional[DegradedModeType] = Field(
        None,
        description="Type of degradation"
    )
    user_acknowledged: bool = Field(
        default=False,
        description="Whether user acknowledged degraded state"
    )
    suggested_at_turn: Optional[int] = Field(
        None,
        description="Turn when escalation was suggested"
    )


class WorkingConclusion(BaseModel):
    """
    Current working conclusion about root cause.

    Represents the best current understanding, even if not fully verified.
    """
    statement: str = Field(..., description="Conclusion statement")
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in this conclusion"
    )
    confidence_level: ConfidenceLevel = Field(
        default=ConfidenceLevel.SPECULATION,
        description="Categorical confidence level"
    )
    supporting_evidence_count: int = Field(
        default=0,
        description="Number of supporting evidence items"
    )
    caveats: List[str] = Field(
        default_factory=list,
        description="Caveats or limitations"
    )
    alternative_explanations: List[str] = Field(
        default_factory=list,
        description="Alternative explanations not ruled out"
    )
    can_proceed_with_solution: bool = Field(
        default=False,
        description="Whether confidence is sufficient for solution"
    )
    next_evidence_needed: List[str] = Field(
        default_factory=list,
        description="Evidence needed to increase confidence"
    )


class TurnRecord(BaseModel):
    """
    Record of a single investigation turn.

    Provides audit trail of investigation progress.
    """
    turn_number: int = Field(..., description="Turn sequence number")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this turn occurred"
    )
    phase: InvestigationPhase = Field(..., description="Phase during this turn")
    user_input_summary: str = Field(
        default="",
        description="Summary of user input"
    )
    agent_action_summary: str = Field(
        default="",
        description="Summary of agent action"
    )
    milestones_completed: List[str] = Field(
        default_factory=list,
        description="Milestones completed this turn"
    )
    evidence_collected: List[str] = Field(
        default_factory=list,
        description="Evidence IDs collected this turn"
    )
    hypotheses_updated: List[str] = Field(
        default_factory=list,
        description="Hypothesis IDs updated this turn"
    )
    outcome: str = Field(
        default="conversation",
        description="Turn outcome: 'progress', 'conversation', 'blocked', 'evidence_collected', etc."
    )


class OODAIteration(BaseModel):
    """
    Record of a single OODA iteration within a phase.
    """
    iteration_id: str = Field(..., description="Unique iteration ID")
    turn_number: int = Field(..., description="Turn when this iteration occurred")
    phase: InvestigationPhase = Field(..., description="Phase during iteration")
    current_step: str = Field(
        ...,
        description="Current OODA step: 'observe', 'orient', 'decide', 'act'"
    )
    steps_completed: List[str] = Field(
        default_factory=list,
        description="OODA steps completed in this iteration"
    )
    made_progress: bool = Field(
        default=False,
        description="Whether this iteration made progress"
    )
    outcome: str = Field(
        default="conversation",
        description="Iteration outcome"
    )


class OODAState(BaseModel):
    """
    Current OODA execution state.
    """
    current_step: str = Field(
        default="observe",
        description="Current OODA step: 'observe', 'orient', 'decide', 'act'"
    )
    current_iteration: int = Field(
        default=0,
        description="Current iteration count within phase"
    )
    iteration_history: List[OODAIteration] = Field(
        default_factory=list,
        description="History of all OODA iterations"
    )
    adaptive_intensity: str = Field(
        default="light",
        description="Current intensity: 'light', 'medium', 'full'"
    )


class MemorySnapshot(BaseModel):
    """
    Snapshot of conversation/evidence at a point in time.
    """
    turn_number: int = Field(..., description="Turn this snapshot was taken")
    summary: str = Field(default="", description="Summary of this snapshot")
    key_facts: List[str] = Field(
        default_factory=list,
        description="Key facts from this snapshot"
    )
    evidence_collected: List[str] = Field(
        default_factory=list,
        description="Evidence IDs from this snapshot"
    )


class HierarchicalMemory(BaseModel):
    """
    Hierarchical memory management (hot/warm/cold tiers).
    """
    hot_memory: List[MemorySnapshot] = Field(
        default_factory=list,
        description="Recent 2-3 iterations (highest priority)"
    )
    warm_memory: List[MemorySnapshot] = Field(
        default_factory=list,
        description="Relevant context (medium priority)"
    )
    cold_memory: List[MemorySnapshot] = Field(
        default_factory=list,
        description="Archived key facts (lowest priority)"
    )


class InvestigationState(BaseModel):
    """
    Complete investigation state stored in case.case_metadata["investigation"].

    This is the root model containing all investigation tracking data.
    Stored as JSON in the Case ORM model, enabling rich investigation
    tracking without schema migrations.

    Enhanced with OODA execution state and hierarchical memory management.
    """
    # Metadata
    investigation_id: str = Field(..., description="Unique investigation ID")
    current_phase: InvestigationPhase = Field(
        default=InvestigationPhase.INTAKE,
        description="Current investigation phase"
    )
    current_turn: int = Field(
        default=0,
        description="Current turn number"
    )
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When investigation started"
    )

    # Strategy
    temporal_state: TemporalState = Field(
        default=TemporalState.ONGOING,
        description="Whether problem is ongoing or historical"
    )
    urgency_level: UrgencyLevel = Field(
        default=UrgencyLevel.UNKNOWN,
        description="Urgency classification"
    )
    strategy: InvestigationStrategy = Field(
        default=InvestigationStrategy.ROOT_CAUSE,
        description="Investigation path strategy"
    )

    # Problem framing
    anomaly_frame: Optional[AnomalyFrame] = Field(
        None,
        description="Problem statement and scope"
    )
    temporal_frame: Optional[TemporalFrame] = Field(
        None,
        description="Timeline information"
    )

    # Hypotheses
    hypotheses: List[HypothesisModel] = Field(
        default_factory=list,
        description="All hypotheses"
    )

    # Evidence
    evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="All collected evidence"
    )

    # Progress
    progress: ProgressMetrics = Field(
        default_factory=ProgressMetrics,
        description="Progress tracking"
    )

    # Escalation
    escalation: EscalationState = Field(
        default_factory=EscalationState,
        description="Escalation state"
    )

    # Conclusions
    working_conclusion: Optional[WorkingConclusion] = Field(
        None,
        description="Current working conclusion"
    )

    # OODA execution layer (NEW)
    ooda_state: Optional[OODAState] = Field(
        None,
        description="Current OODA execution state and iteration tracking"
    )

    # Memory management layer (NEW)
    memory: HierarchicalMemory = Field(
        default_factory=HierarchicalMemory,
        description="Hierarchical memory (hot/warm/cold tiers)"
    )

    # Audit trail
    turn_history: List[TurnRecord] = Field(
        default_factory=list,
        description="History of all turns"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage in case_metadata."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvestigationState":
        """Deserialize from case_metadata."""
        return cls.model_validate(data)

    def get_active_hypotheses(self) -> List[HypothesisModel]:
        """Get all hypotheses with ACTIVE status."""
        return [h for h in self.hypotheses if h.status == HypothesisStatus.ACTIVE]

    def get_validated_hypothesis(self) -> Optional[HypothesisModel]:
        """Get the validated root cause hypothesis if any."""
        for h in self.hypotheses:
            if h.status == HypothesisStatus.VALIDATED:
                return h
        return None

    def check_degraded_mode(self) -> Optional[DegradedModeType]:
        """
        Check if investigation should enter degraded mode.

        Implements FR-CNV circular dialogue detection.
        """
        # No progress for 3+ turns
        if self.progress.turns_without_progress >= 3:
            return DegradedModeType.NO_PROGRESS

        # All hypotheses exhausted
        active = self.get_active_hypotheses()
        captured = [h for h in self.hypotheses if h.status == HypothesisStatus.CAPTURED]
        if not active and not captured and len(self.hypotheses) > 0:
            return DegradedModeType.HYPOTHESIS_SPACE_EXHAUSTED

        # Critical evidence blocked
        if self.progress.evidence_blocked_count >= 3:
            return DegradedModeType.CRITICAL_EVIDENCE_MISSING

        return None
