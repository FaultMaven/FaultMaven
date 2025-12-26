# Documentation Cleanup - Remaining Tasks

**Created**: 2025-12-26
**Status**: In Progress

---

## Completed ✅

1. **Archived microservices planning documents** (to `docs/archive/2025/12/`)
   - `MIGRATION_PHASE_5_PLAN.md`
   - `MIGRATION_PHASE_6_PLAN.md`
   - `ARCHITECTURE_EVALUATION.md`
   - `IMPLEMENTATION_TASK_BRIEF.md`

2. **Updated ARCHITECTURE.md**
   - Completely rewritten for modular monolith
   - Removed all microservices references
   - Added module-by-module architecture details
   - Documented investigation framework integration status

---

## Remaining Tasks

### High Priority

#### 1. Update DEVELOPMENT.md
- Remove microservices development instructions
- Update for single-repo development workflow
- Document module development patterns
- Update testing instructions for monolith
- Reference: `/home/swhouse/product/FaultMaven-Mono/docs/development/`

#### 2. Update README.md
- Model after `FaultMaven-Mono/README.md` structure
- Replace microservices architecture description with modular monolith
- Update quick start for single application (port 8000, not 8090)
- Remove repository table (no longer multiple repos)
- Add current status section (already exists, verify accuracy)
- Update badges and metrics

#### 3. Replace API.md with Auto-Generated Specs
**Steps**:
1. Copy `FaultMaven-Mono/scripts/generate_openapi_spec.py` to `scripts/`
2. Create `docs/api/` directory
3. Run script to generate:
   - `docs/api/openapi.locked.yaml` - Versioned API spec
   - `docs/api/openapi.current.yaml` - Working spec
4. Delete manual `docs/API.md`
5. Create `docs/api/README.md` explaining auto-generated specs
6. Add CI/CD integration for breaking change detection

**Script location**: `/home/swhouse/product/FaultMaven-Mono/scripts/generate_openapi_spec.py`

---

### Medium Priority

#### 4. Update ROADMAP.md
- Review current roadmap items
- Remove microservices migration items (completed)
- Update for monolith evolution roadmap
- Add investigation framework completion (Issue #5)

#### 5. Update DEVELOPMENT.md References
Check and update these sections:
- Local development setup (single service, not multiple)
- Port configuration (8000, not 8001-8006)
- Database initialization (single database)
- Testing strategy (no inter-service testing)

---

### Low Priority

#### 6. Archive Additional Temporal Documents
Consider archiving to `docs/archive/2025/12/`:
- `MIGRATION_STATUS.md` - Historical status
- `MIGRATION_PHASE_4_COMPLETE.md` - Completed milestone
- `MIGRATION_PLAN.md` - Historical plan
- `PHASE_1_COMPLETE.md` - Historical milestone
- `PHASE_1_COMPLETE_NEXT_STEPS.md` - Historical milestone

**Keep**:
- `TESTING_STRATEGY.md` - Still relevant
- `TESTING_IMPLEMENTATION_ROADMAP.md` - Future work

#### 7. Fix Markdown Linting Issues
Run markdown linter and fix warnings in:
- `ARCHITECTURE.md` (blank lines around headings/lists)
- Any other updated documents

---

## Implementation Guide

### Auto-Generated API Documentation

```bash
# 1. Copy script
cp /home/swhouse/product/FaultMaven-Mono/scripts/generate_openapi_spec.py \
   /home/swhouse/product/faultmaven/scripts/

# 2. Create API docs directory
mkdir -p /home/swhouse/product/faultmaven/docs/api

# 3. Generate specs
cd /home/swhouse/product/faultmaven
python scripts/generate_openapi_spec.py

# 4. Delete manual API.md
rm docs/API.md

# 5. Create README explaining the auto-generated approach
# (See template below)
```

### docs/api/README.md Template

```markdown
# FaultMaven API Documentation

This directory contains auto-generated OpenAPI specifications for the FaultMaven API.

## Files

- `openapi.locked.yaml` - Versioned API specification (committed to git)
- `openapi.current.yaml` - Current working specification (generated, not committed)

## Generating API Specs

```bash
python scripts/generate_openapi_spec.py
```

This script:
1. Generates current OpenAPI spec from FastAPI application
2. Compares with locked spec to detect API changes
3. Reports breaking vs non-breaking changes
4. Helps maintain API compatibility

## Breaking Change Detection

The script automatically detects:
- 🔴 **Breaking Changes**: Removed endpoints, removed fields, new required parameters
- 🟢 **Non-Breaking Changes**: New endpoints, new optional fields, deprecated features

## Updating Locked Spec

After reviewing changes:
```bash
cp docs/api/openapi.current.yaml docs/api/openapi.locked.yaml
git add docs/api/openapi.locked.yaml
git commit -m "Update API specification to v<version>"
```

## Interactive API Documentation

When running FaultMaven locally:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
```

---

## Reference Documents

### FaultMaven-Mono Structure
Key documents to reference:
- `/home/swhouse/product/FaultMaven-Mono/README.md` - README structure
- `/home/swhouse/product/FaultMaven-Mono/docs/development/` - Development guides
- `/home/swhouse/product/FaultMaven-Mono/scripts/generate_openapi_spec.py` - API generation

### Current State
- Investigation framework: 80% integrated (4/5 engines)
- Architecture: Modular monolith (6 modules)
- Test pass rate: 148/148 (100%)
- Code coverage: 47%

---

## Commit Strategy

1. **Commit 1**: Archive microservices docs + update ARCHITECTURE.md (current progress)
2. **Commit 2**: Update DEVELOPMENT.md + ROADMAP.md
3. **Commit 3**: Replace README.md
4. **Commit 4**: Setup auto-generated API docs
5. **Commit 5**: Final cleanup (archive remaining temporal docs, fix linting)

---

**Next Action**: Complete tasks 1-3, then commit batch 2
