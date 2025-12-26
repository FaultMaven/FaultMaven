# Phase 1 Complete - Implementation Next Steps

**Status:** Phase 1 COMPLETE ✅
**Date:** 2025-12-25
**Ready for:** Phase 2 Implementation

---

## ✅ Phase 1 Completed (Foundation Enhancement)

### What Was Delivered

**1. Enhanced Pydantic Models** ([investigation.py](../src/faultmaven/modules/case/investigation.py)):

- ✅ **HypothesisModel** - Added 8 missing fields:
  - `initial_likelihood`: Starting confidence baseline
  - `confidence_trajectory`: List[(turn, confidence)] history
  - `last_progress_at_turn`: Stagnation tracking
  - `promoted_to_active_at_turn`: Lifecycle milestone
  - `iterations_without_progress`: Anchoring detection
  - `generation_mode`: "opportunistic" vs "systematic"
  - `triggering_observation`: Capture context

- ✅ **EvidenceItem** - Added classification fields:
  - `form`: Evidence manifestation type
  - `source_type`: Evidence origin

- ✅ **New Models Added:**
  - `OODAIteration`: OODA cycle execution record
  - `OODAState`: Current OODA state with intensity
  - `MemorySnapshot`: Point-in-time conversation snapshot
  - `HierarchicalMemory`: Hot/warm/cold memory tiers

- ✅ **InvestigationState** - Added orchestration layers:
  - `ooda_state`: OODA execution tracking
  - `memory`: Hierarchical memory management
  - Enhanced `TurnRecord` with outcome classification

**2. Added 7 Missing Enums** ([enums.py](../src/faultmaven/modules/case/enums.py)):

- ✅ `OODAStep`: observe, orient, decide, act
- ✅ `EvidenceForm`: 7 evidence types
- ✅ `EvidenceSourceType`: 6 source types
- ✅ `HypothesisGenerationMode`: opportunistic vs systematic
- ✅ `HypothesisCategory`: 8 hypothesis domains
- ✅ `EngagementMode`: consultant vs lead_investigator
- ✅ `TurnOutcome`: 8 turn outcomes

**3. Created Engines Directory** ([engines/](../src/faultmaven/modules/case/engines/)):
- ✅ Directory structure created
- ✅ `__init__.py` with package documentation

**Commits:**
- `8e0e9c6` - Phase 1 Complete: Enhanced foundation models and enums

---

## 🎯 Phase 2: Core Engines Implementation (NEXT)

### Priority Order

**Week 1 Goals:**
1. MilestoneEngine (2 days)
2. HypothesisManager (1.5 days)
3. OODAEngine (1 day)

### Task 2.1: Implement MilestoneEngine (2 days - 16 hours)

**File:** `src/faultmaven/modules/case/engines/milestone_engine.py`

**Port from:** `FaultMaven-Mono/faultmaven/core/investigation/milestone_engine.py` (lines 1-785)

**Key Components:**

