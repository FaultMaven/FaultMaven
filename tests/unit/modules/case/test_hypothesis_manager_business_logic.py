"""
Business logic tests for HypothesisManager.

These tests validate ACTUAL ALGORITHMS and BUSINESS RULES, not just existence checks.

Tested Algorithms:
1. Evidence-ratio confidence calculation: initial + (0.15 × supporting) - (0.20 × refuting)
2. Confidence decay: base × 0.85^iterations_without_progress
3. Auto-transition rules: VALIDATED (≥0.70, ≥2), REFUTED (≤0.20, ≥2), RETIRED (<0.30)
4. Anchoring detection: 3 conditions
5. Progress tracking: 5% threshold for progress detection

Source: FaultMaven-Mono hypothesis_manager.py
"""

import pytest
from datetime import datetime

from faultmaven.modules.case.engines import HypothesisManager, rank_hypotheses_by_likelihood
from faultmaven.modules.case.investigation import HypothesisModel
from faultmaven.modules.case.enums import HypothesisStatus, HypothesisGenerationMode


class TestEvidenceRatioConfidenceCalculation:
    """Validate evidence-ratio confidence formula.

    Formula: initial + (0.15 × supporting) - (0.20 × refuting)
    Source: FaultMaven-Mono lines 160-216
    """

    def test_confidence_increases_with_supporting_evidence(self):
        """Supporting evidence adds 0.15 per item"""
        manager = HypothesisManager()
        hypothesis = manager.create_hypothesis(
            statement="Database connection pool exhausted",
            category="infrastructure",
            initial_likelihood=0.50,
            current_turn=1,
        )

        # Link 2 supporting evidence items
        manager.link_evidence(hypothesis, "ev_001", supports=True, turn=2)
        manager.link_evidence(hypothesis, "ev_002", supports=True, turn=3)

        # Expected: 0.50 + (2 × 0.15) = 0.80
        assert hypothesis.likelihood == 0.80
        assert len(hypothesis.supporting_evidence) == 2

    def test_confidence_decreases_with_refuting_evidence(self):
        """Refuting evidence subtracts 0.20 per item"""
        manager = HypothesisManager()
        hypothesis = manager.create_hypothesis(
            statement="Memory leak in cache module",
            category="code",
            initial_likelihood=0.60,
            current_turn=1,
        )

        # Link 2 refuting evidence items
        manager.link_evidence(hypothesis, "ev_003", supports=False, turn=2)
        manager.link_evidence(hypothesis, "ev_004", supports=False, turn=3)

        # Expected: 0.60 - (2 × 0.20) = 0.20 (with floating point tolerance)
        assert abs(hypothesis.likelihood - 0.20) < 0.001
        assert len(hypothesis.refuting_evidence) == 2

    def test_confidence_clamped_to_valid_range(self):
        """Confidence cannot go below 0.0 or above 1.0"""
        manager = HypothesisManager()
        hypothesis = manager.create_hypothesis(
            statement="DNS resolution failing",
            category="infrastructure",
            initial_likelihood=0.30,
            current_turn=1,
        )

        # Add many refuting evidence (should clamp to 0.0)
        for i in range(5):
            manager.link_evidence(hypothesis, f"ev_refute_{i}", supports=False, turn=i+2)

        # Expected: 0.30 - (5 × 0.20) = -0.70 → clamped to 0.0
        assert hypothesis.likelihood == 0.0

        # Test upper bound
        hypothesis2 = manager.create_hypothesis(
            statement="Config file corrupted",
            category="configuration",
            initial_likelihood=0.80,
            current_turn=10,
        )

        # Add many supporting evidence (should clamp to 1.0)
        for i in range(5):
            manager.link_evidence(hypothesis2, f"ev_support_{i}", supports=True, turn=10+i)

        # Expected: 0.80 + (5 × 0.15) = 1.55 → clamped to 1.0
        assert hypothesis2.likelihood == 1.0

    def test_mixed_evidence_calculates_correctly(self):
        """Supporting and refuting evidence both affect confidence"""
        manager = HypothesisManager()
        hypothesis = manager.create_hypothesis(
            statement="API rate limiting misconfigured",
            category="configuration",
            initial_likelihood=0.50,
            current_turn=1,
        )

        # Add 3 supporting, 1 refuting
        manager.link_evidence(hypothesis, "ev_s1", supports=True, turn=2)
        manager.link_evidence(hypothesis, "ev_s2", supports=True, turn=3)
        manager.link_evidence(hypothesis, "ev_s3", supports=True, turn=4)
        manager.link_evidence(hypothesis, "ev_r1", supports=False, turn=5)

        # Expected: 0.50 + (3 × 0.15) - (1 × 0.20) = 0.75
        assert hypothesis.likelihood == 0.75


