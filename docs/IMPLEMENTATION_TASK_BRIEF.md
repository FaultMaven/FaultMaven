# FaultMaven Hybrid Architecture Implementation Task Brief

## Overview

This task requires creating a detailed implementation plan to migrate FaultMaven from its current microservices architecture (8 deployable units across 12+ repositories) to a **hybrid modular monolith** (3 deployable units).

**Reference Document**: `docs/ARCHITECTURE_EVALUATION.md` contains the complete architectural analysis, design principles, and rationale.

---

## Architecture Decision Summary

### Current State (8 Deployable Units)
```
fm-api-gateway       → Separate container
fm-auth-service      → Separate container
fm-session-service   → Separate container
fm-case-service      → Separate container
fm-evidence-service  → Separate container
fm-knowledge-service → Separate container (query + ingestion combined)
fm-agent-service     → Separate container
fm-job-worker        → Separate container
```

### Target State (3 Deployable Units)
```
faultmaven           → CONSOLIDATED: Docs + Monolith code + Deploy configs
fm-agent-service     → KEEP: Separate (LLM orchestration)
fm-job-worker        → MODIFY: Add embedding generation from Knowledge Service
```

### Service Mapping

| Current Service | Target Destination | Action Required |
|-----------------|-------------------|-----------------|
| fm-api-gateway | faultmaven/src (middleware) | Fold into FastAPI middleware |
| fm-auth-service | faultmaven/src/faultmaven/modules/auth | Migrate as module |
| fm-session-service | faultmaven/src/faultmaven/modules/session | Migrate as module |
| fm-case-service | faultmaven/src/faultmaven/modules/case | Migrate as module |
| fm-evidence-service | faultmaven/src/faultmaven/modules/evidence | Migrate as module |
| fm-knowledge-service | **SPLIT** | Query path → faultmaven/src/faultmaven/modules/knowledge |
| fm-knowledge-service | **SPLIT** | Ingestion path → fm-job-worker |
| fm-agent-service | fm-agent-service | Keep separate, update to async queue |
| fm-job-worker | fm-job-worker | Add embedding tasks from Knowledge Service |

---

## Repository Consolidation Strategy

### Key Decision: Combine Three Repos Into One

The `faultmaven` repository will become the single source of truth containing:
1. **Documentation** (existing) - `docs/`
2. **Monolith application code** (new) - `src/faultmaven/`
3. **Deployment configurations** (from `faultmaven-deploy`) - `deploy/`

**Rationale**:
- Deploy configs are tightly coupled to application version
- Self-hosted users get everything with one `git clone`
- Standard pattern (most projects include docker-compose.yml)
- Reduces repo count from 12+ to 5

---

## Repositories Involved

### Primary Repository (Consolidation Target)
- **`faultmaven`** - Existing docs repo, will add:
  - Monolith application code (`src/`)
  - Deployment configs from `faultmaven-deploy` (`deploy/`)
  - Dockerfile, pyproject.toml, etc.

### To Be Merged Into `faultmaven`
- `faultmaven-deploy` - Docker Compose, Helm charts → `faultmaven/deploy/`

### To Be Modified
- `fm-agent-service` - Update to consume from Redis queue instead of REST
- `fm-job-worker` - Add embedding generation tasks

### To Be Deprecated (may keep as shared lib temporarily)
- `fm-core-lib` - Functionality absorbed into monolith; deprecate after migration

### To Be Archived (after migration complete)
- `fm-api-gateway`
- `fm-auth-service`
- `fm-session-service`
- `fm-case-service`
- `fm-evidence-service`
- `fm-knowledge-service`
- `faultmaven-deploy` (merged into `faultmaven`)

### Unchanged
- `faultmaven-copilot` (browser extension) - API contracts preserved
- `faultmaven-dashboard` (web UI) - API contracts preserved

---

## Implementation Requirements

### Phase 1: Foundation (Provider Abstraction Layer)

**Goal**: Enable same code to run on SQLite/local (Core) or PostgreSQL/S3 (Enterprise)

Create provider interfaces and implementations:
```
src/providers/
├── interfaces.py      # DataProvider, FileProvider, VectorProvider, IdentityProvider
├── data/
│   ├── sqlite.py      # SQLiteDataProvider
│   └── postgresql.py  # PostgreSQLDataProvider
├── files/
│   ├── local.py       # LocalFileProvider
│   └── s3.py          # S3FileProvider
├── vectors/
│   ├── chromadb.py    # ChromaDBProvider
│   └── pinecone.py    # PineconeProvider
└── identity/
    ├── jwt.py         # JWTIdentityProvider
    └── auth0.py       # Auth0IdentityProvider
```

### Phase 2: Monolith Consolidation

**Goal**: Merge 6 services into modular monolith with strict boundaries

