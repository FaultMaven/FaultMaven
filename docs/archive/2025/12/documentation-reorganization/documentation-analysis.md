# Documentation Organization Analysis

**Date**: 2025-12-27
**Purpose**: Address documentation lifecycle and naming convention issues

---

## Executive Summary

**Recommendations**:
1. ✅ Keep TECHNICAL_DEBT.md in docs/ (permanent strategic tracker)
2. ✅ Consolidate duplicate content between TECHNICAL_DEBT.md and checkpoint
3. ✅ Move 1 temporal document to working/
4. ✅ Adopt proposed naming convention (7 UPPERCASE meta, rest lowercase)

**Impact**: Improved organization, better scannability, industry-standard conventions

---

## Issue 1: TECHNICAL_DEBT.md Location

### Question
Should TECHNICAL_DEBT.md be in working/ since it updates frequently?

### Analysis

**Characteristics of TECHNICAL_DEBT.md**:
- Central gap tracking document (authoritative source)
- Referenced by 5+ permanent documents
- Strategic planning tool (not tactical status)
- Comparable to ROADMAP.md in purpose
- Updates reflect progress, not obsolescence

**Comparison with working/ docs**:
| Aspect | TECHNICAL_DEBT.md | Typical working/ Doc |
|--------|-------------------|---------------------|
| **Purpose** | Strategic gap tracking | Tactical status/planning |
| **Lifecycle** | Permanent (shrinks as gaps close) | Temporary (deleted when done) |
| **References** | Referenced by permanent docs | Self-contained |
| **Audience** | All stakeholders | Internal team |
| **Updates** | Progress-driven | Completion-driven |

### Recommendation

**✅ Keep in docs/ (permanent location)**

**Rationale**:
1. **Authoritative source**: It's THE gap tracker, referenced by ARCHITECTURE.md, SYSTEM_DESIGN.md, README.md
2. **Strategic document**: Comparable to ROADMAP.md - both update frequently but remain permanently important
3. **Permanent reference**: Even when all gaps are closed, historical context is valuable
4. **Clear distinction**: "Working" docs are temporary planning; this is permanent strategic tracking

**Analogy**: TECHNICAL_DEBT.md is like a GitHub Project Board - frequently updated but permanently important. Working docs are like scratch notes - useful during work but deleted after.

---

## Issue 2: Duplicate Content

### Problem
TECHNICAL_DEBT.md and CHECKPOINT_2025_12_27.md have ~300 lines of overlapping content:
- Critical gaps descriptions
- Implementation roadmap
- Module status tables
- Effort estimates

### Analysis

**TECHNICAL_DEBT.md Purpose**:
- Strategic gap tracking
- What's NOT implemented
- Priorities and roadmap
- Effort estimates
- Blockers and dependencies

**CHECKPOINT_2025_12_27.md Purpose**:
- Snapshot of work completed
- Git commit history
- Architectural decisions made
- Verification checklist
- Migration notes

**Overlap**:
- Both describe the same 9 gaps
- Both include implementation roadmap
- Both have module status tables
- Both include effort estimates

### Recommendation

**✅ Consolidate by purpose - Keep single source of truth**

**Actions**:

1. **TECHNICAL_DEBT.md** (Strategic tracker):
   - Keep: Gap descriptions, priorities, roadmap, effort estimates
   - Keep: Current implementation status
   - Keep: Decision points and recommendations

2. **CHECKPOINT_2025_12_27.md** (Historical snapshot):
   - Keep: Work completed in this session
   - Keep: Git commit history
   - Keep: Architectural decisions made
   - Keep: Verification checklist
   - **Remove**: Duplicate gap descriptions
   - **Replace with**: "See [TECHNICAL_DEBT.md](../TECHNICAL_DEBT.md) for current gaps and roadmap"

**Benefits**:
- Single source of truth for gaps
- Checkpoint focuses on "what happened"
- TECHNICAL_DEBT focuses on "what's next"
- No synchronization issues

---

## Issue 3: Non-Permanent Files in docs/

### Analysis

**Current docs/ files** (excluding working/):
```
ARCHITECTURE.md                              ✅ Permanent
DEPLOYMENT.md                                ✅ Permanent
DEVELOPMENT.md                               ✅ Permanent
FAQ.md                                       ✅ Permanent
INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md  ❌ Temporal!
MODULAR_MONOLITH_DESIGN.md                   ✅ Permanent
README.md                                    ✅ Permanent
ROADMAP.md                                   ✅ Permanent
SECURITY.md                                  ✅ Permanent
SYSTEM_DESIGN.md                             ✅ Permanent
TECHNICAL_DEBT.md                            ✅ Permanent
TESTING_STRATEGY.md                          ✅ Permanent
TROUBLESHOOTING.md                           ✅ Permanent
```

**Problem File**: `INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md`

**Evidence it's temporal**:
- Title includes "COMPLETE" (completion status)
- Header: "Completion Date: 2025-12-25"
- Content: "Final Status" report
- Purpose: Document completion of integration work
- Not referenced by other permanent docs
- Similar to other completion reports in working/

### Recommendation