class TestConfidenceDecayAlgorithm:
    """Validate confidence decay for stagnant hypotheses.

    Formula: base × 0.85^iterations_without_progress
    Applied when: iterations_without_progress >= 2
    Source: FaultMaven-Mono lines 314-347
    """

    def test_no_decay_when_iterations_less_than_2(self):
        """No decay applied if iterations_without_progress < 2"""
        manager = HypothesisManager()
        hypothesis = manager.create_hypothesis(
            statement="Hypothesis with recent progress",
            category="code",
            initial_likelihood=0.60,
            current_turn=1,
        )
        hypothesis.iterations_without_progress = 1

        manager.apply_confidence_decay(hypothesis, current_turn=5)

        # No decay should occur
        assert hypothesis.likelihood == 0.60

    def test_decay_at_exactly_2_iterations(self):
        """Decay applied at exactly 2 iterations without progress"""
        manager = HypothesisManager()
        hypothesis = manager.create_hypothesis(
            statement="Stagnant hypothesis",
            category="infrastructure",
            initial_likelihood=0.60,
            current_turn=1,
        )
        hypothesis.iterations_without_progress = 2

        manager.apply_confidence_decay(hypothesis, current_turn=5)

        # Expected: 0.60 × 0.85^2 = 0.60 × 0.7225 = 0.4335
        assert abs(hypothesis.likelihood - 0.4335) < 0.001

    def test_decay_increases_exponentially(self):
        """Decay gets stronger with more iterations"""
        manager = HypothesisManager()
        hypothesis = manager.create_hypothesis(
            statement="Very stagnant hypothesis",
            category="code",
            initial_likelihood=0.80,
            current_turn=1,
        )

        # Simulate 5 iterations without progress
        hypothesis.iterations_without_progress = 5
        manager.apply_confidence_decay(hypothesis, current_turn=10)

        # Expected: 0.80 × 0.85^5 = 0.80 × 0.4437 = 0.3550
        assert abs(hypothesis.likelihood - 0.3550) < 0.001

    def test_decay_updates_confidence_trajectory(self):
        """Decay is recorded in confidence trajectory"""
        manager = HypothesisManager()
        hypothesis = manager.create_hypothesis(
            statement="Hypothesis with trajectory",
            category="configuration",
            initial_likelihood=0.70,
            current_turn=1,
        )
        hypothesis.iterations_without_progress = 3

        manager.apply_confidence_decay(hypothesis, current_turn=8)

        # Should have 2 entries: initial (turn 1) + decay (turn 8)
        assert len(hypothesis.confidence_trajectory) == 2
        assert hypothesis.confidence_trajectory[0] == (1, 0.70)
        assert hypothesis.confidence_trajectory[1][0] == 8
        assert abs(hypothesis.confidence_trajectory[1][1] - (0.70 * 0.85**3)) < 0.001


