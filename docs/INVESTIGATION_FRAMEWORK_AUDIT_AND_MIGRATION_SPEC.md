# Investigation Framework Audit & Complete Migration Specification

**Status:** CRITICAL - Complete reimplementation required
**Priority:** #1 - Investigation framework correctness is top priority
**Created:** 2025-12-25
**Approach:** Option A with improved structure

---

## Executive Summary

**Audit conclusion:** The current faultmaven investigation implementation is **SHALLOW AND INCOMPLETE** - approximately 10-15% of the real system. It contains:
- ✅ **Valid:** Data models (Pydantic schemas) - well-structured
- ❌ **Missing:** All orchestration logic (milestone engine, OODA, hypothesis confidence, etc.)
- ❌ **Fake:** The "phase-based sequential" approach is a stub - phases are defined but not actually used

**Verdict:** The FaultMaven-Mono implementation is the **correct and complete** one. We must implement exactly the same logic while keeping structure clean and cohesive.

---

## Detailed Audit: What's Valid vs What's Fake

### ✅ VALID Components (Keep & Enhance)

#### 1. Data Models ([investigation.py](../src/faultmaven/modules/case/investigation.py) - 501 LOC)

**Status:** **80% VALID** - Well-structured Pydantic models, minor enhancements needed

**What's good:**
```python
# Strong data models with proper typing
class InvestigationState(BaseModel):
    investigation_id: str
    current_phase: InvestigationPhase
    current_turn: int
    temporal_state: TemporalState
    urgency_level: UrgencyLevel
    strategy: InvestigationStrategy
    anomaly_frame: Optional[AnomalyFrame]
    temporal_frame: Optional[TemporalFrame]
    hypotheses: List[HypothesisModel]
    evidence: List[EvidenceItem]
    progress: ProgressMetrics
    escalation: EscalationState
    working_conclusion: Optional[WorkingConclusion]
    turn_history: List[TurnRecord]
```

**Comparison with FaultMaven-Mono:**
| Model | faultmaven | FaultMaven-Mono | Gap |
|-------|------------|-----------------|-----|
| **InvestigationState** | ✅ Present | ✅ Present (fuller) | Missing: ooda_engine layer, memory layer, lifecycle layer |
| **AnomalyFrame** | ✅ Present | ✅ Present | ⚠️ Missing: revision history tracking |
| **TemporalFrame** | ✅ Present | ✅ Present | ✅ Equivalent |
| **HypothesisModel** | ✅ Present | ✅ Hypothesis class | ❌ Missing: confidence_trajectory, iterations_without_progress, generation_mode |
| **EvidenceItem** | ✅ Present | ✅ Evidence class | ❌ Missing: form (EvidenceForm enum), source_type (EvidenceSourceType) |
| **ProgressMetrics** | ✅ Present | ✅ InvestigationProgress | ⚠️ Different milestone tracking approach |
| **WorkingConclusion** | ✅ Present | ✅ WorkingConclusion | ✅ Equivalent |
| **TurnRecord** | ✅ Present | ✅ TurnProgress | ⚠️ Missing: outcome classification |

**Required enhancements:**
1. **HypothesisModel** - Add fields from FaultMaven-Mono:
   ```python
   # Add these fields:
   initial_likelihood: float
   confidence_trajectory: List[Tuple[int, float]]  # (turn, confidence)
   iterations_without_progress: int
   generation_mode: HypothesisGenerationMode  # OPPORTUNISTIC vs SYSTEMATIC
   last_progress_at_turn: int
   promoted_to_active_at_turn: Optional[int]
   triggering_observation: Optional[str]
   ```

2. **EvidenceItem** - Add form and source_type:
   ```python
   # Add these fields:
   form: EvidenceForm  # DIRECT_OBSERVATION, SYMPTOM, METRIC, etc.
   source_type: EvidenceSourceType  # USER_PROVIDED, SYSTEM_QUERY, LOG_ANALYSIS
   ```

3. **InvestigationState** - Add OODA and memory layers:
   ```python
   # Add these top-level fields:
   ooda_state: OODAState  # Current OODA iteration, step, history
   memory: HierarchicalMemory  # Hot/warm/cold memory tiers
   ```

**Verdict:** Models are 80% there - enhance with missing fields from FaultMaven-Mono

---

#### 2. Enums ([enums.py](../src/faultmaven/modules/case/enums.py))

**Status:** **90% VALID** - All necessary enums present, minor additions needed

**What's present:**
```python
class InvestigationPhase(int, Enum)  # ✅ 0-6 phases correct
class HypothesisStatus(str, Enum)  # ✅ CAPTURED, ACTIVE, VALIDATED, REFUTED, RETIRED
class TemporalState(str, Enum)  # ✅ ONGOING, HISTORICAL
class UrgencyLevel(str, Enum)  # ✅ CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN
class InvestigationStrategy(str, Enum)  # ✅ MITIGATION_FIRST, ROOT_CAUSE, USER_CHOICE
class ConfidenceLevel(str, Enum)  # ✅ SPECULATION, MEDIUM_CONFIDENCE, HIGH_CONFIDENCE
class DegradedModeType(str, Enum)  # ✅ NO_PROGRESS, HYPOTHESIS_SPACE_EXHAUSTED, etc.
class EvidenceCategory(str, Enum)  # ✅ LOGS, METRICS, CONFIG, CODE, TIMELINE, etc.
class InvestigationMomentum(str, Enum)  # ✅ BLOCKED, LOW, MODERATE, HIGH
```

**Missing from FaultMaven-Mono:**
```python
class OODAStep(str, Enum)  # ❌ OBSERVE, ORIENT, DECIDE, ACT
class EvidenceForm(str, Enum)  # ❌ DIRECT_OBSERVATION, SYMPTOM, METRIC, etc.
class EvidenceSourceType(str, Enum)  # ❌ USER_PROVIDED, SYSTEM_QUERY, LOG_ANALYSIS
class HypothesisGenerationMode(str, Enum)  # ❌ OPPORTUNISTIC, SYSTEMATIC
class HypothesisCategory(str, Enum)  # ❌ Infrastructure, code, config, etc.
class EngagementMode(str, Enum)  # ❌ CONSULTANT, LEAD_INVESTIGATOR
class TurnOutcome(str, Enum)  # ❌ PROGRESS, CONVERSATION, BLOCKED, etc.
```

**Verdict:** Enums are good - add 7 missing enums from FaultMaven-Mono

---

