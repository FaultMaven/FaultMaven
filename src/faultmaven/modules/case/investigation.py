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
        description="Current estimated likelihood of being root cause"
    )
    initial_likelihood: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Initial likelihood when hypothesis was created"
    )
    confidence_level: ConfidenceLevel = Field(
        default=ConfidenceLevel.SPECULATION,
        description="Confidence in this hypothesis"
    )
    confidence_trajectory: List[tuple] = Field(
        default_factory=list,
        description="History of (turn, confidence) values"
    )
    iterations_without_progress: int = Field(
        default=0,
        description="Count of iterations without confidence change"
    )
    supporting_evidence: List[str] = Field(
        default_factory=list,
        description="Evidence supporting this hypothesis"
    )
    refuting_evidence: List[str] = Field(
        default_factory=list,
        description="Evidence refuting this hypothesis"
    )
    test_plan: Optional[str] = Field(
        None,
        description="Plan to test this hypothesis"
    )
    test_results: List[str] = Field(
        default_factory=list,
        description="Results of hypothesis tests"
    )
    captured_at_turn: int = Field(
        default=0,
        description="Turn when hypothesis was captured"
    )
    validated_at_turn: Optional[int] = Field(
        None,
        description="Turn when hypothesis was validated/refuted"
    )


class EvidenceItem(BaseModel):
    """
    Evidence collected during investigation.

    Categorized by which phase/milestone it helps advance.
    """
    evidence_id: str = Field(..., description="Unique identifier")
    description: str = Field(..., description="What this evidence shows")
    category: EvidenceCategory = Field(
        default=EvidenceCategory.OTHER,
        description="Evidence classification"
    )
    source: str = Field(
        default="",
        description="Where this evidence came from"
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
    # Individual milestone flags
    symptom_verified: bool = Field(default=False)
    scope_assessed: bool = Field(default=False)
    timeline_established: bool = Field(default=False)
    changes_identified: bool = Field(default=False)
    root_cause_identified: bool = Field(default=False)
    root_cause_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    root_cause_method: str = Field(default="", description="Method used to identify root cause")
    solution_proposed: bool = Field(default=False)
    verification_complete: bool = Field(default=False, description="Whether verification is complete")
    solution_applied: bool = Field(default=False)
    solution_verified: bool = Field(default=False)
    current_stage: str = Field(default="intake")

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


class ConsultingData(BaseModel):
    """
    Tracking data for knowledge base consultation and problem statement status.
    """
    proposed_problem_statement: Optional[str] = Field(
        None,
        description="The proposed problem statement from consulting phase"
    )
    problem_statement_confirmed: bool = Field(
        default=False,
        description="Whether the problem statement has been confirmed"
    )
    problem_statement_confirmed_at: Optional[datetime] = Field(
        None,
        description="When problem statement was confirmed"
    )
    decided_to_investigate: bool = Field(
        default=False,
        description="Whether user decided to proceed with investigation"
    )
    decision_made_at: Optional[datetime] = Field(
        None,
        description="When investigation decision was made"
    )
    consulted_kbs: List[str] = Field(
        default_factory=list,
        description="List of knowledge base IDs that have been consulted"
    )
    consultation_count: int = Field(
        default=0,
        description="Total number of KB consultations"
    )


class InvestigationProgress(BaseModel):
    """
    Summary of investigation progress for milestone tracking.
    """
    completed_milestones: List[str] = Field(
        default_factory=list,
        description="IDs of completed milestones"
    )
    pending_milestones: List[str] = Field(
        default_factory=list,
        description="IDs of pending milestones"
    )
    current_phase: str = Field(
        default="intake",
        description="Current investigation phase"
    )
    hypothesis_count: int = Field(
        default=0,
        description="Number of active hypotheses"
    )
    evidence_count: int = Field(
        default=0,
        description="Number of evidence items collected"
    )
    momentum_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Investigation momentum (0=stalled, 1=rapid progress)"
    )


class DegradedModeData(BaseModel):
    """
    Data for degraded mode operation tracking.
    """
    mode_type: Optional[DegradedModeType] = Field(
        None,
        description="Type of degradation"
    )
    entered_at: Optional[datetime] = Field(
        None,
        description="When degraded mode was entered"
    )
    reason: str = Field(
        default="",
        description="Detailed reason for degraded mode"
    )
    recovery_attempts: int = Field(
        default=0,
        description="Number of recovery attempts"
    )
    user_notified: bool = Field(
        default=False,
        description="Whether user has been notified"
    )


class OODAIteration(BaseModel):
    """
    Single OODA loop iteration record.
    """
    iteration_id: str = Field(..., description="Unique iteration identifier")
    turn_number: int = Field(..., description="Turn when iteration started")
    phase: InvestigationPhase = Field(..., description="Investigation phase")
    current_step: str = Field(
        default="observe",
        description="Current OODA step (observe/orient/decide/act)"
    )
    steps_completed: List[str] = Field(
        default_factory=list,
        description="OODA steps completed this iteration"
    )
    made_progress: bool = Field(
        default=False,
        description="Whether this iteration made progress"
    )
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this iteration started"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="When this iteration completed"
    )
    outcome: str = Field(
        default="",
        description="Outcome of this iteration"
    )
    hypotheses_updated: List[str] = Field(
        default_factory=list,
        description="Hypothesis IDs updated this iteration"
    )


class OODAState(BaseModel):
    """
    OODA loop state tracking.
    """
    current_iteration: int = Field(
        default=0,
        description="Current OODA iteration number"
    )
    iterations: List[OODAIteration] = Field(
        default_factory=list,
        description="History of OODA iterations"
    )
    intensity_level: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Current investigation intensity (0=low, 1=high)"
    )


class MemorySnapshot(BaseModel):
    """
    Snapshot of investigation memory at a point in time.
    """
    snapshot_id: str = Field(..., description="Unique snapshot identifier")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When snapshot was created"
    )
    summary: str = Field(
        default="",
        description="Summary of this memory period"
    )
    key_findings: List[str] = Field(
        default_factory=list,
        description="Key findings from this period"
    )


class HierarchicalMemory(BaseModel):
    """
    Hierarchical memory management for investigation context.
    """
    hot_turn_count: int = Field(
        default=3,
        description="Number of recent turns in hot memory"
    )
    warm_snapshots: List[MemorySnapshot] = Field(
        default_factory=list,
        description="Snapshots in warm memory"
    )
    cold_summary: str = Field(
        default="",
        description="Summary of cold (oldest) memory"
    )
    total_turns_processed: int = Field(
        default=0,
        description="Total number of turns processed"
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


class InvestigationState(BaseModel):
    """
    Complete investigation state stored in case.case_metadata["investigation"].

    This is the root model containing all investigation tracking data.
    Stored as JSON in the Case ORM model, enabling rich investigation
    tracking without schema migrations.
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

    # OODA state
    ooda_state: Optional[OODAState] = Field(
        None,
        description="OODA loop state tracking"
    )

    # Consulting data
    consulting_data: Optional[ConsultingData] = Field(
        None,
        description="Consulting phase tracking"
    )

    # Hierarchical memory
    hierarchical_memory: Optional[HierarchicalMemory] = Field(
        None,
        description="Memory management"
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