class TestAutoTransitionLogic:
    """Validate automatic status transitions.

    Rules:
    - VALIDATED: confidence ≥ 0.70 AND supporting_count ≥ 2
    - REFUTED: confidence ≤ 0.20 AND refuting_count ≥ 2
    - RETIRED: confidence < 0.30

    Source: FaultMaven-Mono lines 261-313
    """

    def test_validated_requires_both_conditions(self):
        """VALIDATED requires BOTH high confidence AND enough evidence"""
        manager = HypothesisManager()

        # Case 1: High confidence but only 1 supporting evidence (NOT validated)
        # Create hypothesis and manually set values WITHOUT using link_evidence
        hyp1 = manager.create_hypothesis(
            statement="High confidence, insufficient evidence",
            category="code",
            initial_likelihood=0.50,
            current_turn=1,
        )
        hyp1.likelihood = 0.75  # Above 0.70 threshold
        hyp1.supporting_evidence = ["ev_s1"]  # Only 1 (insufficient)
        manager._check_status_transition(hyp1, turn=4)

        assert hyp1.status == HypothesisStatus.ACTIVE  # NOT validated (need ≥2 evidence)

        # Case 2: Enough evidence but low confidence (NOT validated)
        hyp2 = manager.create_hypothesis(
            statement="Sufficient evidence, low confidence",
            category="infrastructure",
            initial_likelihood=0.60,
            current_turn=10,
        )
        hyp2.likelihood = 0.65  # Below 0.70 threshold
        hyp2.supporting_evidence = ["ev_1", "ev_2"]  # Exactly 2
        manager._check_status_transition(hyp2, turn=11)

        assert hyp2.status == HypothesisStatus.ACTIVE  # NOT validated (confidence < 0.70)

        # Case 3: BOTH conditions met (VALIDATED)
        hyp3 = manager.create_hypothesis(
            statement="Meets both validation conditions",
            category="configuration",
            initial_likelihood=0.50,
            current_turn=20,
        )
        manager.link_evidence(hyp3, "ev_a", supports=True, turn=21)  # 0.50 + 0.15 = 0.65
        manager.link_evidence(hyp3, "ev_b", supports=True, turn=22)  # 0.65 + 0.15 = 0.80 → VALIDATED!
        manager.link_evidence(hyp3, "ev_c", supports=True, turn=23)  # 0.80 + 0.15 = 0.95

        assert hyp3.status == HypothesisStatus.VALIDATED  # Meets both conditions
        assert hyp3.validated_at_turn == 22  # Validated after 2nd evidence (≥0.70 + ≥2)

    def test_refuted_requires_both_conditions(self):
        """REFUTED requires BOTH low confidence AND enough refuting evidence"""
        manager = HypothesisManager()

        # Case 1: Low confidence (≤0.20) but only 1 refuting evidence
        # Note: With confidence ≤0.20 and <2 evidence, goes to RETIRED instead
        hyp1 = manager.create_hypothesis(
            statement="Low confidence, insufficient refuting",
            category="code",
            initial_likelihood=0.40,
            current_turn=1,
        )
        hyp1.likelihood = 0.15  # Below REFUTED threshold
        hyp1.refuting_evidence = ["ev_r1"]  # Only 1 (insufficient)
        manager._check_status_transition(hyp1, turn=2)

        # Expected: RETIRED (not REFUTED, because need ≥2 evidence for REFUTED)
        assert hyp1.status == HypothesisStatus.RETIRED

        # Case 2: BOTH conditions met (REFUTED takes precedence over RETIRED)
        hyp2 = manager.create_hypothesis(
            statement="Meets both refutation conditions",
            category="infrastructure",
            initial_likelihood=0.50,
            current_turn=10,
        )
        manager.link_evidence(hyp2, "ev_r1", supports=False, turn=11)
        manager.link_evidence(hyp2, "ev_r2", supports=False, turn=12)  # 0.50 - 0.40 = 0.10

        # Expected: REFUTED (has both ≤0.20 AND ≥2 evidence)
        assert hyp2.status == HypothesisStatus.REFUTED
        assert hyp2.validated_at_turn == 12

    def test_retired_at_low_confidence_threshold(self):
        """RETIRED when confidence < 0.30"""
        manager = HypothesisManager()
        hypothesis = manager.create_hypothesis(
            statement="Low confidence hypothesis",
            category="code",
            initial_likelihood=0.50,
            current_turn=1,
        )

        # Reduce confidence to 0.29 (just below threshold)
        hypothesis.likelihood = 0.29
        manager._check_status_transition(hypothesis, turn=5)

        assert hypothesis.status == HypothesisStatus.RETIRED

    def test_only_active_hypotheses_auto_transition(self):
        """Only ACTIVE hypotheses can auto-transition"""
        manager = HypothesisManager()
        hypothesis = manager.create_hypothesis(
            statement="Captured hypothesis",
            category="infrastructure",
            initial_likelihood=0.50,
            current_turn=1,
            status=HypothesisStatus.CAPTURED,
        )

        # Meet validation criteria but status is CAPTURED
        hypothesis.likelihood = 0.80
        hypothesis.supporting_evidence = ["ev_1", "ev_2"]
        manager._check_status_transition(hypothesis, turn=5)

        # Should remain CAPTURED (not auto-transitioned)
        assert hypothesis.status == HypothesisStatus.CAPTURED