```python
class MilestoneEngine:
    """
    Main orchestration engine for investigation turns.

    Replaces rigid OODA framework with opportunistic milestone completion.
    Processes turns, generates status-based prompts, invokes LLM, updates state.
    """

    def __init__(self, llm_provider):
        self.llm_provider = llm_provider

    # CRITICAL METHODS TO PORT:

    async def process_turn(
        self,
        state: InvestigationState,
        case: Case,
        user_message: str,
        attachments: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point - process one investigation turn.

        Port from lines 111-236 in FaultMaven-Mono.

        Steps:
        1. Generate status-based prompt
        2. Invoke LLM
        3. Extract state updates from response
        4. Update investigation state
        5. Check automatic transitions
        6. Record turn in history

        Returns:
            {
                "agent_response": str,
                "state_updated": InvestigationState,
                "metadata": {...}
            }
        """

    def _build_prompt(
        self,
        case_status: CaseStatus,
        state: InvestigationState,
        user_message: str
    ) -> str:
        """
        Generate status-appropriate prompt.

        Port from lines 241-271.

        Dispatches to:
        - _build_consulting_prompt() for CONSULTING status
        - _build_investigating_prompt() for INVESTIGATING status
        - _build_terminal_prompt() for RESOLVED/CLOSED status
        """

    def _build_consulting_prompt(
        self,
        state: InvestigationState,
        user_message: str
    ) -> str:
        """
        Consultant mode prompt (Phase 0).

        Port from lines 272-295.

        Template:
        - Status: CONSULTING (pre-investigation)
        - Turn: {turn_number}
        - User Message: {user_message}
        - Task: Understand, clarify, propose problem statement
        - Context: Current consulting data
        """

    def _build_investigating_prompt(
        self,
        state: InvestigationState,
        user_message: str
    ) -> str:
        """
        Lead Investigator mode prompt (Phases 1-6).

        Port from lines 297-458.

        Includes:
        - Phase context and objectives
        - Current progress summary
        - OODA guidance
        - Memory context (hot + warm)
        - Milestone tracking
        """

    def _extract_state_updates(self, llm_response: str) -> Dict:
        """
        Parse LLM response for state updates.

        Port from lines 460-530.

        Extracts:
        - Milestones completed
        - Hypotheses generated/updated
        - Evidence collected
        - Phase transitions suggested
        """

    def _check_automatic_transitions(
        self,
        state: InvestigationState,
        case: Case
    ):
        """
        Check if case should auto-transition status.

        Port from lines 532-580.

        Rules:
        - INVESTIGATING → RESOLVED when root cause validated
        - Enter degraded mode if no progress for 3+ turns
        """
```

**Implementation Steps:**

1. Create file with basic structure (1 hour)
2. Implement `__init__` and `process_turn` (3 hours)
3. Implement `_build_prompt` dispatcher (1 hour)
4. Implement `_build_consulting_prompt` (2 hours)
5. Implement `_build_investigating_prompt` (4 hours)
6. Implement `_extract_state_updates` (2 hours)
7. Implement `_check_automatic_transitions` (1 hour)
8. Add logging and error handling (2 hours)

**Testing:**
- Create `tests/unit/modules/case/engines/test_milestone_engine.py`
- Test each prompt generation method
- Test turn processing flow
- Test automatic transitions

**References:**
- FaultMaven-Mono: `faultmaven/core/investigation/milestone_engine.py`
- Lines to port: 1-785
- Active (verified in deprecation analysis)

---

### Task 2.2: Implement HypothesisManager (1.5 days - 12 hours)

**File:** `src/faultmaven/modules/case/engines/hypothesis_manager.py`

**Port from:** `FaultMaven-Mono/faultmaven/core/investigation/hypothesis_manager.py` (lines 1-751)

**Key Components:**

```python
class HypothesisManager:
    """
    Unified hypothesis lifecycle and confidence management.

    Handles:
    - Hypothesis creation (opportunistic + systematic)
    - Evidence linking
    - Confidence calculation (evidence-ratio based)
    - Confidence decay (stagnation penalty)
    - Auto-transition (VALIDATED/REFUTED)
    - Anchoring detection
    """

    # CRITICAL METHODS TO PORT:

    def create_hypothesis(
        self,
        statement: str,
        category: HypothesisCategory,
        initial_likelihood: float,
        current_turn: int,
        generation_mode: HypothesisGenerationMode
    ) -> HypothesisModel:
        """Create new hypothesis. Port from lines 68-119."""

    def link_evidence(
        self,
        hypothesis: HypothesisModel,
        evidence_id: str,
        supports: bool,
        turn: int
    ) -> None:
        """Link evidence and update confidence. Port from lines 121-160."""

    def update_confidence(
        self,
        hypothesis: HypothesisModel,
        current_turn: int
    ) -> float:
        """
        Calculate confidence based on evidence ratio.

        Port from lines 162-220.

        Formula:
            confidence = initial + (0.15 × supporting) - (0.20 × refuting)

        Bounds: [0.0, 1.0]
        """

    def apply_confidence_decay(
        self,
        hypothesis: HypothesisModel,
        current_turn: int
    ) -> float:
        """
        Apply decay for stagnation.

        Port from lines 222-260.

        Formula:
            confidence = base × 0.85^iterations_without_progress
        """

    def _check_auto_transition(
        self,
        hypothesis: HypothesisModel,
        turn: int
    ) -> None:
        """
        Auto-transition to VALIDATED or REFUTED.

        Port from lines 280-320.

        Rules:
        - VALIDATED: confidence ≥ 0.7 AND ≥ 2 supporting evidence
        - REFUTED: confidence ≤ 0.2 AND ≥ 2 refuting evidence
        """

    def detect_anchoring(
        self,
        hypotheses: List[HypothesisModel]
    ) -> Optional[str]:
        """
        Detect anchoring bias patterns.

        Port from lines 392-450.

        Patterns:
        1. 4+ hypotheses in same category
        2. 3+ iterations without progress
        3. Top hypothesis stagnant for 3+ iterations

        Returns: Warning message if detected
        """

    def retire_stalled_hypotheses(
        self,
        hypotheses: List[HypothesisModel],
        turn: int
    ) -> List[str]:
        """Retire hypotheses with no progress for 3+ iterations."""
```

