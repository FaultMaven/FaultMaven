"""Milestone-Based Investigation Engine

This module implements the milestone-based investigation system ported from FaultMaven-Mono.
It replaces rigid phase orchestration with opportunistic milestone completion.

Key Differences from Sequential Approaches:
- NO phase transitions - milestones complete when data is available
- NO sequential constraints - multiple milestones can complete in one turn
- Status-based prompt generation instead of phase-based
- Progress tracked via InvestigationState, not phase transitions

Source Reference:
- FaultMaven-Mono: faultmaven/core/investigation/milestone_engine.py (lines 1-785)

Architecture:
- Process turn → Generate status-based prompt → Invoke LLM → Process response
- Update milestones based on LLM state_updates
- Track turn progress for analytics
- Automatic status transitions (INVESTIGATING → RESOLVED)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from faultmaven.modules.case.orm import Case, CaseStatus
from faultmaven.modules.case.investigation import (
    InvestigationState,
    HypothesisModel,
    EvidenceItem,
    TurnRecord,
    ConsultingData,
    InvestigationProgress,
    DegradedModeData,
)
from faultmaven.modules.case.enums import (
    InvestigationPhase,
    HypothesisStatus,
    TurnOutcome,
    EvidenceCategory,
    DegradedModeType,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Milestone Engine - Main Implementation
# =============================================================================


class MilestoneEngine:
    """
    Milestone-based investigation engine.

    Replaces the old OODA engine with a simpler, more flexible approach where
    the agent completes milestones opportunistically based on available data.

    Responsibilities:
    - Generate prompts based on case status (CONSULTING, INVESTIGATING, RESOLVED)
    - Invoke LLM with appropriate schema
    - Process LLM responses and update case state
    - Track milestone completion and turn progress
    - Automatic status transitions when milestones complete

    Key Design Principles:
    - No phase orchestration - milestones complete when data is available
    - Status-based prompts instead of phase-based
    - Multiple milestones can complete in single turn
    - Repository abstraction for persistence (no direct DB access)

    Ported from: FaultMaven-Mono/faultmaven/core/investigation/milestone_engine.py
    """

    def __init__(
        self,
        llm_provider: Any,  # LLM provider implementation (duck typing for now)
        repository: Any = None,  # Case repository (optional, for testing)
        trace_enabled: bool = True
    ):
        """Initialize milestone engine.

        Args:
            llm_provider: LLM provider implementation with generate() method
            repository: Case repository with save/get methods (optional)
            trace_enabled: Enable observability tracing
        """
        self.llm_provider = llm_provider
        self.repository = repository
        self.trace_enabled = trace_enabled

        logger.info("MilestoneEngine initialized with milestone-based architecture")

    async def process_turn(
        self,
        case: Case,
        user_message: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Process a single conversation turn.

        This is the main entry point for the milestone engine. It:
        1. Generates status-appropriate prompt
        2. Invokes LLM with structured output
        3. Processes response and updates case state
        4. Records turn progress
        5. Checks for automatic status transitions

        Source: FaultMaven-Mono milestone_engine.py lines 111-236

        Args:
            case: Current case (SQLAlchemy ORM model)
            user_message: User's message this turn
            attachments: Optional file attachments

        Returns:
            {
                "agent_response": str,        # Natural language response to user
                "case_updated": Case,         # Updated case object
                "metadata": {
                    "turn_number": int,
                    "milestones_completed": List[str],
                    "progress_made": bool,
                    "status_transitioned": bool,
                    "outcome": TurnOutcome
                }
            }

        Raises:
            MilestoneEngineError: If processing fails
        """
        # Load investigation state from case metadata
        inv_state = self._load_investigation_state(case)

        logger.info(
            f"Processing turn {inv_state.current_turn + 1} for case {case.id} "
            f"(status: {case.status})"
        )

        try:
            # Step 1: Generate status-based prompt
            prompt = self._build_prompt(case, inv_state, user_message, attachments)

            # Step 2: Invoke LLM with structured output
            llm_response_text = await self.llm_provider.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=4000
            )

            # Step 3: Process response and update state
            updated_inv_state, turn_metadata = await self._process_response(
                case=case,
                inv_state=inv_state,
                user_message=user_message,
                llm_response=llm_response_text,
                attachments=attachments
            )

            # Step 4: Increment turn counter
            updated_inv_state.current_turn += 1

            # Step 5: Record turn progress
            turn_record = self._create_turn_record(
                turn_number=updated_inv_state.current_turn,
                milestones_completed=turn_metadata.get("milestones_completed", []),
                evidence_added=turn_metadata.get("evidence_added", []),
                hypotheses_generated=turn_metadata.get("hypotheses_generated", []),
                hypotheses_validated=turn_metadata.get("hypotheses_validated", []),
                solutions_proposed=turn_metadata.get("solutions_proposed", []),
                progress_made=turn_metadata.get("progress_made", False),
                outcome=turn_metadata.get("outcome", TurnOutcome.CONVERSATION),
                user_message=user_message,
                agent_response=llm_response_text,
                phase=updated_inv_state.current_phase
            )
            updated_inv_state.turn_history.append(turn_record)

            # Step 6: Update progress tracking
            if turn_metadata.get("progress_made", False):
                updated_inv_state.turns_without_progress = 0
            else:
                updated_inv_state.turns_without_progress += 1

            # Step 7: Check degraded mode
            if (updated_inv_state.turns_without_progress >= 3 and
                updated_inv_state.degraded_mode is None):
                self._enter_degraded_mode(updated_inv_state, "no_progress")

            # Step 8: Check automatic status transitions
            status_transitioned = self._check_automatic_transitions(case, updated_inv_state)

            # Step 9: Save investigation state back to case metadata
            self._save_investigation_state(case, updated_inv_state)

            # Step 10: Update case timestamps
            case.updated_at = datetime.now(timezone.utc)

            # Step 11: Save case if repository provided
            if self.repository:
                await self.repository.save(case)

            logger.info(
                f"Turn {updated_inv_state.current_turn} processed successfully. "
                f"Status: {case.status}, "
                f"Progress made: {turn_metadata.get('progress_made', False)}"
            )

            return {
                "agent_response": llm_response_text,
                "case_updated": case,
                "metadata": {
                    "turn_number": updated_inv_state.current_turn,
                    "milestones_completed": turn_metadata.get("milestones_completed", []),
                    "progress_made": turn_metadata.get("progress_made", False),
                    "status_transitioned": status_transitioned,
                    "outcome": turn_metadata.get("outcome", TurnOutcome.CONVERSATION),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }

        except Exception as e:
            logger.error(
                f"Error processing turn for case {case.id}: {e}",
                exc_info=True
            )
            raise MilestoneEngineError(f"Turn processing failed: {e}") from e

    # =========================================================================
    # Prompt Generation
    # Source: FaultMaven-Mono milestone_engine.py lines 237-396
    # =========================================================================

    def _build_prompt(
        self,
        case: Case,
        inv_state: InvestigationState,
        user_message: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Build status-appropriate prompt for LLM.

        Generates different prompts based on case status:
        - CONSULTING: Problem understanding and confirmation
        - INVESTIGATING: Milestone-based investigation
        - RESOLVED/CLOSED: Documentation and retrospective

        Source: FaultMaven-Mono milestone_engine.py lines 241-271

        Args:
            case: Current case (ORM model)
            inv_state: Current investigation state
            user_message: User's message
            attachments: Optional file attachments

        Returns:
            Complete prompt string
        """
        if case.status == CaseStatus.CONSULTING:
            return self._build_consulting_prompt(case, inv_state, user_message)
        elif case.status == CaseStatus.INVESTIGATING:
            return self._build_investigating_prompt(case, inv_state, user_message, attachments)
        elif case.status in [CaseStatus.RESOLVED, CaseStatus.CLOSED]:
            return self._build_terminal_prompt(case, inv_state, user_message)
        else:
            raise MilestoneEngineError(f"Unknown case status: {case.status}")

    def _build_consulting_prompt(
        self,
        case: Case,
        inv_state: InvestigationState,
        user_message: str
    ) -> str:
        """
        Build prompt for CONSULTING status.

        Source: FaultMaven-Mono milestone_engine.py lines 272-295
        """
        consulting = inv_state.consulting_data or ConsultingData()

        return f"""You are FaultMaven, an AI troubleshooting copilot. The user is exploring a problem.

Status: CONSULTING (pre-investigation)
Turn: {inv_state.current_turn + 1}

User Message:
{user_message}

Your Task:
1. Understand the user's problem
2. Ask clarifying questions if needed
3. Propose a clear, specific problem statement
4. Suggest quick fixes if obvious
5. Determine if formal investigation is needed

Current Context:
- Proposed Problem Statement: {consulting.proposed_problem_statement or "Not yet defined"}
- Problem Confirmed: {consulting.problem_statement_confirmed}
- Decided to Investigate: {consulting.decided_to_investigate}

Respond naturally and helpfully. If you have enough information, propose a clear problem statement.
If the user confirms it and wants to investigate, let them know you're ready to start."""

    def _build_investigating_prompt(
        self,
        case: Case,
        inv_state: InvestigationState,
        user_message: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Build prompt for INVESTIGATING status.

        Source: FaultMaven-Mono milestone_engine.py lines 297-376
        """
        # Build milestone status
        progress = inv_state.progress
        milestones_status = f"""
Milestones Completed:
- Symptom Verified: {progress.symptom_verified}
- Scope Assessed: {progress.scope_assessed}
- Timeline Established: {progress.timeline_established}
- Changes Identified: {progress.changes_identified}
- Root Cause Identified: {progress.root_cause_identified} (confidence: {progress.root_cause_confidence:.2f})
- Solution Proposed: {progress.solution_proposed}
- Solution Applied: {progress.solution_applied}
- Solution Verified: {progress.solution_verified}

Current Stage: {progress.current_stage}
Progress: {len(progress.completed_milestones)}/8 milestones complete
"""

        # Build evidence summary
        evidence_summary = ""
        if inv_state.evidence_items:
            evidence_summary = f"\nEvidence Collected ({len(inv_state.evidence_items)} items):\n"
            for ev in inv_state.evidence_items[-5:]:  # Last 5 evidence items
                evidence_summary += f"- [{ev.category}] {ev.description}\n"

        # Build hypothesis summary
        hypothesis_summary = ""
        if inv_state.hypotheses:
            active = [h for h in inv_state.hypotheses.values() if h.status == HypothesisStatus.ACTIVE]
            if active:
                hypothesis_summary = f"\nActive Hypotheses ({len(active)}):\n"
                for h in sorted(active, key=lambda x: x.likelihood, reverse=True)[:3]:  # Top 3
                    hypothesis_summary += f"- {h.statement} (likelihood: {h.likelihood:.2f})\n"

        # Build attachments note
        attachments_note = ""
        if attachments:
            attachments_note = f"\nAttachments Provided: {len(attachments)} file(s)"

        return f"""You are FaultMaven, an AI troubleshooting copilot conducting a formal investigation.

Status: INVESTIGATING
Case: {case.title}
Description: {case.description}
Turn: {inv_state.current_turn + 1}

{milestones_status}

{evidence_summary}

{hypothesis_summary}

User Message:
{user_message}
{attachments_note}

Your Task:
Complete as many milestones as possible based on available data. You can complete multiple milestones in one turn.

If the user provides comprehensive data (logs, metrics, etc.), analyze it thoroughly and:
1. Verify symptoms and assess scope
2. Establish timeline and identify changes
3. Identify root cause if evidence is clear
4. Propose solution if root cause is known

Key Principles:
- Milestones complete opportunistically (not sequentially)
- Use evidence to advance investigation
- Generate hypotheses only when root cause is unclear
- Focus on solving the problem efficiently

Respond with your analysis and next steps."""

    def _build_terminal_prompt(
        self,
        case: Case,
        inv_state: InvestigationState,
        user_message: str
    ) -> str:
        """
        Build prompt for RESOLVED/CLOSED status.

        Source: FaultMaven-Mono milestone_engine.py lines 377-396
        """
        return f"""You are FaultMaven, an AI troubleshooting copilot. This case is closed.

Status: {case.status.value.upper()}
Case: {case.title}
Closed At: {case.closed_at.isoformat() if case.closed_at else 'Unknown'}

User Message:
{user_message}

Your Task:
- Answer questions about the investigation
- Provide documentation or summaries if requested
- Clarify findings or recommendations
- DO NOT reopen investigation or modify case state

The investigation is complete. Focus on documentation and knowledge sharing."""

    # =========================================================================
    # Response Processing
    # Source: FaultMaven-Mono milestone_engine.py lines 397-544
    # =========================================================================

    async def _process_response(
        self,
        case: Case,
        inv_state: InvestigationState,
        user_message: str,
        llm_response: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[InvestigationState, Dict[str, Any]]:
        """
        Process LLM response and update investigation state.

        This is where the milestone completion logic lives. Based on the LLM's
        response and any provided evidence, we update:
        - Milestone completion flags
        - Evidence collection
        - Hypothesis generation/validation
        - Solutions

        Source: FaultMaven-Mono milestone_engine.py lines 401-544

        Args:
            case: Current case
            inv_state: Current investigation state
            user_message: User's message
            llm_response: LLM's response text
            attachments: Optional attachments

        Returns:
            (updated_inv_state, turn_metadata)
        """
        # Track what changed this turn
        milestones_completed = []
        evidence_added = []
        hypotheses_generated = []
        hypotheses_validated = []
        solutions_proposed = []

        # Process based on status
        if case.status == CaseStatus.CONSULTING:
            # Check for problem statement confirmation
            if "yes" in user_message.lower() or "correct" in user_message.lower():
                consulting = inv_state.consulting_data or ConsultingData()
                if consulting.proposed_problem_statement:
                    consulting.problem_statement_confirmed = True
                    consulting.problem_statement_confirmed_at = datetime.now(timezone.utc)
                    inv_state.consulting_data = consulting

            # Check for investigation decision
            if "investigate" in user_message.lower() or "go ahead" in user_message.lower():
                consulting = inv_state.consulting_data or ConsultingData()
                if consulting.problem_statement_confirmed:
                    consulting.decided_to_investigate = True
                    consulting.decision_made_at = datetime.now(timezone.utc)
                    inv_state.consulting_data = consulting

            # Check if should transition to INVESTIGATING
            status_transitioned = False
            consulting = inv_state.consulting_data or ConsultingData()
            if (consulting.problem_statement_confirmed and
                consulting.decided_to_investigate):
                await self._transition_to_investigating(case, inv_state)
                status_transitioned = True

            metadata = {
                "progress_made": consulting.problem_statement_confirmed,
                "outcome": TurnOutcome.CONVERSATION,
                "status_transitioned": status_transitioned,
            }

        elif case.status == CaseStatus.INVESTIGATING:
            # Process attachments as evidence
            if attachments:
                for attachment in attachments:
                    evidence = self._create_evidence_from_attachment(
                        case=case,
                        inv_state=inv_state,
                        attachment=attachment,
                        turn_number=inv_state.current_turn + 1
                    )
                    inv_state.evidence_items.append(evidence)
                    evidence_added.append(evidence.evidence_id)

            # Simple keyword-based milestone detection (placeholder)
            # TODO: Replace with structured output parsing
            response_lower = llm_response.lower()

            if not inv_state.progress.symptom_verified and "symptom" in response_lower:
                inv_state.progress.symptom_verified = True
                milestones_completed.append("symptom_verified")

            if not inv_state.progress.root_cause_identified and "root cause" in response_lower:
                inv_state.progress.root_cause_identified = True
                inv_state.progress.root_cause_confidence = 0.8
                inv_state.progress.root_cause_method = "direct_analysis"
                milestones_completed.append("root_cause_identified")

            if not inv_state.progress.solution_proposed and "solution" in response_lower:
                inv_state.progress.solution_proposed = True
                milestones_completed.append("solution_proposed")

            # Determine outcome
            if milestones_completed:
                outcome = TurnOutcome.PROGRESS
            elif attachments:
                outcome = TurnOutcome.EVIDENCE_COLLECTED
            else:
                outcome = TurnOutcome.CONVERSATION

            metadata = {
                "milestones_completed": milestones_completed,
                "evidence_added": evidence_added,
                "hypotheses_generated": hypotheses_generated,
                "hypotheses_validated": hypotheses_validated,
                "solutions_proposed": solutions_proposed,
                "progress_made": len(milestones_completed) > 0 or len(evidence_added) > 0,
                "outcome": outcome,
                "status_transitioned": False
            }

        else:  # RESOLVED or CLOSED
            metadata = {
                "progress_made": False,
                "outcome": TurnOutcome.CONVERSATION,
                "status_transitioned": False
            }

        return inv_state, metadata

    # =========================================================================
    # State Management
    # Source: FaultMaven-Mono milestone_engine.py lines 545-636
    # =========================================================================

    async def _transition_to_investigating(
        self,
        case: Case,
        inv_state: InvestigationState
    ) -> None:
        """
        Transition case from CONSULTING to INVESTIGATING.

        This creates the initial investigation structures and copies the
        confirmed problem statement to the case description.

        Source: FaultMaven-Mono milestone_engine.py lines 549-575
        """
        logger.info(f"Transitioning case {case.id} to INVESTIGATING")

        # Change status
        case.status = CaseStatus.INVESTIGATING

        # Copy confirmed problem statement to description
        consulting = inv_state.consulting_data or ConsultingData()
        if consulting.proposed_problem_statement:
            case.description = consulting.proposed_problem_statement

        # Initialize investigation progress
        inv_state.progress = InvestigationProgress()

    def _check_automatic_transitions(
        self,
        case: Case,
        inv_state: InvestigationState
    ) -> bool:
        """
        Check if case should automatically transition status.

        Automatic Transitions:
        - INVESTIGATING → RESOLVED when solution_verified=True

        Source: FaultMaven-Mono milestone_engine.py lines 576-600

        Returns:
            True if status transitioned, False otherwise
        """
        if (case.status == CaseStatus.INVESTIGATING and
            inv_state.progress.solution_verified):

            case.status = CaseStatus.RESOLVED
            case.resolved_at = datetime.now(timezone.utc)
            case.closed_at = datetime.now(timezone.utc)

            logger.info(
                f"Case {case.id} automatically transitioned to RESOLVED "
                f"(solution verified)"
            )
            return True

        return False

    def _enter_degraded_mode(
        self,
        inv_state: InvestigationState,
        mode_type: str,
        reason: Optional[str] = None
    ) -> None:
        """
        Enter degraded mode when investigation is stuck.

        Source: FaultMaven-Mono milestone_engine.py lines 601-636

        Args:
            inv_state: Investigation state
            mode_type: Type of degradation (no_progress, limited_data, etc.)
            reason: Optional detailed reason
        """
        if inv_state.degraded_mode:
            logger.warning(f"Investigation already in degraded mode")
            return

        # Determine reason if not provided
        if not reason:
            if mode_type == "no_progress":
                reason = f"No progress for {inv_state.turns_without_progress} consecutive turns"
            else:
                reason = "Investigation limitations encountered"

        inv_state.degraded_mode = DegradedModeData(
            mode_type=DegradedModeType(mode_type),
            reason=reason,
            entered_at=datetime.now(timezone.utc),
            attempted_actions=[]
        )

        logger.info(f"Investigation entered degraded mode: {mode_type} - {reason}")

    # =========================================================================
    # Helper Methods
    # Source: FaultMaven-Mono milestone_engine.py lines 637-776
    # =========================================================================

    def _create_evidence_from_attachment(
        self,
        case: Case,
        inv_state: InvestigationState,
        attachment: Dict[str, Any],
        turn_number: int
    ) -> EvidenceItem:
        """
        Create evidence object from file attachment.

        Source: FaultMaven-Mono milestone_engine.py lines 674-712

        Args:
            case: Current case
            inv_state: Investigation state
            attachment: Attachment metadata
            turn_number: Current turn number

        Returns:
            EvidenceItem object
        """
        # Infer category based on investigation state
        category = self._infer_evidence_category(inv_state)

        # Create evidence
        filename = attachment.get('filename', 'unknown')
        evidence = EvidenceItem(
            evidence_id=f"ev_{uuid4().hex[:12]}",
            description=f"Uploaded file: {filename}",
            category=category,
            form="document",
            source_type="user_provided",
            source=filename,
            content_summary=f"File attachment: {filename} ({attachment.get('size', 0)} bytes)",
            collected_at_turn=turn_number
        )

        return evidence

    def _infer_evidence_category(self, inv_state: InvestigationState) -> str:
        """
        Infer evidence category from investigation state.

        Rules:
        - If verification incomplete → symptom_evidence
        - If solution proposed → resolution_evidence
        - Otherwise → causal_evidence

        Source: FaultMaven-Mono milestone_engine.py lines 713-729
        """
        if not inv_state.progress.verification_complete:
            return EvidenceCategory.SYMPTOM_EVIDENCE.value

        if inv_state.progress.solution_proposed:
            return EvidenceCategory.RESOLUTION_EVIDENCE.value

        return EvidenceCategory.CAUSAL_EVIDENCE.value

    def _create_turn_record(
        self,
        turn_number: int,
        milestones_completed: List[str],
        evidence_added: List[str],
        hypotheses_generated: List[str],
        hypotheses_validated: List[str],
        solutions_proposed: List[str],
        progress_made: bool,
        outcome: TurnOutcome,
        user_message: str,
        agent_response: str,
        phase: InvestigationPhase = InvestigationPhase.INTAKE
    ) -> TurnRecord:
        """
        Create turn progress record.

        Source: FaultMaven-Mono milestone_engine.py lines 730-758
        """
        return TurnRecord(
            turn_number=turn_number,
            timestamp=datetime.now(timezone.utc),
            phase=phase,
            milestones_completed=milestones_completed,
            evidence_collected=evidence_added,
            hypotheses_updated=hypotheses_generated + hypotheses_validated,
            outcome=outcome.value if isinstance(outcome, TurnOutcome) else outcome
        )

    def _extract_actions(self, agent_response: str) -> List[str]:
        """
        Extract action keywords from agent response.

        Source: FaultMaven-Mono milestone_engine.py lines 759-770
        """
        action_keywords = ['verified', 'identified', 'proposed', 'tested', 'confirmed', 'analyzed']
        actions = []

        response_lower = agent_response.lower()
        for keyword in action_keywords:
            if keyword in response_lower:
                actions.append(keyword)

        return actions[:5]  # Limit to 5

    def _summarize_text(self, text: str, max_length: int = 200) -> str:
        """
        Summarize long text for storage.

        Source: FaultMaven-Mono milestone_engine.py lines 771-776
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    # =========================================================================
    # State Serialization (Adapter for SQLAlchemy)
    # =========================================================================

    def _load_investigation_state(self, case: Case) -> InvestigationState:
        """
        Load InvestigationState from case.case_metadata JSON.

        The investigation state is stored as JSON in the case_metadata field.
        This allows rich Pydantic models without database schema changes.
        """
        metadata = case.case_metadata or {}
        inv_data = metadata.get("investigation_state", {})

        if inv_data:
            return InvestigationState(**inv_data)
        else:
            # Initialize new investigation state with required fields
            from uuid import uuid4
            return InvestigationState(investigation_id=f"inv_{uuid4().hex[:12]}")

    def _save_investigation_state(
        self,
        case: Case,
        inv_state: InvestigationState
    ) -> None:
        """
        Save InvestigationState to case.case_metadata JSON.

        Serializes the Pydantic model to dict and stores in metadata.
        """
        if case.case_metadata is None:
            case.case_metadata = {}

        case.case_metadata["investigation_state"] = inv_state.model_dump(mode="json")


# =============================================================================
# Exceptions
# =============================================================================


class MilestoneEngineError(Exception):
    """Base exception for milestone engine errors."""
    pass
