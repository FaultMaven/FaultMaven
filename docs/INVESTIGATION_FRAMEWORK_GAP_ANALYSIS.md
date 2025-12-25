# Investigation Framework Gap Analysis

**Status:** CRITICAL - 70% of investigation framework not migrated
**Created:** 2025-12-25
**Related:** PR #20, MONOLITH_EVOLUTION_PLAN.md (Phase 4)

---

## Executive Summary

PR #20 successfully migrated **~30% of the investigation framework** from FaultMaven-Mono to faultmaven. However, **~70% of sophisticated investigation logic remains unmigrated**, representing approximately **6,069 lines of code** across 13 modules.

The current implementation provides:
- ✅ Basic investigation state models
- ✅ Simple investigation lifecycle (initialize, advance turn, add hypothesis)
- ✅ Status transitions (CONSULTING → INVESTIGATING → RESOLVED)
- ✅ Report generation

**What's missing:**
- ❌ Milestone-based investigation engine (785 LOC)
- ❌ OODA loop orchestration (534 LOC)
- ❌ Hypothesis confidence management (751 LOC)
- ❌ Adaptive intensity control
- ❌ Anchoring prevention system
- ❌ Phase loopback and iteration strategies (424 LOC)
- ❌ Workflow progression detection (258 LOC)
- ❌ Memory manager for hierarchical context (590 LOC)
- ❌ Working conclusion generator (494 LOC)
- ❌ Engagement modes (573 LOC)

---

## OpenAPI Generation Analysis

### FaultMaven-Mono Implementation

Found **two comprehensive scripts** for API documentation:

1. **`scripts/generate_openapi_spec.py`** (320 LOC) - Already ported to faultmaven
   - Generates openapi.current.yaml
   - Compares with openapi.locked.yaml baseline
   - Detects breaking vs non-breaking changes
   - Status: ✅ **Already implemented in faultmaven**

2. **`scripts/generate_api_docs.py`** (915 LOC) - **NOT ported yet**
   - Enhanced OpenAPI schema with comprehensive examples
   - Multiple output formats (JSON, YAML, Markdown)
   - Real usage examples for all endpoints
   - Error response documentation
   - Security schemas (placeholders for future auth)
   - Tags and external documentation links
   - Generates `/docs/api/README.md` from OpenAPI schema

### Recommendation for OpenAPI

**Option A (Recommended):** Port `generate_api_docs.py` to faultmaven
- Provides richer API documentation than basic spec
- Includes comprehensive examples for all endpoints
- Generates markdown documentation automatically
- Better developer experience

**Option B:** Enhance existing `generate_openapi_spec.py`
- Keep current implementation
- Add examples and enhanced schemas incrementally
- Less comprehensive but simpler

**Decision needed:** Which approach to take?

---

## Investigation Framework Architecture (FaultMaven-Mono)

### Core Components (6,069 Total Lines)

| Component | LOC | Status | Description |
|-----------|-----|--------|-------------|
| **milestone_engine.py** | 785 | ❌ Not migrated | Main orchestration engine, replaces rigid OODA phases |
| **hypothesis_manager.py** | 751 | ⚠️ Partial (basic CRUD only) | Full hypothesis lifecycle, confidence management, evidence linking |
| **ooda_engine.py** | 534 | ❌ Not migrated | OODA loop execution (Observe-Orient-Decide-Act) |
| **memory_manager.py** | 590 | ❌ Not migrated | Hierarchical working memory, conversation context |
| **engagement_modes.py** | 573 | ❌ Not migrated | Different investigation modes (consulting, investigating, reviewing) |
| **phases.py** | 519 | ⚠️ Partial (enums only) | Phase definitions, objectives, OODA step mappings |
| **working_conclusion_generator.py** | 494 | ❌ Not migrated | Conclusion synthesis, progress metrics |
| **strategy_selector.py** | 461 | ⚠️ Partial (basic logic) | Investigation strategy selection (mitigation vs root cause) |
| **phase_loopback.py** | 424 | ❌ Not migrated | Phase iteration strategies, when to loop back |
| **workflow_progression_detector.py** | 258 | ❌ Not migrated | Automatic phase transition detection |
| **ooda_step_extraction.py** | 217 | ❌ Not migrated | Extract OODA steps from LLM responses |
| **iteration_strategy.py** | 195 | ❌ Not migrated | Iteration planning and control |
| **investigation_coordinator.py** | 194 | ❌ Not migrated | Multi-system conflict resolution |
| **\_\_init\_\_.py** | 74 | ✅ Migrated | Module exports |

