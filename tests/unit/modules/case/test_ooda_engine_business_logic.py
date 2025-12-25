"""
Business logic tests for OODAEngine.

These tests validate ACTUAL ALGORITHMS and BUSINESS RULES, not just existence checks.

Tested Algorithms:
1. Adaptive intensity determination: light/medium/full based on phase and iteration count
2. Anchoring prevention triggers: 3 conditions
3. Iteration continuation logic: min/max iterations, validation completion
4. Phase-specific intensity configs

Source: FaultMaven-Mono ooda_engine.py
"""

import pytest

from faultmaven.modules.case.engines import (
    OODAEngine,
    AdaptiveIntensityController,
    create_ooda_engine,
)
from faultmaven.modules.case.investigation import (
    InvestigationState,
    HypothesisModel,
    OODAState,
)
from faultmaven.modules.case.enums import (
    InvestigationPhase,
    HypothesisStatus,
)


class TestAdaptiveIntensityControl:
    """Validate adaptive intensity determination algorithm.

    Rules:
    - INTAKE: none (no OODA)
    - BLAST_RADIUS/TIMELINE: always light
    - HYPOTHESIS: light (≤2 iter), medium (3+ iter)
    - VALIDATION: medium (≤2 iter), full (3+ iter)
    - SOLUTION: always medium
    - DOCUMENT: always light

    Source: FaultMaven-Mono lines 58-97
    """

    def test_intake_phase_has_no_ooda(self):
        """INTAKE phase returns 'none' intensity"""
        controller = AdaptiveIntensityController()

        intensity = controller.get_intensity_level(
            iteration_count=5,
            phase=InvestigationPhase.INTAKE
        )

        assert intensity == "none"

    def test_blast_radius_always_light(self):
        """BLAST_RADIUS phase is always light regardless of iterations"""
        controller = AdaptiveIntensityController()

        # Test with different iteration counts
        for iter_count in [1, 5, 10]:
            intensity = controller.get_intensity_level(
                iteration_count=iter_count,
                phase=InvestigationPhase.BLAST_RADIUS
            )
            assert intensity == "light", f"Failed at iteration {iter_count}"

    def test_timeline_always_light(self):
        """TIMELINE phase is always light regardless of iterations"""
        controller = AdaptiveIntensityController()

        for iter_count in [1, 5, 10]:
            intensity = controller.get_intensity_level(
                iteration_count=iter_count,
                phase=InvestigationPhase.TIMELINE
            )
            assert intensity == "light", f"Failed at iteration {iter_count}"

    def test_hypothesis_phase_intensity_progression(self):
        """HYPOTHESIS phase: light ≤2 iterations, medium 3+"""
        controller = AdaptiveIntensityController()

        # Iterations 1-2: light
        assert controller.get_intensity_level(1, InvestigationPhase.HYPOTHESIS) == "light"
        assert controller.get_intensity_level(2, InvestigationPhase.HYPOTHESIS) == "light"

        # Iteration 3+: medium
        assert controller.get_intensity_level(3, InvestigationPhase.HYPOTHESIS) == "medium"
        assert controller.get_intensity_level(5, InvestigationPhase.HYPOTHESIS) == "medium"

    def test_validation_phase_intensity_progression(self):
        """VALIDATION phase: medium ≤2 iterations, full 3+"""
        controller = AdaptiveIntensityController()

        # Iterations 1-2: medium
        assert controller.get_intensity_level(1, InvestigationPhase.VALIDATION) == "medium"
        assert controller.get_intensity_level(2, InvestigationPhase.VALIDATION) == "medium"

        # Iteration 3+: full
        assert controller.get_intensity_level(3, InvestigationPhase.VALIDATION) == "full"
        assert controller.get_intensity_level(6, InvestigationPhase.VALIDATION) == "full"

    def test_solution_always_medium(self):
        """SOLUTION phase is always medium"""
        controller = AdaptiveIntensityController()

        for iter_count in [1, 3, 5]:
            intensity = controller.get_intensity_level(
                iteration_count=iter_count,
                phase=InvestigationPhase.SOLUTION
            )
            assert intensity == "medium"

    def test_document_always_light(self):
        """DOCUMENT phase is always light"""
        controller = AdaptiveIntensityController()

        intensity = controller.get_intensity_level(
            iteration_count=1,
            phase=InvestigationPhase.DOCUMENT
        )
        assert intensity == "light"


