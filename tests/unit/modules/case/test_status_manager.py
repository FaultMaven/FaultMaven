"""
Unit tests for CaseStatusManager.

Tests state machine logic without database dependencies.
"""

import pytest
from datetime import datetime

from faultmaven.modules.case.orm import CaseStatus
from faultmaven.modules.case.status_manager import (
    CaseStatusManager,
    InvalidTransitionError,
    ALLOWED_TRANSITIONS,
)


class TestIsTerminal:
    """Test is_terminal method."""

    def test_resolved_is_terminal(self):
        """RESOLVED is a terminal state."""
        assert CaseStatusManager.is_terminal(CaseStatus.RESOLVED) is True

    def test_closed_is_terminal(self):
        """CLOSED is a terminal state."""
        assert CaseStatusManager.is_terminal(CaseStatus.CLOSED) is True

    def test_consulting_is_not_terminal(self):
        """CONSULTING is not a terminal state."""
        assert CaseStatusManager.is_terminal(CaseStatus.CONSULTING) is False

    def test_investigating_is_not_terminal(self):
        """INVESTIGATING is not a terminal state."""
        assert CaseStatusManager.is_terminal(CaseStatus.INVESTIGATING) is False


class TestValidateTransition:
    """Test validate_transition method."""

    # Valid transitions
    def test_consulting_to_investigating_is_valid(self):
        """Can transition from CONSULTING to INVESTIGATING."""
        valid, error = CaseStatusManager.validate_transition(
            CaseStatus.CONSULTING, CaseStatus.INVESTIGATING
        )
        assert valid is True
        assert error is None

    def test_consulting_to_closed_is_valid(self):
        """Can transition from CONSULTING to CLOSED."""
        valid, error = CaseStatusManager.validate_transition(
            CaseStatus.CONSULTING, CaseStatus.CLOSED
        )
        assert valid is True
        assert error is None

    def test_investigating_to_resolved_is_valid(self):
        """Can transition from INVESTIGATING to RESOLVED."""
        valid, error = CaseStatusManager.validate_transition(
            CaseStatus.INVESTIGATING, CaseStatus.RESOLVED
        )
        assert valid is True
        assert error is None

    def test_investigating_to_closed_is_valid(self):
        """Can transition from INVESTIGATING to CLOSED."""
        valid, error = CaseStatusManager.validate_transition(
            CaseStatus.INVESTIGATING, CaseStatus.CLOSED
        )
        assert valid is True
        assert error is None

    # Invalid transitions
    def test_consulting_to_resolved_is_invalid(self):
        """Cannot skip INVESTIGATING to go directly to RESOLVED."""
        valid, error = CaseStatusManager.validate_transition(
            CaseStatus.CONSULTING, CaseStatus.RESOLVED
        )
        assert valid is False
        assert error is not None
        assert "Invalid transition" in error

    def test_resolved_to_anything_is_invalid(self):
        """Cannot transition from RESOLVED (terminal)."""
        for target in CaseStatus:
            if target != CaseStatus.RESOLVED:
                valid, error = CaseStatusManager.validate_transition(
                    CaseStatus.RESOLVED, target
                )
                assert valid is False
                assert "terminal" in error.lower()

    def test_closed_to_anything_is_invalid(self):
        """Cannot transition from CLOSED (terminal)."""
        for target in CaseStatus:
            if target != CaseStatus.CLOSED:
                valid, error = CaseStatusManager.validate_transition(
                    CaseStatus.CLOSED, target
                )
                assert valid is False
                assert "terminal" in error.lower()

    def test_investigating_to_consulting_is_invalid(self):
        """Cannot go backwards from INVESTIGATING to CONSULTING."""
        valid, error = CaseStatusManager.validate_transition(
            CaseStatus.INVESTIGATING, CaseStatus.CONSULTING
        )
        assert valid is False
        assert "Invalid transition" in error


class TestAssertValidTransition:
    """Test assert_valid_transition method."""

    def test_valid_transition_does_not_raise(self):
        """Valid transitions should not raise."""
        # Should not raise
        CaseStatusManager.assert_valid_transition(
            CaseStatus.CONSULTING, CaseStatus.INVESTIGATING
        )

    def test_invalid_transition_raises(self):
        """Invalid transitions should raise InvalidTransitionError."""
        with pytest.raises(InvalidTransitionError) as exc_info:
            CaseStatusManager.assert_valid_transition(
                CaseStatus.RESOLVED, CaseStatus.CONSULTING
            )

        error = exc_info.value
        assert error.current == CaseStatus.RESOLVED
        assert error.target == CaseStatus.CONSULTING
        assert "terminal" in error.reason.lower()


