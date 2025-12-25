# Investigation Framework Integration - Quick Reference

**For Developers**: Fast lookup of integration points and usage patterns

---

## Integration Points (process_turn workflow)

### Step 0.5: Memory Organization (Line 164)
```python
inv_state.memory = self.memory_manager.organize_memory(inv_state)
```
- **Purpose**: Organize turn history into hot/warm/cold tiers
- **Frequency**: Every turn
- **Token Budget**: ~1,600 tokens (vs 4,500+ unmanaged)

### Step 0.7: OODA Iteration Tracking (Lines 170-183)
```python
if case.status == CaseStatus.INVESTIGATING:
    if not inv_state.ooda_state:
        inv_state.ooda_state = OODAState()

    inv_state.ooda_state.current_iteration += 1
    intensity = self.ooda_engine.get_current_intensity(inv_state)
```
- **Purpose**: Track iterations, get adaptive intensity
- **Frequency**: Every turn during INVESTIGATING
- **Returns**: "light", "medium", "full", or "none"

### Step 7.5: Working Conclusion (Lines 217-220)
```python
inv_state.working_conclusion = self.working_conclusion_generator.generate_conclusion(inv_state)
inv_state.progress_metrics = self.working_conclusion_generator.calculate_progress(inv_state)
```
- **Purpose**: Generate current understanding and momentum
- **Frequency**: Every turn
- **Returns**: `WorkingConclusion` + `ProgressMetrics`

### Step 8.3: Phase Loop-back (Lines 235-255)
```python
needs_loopback, outcome, reason = self.phase_orchestrator.detect_loopback_needed(inv_state)

if needs_loopback and outcome and reason:
    next_phase, is_loopback, message = self.phase_orchestrator.determine_next_phase(
        inv_state, outcome, reason
    )
    if is_loopback:
        inv_state.current_phase = next_phase
```
- **Purpose**: Detect and handle phase loop-backs
- **Frequency**: Every turn
- **Triggers**: All hypotheses refuted, insufficient hypotheses

### Step 8.5: Memory Compression (Lines 258-266)
```python
if self.memory_manager.should_trigger_compression(inv_state):
    inv_state.memory = self.memory_manager.compress_memory(
        inv_state.memory,
        max_hot=3, max_warm=5, max_cold=10
    )
```
- **Purpose**: Compress memory to stay within token limits
- **Frequency**: Every 3 turns
- **Limits**: 3 hot, 5 warm, 10 cold snapshots

### Prompt Context: Memory (Lines 386-392)
```python
memory_context = ""
if inv_state.memory:
    memory_context = "\n" + self.memory_manager.get_context_for_prompt(
        inv_state.memory, max_tokens=1600
    )
```
- **Purpose**: Add hierarchical memory to LLM prompt
- **Frequency**: Every turn in investigating prompt
- **Token Budget**: 1,600 tokens max

---

## Engine Instantiation (MilestoneEngine.__init__)

```python
def __init__(self, llm_provider, repository=None, trace_enabled=True):
    self.llm_provider = llm_provider
    self.repository = repository
    self.trace_enabled = trace_enabled

    # Initialize supporting engines
    self.hypothesis_manager = HypothesisManager()
    self.ooda_engine = OODAEngine()
    self.memory_manager = MemoryManager(llm_provider=llm_provider)
    self.working_conclusion_generator = WorkingConclusionGenerator()
    self.phase_orchestrator = PhaseOrchestrator()
```

---

## Model Fields Added

### MemorySnapshot (10 new fields)
```python
snapshot_id: str
turn_range: Tuple[int, int]
tier: str  # "hot", "warm", or "cold"
content_summary: str
key_insights: List[str]
evidence_ids: List[str]
hypothesis_updates: List[str]
confidence_delta: float
token_count_estimate: int
created_at: datetime
```

### WorkingConclusion (3 new fields)
```python
last_updated_turn: int
last_confidence_change_turn: int
generated_at_turn: int
```

### ProgressMetrics (7 new fields)
```python
evidence_provided_count: int
evidence_pending_count: int
investigation_momentum: InvestigationMomentum  # EARLY, ACCELERATING, STEADY, STALLED
next_critical_steps: List[str]
is_degraded_mode: bool
generated_at_turn: int
```

### TurnRecord (1 new field)
```python
progress_made: bool
```

---

## Common Patterns

### Accessing Memory Tiers
```python
# Hot memory (last 3 turns, full detail)
for snapshot in inv_state.memory.hot_memory:
    print(snapshot.content_summary)

# Warm memory (active hypotheses, summarized)
for snapshot in inv_state.memory.warm_memory:
    print(snapshot.key_insights)

# Cold memory (archived facts)
for snapshot in inv_state.memory.cold_memory:
    print(snapshot.content_summary)
```

### Checking Investigation Momentum
```python
if inv_state.progress_metrics.investigation_momentum == InvestigationMomentum.STALLED:
    # Consider entering degraded mode or requesting human guidance
    pass
elif inv_state.progress_metrics.investigation_momentum == InvestigationMomentum.ACCELERATING:
    # Investigation making good progress
    pass
```

