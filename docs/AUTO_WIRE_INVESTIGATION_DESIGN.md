# Auto-Wire Investigation Initialization Design

**Status:** DEFERRED (Requires product/UX input)
**Created:** 2025-12-25
**Related:** PR #20 (Business Logic Migration)

---

## Problem Statement

When a case transitions from `CONSULTING → INVESTIGATING`, should the investigation state be initialized automatically or manually?

Currently: **Manual** - User must call two separate endpoints:
1. `PUT /cases/{id}` with `{"status": "investigating"}`
2. `POST /cases/{id}/investigation/initialize` with parameters

Proposed: **Automatic** - Investigation initializes on status transition

---

## Current User Input Requirements

Investigation initialization requires:

```python
{
    "temporal_state": "ongoing" | "historical",  # Is problem happening now?
    "urgency_level": "critical" | "high" | "medium" | "low" | "unknown",
    "problem_statement": "Optional initial statement"
}
```

### Strategy Determination Matrix

Investigation strategy is auto-determined by temporal_state × urgency:

| Temporal State | Urgency | Strategy | Meaning |
|----------------|---------|----------|---------|
| ONGOING | CRITICAL/HIGH | MITIGATION_FIRST | Quick fix first, then RCA |
| ONGOING | MEDIUM/LOW | USER_CHOICE | Ambiguous - let user decide |
| HISTORICAL | CRITICAL/HIGH | USER_CHOICE | Ambiguous - let user decide |
| HISTORICAL | MEDIUM/LOW | ROOT_CAUSE | Traditional thorough RCA |

---

## User Context

**From your input:**
> "If I remember correctly, LLM should mark the answers to these questions based on the query histories and ask the user to confirm."

This suggests:
1. **LLM analyzes** conversation history to infer `temporal_state` and `urgency_level`
2. **Agent proposes** values based on analysis
3. **User confirms** or overrides

---

## Design Options

### Option A: Fully Automatic (Simple, May Be Wrong)

**Flow:**
```
User: "I want to investigate this problem"
System: (Transitions CONSULTING → INVESTIGATING)
System: (Auto-initializes with defaults: temporal_state=ONGOING, urgency=UNKNOWN)
```

**Pros:**
- ✅ Simplest user experience
- ✅ Fewest API calls
- ✅ Can't forget to initialize

**Cons:**
- ❌ Defaults may be wrong (assumes ONGOING when it might be HISTORICAL)
- ❌ Strategy determination relies on correct inputs
- ❌ No user confirmation

**Risk:** MEDIUM - May start with wrong strategy

---

### Option B: LLM-Inferred with Confirmation (Recommended)

**Flow:**
```
1. User messages during CONSULTING phase
   "Our database started timing out 2 hours ago"
   "All users affected"
   "Production is down"

2. LLM analyzes conversation:
   - Temporal: "started 2 hours ago" + "is down" → ONGOING
   - Urgency: "production down" + "all users" → CRITICAL
   - Strategy: ONGOING + CRITICAL → MITIGATION_FIRST

3. Agent proposes transition:
   "Based on our conversation, this appears to be:
    - An ONGOING problem (started 2 hours ago, still happening)
    - CRITICAL urgency (production outage affecting all users)
    - I recommend MITIGATION_FIRST strategy (quick fix, then root cause)

    Would you like to start a formal investigation? [Yes] [Customize]"

4. User confirms:
   - [Yes] → Auto-initialize with inferred values
   - [Customize] → Show form to override values

5. System transitions CONSULTING → INVESTIGATING + initializes investigation
```

**Pros:**
- ✅ Leverages LLM's contextual understanding
- ✅ User confirms before committing
- ✅ Can override if LLM is wrong
- ✅ Single decision point (no separate endpoints)

**Cons:**
- ⚠️ Requires LLM integration in status transition flow
- ⚠️ More complex implementation
- ⚠️ LLM might misinterpret context

**Risk:** LOW - User confirms before initialization

---

### Option C: Hybrid with Smart Defaults

**Flow:**
```
1. User requests status change to INVESTIGATING

2. System checks if enough context exists:
   - Has conversation history? → Use Option B (LLM inference)
   - No conversation? → Prompt for required inputs

3. Either way, user confirms before initialization
```

**Pros:**
- ✅ Works with or without conversation history
- ✅ Gracefully handles edge cases
- ✅ User always in control

**Cons:**
- ⚠️ Most complex implementation
- ⚠️ Two code paths to maintain

**Risk:** LOW - Most robust solution

---

## Implementation Requirements

### For Option B (Recommended)

#### 1. LLM Prompt for Inference