**✅ Move to working/ and rename**

**Action**:
```bash
mv docs/INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md \
   docs/working/investigation-framework-status.md
```

**Rationale**:
1. This is a completion status report (temporal)
2. Similar to ENGINE_INTEGRATION_STATUS.md already in working/
3. Will be archived after next major milestone
4. Not a permanent reference guide

---

## Issue 4: File Naming Convention

### Current State Analysis

**Current UPPERCASE files** (14 total):
```
ARCHITECTURE.md                              ✅ Top-level meta
DEPLOYMENT.md                                ✅ Top-level meta
DEVELOPMENT.md                               ✅ Top-level meta
FAQ.md                                       ⚠️  Detailed reference
INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md  ❌ Temporal (move)
MODULAR_MONOLITH_DESIGN.md                   ⚠️  Detailed rationale
README.md                                    ✅ Top-level meta
ROADMAP.md                                   ⚠️  Detailed reference
SECURITY.md                                  ✅ Top-level meta
SYSTEM_DESIGN.md                             ✅ Top-level meta
TECHNICAL_DEBT.md                            ✅ Top-level meta
TESTING_STRATEGY.md                          ⚠️  Detailed guide
TROUBLESHOOTING.md                           ⚠️  Detailed guide
```

**Issues**:
- Too many UPPERCASE files (14) - reduced scannability
- Detailed guides use same convention as entry points
- No visual hierarchy
- Name too verbose (INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md = 46 chars)

### Proposed Convention (from user)

**Rule 1: Top-Level Meta (UPPERCASE)**
- Limit to 5-10 most important entry points
- High-level documentation
- First files new developers should read

**Rule 2: Detailed Documentation (lowercase-kebab-case)**
- Specific guides and strategies
- Reference materials
- Better scannability in file lists

**Rule 3: Directories (lowercase)**
- snake_case or kebab-case
- Cross-platform compatibility

**Rule 4: Configuration (Tool-specific)**
- Follow tool standards (Dockerfile, docker-compose.yml, etc.)

### Recommendation

**✅ Adopt proposed convention**

**Tier 1: Top-Level Meta (UPPERCASE) - 7 files**:
```
README.md                    # Main entry point
ARCHITECTURE.md              # System architecture overview
SYSTEM_DESIGN.md             # Design specifications
TECHNICAL_DEBT.md            # Implementation gaps
DEVELOPMENT.md               # Developer setup
DEPLOYMENT.md                # Production deployment
SECURITY.md                  # Security guidelines
```

**Tier 2: Detailed Guides (lowercase-kebab-case) - 5 files**:
```
MODULAR_MONOLITH_DESIGN.md    →  modular-monolith-rationale.md
TESTING_STRATEGY.md           →  testing-strategy.md
TROUBLESHOOTING.md            →  troubleshooting.md
ROADMAP.md                    →  roadmap.md
FAQ.md                        →  faq.md
```

**Tier 3: Temporal/Status (working/) - 1 moved file**:
```
INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md  →  working/investigation-framework-status.md
```

### Benefits

**Improved Scannability**:
```
Before (14 UPPERCASE files - hard to scan):
ARCHITECTURE.md
DEPLOYMENT.md
DEVELOPMENT.md
FAQ.md
INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md  ← too long
MODULAR_MONOLITH_DESIGN.md
README.md
ROADMAP.md
SECURITY.md
SYSTEM_DESIGN.md
TECHNICAL_DEBT.md
TESTING_STRATEGY.md
TROUBLESHOOTING.md

After (7 UPPERCASE + 5 lowercase - clear hierarchy):
ARCHITECTURE.md              ← Top-level entry points
DEPLOYMENT.md
DEVELOPMENT.md
README.md
SECURITY.md
SYSTEM_DESIGN.md
TECHNICAL_DEBT.md
---
faq.md                       ← Detailed guides (visually distinct)
modular-monolith-rationale.md
roadmap.md
testing-strategy.md
troubleshooting.md
```

**Clear Visual Hierarchy**:
- UPPERCASE files immediately stand out as primary entry points
- Lowercase files clearly marked as detailed references
- New developers know where to start

**Industry Standard**:
- Matches common practice (README.md, CONTRIBUTING.md are UPPERCASE)
- Detailed docs in lowercase (testing-guide.md, api-reference.md)
- Used by major projects (Kubernetes, React, etc.)

**Shorter Names**:
- `INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md` (46 chars)
- → `working/investigation-framework-status.md` (40 chars, more descriptive location)

---

## Implementation Plan

### Phase 1: Move Temporal Document

```bash
cd /home/swhouse/product/faultmaven
mv docs/INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md \
   docs/working/investigation-framework-status.md
```

**Update references**:
- docs/README.md: Move from "Framework" section to working/ references
- docs/working/README.md: Add to current documents list

---

### Phase 2: Rename Detailed Documentation

```bash
cd /home/swhouse/product/faultmaven/docs

# Rename 5 files to lowercase-kebab-case
mv MODULAR_MONOLITH_DESIGN.md modular-monolith-rationale.md
mv TESTING_STRATEGY.md testing-strategy.md
mv TROUBLESHOOTING.md troubleshooting.md
mv ROADMAP.md roadmap.md
mv FAQ.md faq.md
```

