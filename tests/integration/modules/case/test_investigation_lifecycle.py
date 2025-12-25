"""
Integration tests for investigation lifecycle.

Tests the full investigation workflow from initialization through completion.
"""

import pytest
from datetime import datetime

from faultmaven.modules.case.orm import Case, CaseStatus
from faultmaven.modules.case.service import CaseService
from faultmaven.modules.case.investigation_service import InvestigationService
from faultmaven.modules.case.enums import (
    InvestigationPhase,
    HypothesisStatus,
    TemporalState,
    UrgencyLevel,
    InvestigationStrategy,
)


@pytest.mark.integration
class TestInvestigationInitialization:
    """Test investigation initialization."""

    async def test_initialize_investigation_for_new_case(
        self,
        db_session,
        mock_case_service,
    ):
        """Initialize investigation state when transitioning to INVESTIGATING."""
        # Create a case
        case = Case(
            id="case-123",
            owner_id="user-456",
            title="Database connection timeout",
            description="Users cannot connect to database",
            status=CaseStatus.CONSULTING,
        )
        db_session.add(case)
        await db_session.commit()

        # Create investigation service
        case_service = CaseService(db_session=db_session)
        investigation_service = InvestigationService(case_service=case_service)

        # Initialize investigation
        state, error = await investigation_service.initialize_investigation(
            case_id="case-123",
            user_id="user-456",
            problem_statement="Database connection timeout",
            temporal_state=TemporalState.ONGOING,
            urgency_level=UrgencyLevel.CRITICAL,
        )

        # Verify initialization
        assert error is None
        assert state is not None
        assert state.current_phase == InvestigationPhase.INTAKE
        assert state.current_turn == 0
        assert state.temporal_state == TemporalState.ONGOING
        assert state.urgency_level == UrgencyLevel.CRITICAL
        assert state.strategy == InvestigationStrategy.MITIGATION_FIRST
        assert state.anomaly_frame.statement == "Database connection timeout"

        # Verify stored in case metadata
        await db_session.refresh(case)
        assert "investigation" in case.case_metadata
        assert case.case_metadata["investigation"]["investigation_id"] == state.investigation_id

    async def test_cannot_initialize_twice(self, db_session):
        """Cannot initialize investigation if already exists."""
        # Create case with existing investigation
        case = Case(
            id="case-789",
            owner_id="user-456",
            title="Test case",
            status=CaseStatus.INVESTIGATING,
            case_metadata={
                "investigation": {
                    "investigation_id": "inv-existing",
                    "current_phase": 0,
                    "current_turn": 0,
                }
            },
        )
        db_session.add(case)
        await db_session.commit()

        case_service = CaseService(db_session=db_session)
        investigation_service = InvestigationService(case_service=case_service)

        # Try to initialize again
        state, error = await investigation_service.initialize_investigation(
            case_id="case-789",
            user_id="user-456",
        )

        assert state is None
        assert error == "Investigation already initialized"

    async def test_strategy_determination_matrix(self, db_session):
        """Test investigation strategy determination based on temporal state and urgency."""
        case_service = CaseService(db_session=db_session)
        investigation_service = InvestigationService(case_service=case_service)

        # Test matrix: ONGOING + CRITICAL → MITIGATION_FIRST
        assert investigation_service._determine_strategy(
            TemporalState.ONGOING, UrgencyLevel.CRITICAL
        ) == InvestigationStrategy.MITIGATION_FIRST

        # Test matrix: ONGOING + HIGH → MITIGATION_FIRST
        assert investigation_service._determine_strategy(
            TemporalState.ONGOING, UrgencyLevel.HIGH
        ) == InvestigationStrategy.MITIGATION_FIRST

        # Test matrix: HISTORICAL + LOW → ROOT_CAUSE
        assert investigation_service._determine_strategy(
            TemporalState.HISTORICAL, UrgencyLevel.LOW
        ) == InvestigationStrategy.ROOT_CAUSE

        # Test matrix: HISTORICAL + MEDIUM → ROOT_CAUSE
        assert investigation_service._determine_strategy(
            TemporalState.HISTORICAL, UrgencyLevel.MEDIUM
        ) == InvestigationStrategy.ROOT_CAUSE

        # Test matrix: Ambiguous cases → USER_CHOICE
        assert investigation_service._determine_strategy(
            TemporalState.ONGOING, UrgencyLevel.LOW
        ) == InvestigationStrategy.USER_CHOICE


