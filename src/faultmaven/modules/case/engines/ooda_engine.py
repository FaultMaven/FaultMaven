"""OODA Engine - Observe-Orient-Decide-Act Execution Manager

This module implements the OODA (Observe-Orient-Decide-Act) tactical execution
engine for FaultMaven's investigation framework. It manages iteration cycles,
adaptive intensity control, and step-by-step execution within each phase.

Ported from: FaultMaven-Mono/faultmaven/core/investigation/ooda_engine.py

OODA Framework:
- Observe: Gather information and evidence (generate evidence requests)
- Orient: Analyze and contextualize data (process evidence, update hypotheses)
- Decide: Choose action or hypothesis (select test, prioritize)
- Act: Execute test or apply solution (verify, implement)

Adaptive Intensity:
- 1-2 iterations: Light intensity (simple problems)
- 3-5 iterations: Medium intensity (typical investigations)
- 6+ iterations: Full intensity (complex root causes)
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from faultmaven.modules.case.investigation import (
    InvestigationState,
    HypothesisModel,
    OODAIteration,
)
from faultmaven.modules.case.enums import (
    InvestigationPhase,
    OODAStep,
    HypothesisStatus,
)

logger = logging.getLogger(__name__)


class OODAEngineError(Exception):
    """Exception raised by OODAEngine"""
    pass


# =============================================================================
# Adaptive Intensity Controller
# =============================================================================


class AdaptiveIntensityController:
    """Controls investigation intensity based on iteration count and complexity

    Intensity levels determine thoroughness of investigation:
    - Light: Quick assessment, 1-2 iterations
    - Medium: Standard investigation, 3-5 iterations
    - Full: Deep analysis, 6+ iterations with anchoring prevention

    Source: FaultMaven-Mono ooda_engine.py lines 49-158
    """

    @staticmethod
    def get_intensity_level(iteration_count: int, phase: InvestigationPhase) -> str:
        """Determine current intensity level

        Args:
            iteration_count: Number of OODA iterations in current phase
            phase: Current investigation phase

        Returns:
            Intensity level: "light", "medium", or "full"

        Source: FaultMaven-Mono lines 58-97
        """
        # Phase 0 has no OODA
        if phase == InvestigationPhase.INTAKE:
            return "none"

        # Phases 1-2: Always light (1-2 iterations expected)
        if phase in [InvestigationPhase.BLAST_RADIUS, InvestigationPhase.TIMELINE]:
            return "light"

        # Phase 3: Medium (2-3 iterations)
        if phase == InvestigationPhase.HYPOTHESIS:
            if iteration_count <= 2:
                return "light"
            return "medium"

        # Phase 4: Full intensity (3-6+ iterations)
        if phase == InvestigationPhase.VALIDATION:
            if iteration_count <= 2:
                return "medium"
            return "full"

        # Phase 5: Medium (2-4 iterations)
        if phase == InvestigationPhase.SOLUTION:
            return "medium"

        # Phase 6: Light (1 iteration)
        if phase == InvestigationPhase.DOCUMENT:
            return "light"

        return "medium"  # Default

    @staticmethod
    def should_trigger_anchoring_prevention(
        iteration_count: int,
        hypotheses: List[HypothesisModel],
    ) -> Tuple[bool, Optional[str]]:
        """Check if anchoring prevention should be triggered

        Anchoring conditions:
        1. 4+ hypotheses in same category
        2. 3+ iterations without confidence improvement
        3. Repeated testing of same hypothesis

        Args:
            iteration_count: Current OODA iteration count
            hypotheses: List of active hypotheses

        Returns:
            Tuple of (should_trigger, reason)

        Source: FaultMaven-Mono lines 100-157
        """
        if iteration_count < 3:
            return False, None

        # Condition 1: Too many hypotheses in same category
        category_counts: Dict[str, int] = {}
        for h in hypotheses:
            if h.status not in [HypothesisStatus.RETIRED, HypothesisStatus.REFUTED]:
                category_counts[h.category] = category_counts.get(h.category, 0) + 1

        for category, count in category_counts.items():
            if count >= 4:
                return True, f"Anchoring detected: {count} hypotheses in '{category}' category"

        # Condition 2: Multiple hypotheses (≥2) with no progress in 3+ iterations
        stalled_hypotheses = [
            h
            for h in hypotheses
            if h.iterations_without_progress >= 3
            and h.status == HypothesisStatus.ACTIVE
        ]
        if len(stalled_hypotheses) >= 2:
            return True, f"Anchoring detected: {len(stalled_hypotheses)} hypotheses without progress"

        # Condition 3: Check if top hypothesis hasn't changed in 3 iterations
        active_hypotheses = [
            h
            for h in hypotheses
            if h.status not in [HypothesisStatus.RETIRED, HypothesisStatus.REFUTED]
        ]
        if active_hypotheses:
            sorted_by_likelihood = sorted(
                active_hypotheses, key=lambda h: h.likelihood, reverse=True
            )
            if sorted_by_likelihood:
                top_hypothesis = sorted_by_likelihood[0]
                # Note: Using iterations_without_progress as proxy for iterations_as_top
                if top_hypothesis.iterations_without_progress >= 3 and top_hypothesis.likelihood < 0.7:
                    return True, "Anchoring detected: Top hypothesis stagnant for 3+ iterations"

        return False, None


# =============================================================================
# OODA Engine
# =============================================================================


class OODAEngine:
    """OODA (Observe-Orient-Decide-Act) execution engine

    Manages tactical execution within each investigation phase:
    - Starts new OODA iterations
    - Executes individual OODA steps
    - Tracks progress
    - Applies adaptive intensity control
    - Triggers anchoring prevention when needed

    Source: FaultMaven-Mono ooda_engine.py lines 165-521
    """

    def __init__(self):
        """Initialize OODA engine"""
        self.intensity_controller = AdaptiveIntensityController()
        self.logger = logging.getLogger(__name__)

    def get_current_intensity(
        self,
        inv_state: InvestigationState,
    ) -> str:
        """Get current intensity level for investigation

        Args:
            inv_state: Current investigation state

        Returns:
            Intensity level: "light", "medium", "full", or "none"
        """
        iteration_count = inv_state.ooda_state.current_iteration if inv_state.ooda_state else 0
        return self.intensity_controller.get_intensity_level(
            iteration_count,
            inv_state.current_phase
        )

    def start_new_iteration(
        self,
        inv_state: InvestigationState,
    ) -> OODAIteration:
        """Start a new OODA iteration in current phase

        Args:
            inv_state: Current investigation state

        Returns:
            New OODAIteration object

        Source: FaultMaven-Mono lines 181-212
        """
        current_phase = inv_state.current_phase
        iteration_num = (inv_state.ooda_state.current_iteration + 1) if inv_state.ooda_state else 1

        # Get active OODA steps for this phase (simplified - all steps active)
        active_steps = [OODAStep.OBSERVE, OODAStep.ORIENT, OODAStep.DECIDE, OODAStep.ACT]

        iteration = OODAIteration(
            iteration_id=f"ooda_{uuid4().hex[:12]}",
            turn_number=inv_state.current_turn,
            phase=current_phase,
            current_step=OODAStep.OBSERVE.value,
            steps_completed=[],
            made_progress=False,
        )

        self.logger.info(
            f"Started OODA iteration {iteration_num} in phase {current_phase.value}, "
            f"active steps: {[s.value for s in active_steps]}"
        )

        return iteration

    def check_anchoring_prevention(
        self,
        inv_state: InvestigationState,
    ) -> Tuple[bool, Optional[str]]:
        """Check if anchoring prevention should be triggered

        Args:
            inv_state: Current investigation state

        Returns:
            Tuple of (should_trigger, reason)

        Source: FaultMaven-Mono lines 100-157
        """
        iteration_count = inv_state.ooda_state.current_iteration if inv_state.ooda_state else 0
        hypotheses = list(inv_state.hypotheses.values()) if inv_state.hypotheses else []

        return self.intensity_controller.should_trigger_anchoring_prevention(
            iteration_count,
            hypotheses
        )

    def should_continue_iterations(
        self,
        inv_state: InvestigationState,
        max_iterations: int = 6,
        min_iterations: int = 1,
    ) -> Tuple[bool, str]:
        """Determine if more OODA iterations needed in current phase

        Args:
            inv_state: Current investigation state
            max_iterations: Maximum iterations allowed for phase
            min_iterations: Minimum iterations required for phase

        Returns:
            Tuple of (should_continue, reason)

        Source: FaultMaven-Mono lines 474-520
        """
        current_iter = inv_state.ooda_state.current_iteration if inv_state.ooda_state else 0
        phase = inv_state.current_phase

        # Check if max iterations reached
        if current_iter >= max_iterations:
            return False, f"Max iterations ({max_iterations}) reached for phase {phase.value}"

        # Check if minimum iterations not yet met
        if current_iter < min_iterations:
            return True, f"Minimum iterations ({min_iterations}) not yet reached"

        # Check for anchoring
        should_trigger, reason = self.check_anchoring_prevention(inv_state)
        if should_trigger:
            return True, f"Continue to address anchoring: {reason}"

        # Check phase-specific completion
        if phase == InvestigationPhase.VALIDATION:
            # Continue until hypothesis validated
            hypotheses = list(inv_state.hypotheses.values()) if inv_state.hypotheses else []
            validated = any(
                h.status == HypothesisStatus.VALIDATED
                and h.likelihood >= 0.7
                for h in hypotheses
            )
            if not validated:
                return True, "No validated hypothesis yet"

        # Phase completion criteria met
        return False, "Phase objectives achieved"

    def get_phase_intensity_config(
        self,
        phase: InvestigationPhase,
    ) -> Tuple[int, int]:
        """Get min/max iteration config for phase

        Args:
            phase: Investigation phase

        Returns:
            Tuple of (min_iterations, max_iterations)

        Source: Derived from FaultMaven-Mono phase definitions
        """
        phase_configs = {
            InvestigationPhase.INTAKE: (0, 0),          # No OODA
            InvestigationPhase.BLAST_RADIUS: (1, 2),    # Light
            InvestigationPhase.TIMELINE: (1, 2),        # Light
            InvestigationPhase.HYPOTHESIS: (2, 3),      # Medium
            InvestigationPhase.VALIDATION: (3, 6),      # Full
            InvestigationPhase.SOLUTION: (2, 4),        # Medium
            InvestigationPhase.DOCUMENT: (1, 1),        # Light
        }
        return phase_configs.get(phase, (1, 3))  # Default


def create_ooda_engine() -> OODAEngine:
    """Factory function to create OODA engine instance

    Returns:
        Configured OODAEngine instance

    Source: FaultMaven-Mono lines 528-534
    """
    return OODAEngine()
