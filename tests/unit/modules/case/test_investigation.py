"""
Unit tests for investigation state models.

Tests the Pydantic models and their serialization without database dependencies.
"""

import pytest
from datetime import datetime

from faultmaven.modules.case.investigation import (
    InvestigationState,
    HypothesisModel,
    AnomalyFrame,
    TemporalFrame,
    ProgressMetrics,
    EscalationState,
    WorkingConclusion,
    EvidenceItem,
    TurnRecord,
)
from faultmaven.modules.case.enums import (
    InvestigationPhase,
    HypothesisStatus,
    ConfidenceLevel,
    DegradedModeType,
    EvidenceCategory,
    InvestigationMomentum,
)


class TestInvestigationState:
    """Test InvestigationState model."""

    def test_create_minimal_state(self):
        """Can create state with minimal fields."""
        state = InvestigationState(investigation_id="test-123")

        assert state.investigation_id == "test-123"
        assert state.current_phase == InvestigationPhase.INTAKE
        assert state.current_turn == 0
        assert state.hypotheses == []
        assert state.evidence == []

    def test_serialization_roundtrip(self):
        """State survives JSON serialization roundtrip."""
        state = InvestigationState(
            investigation_id="test-456",
            current_phase=InvestigationPhase.HYPOTHESIS,
            current_turn=5,
        )
        state.hypotheses.append(
            HypothesisModel(
                hypothesis_id="hyp-1",
                statement="Database connection pool exhausted",
                status=HypothesisStatus.ACTIVE,
            )
        )

        # Serialize and deserialize
        data = state.to_dict()
        restored = InvestigationState.from_dict(data)

        assert restored.investigation_id == "test-456"
        assert restored.current_phase == InvestigationPhase.HYPOTHESIS
        assert restored.current_turn == 5
        assert len(restored.hypotheses) == 1
        assert restored.hypotheses[0].statement == "Database connection pool exhausted"

    def test_get_active_hypotheses(self):
        """get_active_hypotheses returns only ACTIVE status."""
        state = InvestigationState(investigation_id="test")
        state.hypotheses = [
            HypothesisModel(
                hypothesis_id="1",
                statement="Active hypothesis",
                status=HypothesisStatus.ACTIVE,
            ),
            HypothesisModel(
                hypothesis_id="2",
                statement="Refuted hypothesis",
                status=HypothesisStatus.REFUTED,
            ),
            HypothesisModel(
                hypothesis_id="3",
                statement="Captured hypothesis",
                status=HypothesisStatus.CAPTURED,
            ),
        ]

        active = state.get_active_hypotheses()
        assert len(active) == 1
        assert active[0].hypothesis_id == "1"

    def test_get_validated_hypothesis(self):
        """get_validated_hypothesis returns VALIDATED hypothesis."""
        state = InvestigationState(investigation_id="test")
        state.hypotheses = [
            HypothesisModel(
                hypothesis_id="1",
                statement="Active hypothesis",
                status=HypothesisStatus.ACTIVE,
            ),
            HypothesisModel(
                hypothesis_id="2",
                statement="Root cause",
                status=HypothesisStatus.VALIDATED,
            ),
        ]

        validated = state.get_validated_hypothesis()
        assert validated is not None
        assert validated.hypothesis_id == "2"

    def test_get_validated_hypothesis_returns_none_if_no_validated(self):
        """get_validated_hypothesis returns None if none validated."""
        state = InvestigationState(investigation_id="test")
        state.hypotheses = [
            HypothesisModel(
                hypothesis_id="1",
                statement="Active hypothesis",
                status=HypothesisStatus.ACTIVE,
            ),
        ]

        assert state.get_validated_hypothesis() is None


class TestCheckDegradedMode:
    """Test degraded mode detection."""

    def test_no_progress_triggers_degraded(self):
        """3+ turns without progress triggers NO_PROGRESS degraded mode."""
        state = InvestigationState(investigation_id="test")
        state.progress.turns_without_progress = 3

        result = state.check_degraded_mode()
        assert result == DegradedModeType.NO_PROGRESS

    def test_two_turns_no_progress_not_degraded(self):
        """2 turns without progress is not yet degraded."""
        state = InvestigationState(investigation_id="test")
        state.progress.turns_without_progress = 2

        result = state.check_degraded_mode()
        assert result is None

    def test_hypothesis_exhausted_triggers_degraded(self):
        """All hypotheses refuted with none remaining triggers degraded."""
        state = InvestigationState(investigation_id="test")
        state.hypotheses = [
            HypothesisModel(
                hypothesis_id="1",
                statement="Refuted",
                status=HypothesisStatus.REFUTED,
            ),
            HypothesisModel(
                hypothesis_id="2",
                statement="Also refuted",
                status=HypothesisStatus.REFUTED,
            ),
        ]

        result = state.check_degraded_mode()
        assert result == DegradedModeType.HYPOTHESIS_SPACE_EXHAUSTED

    def test_critical_evidence_blocked_triggers_degraded(self):
        """3+ blocked evidence requests triggers degraded."""
        state = InvestigationState(investigation_id="test")
        state.progress.evidence_blocked_count = 3

        result = state.check_degraded_mode()
        assert result == DegradedModeType.CRITICAL_EVIDENCE_MISSING


