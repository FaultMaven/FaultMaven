# FaultMaven Modular Monolith Implementation Task Brief

## Overview

This task requires creating a detailed implementation plan to migrate FaultMaven from its current microservices architecture to a **modular monolith with background worker**.

| Metric | Current | Target |
|--------|---------|--------|
| Deployable units | 8 | 2 |
| Repositories | 12+ | 4 |
| Containers (Core) | 8+ | 2 |

**Reference Documents**:
- `docs/MODULAR_MONOLITH_DESIGN.md` - Target architecture specification
- `docs/ARCHITECTURE_EVALUATION.md` - Migration rationale and evaluation

---

## Migration Summary

### Service Mapping

| Current Service | Target | Action |
|-----------------|--------|--------|
| fm-api-gateway | Monolith middleware | Fold into FastAPI middleware |
| fm-auth-service | `modules/auth` | Migrate as module |
| fm-session-service | `modules/session` | Migrate as module |
| fm-case-service | `modules/case` | Migrate as module |
| fm-evidence-service | `modules/evidence` | Migrate as module |
| fm-knowledge-service | **SPLIT** | Query → `modules/knowledge`, Ingest → Job Worker |
| fm-agent-service | `modules/agent` | Migrate as module with LLMProvider |
| fm-job-worker | fm-job-worker | Add embedding tasks |

### Repository Changes

| Repository | Action |
|------------|--------|
| `faultmaven` | **Primary target** - Add `src/faultmaven/` and `deploy/` |
| `faultmaven-deploy` | Merge into `faultmaven/deploy/`, then archive |
| `fm-job-worker` | Modify to add embedding generation |
| `fm-core-lib` | Deprecate after migration |
| `fm-*-service` (7 repos) | Archive after migration |
| `faultmaven-copilot` | Unchanged (API contracts preserved) |
| `faultmaven-dashboard` | Unchanged (API contracts preserved) |

---

## Implementation Phases

### Phase 1: Foundation (Provider Abstraction Layer)

**Goal**: Create provider interfaces before consolidation

**Tasks**:
1. Create `src/faultmaven/providers/interfaces.py` with all Protocol definitions
2. Implement Core providers (SQLite, Local Files, ChromaDB, JWT)
3. Implement Enterprise providers (PostgreSQL, S3, Pinecone, Auth0)
4. Create LLMProvider implementations (OpenAI, Anthropic, Ollama)
5. Add configuration-based provider selection
6. Test both Core and Enterprise profiles

**Outputs**:
```
src/faultmaven/providers/
├── interfaces.py
├── data/{sqlite.py, postgresql.py}
├── files/{local.py, s3.py}
├── vectors/{chromadb.py, pinecone.py}
├── identity/{jwt.py, auth0.py}
└── llm/{openai.py, anthropic.py, ollama.py}
```

### Phase 2: Infrastructure Abstractions

**Goal**: Abstract Redis access through interfaces

**Tasks**:
1. Create `infrastructure/interfaces.py` with SessionStore, JobQueue, Cache, ResultStore
2. Create `infrastructure/redis_impl.py` with Redis implementations
3. Create in-memory implementations for testing

**Outputs**:
```
src/faultmaven/infrastructure/
├── interfaces.py
├── redis_impl.py
└── memory_impl.py  # For testing
```

### Phase 3: Module Migration

**Goal**: Migrate each service as a module with strict boundaries

**Order** (suggested - dependencies flow down):
1. Auth module (no module dependencies)
2. Session module (depends on Auth)
3. Case module (depends on Session)
4. Evidence module (depends on Case)
5. Knowledge module (query path only)
6. Agent module (depends on Knowledge, uses LLMProvider)

**Per-Module Tasks**:
1. Create module directory structure
2. Migrate service.py, repository.py, models.py
3. Create `__init__.py` with public interface only
4. Convert to async if not already
5. Wire up provider dependencies
6. Add module-level tests
7. Verify import-linter passes

**Module Structure**:
```
modules/{name}/
├── __init__.py     # Public interface ONLY
├── service.py      # Business logic
├── repository.py   # Data access
├── models.py       # DTOs (Pydantic)
└── orm.py          # Internal ORM models
```

### Phase 4: API Layer & Middleware

**Goal**: Create unified API layer with gateway middleware

**Tasks**:
1. Create `middleware/gateway.py` (JWT, CORS, rate limiting)
2. Create API route files for each module
3. Wire up dependency injection
4. Verify all existing endpoints work

**Outputs**:
```
src/faultmaven/
├── main.py
├── middleware/gateway.py
└── api/{auth.py, sessions.py, cases.py, evidence.py, knowledge.py, agent.py}
```

### Phase 5: Knowledge Service Split

**Goal**: Separate query path from ingestion path

**Tasks**:
1. Identify all ingestion-related code in fm-knowledge-service
2. Move embedding generation to fm-job-worker
3. Move text extraction to fm-job-worker
4. Keep vector search in monolith's knowledge module
5. Define job queue event schemas (AsyncAPI)

### Phase 6: Job Worker Updates

**Goal**: Add embedding generation to Job Worker

**Tasks**:
1. Add embedding generation tasks (from Knowledge Service)
2. Add text extraction tasks
3. Define event contracts with versioning
4. Test queue communication with monolith

### Phase 7: Deployment Consolidation

**Goal**: Merge faultmaven-deploy into faultmaven

**Tasks**:
1. Copy Docker Compose files to `faultmaven/deploy/`
2. Update to reference new monolith image
3. Copy Helm charts to `faultmaven/deploy/kubernetes/`
4. Update chart values for 2-container deployment
5. Test Core deployment profile
6. Test Enterprise deployment profile

---

## Critical Constraints

### Module Boundary Rules

| Rule | Enforcement |
|------|-------------|
| No cross-module ORM imports | `import-linter` in CI |
| No shared DB sessions | Code review, architecture tests |
| DTOs at boundaries only | Type checking, linter |
| All public methods async | Type checking |

### API Compatibility

- All existing REST endpoints must work unchanged
- Same request/response schemas
- Same authentication flow
- Client apps (copilot, dashboard) must not require changes

### Testing Requirements

- Each module must be testable in isolation with mocked dependencies
- Architecture tests must verify module boundaries
- Provider contract tests must pass for all implementations

---

## Deliverables Expected from Planning Agent

### 1. Phased Task Breakdown
- Detailed steps for each phase
- Dependencies between tasks
- Parallelization opportunities
- Estimated effort per task

### 2. File-Level Migration Map
- Source file → destination file mapping
- Files requiring modification
- Files to delete

### 3. API Contract Verification
- Endpoint mapping (old service → new module)
- Test strategy for API compatibility

### 4. Testing Strategy
- Unit test approach per module
- Integration test approach
- Rollback procedures

### 5. Risk Assessment
- Potential blockers per phase
- Mitigation strategies
- Contingency plans

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Deployable units | 8 → 2 |
| Repositories | 12+ → 4 |
| API compatibility | 100% preserved |
| Test coverage | Maintained or improved |
| Module extraction test | Each module runs standalone with mocks |
| LLM provider flexibility | Works with OpenAI, Anthropic, Ollama |
| import-linter | Passes in CI |

---

## Questions for Planning Agent

1. Should we build incrementally on `faultmaven` or scaffold fresh then migrate?
2. What's the optimal order for migrating modules given their dependencies?
3. How do we handle the Knowledge Service split atomically?
4. What's the testing strategy during transition (parallel running)?
5. How do we preserve git history when absorbing fm-agent-service?
6. Should we use feature flags during migration for gradual rollout?