class TestProgressTracking:
    """Validate progress detection (5% threshold).

    Rule: Confidence change >= 0.05 counts as progress
    Source: FaultMaven-Mono lines 199-203, 242-254
    """

    def test_progress_resets_iterations_without_progress(self):
        """Progress (≥5% change) resets iterations_without_progress to 0"""
        manager = HypothesisManager()
        hypothesis = manager.create_hypothesis(
            statement="Hypothesis with progress",
            category="code",
            initial_likelihood=0.50,
            current_turn=1,
        )
        hypothesis.iterations_without_progress = 5  # Manually set high value

        # Add supporting evidence (0.50 → 0.65, change = 0.15 > 0.05)
        manager.link_evidence(hypothesis, "ev_001", supports=True, turn=2)

        assert hypothesis.iterations_without_progress == 0  # Reset
        assert hypothesis.last_progress_at_turn == 2

    def test_no_progress_increments_counter(self):
        """Small change (<5%) increments iterations_without_progress"""
        manager = HypothesisManager()
        hypothesis = manager.create_hypothesis(
            statement="Hypothesis with minimal change",
            category="infrastructure",
            initial_likelihood=0.50,
            current_turn=1,
        )
        hypothesis.iterations_without_progress = 2

        # Manually update with tiny change (< 5%)
        manager.update_hypothesis_confidence(
            hypothesis,
            new_likelihood=0.52,  # Change = 0.02 < 0.05
            current_turn=5,
            reason="Minimal update",
        )

        assert hypothesis.iterations_without_progress == 3  # Incremented

    def test_exactly_5_percent_counts_as_progress(self):
        """Exactly 5% change counts as progress"""
        manager = HypothesisManager()
        hypothesis = manager.create_hypothesis(
            statement="Hypothesis at boundary",
            category="configuration",
            initial_likelihood=0.50,
            current_turn=1,
        )
        hypothesis.iterations_without_progress = 3

        # Update with exactly 5% change
        manager.update_hypothesis_confidence(
            hypothesis,
            new_likelihood=0.55,  # Change = 0.05 (exactly threshold)
            current_turn=10,
            reason="Boundary test",
        )

        assert hypothesis.iterations_without_progress == 0  # Reset (≥ 0.05)


