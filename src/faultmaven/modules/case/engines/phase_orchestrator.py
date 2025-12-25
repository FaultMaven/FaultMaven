"""
Phase Orchestrator and Loop-Back Mechanism

Handles phase progression, loop-back patterns, and degraded mode detection.

Key Design Principles:
- Phase progression is not strictly unidirectional
- Failed validation should loop back to hypothesis generation
- New information may require revisiting earlier phases
- Safety limits prevent infinite loops
- Escalation via degraded mode when progress blocked

Source: FaultMaven-Mono phase_loopback.py (lines 1-320)
"""

import logging
from typing import Optional, Tuple, List
from enum import Enum

from faultmaven.modules.case.investigation import InvestigationState
from faultmaven.modules.case.enums import InvestigationPhase, HypothesisStatus

logger = logging.getLogger(__name__)


class PhaseOutcome(str, Enum):
    """
    Phase completion outcomes that determine next phase.

    Source: FaultMaven-Mono lines 29-38
    """
    COMPLETED = "completed"                      # Normal completion → advance
    HYPOTHESIS_REFUTED = "hypothesis_refuted"    # All refuted → loop to HYPOTHESIS
    SCOPE_CHANGED = "scope_changed"              # Scope changed → loop to BLAST_RADIUS
    TIMELINE_WRONG = "timeline_wrong"            # Timeline wrong → loop to TIMELINE
    NEED_MORE_DATA = "need_more_data"            # Insufficient evidence → stay
    STALLED = "stalled"                          # No progress → degraded mode
    ESCALATION_NEEDED = "escalation_needed"      # Human guidance needed


class LoopBackReason(str, Enum):
    """
    Detailed reasons for loop-back.

    Source: FaultMaven-Mono lines 41-51
    """
    ALL_HYPOTHESES_REFUTED = "all_hypotheses_refuted"
    INSUFFICIENT_HYPOTHESES = "insufficient_hypotheses"
    SCOPE_EXPANSION = "scope_expansion"
    SCOPE_REDUCTION = "scope_reduction"
    TIMELINE_REVISION_NEEDED = "timeline_revision_needed"
    CORRELATION_FOUND = "correlation_found"
    EVIDENCE_GAP_IDENTIFIED = "evidence_gap_identified"
    MAX_LOOPS_EXCEEDED = "max_loops_exceeded"


class PhaseOrchestratorError(Exception):
    """Base exception for PhaseOrchestrator errors."""
    pass