**Implementation Steps:**

1. Create file with basic structure (1 hour)
2. Implement `create_hypothesis` (1 hour)
3. Implement `link_evidence` (1 hour)
4. Implement `update_confidence` with formula (2 hours)
5. Implement `apply_confidence_decay` (1 hour)
6. Implement `_check_auto_transition` (1 hour)
7. Implement `detect_anchoring` (2 hours)
8. Implement `retire_stalled_hypotheses` (1 hour)
9. Add tests (2 hours)

---

### Task 2.3: Implement OODAEngine (1 day - 8 hours)

**File:** `src/faultmaven/modules/case/engines/ooda_engine.py`

**Port from:** `FaultMaven-Mono/faultmaven/core/investigation/ooda_engine.py` (lines 1-534)

**Key Components:**

```python
class OODAEngine:
    """
    OODA loop execution and adaptive intensity control.

    Manages:
    - OODA iteration execution
    - Adaptive intensity (light/medium/full)
    - Anchoring prevention triggers
    - OODA step determination
    """

    # CRITICAL METHODS TO PORT:

    def execute_iteration(
        self,
        state: InvestigationState,
        phase: InvestigationPhase
    ) -> OODAIteration:
        """Execute one OODA iteration. Port from lines 200-280."""

    @staticmethod
    def get_adaptive_intensity(
        iteration_count: int,
        phase: InvestigationPhase
    ) -> str:
        """
        Determine investigation intensity.

        Port from lines 58-98.

        Levels:
        - Light: 1-2 iterations (simple problems)
        - Medium: 3-5 iterations (typical)
        - Full: 6+ iterations (complex, enable anchoring)
        """

    @staticmethod
    def should_trigger_anchoring_prevention(
        iteration_count: int,
        hypotheses: List[HypothesisModel]
    ) -> Tuple[bool, Optional[str]]:
        """Check if anchoring prevention should trigger. Port from lines 100-150."""

    def _determine_ooda_step(
        self,
        phase: InvestigationPhase,
        iteration: int
    ) -> OODAStep:
        """Map phase and iteration to OODA step. Port from lines 320-380."""
```

**Implementation Steps:**

1. Create file with basic structure (1 hour)
2. Implement `get_adaptive_intensity` (2 hours)
3. Implement `should_trigger_anchoring_prevention` (1 hour)
4. Implement `execute_iteration` (2 hours)
5. Implement `_determine_ooda_step` (1 hour)
6. Add tests (1 hour)

---

## 📋 Implementation Checklist

### Before Starting Phase 2

- [x] Phase 1 complete and committed
- [x] Foundation models enhanced
- [x] All enums added
- [x] Engines directory created
- [ ] Review FaultMaven-Mono code one more time
- [ ] Set up test environment

### Phase 2 - Week 1

**Day 1-2: MilestoneEngine**
- [ ] Create `milestone_engine.py` stub
- [ ] Implement `process_turn` method
- [ ] Implement prompt generation methods
- [ ] Implement state update extraction
- [ ] Add logging and error handling
- [ ] Write unit tests
- [ ] Commit: "Implement MilestoneEngine core orchestration"