**Total Migration Status:**
- ✅ **Fully Migrated:** ~500 LOC (8%)
- ⚠️ **Partially Migrated:** ~1,500 LOC (25%)
- ❌ **Not Migrated:** ~4,069 LOC (67%)

---

## Detailed Component Analysis

### 1. Milestone Engine (785 LOC) - **CRITICAL**

**Purpose:** Replaces rigid phase-based investigation with opportunistic milestone completion.

**Key Design Principles:**
```python
# From milestone_engine.py:23
"""
Key Differences from OODA:
- NO phase transitions - milestones complete when data is available
- NO sequential constraints - multiple milestones can complete in one turn
- Status-based prompt generation instead of phase-based
- Progress tracked via InvestigationProgress, not phase transitions
"""
```

**What it does:**
1. **Status-based prompts** (CONSULTING, INVESTIGATING, RESOLVED)
   - `_build_consulting_prompt()` - Problem understanding
   - `_build_investigating_prompt()` - Milestone-based investigation
   - `_build_terminal_prompt()` - Documentation and retrospective

2. **Turn processing:**
   - Generates appropriate prompt based on case status
   - Invokes LLM with structured output
   - Processes response and updates case state
   - Tracks milestone completion
   - Records turn progress
   - Checks for automatic status transitions

3. **Progress tracking:**
   - `turns_without_progress` counter
   - Degraded mode detection (3+ turns without progress)
   - Automatic status transitions when milestones complete

**Current faultmaven implementation:**
- ✅ Has basic turn advancement in `investigation_service.py`
- ❌ Missing: Status-based prompt generation
- ❌ Missing: Milestone completion tracking
- ❌ Missing: Automatic degraded mode detection
- ❌ Missing: Turn outcome classification

**Migration complexity:** HIGH
- Requires: LLM provider integration
- Requires: Prompt template system
- Requires: Repository abstraction layer
- Effort estimate: 3-4 days

---

### 2. Hypothesis Manager (751 LOC) - **CRITICAL**

**Purpose:** Complete hypothesis lifecycle management with confidence calculation.

**Current faultmaven:**
```python
# src/faultmaven/modules/case/investigation_service.py
async def add_hypothesis(...) -> Tuple[Optional[InvestigationState], Optional[str]]:
    """Add hypothesis during investigation."""
    # Basic CRUD only - create hypothesis, add to list, save
```

**FaultMaven-Mono implementation:**
```python
# faultmaven/core/investigation/hypothesis_manager.py
class HypothesisManager:
    """Unified hypothesis lifecycle and confidence management

    Responsibilities:
    - Create new hypotheses (CAPTURED or ACTIVE)
    - Update confidence based on evidence
    - Apply confidence decay for stagnation
    - Detect and prevent anchoring bias
    - Track hypothesis testing
    - Auto-transition status (VALIDATED/REFUTED)
    - Evidence linking and ratio calculation
    """
```

**Key features missing from faultmaven:**

1. **Evidence-based confidence calculation:**
   ```python
   # Confidence formula:
   # confidence = initial + (0.15 × supporting_evidence) - (0.20 × refuting_evidence)
   ```

2. **Confidence decay for stagnation:**
   ```python
   # Decay formula:
   # confidence = base × 0.85^iterations_without_progress
   ```

3. **Auto-transition based on thresholds:**
   - `confidence ≥ 0.7` + `≥2 supporting evidence` → VALIDATED
   - `confidence ≤ 0.2` + `≥2 refuting evidence` → REFUTED

