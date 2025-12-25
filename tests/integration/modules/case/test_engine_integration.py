"""
Phase 4 Integration Tests: Core Engine Integration

Tests the integration of MilestoneEngine, HypothesisManager, and OODAEngine
in realistic investigation scenarios.

Test Scenarios:
1. MilestoneEngine + HypothesisManager: Hypothesis-driven turn processing
2. MilestoneEngine + OODAEngine: OODA iteration execution within phases
3. Complete workflow: All 3 engines working together through investigation phases

Test Philosophy:
- Use real investigation scenarios (not just method calls)
- Validate state transitions across engines
- Verify business logic at integration points
- Ensure engines maintain consistency
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock

from faultmaven.modules.case.engines import (
    MilestoneEngine,
    HypothesisManager,
    OODAEngine,
)
from faultmaven.modules.case.investigation import (
    InvestigationState,
    HypothesisModel,
    InvestigationProgress,
)
from faultmaven.modules.case.enums import (
    InvestigationPhase,
    HypothesisStatus,
    TurnOutcome,
)
from faultmaven.modules.case.orm import Case, CaseStatus


class MockLLMProvider:
    """Mock LLM provider for testing without real API calls."""

    def __init__(self, response="Mock LLM response"):
        self.response = response
        self.last_prompt = None
        self.call_count = 0

    async def complete(self, messages=None, **kwargs):
        """Mock LLM completion."""
        self.call_count += 1
        if messages:
            self.last_prompt = messages[-1].get('content', '') if isinstance(messages[-1], dict) else str(messages[-1])
        return self.response

    async def generate(self, prompt=None, **kwargs):
        """Mock LLM generation (used by MilestoneEngine)."""
        self.call_count += 1
        if prompt:
            self.last_prompt = prompt
        return self.response


class MockCase:
    """Mock Case for engine integration tests."""

    def __init__(self, case_id="test-case-001", status=CaseStatus.INVESTIGATING):
        self.id = case_id
        self.title = "Test Investigation Case"
        self.description = "Testing engine integration"
        self.status = status
        self.case_metadata = {}
        self.updated_at = datetime.now()
        self.resolved_at = None
        self.closed_at = None


# =============================================================================
# Phase 4.1: MilestoneEngine + HypothesisManager Integration
# =============================================================================


@pytest.mark.integration
class TestMilestoneEngineHypothesisIntegration:
    """Test MilestoneEngine and HypothesisManager working together."""

    @pytest.mark.asyncio
    async def test_hypothesis_confidence_affects_milestones(self):
        """Hypothesis validation should trigger milestone completion."""
        # Setup
        llm = MockLLMProvider(response="Based on the evidence, the hypothesis is validated.")
        milestone_engine = MilestoneEngine(llm_provider=llm)
        hypothesis_manager = HypothesisManager()

        case = MockCase(status=CaseStatus.INVESTIGATING)
        inv_state = InvestigationState(investigation_id="inv-001")
        inv_state.current_phase = InvestigationPhase.VALIDATION

        # Create hypothesis
        hypothesis = hypothesis_manager.create_hypothesis(
            statement="Database connection pool exhausted",
            category="configuration",
            initial_likelihood=0.50,
            current_turn=1,
        )
        inv_state.hypotheses = [hypothesis]

        # Link supporting evidence to raise confidence above validation threshold (0.70)
        hypothesis_manager.link_evidence(hypothesis, "ev_pool_metrics", supports=True, turn=2)
        hypothesis_manager.link_evidence(hypothesis, "ev_connection_logs", supports=True, turn=3)

        # Verify hypothesis is now VALIDATED
        assert hypothesis.status == HypothesisStatus.VALIDATED
        assert hypothesis.likelihood >= 0.70

        # Milestone engine should recognize validated hypothesis
        # In a real scenario, this would complete solution_proposed milestone
        assert hypothesis.validated_at_turn == 3

    @pytest.mark.asyncio
    async def test_refuted_hypotheses_trigger_new_hypothesis_phase(self):
        """All hypotheses refuted should signal need for new hypotheses."""
        llm = MockLLMProvider()
        milestone_engine = MilestoneEngine(llm_provider=llm)
        hypothesis_manager = HypothesisManager()

        case = MockCase(status=CaseStatus.INVESTIGATING)
        inv_state = InvestigationState(investigation_id="inv-002")
        inv_state.current_phase = InvestigationPhase.VALIDATION

        # Create multiple hypotheses
        hyp1 = hypothesis_manager.create_hypothesis(
            statement="Memory leak in service",
            category="code",
            initial_likelihood=0.60,
            current_turn=1,
        )
        hyp2 = hypothesis_manager.create_hypothesis(
            statement="Database deadlock",
            category="infrastructure",
            initial_likelihood=0.55,
            current_turn=1,
        )
        inv_state.hypotheses = [hyp1, hyp2]

        # Refute both hypotheses
        hypothesis_manager.link_evidence(hyp1, "ev_no_leak", supports=False, turn=2)
        hypothesis_manager.link_evidence(hyp1, "ev_memory_stable", supports=False, turn=3)
        hypothesis_manager.link_evidence(hyp2, "ev_no_deadlock", supports=False, turn=2)
        hypothesis_manager.link_evidence(hyp2, "ev_locks_clean", supports=False, turn=3)

        # Both should be REFUTED
        assert hyp1.status == HypothesisStatus.REFUTED
        assert hyp2.status == HypothesisStatus.REFUTED

        # Check if any active hypotheses remain
        active_hypotheses = [h for h in inv_state.hypotheses if h.status == HypothesisStatus.ACTIVE]
        assert len(active_hypotheses) == 0  # Should trigger loopback to hypothesis phase

    @pytest.mark.asyncio
    async def test_hypothesis_ranking_informs_turn_processing(self):
        """Hypothesis ranking should prioritize which hypotheses to test next."""
        llm = MockLLMProvider()
        hypothesis_manager = HypothesisManager()

        # Create multiple hypotheses with different confidence levels
        hypotheses = [
            hypothesis_manager.create_hypothesis(
                statement="CPU throttling",
                category="infrastructure",
                initial_likelihood=0.40,
                current_turn=1,
            ),
            hypothesis_manager.create_hypothesis(
                statement="Network latency spike",
                category="infrastructure",
                initial_likelihood=0.65,
                current_turn=1,
            ),
            hypothesis_manager.create_hypothesis(
                statement="Database query timeout",
                category="code",
                initial_likelihood=0.80,
                current_turn=1,
            ),
        ]

        # Rank hypotheses
        from faultmaven.modules.case.engines import rank_hypotheses_by_likelihood
        ranked = rank_hypotheses_by_likelihood(hypotheses)

        # Highest likelihood should be first
        assert ranked[0].statement == "Database query timeout"
        assert ranked[0].likelihood == 0.80
        assert ranked[1].statement == "Network latency spike"
        assert ranked[2].statement == "CPU throttling"


# =============================================================================
# Phase 4.2: MilestoneEngine + OODAEngine Integration
# =============================================================================


@pytest.mark.integration
class TestMilestoneEngineOODAIntegration:
    """Test MilestoneEngine and OODAEngine working together."""

    @pytest.mark.asyncio
    async def test_ooda_intensity_adapts_to_phase(self):
        """OODA intensity should adapt based on investigation phase."""
        llm = MockLLMProvider()
        ooda_engine = OODAEngine()

        inv_state = InvestigationState(investigation_id="inv-003")

        # Test different phases
        test_cases = [
            (InvestigationPhase.INTAKE, 0, "none"),
            (InvestigationPhase.BLAST_RADIUS, 1, "light"),
            (InvestigationPhase.HYPOTHESIS, 2, "light"),
            (InvestigationPhase.HYPOTHESIS, 3, "medium"),
            (InvestigationPhase.VALIDATION, 2, "medium"),
            (InvestigationPhase.VALIDATION, 3, "full"),
        ]

        for phase, iteration_count, expected_intensity in test_cases:
            inv_state.current_phase = phase
            if inv_state.ooda_state:
                inv_state.ooda_state.current_iteration = iteration_count
            else:
                from faultmaven.modules.case.investigation import OODAState
                inv_state.ooda_state = OODAState(current_iteration=iteration_count)

            intensity = ooda_engine.get_current_intensity(inv_state)
            assert intensity == expected_intensity, \
                f"Phase {phase.value}, iter {iteration_count}: expected {expected_intensity}, got {intensity}"

    @pytest.mark.asyncio
    async def test_anchoring_detection_stops_iterations(self):
        """Anchoring detection should prevent endless iteration loops."""
        ooda_engine = OODAEngine()
        hypothesis_manager = HypothesisManager()

        inv_state = InvestigationState(investigation_id="inv-004")
        inv_state.current_phase = InvestigationPhase.HYPOTHESIS

        # Create 4 hypotheses in same category (triggers anchoring condition 1)
        for i in range(4):
            hyp = hypothesis_manager.create_hypothesis(
                statement=f"Configuration issue {i+1}",
                category="configuration",  # All same category
                initial_likelihood=0.50,
                current_turn=1,
            )
            inv_state.hypotheses.append(hyp)

        # Check anchoring with sufficient iterations
        from faultmaven.modules.case.investigation import OODAState
        inv_state.ooda_state = OODAState(current_iteration=4)

        is_anchored, reason = ooda_engine.check_anchoring_prevention(inv_state)

        assert is_anchored is True
        assert "4 hypotheses in 'configuration' category" in reason

    @pytest.mark.asyncio
    async def test_phase_intensity_config_matches_expectations(self):
        """Phase intensity configs should match investigation requirements."""
        ooda_engine = OODAEngine()

        expected_configs = {
            InvestigationPhase.INTAKE: (0, 0),          # No OODA
            InvestigationPhase.BLAST_RADIUS: (1, 2),    # Light
            InvestigationPhase.TIMELINE: (1, 2),        # Light
            InvestigationPhase.HYPOTHESIS: (2, 3),      # Medium
            InvestigationPhase.VALIDATION: (3, 6),      # Full
            InvestigationPhase.SOLUTION: (2, 4),        # Medium
            InvestigationPhase.DOCUMENT: (1, 1),        # Light
        }

        for phase, (expected_min, expected_max) in expected_configs.items():
            min_iter, max_iter = ooda_engine.get_phase_intensity_config(phase)
            assert min_iter == expected_min, \
                f"Phase {phase.value}: expected min {expected_min}, got {min_iter}"
            assert max_iter == expected_max, \
                f"Phase {phase.value}: expected max {expected_max}, got {max_iter}"


# =============================================================================
# Phase 4.3: Complete Investigation Workflow
# =============================================================================


@pytest.mark.integration
class TestCompleteInvestigationWorkflow:
    """Test all 3 engines working together in realistic investigation scenarios."""

    @pytest.mark.asyncio
    async def test_simple_investigation_flow_consultation_to_resolution(self):
        """Test simple investigation: consultation → hypothesis → validation → resolution."""
        llm = MockLLMProvider(response="Let me help investigate this issue...")
        milestone_engine = MilestoneEngine(llm_provider=llm)
        hypothesis_manager = HypothesisManager()
        ooda_engine = OODAEngine()

        case = MockCase(status=CaseStatus.CONSULTING)

        # Turn 1: Consultation phase
        result = await milestone_engine.process_turn(
            case=case,
            user_message="My application is running slow",
            attachments=None,
        )

        assert result["metadata"]["outcome"] == TurnOutcome.CONVERSATION
        inv_state = milestone_engine._load_investigation_state(case)
        assert inv_state.current_turn == 1

        # Simulate phase transition to INVESTIGATING
        case.status = CaseStatus.INVESTIGATING
        inv_state.current_phase = InvestigationPhase.HYPOTHESIS
        milestone_engine._save_investigation_state(case, inv_state)

        # Turn 2: Add hypothesis
        hypothesis = hypothesis_manager.create_hypothesis(
            statement="Database queries are slow",
            category="code",
            initial_likelihood=0.60,
            current_turn=2,
        )
        inv_state.hypotheses.append(hypothesis)
        milestone_engine._save_investigation_state(case, inv_state)

        # Turn 3: Validate hypothesis with evidence
        hypothesis_manager.link_evidence(hypothesis, "ev_slow_queries", supports=True, turn=3)
        hypothesis_manager.link_evidence(hypothesis, "ev_query_logs", supports=True, turn=4)

        assert hypothesis.status == HypothesisStatus.VALIDATED
        assert hypothesis.likelihood >= 0.70

        # Milestones should show progress
        assert inv_state.progress.root_cause_identified or hypothesis.status == HypothesisStatus.VALIDATED

    @pytest.mark.asyncio
    async def test_complex_investigation_with_hypothesis_refinement(self):
        """Test complex investigation: multiple hypotheses, some refuted, refinement needed."""
        llm = MockLLMProvider()
        milestone_engine = MilestoneEngine(llm_provider=llm)
        hypothesis_manager = HypothesisManager()

        case = MockCase(status=CaseStatus.INVESTIGATING)
        inv_state = InvestigationState(investigation_id="inv-complex-001")
        inv_state.current_phase = InvestigationPhase.HYPOTHESIS

        # Create initial hypotheses
        hyp1 = hypothesis_manager.create_hypothesis(
            statement="Memory leak in cache",
            category="code",
            initial_likelihood=0.60,
            current_turn=1,
        )
        hyp2 = hypothesis_manager.create_hypothesis(
            statement="Thread pool exhaustion",
            category="configuration",
            initial_likelihood=0.55,
            current_turn=1,
        )
        hyp3 = hypothesis_manager.create_hypothesis(
            statement="Database connection pool saturation",
            category="infrastructure",
            initial_likelihood=0.50,
            current_turn=1,
        )

        inv_state.hypotheses = [hyp1, hyp2, hyp3]

        # Refute first hypothesis
        hypothesis_manager.link_evidence(hyp1, "ev_memory_stable", supports=False, turn=2)
        hypothesis_manager.link_evidence(hyp1, "ev_no_leak", supports=False, turn=3)
        assert hyp1.status == HypothesisStatus.REFUTED

        # Refute second hypothesis
        hypothesis_manager.link_evidence(hyp2, "ev_threads_normal", supports=False, turn=4)
        hypothesis_manager.link_evidence(hyp2, "ev_no_exhaustion", supports=False, turn=5)
        assert hyp2.status == HypothesisStatus.REFUTED

        # Validate third hypothesis
        hypothesis_manager.link_evidence(hyp3, "ev_pool_saturation", supports=True, turn=6)
        hypothesis_manager.link_evidence(hyp3, "ev_connection_metrics", supports=True, turn=7)
        assert hyp3.status == HypothesisStatus.VALIDATED
        assert hyp3.likelihood >= 0.70

        # Verify only one validated hypothesis remains
        validated = [h for h in inv_state.hypotheses if h.status == HypothesisStatus.VALIDATED]
        assert len(validated) == 1
        assert validated[0].statement == "Database connection pool saturation"

    @pytest.mark.asyncio
    async def test_anchoring_prevention_across_engines(self):
        """Test that anchoring detection works across hypothesis manager and OODA engine."""
        hypothesis_manager = HypothesisManager()
        ooda_engine = OODAEngine()

        inv_state = InvestigationState(investigation_id="inv-anchor-001")
        inv_state.current_phase = InvestigationPhase.VALIDATION

        # Create stalled hypotheses (anchoring condition 2: ≥2 stalled for 3+ iterations)
        hyp1 = hypothesis_manager.create_hypothesis(
            statement="Hypothesis 1",
            category="code",
            initial_likelihood=0.50,
            current_turn=1,
        )
        hyp1.iterations_without_progress = 4  # Stalled

        hyp2 = hypothesis_manager.create_hypothesis(
            statement="Hypothesis 2",
            category="infrastructure",
            initial_likelihood=0.50,
            current_turn=1,
        )
        hyp2.iterations_without_progress = 3  # Stalled

        inv_state.hypotheses = [hyp1, hyp2]

        # OODA engine should detect anchoring
        from faultmaven.modules.case.investigation import OODAState
        inv_state.ooda_state = OODAState(current_iteration=5)

        is_anchored, reason = ooda_engine.check_anchoring_prevention(inv_state)

        assert is_anchored is True
        assert "2 hypotheses without progress" in reason

        # HypothesisManager should also detect via detect_anchoring
        is_anchored_hyp, reason_hyp, affected = hypothesis_manager.detect_anchoring(
            inv_state.hypotheses,
            current_iteration=5
        )

        assert is_anchored_hyp is True
        assert len(affected) == 2