class TestAnchoringDetection:
    """Validate anchoring bias detection.

    Conditions:
    1. 4+ hypotheses in same category
    2. 2+ hypotheses with 3+ iterations without progress
    3. Top hypothesis stagnant for 3+ iterations with <70% confidence

    Source: FaultMaven-Mono lines 441-513
    """

    def test_anchoring_detected_by_category_clustering(self):
        """Condition 1: 4+ hypotheses in same category"""
        manager = HypothesisManager()
        hypotheses = []

        # Create 4 hypotheses in "infrastructure" category
        for i in range(4):
            hyp = manager.create_hypothesis(
                statement=f"Infrastructure hypothesis {i+1}",
                category="infrastructure",
                initial_likelihood=0.50,
                current_turn=1,
            )
            hypotheses.append(hyp)

        is_anchored, reason, affected = manager.detect_anchoring(hypotheses, current_iteration=5)

        assert is_anchored is True
        assert "4 hypotheses in 'infrastructure' category" in reason
        assert len(affected) == 4

    def test_no_anchoring_with_3_in_same_category(self):
        """Not anchored with only 3 hypotheses in same category"""
        manager = HypothesisManager()
        hypotheses = []

        # Create only 3 hypotheses in same category
        for i in range(3):
            hyp = manager.create_hypothesis(
                statement=f"Code hypothesis {i+1}",
                category="code",
                initial_likelihood=0.50,
                current_turn=1,
            )
            hypotheses.append(hyp)

        is_anchored, reason, affected = manager.detect_anchoring(hypotheses, current_iteration=5)

        assert is_anchored is False

    def test_anchoring_detected_by_multiple_stalled(self):
        """Condition 2: 2+ hypotheses with 3+ iterations without progress"""
        manager = HypothesisManager()
        hypotheses = []

        # Create 2 stalled hypotheses
        for i in range(2):
            hyp = manager.create_hypothesis(
                statement=f"Stalled hypothesis {i+1}",
                category=f"category_{i}",  # Different categories
                initial_likelihood=0.50,
                current_turn=1,
            )
            hyp.iterations_without_progress = 3  # Exactly threshold
            hypotheses.append(hyp)

        is_anchored, reason, affected = manager.detect_anchoring(hypotheses, current_iteration=5)

        assert is_anchored is True
        assert "2 hypotheses without progress for 3+ iterations" in reason
        assert len(affected) == 2

    def test_no_anchoring_with_only_one_stalled(self):
        """Not anchored with only 1 stalled hypothesis if confidence is high"""
        manager = HypothesisManager()
        hypotheses = []

        # Create only 1 stalled hypothesis with HIGH confidence (exempts from condition 3)
        hyp = manager.create_hypothesis(
            statement="Single stalled hypothesis with high confidence",
            category="code",
            initial_likelihood=0.75,  # Above 70% threshold
            current_turn=1,
        )
        hyp.iterations_without_progress = 5
        hypotheses.append(hyp)

        is_anchored, reason, affected = manager.detect_anchoring(hypotheses, current_iteration=5)

        assert is_anchored is False  # High confidence exempts from condition 3

    def test_anchoring_detected_by_stagnant_top_hypothesis(self):
        """Condition 3: Top hypothesis stagnant 3+ iterations with <70% confidence"""
        manager = HypothesisManager()
        hypotheses = []

        # Create top hypothesis (highest likelihood)
        top_hyp = manager.create_hypothesis(
            statement="Stagnant top hypothesis",
            category="infrastructure",
            initial_likelihood=0.65,  # Below 70%
            current_turn=1,
        )
        top_hyp.iterations_without_progress = 3  # Exactly threshold
        hypotheses.append(top_hyp)

        # Create lower confidence hypothesis
        low_hyp = manager.create_hypothesis(
            statement="Lower hypothesis",
            category="code",
            initial_likelihood=0.30,
            current_turn=1,
        )
        hypotheses.append(low_hyp)

        is_anchored, reason, affected = manager.detect_anchoring(hypotheses, current_iteration=5)

        assert is_anchored is True
        assert "Top hypothesis stagnant" in reason
        assert "65%" in reason or "0.65" in reason  # Check confidence mentioned
        assert len(affected) == 1

    def test_no_anchoring_when_top_hypothesis_high_confidence(self):
        """Not anchored if top hypothesis has ≥70% confidence"""
        manager = HypothesisManager()
        hypotheses = []

        # Top hypothesis with high confidence
        top_hyp = manager.create_hypothesis(
            statement="High confidence top",
            category="code",
            initial_likelihood=0.75,  # Above 70%
            current_turn=1,
        )
        top_hyp.iterations_without_progress = 5  # High stagnation
        hypotheses.append(top_hyp)

        is_anchored, reason, affected = manager.detect_anchoring(hypotheses, current_iteration=5)

        assert is_anchored is False  # High confidence exempts from anchoring