@pytest.mark.integration
class TestInvestigationAdvancement:
    """Test turn advancement and progress tracking."""

    async def test_advance_turn_increments_counter(self, db_session):
        """Advancing turn increments turn counter and records history."""
        # Setup case with investigation
        case = Case(
            id="case-adv-1",
            owner_id="user-456",
            title="Test advancement",
            status=CaseStatus.INVESTIGATING,
        )
        db_session.add(case)
        await db_session.commit()

        case_service = CaseService(db_session=db_session)
        investigation_service = InvestigationService(case_service=case_service)

        # Initialize
        await investigation_service.initialize_investigation(
            case_id="case-adv-1",
            user_id="user-456",
        )

        # Advance turn
        state, error = await investigation_service.advance_turn(
            case_id="case-adv-1",
            user_id="user-456",
            user_input_summary="Checked logs, found connection pool exhaustion",
            agent_action_summary="Identified pattern in error messages",
            milestones_completed=["blast_radius"],
        )

        assert error is None
        assert state.current_turn == 1
        assert len(state.turn_history) == 1
        assert state.turn_history[0].turn_number == 1
        assert "connection pool exhaustion" in state.turn_history[0].user_input_summary

    async def test_phase_transition_during_advancement(self, db_session):
        """Phase can transition during turn advancement."""
        case = Case(
            id="case-phase-1",
            owner_id="user-456",
            title="Test phase transition",
            status=CaseStatus.INVESTIGATING,
        )
        db_session.add(case)
        await db_session.commit()

        case_service = CaseService(db_session=db_session)
        investigation_service = InvestigationService(case_service=case_service)

        # Initialize in INTAKE phase
        await investigation_service.initialize_investigation(
            case_id="case-phase-1",
            user_id="user-456",
        )

        # Advance with phase transition
        state, error = await investigation_service.advance_turn(
            case_id="case-phase-1",
            user_id="user-456",
            user_input_summary="Gathered all initial information",
            phase_transition=InvestigationPhase.BLAST_RADIUS,
        )

        assert error is None
        assert state.current_phase == InvestigationPhase.BLAST_RADIUS
        assert len(state.phase_transitions) == 1
        assert state.phase_transitions[0]["from_phase"] == InvestigationPhase.INTAKE.value
        assert state.phase_transitions[0]["to_phase"] == InvestigationPhase.BLAST_RADIUS.value


@pytest.mark.integration
class TestHypothesisManagement:
    """Test hypothesis lifecycle management."""

    async def test_add_hypothesis_to_investigation(self, db_session):
        """Add hypothesis during investigation."""
        case = Case(
            id="case-hyp-1",
            owner_id="user-456",
            title="Test hypothesis",
            status=CaseStatus.INVESTIGATING,
        )
        db_session.add(case)
        await db_session.commit()

        case_service = CaseService(db_session=db_session)
        investigation_service = InvestigationService(case_service=case_service)

        # Initialize
        await investigation_service.initialize_investigation(
            case_id="case-hyp-1",
            user_id="user-456",
        )

        # Add hypothesis
        state, error = await investigation_service.add_hypothesis(
            case_id="case-hyp-1",
            user_id="user-456",
            statement="Connection pool size is too small",
            category="configuration",
            likelihood=0.7,
        )

        assert error is None
        assert len(state.hypotheses) == 1
        hypothesis = state.hypotheses[0]
        assert hypothesis.statement == "Connection pool size is too small"
        assert hypothesis.category == "configuration"
        assert hypothesis.likelihood == 0.7
        assert hypothesis.status == HypothesisStatus.CAPTURED

    async def test_update_hypothesis_status(self, db_session):
        """Update hypothesis through lifecycle states."""
        case = Case(
            id="case-hyp-2",
            owner_id="user-456",
            title="Test hypothesis lifecycle",
            status=CaseStatus.INVESTIGATING,
        )
        db_session.add(case)
        await db_session.commit()

        case_service = CaseService(db_session=db_session)
        investigation_service = InvestigationService(case_service=case_service)

        # Initialize and add hypothesis
        await investigation_service.initialize_investigation(
            case_id="case-hyp-2",
            user_id="user-456",
        )

        state, _ = await investigation_service.add_hypothesis(
            case_id="case-hyp-2",
            user_id="user-456",
            statement="Memory leak in application",
            category="code",
        )

        hypothesis_id = state.hypotheses[0].hypothesis_id

        # Transition to ACTIVE
        state, error = await investigation_service.update_hypothesis_status(
            case_id="case-hyp-2",
            user_id="user-456",
            hypothesis_id=hypothesis_id,
            new_status=HypothesisStatus.ACTIVE,
        )

        assert error is None
        assert state.hypotheses[0].status == HypothesisStatus.ACTIVE

        # Validate hypothesis
        state, error = await investigation_service.update_hypothesis_status(
            case_id="case-hyp-2",
            user_id="user-456",
            hypothesis_id=hypothesis_id,
            new_status=HypothesisStatus.VALIDATED,
        )

        assert error is None
        assert state.hypotheses[0].status == HypothesisStatus.VALIDATED


