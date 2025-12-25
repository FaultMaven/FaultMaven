"""
Working Conclusion Generator

Generates the agent's current best understanding of the root cause
and tracks investigation progress metrics.

This module is called EVERY turn to maintain a coherent investigation narrative
and provide the user with transparency about the current state of understanding.

Source: FaultMaven-Mono working_conclusion_generator.py (lines 1-494)
"""

import logging
from typing import List, Optional, Tuple

from faultmaven.modules.case.investigation import (
    InvestigationState,
    WorkingConclusion,
    ProgressMetrics,
    HypothesisModel,
    EvidenceItem,
    TurnRecord,
)
from faultmaven.modules.case.enums import (
    HypothesisStatus,
    ConfidenceLevel,
    InvestigationPhase,
    InvestigationMomentum,
)

logger = logging.getLogger(__name__)


class WorkingConclusionGeneratorError(Exception):
    """Base exception for WorkingConclusionGenerator errors."""
    pass


class WorkingConclusionGenerator:
    """
    Generates working conclusions and progress metrics.

    Responsibilities:
    - Generate current best understanding based on hypothesis confidence
    - Calculate investigation progress metrics
    - Determine if can proceed with solution
    - Identify next evidence needed

    Source: FaultMaven-Mono working_conclusion_generator.py lines 24-280
    """

    def __init__(self):
        """Initialize WorkingConclusionGenerator."""
        self.logger = logging.getLogger(__name__)

    def generate_conclusion(
        self,
        inv_state: InvestigationState,
    ) -> WorkingConclusion:
        """
        Generate working conclusion based on current investigation state.

        Called EVERY turn to maintain agent's current best understanding.

        Args:
            inv_state: Current investigation state

        Returns:
            WorkingConclusion with confidence level and evidence basis

        Source: FaultMaven-Mono lines 24-105
        """
        # Get active and validated hypotheses
        active_hypotheses = [
            h for h in inv_state.hypotheses
            if h.status in [HypothesisStatus.ACTIVE, HypothesisStatus.VALIDATED]
        ]

        if not active_hypotheses:
            # No active hypotheses - early phase or all refuted
            return self._create_early_phase_conclusion(inv_state)

        # Get hypothesis with highest confidence
        best_hypothesis = max(active_hypotheses, key=lambda h: h.likelihood)

        # Calculate evidence metrics
        supporting_count = len([
            e for e in inv_state.evidence
            if best_hypothesis.hypothesis_id in e.supports_hypotheses
        ])

        # Determine confidence level
        confidence = best_hypothesis.likelihood
        confidence_level = self._get_confidence_level(confidence)

        # Generate caveats
        caveats = self._generate_caveats(best_hypothesis, inv_state)

        # Get alternative explanations
        alternatives = [
            h.statement
            for h in active_hypotheses
            if h.hypothesis_id != best_hypothesis.hypothesis_id and h.likelihood >= 0.30
        ][:3]  # Top 3 alternatives

        # Determine next evidence needed
        next_evidence = self._determine_next_evidence(best_hypothesis, inv_state)

        # Check if can proceed with solution (≥70% confidence)
        can_proceed = confidence >= 0.70

        return WorkingConclusion(
            statement=best_hypothesis.statement,
            confidence=confidence,
            confidence_level=confidence_level,
            supporting_evidence_count=supporting_count,
            caveats=caveats,
            alternative_explanations=alternatives,
            can_proceed_with_solution=can_proceed,
            next_evidence_needed=next_evidence,
            last_updated_turn=inv_state.current_turn,
            last_confidence_change_turn=self._find_last_confidence_change(inv_state),
            generated_at_turn=inv_state.current_turn,
        )

    def calculate_progress(
        self,
        inv_state: InvestigationState,
    ) -> ProgressMetrics:
        """
        Calculate investigation progress metrics.

        Replaces binary "stalled/not-stalled" with continuous measurement.

        Args:
            inv_state: Current investigation state

        Returns:
            ProgressMetrics with momentum and next steps

        Source: FaultMaven-Mono lines 108-200
        """
        # Count hypotheses by status
        active_hypotheses = [
            h for h in inv_state.hypotheses
            if h.status in [HypothesisStatus.ACTIVE, HypothesisStatus.VALIDATED]
        ]
        active_count = len(active_hypotheses)

        # Count evidence
        evidence_provided = len(inv_state.evidence)
        evidence_blocked = sum(1 for h in inv_state.hypotheses for e in h.refuting_evidence_ids)

        # Determine investigation momentum
        momentum = self._determine_momentum(inv_state)

        # Calculate turns since last progress
        turns_since_progress = self._calculate_turns_since_progress(inv_state)

        # Determine if degraded mode
        is_degraded = inv_state.degraded_mode is not None

        # Generate next steps
        next_steps = self._generate_next_steps(inv_state, active_hypotheses)

        return ProgressMetrics(
            evidence_provided_count=evidence_provided,
            evidence_blocked_count=evidence_blocked,
            evidence_pending_count=0,  # Would need evidence_requests to calculate
            active_hypotheses_count=active_count,
            turns_without_progress=turns_since_progress,
            investigation_momentum=momentum,
            next_critical_steps=next_steps,
            is_degraded_mode=is_degraded,
            generated_at_turn=inv_state.current_turn,
        )

    def _create_early_phase_conclusion(
        self,
        inv_state: InvestigationState
    ) -> WorkingConclusion:
        """
        Create conclusion for early investigation phase (no hypotheses yet).

        Args:
            inv_state: Current investigation state

        Returns:
            Early-phase WorkingConclusion

        Source: FaultMaven-Mono lines 210-240
        """
        phase = inv_state.current_phase

        if phase == InvestigationPhase.INTAKE:
            statement = "Gathering initial information about the issue"
        elif phase == InvestigationPhase.BLAST_RADIUS:
            statement = "Assessing scope and impact of the issue"
        elif phase == InvestigationPhase.TIMELINE:
            statement = "Establishing timeline of events"
        else:
            statement = "Developing hypotheses about root cause"

        return WorkingConclusion(
            statement=statement,
            confidence=0.0,
            confidence_level=ConfidenceLevel.SPECULATION,
            supporting_evidence_count=len(inv_state.evidence),
            caveats=["Investigation in early phase"],
            alternative_explanations=[],
            can_proceed_with_solution=False,
            next_evidence_needed=["User input about the issue"],
            last_updated_turn=inv_state.current_turn,
            last_confidence_change_turn=0,
            generated_at_turn=inv_state.current_turn,
        )

    def _get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """
        Convert numeric confidence to categorical level.

        Args:
            confidence: Numeric confidence (0.0-1.0)

        Returns:
            ConfidenceLevel enum

        Source: FaultMaven-Mono lines 250-270
        """
        if confidence >= 0.85:
            return ConfidenceLevel.CERTAIN
        elif confidence >= 0.70:
            return ConfidenceLevel.LIKELY
        elif confidence >= 0.50:
            return ConfidenceLevel.MODERATE
        elif confidence >= 0.30:
            return ConfidenceLevel.POSSIBLE
        else:
            return ConfidenceLevel.SPECULATION

    def _generate_caveats(
        self,
        hypothesis: HypothesisModel,
        inv_state: InvestigationState
    ) -> List[str]:
        """
        Generate caveats for the conclusion.

        Args:
            hypothesis: Best hypothesis
            inv_state: Investigation state

        Returns:
            List of caveats

        Source: FaultMaven-Mono lines 280-320
        """
        caveats = []

        # Low supporting evidence
        supporting_count = len([
            e for e in inv_state.evidence
            if hypothesis.hypothesis_id in e.supports_hypotheses
        ])
        if supporting_count < 2:
            caveats.append("Limited supporting evidence")

        # Confidence not validated
        if hypothesis.likelihood < 0.70:
            caveats.append("Confidence below validation threshold (70%)")

        # Alternative hypotheses exist
        active_alternatives = [
            h for h in inv_state.hypotheses
            if h.status == HypothesisStatus.ACTIVE
            and h.hypothesis_id != hypothesis.hypothesis_id
            and h.likelihood >= 0.30
        ]
        if active_alternatives:
            caveats.append(f"{len(active_alternatives)} alternative explanations not ruled out")

        # No progress recently
        if hypothesis.iterations_without_progress >= 3:
            caveats.append("No recent progress on this hypothesis")

        return caveats

    def _determine_next_evidence(
        self,
        hypothesis: HypothesisModel,
        inv_state: InvestigationState
    ) -> List[str]:
        """
        Determine what evidence is needed next.

        Args:
            hypothesis: Best hypothesis
            inv_state: Investigation state

        Returns:
            List of next evidence needed

        Source: FaultMaven-Mono lines 330-370
        """
        next_evidence = []

        # If confidence low, need more supporting evidence
        if hypothesis.likelihood < 0.70:
            next_evidence.append(f"Evidence to support: {hypothesis.statement}")

        # If alternatives exist, need discriminating evidence
        active_alternatives = [
            h for h in inv_state.hypotheses
            if h.status == HypothesisStatus.ACTIVE
            and h.hypothesis_id != hypothesis.hypothesis_id
            and h.likelihood >= 0.30
        ]
        if active_alternatives:
            next_evidence.append("Evidence to rule out alternative explanations")

        # Default
        if not next_evidence:
            next_evidence.append("Additional validation evidence")

        return next_evidence

    def _find_last_confidence_change(
        self,
        inv_state: InvestigationState
    ) -> int:
        """
        Find the turn when confidence last changed.

        Args:
            inv_state: Investigation state

        Returns:
            Turn number of last confidence change

        Source: FaultMaven-Mono lines 380-410
        """
        # Look through turn history for hypothesis updates
        for turn in reversed(inv_state.turn_history):
            if turn.hypotheses_updated:
                return turn.turn_number

        return 0

    def _determine_momentum(
        self,
        inv_state: InvestigationState
    ) -> InvestigationMomentum:
        """
        Determine investigation momentum.

        Args:
            inv_state: Investigation state

        Returns:
            InvestigationMomentum enum

        Source: FaultMaven-Mono lines 420-460
        """
        # Check recent turns for progress
        recent_turns = inv_state.turn_history[-3:] if inv_state.turn_history else []

        if not recent_turns:
            return InvestigationMomentum.EARLY

        # Count turns with progress
        progress_count = sum(1 for t in recent_turns if t.progress_made)

        if progress_count >= 2:
            return InvestigationMomentum.ACCELERATING
        elif progress_count == 1:
            return InvestigationMomentum.STEADY
        else:
            # Check if any validated hypotheses
            validated = any(
                h.status == HypothesisStatus.VALIDATED
                for h in inv_state.hypotheses
            )
            if validated:
                return InvestigationMomentum.STEADY
            else:
                return InvestigationMomentum.STALLED

    def _calculate_turns_since_progress(
        self,
        inv_state: InvestigationState
    ) -> int:
        """
        Calculate turns since last progress.

        Args:
            inv_state: Investigation state

        Returns:
            Number of turns since progress

        Source: FaultMaven-Mono lines 470-494
        """
        # Look through turn history from most recent
        for i, turn in enumerate(reversed(inv_state.turn_history)):
            if turn.progress_made:
                return i

        # No progress found
        return len(inv_state.turn_history)

    def _generate_next_steps(
        self,
        inv_state: InvestigationState,
        active_hypotheses: List[HypothesisModel]
    ) -> List[str]:
        """
        Generate list of next critical steps.

        Args:
            inv_state: Investigation state
            active_hypotheses: List of active hypotheses

        Returns:
            List of next steps
        """
        next_steps = []

        if not active_hypotheses:
            next_steps.append("Generate new hypotheses")
        elif all(h.likelihood < 0.50 for h in active_hypotheses):
            next_steps.append("Gather evidence to increase confidence")
        elif any(h.likelihood >= 0.70 for h in active_hypotheses):
            next_steps.append("Propose solution based on validated hypothesis")
        else:
            next_steps.append("Continue evidence collection")

        return next_steps
