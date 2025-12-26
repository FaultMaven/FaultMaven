"""
Investigation state models for milestone-based tracking.

Ported from legacy: models/investigation.py
Adapted to work with SQLAlchemy ORM via JSON storage in case.case_metadata.

These Pydantic models provide rich investigation tracking without requiring
database schema changes - the entire state is serialized to JSON.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
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

    # Additional fields for WorkingConclusionGenerator
    evidence_provided_count: int = Field(
        default=0,
        description="Number of evidence items provided"
    )
    evidence_pending_count: int = Field(
        default=0,
        description="Number of evidence requests pending"
    )
    investigation_momentum: InvestigationMomentum = Field(
        default=InvestigationMomentum.EARLY,
        description="Investigation momentum status"
    )
    next_critical_steps: List[str] = Field(
        default_factory=list,
        description="Next critical steps to take"
    )
    is_degraded_mode: bool = Field(
        default=False,
        description="Whether investigation is in degraded mode"
    )
    generated_at_turn: int = Field(
        default=0,
        description="Turn when these metrics were generated"
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
    last_updated_turn: int = Field(
        default=0,
        description="Turn when this conclusion was last updated"
    )
    last_confidence_change_turn: int = Field(
        default=0,
        description="Turn when confidence last changed"
    )
    generated_at_turn: int = Field(
        default=0,
        description="Turn when this conclusion was generated"
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
    progress_made: bool = Field(
        default=False,
        description="Whether meaningful progress was made this turn"
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

    Used by MemoryManager for hierarchical memory (hot/warm/cold tiers).
    """
    snapshot_id: str = Field(..., description="Unique snapshot identifier")
    turn_range: Tuple[int, int] = Field(..., description="(start_turn, end_turn) covered by snapshot")
    tier: str = Field(..., description="Memory tier: 'hot', 'warm', or 'cold'")
    content_summary: str = Field(default="", description="Summary of content")
    key_insights: List[str] = Field(
        default_factory=list,
        description="Key insights from this snapshot"
    )
    evidence_ids: List[str] = Field(
        default_factory=list,
        description="Evidence IDs referenced"
    )
    hypothesis_updates: List[str] = Field(
        default_factory=list,
        description="Hypothesis IDs updated"
    )
    confidence_delta: float = Field(
        default=0.0,
        description="Net confidence change in this snapshot"
    )
    token_count_estimate: int = Field(
        default=0,
        description="Estimated token count"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When snapshot was created"
    )

    # Legacy fields for backward compatibility
    turn_number: Optional[int] = Field(default=None, description="Turn number (legacy)")
    summary: Optional[str] = Field(default=None, description="Summary (legacy)")
    key_facts: Optional[List[str]] = Field(default=None, description="Key facts (legacy)")
    evidence_collected: Optional[List[str]] = Field(default=None, description="Evidence collected (legacy)")


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


class ConsultingData(BaseModel):
    """
    Pre-investigation CONSULTING status data.

    Captures early problem exploration before formal investigation commitment.
    Source: FaultMaven-Mono case.py lines 715-795
    """
    proposed_problem_statement: Optional[str] = Field(
        None,
        description="Agent's formalized problem statement",
        max_length=1000
    )
    problem_statement_confirmed: bool = Field(
        default=False,
        description="User confirmed the formalized problem statement"
    )
    problem_statement_confirmed_at: Optional[datetime] = None

    quick_suggestions: List[str] = Field(
        default_factory=list,
        description="Quick fixes or guidance provided during consulting"
    )
    decided_to_investigate: bool = Field(
        default=False,
        description="Whether user committed to formal investigation"
    )
    decision_made_at: Optional[datetime] = None
    consultation_turns: int = Field(default=0, ge=0)