4. **Anchoring prevention:**
   - Detect: 4+ hypotheses in same category
   - Detect: 3+ iterations without progress
   - Action: Retire low-progress hypotheses, force alternatives

5. **Hypothesis lifecycle states:**
   - CAPTURED (opportunistic from early phases)
   - ACTIVE (currently being tested)
   - VALIDATED (confirmed by evidence)
   - REFUTED (disproved by evidence)
   - RETIRED (abandoned)
   - SUPERSEDED (better hypothesis found)

**Migration complexity:** MEDIUM-HIGH
- Requires: Evidence linking system
- Requires: Confidence calculation engine
- Requires: Stagnation detection
- Effort estimate: 2-3 days

---

### 3. OODA Engine (534 LOC) - **HIGH PRIORITY**

**Purpose:** Tactical execution manager for Observe-Orient-Decide-Act cycles.

**Architecture:**
```python
# From ooda_engine.py:9
"""
OODA Framework:
- Observe: Gather information and evidence (generate evidence requests)
- Orient: Analyze and contextualize data (process evidence, update hypotheses)
- Decide: Choose action or hypothesis (select test, prioritize)
- Act: Execute test or apply solution (verify, implement)

Adaptive Intensity:
- 1-2 iterations: Light intensity (simple problems)
- 3-5 iterations: Medium intensity (typical investigations)
- 6+ iterations: Full intensity (complex root causes)
"""
```

**Key components:**

1. **AdaptiveIntensityController:**
   - Adjusts investigation thoroughness based on iteration count
   - Light → Medium → Full intensity progression
   - Triggers anchoring prevention at full intensity

2. **OODA iteration management:**
   - Tracks which OODA step is current
   - Records iteration history
   - Detects stagnation

3. **Phase-specific OODA steps:**
   - Different OODA steps for different investigation phases
   - Maps phases to appropriate observation/action strategies

**Current faultmaven:**
- ❌ No OODA implementation at all
- Uses simple turn-based advancement without OODA structure

**Migration complexity:** HIGH
- Requires: Phase definitions
- Requires: OODA step extraction from LLM responses
- Requires: Iteration tracking
- Effort estimate: 3-4 days

---

### 4. Memory Manager (590 LOC) - **MEDIUM PRIORITY**

**Purpose:** Hierarchical working memory for conversation context.

**What it manages:**
- Conversation history with semantic chunking
- Evidence hierarchy (categorized by type)
- Hypothesis relationships
- Phase-specific context
- Working conclusions

**Current faultmaven:**
- ❌ No memory management beyond flat message list
- Case has `messages` field but no semantic organization

**Migration complexity:** MEDIUM
- Requires: Conversation chunking logic
- Requires: Context window management
- Effort estimate: 2 days

---

### 5. Working Conclusion Generator (494 LOC) - **MEDIUM PRIORITY**

**Purpose:** Synthesize current understanding and progress metrics.

**Features:**
- Generates interim conclusions based on evidence
- Tracks progress metrics
- Suggests when to advance phase or close investigation
- Provides confidence levels for conclusions

**Current faultmaven:**
- ❌ No working conclusion generation
- Report generation is final only, not interim

**Migration complexity:** MEDIUM
- Requires: Evidence synthesis
- Requires: Progress metric calculation
- Effort estimate: 2 days

---

### 6. Phase Loopback (424 LOC) - **LOW-MEDIUM PRIORITY**

**Purpose:** Determine when to iterate within a phase vs advance.

**Features:**
- Phase completion criteria
- Loop-back conditions (insufficient evidence, low confidence)
- Maximum iteration limits per phase

**Current faultmaven:**
- ⚠️ Has basic phase enum but no loopback logic

**Migration complexity:** MEDIUM
- Requires: Phase completion detection
- Requires: Evidence sufficiency checks
- Effort estimate: 1-2 days

---

### 7. Workflow Progression Detector (258 LOC) - **LOW PRIORITY**