### ❌ FAKE/SHALLOW Components (Completely Rewrite)

#### 1. InvestigationService ([investigation_service.py](../src/faultmaven/modules/case/investigation_service.py) - 608 LOC)

**Status:** **FAKE - Only 10% of real functionality**

**What it currently has:**
```python
class InvestigationService:
    async def initialize_investigation(...)  # ✅ Basic initialization
    async def advance_turn(...)  # ⚠️ SHALLOW - just increments counter
    async def add_hypothesis(...)  # ⚠️ SHALLOW - just appends to list
    async def update_hypothesis_status(...)  # ⚠️ SHALLOW - just updates status
    async def add_evidence(...)  # ⚠️ SHALLOW - just appends to list
    async def update_working_conclusion(...)  # ⚠️ SHALLOW - just sets field

    # NO ACTUAL ORCHESTRATION LOGIC
    # NO CONFIDENCE CALCULATION
    # NO EVIDENCE-BASED VALIDATION
    # NO ANCHORING PREVENTION
    # NO OODA EXECUTION
    # NO MILESTONE TRACKING
```

**What FaultMaven-Mono has:**
```python
# 13 sophisticated modules totaling 6,069 LOC:

# Core orchestration (785 LOC)
class MilestoneEngine:
    async def process_turn(case, user_message, attachments)
    def _build_prompt(case, user_message, attachments)  # Status-based
    def _build_consulting_prompt(...)
    def _build_investigating_prompt(...)
    def _process_response(...)
    def _check_automatic_transitions(...)
    def _enter_degraded_mode(...)

# OODA execution (534 LOC)
class OODAEngine:
    def execute_iteration(state, phase)
    def _determine_ooda_step(phase, iteration_count)
    def get_adaptive_intensity(iteration_count, phase)
    def should_trigger_anchoring_prevention(...)

# Hypothesis confidence management (751 LOC)
class HypothesisManager:
    def create_hypothesis(...)
    def link_evidence(hypothesis, evidence_id, supports)
    def update_confidence(hypothesis)  # Evidence-ratio based
    def apply_confidence_decay(hypothesis)  # Stagnation penalty
    def check_auto_transition(hypothesis)  # VALIDATED/REFUTED thresholds
    def detect_anchoring(hypotheses)
    def retire_stalled_hypotheses(hypotheses)

# Memory management (590 LOC)
class MemoryManager:
    def organize_context(conversation, evidence, hypotheses)
    def get_hot_memory()  # Recent critical info
    def get_warm_memory()  # Relevant context
    def prune_cold_memory()  # Archive old context

# Working conclusion generation (494 LOC)
class WorkingConclusionGenerator:
    def generate_conclusion(state)
    def assess_confidence(evidence, hypotheses)
    def identify_gaps(state)
    def should_suggest_closure(state)

# Phase management (424 LOC)
class PhaseLoopback:
    def should_advance_phase(state)
    def should_loop_back(state)
    def get_phase_completion_criteria(phase)

# And 7 more supporting modules...
```

**Comparison:**

| Capability | faultmaven | FaultMaven-Mono | Implementation Gap |
|------------|------------|-----------------|-------------------|
| **Turn processing** | ✅ Basic counter | ✅ Full orchestration | ❌ No prompt generation, no LLM invocation, no response processing |
| **Hypothesis confidence** | ❌ None | ✅ Evidence-ratio formula + decay | ❌ Completely missing |
| **Evidence linking** | ❌ None | ✅ HypothesisEvidenceLink | ❌ Completely missing |
| **Anchoring prevention** | ❌ None | ✅ Detection + intervention | ❌ Completely missing |
| **OODA execution** | ❌ None | ✅ Full OODA loop | ❌ Completely missing |
| **Milestone tracking** | ⚠️ List only | ✅ Opportunistic completion | ❌ No completion logic |
| **Phase progression** | ⚠️ Manual only | ✅ Automatic detection | ❌ No detection logic |
| **Memory management** | ❌ None | ✅ Hierarchical tiers | ❌ Completely missing |
| **Working conclusions** | ⚠️ Set only | ✅ Auto-generation | ❌ No generation logic |
| **Degraded mode** | ⚠️ Detection only | ✅ Detection + intervention | ⚠️ Detection present, no intervention |

**Verdict:** Current service is a **CRUD wrapper with no intelligence** - must reimplement all 13 modules

---

#### 2. Phase-Based Sequential Approach

**Status:** **FAKE - Phases defined but not used**

**Current implementation:**
```python
# investigation_service.py:234
if phase_transition and phase_transition != state.current_phase:
    state.current_phase = phase_transition
    made_progress = True
```

**Problem:** Phase transition is **manual parameter** - there's NO logic to:
- Determine when a phase is complete
- Suggest phase transitions
- Enforce phase prerequisites
- Map phases to OODA steps
- Handle phase loopback

**FaultMaven-Mono approach:**
```python
# phases.py - 519 LOC defining:
- Phase objectives (what each phase accomplishes)
- Phase completion criteria (when to advance)
- OODA step mappings (which OODA steps per phase)
- Phase prerequisites (what must be complete before entering)
- Loopback conditions (when to iterate within phase)

# workflow_progression_detector.py - 258 LOC:
def detect_phase_completion(state, current_phase):
    """Analyzes evidence and hypotheses to determine if phase is complete."""

# phase_loopback.py - 424 LOC:
def should_loop_back(state, phase):
    """Determines if we should iterate within phase vs advance."""
```

**Verdict:** Phases are **cosmetic** - no actual phase orchestration logic exists

---

## What Must Be Implemented (Complete Specification)

### Architecture: 3-Layer Structure (Clean & Cohesive)