class InvestigationProgress(BaseModel):
    """
    Milestone-based progress tracking.

    Track what's completed, not what phase we're in.
    Agent completes milestones opportunistically based on data availability.
    Source: FaultMaven-Mono case.py lines 230-445
    """
    # Verification Milestones
    symptom_verified: bool = False
    scope_assessed: bool = False
    timeline_established: bool = False
    changes_identified: bool = False

    # Investigation Milestones
    root_cause_identified: bool = False
    root_cause_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    root_cause_method: Optional[str] = None

    # Resolution Milestones
    solution_proposed: bool = False
    solution_applied: bool = False
    solution_verified: bool = False

    # Path-Specific
    mitigation_applied: bool = False

    # Timestamps
    verification_completed_at: Optional[datetime] = None
    investigation_completed_at: Optional[datetime] = None
    resolution_completed_at: Optional[datetime] = None

    @property
    def verification_complete(self) -> bool:
        """Check if all verification milestones completed"""
        return (
            self.symptom_verified and
            self.scope_assessed and
            self.timeline_established and
            self.changes_identified
        )

    @property
    def current_stage(self) -> str:
        """Compute investigation stage from completed milestones"""
        if self.solution_proposed or self.solution_applied or self.solution_verified:
            return "solution"
        if self.root_cause_identified:
            return "hypothesis_validation"
        if self.symptom_verified:
            return "hypothesis_formulation"
        return "symptom_verification"

    @property
    def completed_milestones(self) -> List[str]:
        """Get list of completed milestone names"""
        milestones = []
        if self.symptom_verified:
            milestones.append("symptom_verified")
        if self.scope_assessed:
            milestones.append("scope_assessed")
        if self.timeline_established:
            milestones.append("timeline_established")
        if self.changes_identified:
            milestones.append("changes_identified")
        if self.root_cause_identified:
            milestones.append("root_cause_identified")
        if self.solution_proposed:
            milestones.append("solution_proposed")
        if self.solution_applied:
            milestones.append("solution_applied")
        if self.solution_verified:
            milestones.append("solution_verified")
        return milestones


class DegradedModeData(BaseModel):
    """
    Investigation degraded mode tracking.

    Entered when investigation is blocked or struggling.
    Source: FaultMaven-Mono case.py lines 2434-2492
    """
    mode_type: DegradedModeType
    entered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = Field(..., max_length=1000)
    attempted_actions: List[str] = Field(default_factory=list)

    fallback_offered: Optional[str] = Field(None, max_length=1000)
    user_choice: Optional[str] = Field(None, max_length=100)

    exited_at: Optional[datetime] = None
    exit_reason: Optional[str] = None


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

    # Progress (milestone-based)
    progress: InvestigationProgress = Field(
        default_factory=InvestigationProgress,
        description="Milestone-based progress tracking"
    )

    # Legacy progress metrics (for compatibility)
    progress_metrics: ProgressMetrics = Field(
        default_factory=ProgressMetrics,
        description="Legacy progress tracking (deprecated, use progress instead)"
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

    # Consulting data (Phase 0 - CONSULTING status)
    consulting_data: Optional[ConsultingData] = Field(
        None,
        description="Pre-investigation consulting data"
    )

    # Degraded mode tracking
    degraded_mode: Optional[DegradedModeData] = Field(
        None,
        description="Degraded mode state when investigation is struggling"
    )

    # Progress tracking
    turns_without_progress: int = Field(
        default=0,
        description="Consecutive turns without meaningful progress"
    )

    # Audit trail
    turn_history: List[TurnRecord] = Field(
        default_factory=list,
        description="History of all turns"
    )

    # Compatibility aliases for MilestoneEngine
    @property
    def evidence_items(self) -> List[EvidenceItem]:
        """Alias for evidence (used by MilestoneEngine)"""
        return self.evidence

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
        if self.progress_metrics.turns_without_progress >= 3:
            return DegradedModeType.NO_PROGRESS

        # All hypotheses exhausted
        active = self.get_active_hypotheses()
        captured = [h for h in self.hypotheses if h.status == HypothesisStatus.CAPTURED]
        if not active and not captured and len(self.hypotheses) > 0:
            return DegradedModeType.HYPOTHESIS_SPACE_EXHAUSTED

        # Critical evidence blocked
        if self.progress_metrics.evidence_blocked_count >= 3:
            return DegradedModeType.CRITICAL_EVIDENCE_MISSING

        return None