class TestAnchoringPreventionTriggers:
    """Validate anchoring detection algorithm.

    Conditions:
    1. ≥4 hypotheses in same category
    2. Multiple hypotheses (≥1) with ≥3 iterations_without_progress
    3. Top hypothesis stagnant ≥3 iterations with <70% confidence

    Must have ≥3 iterations before any anchoring triggers.

    Source: FaultMaven-Mono lines 100-157
    """

    def test_no_anchoring_before_3_iterations(self):
        """Anchoring cannot trigger before 3 iterations"""
        controller = AdaptiveIntensityController()

        # Create many stalled hypotheses
        hypotheses = []
        for i in range(5):
            hyp = HypothesisModel(
                hypothesis_id=f"hyp_{i}",
                statement=f"Hypothesis {i}",
                category="infrastructure",
                likelihood=0.50,
                initial_likelihood=0.50,
            )
            hyp.iterations_without_progress = 5  # Highly stalled
            hypotheses.append(hyp)

        # Test with iterations < 3
        should_trigger, reason = controller.should_trigger_anchoring_prevention(
            iteration_count=2,
            hypotheses=hypotheses
        )

        assert should_trigger is False
        assert reason is None

    def test_anchoring_by_category_clustering(self):
        """Condition 1: ≥4 hypotheses in same category"""
        controller = AdaptiveIntensityController()

        # Create 4 hypotheses in "infrastructure" category
        hypotheses = []
        for i in range(4):
            hyp = HypothesisModel(
                hypothesis_id=f"hyp_{i}",
                statement=f"Infrastructure hypothesis {i}",
                category="infrastructure",
                likelihood=0.50,
                initial_likelihood=0.50,
                status=HypothesisStatus.ACTIVE,
            )
            hypotheses.append(hyp)

        should_trigger, reason = controller.should_trigger_anchoring_prevention(
            iteration_count=3,
            hypotheses=hypotheses
        )

        assert should_trigger is True
        assert "4 hypotheses in 'infrastructure' category" in reason

    def test_no_anchoring_with_only_3_in_same_category(self):
        """Not anchored with only 3 hypotheses in same category"""
        controller = AdaptiveIntensityController()

        # Create only 3 hypotheses in same category
        hypotheses = []
        for i in range(3):
            hyp = HypothesisModel(
                hypothesis_id=f"hyp_{i}",
                statement=f"Code hypothesis {i}",
                category="code",
                likelihood=0.50,
                initial_likelihood=0.50,
                status=HypothesisStatus.ACTIVE,
            )
            hypotheses.append(hyp)

        should_trigger, reason = controller.should_trigger_anchoring_prevention(
            iteration_count=3,
            hypotheses=hypotheses
        )

        assert should_trigger is False

    def test_anchoring_by_multiple_stalled(self):
        """Condition 2: Multiple hypotheses with ≥3 iterations_without_progress"""
        controller = AdaptiveIntensityController()

        # Create 2 stalled hypotheses in different categories
        hypotheses = []
        for i in range(2):
            hyp = HypothesisModel(
                hypothesis_id=f"hyp_{i}",
                statement=f"Stalled hypothesis {i}",
                category=f"category_{i}",  # Different categories
                likelihood=0.50,
                initial_likelihood=0.50,
                status=HypothesisStatus.ACTIVE,
            )
            hyp.iterations_without_progress = 3  # Exactly at threshold
            hypotheses.append(hyp)

        should_trigger, reason = controller.should_trigger_anchoring_prevention(
            iteration_count=3,
            hypotheses=hypotheses
        )

        assert should_trigger is True
        assert "hypotheses without progress" in reason

    def test_anchoring_by_stagnant_top_hypothesis(self):
        """Condition 3: Top hypothesis stagnant ≥3 iterations with <70% confidence"""
        controller = AdaptiveIntensityController()

        # Create top hypothesis (highest likelihood) that's stagnant
        hypotheses = []

        top_hyp = HypothesisModel(
            hypothesis_id="hyp_top",
            statement="Stagnant top hypothesis",
            category="infrastructure",
            likelihood=0.65,  # Below 70%
            initial_likelihood=0.65,
            status=HypothesisStatus.ACTIVE,
        )
        top_hyp.iterations_without_progress = 3  # Exactly threshold
        hypotheses.append(top_hyp)

        # Lower confidence hypothesis
        low_hyp = HypothesisModel(
            hypothesis_id="hyp_low",
            statement="Lower hypothesis",
            category="code",
            likelihood=0.30,
            initial_likelihood=0.30,
            status=HypothesisStatus.ACTIVE,
        )
        hypotheses.append(low_hyp)

        should_trigger, reason = controller.should_trigger_anchoring_prevention(
            iteration_count=3,
            hypotheses=hypotheses
        )

        assert should_trigger is True
        assert "Top hypothesis stagnant" in reason

    def test_no_anchoring_when_top_hypothesis_high_confidence(self):
        """High confidence (≥70%) exempts from condition 3"""
        controller = AdaptiveIntensityController()

        hypotheses = []

        # Top hypothesis with high confidence
        top_hyp = HypothesisModel(
            hypothesis_id="hyp_top",
            statement="High confidence top",
            category="code",
            likelihood=0.75,  # Above 70%
            initial_likelihood=0.75,
            status=HypothesisStatus.ACTIVE,
        )
        top_hyp.iterations_without_progress = 5  # High stagnation
        hypotheses.append(top_hyp)

        should_trigger, reason = controller.should_trigger_anchoring_prevention(
            iteration_count=5,
            hypotheses=hypotheses
        )

        assert should_trigger is False

    def test_retired_and_refuted_excluded_from_anchoring(self):
        """RETIRED and REFUTED hypotheses don't count for anchoring"""
        controller = AdaptiveIntensityController()

        hypotheses = []

        # Create 4 hypotheses in same category, but 2 are RETIRED
        for i in range(4):
            hyp = HypothesisModel(
                hypothesis_id=f"hyp_{i}",
                statement=f"Hypothesis {i}",
                category="infrastructure",
                likelihood=0.50,
                initial_likelihood=0.50,
                status=HypothesisStatus.RETIRED if i < 2 else HypothesisStatus.ACTIVE,
            )
            hypotheses.append(hyp)

        should_trigger, reason = controller.should_trigger_anchoring_prevention(
            iteration_count=3,
            hypotheses=hypotheses
        )

        # Only 2 ACTIVE hypotheses, so no anchoring
        assert should_trigger is False