**Day 3-4: HypothesisManager**
- [ ] Create `hypothesis_manager.py` stub
- [ ] Implement confidence calculation
- [ ] Implement evidence linking
- [ ] Implement confidence decay
- [ ] Implement anchoring detection
- [ ] Write unit tests
- [ ] Commit: "Implement HypothesisManager with confidence algorithms"

**Day 5: OODAEngine**
- [ ] Create `ooda_engine.py` stub
- [ ] Implement adaptive intensity
- [ ] Implement OODA iteration
- [ ] Implement step determination
- [ ] Write unit tests
- [ ] Commit: "Implement OODAEngine with adaptive intensity"

### Integration (End of Week 1)

- [ ] Update `investigation_service.py` to use engines
- [ ] Replace `advance_turn()` with `process_turn()` delegation
- [ ] Add LLM provider integration
- [ ] Run integration tests
- [ ] Commit: "Integrate core engines into investigation service"

---

## 🔗 Key References

**Documentation:**
- [INVESTIGATION_FRAMEWORK_AUDIT_AND_MIGRATION_SPEC.md](INVESTIGATION_FRAMEWORK_AUDIT_AND_MIGRATION_SPEC.md) - Complete migration spec
- [FAULTMAVEN_MONO_DEPRECATION_ANALYSIS.md](FAULTMAVEN_MONO_DEPRECATION_ANALYSIS.md) - Verified active components
- [INVESTIGATION_FRAMEWORK_GAP_ANALYSIS.md](INVESTIGATION_FRAMEWORK_GAP_ANALYSIS.md) - Initial gap analysis

**Source Code (FaultMaven-Mono):**
- `faultmaven/core/investigation/milestone_engine.py` - Lines 1-785
- `faultmaven/core/investigation/hypothesis_manager.py` - Lines 1-751
- `faultmaven/core/investigation/ooda_engine.py` - Lines 1-534
- `faultmaven/core/investigation/__init__.py` - Module exports

**Current Code (faultmaven):**
- `src/faultmaven/modules/case/investigation.py` - Enhanced models
- `src/faultmaven/modules/case/enums.py` - All enums
- `src/faultmaven/modules/case/investigation_service.py` - Service to be refactored
- `src/faultmaven/modules/case/engines/__init__.py` - Engines package

---

## 💡 Implementation Tips

**1. Use Type Hints:**
```python
from typing import Optional, List, Dict, Any, Tuple
from faultmaven.modules.case.investigation import InvestigationState, HypothesisModel
from faultmaven.modules.case.enums import InvestigationPhase, OODAStep
```

**2. Add Comprehensive Logging:**
```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Processing turn {turn} for case {case_id}")
logger.debug(f"Hypothesis confidence updated: {old} → {new}")
```

**3. Follow FaultMaven-Mono Structure:**
- Copy method signatures exactly
- Port algorithms line-by-line
- Keep same variable names for clarity
- Add comments referencing source line numbers

**4. Test Each Component:**
```python
# tests/unit/modules/case/engines/test_milestone_engine.py
async def test_process_turn_consulting_mode():
    """Test turn processing in CONSULTING status."""
    state = InvestigationState(...)
    result = await engine.process_turn(state, case, "user message")
    assert result["agent_response"] is not None
    assert result["state_updated"].current_turn == 1
```

**5. Incremental Commits:**
- Commit after each major component
- Use descriptive messages
- Reference source file and lines

---

## 🚀 Ready to Continue

**Status:** Phase 1 complete, foundation solid, ready for Phase 2

**Next Action:** Begin Task 2.1 - Implement MilestoneEngine

**Estimated Completion:**
- Phase 2 (Core engines): Week 1 (5 days)
- Phase 3 (Supporting engines): Week 2 (3 days)
- Phase 4 (Integration): Week 2 (2 days)
- Phase 5 (Testing/Docs): Week 3 (2 days)

**Total: 12 working days (2.5 weeks)**

All specifications are ready. Implementation can proceed incrementally with clear milestones.