```
┌─────────────────────────────────────────────────────────────────┐
│                   Layer 1: Service Layer                        │
│  (investigation_service.py - Public API, Case integration)      │
│                                                                  │
│  - initialize_investigation()                                   │
│  - advance_turn()  ← Delegates to MilestoneEngine               │
│  - add_hypothesis()  ← Delegates to HypothesisManager           │
│  - get_working_conclusion()  ← Delegates to ConclusionGenerator │
│  - Case metadata persistence                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Layer 2: Orchestration Layer                   │
│         (Engines and managers - Business logic)                 │
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │  MilestoneEngine     │  │  HypothesisManager   │            │
│  │  - process_turn()    │  │  - update_confidence()│            │
│  │  - build_prompt()    │  │  - link_evidence()   │            │
│  │  - track_progress()  │  │  - detect_anchoring()│            │
│  └──────────────────────┘  └──────────────────────┘            │
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │  OODAEngine          │  │  MemoryManager       │            │
│  │  - execute_iteration()│  │  - organize_context()│            │
│  │  - adaptive_intensity│  │  - tier_management   │            │
│  └──────────────────────┘  └──────────────────────┘            │
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │  WorkingConclusion   │  │  PhaseOrchestrator   │            │
│  │  Generator           │  │  - detect_completion()│            │
│  └──────────────────────┘  └──────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Layer 3: Foundation Layer                     │
│              (Data models, enums, utilities)                    │
│                                                                  │
│  - investigation.py (Pydantic models)                           │
│  - enums.py (All enums)                                         │
│  - evidence_linking.py (Evidence-hypothesis relationships)      │
│  - confidence_calculator.py (Formulas and algorithms)           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Complete Migration Plan (Option A with Clean Structure)

### Phase 1: Foundation Enhancement (Week 1 - Days 1-2)

**Goal:** Upgrade data models and enums to match FaultMaven-Mono

#### Task 1.1: Enhance Pydantic Models (4 hours)

**File:** `src/faultmaven/modules/case/investigation.py`

**Changes:**
1. Add missing fields to `HypothesisModel`:
   ```python
   initial_likelihood: float = Field(...)
   confidence_trajectory: List[Tuple[int, float]] = Field(default_factory=list)
   iterations_without_progress: int = Field(default=0)
   last_progress_at_turn: int = Field(default=0)
   generation_mode: HypothesisGenerationMode = Field(...)
   promoted_to_active_at_turn: Optional[int] = None
   triggering_observation: Optional[str] = None
   ```

2. Add missing fields to `EvidenceItem`:
   ```python
   form: EvidenceForm = Field(...)
   source_type: EvidenceSourceType = Field(...)
   ```

3. Add new models:
   ```python
   class OODAState(BaseModel):
       current_step: OODAStep
       current_iteration: int
       iteration_history: List[OODAIteration]
       adaptive_intensity: str  # "light", "medium", "full"

   class HierarchicalMemory(BaseModel):
       hot_memory: List[str]  # Last 3 turns
       warm_memory: List[str]  # Relevant context
       cold_memory: List[str]  # Archived

   class OODAIteration(BaseModel):
       iteration_id: str
       turn_number: int
       phase: InvestigationPhase
       steps_completed: List[OODAStep]
       made_progress: bool
       outcome: TurnOutcome
   ```

4. Update `InvestigationState` to include:
   ```python
   ooda_state: Optional[OODAState] = None
   memory: HierarchicalMemory = Field(default_factory=HierarchicalMemory)
   ```

**Tests:** `tests/unit/modules/case/test_investigation_models.py` (2 hours)

---

#### Task 1.2: Add Missing Enums (2 hours)

**File:** `src/faultmaven/modules/case/enums.py`

**Add 7 enums:**
```python
class OODAStep(str, Enum):
    OBSERVE = "observe"
    ORIENT = "orient"
    DECIDE = "decide"
    ACT = "act"

class EvidenceForm(str, Enum):
    DIRECT_OBSERVATION = "direct_observation"
    SYMPTOM = "symptom"
    METRIC = "metric"
    LOG_ENTRY = "log_entry"
    CONFIG_VALUE = "config_value"
    TEST_RESULT = "test_result"

class EvidenceSourceType(str, Enum):
    USER_PROVIDED = "user_provided"
    SYSTEM_QUERY = "system_query"
    LOG_ANALYSIS = "log_analysis"
    METRIC_QUERY = "metric_query"
    CODE_INSPECTION = "code_inspection"

class HypothesisGenerationMode(str, Enum):
    OPPORTUNISTIC = "opportunistic"  # Captured from early phases
    SYSTEMATIC = "systematic"  # Generated in hypothesis phase

class HypothesisCategory(str, Enum):
    INFRASTRUCTURE = "infrastructure"
    CODE = "code"
    CONFIGURATION = "configuration"
    DATA = "data"
    EXTERNAL_DEPENDENCY = "external_dependency"
    HUMAN_ERROR = "human_error"

class EngagementMode(str, Enum):
    CONSULTANT = "consultant"
    LEAD_INVESTIGATOR = "lead_investigator"

class TurnOutcome(str, Enum):
    PROGRESS = "progress"  # Milestone completed
    CONVERSATION = "conversation"  # Clarification only
    BLOCKED = "blocked"  # Hit obstacle
    EVIDENCE_COLLECTED = "evidence_collected"
    HYPOTHESIS_VALIDATED = "hypothesis_validated"
    HYPOTHESIS_REFUTED = "hypothesis_refuted"