### Getting Current Intensity
```python
intensity = self.ooda_engine.get_current_intensity(inv_state)

if intensity == "full":
    # Use thorough investigation with anchoring prevention
    pass
elif intensity == "medium":
    # Standard investigation depth
    pass
elif intensity == "light":
    # Quick assessment
    pass
```

### Loop-back Detection
```python
needs_loopback, outcome, reason = self.phase_orchestrator.detect_loopback_needed(inv_state)

if needs_loopback:
    # Loop-back conditions met
    if outcome == PhaseOutcome.HYPOTHESIS_REFUTED:
        # All hypotheses refuted, loop back to HYPOTHESIS phase
        pass
    elif outcome == PhaseOutcome.SCOPE_CHANGED:
        # Scope changed, loop back to BLAST_RADIUS
        pass
```

---

## Type Fixes Applied

### hypotheses: List vs Dict
```python
# ❌ WRONG (was treating as Dict)
active = [h for h in inv_state.hypotheses.values() if ...]

# ✅ CORRECT (it's a List)
active = [h for h in inv_state.hypotheses if ...]
```

### turn.outcome: str vs Enum
```python
# ❌ WRONG (already a string)
summary = f"Turn {turn.turn_number} → {turn.outcome.value}"

# ✅ CORRECT
summary = f"Turn {turn.turn_number} → {turn.outcome}"
```

---

## Testing Patterns

### Mock LLM Provider
```python
class MockLLMProvider:
    def __init__(self, response="Mock response"):
        self.response = response

    async def generate(self, prompt, **kwargs):
        return self.response
```

### Mock Case
```python
class MockCase:
    def __init__(self, status=CaseStatus.INVESTIGATING):
        self.id = "test-case-001"
        self.title = "Test Case"
        self.status = status
        self.case_metadata = {}
```

### Integration Test Pattern
```python
@pytest.mark.asyncio
async def test_engine_integration():
    llm = MockLLMProvider()
    engine = MilestoneEngine(llm_provider=llm)
    case = MockCase(status=CaseStatus.INVESTIGATING)

    # Process turn
    result = await engine.process_turn(case, "Test message")

    # Verify integration
    inv_state = engine._load_investigation_state(case)
    assert inv_state.memory is not None  # MemoryManager
    assert inv_state.working_conclusion is not None  # WorkingConclusionGenerator
    assert inv_state.ooda_state is not None  # OODAEngine
```

---

## Debugging Tips

### Enable Trace Logging
```python
import logging
logging.basicConfig(level=logging.INFO)

engine = MilestoneEngine(llm_provider=llm, trace_enabled=True)
```

### Check Memory Organization
```python
logger.info(f"Hot memory: {len(inv_state.memory.hot_memory)} snapshots")
logger.info(f"Warm memory: {len(inv_state.memory.warm_memory)} snapshots")
logger.info(f"Cold memory: {len(inv_state.memory.cold_memory)} snapshots")
```

### Monitor OODA Iterations
```python
logger.info(
    f"OODA iteration {inv_state.ooda_state.current_iteration}, "
    f"intensity: {intensity}, "
    f"phase: {inv_state.current_phase.value}"
)
```

### Track Progress Momentum
```python
logger.info(
    f"Momentum: {inv_state.progress_metrics.investigation_momentum.value}, "
    f"Turns without progress: {inv_state.progress_metrics.turns_without_progress}"
)
```

---

## Common Issues & Solutions

### Issue: "AttributeError: 'list' object has no attribute 'values'"
**Solution**: Remove `.values()` - `hypotheses` is a List, not Dict

### Issue: "AttributeError: 'str' object has no attribute 'value'"
**Solution**: Remove `.value` - `turn.outcome` is already a string

### Issue: Memory compression not triggering
**Solution**: Check `should_trigger_compression()` - triggers every 3 turns

### Issue: OODA state is None
**Solution**: Ensure `case.status == CaseStatus.INVESTIGATING` before tracking

---

## Performance Considerations

### Memory Tier Limits
- **Hot**: Max 3 snapshots (~600 tokens)
- **Warm**: Max 5 snapshots (~300 tokens)
- **Cold**: Max 10 snapshots (~100 tokens)
- **Total**: ~1,600 tokens (vs 4,500+ unmanaged)

### Compression Frequency
- Every 3 turns (turn % 3 == 0)
- Demotes warm → cold
- Drops oldest cold snapshots

### OODA Iteration Limits
- No hard limits implemented
- Anchoring prevention triggers at iteration 3+
- Degraded mode triggers after 3 turns without progress

---

## References

- **Full Documentation**: [ENGINE_INTEGRATION_STATUS.md](ENGINE_INTEGRATION_STATUS.md)
- **Resolution Report**: [DESIGN_AUDIT_RESOLUTION.md](DESIGN_AUDIT_RESOLUTION.md)
- **Completion Summary**: [INTEGRATION_COMPLETION_SUMMARY.md](INTEGRATION_COMPLETION_SUMMARY.md)
- **Original Audit**: [INVESTIGATION_FRAMEWORK_DESIGN_AUDIT.md](INVESTIGATION_FRAMEWORK_DESIGN_AUDIT.md)

---

**Last Updated**: 2025-12-25
**Version**: 1.0 (80% integration complete)
