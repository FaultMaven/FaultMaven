"""
Agent response types aligned with SRS FR-RT.

Ported from legacy: models/responses.py
Defines the 7+ response types and structured response models.
"""

from enum import Enum
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class ResponseType(str, Enum):
    """
    Agent response types per SRS FR-RT.

    Response type determination considers:
    - Urgency level
    - Information completeness
    - Case phase
    - User expertise
    - Domain complexity
    - Solution confidence
    """
    ANSWER = "answer"                           # Direct solution with actionable steps
    PLAN_PROPOSAL = "plan_proposal"             # Multi-step procedure with dependencies
    CLARIFICATION_REQUEST = "clarification_request"  # Request for additional information
    CONFIRMATION_REQUEST = "confirmation_request"    # Approval before risky actions
    SOLUTION_READY = "solution_ready"           # Verified complete solution
    NEEDS_MORE_DATA = "needs_more_data"         # Request for file uploads/data
    ESCALATION_REQUIRED = "escalation_required" # Human expert intervention needed
    VISUAL_DIAGRAM = "visual_diagram"           # Diagram or visualization
    COMPARISON_TABLE = "comparison_table"       # Tabular comparison


class SafetyLevel(str, Enum):
    """Command safety classification."""
    SAFE = "safe"                     # No risk, read-only
    READ_ONLY = "read_only"           # Safe, only reads data
    CAUTION = "caution"               # Could have side effects
    REQUIRES_CONFIRMATION = "requires_confirmation"  # Needs explicit approval
    DANGEROUS = "dangerous"           # Could cause damage


class SuggestedAction(BaseModel):
    """UI action suggestion for the client."""
    action_type: str = Field(..., description="Type of action (e.g., 'run_command', 'upload_file')")
    label: str = Field(..., description="Display label for the action")
    description: Optional[str] = Field(None, description="Detailed description")
    data: Optional[dict] = Field(None, description="Action-specific payload")
    icon: Optional[str] = Field(None, description="Icon identifier")


class CommandSuggestion(BaseModel):
    """Diagnostic command suggestion."""
    command: str = Field(..., description="The command to execute")
    description: str = Field(..., description="What this command does")
    safety_level: SafetyLevel = Field(SafetyLevel.SAFE, description="Safety classification")
    expected_output: Optional[str] = Field(None, description="What to expect from output")


class CommandValidation(BaseModel):
    """Command safety validation result."""
    command: str
    is_safe: bool
    safety_level: SafetyLevel
    explanation: str
    concerns: List[str] = []
    alternatives: List[str] = []


class EvidenceRequest(BaseModel):
    """Request for additional evidence/data."""
    evidence_type: str = Field(..., description="Type of evidence needed")
    description: str = Field(..., description="What evidence is needed and why")
    collection_method: Optional[str] = Field(None, description="How to collect this evidence")
    expected_format: Optional[str] = Field(None, description="Expected data format")
    urgency: str = Field("normal", description="How urgently this is needed")


class AgentResponse(BaseModel):
    """
    Structured agent response with type classification.

    This is the canonical response format from the agent service,
    enabling type-specific UI rendering and behavior.
    """
    response_type: ResponseType = Field(..., description="Classification of this response")
    content: str = Field(..., description="Main response content (markdown)")

    # Optional structured data
    suggested_actions: List[SuggestedAction] = Field(
        default_factory=list,
        description="Suggested UI actions"
    )
    commands: List[CommandSuggestion] = Field(
        default_factory=list,
        description="Diagnostic commands to run"
    )
    evidence_requests: List[EvidenceRequest] = Field(
        default_factory=list,
        description="Additional evidence/data needed"
    )

    # Confidence and metadata
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence in this response (0-1)"
    )
    phase: Optional[str] = Field(None, description="Current investigation phase")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "response_type": "answer",
                "content": "Based on the logs, the issue is...",
                "confidence": 0.85,
                "commands": [
                    {
                        "command": "kubectl logs -n prod deployment/api",
                        "description": "Get API deployment logs",
                        "safety_level": "read_only"
                    }
                ]
            }
        }


class PhaseSpecificFields(BaseModel):
    """Phase-specific response fields (for LeadInvestigator mode)."""

    # Phase 1: Blast Radius
    scope_assessment: Optional[dict] = Field(
        None,
        description="Affected users, components, impact severity"
    )

    # Phase 2: Timeline
    timeline_update: Optional[dict] = Field(
        None,
        description="Problem start time, recent changes, correlations"
    )

    # Phase 3: Hypothesis
    hypothesis: Optional[dict] = Field(
        None,
        description="Root cause hypothesis with likelihood and rationale"
    )

    # Phase 4: Validation
    test_result: Optional[dict] = Field(
        None,
        description="Hypothesis test result with confidence changes"
    )

    # Phase 5: Solution
    solution_proposal: Optional[dict] = Field(
        None,
        description="Solution approach, risks, verification method"
    )

    # Phase 6: Document
    case_summary: Optional[dict] = Field(
        None,
        description="Root cause, solution, lessons learned"
    )


class LeadInvestigatorResponse(AgentResponse):
    """
    Extended response for Lead Investigator mode.

    Includes phase-specific fields for investigation tracking.
    """
    phase_data: PhaseSpecificFields = Field(
        default_factory=PhaseSpecificFields,
        description="Phase-specific structured data"
    )
    milestones_completed: List[str] = Field(
        default_factory=list,
        description="Milestones completed in this turn"
    )
    next_milestone: Optional[str] = Field(
        None,
        description="Next milestone to work toward"
    )


def get_response_model_for_type(response_type: ResponseType) -> type:
    """Get the appropriate response model class for a response type."""
    # Most types use base AgentResponse
    # Lead Investigator phases use extended model
    return AgentResponse


def create_minimal_response(
    content: str,
    response_type: ResponseType = ResponseType.ANSWER
) -> AgentResponse:
    """Create a minimal response with just content."""
    return AgentResponse(
        response_type=response_type,
        content=content,
    )
