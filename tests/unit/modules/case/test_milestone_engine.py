"""
Unit tests for MilestoneEngine.

Tests the engine logic without database dependencies using mock objects.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from faultmaven.modules.case.engines import MilestoneEngine, MilestoneEngineError
from faultmaven.modules.case.investigation import (
    InvestigationState,
    ConsultingData,
    InvestigationProgress,
    EvidenceItem,
)
from faultmaven.modules.case.enums import TurnOutcome
from faultmaven.modules.case.orm import CaseStatus


class MockCase:
    """Mock Case object for testing without SQLAlchemy."""

    def __init__(self, status="consulting"):
        self.id = "test-case-001"
        self.title = "Test Case"
        self.description = "Test description"
        # Convert string status to CaseStatus enum
        if isinstance(status, str):
            status_map = {
                "consulting": CaseStatus.CONSULTING,
                "investigating": CaseStatus.INVESTIGATING,
                "resolved": CaseStatus.RESOLVED,
                "closed": CaseStatus.CLOSED,
            }
            self.status = status_map.get(status, CaseStatus.CONSULTING)
        else:
            self.status = status
        self.case_metadata = {}
        self.updated_at = datetime.now()
        self.resolved_at = None
        self.closed_at = None


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def __init__(self, response="Mock LLM response"):
        self.response = response
        self.last_prompt = None

    async def generate(self, prompt, temperature=0.7, max_tokens=4000):
        self.last_prompt = prompt
        return self.response


class TestMilestoneEngine:
    """Test MilestoneEngine core functionality."""

    def test_engine_initialization(self):
        """Engine initializes with required dependencies."""
        llm = MockLLMProvider()
        engine = MilestoneEngine(llm_provider=llm)

        assert engine.llm_provider is llm
        assert engine.repository is None
        assert engine.trace_enabled is True

    def test_state_serialization(self):
        """State serialization and deserialization works."""
        llm = MockLLMProvider()
        engine = MilestoneEngine(llm_provider=llm)
        case = MockCase()

        # Create state
        inv_state = InvestigationState(investigation_id="inv-001")

        # Save to case metadata
        engine._save_investigation_state(case, inv_state)
        assert "investigation_state" in case.case_metadata

        # Load from case metadata
        loaded_state = engine._load_investigation_state(case)
        assert loaded_state.investigation_id == "inv-001"

    def test_consulting_prompt_generation(self):
        """Generates correct prompt for CONSULTING status."""
        llm = MockLLMProvider()
        engine = MilestoneEngine(llm_provider=llm)
        case = MockCase(status="consulting")
        inv_state = InvestigationState(investigation_id="inv-001")

        prompt = engine._build_consulting_prompt(case, inv_state, "My app is broken")

        assert "CONSULTING" in prompt
        assert "My app is broken" in prompt
        assert "pre-investigation" in prompt
        assert "propose a clear problem statement" in prompt

    def test_investigating_prompt_generation(self):
        """Generates correct prompt for INVESTIGATING status."""
        llm = MockLLMProvider()
        engine = MilestoneEngine(llm_provider=llm)
        case = MockCase(status="investigating")
        inv_state = InvestigationState(investigation_id="inv-001")

        prompt = engine._build_investigating_prompt(case, inv_state, "Here are my logs")

        assert "INVESTIGATING" in prompt
        assert "Here are my logs" in prompt
        assert "Milestones Completed" in prompt
        assert "symptom verified" in prompt.lower()  # Changed from symptom_verified to symptom verified

    def test_terminal_prompt_generation(self):
        """Generates correct prompt for RESOLVED status."""
        llm = MockLLMProvider()
        engine = MilestoneEngine(llm_provider=llm)
        case = MockCase(status="resolved")
        case.closed_at = datetime.now()
        inv_state = InvestigationState(investigation_id="inv-001")

        prompt = engine._build_terminal_prompt(case, inv_state, "Can you explain the fix?")

        assert "RESOLVED" in prompt
        assert "closed" in prompt.lower()
        assert "DO NOT reopen" in prompt

    def test_evidence_creation_from_attachment(self):
        """Creates evidence from file attachment."""
        llm = MockLLMProvider()
        engine = MilestoneEngine(llm_provider=llm)
        case = MockCase(status="investigating")
        inv_state = InvestigationState(investigation_id="inv-001")

        attachment = {
            "filename": "error.log",
            "file_id": "file-001",
            "size": 2048,
        }

        evidence = engine._create_evidence_from_attachment(
            case, inv_state, attachment, turn_number=1
        )

        assert evidence.evidence_id.startswith("ev_")
        assert "error.log" in evidence.content_summary  # Changed from .summary to .content_summary
        assert evidence.collected_at_turn == 1

    def test_evidence_category_inference_symptom(self):
        """Infers symptom_evidence category for unverified investigations."""
        llm = MockLLMProvider()
        engine = MilestoneEngine(llm_provider=llm)
        inv_state = InvestigationState(investigation_id="inv-001")
        # progress starts with verification_complete=False

        category = engine._infer_evidence_category(inv_state)

        assert category == "symptom_evidence"

    def test_evidence_category_inference_resolution(self):
        """Infers resolution_evidence when solution proposed."""
        llm = MockLLMProvider()
        engine = MilestoneEngine(llm_provider=llm)
        inv_state = InvestigationState(investigation_id="inv-001")
        # Must set verification complete first (checked before solution_proposed)
        inv_state.progress.symptom_verified = True
        inv_state.progress.scope_assessed = True
        inv_state.progress.timeline_established = True
        inv_state.progress.changes_identified = True
        inv_state.progress.solution_proposed = True

        category = engine._infer_evidence_category(inv_state)

        assert category == "resolution_evidence"

    def test_turn_record_creation(self):
        """Creates turn record with correct fields."""
        llm = MockLLMProvider()
        engine = MilestoneEngine(llm_provider=llm)

        turn_record = engine._create_turn_record(
            turn_number=5,
            milestones_completed=["symptom_verified"],
            evidence_added=["ev_001"],
            hypotheses_generated=[],
            hypotheses_validated=[],
            solutions_proposed=[],
            progress_made=True,
            outcome=TurnOutcome.PROGRESS,
            user_message="User message here",
            agent_response="Agent response here",
        )

        assert turn_record.turn_number == 5
        # TurnRecord uses 'outcome' not 'progress_made'
        assert turn_record.outcome == "progress"  # TurnOutcome.PROGRESS.value
        assert turn_record.milestones_completed == ["symptom_verified"]

    def test_action_extraction(self):
        """Extracts action keywords from agent response."""
        llm = MockLLMProvider()
        engine = MilestoneEngine(llm_provider=llm)

        response = "I verified the symptom and identified the root cause."
        actions = engine._extract_actions(response)

        assert "verified" in actions
        assert "identified" in actions

    def test_text_summarization(self):
        """Summarizes long text correctly."""
        llm = MockLLMProvider()
        engine = MilestoneEngine(llm_provider=llm)

        # Short text unchanged
        short = "Short text"
        assert engine._summarize_text(short, 20) == "Short text"

        # Long text truncated
        long = "A" * 300
        summary = engine._summarize_text(long, 200)
        assert len(summary) == 200
        assert summary.endswith("...")

    def test_degraded_mode_entry(self):
        """Enters degraded mode with correct data."""
        llm = MockLLMProvider()
        engine = MilestoneEngine(llm_provider=llm)
        inv_state = InvestigationState(investigation_id="inv-001")

        engine._enter_degraded_mode(inv_state, "no_progress")

        assert inv_state.degraded_mode is not None
        assert inv_state.degraded_mode.mode_type.value == "no_progress"
        assert "consecutive turns" in inv_state.degraded_mode.reason.lower()

    def test_degraded_mode_already_entered(self):
        """Doesn't re-enter degraded mode if already degraded."""
        llm = MockLLMProvider()
        engine = MilestoneEngine(llm_provider=llm)
        inv_state = InvestigationState(investigation_id="inv-001")

        # Enter first time
        engine._enter_degraded_mode(inv_state, "no_progress")
        first_entry = inv_state.degraded_mode

        # Try to enter again
        engine._enter_degraded_mode(inv_state, "critical_evidence_missing")

        # Should still be first entry
        assert inv_state.degraded_mode is first_entry

    def test_automatic_transition_to_resolved(self):
        """Automatically transitions INVESTIGATING → RESOLVED when verified."""
        llm = MockLLMProvider()
        engine = MilestoneEngine(llm_provider=llm)
        case = MockCase(status="investigating")
        inv_state = InvestigationState(investigation_id="inv-001")
        inv_state.progress.solution_verified = True

        transitioned = engine._check_automatic_transitions(case, inv_state)

        assert transitioned is True
        assert case.status == "resolved"
        assert case.resolved_at is not None
        assert case.closed_at is not None

    def test_no_transition_when_not_verified(self):
        """Doesn't transition when solution not verified."""
        llm = MockLLMProvider()
        engine = MilestoneEngine(llm_provider=llm)
        case = MockCase(status="investigating")
        inv_state = InvestigationState(investigation_id="inv-001")
        inv_state.progress.solution_proposed = True  # Not verified

        transitioned = engine._check_automatic_transitions(case, inv_state)

        assert transitioned is False
        assert case.status == "investigating"

    @pytest.mark.asyncio
    async def test_transition_to_investigating(self):
        """Transitions from CONSULTING to INVESTIGATING correctly."""
        llm = MockLLMProvider()
        engine = MilestoneEngine(llm_provider=llm)
        case = MockCase(status="consulting")
        inv_state = InvestigationState(investigation_id="inv-001")
        inv_state.consulting_data = ConsultingData(
            proposed_problem_statement="Database connection failing"
        )

        await engine._transition_to_investigating(case, inv_state)

        assert case.status == "investigating"
        assert case.description == "Database connection failing"
        assert isinstance(inv_state.progress, InvestigationProgress)