class TestForceAlternativeGeneration:
    """Validate anchoring prevention actions.

    Actions:
    - Identify dominant category
    - Retire low-progress hypotheses in dominant category
    - Return constraints for alternative generation

    Source: FaultMaven-Mono lines 515-571
    """

    def test_retires_low_progress_hypotheses_in_dominant_category(self):
        """Retires hypotheses with ≥2 iterations_without_progress in dominant category"""
        manager = HypothesisManager()
        hypotheses = []

        # Create 4 hypotheses in "infrastructure" (dominant)
        for i in range(4):
            hyp = manager.create_hypothesis(
                statement=f"Infrastructure hyp {i+1}",
                category="infrastructure",
                initial_likelihood=0.50,
                current_turn=1,
            )
            hyp.iterations_without_progress = 2 if i < 3 else 1  # 3 eligible for retirement
            hypotheses.append(hyp)

        # Create 1 hypothesis in "code"
        code_hyp = manager.create_hypothesis(
            statement="Code hypothesis",
            category="code",
            initial_likelihood=0.50,
            current_turn=1,
        )
        hypotheses.append(code_hyp)

        result = manager.force_alternative_generation(hypotheses, current_turn=10)

        # Check that 3 infrastructure hypotheses were retired
        retired_count = sum(1 for h in hypotheses if h.status == HypothesisStatus.RETIRED)
        assert retired_count == 3
        assert result["retired_count"] == 3
        assert result["dominant_category"] == "infrastructure"

    def test_returns_constraints_for_alternative_generation(self):
        """Returns constraints excluding dominant category"""
        manager = HypothesisManager()
        hypotheses = []

        # Create dominant category
        for i in range(3):
            hyp = manager.create_hypothesis(
                statement=f"Config hypothesis {i+1}",
                category="configuration",
                initial_likelihood=0.50,
                current_turn=1,
            )
            hyp.iterations_without_progress = 3
            hypotheses.append(hyp)

        result = manager.force_alternative_generation(hypotheses, current_turn=5)

        assert result["action"] == "force_alternative_generation"
        assert result["dominant_category"] == "configuration"
        assert "configuration" in result["constraints"]["exclude_categories"]
        assert result["constraints"]["require_diverse_categories"] is True
        assert result["constraints"]["min_new_hypotheses"] == 2