class TestIterationContinuationLogic:
    """Validate iteration continuation decision logic.

    Rules:
    - Continue if current_iter < min_iterations
    - Stop if current_iter >= max_iterations
    - Continue if anchoring detected
    - Continue if no validated hypothesis in VALIDATION phase
    - Stop otherwise

    Source: FaultMaven-Mono lines 474-520
    """

    def test_continue_when_below_minimum(self):
        """Continue when current_iter < min_iterations"""
        engine = OODAEngine()
        inv_state = InvestigationState(
            investigation_id="inv_001",
            current_phase=InvestigationPhase.HYPOTHESIS,
        )
        inv_state.ooda_state = OODAState(current_iteration=1)

        should_continue, reason = engine.should_continue_iterations(
            inv_state,
            max_iterations=5,
            min_iterations=2
        )

        assert should_continue is True
        assert "Minimum iterations" in reason

    def test_stop_when_max_reached(self):
        """Stop when current_iter >= max_iterations"""
        engine = OODAEngine()
        inv_state = InvestigationState(
            investigation_id="inv_001",
            current_phase=InvestigationPhase.HYPOTHESIS,
        )
        inv_state.ooda_state = OODAState(current_iteration=6)

        should_continue, reason = engine.should_continue_iterations(
            inv_state,
            max_iterations=6,
            min_iterations=2
        )

        assert should_continue is False
        assert "Max iterations (6) reached" in reason

    def test_continue_when_anchoring_detected(self):
        """Continue when anchoring detected (even past minimum)"""
        engine = OODAEngine()
        inv_state = InvestigationState(
            investigation_id="inv_001",
            current_phase=InvestigationPhase.HYPOTHESIS,
        )
        inv_state.ooda_state = OODAState(current_iteration=3)

        # Create 4 hypotheses in same category to trigger anchoring
        inv_state.hypotheses = []
        for i in range(4):
            hyp = HypothesisModel(
                hypothesis_id=f"hyp_{i}",
                statement=f"Hypothesis {i}",
                category="infrastructure",
                likelihood=0.50,
                initial_likelihood=0.50,
                status=HypothesisStatus.ACTIVE,
            )
            inv_state.hypotheses.append(hyp)

        should_continue, reason = engine.should_continue_iterations(
            inv_state,
            max_iterations=5,
            min_iterations=2
        )

        assert should_continue is True
        assert "anchoring" in reason.lower()

    def test_continue_validation_without_validated_hypothesis(self):
        """Continue VALIDATION phase if no validated hypothesis"""
        engine = OODAEngine()
        inv_state = InvestigationState(
            investigation_id="inv_001",
            current_phase=InvestigationPhase.VALIDATION,
        )
        inv_state.ooda_state = OODAState(current_iteration=2)

        # Add active hypothesis (not validated)
        inv_state.hypotheses = [
            HypothesisModel(
                hypothesis_id="hyp_1",
                statement="Active hypothesis",
                category="code",
                likelihood=0.50,
                initial_likelihood=0.50,
                status=HypothesisStatus.ACTIVE,
            )
        ]

        should_continue, reason = engine.should_continue_iterations(
            inv_state,
            max_iterations=6,
            min_iterations=2
        )

        assert should_continue is True
        assert "No validated hypothesis yet" in reason

    def test_stop_validation_when_hypothesis_validated(self):
        """Stop VALIDATION phase when hypothesis validated with ≥70% confidence"""
        engine = OODAEngine()
        inv_state = InvestigationState(
            investigation_id="inv_001",
            current_phase=InvestigationPhase.VALIDATION,
        )
        inv_state.ooda_state = OODAState(current_iteration=3)

        # Add validated hypothesis with sufficient confidence
        inv_state.hypotheses = [
            HypothesisModel(
                hypothesis_id="hyp_1",
                statement="Validated hypothesis",
                category="code",
                likelihood=0.75,  # ≥70%
                initial_likelihood=0.50,
                status=HypothesisStatus.VALIDATED,
            )
        ]

        should_continue, reason = engine.should_continue_iterations(
            inv_state,
            max_iterations=6,
            min_iterations=2
        )

        assert should_continue is False
        assert "objectives achieved" in reason.lower()

    def test_stop_when_objectives_achieved(self):
        """Stop when phase objectives achieved (non-VALIDATION phase)"""
        engine = OODAEngine()
        inv_state = InvestigationState(
            investigation_id="inv_001",
            current_phase=InvestigationPhase.HYPOTHESIS,
        )
        inv_state.ooda_state = OODAState(current_iteration=3)

        should_continue, reason = engine.should_continue_iterations(
            inv_state,
            max_iterations=5,
            min_iterations=2
        )

        # Past minimum, no anchoring, not VALIDATION → stop
        assert should_continue is False
        assert "objectives achieved" in reason.lower()