**Purpose:** Automatically detect when to transition phases.

**Features:**
- Analyzes conversation and evidence
- Detects implicit phase completion signals
- Suggests phase transitions to user

**Current faultmaven:**
- ❌ No automatic progression detection
- Phase transitions are manual only

**Migration complexity:** LOW-MEDIUM
- Requires: Pattern matching on evidence/hypotheses
- Effort estimate: 1 day

---

### 8. Engagement Modes (573 LOC) - **LOW PRIORITY**

**Purpose:** Different modes for different investigation scenarios.

**Modes:**
- CONSULTING: Pre-investigation exploration
- INVESTIGATING: Active troubleshooting
- REVIEWING: Post-mortem analysis
- TRAINING: Learning mode

**Current faultmaven:**
- ⚠️ Has CONSULTING vs INVESTIGATING status
- ❌ No mode-specific behavior variations

**Migration complexity:** LOW
- Requires: Mode-specific prompt templates
- Effort estimate: 1 day

---

## Root Cause Analysis: Why Only 30% Was Migrated

### Investigation of PR #20 Scope

Looking at the MIGRATION_PLAN.md and PR #20 implementation:

**What was explicitly planned:**
1. ✅ Investigation state models (Pydantic schemas)
2. ✅ Basic investigation service (initialize, advance, add hypothesis)
3. ✅ Report generation service
4. ✅ Status transitions (CONSULTING → INVESTIGATING)

**What was deferred (from PR20_DEFERRED_ITEMS_ANALYSIS.md):**
1. Auto-wire investigation initialization → **Needs product input** (valid deferral)
2. Integration tests → **Should not have been deferred** (added after feedback)
3. Unit tests → **Should not have been deferred** (added after feedback)

**What was missed entirely:**
- Milestone engine orchestration
- OODA loop implementation
- Hypothesis confidence management
- Memory management
- Working conclusions
- Phase loopback logic
- Workflow progression detection

### Why the Gap Exists

**Hypothesis 1: Scope Creep Prevention**
- MIGRATION_PLAN.md focused on "business logic migration"
- Interpreted as "data models + basic CRUD" rather than "complete investigation framework"
- Missing components seen as "advanced features" rather than "core architecture"

**Hypothesis 2: Complexity Underestimation**
- Investigation framework appears simple on surface (phases + hypotheses)
- Actual implementation has deep architectural sophistication
- 6,000+ LOC wasn't fully analyzed before starting migration

**Hypothesis 3: Incremental Approach**
- Phase 4 of MONOLITH_EVOLUTION_PLAN.md was meant to be incremental
- PR #20 was "Phase 4a" (foundations)
- Remaining components intended for future PRs

**Most likely:** Combination of all three
- Scope was intentionally limited to "get something working"
- Complexity of full framework wasn't fully appreciated
- Plan was to iterate in subsequent PRs

---

## Recommended Migration Strategy

### Option A: Complete Migration Now (Recommended)

**Approach:**
1. Create comprehensive investigation framework design document
2. Break into logical phases:
   - **Phase 1:** Milestone engine + turn processing (1 week)
   - **Phase 2:** OODA orchestration + adaptive intensity (1 week)
   - **Phase 3:** Hypothesis confidence + evidence linking (1 week)
   - **Phase 4:** Memory manager + working conclusions (1 week)
   - **Phase 5:** Phase loopback + progression detection (3 days)

**Pros:**
- ✅ Complete feature parity with FaultMaven-Mono
- ✅ Sophisticated investigation capabilities
- ✅ Proper architectural foundation

**Cons:**
- ⚠️ Significant effort (4-5 weeks)
- ⚠️ Delays other features

**Total effort:** 4-5 weeks (with testing)

---

### Option B: Minimal Viable Investigation (Alternative)

**Approach:**
1. Keep current simple implementation
2. Add only essential features:
   - Hypothesis confidence calculation (3 days)
   - Evidence linking (2 days)
   - Basic milestone tracking (3 days)
   - Skip: OODA, memory manager, working conclusions