class TestHypothesisHelperMethods:
    """Validate helper and query methods."""

    def test_get_testable_hypotheses_returns_active_only(self):
        """Only ACTIVE hypotheses with likelihood > 0.2 are testable"""
        manager = HypothesisManager()
        hypotheses = []

        # Create ACTIVE hypothesis (testable)
        active_high = manager.create_hypothesis(
            statement="Active high confidence",
            category="code",
            initial_likelihood=0.70,
            current_turn=1,
        )
        hypotheses.append(active_high)

        # Create ACTIVE but low confidence (not testable)
        active_low = manager.create_hypothesis(
            statement="Active low confidence",
            category="infrastructure",
            initial_likelihood=0.15,  # Below 0.2
            current_turn=1,
        )
        hypotheses.append(active_low)

        # Create VALIDATED (not testable)
        validated = manager.create_hypothesis(
            statement="Already validated",
            category="configuration",
            initial_likelihood=0.80,
            current_turn=1,
        )
        validated.status = HypothesisStatus.VALIDATED
        hypotheses.append(validated)

        testable = manager.get_testable_hypotheses(hypotheses, max_count=10)

        assert len(testable) == 1
        assert testable[0].hypothesis_id == active_high.hypothesis_id

    def test_get_validated_hypothesis_returns_highest_confidence(self):
        """Returns validated hypothesis with highest confidence"""
        manager = HypothesisManager()
        hypotheses = []

        # Create 2 validated hypotheses
        val1 = manager.create_hypothesis(
            statement="Validated hypothesis 1",
            category="code",
            initial_likelihood=0.75,
            current_turn=1,
        )
        val1.status = HypothesisStatus.VALIDATED
        hypotheses.append(val1)

        val2 = manager.create_hypothesis(
            statement="Validated hypothesis 2",
            category="infrastructure",
            initial_likelihood=0.90,  # Higher confidence
            current_turn=1,
        )
        val2.status = HypothesisStatus.VALIDATED
        hypotheses.append(val2)

        result = manager.get_validated_hypothesis(hypotheses)

        assert result.hypothesis_id == val2.hypothesis_id
        assert result.likelihood == 0.90

    def test_rank_hypotheses_by_likelihood(self):
        """Hypotheses sorted by likelihood descending"""
        manager = HypothesisManager()
        hypotheses = []

        # Create hypotheses with different likelihoods
        for likelihood in [0.30, 0.80, 0.50, 0.90]:
            hyp = manager.create_hypothesis(
                statement=f"Hypothesis {likelihood}",
                category="code",
                initial_likelihood=likelihood,
                current_turn=1,
            )
            hypotheses.append(hyp)

        ranked = rank_hypotheses_by_likelihood(hypotheses)

        assert ranked[0].likelihood == 0.90
        assert ranked[1].likelihood == 0.80
        assert ranked[2].likelihood == 0.50
        assert ranked[3].likelihood == 0.30


class TestFullWorkflow:
    """Integration test: complete hypothesis lifecycle"""

    def test_complete_hypothesis_validation_workflow(self):
        """Simulate complete workflow from creation to validation"""
        manager = HypothesisManager()

        # Turn 1: Create hypothesis
        hypothesis = manager.create_hypothesis(
            statement="API gateway timeout misconfigured",
            category="configuration",
            initial_likelihood=0.50,
            current_turn=1,
        )

        assert hypothesis.status == HypothesisStatus.ACTIVE
        assert hypothesis.likelihood == 0.50

        # Turn 2: Add supporting evidence
        manager.link_evidence(hypothesis, "ev_timeout_logs", supports=True, turn=2)
        assert hypothesis.likelihood == 0.65  # 0.50 + 0.15

        # Turn 3: Add more supporting evidence
        manager.link_evidence(hypothesis, "ev_config_diff", supports=True, turn=3)
        assert hypothesis.likelihood == 0.80  # 0.65 + 0.15

        # Should auto-transition to VALIDATED (≥0.70 + ≥2 supporting)
        assert hypothesis.status == HypothesisStatus.VALIDATED
        assert hypothesis.validated_at_turn == 3
        assert len(hypothesis.supporting_evidence) == 2

    def test_complete_hypothesis_refutation_workflow(self):
        """Simulate complete workflow from creation to refutation"""
        manager = HypothesisManager()

        # Turn 1: Create hypothesis
        hypothesis = manager.create_hypothesis(
            statement="Memory leak in worker process",
            category="code",
            initial_likelihood=0.50,
            current_turn=1,
        )

        # Turn 2-3: Add refuting evidence
        manager.link_evidence(hypothesis, "ev_memory_stable", supports=False, turn=2)
        assert hypothesis.likelihood == 0.30  # 0.50 - 0.20

        manager.link_evidence(hypothesis, "ev_no_leak_pattern", supports=False, turn=3)
        # Expected: 0.30 - 0.20 = 0.10 (with floating point tolerance)
        assert abs(hypothesis.likelihood - 0.10) < 0.001

        # Should auto-transition to REFUTED (≤0.20 + ≥2 refuting)
        assert hypothesis.status == HypothesisStatus.REFUTED
        assert hypothesis.validated_at_turn == 3
        assert len(hypothesis.refuting_evidence) == 2