class TestMilestoneEngineIntegration:
    """Integration tests for full turn processing."""

    @pytest.mark.asyncio
    async def test_process_turn_consulting(self):
        """Processes turn in CONSULTING status."""
        llm = MockLLMProvider(response="Let me understand your problem...")
        engine = MilestoneEngine(llm_provider=llm)
        case = MockCase(status="consulting")

        result = await engine.process_turn(
            case=case,
            user_message="My database keeps crashing",
            attachments=None
        )

        assert "agent_response" in result
        assert "case_updated" in result
        assert "metadata" in result
        assert result["metadata"]["outcome"] == TurnOutcome.CONVERSATION

    @pytest.mark.asyncio
    async def test_process_turn_with_attachments(self):
        """Processes turn with file attachments."""
        llm = MockLLMProvider(response="I see the error in your logs...")
        engine = MilestoneEngine(llm_provider=llm)
        case = MockCase(status="investigating")

        attachments = [
            {"filename": "error.log", "file_id": "file-001", "size": 1024}
        ]

        result = await engine.process_turn(
            case=case,
            user_message="Here are the error logs",
            attachments=attachments
        )

        assert result["metadata"]["outcome"] == TurnOutcome.EVIDENCE_COLLECTED
        assert len(result["metadata"]["milestones_completed"]) >= 0

    @pytest.mark.asyncio
    async def test_process_turn_increments_turn_counter(self):
        """Turn counter increments correctly."""
        llm = MockLLMProvider()
        engine = MilestoneEngine(llm_provider=llm)
        case = MockCase(status="consulting")

        # Load initial state
        inv_state = engine._load_investigation_state(case)
        initial_turn = inv_state.current_turn

        # Process turn
        await engine.process_turn(case, "test message")

        # Load updated state
        updated_state = engine._load_investigation_state(case)
        assert updated_state.current_turn == initial_turn + 1

    @pytest.mark.asyncio
    async def test_process_turn_tracks_progress(self):
        """Turn history is recorded correctly."""
        llm = MockLLMProvider()
        engine = MilestoneEngine(llm_provider=llm)
        case = MockCase(status="consulting")

        await engine.process_turn(case, "First message")
        await engine.process_turn(case, "Second message")

        inv_state = engine._load_investigation_state(case)
        assert len(inv_state.turn_history) == 2
        assert inv_state.turn_history[0].turn_number == 1
        assert inv_state.turn_history[1].turn_number == 2