**Pros:**
- ✅ Faster to implement (1-2 weeks)
- ✅ Good enough for basic use cases

**Cons:**
- ❌ Missing sophisticated investigation capabilities
- ❌ Limited differentiation from basic chat
- ❌ Will need to revisit later anyway

**Total effort:** 1-2 weeks

---

### Option C: Hybrid Approach (Practical)

**Approach:**
1. **Immediate (Week 1):** Core enhancements
   - Hypothesis confidence calculation with evidence linking
   - Basic milestone tracking
   - Turn outcome classification

2. **Near-term (Weeks 2-3):** Investigation intelligence
   - Milestone engine for turn processing
   - Status-based prompt generation
   - Automatic degraded mode detection

3. **Medium-term (Weeks 4-5):** Advanced features
   - OODA orchestration
   - Memory manager
   - Working conclusions

4. **Future:** Nice-to-haves
   - Phase loopback optimization
   - Workflow progression detector
   - Engagement modes

**Pros:**
- ✅ Delivers value incrementally
- ✅ Core capabilities within 2-3 weeks
- ✅ Can pause after each phase based on priorities

**Cons:**
- ⚠️ Requires careful interface design to allow incremental addition

**Total effort:** 2-3 weeks for core, 4-5 weeks for complete

---

## Design Issues That Surfaced

### Issue 1: Investigation Initialization Ambiguity

**Problem identified in AUTO_WIRE_INVESTIGATION_DESIGN.md:**
- When transitioning CONSULTING → INVESTIGATING, should initialization be automatic or manual?
- Current PR #20: Manual (two separate API calls)
- FaultMaven-Mono: Automatic with LLM inference

**Root cause:**
- PR #20 focused on data structures, not user flow
- Missing: LLM-based temporal_state and urgency_level inference
- Missing: Confirmation modal UX design

**Status:** Documented, awaiting product decision

---

### Issue 2: Investigation vs Report Service Overlap

**Discovered during implementation:**
- `InvestigationService` manages investigation lifecycle
- `ReportService` generates reports from investigation
- **Overlap:** Who owns "investigation conclusion"?

**Current design:**
- InvestigationState has `conclusions` field
- ReportService generates reports from InvestigationState
- **Gap:** No working conclusion generation during investigation

**Fix needed:**
- Add WorkingConclusionGenerator to InvestigationService
- Reports use working conclusions as input
- Clear separation of concerns

---

### Issue 3: Milestone Tracking vs Phase Progression

**Design conflict:**
- FaultMaven-Mono has **two paradigms:**
  1. Milestone-based (opportunistic completion)
  2. Phase-based (sequential progression)

**Question:** Which one to use?

**FaultMaven-Mono answer (from milestone_engine.py:8):**
```python
"""
Key Differences from OODA:
- NO phase transitions - milestones complete when data is available
- NO sequential constraints - multiple milestones can complete in one turn
"""
```

**Current faultmaven:**
- Uses phase-based approach (InvestigationPhase enum)
- Missing: Milestone-based flexibility

**Fix needed:**
- Adopt milestone-based approach as primary
- Keep phases as organizational structure
- Allow opportunistic milestone completion within phases

---

### Issue 4: Evidence Management Architecture

**Missing from PR #20:**
- Evidence linking to hypotheses
- Evidence categorization (logs, metrics, configs)
- Evidence stance (supporting vs refuting)

**FaultMaven-Mono has:**
```python
class Evidence:
    evidence_id: str
    category: EvidenceCategory  # LOGS, METRICS, CONFIG, etc.
    form: EvidenceForm  # DIRECT_OBSERVATION, SYMPTOM, etc.
    source_type: EvidenceSourceType  # USER_PROVIDED, SYSTEM_QUERY, etc.

class HypothesisEvidenceLink:
    hypothesis_id: str
    evidence_id: str
    stance: EvidenceStance  # SUPPORTING, REFUTING, NEUTRAL
```

