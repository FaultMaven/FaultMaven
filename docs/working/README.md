# Working Documentation

**Temporary planning, status tracking, and work-in-progress documents.**

This folder contains **short-term documentation** that supports active development work but is not permanent reference material.

---

## Purpose

Documents in this folder are:

- ✅ **Temporary** - Will be deleted or archived when work is complete
- ✅ **Planning** - Support active development or migration work
- ✅ **Status Tracking** - Track progress on specific initiatives
- ✅ **Work-in-Progress** - Drafts or analysis for ongoing work

---

## Lifecycle

### When to Add Documents Here

- Feature implementation roadmaps
- Integration status reports
- Test coverage tracking (temporary)
- Documentation cleanup tracking
- Migration/refactoring plans
- Gap analysis (superseded by TECHNICAL_DEBT.md)

### When to Remove Documents

Documents should be **deleted** or **archived** when:

1. **Work is complete** - Feature implemented, migration done
2. **Superseded** - Information moved to permanent docs
3. **No longer relevant** - Approach abandoned or changed

### Deletion Markers

Documents may include comments indicating when they should be removed:

```markdown
<!-- DELETE WHEN: Investigation framework integration is 100% complete -->
<!-- DELETE WHEN: All microservices documentation has been updated -->
```

---

## Current Documents

### Checkpoints

- **CHECKPOINT_2025_12_27.md** - Latest checkpoint snapshot
  - Delete when: Superseded by next major milestone

### Framework Status

- **investigation-framework-status.md** - Investigation framework integration status
  - Delete when: Framework 100% complete (move final summary to ARCHITECTURE.md)

### Documentation Management

- **documentation-analysis.md** - Documentation organization analysis
  - Delete when: All recommendations implemented
- **DOCUMENTATION_REORGANIZATION_PLAN.md** - Reorganization plan
  - Delete when: Plan fully executed
- **DOCUMENTATION_CLEANUP_COMPLETE.md** - Completion status
  - Delete when: Documentation consolidation is fully accepted
- **DOCUMENTATION_CLEANUP_TODO.md** - Cleanup tasks
  - Delete when: All tasks completed and verified

### Integration & Status

- **ENGINE_INTEGRATION_STATUS.md** - Engine integration tracking
  - Delete when: All engines integrated (move summary to ARCHITECTURE.md)
- **INTEGRATION_COMPLETION_SUMMARY.md** - Integration summary
  - Delete when: Integration complete (move to archive)

### Feature Parity

- **FEATURE_PARITY_TRACKING.md** - Feature parity vs FaultMaven-Mono
  - Delete when: Superseded by TECHNICAL_DEBT.md (already deprecated)
  - Note: TECHNICAL_DEBT.md is now the authoritative gap tracker

### Testing

- **TESTING_IMPLEMENTATION_ROADMAP.md** - Testing roadmap
  - Delete when: Roadmap complete or moved to testing-strategy.md
- **HYPOTHESIS_MANAGER_TEST_COVERAGE.md** - Test coverage report
  - Delete when: Coverage integrated into CI reporting
- **MILESTONE_ENGINE_TEST_COVERAGE.md** - Test coverage report
  - Delete when: Coverage integrated into CI reporting
- **OODA_ENGINE_TEST_COVERAGE.md** - Test coverage report
  - Delete when: Coverage integrated into CI reporting

### Analysis

- **FAULTMAVEN_MONO_DEPRECATION_ANALYSIS.md** - Deprecation analysis
  - Delete when: Decision finalized and documented in roadmap.md

---

## Best Practices

1. **Add deletion markers** - Help future maintainers know when to clean up
2. **Link to permanent docs** - When work is done, update permanent docs
3. **Archive if valuable** - Move to `archive/` if historically useful
4. **Delete if transient** - Remove purely temporary status tracking

---

## Related Folders

- **[../ (parent)](../README.md)** - Permanent long-term documentation
- **[../archive/](../archive/)** - Historical reference documents

---

**Last Updated**: 2025-12-27
**Current Documents**: 15
**Purpose**: Active development planning and status tracking
