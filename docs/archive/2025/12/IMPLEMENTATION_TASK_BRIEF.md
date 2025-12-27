# FaultMaven Modular Monolith Implementation Task Brief

## Overview

This task requires creating a detailed implementation plan to migrate FaultMaven from its current microservices architecture to a **true modular monolith**.

| Metric | Current | Target |
|--------|---------|--------|
| Repositories | 12+ | 2 |
| Deployable Units | 8 | 1 |
| Containers | 8+ | 1 |
| Processes | 8+ | 1 |

**Reference Document**: `docs/MODULAR_MONOLITH_DESIGN.md` - Target architecture specification

---

## Migration Summary

### Service Mapping

| Current Service | Target | Action |
|-----------------|--------|--------|
| fm-api-gateway | Middleware | Fold into FastAPI middleware |
| fm-auth-service | `modules/auth` | Migrate as module |
| fm-session-service | `modules/session` | Migrate as module |
| fm-case-service | `modules/case` | Migrate as module |
| fm-evidence-service | `modules/evidence` | Migrate as module |
| fm-knowledge-service | `modules/knowledge` | Migrate as module (query + ingestion) |
| fm-agent-service | `modules/agent` | Migrate as module with LLMProvider |
| fm-job-worker | In-process tasks | Absorb into modules (asyncio.create_task) |

### Repository Changes

| Repository | Action |
|------------|--------|
| `faultmaven` | **Primary target** - Add `src/faultmaven/`, `dashboard/`, `deploy/` |
| `faultmaven-dashboard` | Merge into `faultmaven/dashboard/` |
| `faultmaven-deploy` | Merge into `faultmaven/deploy/` |
| `fm-*-service` (7 repos) | Archive after migration |
| `fm-job-worker` | Archive (functionality absorbed) |
| `fm-core-lib` | Deprecate (absorbed into monolith) |
| `faultmaven-copilot` | Unchanged (separate distribution) |

---

## Implementation Phases

### Phase 1: Foundation (Provider Abstraction Layer)

**Goal**: Create provider interfaces before consolidation

**Tasks**:
1. Create `src/faultmaven/providers/interfaces.py` with all Protocol definitions
2. Implement Core providers (SQLite, Local Files, ChromaDB, JWT)
3. Implement Enterprise providers (PostgreSQL, S3, Pinecone, Auth0)
4. Create LLMProvider implementations (OpenAI, Anthropic, Ollama)
5. Create EmbeddingProvider implementations (OpenAI, Cohere, local)
6. Add configuration-based provider selection
7. Test all profiles

**Outputs**:
```
src/faultmaven/providers/
├── interfaces.py
├── data/{sqlite.py, postgresql.py}
├── files/{local.py, s3.py}
├── vectors/{chromadb.py, pinecone.py}
├── identity/{jwt.py, auth0.py}
├── llm/{openai.py, anthropic.py, ollama.py}
└── embedding/{openai.py, cohere.py, local.py}
```

### Phase 2: Module Migration

**Goal**: Migrate each service as a module with strict boundaries

**Order** (dependencies flow down):
1. Auth module (no module dependencies)
2. Session module (depends on Auth)
3. Case module (depends on Session)
4. Evidence module (depends on Case)
5. Knowledge module (query + ingestion, uses EmbeddingProvider)
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

### Phase 3: API Layer & Middleware

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

### Phase 4: Async Task Patterns

**Goal**: Implement in-process async patterns for long-running operations

**Tasks**:
1. Implement async pattern for Agent chat (submit → poll)
2. Implement async pattern for Knowledge ingestion (upload → status)
3. Add in-process scheduler for cleanup tasks (APScheduler)
4. Store job status in memory or Redis

**Patterns**:
```python
# Long-running task
@router.post("/v1/agent/chat")
async def submit_chat(request: ChatRequest):
    job_id = str(uuid4())
    asyncio.create_task(process_chat(job_id, request))
    return {"job_id": job_id, "status": "processing"}

@router.get("/v1/agent/chat/{job_id}")
async def get_result(job_id: str):
    return await get_job_result(job_id)
```

### Phase 5: Dashboard Integration

**Goal**: Bundle dashboard into monolith

**Tasks**:
1. Copy `faultmaven-dashboard` source to `faultmaven/dashboard/`
2. Create multi-stage Dockerfile (build dashboard, then Python)
3. Configure FastAPI to serve static files at `/`
4. Verify dashboard works with bundled API

**Dockerfile**:
```dockerfile
FROM node:20 AS dashboard
WORKDIR /app/dashboard
COPY dashboard/ .
RUN npm ci && npm run build

FROM python:3.12-slim
COPY --from=dashboard /app/dashboard/dist /app/static/dashboard
COPY src/ /app/src/
RUN pip install .
CMD ["uvicorn", "faultmaven.main:app", "--host", "0.0.0.0"]
```

### Phase 6: Deployment Consolidation

**Goal**: Merge deploy configs and simplify

**Tasks**:
1. Copy Docker Compose files to `faultmaven/deploy/`
2. Update to single container deployment
3. Copy Helm charts to `faultmaven/deploy/kubernetes/`
4. Update chart values for single container
5. Test all deployment profiles

**docker-compose.yml**:
```yaml
services:
  faultmaven:
    image: faultmaven:latest
    environment:
      DATABASE_URL: sqlite:///data/faultmaven.db
      LLM_PROVIDER: openai
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    volumes:
      - ./data:/data
    ports:
      - "8000:8000"
```

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
- Copilot must not require changes

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
| Repositories | 12+ → 2 |
| Deployable units | 8 → 1 |
| Containers | 8+ → 1 |
| API compatibility | 100% preserved |
| Test coverage | Maintained or improved |
| Module extraction test | Each module runs standalone with mocks |
| Run from source | `pip install . && uvicorn faultmaven.main:app` works |
| Single docker run | `docker run faultmaven:latest` works |

---

## Questions for Planning Agent

1. Should we build incrementally on `faultmaven` or scaffold fresh then migrate?
2. What's the optimal order for migrating modules given their dependencies?
3. How do we preserve git history when absorbing multiple repos?
4. What's the testing strategy during transition (parallel running)?
5. Should we use feature flags during migration for gradual rollout?