---

### Phase 3: Update All References

**Files to update**:

1. **docs/README.md** (Documentation map)
   - Architecture & Design section
   - Reference section
   - Documentation by Role section
   - Documentation by Task section

2. **docs/ARCHITECTURE.md**
   - Related documents section
   - Cross-references

3. **docs/TECHNICAL_DEBT.md**
   - Related documents section

4. **docs/SYSTEM_DESIGN.md**
   - Related documents section

5. **Root README.md**
   - Documentation links section

6. **docs/working/CHECKPOINT_2025_12_27.md**
   - References section
   - Documentation structure section

7. **docs/working/README.md**
   - Current documents list

---

### Phase 4: Consolidate Checkpoint Content

**In CHECKPOINT_2025_12_27.md**:

Remove duplicate sections:
- Technical Debt Summary (lines 217-250)
- Implementation roadmap details

Add reference instead:
```markdown
## Technical Debt Summary

For current implementation gaps and roadmap, see [TECHNICAL_DEBT.md](../TECHNICAL_DEBT.md).

**Snapshot at checkpoint** (2025-12-27):
- 9 gaps identified (4 critical, 3 high, 2 low)
- Total effort: 16.5 weeks (all gaps), 12.5 weeks (MVP)
- Next priority: Structured LLM output (2 weeks, unblocks everything)
```

Keep unique checkpoint content:
- Git commit history
- Architectural decisions made
- Work completed in this session
- Verification checklist

---

### Phase 5: Test and Verify

**Checklist**:
- [ ] All markdown links work
- [ ] No broken cross-references
- [ ] Documentation map accurate
- [ ] Working/ README updated
- [ ] Checkpoint consolidated (no duplication)
- [ ] Git history preserved

---

## Final Structure

### docs/ (Permanent - 13 files)

**Top-Level Meta (UPPERCASE - 7 files)**:
```
docs/
├── README.md                    # Documentation map
├── ARCHITECTURE.md              # System architecture
├── SYSTEM_DESIGN.md             # Design specifications
├── TECHNICAL_DEBT.md            # Implementation gaps
├── DEVELOPMENT.md               # Developer guide
├── DEPLOYMENT.md                # Deployment guide
└── SECURITY.md                  # Security guide
```

**Detailed Guides (lowercase-kebab-case - 5 files)**:
```
docs/
├── modular-monolith-rationale.md  # Design rationale
├── testing-strategy.md            # Testing approach
├── troubleshooting.md             # Common issues
├── roadmap.md                     # Product roadmap
└── faq.md                         # FAQ
```

**API Documentation**:
```
docs/api/
└── README.md                      # Auto-generated API docs
```

---

### docs/working/ (Temporal - 12 files)

```
docs/working/
├── README.md                                # Lifecycle management
├── CHECKPOINT_2025_12_27.md                 # Latest checkpoint
├── investigation-framework-status.md        # MOVED from docs/
├── DOCUMENTATION_CLEANUP_COMPLETE.md        # Cleanup status
├── DOCUMENTATION_CLEANUP_TODO.md            # Cleanup tasks
├── ENGINE_INTEGRATION_STATUS.md             # Engine integration
├── INTEGRATION_COMPLETION_SUMMARY.md        # Integration summary
├── FEATURE_PARITY_TRACKING.md              # Feature parity
├── FAULTMAVEN_MONO_DEPRECATION_ANALYSIS.md # Deprecation
├── TESTING_IMPLEMENTATION_ROADMAP.md        # Testing roadmap
├── HYPOTHESIS_MANAGER_TEST_COVERAGE.md      # Coverage
├── MILESTONE_ENGINE_TEST_COVERAGE.md        # Coverage
└── OODA_ENGINE_TEST_COVERAGE.md             # Coverage
```

---

## Recommendations Summary

| Issue | Recommendation | Rationale |
|-------|----------------|-----------|
| 1. TECHNICAL_DEBT.md location | ✅ Keep in docs/ | Strategic tracker, permanent reference |
| 2. Duplicate content | ✅ Consolidate | Single source of truth, checkpoint references TD |
| 3. Temporal doc in permanent | ✅ Move to working/ | Completion report, similar to other status docs |
| 4. Naming convention | ✅ Adopt proposal | Better scannability, industry standard |

**Total changes**:
- 1 file moved (docs/ → working/)
- 5 files renamed (UPPERCASE → lowercase-kebab-case)
- 7 files updated (cross-references)
- 1 file consolidated (checkpoint content)

**Estimated effort**: 30-45 minutes
**Risk**: Low (git preserves history)

---

## Next Steps

**Awaiting approval**:
1. ✅ Approve analysis and recommendations?
2. ✅ Proceed with implementation?

**If approved**:
1. Execute Phase 1-5
2. Test all markdown links
3. Commit changes
4. Update checkpoint document

---

**Status**: Analysis complete, awaiting approval to implement
**Created**: 2025-12-27
**Author**: tech-writer agent
