"""
Investigation domain enums.

Ported from legacy: models/investigation.py, models/case.py
These enums provide the foundation for investigation tracking and evidence classification.
"""

from enum import Enum


class InvestigationPhase(int, Enum):
    """
    Investigation phases from OODA-based methodology.

    The investigation progresses through these phases, though not strictly linearly.
    Phase transitions are recorded for audit and analytics.
    """
    INTAKE = 0           # Initial problem intake
    BLAST_RADIUS = 1     # Scope and impact assessment
    TIMELINE = 2         # Temporal analysis
    HYPOTHESIS = 3       # Root cause hypothesis formulation
    VALIDATION = 4       # Hypothesis testing and validation
    SOLUTION = 5         # Solution implementation
    DOCUMENT = 6         # Final documentation


class HypothesisStatus(str, Enum):
    """
    Hypothesis lifecycle states.

    Hypotheses progress through these states as evidence is gathered.
    """
    CAPTURED = "captured"       # Initial capture, not yet active
    ACTIVE = "active"           # Currently being investigated
    VALIDATED = "validated"     # Confirmed as root cause
    REFUTED = "refuted"         # Disproven by evidence
    RETIRED = "retired"         # Abandoned (insufficient evidence)
    SUPERSEDED = "superseded"   # Replaced by better hypothesis


class ConfidenceLevel(str, Enum):
    """
    Investigation confidence levels.

    Used to indicate certainty in conclusions and hypotheses.
    """
    SPECULATION = "speculation"  # Initial guess, minimal evidence
    PROBABLE = "probable"        # Some supporting evidence
    CONFIDENT = "confident"      # Strong evidence, high certainty
    VERIFIED = "verified"        # Conclusively proven


class DegradedModeType(str, Enum):
    """
    Types of investigation degradation.

    Used to detect when an investigation is stalled (FR-CNV circular dialogue detection).
    """
    CRITICAL_EVIDENCE_MISSING = "critical_evidence_missing"
    EXPERTISE_REQUIRED = "expertise_required"
    SYSTEMIC_ISSUE = "systemic_issue"
    HYPOTHESIS_SPACE_EXHAUSTED = "hypothesis_space_exhausted"
    GENERAL_LIMITATION = "general_limitation"
    NO_PROGRESS = "no_progress"  # 3+ turns without advancement


class EvidenceCategory(str, Enum):
    """
    Evidence classification by investigation phase.

    Evidence is categorized based on what phase/milestone it helps advance.
    """
    SYMPTOM_EVIDENCE = "symptom_evidence"       # Verifies symptoms/scope/timeline
    CAUSAL_EVIDENCE = "causal_evidence"         # Tests hypotheses for root cause
    RESOLUTION_EVIDENCE = "resolution_evidence" # Validates solution effectiveness
    OTHER = "other"                             # Contextual but doesn't advance milestones


class InvestigationMomentum(str, Enum):
    """
    Investigation progress momentum indicator.

    Used for analytics and to detect stalled investigations.
    """
    HIGH = "high"           # Rapid progress, evidence flowing
    MODERATE = "moderate"   # Steady progress
    LOW = "low"             # Slow progress, may need intervention
    BLOCKED = "blocked"     # No progress possible without external action


class TemporalState(str, Enum):
    """
    Problem temporal classification.

    Affects investigation strategy selection.
    """
    ONGOING = "ongoing"       # Problem currently happening
    HISTORICAL = "historical" # Problem occurred in past


class UrgencyLevel(str, Enum):
    """
    Problem urgency classification.

    Combined with TemporalState to determine investigation path.
    """
    CRITICAL = "critical"   # Total outage, data loss, security breach
    HIGH = "high"           # Significant impact, partial outage
    MEDIUM = "medium"       # Moderate impact
    LOW = "low"             # Minimal impact
    UNKNOWN = "unknown"     # Not yet assessed


class InvestigationStrategy(str, Enum):
    """
    Investigation path strategy.

    Determined by temporal state × urgency matrix:
    - MITIGATION_FIRST: ONGOING + (CRITICAL or HIGH)
    - ROOT_CAUSE: HISTORICAL + (LOW or MEDIUM)
    """
    MITIGATION_FIRST = "mitigation_first"  # Quick fix first, then RCA
    ROOT_CAUSE = "root_cause"              # Traditional thorough RCA
    USER_CHOICE = "user_choice"            # Ambiguous case, let user decide