@pytest.mark.integration
class TestInvestigationRetrieval:
    """Test retrieving investigation state."""

    async def test_get_investigation_state(self, db_session):
        """Retrieve investigation state from case."""
        case = Case(
            id="case-get-1",
            owner_id="user-456",
            title="Test retrieval",
            status=CaseStatus.INVESTIGATING,
        )
        db_session.add(case)
        await db_session.commit()

        case_service = CaseService(db_session=db_session)
        investigation_service = InvestigationService(case_service=case_service)

        # Initialize
        original_state, _ = await investigation_service.initialize_investigation(
            case_id="case-get-1",
            user_id="user-456",
            problem_statement="Test problem",
        )

        # Retrieve
        retrieved_state = await investigation_service.get_investigation_state(
            case_id="case-get-1",
            user_id="user-456",
        )

        assert retrieved_state is not None
        assert retrieved_state.investigation_id == original_state.investigation_id
        assert retrieved_state.current_phase == InvestigationPhase.INTAKE
        assert retrieved_state.anomaly_frame.statement == "Test problem"

    async def test_get_nonexistent_investigation(self, db_session):
        """Getting investigation for case without one returns None."""
        case = Case(
            id="case-no-inv",
            owner_id="user-456",
            title="No investigation",
            status=CaseStatus.CONSULTING,
        )
        db_session.add(case)
        await db_session.commit()

        case_service = CaseService(db_session=db_session)
        investigation_service = InvestigationService(case_service=case_service)

        state = await investigation_service.get_investigation_state(
            case_id="case-no-inv",
            user_id="user-456",
        )

        assert state is None


@pytest.mark.integration
class TestInvestigationPersistence:
    """Test that investigation state persists correctly in database."""

    async def test_investigation_survives_service_recreation(self, db_session):
        """Investigation state persists across service instances."""
        # Create case
        case = Case(
            id="case-persist-1",
            owner_id="user-456",
            title="Persistence test",
            status=CaseStatus.INVESTIGATING,
        )
        db_session.add(case)
        await db_session.commit()

        # Service instance 1: Initialize investigation
        case_service_1 = CaseService(db_session=db_session)
        investigation_service_1 = InvestigationService(case_service=case_service_1)

        state_1, _ = await investigation_service_1.initialize_investigation(
            case_id="case-persist-1",
            user_id="user-456",
            problem_statement="Original problem",
        )

        investigation_id = state_1.investigation_id

        # Simulate service recreation (new instance)
        case_service_2 = CaseService(db_session=db_session)
        investigation_service_2 = InvestigationService(case_service=case_service_2)

        # Retrieve with new service instance
        state_2 = await investigation_service_2.get_investigation_state(
            case_id="case-persist-1",
            user_id="user-456",
        )

        # Should be identical
        assert state_2.investigation_id == investigation_id
        assert state_2.anomaly_frame.statement == "Original problem"
        assert state_2.current_phase == InvestigationPhase.INTAKE

    async def test_investigation_updates_case_updated_at(self, db_session):
        """Investigation operations update case.updated_at timestamp."""
        case = Case(
            id="case-timestamp-1",
            owner_id="user-456",
            title="Timestamp test",
            status=CaseStatus.CONSULTING,
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )
        db_session.add(case)
        await db_session.commit()

        original_updated_at = case.updated_at

        case_service = CaseService(db_session=db_session)
        investigation_service = InvestigationService(case_service=case_service)

        # Initialize investigation
        await investigation_service.initialize_investigation(
            case_id="case-timestamp-1",
            user_id="user-456",
        )

        # Refresh case
        await db_session.refresh(case)

        # updated_at should have changed
        assert case.updated_at > original_updated_at