class TestGetAllowedTransitions:
    """Test get_allowed_transitions method."""

    def test_consulting_allowed_transitions(self):
        """CONSULTING can go to INVESTIGATING or CLOSED."""
        allowed = CaseStatusManager.get_allowed_transitions(CaseStatus.CONSULTING)
        assert set(allowed) == {CaseStatus.INVESTIGATING, CaseStatus.CLOSED}

    def test_investigating_allowed_transitions(self):
        """INVESTIGATING can go to RESOLVED or CLOSED."""
        allowed = CaseStatusManager.get_allowed_transitions(CaseStatus.INVESTIGATING)
        assert set(allowed) == {CaseStatus.RESOLVED, CaseStatus.CLOSED}

    def test_resolved_has_no_allowed_transitions(self):
        """RESOLVED is terminal - no transitions allowed."""
        allowed = CaseStatusManager.get_allowed_transitions(CaseStatus.RESOLVED)
        assert allowed == []

    def test_closed_has_no_allowed_transitions(self):
        """CLOSED is terminal - no transitions allowed."""
        allowed = CaseStatusManager.get_allowed_transitions(CaseStatus.CLOSED)
        assert allowed == []


class TestGetAgentMessage:
    """Test get_agent_message method."""

    def test_consulting_to_investigating_has_message(self):
        """Starting investigation triggers agent message."""
        message = CaseStatusManager.get_agent_message(
            CaseStatus.CONSULTING, CaseStatus.INVESTIGATING
        )
        assert message is not None
        assert "investigation" in message.lower()

    def test_investigating_to_resolved_has_message(self):
        """Resolution triggers agent message."""
        message = CaseStatusManager.get_agent_message(
            CaseStatus.INVESTIGATING, CaseStatus.RESOLVED
        )
        assert message is not None
        assert "resolved" in message.lower()

    def test_undefined_transition_returns_none(self):
        """Undefined transitions return None."""
        # This is an invalid transition, but we still check the message
        message = CaseStatusManager.get_agent_message(
            CaseStatus.CONSULTING, CaseStatus.RESOLVED
        )
        assert message is None


class TestGetTerminalFields:
    """Test get_terminal_fields method."""

    def test_resolved_returns_resolved_fields(self):
        """RESOLVED sets resolved_at and resolved_by."""
        fields = CaseStatusManager.get_terminal_fields(
            CaseStatus.RESOLVED, "user-123"
        )

        assert "resolved_at" in fields
        assert "resolved_by" in fields
        assert fields["resolved_by"] == "user-123"
        assert isinstance(fields["resolved_at"], datetime)

    def test_closed_returns_closed_fields(self):
        """CLOSED sets closed_at and closed_by."""
        fields = CaseStatusManager.get_terminal_fields(
            CaseStatus.CLOSED, "user-456"
        )

        assert "closed_at" in fields
        assert "closed_by" in fields
        assert fields["closed_by"] == "user-456"
        assert isinstance(fields["closed_at"], datetime)

    def test_non_terminal_returns_empty(self):
        """Non-terminal states return empty dict."""
        fields = CaseStatusManager.get_terminal_fields(
            CaseStatus.INVESTIGATING, "user-789"
        )
        assert fields == {}


class TestBuildAuditRecord:
    """Test build_audit_record method."""

    def test_builds_complete_record(self):
        """Creates a complete audit record."""
        record = CaseStatusManager.build_audit_record(
            CaseStatus.CONSULTING,
            CaseStatus.INVESTIGATING,
            "user-123",
            auto=False,
            reason="User confirmed problem"
        )

        assert record["from_status"] == "consulting"
        assert record["to_status"] == "investigating"
        assert record["changed_by"] == "user-123"
        assert record["auto"] is False
        assert record["reason"] == "User confirmed problem"
        assert "changed_at" in record

    def test_defaults_auto_to_false(self):
        """auto defaults to False."""
        record = CaseStatusManager.build_audit_record(
            CaseStatus.INVESTIGATING,
            CaseStatus.RESOLVED,
            "user-123"
        )
        assert record["auto"] is False

    def test_reason_can_be_none(self):
        """reason can be None."""
        record = CaseStatusManager.build_audit_record(
            CaseStatus.INVESTIGATING,
            CaseStatus.RESOLVED,
            "user-123"
        )
        assert record["reason"] is None


class TestCanTransitionTo:
    """Test can_transition_to convenience method."""

    def test_returns_true_for_valid(self):
        """Returns True for valid transitions."""
        assert CaseStatusManager.can_transition_to(
            CaseStatus.CONSULTING, CaseStatus.INVESTIGATING
        ) is True

    def test_returns_false_for_invalid(self):
        """Returns False for invalid transitions."""
        assert CaseStatusManager.can_transition_to(
            CaseStatus.RESOLVED, CaseStatus.CONSULTING
        ) is False


class TestTransitionCompleteness:
    """Test that all transitions are properly defined."""

    def test_all_statuses_have_transition_rules(self):
        """Every status should have an entry in ALLOWED_TRANSITIONS."""
        for status in CaseStatus:
            assert status in ALLOWED_TRANSITIONS

    def test_transition_targets_are_valid_statuses(self):
        """All transition targets should be valid CaseStatus values."""
        for source, targets in ALLOWED_TRANSITIONS.items():
            for target in targets:
                assert isinstance(target, CaseStatus)