```python
# src/faultmaven/modules/case/llm_analyzer.py
class InvestigationContextAnalyzer:
    """Analyzes conversation to infer investigation parameters."""

    async def analyze_for_investigation(
        self,
        conversation_history: list[dict],
        case_description: str,
    ) -> dict:
        """
        Analyze conversation to infer temporal_state and urgency_level.

        Returns:
            {
                "temporal_state": "ongoing" | "historical",
                "urgency_level": "critical" | "high" | "medium" | "low",
                "confidence": 0.0-1.0,
                "reasoning": "Explanation of analysis"
            }
        """
        prompt = f"""Analyze this technical support conversation to determine:

1. Temporal State: Is this an ONGOING problem (currently happening) or HISTORICAL (happened in the past)?
2. Urgency Level: How urgent is this? (CRITICAL, HIGH, MEDIUM, LOW)

Conversation:
{self._format_conversation(conversation_history)}

Case Description: {case_description}

Respond in JSON:
{{
    "temporal_state": "ongoing" or "historical",
    "urgency_level": "critical" | "high" | "medium" | "low",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation citing specific evidence from conversation"
}}

Temporal State Guidelines:
- ONGOING: Problem is currently active ("is happening", "can't connect", present tense)
- HISTORICAL: Problem occurred in past ("happened yesterday", "was broken", past tense)

Urgency Guidelines:
- CRITICAL: Total outage, data loss, security breach, all users affected
- HIGH: Significant impact, many users affected, partial outage
- MEDIUM: Moderate impact, some users affected
- LOW: Minor issue, few users affected, workaround exists
"""

        response = await self.llm.chat([
            {"role": "system", "content": "You are an expert at analyzing technical problem urgency and timeline."},
            {"role": "user", "content": prompt}
        ])

        return json.loads(response.content)
```

#### 2. Agent Response Type for Confirmation

```python
# src/faultmaven/modules/agent/response_types.py (already exists!)

# Add new response type:
class InvestigationTransitionProposal(BaseModel):
    """Proposal to transition to formal investigation."""

    temporal_state: TemporalState
    urgency_level: UrgencyLevel
    strategy: InvestigationStrategy
    confidence: float
    reasoning: str
    suggested_actions: list[SuggestedAction]  # [Yes] [Customize] buttons

# Agent returns:
AgentResponse(
    response_type=ResponseType.CONFIRMATION_REQUEST,
    content="Based on our conversation, this appears to be...",
    suggested_actions=[
        SuggestedAction(
            action_type="start_investigation",
            label="Start Investigation",
            data={"temporal_state": "ongoing", "urgency_level": "critical"}
        ),
        SuggestedAction(
            action_type="customize_investigation",
            label="Customize Parameters",
            data={"show_form": true}
        ),
    ]
)
```

#### 3. Modified CaseService

```python
# src/faultmaven/modules/case/service.py

async def request_investigation_transition(
    self,
    case_id: str,
    user_id: str,
    llm_analyzer: InvestigationContextAnalyzer,
) -> dict:
    """
    Analyze case and propose investigation initialization.

    This is called when user wants to start investigating.
    Returns proposal for user confirmation.
    """
    case = await self.get_case(case_id, user_id)

    # Get conversation history
    messages = case.messages  # Assuming this exists

    # Analyze with LLM
    analysis = await llm_analyzer.analyze_for_investigation(
        conversation_history=messages,
        case_description=case.description,
    )

    return {
        "proposal": analysis,
        "case_id": case_id,
        "action_required": "confirm_or_customize",
    }


async def confirm_investigation_transition(
    self,
    case_id: str,
    user_id: str,
    temporal_state: TemporalState,
    urgency_level: UrgencyLevel,
    investigation_service: InvestigationService,
) -> Tuple[Case, Optional[InvestigationState]]:
    """
    Execute confirmed investigation transition.

    This is called after user confirms the parameters.
    """
    # Update case status
    case = await self.get_case(case_id, user_id)
    old_status = case.status
    case.status = CaseStatus.INVESTIGATING
    case.updated_at = datetime.utcnow()

    # Initialize investigation
    investigation_state, error = await investigation_service.initialize_investigation(
        case_id=case_id,
        user_id=user_id,
        problem_statement=case.description,
        temporal_state=temporal_state,
        urgency_level=urgency_level,
    )

    if error:
        # Rollback status change
        case.status = old_status
        raise Exception(f"Failed to initialize investigation: {error}")

    await self.db.commit()
    await self.db.refresh(case)

    return case, investigation_state
```

#### 4. API Endpoints