class TestPhaseIntensityConfiguration:
    """Validate phase-specific iteration configs.

    Expected configs:
    - INTAKE: (0, 0) - no OODA
    - BLAST_RADIUS: (1, 2)
    - TIMELINE: (1, 2)
    - HYPOTHESIS: (2, 3)
    - VALIDATION: (3, 6)
    - SOLUTION: (2, 4)
    - DOCUMENT: (1, 1)

    Source: Derived from FaultMaven-Mono phase definitions
    """

    def test_intake_no_iterations(self):
        """INTAKE phase has no OODA iterations"""
        engine = OODAEngine()
        min_iter, max_iter = engine.get_phase_intensity_config(InvestigationPhase.INTAKE)

        assert min_iter == 0
        assert max_iter == 0

    def test_blast_radius_light_config(self):
        """BLAST_RADIUS phase: (1, 2) iterations"""
        engine = OODAEngine()
        min_iter, max_iter = engine.get_phase_intensity_config(InvestigationPhase.BLAST_RADIUS)

        assert min_iter == 1
        assert max_iter == 2

    def test_timeline_light_config(self):
        """TIMELINE phase: (1, 2) iterations"""
        engine = OODAEngine()
        min_iter, max_iter = engine.get_phase_intensity_config(InvestigationPhase.TIMELINE)

        assert min_iter == 1
        assert max_iter == 2

    def test_hypothesis_medium_config(self):
        """HYPOTHESIS phase: (2, 3) iterations"""
        engine = OODAEngine()
        min_iter, max_iter = engine.get_phase_intensity_config(InvestigationPhase.HYPOTHESIS)

        assert min_iter == 2
        assert max_iter == 3

    def test_validation_full_config(self):
        """VALIDATION phase: (3, 6) iterations"""
        engine = OODAEngine()
        min_iter, max_iter = engine.get_phase_intensity_config(InvestigationPhase.VALIDATION)

        assert min_iter == 3
        assert max_iter == 6

    def test_solution_medium_config(self):
        """SOLUTION phase: (2, 4) iterations"""
        engine = OODAEngine()
        min_iter, max_iter = engine.get_phase_intensity_config(InvestigationPhase.SOLUTION)

        assert min_iter == 2
        assert max_iter == 4

    def test_document_light_config(self):
        """DOCUMENT phase: (1, 1) iteration"""
        engine = OODAEngine()
        min_iter, max_iter = engine.get_phase_intensity_config(InvestigationPhase.DOCUMENT)

        assert min_iter == 1
        assert max_iter == 1