```

**Tests:** `tests/unit/modules/case/test_enums.py` (1 hour)

**Deliverable:** Enhanced data models matching FaultMaven-Mono structure
**Effort:** 7 hours (1 day)

---

### Phase 2: Core Engines Implementation (Week 1 - Days 3-5)

**Goal:** Implement the 3 critical engines (Milestone, OODA, Hypothesis)

#### Task 2.1: Milestone Engine (2 days)

**New file:** `src/faultmaven/modules/case/engines/milestone_engine.py`

**Port from:** `FaultMaven-Mono/faultmaven/core/investigation/milestone_engine.py` (785 LOC)

**Structure:**
```python
class MilestoneEngine:
    """Main orchestration engine for investigation turns."""

    def __init__(self, llm_provider: ILLMProvider):
        self.llm_provider = llm_provider

    async def process_turn(
        self,
        state: InvestigationState,
        case: Case,
        user_message: str,
        attachments: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Process one investigation turn.

        Returns:
            {
                "agent_response": str,
                "state_updated": InvestigationState,
                "metadata": {
                    "turn_number": int,
                    "milestones_completed": List[str],
                    "progress_made": bool,
                    "outcome": TurnOutcome
                }
            }
        """
        # 1. Generate status-based prompt
        prompt = self._build_prompt(case.status, state, user_message)

        # 2. Invoke LLM
        llm_response = await self.llm_provider.generate(prompt)

        # 3. Process response and extract state updates
        updates = self._extract_state_updates(llm_response)

        # 4. Update state
        updated_state = self._apply_updates(state, updates)

        # 5. Check automatic transitions
        self._check_automatic_transitions(updated_state, case)

        # 6. Record turn
        self._record_turn(updated_state, user_message, llm_response)

        return {
            "agent_response": llm_response.text,
            "state_updated": updated_state,
            "metadata": {...}
        }

    def _build_prompt(
        self,
        case_status: CaseStatus,
        state: InvestigationState,
        user_message: str
    ) -> str:
        """Build status-appropriate prompt."""
        if case_status == CaseStatus.CONSULTING:
            return self._build_consulting_prompt(state, user_message)
        elif case_status == CaseStatus.INVESTIGATING:
            return self._build_investigating_prompt(state, user_message)
        else:
            return self._build_terminal_prompt(state, user_message)

    def _build_consulting_prompt(self, state, user_message) -> str:
        """Consultant mode prompt (Phase 0)."""
        return f"""You are FaultMaven, an AI troubleshooting copilot.
Status: CONSULTING
Turn: {state.current_turn + 1}

User Message: {user_message}

Your Task:
1. Understand the user's problem
2. Ask clarifying questions if needed
3. Propose a clear problem statement
4. Determine if formal investigation is needed

Respond naturally and helpfully."""

    def _build_investigating_prompt(self, state, user_message) -> str:
        """Lead Investigator mode prompt (Phases 1-6)."""
        phase_info = self._get_phase_context(state.current_phase)
        ooda_guidance = self._get_ooda_guidance(state)
        progress_summary = self._get_progress_summary(state)

        return f"""You are FaultMaven, leading this investigation.
Phase: {state.current_phase.name}
Turn: {state.current_turn + 1}
Strategy: {state.strategy.value}

== Phase Objective ==
{phase_info.objective}

== Current Progress ==
{progress_summary}

== OODA Guidance ==
{ooda_guidance}

== User Message ==
{user_message}

== Your Response ==
Provide analysis, request evidence, or propose actions.
"""

    def _extract_state_updates(self, llm_response) -> Dict:
        """Extract structured updates from LLM response."""
        # Parse LLM response for:
        # - Milestones completed
        # - Hypotheses generated/updated
        # - Evidence collected
        # - Phase transitions
        pass

    def _check_automatic_transitions(self, state, case):
        """Check if case should auto-transition status."""
        # INVESTIGATING → RESOLVED when root cause validated
        if state.get_validated_hypothesis():
            case.status = CaseStatus.RESOLVED

        # Check degraded mode
        degraded_type = state.check_degraded_mode()
        if degraded_type:
            self._enter_degraded_mode(state, degraded_type)
```

**Key methods to port:**
1. `process_turn()` - Main entry point (lines 111-236 in FM-Mono)
2. `_build_prompt()` - Status-based dispatch (lines 241-271)
3. `_build_consulting_prompt()` - Phase 0 (lines 272-295)
4. `_build_investigating_prompt()` - Phases 1-6 (lines 297-458)
5. `_process_response()` - State extraction (lines 460-530)
6. `_check_automatic_transitions()` - Auto-advancement (lines 532-580)
7. `_enter_degraded_mode()` - Degradation handling (lines 582-620)

**Tests:** `tests/unit/modules/case/engines/test_milestone_engine.py`
- Test consulting prompt generation
- Test investigating prompt generation
- Test turn processing
- Test automatic transitions
- Test degraded mode detection

**Effort:** 16 hours (2 days)

---

#### Task 2.2: Hypothesis Manager (1.5 days)

**New file:** `src/faultmaven/modules/case/engines/hypothesis_manager.py`

**Port from:** `FaultMaven-Mono/faultmaven/core/investigation/hypothesis_manager.py` (751 LOC)

**Structure:**
```python
class HypothesisManager:
    """Manages hypothesis lifecycle with evidence-based confidence."""

    def create_hypothesis(
        self,
        statement: str,
        category: HypothesisCategory,
        initial_likelihood: float,
        current_turn: int,
        generation_mode: HypothesisGenerationMode,
    ) -> HypothesisModel:
        """Create new hypothesis."""
        return HypothesisModel(
            hypothesis_id=str(uuid.uuid4()),
            statement=statement,
            category=category,
            likelihood=initial_likelihood,
            initial_likelihood=initial_likelihood,
            confidence_trajectory=[(current_turn, initial_likelihood)],
            generation_mode=generation_mode,
            captured_at_turn=current_turn,
            status=HypothesisStatus.CAPTURED if generation_mode == HypothesisGenerationMode.OPPORTUNISTIC else HypothesisStatus.ACTIVE
        )

    def link_evidence(
        self,
        hypothesis: HypothesisModel,
        evidence_id: str,
        supports: bool,
        turn: int
    ) -> None:
        """Link evidence to hypothesis (supporting or refuting)."""
        if supports:
            if evidence_id not in hypothesis.supporting_evidence:
                hypothesis.supporting_evidence.append(evidence_id)
        else:
            if evidence_id not in hypothesis.refuting_evidence:
                hypothesis.refuting_evidence.append(evidence_id)

        # Update confidence after linking
        self.update_confidence(hypothesis, turn)

    def update_confidence(
        self,
        hypothesis: HypothesisModel,
        current_turn: int
    ) -> float:
        """Calculate confidence based on evidence ratio.

        Formula:
            confidence = initial + (0.15 × supporting) - (0.20 × refuting)

        Bounds: [0.0, 1.0]
        """
        supporting_count = len(hypothesis.supporting_evidence)
        refuting_count = len(hypothesis.refuting_evidence)

        evidence_adjustment = (0.15 * supporting_count) - (0.20 * refuting_count)
        new_confidence = hypothesis.initial_likelihood + evidence_adjustment

        # Clamp to [0.0, 1.0]
        new_confidence = max(0.0, min(1.0, new_confidence))

        # Record in trajectory
        hypothesis.confidence_trajectory.append((current_turn, new_confidence))
        hypothesis.likelihood = new_confidence

        # Check for auto-transition
        self._check_auto_transition(hypothesis, current_turn)

        return new_confidence

    def apply_confidence_decay(
        self,
        hypothesis: HypothesisModel,
        current_turn: int
    ) -> float:
        """Apply decay for stagnation.

        Formula:
            confidence = base × 0.85^iterations_without_progress
        """
        if hypothesis.iterations_without_progress > 0:
            decay_factor = 0.85 ** hypothesis.iterations_without_progress
            new_confidence = hypothesis.likelihood * decay_factor
            hypothesis.likelihood = new_confidence
            hypothesis.confidence_trajectory.append((current_turn, new_confidence))
            return new_confidence
        return hypothesis.likelihood

    def _check_auto_transition(
        self,
        hypothesis: HypothesisModel,
        turn: int
    ) -> None:
        """Auto-transition to VALIDATED or REFUTED."""
        # VALIDATED: confidence ≥ 0.7 AND ≥ 2 supporting evidence
        if (hypothesis.likelihood >= 0.7 and
            len(hypothesis.supporting_evidence) >= 2):
            hypothesis.status = HypothesisStatus.VALIDATED
            hypothesis.validated_at_turn = turn

        # REFUTED: confidence ≤ 0.2 AND ≥ 2 refuting evidence
        elif (hypothesis.likelihood <= 0.2 and
              len(hypothesis.refuting_evidence) >= 2):
            hypothesis.status = HypothesisStatus.REFUTED
            hypothesis.validated_at_turn = turn

    def detect_anchoring(
        self,
        hypotheses: List[HypothesisModel]
    ) -> Optional[str]:
        """Detect anchoring bias patterns.

        Patterns:
        1. 4+ hypotheses in same category
        2. 3+ iterations without progress
        3. Top hypothesis stagnant for 3+ iterations

        Returns: Warning message if detected
        """
        # Pattern 1: Category clustering
        category_counts = {}
        for h in hypotheses:
            if h.status not in [HypothesisStatus.RETIRED, HypothesisStatus.REFUTED]:
                cat = h.category.value
                category_counts[cat] = category_counts.get(cat, 0) + 1

        for category, count in category_counts.items():
            if count >= 4:
                return f"Anchoring detected: {count} hypotheses in '{category}' category"

        # Pattern 2: Stagnation
        stalled = [h for h in hypotheses
                   if h.iterations_without_progress >= 3
                   and h.status == HypothesisStatus.ACTIVE]
        if stalled:
            return f"Anchoring detected: {len(stalled)} hypotheses without progress"

        return None

    def retire_stalled_hypotheses(
        self,
        hypotheses: List[HypothesisModel],
        turn: int
    ) -> List[str]:
        """Retire hypotheses with no progress for 3+ iterations."""
        retired_ids = []
        for h in hypotheses:
            if (h.status == HypothesisStatus.ACTIVE and
                h.iterations_without_progress >= 3):
                h.status = HypothesisStatus.RETIRED
                h.validated_at_turn = turn
                retired_ids.append(h.hypothesis_id)
        return retired_ids
```

**Key methods to port:**
1. `create_hypothesis()` - Lines 68-119
2. `link_evidence()` - Lines 121-160
3. `update_confidence()` - Lines 162-220
4. `apply_confidence_decay()` - Lines 222-260
5. `detect_anchoring()` - Lines 392-450
6. `retire_stalled_hypotheses()` - Lines 452-480

**Tests:** `tests/unit/modules/case/engines/test_hypothesis_manager.py`
- Test confidence calculation formula
- Test confidence decay
- Test auto-transition thresholds
- Test anchoring detection
- Test evidence linking

**Effort:** 12 hours (1.5 days)

---

#### Task 2.3: OODA Engine (1 day)

**New file:** `src/faultmaven/modules/case/engines/ooda_engine.py`

**Port from:** `FaultMaven-Mono/faultmaven/core/investigation/ooda_engine.py` (534 LOC)

**Structure:**
```python
class OODAEngine:
    """OODA loop execution and adaptive intensity control."""

    def execute_iteration(
        self,
        state: InvestigationState,
        phase: InvestigationPhase
    ) -> OODAIteration:
        """Execute one OODA iteration within a phase."""
        iteration = OODAIteration(
            iteration_id=str(uuid.uuid4()),
            turn_number=state.current_turn,
            phase=phase,
            steps_completed=[],
            made_progress=False,
            outcome=TurnOutcome.CONVERSATION
        )

        # Determine intensity
        intensity = self.get_adaptive_intensity(
            state.ooda_state.current_iteration,
            phase
        )

        # Determine current OODA step
        current_step = self._determine_ooda_step(
            phase,
            state.ooda_state.current_iteration
        )

        state.ooda_state.current_step = current_step
        iteration.steps_completed.append(current_step)

        # Check anchoring prevention
        should_intervene, reason = self.should_trigger_anchoring_prevention(
            state.ooda_state.current_iteration,
            state.hypotheses
        )

        if should_intervene:
            # Force alternative generation
            state.progress.next_steps.append(
                "ANCHORING INTERVENTION: Generate alternative hypotheses"
            )

        return iteration

    @staticmethod
    def get_adaptive_intensity(
        iteration_count: int,
        phase: InvestigationPhase
    ) -> str:
        """Determine investigation intensity.

        Levels:
        - Light: 1-2 iterations (simple problems)
        - Medium: 3-5 iterations (typical)
        - Full: 6+ iterations (complex, enable anchoring prevention)
        """
        if phase == InvestigationPhase.INTAKE:
            return "none"

        if phase in [InvestigationPhase.BLAST_RADIUS, InvestigationPhase.TIMELINE]:
            return "light"

        if phase == InvestigationPhase.HYPOTHESIS:
            return "light" if iteration_count <= 2 else "medium"

        if phase == InvestigationPhase.VALIDATION:
            if iteration_count <= 2:
                return "medium"
            return "full"

        if phase == InvestigationPhase.SOLUTION:
            return "medium"

        if phase == InvestigationPhase.DOCUMENT:
            return "light"

        return "medium"

    @staticmethod
    def should_trigger_anchoring_prevention(
        iteration_count: int,
        hypotheses: List[HypothesisModel]
    ) -> Tuple[bool, Optional[str]]:
        """Check if anchoring prevention should trigger."""
        if iteration_count < 3:
            return False, None

        # Check via HypothesisManager
        manager = HypothesisManager()
        warning = manager.detect_anchoring(hypotheses)

        if warning:
            return True, warning

        return False, None

    def _determine_ooda_step(
        self,
        phase: InvestigationPhase,
        iteration: int
    ) -> OODAStep:
        """Map phase and iteration to OODA step."""
        # Phase-specific OODA mappings
        if phase == InvestigationPhase.BLAST_RADIUS:
            # Observation-heavy phase
            return OODAStep.OBSERVE if iteration == 0 else OODAStep.ORIENT

        elif phase == InvestigationPhase.HYPOTHESIS:
            # Orient-Decide phase
            return OODAStep.ORIENT if iteration == 0 else OODAStep.DECIDE

        elif phase == InvestigationPhase.VALIDATION:
            # Full OODA cycle
            cycle_position = iteration % 4
            return [OODAStep.OBSERVE, OODAStep.ORIENT, OODAStep.DECIDE, OODAStep.ACT][cycle_position]

        elif phase == InvestigationPhase.SOLUTION:
            # Act-heavy phase
            return OODAStep.ACT

        else:
            return OODAStep.OBSERVE
```

**Key methods to port:**
1. `get_adaptive_intensity()` - Lines 58-98
2. `should_trigger_anchoring_prevention()` - Lines 100-150
3. `execute_iteration()` - Lines 200-280
4. `_determine_ooda_step()` - Lines 320-380

**Tests:** `tests/unit/modules/case/engines/test_ooda_engine.py`
- Test intensity determination
- Test anchoring detection
- Test OODA step mapping
- Test iteration execution

**Effort:** 8 hours (1 day)

**Phase 2 Deliverable:** 3 core engines implemented
**Total Effort:** 36 hours (4.5 days, round to 5)

---

### Phase 3: Supporting Engines (Week 2 - Days 1-3)

#### Task 3.1: Memory Manager (1 day)

**New file:** `src/faultmaven/modules/case/engines/memory_manager.py`

**Port from:** `FaultMaven-Mono/faultmaven/core/investigation/memory_manager.py` (590 LOC)

**Structure:**
```python
class MemoryManager:
    """Hierarchical memory management for token optimization."""

    def organize_context(
        self,
        state: InvestigationState,
        conversation_history: List[Dict]
    ) -> HierarchicalMemory:
        """Organize context into hot/warm/cold tiers."""
        memory = HierarchicalMemory()

        # Hot memory: Last 3 turns
        recent_turns = state.turn_history[-3:]
        memory.hot_memory = [
            f"Turn {t.turn_number}: {t.user_input_summary} → {t.agent_action_summary}"
            for t in recent_turns
        ]

        # Warm memory: Active hypotheses + recent evidence
        active_hyps = state.get_active_hypotheses()
        memory.warm_memory = [
            f"Hypothesis: {h.statement} (confidence: {h.likelihood:.2f})"
            for h in active_hyps
        ]

        recent_evidence = [e for e in state.evidence if e.collected_at_turn >= state.current_turn - 5]
        memory.warm_memory.extend([
            f"Evidence: {e.description}"
            for e in recent_evidence
        ])

        # Cold memory: Older context (archived)
        old_turns = state.turn_history[:-3]
        memory.cold_memory = [
            f"Turn {t.turn_number} summary"
            for t in old_turns
        ]

        return memory

    def get_hot_memory(self, memory: HierarchicalMemory) -> str:
        """Get hot memory for prompt (always included)."""
        return "\n".join(memory.hot_memory)

    def get_warm_memory(self, memory: HierarchicalMemory, max_tokens: int = 2000) -> str:
        """Get warm memory for prompt (token-limited)."""
        # Estimate tokens and truncate if needed
        content = "\n".join(memory.warm_memory)
        # Simple token estimation: ~4 chars per token
        estimated_tokens = len(content) / 4
        if estimated_tokens > max_tokens:
            # Truncate to fit
            char_limit = max_tokens * 4
            content = content[:char_limit] + "..."
        return content

    def prune_cold_memory(self, memory: HierarchicalMemory, keep_count: int = 20) -> None:
        """Prune cold memory to keep only recent items."""
        if len(memory.cold_memory) > keep_count:
            memory.cold_memory = memory.cold_memory[-keep_count:]
```

**Tests:** `tests/unit/modules/case/engines/test_memory_manager.py`

**Effort:** 8 hours

---

#### Task 3.2: Working Conclusion Generator (1 day)

**New file:** `src/faultmaven/modules/case/engines/working_conclusion_generator.py`

**Port from:** `FaultMaven-Mono/faultmaven/core/investigation/working_conclusion_generator.py` (494 LOC)

**Structure:**
```python
class WorkingConclusionGenerator:
    """Generate interim conclusions based on current evidence."""

    def generate_conclusion(
        self,
        state: InvestigationState
    ) -> Optional[WorkingConclusion]:
        """Generate working conclusion from current state."""
        # Find highest-confidence hypothesis
        if not state.hypotheses:
            return None

        sorted_hyps = sorted(
            state.hypotheses,
            key=lambda h: h.likelihood,
            reverse=True
        )
        top_hypothesis = sorted_hyps[0]

        # Calculate overall confidence
        confidence = self._assess_confidence(state, top_hypothesis)

        # Identify gaps
        gaps = self._identify_gaps(state)

        # Check if can proceed with solution
        can_proceed = (
            confidence >= 0.7 and
            len(top_hypothesis.supporting_evidence) >= 2 and
            len(gaps) == 0
        )

        return WorkingConclusion(
            statement=top_hypothesis.statement,
            confidence=confidence,
            confidence_level=self._map_confidence_level(confidence),
            supporting_evidence_count=len(top_hypothesis.supporting_evidence),
            caveats=self._generate_caveats(top_hypothesis, state),
            alternative_explanations=[
                h.statement for h in sorted_hyps[1:4]
                if h.status not in [HypothesisStatus.REFUTED, HypothesisStatus.RETIRED]
            ],
            can_proceed_with_solution=can_proceed,
            next_evidence_needed=gaps
        )

    def _assess_confidence(
        self,
        state: InvestigationState,
        hypothesis: HypothesisModel
    ) -> float:
        """Assess overall confidence in conclusion."""
        # Base confidence from hypothesis
        base = hypothesis.likelihood

        # Penalty for missing evidence
        missing_penalty = len(self._identify_gaps(state)) * 0.1

        # Bonus for multiple supporting evidence
        evidence_bonus = min(0.1, len(hypothesis.supporting_evidence) * 0.03)

        return max(0.0, min(1.0, base - missing_penalty + evidence_bonus))

    def _identify_gaps(self, state: InvestigationState) -> List[str]:
        """Identify missing evidence."""
        gaps = []

        # Check milestone completion
        if "timeline_established" not in state.progress.completed_milestones:
            gaps.append("Timeline not fully established")

        if "scope_assessed" not in state.progress.completed_milestones:
            gaps.append("Impact scope not assessed")

        # Check evidence categories
        evidence_categories = {e.category for e in state.evidence}
        if EvidenceCategory.LOGS not in evidence_categories:
            gaps.append("No log evidence collected")

        if EvidenceCategory.METRICS not in evidence_categories:
            gaps.append("No metric evidence collected")

        return gaps

    def should_suggest_closure(self, state: InvestigationState) -> bool:
        """Determine if investigation can be closed."""
        conclusion = self.generate_conclusion(state)

        if not conclusion:
            return False

        return (
            conclusion.can_proceed_with_solution and
            conclusion.confidence >= 0.8 and
            len(conclusion.next_evidence_needed) == 0
        )
```

**Tests:** `tests/unit/modules/case/engines/test_working_conclusion_generator.py`

**Effort:** 8 hours

---

#### Task 3.3: Phase Orchestrator (1 day)

**New file:** `src/faultmaven/modules/case/engines/phase_orchestrator.py`

**Port from:**
- `FaultMaven-Mono/faultmaven/core/investigation/phase_loopback.py` (424 LOC)
- `FaultMaven-Mono/faultmaven/core/investigation/workflow_progression_detector.py` (258 LOC)

**Structure:**
```python
class PhaseOrchestrator:
    """Manages phase progression and loopback."""

    def detect_phase_completion(
        self,
        state: InvestigationState
    ) -> bool:
        """Detect if current phase is complete."""
        phase = state.current_phase

        if phase == InvestigationPhase.INTAKE:
            # Complete when problem statement confirmed
            return (
                state.anomaly_frame is not None and
                state.anomaly_frame.confidence >= 0.7
            )

        elif phase == InvestigationPhase.BLAST_RADIUS:
            # Complete when scope assessed
            return "scope_assessed" in state.progress.completed_milestones

        elif phase == InvestigationPhase.TIMELINE:
            # Complete when timeline established
            return (
                state.temporal_frame is not None and
                state.temporal_frame.completeness >= 0.7
            )

        elif phase == InvestigationPhase.HYPOTHESIS:
            # Complete when ≥ 3 hypotheses generated
            return len(state.hypotheses) >= 3

        elif phase == InvestigationPhase.VALIDATION:
            # Complete when root cause validated
            return state.get_validated_hypothesis() is not None

        elif phase == InvestigationPhase.SOLUTION:
            # Complete when solution verified
            return "solution_verified" in state.progress.completed_milestones

        else:
            return False

    def should_loop_back(
        self,
        state: InvestigationState
    ) -> Tuple[bool, Optional[str]]:
        """Determine if should iterate within phase vs advance."""
        phase = state.current_phase

        # Check iteration limit (max 5 per phase)
        phase_iterations = sum(
            1 for t in state.turn_history
            if t.phase == phase
        )
        if phase_iterations >= 5:
            return False, "Max iterations reached"

        # Check if prerequisites met
        if phase == InvestigationPhase.VALIDATION:
            if len(state.hypotheses) == 0:
                return True, "Need hypotheses before testing"

        # Check evidence sufficiency
        if phase == InvestigationPhase.HYPOTHESIS:
            if len(state.evidence) < 3:
                return True, "Need more evidence before hypothesizing"

        return False, None

    def suggest_phase_transition(
        self,
        state: InvestigationState
    ) -> Optional[InvestigationPhase]:
        """Suggest next phase if current is complete."""
        if self.detect_phase_completion(state):
            current = state.current_phase
            # Sequential progression
            next_phases = {
                InvestigationPhase.INTAKE: InvestigationPhase.BLAST_RADIUS,
                InvestigationPhase.BLAST_RADIUS: InvestigationPhase.TIMELINE,
                InvestigationPhase.TIMELINE: InvestigationPhase.HYPOTHESIS,
                InvestigationPhase.HYPOTHESIS: InvestigationPhase.VALIDATION,
                InvestigationPhase.VALIDATION: InvestigationPhase.SOLUTION,
                InvestigationPhase.SOLUTION: InvestigationPhase.DOCUMENT,
            }
            return next_phases.get(current)
        return None
```

**Tests:** `tests/unit/modules/case/engines/test_phase_orchestrator.py`

**Effort:** 8 hours

**Phase 3 Deliverable:** 3 supporting engines
**Total Effort:** 24 hours (3 days)

---

### Phase 4: Service Layer Integration (Week 2 - Days 4-5)

**Goal:** Wire engines into InvestigationService with clean API

#### Task 4.1: Refactor InvestigationService (1.5 days)

**File:** `src/faultmaven/modules/case/investigation_service.py`

**Changes:**
```python
class InvestigationService:
    """Service layer orchestrating investigation engines."""

    def __init__(
        self,
        case_service: CaseService,
        llm_provider: ILLMProvider
    ):
        self.case_service = case_service

        # Initialize engines
        self.milestone_engine = MilestoneEngine(llm_provider)
        self.hypothesis_manager = HypothesisManager()
        self.ooda_engine = OODAEngine()
        self.memory_manager = MemoryManager()
        self.conclusion_generator = WorkingConclusionGenerator()
        self.phase_orchestrator = PhaseOrchestrator()

    async def process_turn(
        self,
        case_id: str,
        user_id: str,
        user_message: str,
        attachments: Optional[List[Dict]] = None
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """Process one investigation turn (main entry point).

        This replaces the old advance_turn() method with full orchestration.

        Returns:
            Tuple of (result_dict, error_message)
            result_dict = {
                "agent_response": str,
                "case_updated": Case,
                "investigation_state": InvestigationState,
                "metadata": {...}
            }
        """
        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return None, "Case not found"

        state = await self.get_investigation_state(case_id, user_id)
        if not state:
            return None, "Investigation not initialized"

        # Process turn through milestone engine
        result = await self.milestone_engine.process_turn(
            state=state,
            case=case,
            user_message=user_message,
            attachments=attachments
        )

        # Update state in DB
        case.case_metadata[self.INVESTIGATION_KEY] = result["state_updated"].to_dict()
        case.updated_at = datetime.utcnow()
        await self.case_service.db.commit()
        await self.case_service.db.refresh(case)

        return {
            "agent_response": result["agent_response"],
            "case_updated": case,
            "investigation_state": result["state_updated"],
            "metadata": result["metadata"]
        }, None

    async def add_hypothesis(
        self,
        case_id: str,
        user_id: str,
        statement: str,
        category: HypothesisCategory,
        generation_mode: HypothesisGenerationMode,
        likelihood: float = 0.5
    ) -> Tuple[Optional[InvestigationState], Optional[str]]:
        """Add hypothesis using HypothesisManager."""
        case = await self.case_service.get_case(case_id, user_id)
        if not case:
            return None, "Case not found"

        state = await self.get_investigation_state(case_id, user_id)
        if not state:
            return None, "Investigation not initialized"

        # Use hypothesis manager
        hypothesis = self.hypothesis_manager.create_hypothesis(
            statement=statement,
            category=category,
            initial_likelihood=likelihood,
            current_turn=state.current_turn,
            generation_mode=generation_mode
        )

        state.hypotheses.append(hypothesis)

        # Update DB
        case.case_metadata[self.INVESTIGATION_KEY] = state.to_dict()
        await self.case_service.db.commit()

        return state, None

    async def link_evidence_to_hypothesis(
        self,
        case_id: str,
        user_id: str,
        hypothesis_id: str,
        evidence_id: str,
        supports: bool
    ) -> Tuple[Optional[InvestigationState], Optional[str]]:
        """Link evidence using HypothesisManager."""
        state = await self.get_investigation_state(case_id, user_id)
        if not state:
            return None, "Investigation not initialized"

        # Find hypothesis
        hypothesis = next(
            (h for h in state.hypotheses if h.hypothesis_id == hypothesis_id),
            None
        )
        if not hypothesis:
            return None, "Hypothesis not found"

        # Link evidence and update confidence
        self.hypothesis_manager.link_evidence(
            hypothesis=hypothesis,
            evidence_id=evidence_id,
            supports=supports,
            turn=state.current_turn
        )

        # Save
        case = await self.case_service.get_case(case_id, user_id)
        case.case_metadata[self.INVESTIGATION_KEY] = state.to_dict()
        await self.case_service.db.commit()

        return state, None

    async def generate_working_conclusion(
        self,
        case_id: str,
        user_id: str
    ) -> Tuple[Optional[WorkingConclusion], Optional[str]]:
        """Generate working conclusion using ConclusionGenerator."""
        state = await self.get_investigation_state(case_id, user_id)
        if not state:
            return None, "Investigation not initialized"

        conclusion = self.conclusion_generator.generate_conclusion(state)

        if conclusion:
            # Update state
            state.working_conclusion = conclusion
            case = await self.case_service.get_case(case_id, user_id)
            case.case_metadata[self.INVESTIGATION_KEY] = state.to_dict()
            await self.case_service.db.commit()

        return conclusion, None
```

**Remove old methods:**
- ❌ `advance_turn()` → Replaced by `process_turn()`
- ❌ `update_hypothesis_status()` → Handled by HypothesisManager
- ❌ `update_working_conclusion()` → Handled by ConclusionGenerator

**Keep methods:**
- ✅ `initialize_investigation()`
- ✅ `get_investigation_state()`
- ✅ `_determine_strategy()`

**Tests:** Update all integration tests to use new API

**Effort:** 12 hours

---

#### Task 4.2: Update Integration Tests (0.5 days)

**File:** `tests/integration/modules/case/test_investigation_lifecycle.py`

**Updates:**
- Replace `advance_turn()` calls with `process_turn()`
- Add tests for evidence linking
- Add tests for working conclusion generation
- Add tests for phase progression

**Effort:** 4 hours

**Phase 4 Deliverable:** Clean service layer integration
**Total Effort:** 16 hours (2 days)

---

### Phase 5: Testing & Documentation (Week 3 - Days 1-2)

#### Task 5.1: Comprehensive Testing (1 day)

**Unit tests:**
- ✅ All engine unit tests (from Phases 2-3)
- ✅ Model validation tests
- ✅ Enum tests

**Integration tests:**
- Test complete investigation lifecycle
- Test CONSULTING → INVESTIGATING → RESOLVED flow
- Test hypothesis confidence updates
- Test anchoring prevention
- Test degraded mode detection
- Test automatic phase progression

**Performance tests:**
- Test memory management under load
- Test prompt generation performance
- Test state serialization/deserialization

**Effort:** 8 hours

---

#### Task 5.2: Documentation (1 day)

**Documents to create:**
1. `docs/investigation/ARCHITECTURE.md` - System architecture
2. `docs/investigation/ENGINES.md` - Engine documentation
3. `docs/investigation/HYPOTHESIS_CONFIDENCE.md` - Confidence algorithm
4. `docs/investigation/PHASE_PROGRESSION.md` - Phase lifecycle
5. Update `docs/API.md` with new investigation endpoints

**Code documentation:**
- Docstrings for all engines
- Examples in docstrings
- Architecture diagrams (Mermaid)

**Effort:** 8 hours

**Phase 5 Deliverable:** Complete testing and documentation
**Total Effort:** 16 hours (2 days)

---

## Implementation Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| **Phase 1: Foundation Enhancement** | 1 day | Enhanced models + enums |
| **Phase 2: Core Engines** | 5 days | Milestone, OODA, Hypothesis engines |
| **Phase 3: Supporting Engines** | 3 days | Memory, Conclusion, Phase engines |
| **Phase 4: Service Integration** | 2 days | Refactored service layer |
| **Phase 5: Testing & Docs** | 2 days | Complete test coverage + docs |
| **Buffer** | 2 days | Bug fixes, refinement |
| **TOTAL** | **15 days (3 weeks)** | **Complete investigation framework** |

---

## Success Criteria

**Must have (MVP):**
- ✅ All 6 engines implemented and tested
- ✅ Evidence-based hypothesis confidence
- ✅ Anchoring prevention
- ✅ OODA loop execution
- ✅ Milestone tracking
- ✅ Working conclusion generation
- ✅ Phase progression detection
- ✅ 80%+ test coverage

**Should have:**
- Memory management optimization
- Performance benchmarks
- Comprehensive documentation

**Nice to have:**
- Visualization of hypothesis confidence trajectory
- Investigation replay functionality
- Advanced analytics

---

## Migration Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **LLM integration complexity** | Medium | High | Use provider abstraction, extensive mocking in tests |
| **State serialization issues** | Low | Medium | Thorough Pydantic validation, migration tests |
| **Performance regression** | Low | Medium | Benchmark before/after, optimize hot paths |
| **Breaking API changes** | Low | Low | Maintain backwards compatibility layer |
| **Timeline overrun** | Medium | Medium | 2-day buffer built in, incremental delivery |

---

## Next Steps

1. **Immediate:** Review this specification with team
2. **Day 1:** Start Phase 1 (foundation enhancement)
3. **Daily:** Commit incremental progress
4. **Weekly:** Demo working engines
5. **Week 3:** Complete implementation and testing

**Status:** Ready to implement
**Approval needed:** Confirm priority and timeline with product team
