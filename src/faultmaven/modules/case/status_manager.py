"""
Case status manager with state machine validation.

Ported from legacy: services/domain/case_status_manager.py

This provides centralized state transition logic for cases, ensuring:
- Only valid transitions are allowed
- Terminal states are respected
- Audit trails are maintained
- Agent messages are triggered on transitions
"""

from datetime import datetime
from typing import Optional, Tuple, Dict, List

from faultmaven.modules.case.orm import CaseStatus


# Valid state transitions
# Key = current state, Value = list of allowed target states
ALLOWED_TRANSITIONS: Dict[CaseStatus, List[CaseStatus]] = {
    CaseStatus.CONSULTING: [CaseStatus.INVESTIGATING, CaseStatus.CLOSED],
    CaseStatus.INVESTIGATING: [CaseStatus.RESOLVED, CaseStatus.CLOSED],
    CaseStatus.RESOLVED: [],  # Terminal - no transitions allowed
    CaseStatus.CLOSED: [],    # Terminal - no transitions allowed
}


# Messages sent to agent on status change
# These simulate user messages to trigger appropriate agent behavior
STATUS_CHANGE_MESSAGES: Dict[Tuple[CaseStatus, CaseStatus], str] = {
    (CaseStatus.CONSULTING, CaseStatus.INVESTIGATING): (
        "The user has confirmed the problem description. "
        "Begin formal investigation with milestone tracking."
    ),
    (CaseStatus.INVESTIGATING, CaseStatus.RESOLVED): (
        "The solution has been verified and the problem is resolved. "
        "Document the resolution for future reference."
    ),
    (CaseStatus.INVESTIGATING, CaseStatus.CLOSED): (
        "The investigation has been closed without resolution. "
        "This may be due to escalation or abandonment."
    ),
    (CaseStatus.CONSULTING, CaseStatus.CLOSED): (
        "The case has been closed during the consulting phase. "
        "No formal investigation was started."
    ),
}


class InvalidTransitionError(Exception):
    """Raised when an invalid status transition is attempted."""

    def __init__(self, current: CaseStatus, target: CaseStatus, reason: str):
        self.current = current
        self.target = target
        self.reason = reason
        super().__init__(f"Invalid transition {current.value} → {target.value}: {reason}")


class CaseStatusManager:
    """
    Static utility class for case status transitions.

    This implements the state machine for case lifecycle management,
    ensuring all transitions are valid and properly audited.
    """

    @staticmethod
    def is_terminal(status: CaseStatus) -> bool:
        """
        Check if status is terminal (no further transitions allowed).

        Args:
            status: The status to check

        Returns:
            True if terminal (RESOLVED or CLOSED), False otherwise
        """
        return status.is_terminal

    @staticmethod
    def validate_transition(
        current: CaseStatus,
        target: CaseStatus
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a status transition.

        Args:
            current: Current case status
            target: Desired target status

        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if transition is valid
            - (False, reason) if transition is invalid
        """
        # Can't transition from terminal states
        if CaseStatusManager.is_terminal(current):
            return False, f"Cannot transition from terminal state '{current.value}'"

        # Check if target is in allowed transitions
        allowed = ALLOWED_TRANSITIONS.get(current, [])
        if target not in allowed:
            allowed_str = ", ".join(s.value for s in allowed) if allowed else "none"
            return False, (
                f"Invalid transition: '{current.value}' → '{target.value}'. "
                f"Allowed targets: {allowed_str}"
            )

        return True, None

    @staticmethod
    def assert_valid_transition(current: CaseStatus, target: CaseStatus) -> None:
        """
        Assert that a transition is valid, raising an error if not.

        Args:
            current: Current case status
            target: Desired target status

        Raises:
            InvalidTransitionError: If the transition is not allowed
        """
        valid, reason = CaseStatusManager.validate_transition(current, target)
        if not valid:
            raise InvalidTransitionError(current, target, reason)

    @staticmethod
    def get_allowed_transitions(current: CaseStatus) -> List[CaseStatus]:
        """
        Get list of valid target states from current state.

        Args:
            current: Current case status

        Returns:
            List of status values that can be transitioned to
        """
        return ALLOWED_TRANSITIONS.get(current, [])

    @staticmethod
    def get_agent_message(
        old_status: CaseStatus,
        new_status: CaseStatus
    ) -> Optional[str]:
        """
        Get message to send to agent for this transition.

        These messages are used to inform the AI agent about status changes,
        triggering appropriate behavior updates.

        Args:
            old_status: Previous case status
            new_status: New case status

        Returns:
            Message string if defined, None otherwise
        """
        return STATUS_CHANGE_MESSAGES.get((old_status, new_status))

    @staticmethod
    def get_terminal_fields(
        new_status: CaseStatus,
        user_id: str
    ) -> Dict:
        """
        Get fields to update when entering terminal state.

        Sets appropriate timestamps and user references for resolution/closure.

        Args:
            new_status: The terminal status being entered
            user_id: ID of the user triggering the transition

        Returns:
            Dictionary of field names to values to update
        """
        now = datetime.utcnow()

        if new_status == CaseStatus.RESOLVED:
            return {
                "resolved_at": now,
                "resolved_by": user_id,
            }
        elif new_status == CaseStatus.CLOSED:
            return {
                "closed_at": now,
                "closed_by": user_id,
            }

        return {}

    @staticmethod
    def build_audit_record(
        old_status: CaseStatus,
        new_status: CaseStatus,
        user_id: str,
        auto: bool = False,
        reason: Optional[str] = None
    ) -> Dict:
        """
        Build audit trail entry for status change.

        Creates a structured record for storing in case_metadata["status_history"].

        Args:
            old_status: Previous status
            new_status: New status
            user_id: ID of user who triggered the change
            auto: Whether this was an automatic transition
            reason: Optional human-readable reason for the change

        Returns:
            Dictionary suitable for JSON serialization
        """
        return {
            "from_status": old_status.value,
            "to_status": new_status.value,
            "changed_at": datetime.utcnow().isoformat(),
            "changed_by": user_id,
            "auto": auto,
            "reason": reason,
        }

    @staticmethod
    def can_transition_to(current: CaseStatus, target: CaseStatus) -> bool:
        """
        Simple check if transition is allowed (no error message).

        Args:
            current: Current case status
            target: Desired target status

        Returns:
            True if transition is allowed, False otherwise
        """
        valid, _ = CaseStatusManager.validate_transition(current, target)
        return valid

    @staticmethod
    def get_transition_description(
        old_status: CaseStatus,
        new_status: CaseStatus
    ) -> str:
        """
        Get a human-readable description of a status transition.

        Args:
            old_status: Previous status
            new_status: New status

        Returns:
            Description string
        """
        descriptions = {
            (CaseStatus.CONSULTING, CaseStatus.INVESTIGATING): (
                "Starting formal investigation"
            ),
            (CaseStatus.INVESTIGATING, CaseStatus.RESOLVED): (
                "Problem resolved with verified solution"
            ),
            (CaseStatus.INVESTIGATING, CaseStatus.CLOSED): (
                "Investigation closed without resolution"
            ),
            (CaseStatus.CONSULTING, CaseStatus.CLOSED): (
                "Case closed during initial consultation"
            ),
        }

        return descriptions.get(
            (old_status, new_status),
            f"Status changed from {old_status.value} to {new_status.value}"
        )