class TestOODAEngineIntegration:
    """Integration tests for OODAEngine."""

    def test_engine_initialization(self):
        """Engine initializes with correct components"""
        engine = OODAEngine()

        assert isinstance(engine.intensity_controller, AdaptiveIntensityController)
        assert engine.logger is not None

    def test_factory_function(self):
        """Factory function creates configured engine"""
        engine = create_ooda_engine()

        assert isinstance(engine, OODAEngine)
        assert isinstance(engine.intensity_controller, AdaptiveIntensityController)

    def test_get_current_intensity(self):
        """get_current_intensity returns correct intensity for state"""
        engine = OODAEngine()
        inv_state = InvestigationState(
            investigation_id="inv_001",
            current_phase=InvestigationPhase.VALIDATION,
        )
        inv_state.ooda_state = OODAState(current_iteration=3)

        intensity = engine.get_current_intensity(inv_state)

        # VALIDATION with 3 iterations → full
        assert intensity == "full"

    def test_start_new_iteration(self):
        """start_new_iteration creates valid OODAIteration"""
        engine = OODAEngine()
        inv_state = InvestigationState(
            investigation_id="inv_001",
            current_phase=InvestigationPhase.HYPOTHESIS,
            current_turn=5,
        )
        inv_state.ooda_state = OODAState(current_iteration=2)

        iteration = engine.start_new_iteration(inv_state)

        assert iteration.iteration_id.startswith("ooda_")
        assert iteration.turn_number == 5
        assert iteration.phase == InvestigationPhase.HYPOTHESIS
        assert iteration.current_step == "observe"
        assert iteration.made_progress is False

    def test_check_anchoring_prevention(self):
        """check_anchoring_prevention delegates to controller correctly"""
        engine = OODAEngine()
        inv_state = InvestigationState(
            investigation_id="inv_001",
            current_phase=InvestigationPhase.HYPOTHESIS,
        )
        inv_state.ooda_state = OODAState(current_iteration=3)

        # Create 4 hypotheses in same category
        inv_state.hypotheses = []
        for i in range(4):
            hyp = HypothesisModel(
                hypothesis_id=f"hyp_{i}",
                statement=f"Hypothesis {i}",
                category="infrastructure",
                likelihood=0.50,
                initial_likelihood=0.50,
                status=HypothesisStatus.ACTIVE,
            )
            inv_state.hypotheses.append(hyp)

        should_trigger, reason = engine.check_anchoring_prevention(inv_state)

        assert should_trigger is True
        assert "4 hypotheses" in reason