class TestProgressMetrics:
    """Test ProgressMetrics model."""

    def test_completion_percentage_calculation(self):
        """Completion percentage calculated correctly."""
        progress = ProgressMetrics(
            completed_milestones=["symptom_verified", "scope_assessed"],
            pending_milestones=["timeline_established", "root_cause_identified"],
        )

        assert progress.completion_percentage == 50.0

    def test_completion_percentage_empty(self):
        """Completion percentage is 0 when no milestones."""
        progress = ProgressMetrics(
            completed_milestones=[],
            pending_milestones=[],
        )

        assert progress.completion_percentage == 0.0

    def test_completion_percentage_all_complete(self):
        """Completion percentage is 100 when all complete."""
        progress = ProgressMetrics(
            completed_milestones=["a", "b", "c"],
            pending_milestones=[],
        )

        assert progress.completion_percentage == 100.0

    def test_is_stalled_property(self):
        """is_stalled returns True after 3+ turns without progress."""
        progress = ProgressMetrics()

        progress.turns_without_progress = 2
        assert progress.is_stalled is False

        progress.turns_without_progress = 3
        assert progress.is_stalled is True


class TestHypothesisModel:
    """Test HypothesisModel."""

    def test_create_hypothesis(self):
        """Can create hypothesis with required fields."""
        hypothesis = HypothesisModel(
            hypothesis_id="h-123",
            statement="Connection pool exhausted",
        )

        assert hypothesis.hypothesis_id == "h-123"
        assert hypothesis.status == HypothesisStatus.CAPTURED
        assert hypothesis.likelihood == 0.5
        assert hypothesis.supporting_evidence == []

    def test_hypothesis_serialization(self):
        """Hypothesis serializes correctly."""
        hypothesis = HypothesisModel(
            hypothesis_id="h-456",
            statement="Memory leak in service",
            status=HypothesisStatus.ACTIVE,
            likelihood=0.75,
            supporting_evidence=["Evidence 1"],
        )

        data = hypothesis.model_dump(mode="json")

        assert data["hypothesis_id"] == "h-456"
        assert data["status"] == "active"
        assert data["likelihood"] == 0.75


class TestAnomalyFrame:
    """Test AnomalyFrame model."""

    def test_create_anomaly_frame(self):
        """Can create anomaly frame."""
        frame = AnomalyFrame(
            statement="API timeout on /checkout endpoint",
            affected_components=["api-gateway", "payment-service"],
            severity="high",
        )

        assert frame.statement == "API timeout on /checkout endpoint"
        assert len(frame.affected_components) == 2
        assert frame.confidence == 0.0  # Default


class TestEvidenceItem:
    """Test EvidenceItem model."""

    def test_create_evidence(self):
        """Can create evidence item."""
        evidence = EvidenceItem(
            evidence_id="e-123",
            description="Error logs showing connection refused",
            category=EvidenceCategory.SYMPTOM_EVIDENCE,
            source="Application logs",
        )

        assert evidence.evidence_id == "e-123"
        assert evidence.category == EvidenceCategory.SYMPTOM_EVIDENCE


class TestWorkingConclusion:
    """Test WorkingConclusion model."""

    def test_create_conclusion(self):
        """Can create working conclusion."""
        conclusion = WorkingConclusion(
            statement="Root cause is database connection limit",
            confidence=0.85,
            confidence_level=ConfidenceLevel.CONFIDENT,
            can_proceed_with_solution=True,
        )

        assert conclusion.statement == "Root cause is database connection limit"
        assert conclusion.can_proceed_with_solution is True


class TestTurnRecord:
    """Test TurnRecord model."""

    def test_create_turn_record(self):
        """Can create turn record."""
        record = TurnRecord(
            turn_number=5,
            phase=InvestigationPhase.HYPOTHESIS,
            user_input_summary="Provided error logs",
            agent_action_summary="Identified potential root cause",
            milestones_completed=["root_cause_identified"],
        )

        assert record.turn_number == 5
        assert record.phase == InvestigationPhase.HYPOTHESIS
        assert len(record.milestones_completed) == 1