```python
# src/faultmaven/modules/case/router.py

@router.post("/{case_id}/investigation/propose")
async def propose_investigation_transition(
    case_id: str,
    case_service: CaseService = Depends(get_case_service),
    llm_analyzer: InvestigationContextAnalyzer = Depends(get_llm_analyzer),
    current_user: dict = Depends(get_current_user),
):
    """
    Analyze case and propose investigation parameters.

    Returns LLM-inferred temporal_state and urgency_level for user confirmation.
    """
    proposal = await case_service.request_investigation_transition(
        case_id=case_id,
        user_id=current_user["id"],
        llm_analyzer=llm_analyzer,
    )

    return {
        "temporal_state": proposal["proposal"]["temporal_state"],
        "urgency_level": proposal["proposal"]["urgency_level"],
        "strategy": determine_strategy(
            proposal["proposal"]["temporal_state"],
            proposal["proposal"]["urgency_level"],
        ),
        "confidence": proposal["proposal"]["confidence"],
        "reasoning": proposal["proposal"]["reasoning"],
    }


@router.post("/{case_id}/investigation/start")
async def start_investigation(
    case_id: str,
    request: StartInvestigationRequest,
    case_service: CaseService = Depends(get_case_service),
    investigation_service: InvestigationService = Depends(get_investigation_service),
    current_user: dict = Depends(get_current_user),
):
    """
    Start formal investigation with confirmed parameters.

    This endpoint:
    1. Transitions case status CONSULTING → INVESTIGATING
    2. Initializes investigation state
    3. Returns updated case + investigation state

    Body:
        {
            "temporal_state": "ongoing" | "historical",
            "urgency_level": "critical" | "high" | "medium" | "low"
        }
    """
    case, investigation = await case_service.confirm_investigation_transition(
        case_id=case_id,
        user_id=current_user["id"],
        temporal_state=request.temporal_state,
        urgency_level=request.urgency_level,
        investigation_service=investigation_service,
    )

    return {
        "case": case.to_dict(),
        "investigation": investigation.to_dict() if investigation else None,
    }
```

---

## Frontend Flow

```typescript
// User clicks "Start Investigation" button

// 1. Get AI proposal
const proposal = await fetch(`/cases/${caseId}/investigation/propose`, {
  method: 'POST'
});

// 2. Show confirmation modal
<ConfirmInvestigationModal
  temporalState={proposal.temporal_state}
  urgencyLevel={proposal.urgency_level}
  strategy={proposal.strategy}
  reasoning={proposal.reasoning}
  confidence={proposal.confidence}
  onConfirm={(params) => startInvestigation(params)}
  onCustomize={() => showCustomizeForm()}
/>

// 3. On confirmation, start investigation
async function startInvestigation(params) {
  const result = await fetch(`/cases/${caseId}/investigation/start`, {
    method: 'POST',
    body: JSON.stringify(params)
  });

  // Navigate to investigation view
  router.push(`/cases/${caseId}/investigation`);
}
```

---

## Decision Required

**Questions for Product/UX Team:**

1. Should investigation initialization be automatic or require user confirmation?
2. Is LLM inference acceptable for critical parameters (temporal_state, urgency)?
3. What should happen if LLM confidence is low (<0.7)?
4. Should we show the "Customize" option every time, or only on low confidence?
5. What's the fallback if LLM analysis fails?

**Recommended Decision:** **Option B (LLM-Inferred with Confirmation)**

**Rationale:**
- Leverages existing conversation context (user already explained the problem)
- Maintains user control (confirmation required)
- Good UX (single decision point, not multiple forms)
- Safe (user confirms before committing)

---

## Implementation Estimate

**Effort:** 2-3 days

**Tasks:**
1. Create `InvestigationContextAnalyzer` service (4 hours)
2. Add `propose` and `start` endpoints (2 hours)
3. Update `CaseService` with transition methods (2 hours)
4. Write tests for LLM analysis (3 hours)
5. Frontend integration (1 day)
6. QA and edge case handling (4 hours)

**Dependencies:**
- Existing LLM provider
- Conversation history storage in case.messages
- Frontend modal component

---

## Testing Strategy

```python
# tests/integration/test_auto_wire_investigation.py

async def test_llm_proposes_correct_temporal_state():
    """LLM correctly identifies ONGOING problem from conversation."""
    messages = [
        {"role": "user", "content": "Our API is down right now"},
        {"role": "assistant", "content": "When did this start?"},
        {"role": "user", "content": "About 30 minutes ago"},
    ]

    analysis = await analyzer.analyze_for_investigation(messages, "API outage")

    assert analysis["temporal_state"] == "ongoing"
    assert analysis["confidence"] > 0.8


async def test_llm_proposes_correct_urgency():
    """LLM correctly identifies CRITICAL urgency."""
    messages = [
        {"role": "user", "content": "Production is completely down"},
        {"role": "user", "content": "All users affected"},
    ]

    analysis = await analyzer.analyze_for_investigation(messages, "Outage")

    assert analysis["urgency_level"] == "critical"


async def test_full_transition_flow():
    """Complete flow: propose → confirm → investigate."""
    # 1. Propose
    proposal = await case_service.request_investigation_transition(...)

    # 2. Confirm
    case, investigation = await case_service.confirm_investigation_transition(
        case_id=case.id,
        user_id=user.id,
        temporal_state=proposal["proposal"]["temporal_state"],
        urgency_level=proposal["proposal"]["urgency_level"],
        investigation_service=investigation_service,
    )

    # 3. Verify
    assert case.status == CaseStatus.INVESTIGATING
    assert investigation is not None
    assert investigation.strategy == InvestigationStrategy.MITIGATION_FIRST
```

---

## Next Steps

1. **Product Decision:** Review options A/B/C, choose approach
2. **UX Design:** Design confirmation modal/form
3. **Implementation:** Follow Option B design above
4. **Testing:** Write integration tests
5. **Documentation:** Update API docs with new endpoints
6. **Rollout:** Feature flag for gradual rollout

**Status:** Awaiting product team input
**Owner:** TBD
**Timeline:** TBD after approval