**Current faultmaven:**
- No Evidence model at all
- Hypotheses have `supporting_evidence` and `refuting_evidence` lists
- But evidence is just strings, not structured objects

**Fix needed:**
- Create Evidence ORM model
- Create HypothesisEvidenceLink relationship table
- Implement evidence categorization

---

## Immediate Next Steps

### Step 1: Finalize OpenAPI Enhancement (2-3 hours)

**Decision needed:** Port `generate_api_docs.py` or enhance existing?

**Recommendation:** Port `generate_api_docs.py`
- Already proven implementation
- Comprehensive examples
- Better developer experience

**Actions:**
1. Copy `generate_api_docs.py` to faultmaven/scripts/
2. Update imports to use faultmaven modules
3. Add examples for faultmaven-specific endpoints
4. Run and verify output

---

### Step 2: Create Investigation Framework Design Document (1 day)

**Content:**
1. Architecture overview (milestone vs phase paradigms)
2. Component dependency graph
3. Migration priority matrix
4. API surface area changes
5. Database schema additions
6. LLM integration requirements

**Deliverable:** `docs/INVESTIGATION_FRAMEWORK_DESIGN.md`

---

### Step 3: Product Decision on Scope (Meeting)

**Questions for stakeholders:**
1. Do we need full FaultMaven-Mono investigation capabilities?
2. Can we ship with "Minimal Viable Investigation" (Option B)?
3. Should we do incremental rollout (Option C)?
4. What's the priority: sophisticated investigation vs other features?

**Inputs needed:**
- Product roadmap priorities
- User feedback on current investigation flow
- Competitive analysis (what do competitors offer?)

---

### Step 4: Implement Chosen Approach

**If Option A (Complete):**
- Create detailed task breakdown (20-30 tasks)
- Assign to team or agent
- Target: 4-5 weeks with testing

**If Option B (Minimal):**
- Focus on hypothesis confidence + evidence linking
- Target: 1-2 weeks

**If Option C (Hybrid):**
- Start with Week 1 core enhancements
- Reassess after each phase

---

## Testing Strategy for Migration

### Unit Tests Required

**Per component:**
- `test_milestone_engine.py` - Turn processing, prompt generation
- `test_hypothesis_manager.py` - Confidence calculation, anchoring prevention
- `test_ooda_engine.py` - OODA iteration, intensity control
- `test_memory_manager.py` - Context management
- `test_working_conclusion_generator.py` - Conclusion synthesis

**Coverage target:** 80%+ for all investigation components

---

### Integration Tests Required

**End-to-end flows:**
1. Complete investigation lifecycle (CONSULTING → INVESTIGATING → RESOLVED)
2. Hypothesis lifecycle (CAPTURED → ACTIVE → VALIDATED)
3. Evidence linking and confidence updates
4. Milestone completion and phase progression
5. Degraded mode detection and recovery

**Test file:** `tests/integration/modules/case/test_investigation_full_lifecycle.py`

---

## Conclusion

**Key findings:**
1. ✅ PR #20 successfully migrated basic investigation data models and CRUD operations
2. ❌ ~70% of sophisticated investigation framework not migrated (6,069 LOC)
3. ⚠️ Current implementation lacks:
   - Milestone-based orchestration
   - OODA loop execution
   - Hypothesis confidence management
   - Evidence linking
   - Memory management
   - Working conclusions
4. ✅ OpenAPI generation: `generate_openapi_spec.py` ported, `generate_api_docs.py` available for enhancement

**Recommendations:**
1. **Immediate:** Port `generate_api_docs.py` for better API documentation (2-3 hours)
2. **Short-term:** Create comprehensive investigation framework design document (1 day)
3. **Medium-term:** Choose migration strategy (Options A/B/C) based on product priorities
4. **Long-term:** Implement chosen approach with incremental delivery (2-5 weeks)

**Critical decision needed:** Scope of investigation framework migration (see Step 3)

---

**Next Action:** Review this analysis with product team to determine migration priority and approach.

**Owner:** TBD
**Timeline:** TBD after scope decision
