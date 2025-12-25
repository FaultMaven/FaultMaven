"""
Investigation service for milestone-based progress tracking.

Ported from legacy: services/domain/investigation_service.py

This service manages the investigation state within cases, providing:
- Investigation initialization when transitioning to INVESTIGATING
- Turn advancement with milestone tracking
- Hypothesis management
- Progress reporting
- Degraded mode detection (FR-CNV circular dialogue)
"""

import uuid
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

from sqlalchemy.orm.attributes import flag_modified

from faultmaven.modules.case.orm import Case, CaseStatus
from faultmaven.modules.case.service import CaseService
from faultmaven.modules.case.status_manager import CaseStatusManager
from faultmaven.modules.case.investigation import (
    InvestigationState,
    HypothesisModel,
    EvidenceItem,
    AnomalyFrame,
    TemporalFrame,
    WorkingConclusion,
    TurnRecord,
    InvestigationProgress,
    ProgressMetrics,
)
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


class InvestigationService:
    """
    Service for managing investigation state within cases.

    The investigation state is stored in case.case_metadata["investigation"]
    as a JSON blob, allowing rich tracking without schema changes.

    Key responsibilities:
    - Initialize investigation when case transitions to INVESTIGATING
    - Track turn-by-turn progress
    - Manage hypotheses through their lifecycle
    - Detect degraded mode (stalled investigations)
    - Provide progress summaries
    """

    INVESTIGATION_KEY = "investigation"

    def __init__(self, case_service: CaseService):
        """
        Initialize investigation service.

        Args:
            case_service: CaseService for case access
        """
        self.case_service = case_service

    async def get_investigation_state(
        self,
        case_id: str,
        user_id: str
    ) -> Optional[InvestigationState]:
        """
        Get investigation state for a case.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification

        Returns:
            InvestigationState if exists, None otherwise
        """
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
        problem_statement: Optional[str] = None,
        temporal_state: TemporalState = TemporalState.ONGOING,
        urgency_level: UrgencyLevel = UrgencyLevel.UNKNOWN,
    ) -> Tuple[Optional[InvestigationState], Optional[str]]:
        """
        Initialize investigation state when transitioning to INVESTIGATING.

        This should be called when a case transitions from CONSULTING to
        INVESTIGATING. It sets up the investigation tracking structure.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification
            problem_statement: Optional initial problem statement
            temporal_state: Whether problem is ongoing or historical
            urgency_level: Initial urgency assessment

        Returns:
            Tuple of (InvestigationState, error_message)
        """
        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return None, "Case not found"

        # Check if investigation already exists
        if case.case_metadata.get(self.INVESTIGATION_KEY):
            return None, "Investigation already initialized"

        # Determine strategy based on temporal state and urgency
        strategy = self._determine_strategy(temporal_state, urgency_level)

        # Initialize investigation state
        state = InvestigationState(
            investigation_id=str(uuid.uuid4()),
            current_phase=InvestigationPhase.INTAKE,
            current_turn=0,
            started_at=datetime.utcnow(),
            temporal_state=temporal_state,
            urgency_level=urgency_level,
            strategy=strategy,
            progress=InvestigationProgress(),
        )

        # Set initial problem statement if provided
        if problem_statement:
            state.anomaly_frame = AnomalyFrame(
                statement=problem_statement,
                framed_at_turn=0,
            )

        # Store in case metadata
        if case.case_metadata is None:
            case.case_metadata = {}
        case.case_metadata[self.INVESTIGATION_KEY] = state.to_dict()
        flag_modified(case, "case_metadata")
        flag_modified(case, "case_metadata")  # Mark JSON field as modified
        case.updated_at = datetime.utcnow()

        await self.case_service.db.commit()
        await self.case_service.db.refresh(case)

        return state, None

    def _determine_strategy(
        self,
        temporal_state: TemporalState,
        urgency_level: UrgencyLevel
    ) -> InvestigationStrategy:
        """
        Determine investigation strategy based on temporal state and urgency.

        Strategy matrix:
        - ONGOING + CRITICAL/HIGH → MITIGATION_FIRST
        - HISTORICAL + LOW/MEDIUM → ROOT_CAUSE
        - Ambiguous cases → USER_CHOICE
        """
        if temporal_state == TemporalState.ONGOING:
            if urgency_level in (UrgencyLevel.CRITICAL, UrgencyLevel.HIGH):
                return InvestigationStrategy.MITIGATION_FIRST
            elif urgency_level in (UrgencyLevel.LOW, UrgencyLevel.MEDIUM):
                return InvestigationStrategy.USER_CHOICE
        else:  # HISTORICAL
            if urgency_level in (UrgencyLevel.LOW, UrgencyLevel.MEDIUM):
                return InvestigationStrategy.ROOT_CAUSE
            elif urgency_level in (UrgencyLevel.CRITICAL, UrgencyLevel.HIGH):
                return InvestigationStrategy.USER_CHOICE

        return InvestigationStrategy.ROOT_CAUSE

    async def advance_turn(
        self,
        case_id: str,
        user_id: str,
        user_input_summary: str = "",
        agent_action_summary: str = "",
        milestones_completed: Optional[List[str]] = None,
        phase_transition: Optional[InvestigationPhase] = None,
    ) -> Tuple[Optional[InvestigationState], Optional[str]]:
        """
        Advance investigation by one turn.

        Called after each user-agent interaction to track progress.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification
            user_input_summary: Summary of user's input this turn
            agent_action_summary: Summary of agent's action this turn
            milestones_completed: List of milestone IDs completed this turn
            phase_transition: Optional new phase to transition to

        Returns:
            Tuple of (updated InvestigationState, error_message)
        """
        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return None, "Case not found"

        data = case.case_metadata.get(self.INVESTIGATION_KEY)
        if not data:
            return None, "Investigation not initialized"

        state = InvestigationState.from_dict(data)
        state.current_turn += 1

        # Track if we made progress this turn
        made_progress = False

        # Complete milestones
        if milestones_completed:
            for milestone in milestones_completed:
                if milestone in state.progress.pending_milestones:
                    state.progress.pending_milestones.remove(milestone)
                    state.progress.completed_milestones.append(milestone)
                    made_progress = True

        # Phase transition
        if phase_transition and phase_transition != state.current_phase:
            state.current_phase = phase_transition
            made_progress = True

        # Update progress momentum
        if made_progress:
            state.progress_metrics.turns_without_progress = 0
            state.progress_metrics.momentum = InvestigationMomentum.MODERATE
        else:
            state.progress_metrics.turns_without_progress += 1
            if state.progress_metrics.turns_without_progress >= 3:
                state.progress_metrics.momentum = InvestigationMomentum.BLOCKED
            elif state.progress_metrics.turns_without_progress >= 2:
                state.progress_metrics.momentum = InvestigationMomentum.LOW

        # Check for degraded mode
        degraded_type = state.check_degraded_mode()
        if degraded_type and not state.escalation.degraded_mode:
            state.escalation.degraded_mode = True
            state.escalation.degraded_mode_type = degraded_type
            state.escalation.escalation_suggested = True
            state.escalation.escalation_reason = self._get_degraded_reason(degraded_type)
            state.escalation.suggested_at_turn = state.current_turn

        # Record turn in history
        turn_record = TurnRecord(
            turn_number=state.current_turn,
            timestamp=datetime.utcnow(),
            phase=state.current_phase,
            user_input_summary=user_input_summary,
            agent_action_summary=agent_action_summary,
            milestones_completed=milestones_completed or [],
        )
        state.turn_history.append(turn_record)

        # Update active hypothesis count
        state.progress_metrics.active_hypotheses_count = len(state.get_active_hypotheses())

        # Update case
        case.case_metadata[self.INVESTIGATION_KEY] = state.to_dict()
        flag_modified(case, "case_metadata")
        case.updated_at = datetime.utcnow()

        await self.case_service.db.commit()
        await self.case_service.db.refresh(case)

        return state, None

    def _get_degraded_reason(self, degraded_type: DegradedModeType) -> str:
        """Get human-readable reason for degraded mode."""
        reasons = {
            DegradedModeType.NO_PROGRESS: (
                "The investigation has not made progress in the last 3 turns. "
                "Consider providing additional information or escalating."
            ),
            DegradedModeType.HYPOTHESIS_SPACE_EXHAUSTED: (
                "All investigated hypotheses have been ruled out. "
                "The root cause may require domain expertise."
            ),
            DegradedModeType.CRITICAL_EVIDENCE_MISSING: (
                "Critical evidence cannot be obtained. "
                "The investigation is blocked without this data."
            ),
            DegradedModeType.EXPERTISE_REQUIRED: (
                "This issue requires specialized expertise. "
                "Consider involving a domain expert."
            ),
            DegradedModeType.SYSTEMIC_ISSUE: (
                "This appears to be a systemic issue. "
                "Resolution may require architectural changes."
            ),
            DegradedModeType.GENERAL_LIMITATION: (
                "The investigation has reached a limitation. "
                "Human intervention may be needed."
            ),
        }
        return reasons.get(degraded_type, "Investigation is in degraded mode.")

    async def add_hypothesis(
        self,
        case_id: str,
        user_id: str,
        statement: str,
        category: str = "",
        likelihood: float = 0.5,
    ) -> Tuple[Optional[HypothesisModel], Optional[str]]:
        """
        Add a hypothesis to the investigation.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification
            statement: Hypothesis statement
            category: Category (e.g., 'infrastructure', 'code')
            likelihood: Initial likelihood (0-1)

        Returns:
            Tuple of (HypothesisModel, error_message)
        """
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
            status=HypothesisStatus.CAPTURED,
            likelihood=likelihood,
            captured_at_turn=state.current_turn,
        )

        state.hypotheses.append(hypothesis)

        # Update case
        case.case_metadata[self.INVESTIGATION_KEY] = state.to_dict()
        flag_modified(case, "case_metadata")
        await self.case_service.db.commit()

        return hypothesis, None

    async def update_hypothesis_status(
        self,
        case_id: str,
        user_id: str,
        hypothesis_id: str,
        new_status: HypothesisStatus,
        evidence: Optional[str] = None,
    ) -> Tuple[Optional[HypothesisModel], Optional[str]]:
        """
        Update the status of a hypothesis.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification
            hypothesis_id: Hypothesis to update
            new_status: New status
            evidence: Optional evidence to add

        Returns:
            Tuple of (updated HypothesisModel, error_message)
        """
        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return None, "Case not found"

        data = case.case_metadata.get(self.INVESTIGATION_KEY)
        if not data:
            return None, "Investigation not initialized"

        state = InvestigationState.from_dict(data)

        # Find hypothesis
        hypothesis = None
        for h in state.hypotheses:
            if h.hypothesis_id == hypothesis_id:
                hypothesis = h
                break

        if not hypothesis:
            return None, "Hypothesis not found"

        # Update status
        hypothesis.status = new_status
        if new_status in (HypothesisStatus.VALIDATED, HypothesisStatus.REFUTED):
            hypothesis.validated_at_turn = state.current_turn

        # Add evidence
        if evidence:
            if new_status == HypothesisStatus.VALIDATED:
                hypothesis.supporting_evidence.append(evidence)
            elif new_status == HypothesisStatus.REFUTED:
                hypothesis.refuting_evidence.append(evidence)

        # Update progress
        state.progress_metrics.active_hypotheses_count = len(state.get_active_hypotheses())

        # Update case
        case.case_metadata[self.INVESTIGATION_KEY] = state.to_dict()
        flag_modified(case, "case_metadata")
        await self.case_service.db.commit()

        return hypothesis, None

    async def add_evidence(
        self,
        case_id: str,
        user_id: str,
        description: str,
        category: EvidenceCategory = EvidenceCategory.OTHER,
        source: str = "",
        content_summary: str = "",
    ) -> Tuple[Optional[EvidenceItem], Optional[str]]:
        """
        Add evidence to the investigation.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification
            description: What this evidence shows
            category: Evidence classification
            source: Where evidence came from
            content_summary: Summary of content

        Returns:
            Tuple of (EvidenceItem, error_message)
        """
        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return None, "Case not found"

        data = case.case_metadata.get(self.INVESTIGATION_KEY)
        if not data:
            return None, "Investigation not initialized"

        state = InvestigationState.from_dict(data)

        evidence = EvidenceItem(
            evidence_id=str(uuid.uuid4()),
            description=description,
            category=category,
            source=source,
            content_summary=content_summary,
            collected_at_turn=state.current_turn,
        )

        state.evidence.append(evidence)

        # Update case
        case.case_metadata[self.INVESTIGATION_KEY] = state.to_dict()
        flag_modified(case, "case_metadata")
        await self.case_service.db.commit()

        return evidence, None

    async def set_working_conclusion(
        self,
        case_id: str,
        user_id: str,
        statement: str,
        confidence: float = 0.5,
        confidence_level: ConfidenceLevel = ConfidenceLevel.PROBABLE,
        caveats: Optional[List[str]] = None,
    ) -> Tuple[Optional[WorkingConclusion], Optional[str]]:
        """
        Set or update the working conclusion.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification
            statement: Conclusion statement
            confidence: Numeric confidence (0-1)
            confidence_level: Categorical confidence
            caveats: List of caveats

        Returns:
            Tuple of (WorkingConclusion, error_message)
        """
        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return None, "Case not found"

        data = case.case_metadata.get(self.INVESTIGATION_KEY)
        if not data:
            return None, "Investigation not initialized"

        state = InvestigationState.from_dict(data)

        conclusion = WorkingConclusion(
            statement=statement,
            confidence=confidence,
            confidence_level=confidence_level,
            supporting_evidence_count=len(state.evidence),
            caveats=caveats or [],
            can_proceed_with_solution=confidence_level in (
                ConfidenceLevel.CONFIDENT,
                ConfidenceLevel.VERIFIED
            ),
        )

        state.working_conclusion = conclusion

        # Update case
        case.case_metadata[self.INVESTIGATION_KEY] = state.to_dict()
        flag_modified(case, "case_metadata")
        await self.case_service.db.commit()

        return conclusion, None

    async def get_progress(
        self,
        case_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get investigation progress summary.

        Returns a simplified view suitable for API responses.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification

        Returns:
            Progress summary dict or None
        """
        state = await self.get_investigation_state(case_id, user_id)
        if not state:
            return None

        return {
            "investigation_id": state.investigation_id,
            "current_phase": state.current_phase.name,
            "current_turn": state.current_turn,
            "started_at": state.started_at.isoformat(),
            "strategy": state.strategy.value,
            "completion_percentage": state.progress.completion_percentage,
            "completed_milestones": state.progress.completed_milestones,
            "pending_milestones": state.progress.pending_milestones,
            "active_hypotheses": state.progress_metrics.active_hypotheses_count,
            "total_hypotheses": len(state.hypotheses),
            "evidence_count": len(state.evidence),
            "momentum": state.progress_metrics.momentum.value,
            "degraded_mode": state.escalation.degraded_mode,
            "degraded_reason": (
                state.escalation.escalation_reason
                if state.escalation.degraded_mode else None
            ),
            "working_conclusion": (
                state.working_conclusion.statement
                if state.working_conclusion else None
            ),
            "conclusion_confidence": (
                state.working_conclusion.confidence
                if state.working_conclusion else None
            ),
        }

    async def acknowledge_degraded_mode(
        self,
        case_id: str,
        user_id: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Acknowledge degraded mode to continue investigation.

        Args:
            case_id: Case ID
            user_id: User ID for ownership verification

        Returns:
            Tuple of (success, error_message)
        """
        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return False, "Case not found"

        data = case.case_metadata.get(self.INVESTIGATION_KEY)
        if not data:
            return False, "Investigation not initialized"

        state = InvestigationState.from_dict(data)

        if not state.escalation.degraded_mode:
            return False, "Not in degraded mode"

        state.escalation.user_acknowledged = True
        state.progress_metrics.turns_without_progress = 0  # Reset counter

        # Update case
        case.case_metadata[self.INVESTIGATION_KEY] = state.to_dict()
        flag_modified(case, "case_metadata")
        await self.case_service.db.commit()

        return True, None
