# Documentation Reorganization Plan

**Created**: 2025-12-27
**Status**: Proposed
**Purpose**: Address naming consistency and document lifecycle issues

---

## Issues Identified

### 1. TECHNICAL_DEBT.md Location
**Issue**: Should it be in working/ since it updates frequently?
**Decision**: **Keep in docs/** (permanent location)
**Rationale**:
- Central strategic planning document
- Referenced by ARCHITECTURE.md, SYSTEM_DESIGN.md, README.md
- Similar to ROADMAP.md - frequently updated but permanently important
- "Working" docs are for temporary planning; this is permanent gap tracking

### 2. Duplicate Content
**Issue**: TECHNICAL_DEBT.md and CHECKPOINT_2025_12_27.md have significant overlap
**Decision**: **Consolidate by purpose**
**Actions**:
- TECHNICAL_DEBT.md: Keep only gap tracking (what's missing, priorities, roadmap)
- CHECKPOINT_2025_12_27.md: Keep only checkpoint-specific content (commits, decisions, snapshot)
- Checkpoint references TECHNICAL_DEBT.md instead of duplicating gaps

### 3. Temporal Document in Permanent Location
**Issue**: INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md is a status report (temporal)
**Decision**: **Move to working/ and rename**
**Action**:
- Move to `docs/working/investigation-framework-status.md`
- This is a completion status report, not permanent reference

### 4. File Naming Convention Inconsistency
**Issue**: Too many UPPERCASE files (14), names too verbose
**Decision**: **Adopt proposed convention**

---

## Proposed File Naming Convention

### Rule 1: Top-Level Meta Documents (UPPERCASE)
**Limit to 5-7 most important entry points**

Keep UPPERCASE:
- ✅ `README.md` - Main entry point
- ✅ `ARCHITECTURE.md` - System architecture overview
- ✅ `SYSTEM_DESIGN.md` - Design of record (specifications)
- ✅ `TECHNICAL_DEBT.md` - Implementation gap tracker
- ✅ `DEVELOPMENT.md` - Developer setup and workflow
- ✅ `DEPLOYMENT.md` - Production deployment guide
- ✅ `SECURITY.md` - Security guidelines

**Total**: 7 UPPERCASE files (down from 14)

### Rule 2: Detailed Documentation (lowercase-kebab-case)
**For specific guides, strategies, and references**

Rename to lowercase:
- `MODULAR_MONOLITH_DESIGN.md` → `modular-monolith-rationale.md`
- `TESTING_STRATEGY.md` → `testing-strategy.md`
- `TROUBLESHOOTING.md` → `troubleshooting.md`
- `ROADMAP.md` → `roadmap.md`
- `FAQ.md` → `faq.md`

### Rule 3: Status/Temporal Documents (working/ folder)
**For completion reports and status tracking**

Move and rename:
- `INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md` → `working/investigation-framework-status.md`

---

## Detailed Renaming Plan

### Phase 1: Move Temporal Documents (1 file)

**Move to working/**:
```bash
# 1. Investigation framework status (temporal completion report)
mv docs/INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md \
   docs/working/investigation-framework-status.md
```

**Why**: This is a completion status report from 2025-12-25, not permanent reference documentation.

---

### Phase 2: Rename Detailed Documentation (5 files)

**Lowercase conversion**:
```bash
# 1. Modular monolith rationale
mv docs/MODULAR_MONOLITH_DESIGN.md docs/modular-monolith-rationale.md

# 2. Testing strategy
mv docs/TESTING_STRATEGY.md docs/testing-strategy.md

# 3. Troubleshooting guide
mv docs/TROUBLESHOOTING.md docs/troubleshooting.md

# 4. Product roadmap
mv docs/ROADMAP.md docs/roadmap.md

# 5. FAQ
mv docs/FAQ.md docs/faq.md
```

**Why**: These are detailed guides, not top-level entry points. Lowercase improves scannability.

---

### Phase 3: Update References

**Files with references to renamed documents**:

1. **docs/README.md** (Documentation map)
   - Update all file references to use new names
   - Update table entries

2. **docs/ARCHITECTURE.md**
   - Update cross-references to renamed files

3. **docs/TECHNICAL_DEBT.md**
   - Update "Related Documents" section

4. **docs/SYSTEM_DESIGN.md**
   - Update "Related Documents" section

5. **Root README.md**
   - Update documentation links

6. **docs/working/CHECKPOINT_2025_12_27.md**
   - Update file references

---

## Final Structure

### Permanent Documentation (docs/)

**Top-Level Meta (UPPERCASE - 7 files)**:
```
docs/
├── README.md                    # Documentation map
├── ARCHITECTURE.md              # System architecture
├── SYSTEM_DESIGN.md             # Design specifications
├── TECHNICAL_DEBT.md            # Implementation gaps
├── DEVELOPMENT.md               # Developer guide
├── DEPLOYMENT.md                # Deployment guide
└── SECURITY.md                  # Security guidelines
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

**Subdirectories**:
```
docs/
└── api/
    └── README.md                  # API documentation
```

**Total long-term docs**: 13 files (down from 14)

---

### Working Documentation (docs/working/)

**Status & Planning (11 files)**:
```
docs/working/
├── README.md                                # Lifecycle management
├── CHECKPOINT_2025_12_27.md                 # Latest checkpoint
├── investigation-framework-status.md        # Framework completion (MOVED)
├── DOCUMENTATION_CLEANUP_COMPLETE.md        # Cleanup status
├── DOCUMENTATION_CLEANUP_TODO.md            # Cleanup tasks
├── ENGINE_INTEGRATION_STATUS.md             # Engine integration
├── INTEGRATION_COMPLETION_SUMMARY.md        # Integration summary
├── FEATURE_PARITY_TRACKING.md              # Feature parity (deprecated)
├── FAULTMAVEN_MONO_DEPRECATION_ANALYSIS.md # Deprecation analysis
├── TESTING_IMPLEMENTATION_ROADMAP.md        # Testing roadmap
├── HYPOTHESIS_MANAGER_TEST_COVERAGE.md      # Test coverage
├── MILESTONE_ENGINE_TEST_COVERAGE.md        # Test coverage
└── OODA_ENGINE_TEST_COVERAGE.md             # Test coverage
```

---

## Benefits

### Improved Scannability
- **Top 7 UPPERCASE** files stand out as primary entry points
- **Detailed guides** in lowercase are easier to scan in file lists
- Clear visual hierarchy

### Better Organization
- Temporal documents properly categorized in working/
- Permanent references stay in docs/
- Reduced confusion about document lifecycle

### Consistency
- Follows industry best practices (lowercase for detailed docs)
- Matches proposed naming convention
- Cross-platform compatibility (lowercase directories)

### Reduced Clutter
- 14 UPPERCASE files → 7 UPPERCASE files
- Clearer what's important vs detailed

---

## Implementation Steps

### Step 1: Move Temporal Document
```bash
cd /home/swhouse/product/faultmaven
mv docs/INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md \
   docs/working/investigation-framework-status.md
```

### Step 2: Rename Detailed Documentation
```bash
cd /home/swhouse/product/faultmaven/docs

# Rename 5 files
mv MODULAR_MONOLITH_DESIGN.md modular-monolith-rationale.md
mv TESTING_STRATEGY.md testing-strategy.md
mv TROUBLESHOOTING.md troubleshooting.md
mv ROADMAP.md roadmap.md
mv FAQ.md faq.md
```

### Step 3: Update README.md References
- Update docs/README.md with new file names
- Fix all cross-references in tables

### Step 4: Update Cross-References
- ARCHITECTURE.md
- TECHNICAL_DEBT.md
- SYSTEM_DESIGN.md
- Root README.md
- CHECKPOINT_2025_12_27.md

### Step 5: Consolidate Checkpoint Content
- Remove duplicate gap descriptions from CHECKPOINT
- Reference TECHNICAL_DEBT.md instead
- Keep only checkpoint-specific content

### Step 6: Commit Changes
```bash
git add -A
git commit -m "docs: Reorganize and rename for consistency

- Move INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md to working/
- Rename 5 detailed docs to lowercase-kebab-case
- Update all cross-references
- Consolidate checkpoint duplicate content
- Adopt consistent naming convention (7 UPPERCASE meta, rest lowercase)

Naming convention:
- UPPERCASE: Top 7 entry points only
- lowercase-kebab-case: Detailed guides
- Improved scannability and organization"
```

---

## Verification Checklist

After implementation:

- [ ] All links in docs/README.md work
- [ ] Cross-references in ARCHITECTURE.md point to correct files
- [ ] TECHNICAL_DEBT.md references updated
- [ ] SYSTEM_DESIGN.md references updated
- [ ] Root README.md links work
- [ ] CHECKPOINT references updated
- [ ] No broken markdown links
- [ ] Git history preserved

---

## Approval Required

**Questions for user**:
1. ✅ Approve keeping TECHNICAL_DEBT.md in docs/ (permanent)?
2. ✅ Approve moving INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md to working/?
3. ✅ Approve renaming 5 files to lowercase-kebab-case?
4. ✅ Approve consolidating checkpoint duplicate content?

---

**Status**: Awaiting approval to proceed
**Estimated Effort**: 30 minutes
**Risk**: Low (git preserves history, all changes are renames/moves)