class PhaseOrchestrator:
    """
    Handles phase progression and loop-back decisions.

    Safety Features:
    - Maximum 3 loop-backs per investigation
    - Escalation options when max exceeded
    - Loop-back tracking and metrics

    Source: FaultMaven-Mono lines 54-320
    """

    MAX_LOOP_BACKS = 3

    def __init__(self):
        """Initialize PhaseOrchestrator."""
        self.logger = logging.getLogger(__name__)
        self.loop_back_history: List[Tuple[InvestigationPhase, InvestigationPhase, str]] = []

    def determine_next_phase(
        self,
        inv_state: InvestigationState,
        outcome: PhaseOutcome,
        reason: Optional[LoopBackReason] = None,
    ) -> Tuple[InvestigationPhase, bool, Optional[str]]:
        """
        Determine next phase based on current phase and outcome.

        Args:
            inv_state: Current investigation state
            outcome: Phase completion outcome
            reason: Optional detailed reason for outcome

        Returns:
            Tuple of (next_phase, is_loop_back, message)

        Source: FaultMaven-Mono lines 68-140
        """
        current_phase = inv_state.current_phase

        self.logger.info(
            f"Determining next phase: {current_phase.value} → outcome={outcome.value}",
            extra={"reason": reason.value if reason else None}
        )

        # Handle normal completion
        if outcome == PhaseOutcome.COMPLETED:
            return self._handle_completed(current_phase, inv_state)

        # Handle loop-back outcomes
        elif outcome == PhaseOutcome.HYPOTHESIS_REFUTED:
            return self._handle_hypothesis_refuted(current_phase, inv_state, reason)

        elif outcome == PhaseOutcome.SCOPE_CHANGED:
            return self._handle_scope_changed(current_phase, inv_state, reason)

        elif outcome == PhaseOutcome.TIMELINE_WRONG:
            return self._handle_timeline_wrong(current_phase, inv_state, reason)

        elif outcome == PhaseOutcome.NEED_MORE_DATA:
            return self._handle_need_more_data(current_phase, inv_state)

        elif outcome == PhaseOutcome.STALLED:
            return self._handle_stalled(current_phase, inv_state)

        elif outcome == PhaseOutcome.ESCALATION_NEEDED:
            return self._handle_escalation(current_phase, inv_state)

        else:
            raise PhaseOrchestratorError(f"Unknown phase outcome: {outcome}")

    def _handle_completed(
        self,
        current_phase: InvestigationPhase,
        inv_state: InvestigationState,
    ) -> Tuple[InvestigationPhase, bool, Optional[str]]:
        """
        Handle normal phase completion → advance to next phase.

        Args:
            current_phase: Current phase
            inv_state: Investigation state

        Returns:
            Tuple of (next_phase, is_loop_back, message)

        Source: FaultMaven-Mono lines 150-180
        """
        phase_sequence = [
            InvestigationPhase.INTAKE,
            InvestigationPhase.BLAST_RADIUS,
            InvestigationPhase.TIMELINE,
            InvestigationPhase.HYPOTHESIS,
            InvestigationPhase.VALIDATION,
            InvestigationPhase.SOLUTION,
            InvestigationPhase.DOCUMENT,
        ]

        current_index = phase_sequence.index(current_phase)
        if current_index < len(phase_sequence) - 1:
            next_phase = phase_sequence[current_index + 1]
            message = f"Advancing to {next_phase.value}"
            return next_phase, False, message
        else:
            # Already at final phase
            return current_phase, False, "Investigation complete"

    def _handle_hypothesis_refuted(
        self,
        current_phase: InvestigationPhase,
        inv_state: InvestigationState,
        reason: Optional[LoopBackReason],
    ) -> Tuple[InvestigationPhase, bool, Optional[str]]:
        """
        Handle all hypotheses refuted → loop back to HYPOTHESIS phase.

        Args:
            current_phase: Current phase
            inv_state: Investigation state
            reason: Loop-back reason

        Returns:
            Tuple of (next_phase, is_loop_back, message)

        Source: FaultMaven-Mono lines 190-220
        """
        # Check loop-back limit
        if len(self.loop_back_history) >= self.MAX_LOOP_BACKS:
            return self._trigger_degraded_mode(
                current_phase,
                "Maximum loop-backs exceeded"
            )

        # Loop back to HYPOTHESIS phase
        next_phase = InvestigationPhase.HYPOTHESIS
        message = f"All hypotheses refuted, looping back to {next_phase.value}"

        # Record loop-back
        self.loop_back_history.append((
            current_phase,
            next_phase,
            reason.value if reason else "hypothesis_refuted"
        ))

        return next_phase, True, message

    def _handle_scope_changed(
        self,
        current_phase: InvestigationPhase,
        inv_state: InvestigationState,
        reason: Optional[LoopBackReason],
    ) -> Tuple[InvestigationPhase, bool, Optional[str]]:
        """
        Handle scope change → loop back to BLAST_RADIUS phase.

        Args:
            current_phase: Current phase
            inv_state: Investigation state
            reason: Loop-back reason

        Returns:
            Tuple of (next_phase, is_loop_back, message)

        Source: FaultMaven-Mono lines 230-260
        """
        # Check loop-back limit
        if len(self.loop_back_history) >= self.MAX_LOOP_BACKS:
            return self._trigger_degraded_mode(
                current_phase,
                "Maximum loop-backs exceeded"
            )

        # Loop back to BLAST_RADIUS phase
        next_phase = InvestigationPhase.BLAST_RADIUS
        message = f"Scope changed, looping back to {next_phase.value}"

        # Record loop-back
        self.loop_back_history.append((
            current_phase,
            next_phase,
            reason.value if reason else "scope_changed"
        ))

        return next_phase, True, message

    def _handle_timeline_wrong(
        self,
        current_phase: InvestigationPhase,
        inv_state: InvestigationState,
        reason: Optional[LoopBackReason],
    ) -> Tuple[InvestigationPhase, bool, Optional[str]]:
        """
        Handle timeline error → loop back to TIMELINE phase.

        Args:
            current_phase: Current phase
            inv_state: Investigation state
            reason: Loop-back reason

        Returns:
            Tuple of (next_phase, is_loop_back, message)

        Source: FaultMaven-Mono lines 270-300
        """
        # Check loop-back limit
        if len(self.loop_back_history) >= self.MAX_LOOP_BACKS:
            return self._trigger_degraded_mode(
                current_phase,
                "Maximum loop-backs exceeded"
            )

        # Loop back to TIMELINE phase
        next_phase = InvestigationPhase.TIMELINE
        message = f"Timeline incorrect, looping back to {next_phase.value}"

        # Record loop-back
        self.loop_back_history.append((
            current_phase,
            next_phase,
            reason.value if reason else "timeline_wrong"
        ))

        return next_phase, True, message

    def _handle_need_more_data(
        self,
        current_phase: InvestigationPhase,
        inv_state: InvestigationState,
    ) -> Tuple[InvestigationPhase, bool, Optional[str]]:
        """
        Handle insufficient data → stay in current phase.

        Args:
            current_phase: Current phase
            inv_state: Investigation state

        Returns:
            Tuple of (next_phase, is_loop_back, message)
        """
        message = "Insufficient data, staying in current phase"
        return current_phase, False, message

    def _handle_stalled(
        self,
        current_phase: InvestigationPhase,
        inv_state: InvestigationState,
    ) -> Tuple[InvestigationPhase, bool, Optional[str]]:
        """
        Handle stalled progress → enter degraded mode.

        Args:
            current_phase: Current phase
            inv_state: Investigation state

        Returns:
            Tuple of (next_phase, is_loop_back, message)
        """
        return self._trigger_degraded_mode(current_phase, "Investigation stalled")

    def _handle_escalation(
        self,
        current_phase: InvestigationPhase,
        inv_state: InvestigationState,
    ) -> Tuple[InvestigationPhase, bool, Optional[str]]:
        """
        Handle escalation needed → stay in phase, signal for human intervention.

        Args:
            current_phase: Current phase
            inv_state: Investigation state

        Returns:
            Tuple of (next_phase, is_loop_back, message)
        """
        message = "Human guidance needed, staying in current phase"
        return current_phase, False, message

    def _trigger_degraded_mode(
        self,
        current_phase: InvestigationPhase,
        reason: str,
    ) -> Tuple[InvestigationPhase, bool, Optional[str]]:
        """
        Trigger degraded mode when unable to make progress.

        Args:
            current_phase: Current phase
            reason: Reason for degraded mode

        Returns:
            Tuple of (next_phase, is_loop_back, message)
        """
        message = f"Degraded mode triggered: {reason}"
        self.logger.warning(f"Entering degraded mode: {reason}")
        return current_phase, False, message

    def detect_loopback_needed(
        self,
        inv_state: InvestigationState,
    ) -> Tuple[bool, Optional[PhaseOutcome], Optional[LoopBackReason]]:
        """
        Detect if loop-back is needed based on investigation state.

        Args:
            inv_state: Current investigation state

        Returns:
            Tuple of (needs_loopback, outcome, reason)

        Source: Based on FaultMaven-Mono logic
        """
        # Check if all hypotheses refuted
        if inv_state.current_phase in [InvestigationPhase.VALIDATION, InvestigationPhase.SOLUTION]:
            active_hypotheses = [
                h for h in inv_state.hypotheses
                if h.status in [HypothesisStatus.ACTIVE, HypothesisStatus.VALIDATED]
            ]

            if not active_hypotheses and len(inv_state.hypotheses) > 0:
                # All hypotheses refuted
                return True, PhaseOutcome.HYPOTHESIS_REFUTED, LoopBackReason.ALL_HYPOTHESES_REFUTED

        # Check if insufficient hypotheses
        if inv_state.current_phase == InvestigationPhase.VALIDATION:
            if len(inv_state.hypotheses) < 1:
                return True, PhaseOutcome.HYPOTHESIS_REFUTED, LoopBackReason.INSUFFICIENT_HYPOTHESES

        # No loop-back needed
        return False, None, None

    def get_loop_back_count(self) -> int:
        """Get count of loop-backs in current investigation."""
        return len(self.loop_back_history)

    def is_at_loop_back_limit(self) -> bool:
        """Check if at maximum loop-back limit."""
        return len(self.loop_back_history) >= self.MAX_LOOP_BACKS