Target structure:
```
faultmaven-core/
├── src/
│   ├── main.py                    # FastAPI app entry point
│   ├── middleware/
│   │   └── gateway.py             # JWT, CORS, rate limiting (from API Gateway)
│   ├── api/
│   │   ├── auth.py                # /v1/auth/* routes
│   │   ├── sessions.py            # /v1/sessions/* routes
│   │   ├── cases.py               # /v1/cases/* routes
│   │   ├── evidence.py            # /v1/evidence/* routes
│   │   └── knowledge.py           # /v1/knowledge/* routes (query only)
│   ├── modules/
│   │   ├── auth/
│   │   │   ├── __init__.py        # Public interface ONLY
│   │   │   ├── service.py
│   │   │   ├── repository.py
│   │   │   ├── models.py          # DTOs
│   │   │   └── orm.py             # Internal ORM models
│   │   ├── session/
│   │   ├── case/
│   │   ├── evidence/
│   │   └── knowledge/             # Query path only
│   ├── infrastructure/
│   │   ├── interfaces.py          # SessionStore, JobQueue, Cache protocols
│   │   └── redis_impl.py          # Redis implementations
│   └── providers/                 # From Phase 1
├── tests/
│   ├── test_architecture.py       # Module boundary enforcement tests
│   └── modules/
├── pyproject.toml                 # With import-linter config
└── Dockerfile
```

**Critical Constraints**:
1. **No shared ORM models** - Each module owns its models
2. **No shared SQLAlchemy sessions** - Each module owns its session factory
3. **DTOs at boundaries** - Only expose Pydantic models in `__init__.py`
4. **Async-safe interfaces** - All public service methods must be async
5. **Import linter enforcement** - CI must fail on cross-module internal imports

### Phase 3: Async AI Communication

**Goal**: Replace synchronous REST with Redis job queue

Changes to `faultmaven-core`:
- Add `AgentClient` that enqueues to Redis instead of HTTP calls
- Add `/v1/agent/chat` endpoint that returns job_id immediately
- Add `/v1/agent/chat/{job_id}` polling endpoint
- Optional: WebSocket support for push notifications

Changes to `fm-agent-service`:
- Replace REST API with Redis queue consumer (RQ or Celery worker)
- Store results in Redis with TTL
- Keep Knowledge search as HTTP call to Core (for RAG context)

### Phase 4: Knowledge Service Split

**Goal**: Separate query path (fast, sync) from ingestion path (slow, async)

Query path → `faultmaven-core/modules/knowledge`:
- Vector similarity search
- Document metadata retrieval
- Collection management

Ingestion path → `fm-job-worker`:
- Text extraction from documents
- Chunking with overlap
- Embedding generation (BGE-M3 / Sentence Transformers)
- Vector upsert to ChromaDB/Pinecone

### Phase 5: Deployment Updates

**Goal**: Simplify deployment configuration

Update `faultmaven-deploy`:
```yaml
# docker-compose.core.yml (before)
services:
  api-gateway:
  auth-service:
  session-service:
  case-service:
  evidence-service:
  knowledge-service:
  agent-service:
  job-worker:
  redis:
  chromadb:

# docker-compose.core.yml (after)
services:
  faultmaven-core:     # Replaces 6 services
  agent-service:       # Unchanged
  job-worker:          # Now includes embeddings
  redis:
  chromadb:
```

---

## Expectations for Implementation Plan

### Deliverables

1. **Phased Task Breakdown**
   - Detailed steps for each phase
   - Dependencies between tasks
   - Parallelization opportunities

2. **File-Level Migration Map**
   - Which files move where
   - Which files need modification
   - Which files get deleted

3. **API Contract Preservation**
   - Mapping of current endpoints to new locations
   - Verification that client apps don't break

4. **Testing Strategy**
   - How to verify each phase works
   - Rollback procedures
   - Integration test approach

5. **Risk Assessment**
   - Potential blockers per phase
   - Mitigation strategies

### Constraints

- **API Compatibility**: External REST API must remain unchanged (same routes, same request/response schemas)
- **Zero Downtime Goal**: Plan should support gradual migration if possible
- **Branch Strategy**: Recommend feature branch approach for each phase

### Success Criteria

| Metric | Target |
|--------|--------|
| Deployable units | 8 → 3 |
| Containers (Core deployment) | 8 → 3 |
| API compatibility | 100% preserved |
| Test coverage | Maintained or improved |
| Module extraction test | Each module runs standalone with mocks |

---

## Key Design Principles to Preserve

The implementation plan must respect these non-negotiable principles from the architecture evaluation:

1. **No Cross-Module Joins** - Enforce via import-linter
2. **Infrastructure as Abstraction** - Redis accessed via `SessionStore`, `JobQueue`, `Cache` interfaces
3. **Event Contract Versioning** - AsyncAPI schemas for queue messages
4. **Extraction-Ready Modules** - Can run any module as standalone service with mocked deps
5. **Provider Abstraction** - Same code runs on SQLite or PostgreSQL via config

---

## Reference Materials

- `docs/ARCHITECTURE_EVALUATION.md` - Complete architectural analysis
- `docs/ARCHITECTURE.md` - Current system documentation
- `docs/API.md` - REST API reference (must be preserved)
- `docs/DEPLOYMENT.md` - Current deployment guide

---

## Questions for Planning Agent

1. Should we create `faultmaven-core` as a fresh repo or fork from an existing service?
2. What's the recommended order for migrating modules (Auth first? Case first?)?
3. How do we handle the Knowledge Service split atomically?
4. Should Agent Service changes happen before or after Core consolidation?
5. What's the testing strategy during the transition period (running both old and new)?
