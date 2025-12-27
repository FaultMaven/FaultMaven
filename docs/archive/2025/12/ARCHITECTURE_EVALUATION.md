# FaultMaven Architecture Evaluation: Microservices vs Modular Monolith

## Executive Summary

This document evaluates FaultMaven's current microservices architecture against a Modular Monolith pattern, considering the product's business model, development context, and operational requirements.

### Strategic Position: Monolith-First, Service-Ready

FaultMaven adopts a **monolith-first, service-ready** architecture:

- **Consolidated to match current scale** - 7 services → 1 modular monolith
- **Preserved extraction paths for enterprise growth** - strict module boundaries enable future decomposition
- **Only genuinely independent background processing separate** - Job Worker handles async tasks

This is not "moving away from microservices" — it's **right-sizing architecture to business reality** while maintaining the option to scale components independently when justified.

### Recommended Grouping

| Destination | Services | Rationale |
|-------------|----------|-----------|
| **Monolith** | API Gateway (middleware), Auth, Session, Case, Evidence, Knowledge (query path), Agent | Same failure domain, critical path, LLM is external |
| **Separate** | Job Worker | CPU-intensive embeddings, background processing, async |

**Key Insights**:
1. **Agent Service belongs in monolith** - LLM providers (OpenAI, Anthropic) are external. Agent just orchestrates HTTP calls—no different from calling Stripe or any external API. If Agent fails, the app is broken anyway (same failure domain).
2. **Knowledge Service must be split** - Vector search (query path) belongs in the monolith; embedding generation (ingestion path) belongs in the Job Worker.

**Result**: 8 deployable units → 2 (75% reduction)

---

## 1. Current Architecture Analysis

### 1.1 Service Inventory

FaultMaven consists of 7 microservices across 12+ repositories:

| Service | Responsibility | Coupling Level |
|---------|----------------|----------------|
| API Gateway | Routing, JWT validation | High (calls all services) |
| Auth Service | User registration, login | Low |
| Session Service | Session management | Medium (Auth dependency) |
| Case Service | Case CRUD, messages | Medium (Session dependency) |
| Knowledge Service | Document embeddings, search | Low |
| Evidence Service | File uploads | Medium (Case dependency) |
| Agent Service | LLM orchestration | High (calls KB, Case, LLM) |
| Job Worker | Async processing | Medium (KB dependency) |

### 1.2 Observed Coupling Patterns

```
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                            │
│  (JWT validation, routing - calls ALL downstream services)  │
└────────────┬────────────────────────────────────────────────┘
             │
    ┌────────┴────────┬─────────────┬─────────────┬──────────┐
    ▼                 ▼             ▼             ▼          ▼
┌────────┐     ┌──────────┐   ┌──────────┐  ┌─────────┐ ┌────────┐
│  Auth  │────▶│ Session  │   │   Case   │◀─│Evidence │ │   KB   │
└────────┘     └──────────┘   └────┬─────┘  └─────────┘ └───┬────┘
                                   │                        │
                                   ▼                        ▼
                              ┌─────────┐            ┌───────────┐
                              │  Agent  │───────────▶│Job Worker │
                              │(LLM Hub)│            └───────────┘
                              └─────────┘
```

**Key Observations:**
- Auth → Session → Case → Evidence forms a tight dependency chain
- Agent Service is the orchestration hub (high fan-out)
- Most inter-service calls are **synchronous REST**
- Shared library (`fm-core-lib`) indicates common patterns

---

## 2. Business Model Assessment

### 2.1 Open-Core Model

| Aspect | FaultMaven Core | FaultMaven Enterprise |
|--------|-----------------|----------------------|
| License | Apache 2.0 (Open Source) | Proprietary SaaS |
| Deployment | Self-hosted (Docker Compose) | Managed Kubernetes |
| Target | Individual users, small teams | Enterprise teams |
| Revenue | Community/adoption | Direct subscription |

### 2.2 Implications for Architecture

**Self-Hosted (Core) Requirements:**
- Simple deployment (fewer moving parts = easier adoption)
- Low operational overhead for users
- Works on modest hardware (4GB RAM recommended)
- Single-user to small team scale

**Enterprise SaaS Requirements:**
- Multi-tenancy and isolation
- Horizontal scaling
- High availability (99.9% SLA)
- Independent service scaling

### 2.3 Business Model Verdict

| Criterion | Microservices Fit | Modular Monolith Fit |
|-----------|-------------------|---------------------|
| Core self-hosted simplicity | ❌ Poor | ✅ Excellent |
| Enterprise scaling | ✅ Good | ⚠️ Adequate |
| Adoption friction | ❌ High (7 services) | ✅ Low (1 binary) |
| Operational cost for users | ❌ High | ✅ Low |

**The open-core model with self-hosted deployment strongly favors simplicity.** Microservices add friction for Core users who must orchestrate 7+ containers.

---

## 3. Development Model Assessment

### 3.1 Repository Structure

Current: **12+ separate repositories**
- `fm-auth-service`, `fm-session-service`, `fm-case-service`, etc.
- `fm-core-lib` (shared library)
- `faultmaven-deploy` (orchestration)
- Client applications (2 repos)

### 3.2 Development Workflow Implications

| Activity | Microservices Impact | Monolith Comparison |
|----------|---------------------|---------------------|
| Cross-service feature | Multiple PRs, version coordination | Single PR |
| Local development | Run 7+ services (Docker Compose) | Run 1 process |
| Integration testing | Complex multi-container setup | Simple test harness |
| Debugging | Distributed tracing required | Standard debugger |
| Dependency updates | Coordinate across repos | Single update |
| CI/CD | 7+ pipelines | 1 pipeline |

### 3.3 Shared Library Anti-Pattern

The existence of `fm-core-lib` reveals tight coupling:
- Common Pydantic models shared across services
- Database client utilities
- Error handling patterns
- Type definitions

**This is a "Distributed Monolith" indicator** - the services are not truly independent; they share significant code and must be versioned together.

### 3.4 Team Size Considerations

Based on the architecture documentation, FaultMaven appears to be developed by a **small team** (likely < 10 developers):
- Single owner per repository pattern
- No team-based service ownership mentioned
- Shared patterns suggest single design authority

**Conway's Law Application:**
> "Organizations design systems that mirror their communication structure."

A small, collaborative team is better served by a unified codebase. Microservices excel when **independent teams** need to deploy independently.

### 3.5 Development Model Verdict

| Criterion | Current (Microservices) | Modular Monolith |
|-----------|------------------------|------------------|
| Development velocity | ❌ Slower (multi-repo) | ✅ Faster |
| Cognitive overhead | ❌ High (7 services) | ✅ Lower |
| Onboarding complexity | ❌ High | ✅ Lower |
| Feature iteration speed | ❌ Slower | ✅ Faster |
| Team autonomy | ⚠️ Premature optimization | ✅ Sufficient |

---

## 4. Technical Trade-off Analysis

### 4.1 Microservices Benefits (Current State)

| Benefit | Realized in FaultMaven? | Assessment |
|---------|------------------------|------------|
| Independent deployment | ⚠️ Partial | Services still tightly coupled |
| Technology heterogeneity | ❌ No | All Python/FastAPI |
| Independent scaling | ⚠️ Partial | Only Agent/KB truly need it |
| Fault isolation | ✅ Yes | LLM failures don't crash Auth |
| Team autonomy | ❌ No | Small team, shared patterns |

### 4.2 Microservices Costs (Current State)

| Cost | Impact on FaultMaven |
|------|---------------------|
| Network latency | Every request traverses multiple services |
| Distributed transactions | Case + Evidence + Messages = complex |
| Operational complexity | 7 services × monitoring, logging, alerting |
| Debugging difficulty | Distributed tracing required |
| Deployment coordination | Services must be compatible |
| Infrastructure overhead | 7 containers minimum |

### 4.3 Domain Boundary Analysis

Examining the actual domain boundaries:

```
┌─────────────────────────────────────────────────────────────────┐
│                    CORE CRUD DOMAIN                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐           │
│  │  Auth   │  │ Session │  │  Case   │  │ Evidence │           │
│  └─────────┘  └─────────┘  └─────────┘  └──────────┘           │
│                                                                 │
│  - Simple CRUD operations                                       │
│  - Transactional consistency needed                             │
│  - Low computational complexity                                 │
│  - Tight temporal coupling (login → session → case → evidence)  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                 COMPUTE-INTENSIVE DOMAIN                        │
│  ┌───────────────┐    ┌─────────────────┐                      │
│  │ Agent Service │    │Knowledge Service│                      │
│  │   (LLM Hub)   │    │ (Embeddings/RAG)│                      │
│  └───────────────┘    └─────────────────┘                      │
│                                                                 │
│  - CPU/memory intensive                                         │
│  - External API dependencies (LLM providers)                    │
│  - Different scaling characteristics                            │
│  - Async processing beneficial                                  │
└─────────────────────────────────────────────────────────────────┘
```

**The domains have fundamentally different characteristics:**
- Core CRUD: Latency-sensitive, transactional, simple operations
- Compute Domain: Throughput-oriented, async-friendly, resource-intensive

### 4.4 Scalability Analysis

| Service | Scaling Need | Microservice Justified? |
|---------|-------------|------------------------|
| API Gateway | Horizontal (stateless) | ⚠️ Could be app layer |
| Auth Service | Low (infrequent) | ❌ No |
| Session Service | Medium (Redis-backed) | ❌ No (Redis handles it) |
| Case Service | Medium (CRUD) | ❌ No |
| Evidence Service | Medium (I/O bound) | ❌ No |
| Knowledge Service | **High (embeddings)** | ✅ Yes |
| Agent Service | **High (LLM calls)** | ✅ Yes |
| Job Worker | High (async) | ✅ Yes (already separate) |

**Only 2-3 services genuinely benefit from independent scaling.**

---

## 5. Recommended Architecture: Hybrid Modular Monolith

### 5.0 Critical Decision: Service Grouping Analysis

The most important architectural decision is determining which services belong in the monolith vs. remain separate. This analysis evaluates each service against three dimensions: **Business**, **Operational**, and **Development** requirements.

#### 5.0.1 Service-by-Service Analysis

| Service | Business Criticality | Operational Profile | Development Velocity | Verdict |
|---------|---------------------|---------------------|---------------------|---------|
| **API Gateway** | Cross-cutting | Stateless, low compute | Stable | → Middleware |
| **Auth Service** | Core | Low frequency, bursty | Stable | → Monolith |
| **Session Service** | Core | Medium, Redis-backed | Stable | → Monolith |
| **Case Service** | Core | Medium, CRUD | Active | → Monolith |
| **Evidence Service** | Core | I/O bound (files) | Moderate | → Monolith |
| **Knowledge Service** | Core | **SPLIT** (see below) | Active | → **SPLIT** |
| **Agent Service** | Differentiator | Network I/O (LLM external) | Very Active | → **Monolith** |
| **Job Worker** | Support | Background, CPU-bound | Moderate | → Separate |

#### 5.0.2 The Knowledge Service Must Be Split

**Critical Insight**: The Knowledge Service performs two fundamentally different operations:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Knowledge Service (Current)                       │
├─────────────────────────────────┬───────────────────────────────────────┤
│      QUERY PATH                 │         INGESTION PATH                │
│  (Vector Search)                │      (Embedding Generation)           │
├─────────────────────────────────┼───────────────────────────────────────┤
│ • Fast (10-50ms)                │ • Slow (seconds to minutes)           │
│ • Synchronous                   │ • Asynchronous                        │
│ • Read-heavy                    │ • Write-heavy, CPU-intensive          │
│ • Scales with query load        │ • Scales with document volume         │
│ • User-facing latency           │ • Background processing               │
├─────────────────────────────────┼───────────────────────────────────────┤
│ → MONOLITH MODULE               │ → JOB WORKER                          │
│   (direct vector DB access)     │   (async embedding tasks)             │
└─────────────────────────────────┴───────────────────────────────────────┘
```

**Why This Matters**:
- Keeping them together forces unnecessary complexity (async handling in a sync service)
- Query path is just a database call (like SQL) - no reason to be separate
- Ingestion is genuinely async - belongs with other background tasks

#### 5.0.3 Why Agent Service Belongs in the Monolith

**Original reasoning for separation** (now rejected):
- Resource isolation (GPU/memory spikes)
- Independent scaling
- Different failure mode

**Why that reasoning is flawed**:

| Factor | Reality |
|--------|---------|
| **Heavy compute** | Done by OpenAI/Anthropic/external LLM providers, not by us |
| **Agent Service work** | HTTP orchestration, prompt construction, response parsing |
| **Resource profile** | Network I/O bound, not CPU/GPU bound |
| **Scaling trigger** | If Agent needs scaling, whole app does too (critical path) |
| **Failure impact** | Agent down = app down anyway (not an isolated failure domain) |

The Agent Service is essentially an **orchestration module** making external API calls—no different from a module calling Stripe, Twilio, or any other external service.

**What about local LLMs (Ollama, vLLM)?**

The separation is in the **design** (LLMProvider abstraction), not in the **deployment**:

```
Monolith → LLMProvider interface → OpenAI API
                                 → Anthropic API
                                 → Local Ollama (HTTP to localhost:11434)
```

Local vs cloud is **configuration**, not architecture. The monolith makes HTTP calls either way. Ollama runs as infrastructure (like Postgres or Redis), not as an application service we'd extract.

#### 5.0.5 Domain Coupling Analysis

```
TIGHT COUPLING (should be together):
┌─────────────────────────────────────────────────────────────────┐
│                    Core Platform Domain                         │
│                                                                 │
│  User Journey: Register → Login → Create Case → Upload Evidence │
│                                     ↓                           │
│  Auth ←──→ Session ←──→ Case ←──→ Evidence                     │
│    │                      │           │                         │
│    └──── all require ─────┴───────────┴── transactional ───────│
│                                                                 │
│  + Knowledge (Query) - just another data source for cases       │
│  + Agent - orchestrates external LLM calls on critical path     │
└─────────────────────────────────────────────────────────────────┘

LOOSE COUPLING (can be separate):
┌─────────────────────────────────────────────────────────────────┐
│                   Background Processing Domain                   │
│                                                                 │
│  Job Worker: Embedding generation, document extraction,         │
│              scheduled tasks, post-mortem generation            │
│                                                                 │
│  No user-facing latency, CPU-intensive, different scaling       │
└─────────────────────────────────────────────────────────────────┘
```

#### 5.0.6 Operational Characteristics Matrix

| Characteristic | Auth | Session | Case | Evidence | KB Query | Agent | KB Ingest | Job Worker |
|---------------|------|---------|------|----------|----------|-------|-----------|------------|
| **Latency Sensitivity** | High | High | High | Medium | High | High | Low | Low |
| **Compute Intensity** | Low | Low | Low | Low | Low | Low* | **HIGH** | **HIGH** |
| **External Dependencies** | None | Redis | DB | Files | VectorDB | LLM APIs | VectorDB | VectorDB |
| **Failure Impact** | Total | Total | Total | Degraded | Degraded | Total | None | None |
| **Scaling Trigger** | Users | Sessions | Cases | Uploads | Searches | Chats | Documents | Queue |

*Agent compute is **low** because LLM inference happens externally (OpenAI/Anthropic). Agent just orchestrates HTTP calls.

**Key Observations**:
1. Auth/Session/Case/Evidence/KB-Query/Agent all have similar profiles (low local compute, high latency sensitivity, critical path)
2. KB-Ingest/Job-Worker have high compute needs and tolerate latency (background processing)
3. Agent's external LLM dependency is no different from any external API call (like payments or email)

#### 5.0.7 Failure Domain Analysis

```
If Service Fails...     What Happens?                   Acceptable?
─────────────────────────────────────────────────────────────────────
Auth                    → Can't login, total outage      NO   ─┐
Session                 → Can't use app, total outage    NO   │
Case                    → Can't create/view cases        NO   │
Evidence                → Can't upload files             NO   ├─ Same failure domain
KB Query                → Can't search KB                NO   │   = should be together
Agent                   → Can't get AI responses         NO   ─┘

Job Worker              → Documents queue up             DEGRADED (process later)
KB Ingest               → Embeddings queue up            DEGRADED (process later)
```

**Conclusion**: Services that cause "total outage" together should be deployed together. Agent is on the critical path—if it fails, users can't get AI responses, which is the core value proposition.

#### 5.0.8 Final Grouping Decision

Based on the analysis above:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        MONOLITH (7 Services → 1)                        │
│                                                                         │
│  ┌─────────┐  ┌─────────┐  ┌────────┐  ┌──────────┐  ┌──────────────┐  │
│  │   API   │  │  Auth   │  │Session │  │   Case   │  │   Evidence   │  │
│  │Gateway  │  │ Module  │  │ Module │  │  Module  │  │    Module    │  │
│  │(middle- │  │         │  │        │  │          │  │              │  │
│  │  ware)  │  │         │  │        │  │          │  │              │  │
│  └─────────┘  └─────────┘  └────────┘  └──────────┘  └──────────────┘  │
│                                                                         │
│  ┌───────────────────────────────┐  ┌───────────────────────────────┐  │
│  │       Knowledge Module        │  │         Agent Module          │  │
│  │  (Vector Search ONLY - query  │  │  (LLM orchestration - calls   │  │
│  │   path, not embedding gen)    │  │   external providers via      │  │
│  │                               │  │   LLMProvider abstraction)    │  │
│  └───────────────────────────────┘  └───────────────────────────────┘  │
│                                                                         │
│  Rationale:                                                             │
│  • Same failure domain (if one fails, app is broken)                   │
│  • Same scaling characteristics (request-driven, low local compute)    │
│  • Agent compute is external (LLM providers do the heavy lifting)      │
│  • Transactional consistency possible                                  │
│  • Eliminates 6+ network hops per request                              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                      SEPARATE SERVICE: Job Worker                       │
│                                                                         │
│  Responsibilities (consolidated):                                       │
│  • Embedding generation (from KB Ingest path)                          │
│  • Document text extraction                                            │
│  • Scheduled cleanup tasks                                             │
│  • Post-mortem generation                                              │
│                                                                         │
│  Rationale:                                                             │
│  • Background processing (no user-facing latency)                      │
│  • CPU-intensive (embedding models run locally)                        │
│  • Different scaling model (workers scale with queue depth)            │
│  • Can run on cheaper compute (no need for fast networking)            │
│  • Failure = delayed processing, not outage                            │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 5.0.9 Grouping Summary

| Before (Current) | After (Recommended) | Rationale |
|------------------|---------------------|-----------|
| API Gateway | → Middleware in Monolith | No value as separate container |
| Auth Service | → Monolith Module | Core platform, same failure domain |
| Session Service | → Monolith Module | Core platform, same failure domain |
| Case Service | → Monolith Module | Core platform, same failure domain |
| Evidence Service | → Monolith Module | Core platform, same failure domain |
| Knowledge Service | → **SPLIT** | Query → Monolith, Ingest → Job Worker |
| Agent Service | → **Monolith Module** | LLM is external, just HTTP orchestration |
| Job Worker | → Separate Service | Background processing, CPU-intensive |

**Final Count**:
- **Before**: 7 microservices + 1 worker = 8 deployable units
- **After**: 1 monolith + 1 worker = 2 deployable units (75% reduction)

---

### 5.1 Proposed Structure

**Final Refined Architecture**:

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        FaultMaven Core Application                        │
│                    (Modular Monolith - 7 Services → 1)                    │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    Gateway Middleware Layer                          │ │
│  │  (JWT validation, CORS, rate limiting, request logging)             │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                    │                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                       API Layer (FastAPI)                            │ │
│  │  /auth/*  │  /sessions/*  │  /cases/*  │  /evidence/*  │  /agent/*  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                    │                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │              Module Boundaries (No Cross-Module Joins)               │ │
│  │  ┌────────┐ ┌─────────┐ ┌────────┐ ┌──────────┐ ┌──────────────┐    │ │
│  │  │  Auth  │ │ Session │ │  Case  │ │ Evidence │ │  Knowledge   │    │ │
│  │  │ Module │ │ Module  │ │ Module │ │  Module  │ │   Module     │    │ │
│  │  └────────┘ └─────────┘ └────────┘ └──────────┘ │ (query only) │    │ │
│  │                                                  └──────────────┘    │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │                      Agent Module                             │   │ │
│  │  │  • LLM orchestration via LLMProvider abstraction             │   │ │
│  │  │  • Prompt construction, response parsing                     │   │ │
│  │  │  • Calls external providers (OpenAI, Anthropic, Ollama)      │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                    │                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                   Provider Abstraction Layer                         │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │ │
│  │  │ Identity │ │   Data   │ │  Files   │ │  Vector  │ │    LLM    │  │ │
│  │  │ Provider │ │ Provider │ │ Provider │ │ Provider │ │  Provider │  │ │
│  │  ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤ ├───────────┤  │ │
│  │  │JWT│Auth0 │ │SQLite│PG │ │Local│S3  │ │Chroma│   │ │OpenAI│    │  │ │
│  │  │          │ │          │ │          │ │Pinecone  │ │Anthropic│ │  │ │
│  │  │          │ │          │ │          │ │          │ │Ollama    │  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └───────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
                                    │
                          Async (Redis Queue)
                                    │
                                    ▼
              ┌───────────────────────────────────────────┐
              │              Job Worker                    │
              │        (Background Processing)             │
              │                                            │
              │  • EMBEDDING GENERATION                    │
              │    (moved from Knowledge Service)          │
              │  • Document text extraction                │
              │  • Scheduled cleanup tasks                 │
              │  • Post-mortem generation                  │
              │  • Scales with queue depth                 │
              │                                            │
              │  Why separate:                             │
              │  • CPU-intensive (embedding models)        │
              │  • No user-facing latency requirements     │
              │  • Different scaling model (queue-based)   │
              │  • Failure = delayed processing, not outage│
              └───────────────────────────────────────────┘
                                    │
                              ┌───────────┐
                              │   Redis   │
                              │  (Queue)  │
                              └───────────┘
```

**Container Count by Deployment**:

| Deployment | Containers | Components |
|------------|------------|------------|
| **Core (Minimal)** | 2 | faultmaven + redis |
| **Core (Full)** | 3 | faultmaven + redis + chromadb |
| **Enterprise** | 4+ | faultmaven + job-workers + redis-cluster + managed-db |

**Deployment Unit Reduction**:
- **Before**: 8 deployable units (7 microservices + 1 worker)
- **After**: 2 deployable units (1 monolith + 1 worker)
- **Reduction**: 75% fewer containers to manage

### 5.2 Module Design Within Monolith

```python
# faultmaven/
├── src/faultmaven/
│   ├── main.py                 # FastAPI application entry
│   ├── api/
│   │   ├── auth.py             # Auth routes
│   │   ├── sessions.py         # Session routes
│   │   ├── cases.py            # Case routes
│   │   ├── evidence.py         # Evidence routes
│   │   └── agent.py            # Agent/chat routes
│   │
│   ├── modules/
│   │   ├── auth/
│   │   │   ├── __init__.py     # Public interface
│   │   │   ├── service.py      # Business logic
│   │   │   ├── repository.py   # Data access
│   │   │   └── models.py       # Domain models
│   │   │
│   │   ├── session/
│   │   │   └── ...
│   │   │
│   │   ├── case/
│   │   │   └── ...
│   │   │
│   │   ├── evidence/
│   │   │   └── ...
│   │   │
│   │   ├── knowledge/          # Query path only
│   │   │   └── ...
│   │   │
│   │   └── agent/              # LLM orchestration
│   │       ├── __init__.py     # Public interface
│   │       ├── service.py      # Chat orchestration
│   │       ├── router.py       # Model selection
│   │       └── models.py       # Request/response DTOs
│   │
│   ├── providers/
│   │   ├── llm/                # LLMProvider implementations
│   │   │   ├── base.py         # Abstract interface
│   │   │   ├── openai.py       # OpenAI implementation
│   │   │   ├── anthropic.py    # Anthropic implementation
│   │   │   └── ollama.py       # Local Ollama implementation
│   │   └── ...
│   │
│   └── infrastructure/
│       ├── database.py         # DB connection
│       ├── config.py           # Settings
│       └── middleware.py       # Auth middleware
│
├── tests/
├── deploy/                     # Docker Compose, Helm charts
├── Dockerfile
└── pyproject.toml
```

### 5.3 Module Boundary Enforcement

```python
# modules/auth/__init__.py - Public interface only
from .service import AuthService
from .models import User, TokenPair

__all__ = ["AuthService", "User", "TokenPair"]

# Other modules import through public interface:
# from modules.auth import AuthService
```

**Enforcement options:**
- Import linting rules (e.g., `import-linter`)
- Architecture tests (e.g., `pytest-arch`)
- Code review guidelines

### 5.4 Comparison: Current vs Proposed

| Aspect | Current (7 Microservices) | Proposed (Hybrid) |
|--------|--------------------------|-------------------|
| Repositories | 12+ | 5 |
| Containers (Core) | 7+ | 2 |
| Containers (Enterprise) | 7+ | 3-4 |
| Network hops (typical request) | 3-4 | 0-1 |
| Deployment complexity | High | Low |
| Development velocity | Lower | Higher |
| Independent scaling | All services | Only background processing |
| Transactional integrity | Distributed | Local (all user-facing) |

---

## 6. Refined Design Principles

The following design principles are critical for a successful hybrid architecture implementation.

### 6.1 Simplified API Layer (Eliminate Standalone Gateway)

**Problem**: The current standalone API Gateway adds deployment complexity without providing value that couldn't be achieved at the application layer.

**Recommendation**: Fold gateway functionality directly into the Core Monolith as FastAPI middleware.

```
BEFORE (Current):                    AFTER (Recommended):
┌─────────────────────┐              ┌─────────────────────────────────┐
│   API Gateway       │              │     FaultMaven Core             │
│   (Container #1)    │              │  ┌───────────────────────────┐  │
│  - JWT validation   │              │  │   Middleware Layer        │  │
│  - Rate limiting    │              │  │  - JWT validation         │  │
│  - CORS             │              │  │  - Rate limiting          │  │
│  - Routing          │              │  │  - CORS                   │  │
└────────┬────────────┘              │  │  - Request logging        │  │
         │                           │  └───────────────────────────┘  │
         ▼                           │              │                  │
┌─────────────────────┐              │  ┌───────────────────────────┐  │
│   Core Services     │              │  │   Application Layer       │  │
│   (Containers 2-5)  │              │  │  - Auth, Session, Case,   │  │
└─────────────────────┘              │  │    Evidence modules       │  │
                                     │  └───────────────────────────┘  │
                                     └─────────────────────────────────┘
```

**Implementation**:

```python
# src/middleware/gateway.py

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

def configure_gateway_middleware(app: FastAPI):
    """Fold API Gateway functionality into the application layer."""

    # CORS (previously in gateway)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting (previously in gateway)
    app.state.limiter = limiter

    # JWT validation middleware (previously in gateway)
    @app.middleware("http")
    async def jwt_validation_middleware(request: Request, call_next):
        # Skip auth for public endpoints
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        token = request.headers.get("Authorization")
        if not token:
            raise HTTPException(status_code=401, detail="Missing token")

        # Validate and attach user context
        request.state.user = validate_jwt(token)
        return await call_next(request)

# src/main.py
app = FastAPI(title="FaultMaven Core")
configure_gateway_middleware(app)
```

**Deployment Impact**:

| Deployment | Before | After |
|------------|--------|-------|
| FaultMaven Core | API Gateway + 4 services = 5+ containers | 1 Core container |
| Enterprise SaaS | Can add Kong/AWS API Gateway in front | Same Core + managed gateway |

**Enterprise Note**: For SaaS deployments requiring advanced features (API keys, usage metering, OAuth flows), place a managed gateway (Kong, AWS API Gateway, Cloudflare) in front of the cluster. The Core monolith handles basic auth; the managed gateway handles enterprise concerns.

---

### 6.2 Strict Data Isolation (No Cross-Module Joins)

**Problem**: Without discipline, a modular monolith degrades into "Monolithic Hell" where modules become tangled through direct database access.

**Recommendation**: Enforce a strict "No Cross-Module Joins" rule.

**The Golden Rule**:
> A module may NEVER directly query another module's database tables. All cross-module data access MUST go through the public service interface.

```
❌ FORBIDDEN: Direct cross-module database access

# In case/repository.py
def get_case_with_user(case_id: str):
    # WRONG: Directly joining auth tables
    return db.query(Case, User).join(User).filter(Case.id == case_id).first()

✅ REQUIRED: Access through public interface

# In case/service.py
from modules.auth import AuthService  # Public interface only

class CaseService:
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service

    def get_case_with_user(self, case_id: str) -> CaseWithUser:
        case = self.case_repo.get(case_id)
        user = self.auth_service.get_user(case.user_id)  # Through public API
        return CaseWithUser(case=case, user=user)
```

**Module Boundary Contract**:

```python
# modules/auth/__init__.py - THE ONLY PUBLIC INTERFACE

from .service import AuthService
from .models import User, TokenPair, UserPublic  # Only expose DTOs, not ORM models

__all__ = ["AuthService", "User", "TokenPair", "UserPublic"]

# NEVER export: Base, UserORM, auth_tables, session, etc.
```

**Enforcement Mechanisms**:

1. **Import Linting** (`import-linter`):

```ini
# pyproject.toml
[tool.importlinter]
root_package = "faultmaven"

[[tool.importlinter.contracts]]
name = "Modules cannot import each other's internals"
type = "independence"
modules = [
    "faultmaven.modules.auth.repository",
    "faultmaven.modules.auth.orm",
    "faultmaven.modules.session.repository",
    "faultmaven.modules.session.orm",
    "faultmaven.modules.case.repository",
    "faultmaven.modules.case.orm",
    "faultmaven.modules.evidence.repository",
    "faultmaven.modules.evidence.orm",
]
```

2. **Architecture Tests** (`pytest`):

```python
# tests/test_architecture.py

def test_no_cross_module_orm_imports():
    """Ensure modules don't import each other's ORM models."""
    import ast
    from pathlib import Path

    modules = ["auth", "session", "case", "evidence"]

    for module in modules:
        module_path = Path(f"src/modules/{module}")
        for py_file in module_path.glob("**/*.py"):
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    # Check for forbidden cross-module imports
                    for other in modules:
                        if other != module:
                            assert f"modules.{other}.repository" not in ast.dump(node)
                            assert f"modules.{other}.orm" not in ast.dump(node)
```

3. **Database Schema Separation** (logical namespacing):

```python
# Each module owns its tables with clear prefixes
class AuthBase(Base):
    __table_args__ = {"schema": "auth"}  # PostgreSQL schema isolation

class CaseBase(Base):
    __table_args__ = {"schema": "cases"}

# For SQLite (no schema support), use table prefixes:
# auth_users, auth_tokens, case_cases, case_messages, etc.
```

**Benefit**: This guarantees that any module (e.g., Auth) can be extracted into a separate microservice later by simply:
1. Moving the module to its own repository
2. Replacing in-process service calls with HTTP/gRPC calls
3. No database layer changes required

---

### 6.3 Async Pattern for Long-Running LLM Calls

**Problem**: LLM calls take 10-60+ seconds. Even with Agent as a module inside the monolith, synchronous HTTP handling causes:
- UI hangs while waiting for LLM responses
- HTTP timeouts on long responses
- Poor user experience

**Recommendation**: Use async request/response pattern with job tracking for LLM operations.

```
┌──────────┐  POST /chat    ┌─────────────────────────────────────────────┐
│  Client  │ ─────────────▶ │              FaultMaven Monolith            │
│          │ ◀───────────── │  ┌─────────┐      ┌─────────────────────┐  │
└──────────┘  {job_id}      │  │   API   │─────▶│    Agent Module     │  │
     │                      │  └─────────┘      │  • Start async task │  │
     │ Poll /chat/{job_id}  │                   │  • Call LLMProvider │  │
     │ or WebSocket/SSE     │                   │  • Store result     │  │
     └──────────────────────│                   └─────────────────────┘  │
                            └─────────────────────────────────────────────┘
```

**Implementation**:

```python
# src/modules/agent/service.py

import asyncio
from uuid import uuid4

class AgentService:
    """LLM orchestration - runs inside the monolith."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        knowledge: KnowledgeService,
        result_store: ResultStore,  # Redis-backed
    ):
        self.llm = llm_provider
        self.knowledge = knowledge
        self.results = result_store

    async def submit_chat(self, case_id: str, message: str, context: dict) -> str:
        """Submit chat request, return job ID immediately."""
        job_id = str(uuid4())

        # Start background task (runs in same process)
        asyncio.create_task(
            self._process_chat(job_id, case_id, message, context)
        )

        return job_id

    async def _process_chat(
        self, job_id: str, case_id: str, message: str, context: dict
    ):
        """Background task for LLM processing."""
        try:
            # Search knowledge base (fast, local)
            kb_results = await self.knowledge.search(message)

            # Call LLM (slow, external)
            response = await self.llm.chat(
                message=message,
                context=context,
                sources=kb_results,
            )

            # Store result
            await self.results.set(job_id, ChatResult(
                status="completed",
                response=response,
                sources=kb_results,
            ))

        except Exception as e:
            await self.results.set(job_id, ChatResult(
                status="failed",
                error=str(e),
            ))

    async def get_result(self, job_id: str) -> Optional[ChatResult]:
        """Poll for job result."""
        return await self.results.get(job_id)

# API endpoint
@router.post("/v1/agent/chat")
async def submit_chat(
    request: ChatRequest,
    agent: AgentService = Depends(get_agent_service),
):
    job_id = await agent.submit_chat(
        case_id=request.case_id,
        message=request.message,
        context=request.context,
    )
    return {"job_id": job_id, "status": "processing"}

@router.get("/v1/agent/chat/{job_id}")
async def get_chat_result(
    job_id: str,
    agent: AgentService = Depends(get_agent_service),
):
    result = await agent.get_result(job_id)
    if result:
        return {"status": result.status, "result": result}
    return {"status": "processing"}
```

**Benefits**:

| Aspect | Synchronous | Async Pattern |
|--------|-------------|---------------|
| UI responsiveness | Blocks for 10-60s | Immediate acknowledgment |
| HTTP timeouts | Risk of 504 | No timeout issues |
| User experience | Spinning loader | Progress indicator, SSE streaming |
| Implementation | Simple but blocking | Slightly more complex, better UX |

**Client-Side Pattern** (for extension/dashboard):

```typescript
// Browser extension: Poll or SSE
async function sendMessage(message: string): Promise<ChatResponse> {
  // 1. Submit (immediate response)
  const { job_id } = await api.post('/v1/agent/chat', { message });

  // 2. Poll for result (or use SSE for streaming)
  while (true) {
    const { status, result } = await api.get(`/v1/agent/chat/${job_id}`);
    if (status === 'completed') return result;
    if (status === 'failed') throw new Error('Chat failed');
    await sleep(1000); // Poll every second
  }
}
```

**Note**: This async pattern runs inside the monolith process. For extreme scale, the background task processing could be moved to the Job Worker, but for most deployments the in-process async approach is sufficient and simpler.

---

### 6.4 Deployment Neutrality (Provider Abstraction Layer)

**Problem**: The same codebase must run on:
- A developer's laptop (SQLite, local files)
- A small team's server (PostgreSQL, local files)
- Enterprise SaaS (PostgreSQL cluster, S3, managed Redis)

**Recommendation**: Implement a provider abstraction layer for all infrastructure dependencies.

**Abstraction Boundaries**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Application Layer                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Modules: Auth, Session, Case, Evidence                      │   │
│  │  (Business logic uses abstract interfaces only)              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Provider Abstraction Layer                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐  │   │
│  │  │ Identity │  │   Data   │  │   Files  │  │   Vector    │  │   │
│  │  │ Provider │  │ Provider │  │ Provider │  │  Provider   │  │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬──────┘  │   │
│  └───────┼─────────────┼─────────────┼───────────────┼─────────┘   │
│          │             │             │               │              │
└──────────┼─────────────┼─────────────┼───────────────┼──────────────┘
           │             │             │               │
   ┌───────┴───────┐ ┌───┴────┐ ┌──────┴──────┐ ┌──────┴──────┐
   │ JWT (Core)    │ │ SQLite │ │ Local Files │ │  ChromaDB   │
   │ Auth0 (Ent)   │ │ Postgres│ │ S3/MinIO   │ │  Pinecone   │
   │ Okta (Ent)    │ │        │ │            │ │             │
   └───────────────┘ └────────┘ └─────────────┘ └─────────────┘
```

**Implementation**:

```python
# src/providers/base.py

from abc import ABC, abstractmethod
from typing import Protocol, TypeVar, Generic

T = TypeVar("T")

class DataProvider(Protocol[T]):
    """Abstract interface for data persistence."""

    async def get(self, id: str) -> Optional[T]: ...
    async def save(self, entity: T) -> T: ...
    async def delete(self, id: str) -> bool: ...
    async def query(self, **filters) -> list[T]: ...

class FileProvider(Protocol):
    """Abstract interface for file storage."""

    async def upload(self, key: str, data: bytes, content_type: str) -> str: ...
    async def download(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> bool: ...
    async def get_url(self, key: str, expires_in: int = 3600) -> str: ...

class VectorProvider(Protocol):
    """Abstract interface for vector storage."""

    async def upsert(self, collection: str, id: str, vector: list[float], metadata: dict): ...
    async def search(self, collection: str, vector: list[float], top_k: int) -> list[dict]: ...
    async def delete(self, collection: str, id: str): ...

class IdentityProvider(Protocol):
    """Abstract interface for authentication."""

    async def validate_token(self, token: str) -> Optional[User]: ...
    async def create_token(self, user: User) -> TokenPair: ...
    async def refresh_token(self, refresh_token: str) -> TokenPair: ...
```

```python
# src/providers/data/sqlite.py

class SQLiteDataProvider(DataProvider[T]):
    """SQLite implementation for FaultMaven Core."""

    def __init__(self, db_path: str):
        self.engine = create_engine(f"sqlite:///{db_path}")

    async def get(self, id: str) -> Optional[T]:
        async with self.session() as session:
            return await session.get(self.model, id)

    # ... other implementations

# src/providers/data/postgresql.py

class PostgreSQLDataProvider(DataProvider[T]):
    """PostgreSQL implementation for Enterprise."""

    def __init__(self, connection_url: str):
        self.engine = create_async_engine(connection_url)

    async def get(self, id: str) -> Optional[T]:
        async with self.session() as session:
            return await session.get(self.model, id)
```

```python
# src/providers/files/local.py

class LocalFileProvider(FileProvider):
    """Local filesystem for FaultMaven Core."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        path = self.base_path / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

# src/providers/files/s3.py

class S3FileProvider(FileProvider):
    """S3/MinIO for Enterprise."""

    def __init__(self, bucket: str, client: S3Client):
        self.bucket = bucket
        self.client = client

    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        await self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return f"s3://{self.bucket}/{key}"
```

**Configuration-Based Provider Selection**:

```python
# src/config.py

from pydantic_settings import BaseSettings
from enum import Enum

class DeploymentProfile(str, Enum):
    CORE = "core"           # Self-hosted, minimal dependencies
    TEAM = "team"           # Self-hosted, PostgreSQL
    ENTERPRISE = "enterprise"  # SaaS, full infrastructure

class Settings(BaseSettings):
    PROFILE: DeploymentProfile = DeploymentProfile.CORE

    # Data provider
    DATABASE_URL: str = "sqlite:///./faultmaven.db"

    # File provider
    FILE_STORAGE: str = "local"  # local, s3, minio
    FILE_STORAGE_PATH: str = "./data/files"
    S3_BUCKET: Optional[str] = None

    # Vector provider
    VECTOR_STORE: str = "chromadb"  # chromadb, pinecone
    CHROMADB_PATH: str = "./data/chromadb"

    # Identity provider
    IDENTITY_PROVIDER: str = "jwt"  # jwt, auth0, okta

# src/dependencies.py

def get_providers(settings: Settings) -> Providers:
    """Factory for creating providers based on deployment profile."""

    # Data provider
    if settings.DATABASE_URL.startswith("sqlite"):
        data = SQLiteDataProvider(settings.DATABASE_URL)
    else:
        data = PostgreSQLDataProvider(settings.DATABASE_URL)

    # File provider
    if settings.FILE_STORAGE == "local":
        files = LocalFileProvider(settings.FILE_STORAGE_PATH)
    elif settings.FILE_STORAGE == "s3":
        files = S3FileProvider(settings.S3_BUCKET, boto3.client("s3"))

    # Vector provider
    if settings.VECTOR_STORE == "chromadb":
        vectors = ChromaDBProvider(settings.CHROMADB_PATH)
    elif settings.VECTOR_STORE == "pinecone":
        vectors = PineconeProvider(settings.PINECONE_API_KEY)

    # Identity provider
    if settings.IDENTITY_PROVIDER == "jwt":
        identity = JWTIdentityProvider(settings.JWT_SECRET)
    elif settings.IDENTITY_PROVIDER == "auth0":
        identity = Auth0IdentityProvider(settings.AUTH0_DOMAIN)

    return Providers(data=data, files=files, vectors=vectors, identity=identity)
```

**Deployment Examples**:

```yaml
# docker-compose.core.yml (Self-Hosted Minimal)
services:
  faultmaven:
    image: faultmaven/core:latest
    environment:
      PROFILE: core
      DATABASE_URL: sqlite:///data/faultmaven.db
      FILE_STORAGE: local
      FILE_STORAGE_PATH: /data/files
      VECTOR_STORE: chromadb
      CHROMADB_PATH: /data/chromadb
    volumes:
      - ./data:/data

# docker-compose.enterprise.yml (SaaS)
services:
  faultmaven:
    image: faultmaven/core:latest
    environment:
      PROFILE: enterprise
      DATABASE_URL: postgresql://user:pass@rds.amazonaws.com:5432/faultmaven
      FILE_STORAGE: s3
      S3_BUCKET: faultmaven-files-prod
      VECTOR_STORE: pinecone
      PINECONE_API_KEY: ${PINECONE_API_KEY}
      IDENTITY_PROVIDER: auth0
      AUTH0_DOMAIN: faultmaven.auth0.com
```

**Benefit**: Exact same Docker image runs everywhere. Configuration determines infrastructure. This is the key enabler for the open-core business model.

---

### 6.5 Extraction-Ready Module Design

**Problem**: "Modules can be extracted later" is only true if boundaries are enforced aggressively from day one. Without explicit safeguards, future extraction becomes theoretically possible but practically painful.

**Recommendation**: Enforce these non-negotiable rules to preserve extractability:

**The Extraction Readiness Checklist**:

| Rule | Enforcement | Why It Matters |
|------|-------------|----------------|
| No shared ORM models across modules | Import linter | Prevents tight DB coupling |
| No shared SQLAlchemy sessions | Code review, tests | Each module owns its connection |
| Explicit DTOs at module boundaries | Type checker, linter | Clear contracts, no ORM leakage |
| Service interfaces async-safe | All public methods async | Ready for HTTP/gRPC extraction |
| No direct cross-module imports | `import-linter` CI check | Only public interfaces exposed |

**Implementation**:

```python
# ❌ WRONG: Shared ORM models leak implementation details
# modules/case/service.py
from modules.auth.orm import UserORM  # FORBIDDEN - internal ORM model

# ✅ CORRECT: Use DTOs at boundaries
# modules/case/service.py
from modules.auth import AuthService, UserDTO  # Public interface only

class CaseService:
    def __init__(self, auth_service: AuthService):
        self.auth = auth_service

    async def get_case_with_owner(self, case_id: str) -> CaseWithOwner:
        case = await self.case_repo.get(case_id)
        # Call through public async interface - extraction-ready
        owner: UserDTO = await self.auth.get_user(case.owner_id)
        return CaseWithOwner(case=case, owner=owner)
```

```python
# ❌ WRONG: Shared database session
# modules/case/repository.py
from shared.database import get_session  # Shared session = extraction blocker

# ✅ CORRECT: Module owns its session
# modules/case/repository.py
from modules.case.database import CaseSession  # Module-scoped session

class CaseRepository:
    def __init__(self, session_factory: Callable[[], CaseSession]):
        self._session_factory = session_factory
```

**Extraction Test**: Before every major release, verify you can run any single module as a standalone service with mocked dependencies. If you can't, you've accumulated extraction debt.

---

### 6.6 Infrastructure as Abstraction (Redis is Not a Service)

**Problem**: Redis appears in multiple conceptual roles (session backing, job queue, result cache, rate limiting). If modules depend on Redis directly, it becomes the next `fm-core-lib` - a hidden coupling point.

**Recommendation**: Treat all infrastructure as abstract interfaces. Modules depend on capabilities, not implementations.

**Infrastructure Abstraction Map**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Module Layer                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Modules depend on INTERFACES, not implementations              │   │
│  │                                                                 │   │
│  │  SessionStore    JobQueue    Cache    RateLimiter               │   │
│  │       │             │          │           │                    │   │
│  └───────┼─────────────┼──────────┼───────────┼────────────────────┘   │
│          │             │          │           │                        │
└──────────┼─────────────┼──────────┼───────────┼────────────────────────┘
           │             │          │           │
┌──────────┼─────────────┼──────────┼───────────┼────────────────────────┐
│          ▼             ▼          ▼           ▼                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                Infrastructure Layer                             │   │
│  │                                                                 │   │
│  │  RedisSessionStore  RedisQueue  RedisCache  RedisRateLimiter    │   │
│  │  MemorySessionStore InMemQueue  NoOpCache   NoOpRateLimiter     │   │
│  │  (for testing)      (testing)   (testing)   (dev mode)          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│                              Redis                                     │
│                          (single instance)                             │
└────────────────────────────────────────────────────────────────────────┘
```

**Implementation**:

```python
# src/infrastructure/interfaces.py

from typing import Protocol, Optional, Any
from datetime import timedelta

class SessionStore(Protocol):
    """Abstract session storage - NOT Redis-specific."""
    async def get(self, session_id: str) -> Optional[dict]: ...
    async def set(self, session_id: str, data: dict, ttl: timedelta) -> None: ...
    async def delete(self, session_id: str) -> None: ...

class JobQueue(Protocol):
    """Abstract job queue - NOT Redis/Celery-specific."""
    async def enqueue(self, job_type: str, payload: dict, **options) -> str: ...
    async def get_result(self, job_id: str) -> Optional[Any]: ...

class Cache(Protocol):
    """Abstract cache - NOT Redis-specific."""
    async def get(self, key: str) -> Optional[bytes]: ...
    async def set(self, key: str, value: bytes, ttl: timedelta) -> None: ...
    async def invalidate(self, pattern: str) -> None: ...

# src/infrastructure/redis_impl.py

class RedisSessionStore(SessionStore):
    def __init__(self, redis: Redis):
        self._redis = redis

    async def get(self, session_id: str) -> Optional[dict]:
        data = await self._redis.get(f"session:{session_id}")
        return json.loads(data) if data else None

# Modules use the interface, not Redis directly:
# modules/session/service.py
class SessionService:
    def __init__(self, store: SessionStore):  # Interface, not Redis
        self._store = store
```

**Benefit**:
- Modules are testable without Redis
- Can swap implementations (Redis → Memcached, Redis → DynamoDB)
- Clear separation prevents "Redis is our database" antipattern

---

### 6.7 Event Contract Versioning

**Problem**: With async Agent communication, Job Worker, and background ingestion, event schemas become more important than REST schemas. Unversioned events lead to silent failures and deployment nightmares.

**Recommendation**: Treat event contracts as first-class API boundaries with explicit versioning.

**Event Schema Strategy**:

```yaml
# events/schemas/chat_request.v1.yaml (AsyncAPI format)
asyncapi: 2.6.0
info:
  title: FaultMaven Agent Events
  version: 1.0.0

channels:
  agent.chat.request:
    publish:
      message:
        name: ChatRequest
        schemaFormat: application/vnd.aai.asyncapi+json;version=2.6.0
        payload:
          type: object
          required: [job_id, case_id, message, version]
          properties:
            version:
              type: string
              enum: ["1.0"]  # Explicit version in payload
            job_id:
              type: string
              format: uuid
            case_id:
              type: string
            message:
              type: string
            context:
              type: object
              additionalProperties: true
```

**Versioning Rules**:

| Change Type | Action Required | Example |
|-------------|-----------------|---------|
| Add optional field | Minor bump, backward compatible | Add `priority` field |
| Add required field | Major bump, migration needed | Add `tenant_id` required |
| Remove field | Major bump, deprecation period | Remove `legacy_context` |
| Change field type | Major bump, new schema version | `case_id: int` → `string` |

**Implementation**:

```python
# events/models.py

from pydantic import BaseModel, Field
from typing import Literal

class ChatRequestV1(BaseModel):
    """Chat request event - Version 1.0"""
    version: Literal["1.0"] = "1.0"
    job_id: str
    case_id: str
    message: str
    context: dict = Field(default_factory=dict)

class ChatRequestV2(BaseModel):
    """Chat request event - Version 2.0 (adds required tenant_id)"""
    version: Literal["2.0"] = "2.0"
    job_id: str
    case_id: str
    tenant_id: str  # NEW: Required in v2
    message: str
    context: dict = Field(default_factory=dict)

# Consumer handles multiple versions
def process_chat_request(payload: dict):
    version = payload.get("version", "1.0")
    if version == "1.0":
        request = ChatRequestV1(**payload)
        tenant_id = infer_tenant_from_case(request.case_id)  # Backward compat
    elif version == "2.0":
        request = ChatRequestV2(**payload)
        tenant_id = request.tenant_id
    else:
        raise UnsupportedVersionError(version)
```

**CI Enforcement**:

```yaml
# .github/workflows/event-contracts.yml
- name: Validate event schemas
  run: |
    asyncapi validate events/schemas/*.yaml

- name: Check backward compatibility
  run: |
    # Compare against main branch schemas
    asyncapi diff events/schemas/ origin/main:events/schemas/ --breaking
```

---

### 6.8 Agent Module Evolution Path

**Context**: The Agent Module lives inside the monolith but may need internal decomposition as AI capabilities grow. Design for future complexity without premature extraction.

**Current State**: Agent is a module with clear internal structure:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Agent Module (Inside Monolith)                        │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     Today: Single Module                         │   │
│  │                                                                   │   │
│  │  Request → Prompt Build → LLMProvider Call → Response Parse      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │               Tomorrow: Internal Sub-components                  │   │
│  │                                                                   │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │   │
│  │  │   Router     │  │   Executor   │  │      Optimizer         │ │   │
│  │  │              │  │              │  │                        │ │   │
│  │  │ • Model      │  │ • LLM calls  │  │ • Response caching     │ │   │
│  │  │   selection  │  │ • Retry      │  │ • Cost optimization    │ │   │
│  │  │ • Load       │  │   logic      │  │ • Semantic dedup       │ │   │
│  │  │   balancing  │  │ • Streaming  │  │ • Prompt compression   │ │   │
│  │  │ • Fallback   │  │              │  │                        │ │   │
│  │  │   chains     │  │              │  │                        │ │   │
│  │  └──────────────┘  └──────────────┘  └────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

**Extraction Triggers** (when to consider extracting Agent to separate service):

| Signal | Threshold | Action |
|--------|-----------|--------|
| CPU contention | Agent async tasks starving other modules | Consider extraction |
| Team size | 3+ dedicated AI engineers | Consider extraction |
| Deployment cadence | Agent needs daily deploys, rest is stable | Consider extraction |
| Extreme scale | 1000+ concurrent LLM calls | Consider extraction |

**Note**: These thresholds are unlikely for most deployments. The LLMProvider abstraction means extraction is straightforward if ever needed—just move the module to its own service and change internal calls to HTTP calls.

**Design for Future Flexibility**:

```python
# src/modules/agent/service.py - Today's implementation with internal boundaries

class AgentService:
    """Main entry point - stable interface whether module or service."""

    def __init__(
        self,
        router: ModelRouter,           # Internal boundary
        llm_provider: LLMProvider,     # Provider abstraction
        optimizer: ResponseOptimizer,  # Internal boundary
    ):
        self.router = router
        self.llm = llm_provider
        self.optimizer = optimizer

    async def process_chat(self, request: ChatRequest) -> ChatResponse:
        # Check cache first (Optimizer)
        cached = await self.optimizer.get_cached(request)
        if cached:
            return cached

        # Select model (Router)
        model = await self.router.select_model(request)

        # Execute LLM call via provider (could be OpenAI, Anthropic, Ollama)
        response = await self.llm.chat(model, request)

        # Cache and optimize (Optimizer)
        await self.optimizer.cache_response(request, response)

        return response
```

**The key insight**: The `AgentService` interface remains stable whether it's a module or a service. Internal decomposition and potential extraction don't require API changes.

---

## 7. Migration Path

### Phase 1: Establish Provider Abstraction Layer

**Goal**: Decouple business logic from infrastructure before consolidation.

1. Define provider interfaces (Data, Files, Vector, Identity)
2. Create SQLite/Local implementations for Core
3. Create PostgreSQL/S3 implementations for Enterprise
4. Add configuration-based provider selection
5. Test both profiles end-to-end

**Effort**: 1-2 weeks
**Risk**: Low (additive changes, no breaking modifications)

### Phase 2: Consolidate Core Services into Monolith

**Goal**: Merge Auth, Session, Case, Evidence into a single application.

1. Create `faultmaven-core` repository
2. Migrate each service as a module with strict boundaries
3. Fold API Gateway logic into FastAPI middleware
4. Enforce "No Cross-Module Joins" rule with import linting
5. Add architecture tests to CI pipeline
6. Maintain API compatibility (same routes, same contracts)

**Effort**: 2-3 weeks
**Risk**: Low (internal refactoring, external APIs unchanged)

### Phase 3: Implement Async AI Communication

**Goal**: Replace synchronous Agent calls with event-driven pattern.

1. Introduce job queue (Redis + RQ/Celery) for AI requests
2. Update Core to enqueue requests and return job IDs
3. Update Agent Service to consume from queue
4. Add polling endpoint and optional WebSocket support
5. Update browser extension for async flow

**Effort**: 1-2 weeks
**Risk**: Medium (client-side changes required)

### Phase 4: Simplify Deployment

**Goal**: Reduce Core deployment to 2-3 containers.

1. Build single Docker image for Core monolith
2. Update Docker Compose for Core (faultmaven + redis + chromadb)
3. Update Kubernetes Helm charts for Enterprise
4. Comprehensive documentation update

**Effort**: 1 week
**Risk**: Low (deployment changes only)

### Migration Summary

| Phase | Duration | Key Deliverable |
|-------|----------|-----------------|
| 1: Provider Abstraction | 1-2 weeks | Same code runs on SQLite or PostgreSQL |
| 2: Consolidate Services | 2-3 weeks | 7 services → 1 modular monolith (includes Agent + KB query path) |
| 3: Async LLM Pattern | 1-2 weeks | Non-blocking LLM interactions within monolith |
| 4: Simplify Deployment | 1 week | 8 containers → 2 containers |
| **Total** | **5-8 weeks** | **Production-ready hybrid architecture** |

---

## 8. Decision Matrix

### 8.1 Scoring Criteria

| Criterion | Weight | Microservices | Modular Monolith | Hybrid |
|-----------|--------|---------------|------------------|--------|
| Core deployment simplicity | 25% | 2/10 | 9/10 | 8/10 |
| Enterprise scalability | 20% | 9/10 | 6/10 | 8/10 |
| Development velocity | 20% | 4/10 | 9/10 | 8/10 |
| Operational overhead | 15% | 3/10 | 9/10 | 7/10 |
| Fault isolation | 10% | 9/10 | 5/10 | 7/10 |
| Future flexibility | 10% | 8/10 | 7/10 | 8/10 |

### 8.2 Weighted Scores

| Architecture | Weighted Score |
|--------------|---------------|
| Current Microservices | **4.7 / 10** |
| Pure Modular Monolith | **7.6 / 10** |
| **Hybrid (Recommended)** | **7.8 / 10** |

---

## 9. Recommendations

### 9.1 Primary Recommendation

**Adopt a Modular Monolith with Background Worker:**

1. **Consolidate 7 services → 1 Monolith**: API Gateway (as middleware), Auth, Session, Case, Evidence, Knowledge (query path), Agent
2. **Split Knowledge Service**: Vector search → Monolith module, Embedding generation → Job Worker
3. **Keep 1 service separate**: Job Worker (background processing + embeddings)
4. **Simplify** deployment for Core users (2 containers vs 8)
5. **Maintain** extraction paths via strict module boundaries and provider abstractions

### 9.2 Rationale

| Factor | Why This Wins |
|--------|---------------|
| **Business model** | Core users need simplicity; Enterprise scales via replicas |
| **Team structure** | Small team more productive with unified codebase |
| **Domain coupling** | Auth→Session→Case→Evidence→KB-Query→Agent all share failure domain |
| **Agent reality** | LLM is external—Agent just orchestrates HTTP calls like any external API |
| **Scaling reality** | Only Job Worker (CPU-intensive embeddings) needs independent scaling |
| **Operational cost** | Reduces Core deployment from 8 to 2 containers (75% reduction) |
| **KB Service split** | Query path is fast (monolith); Ingestion is slow (worker) |

### 9.3 What to Avoid

1. **Don't keep Agent separate**: LLM compute is external; Agent is just orchestration code on the critical path
2. **Don't keep Knowledge Service whole**: Query and Ingestion paths have fundamentally different operational profiles
3. **Don't keep current state**: 8 microservices overhead isn't justified by actual independence
4. **Don't over-engineer modules**: Keep boundaries simple; only extract if concrete triggers are hit

---

## 10. Conclusion

FaultMaven's current microservices architecture represents **premature optimization** for the product's stage and business model. The overhead of 8 deployable units is not justified when:

- The target includes self-hosted users who need simplicity
- A small team maintains all services
- Only 1 service (Job Worker for embeddings) genuinely needs independent scaling
- 7 services share the same failure domain and operational characteristics
- The Knowledge Service conflates two distinct functions (query vs. ingestion)
- Agent's "heavy compute" is actually external (LLM providers do the work)

A **Modular Monolith with Background Worker** approach provides:
- Simpler deployment for Core users (2 containers vs 8 = adoption advantage)
- Maintained scalability via horizontal scaling of the monolith
- Faster development velocity (single codebase, single deploy)
- Lower operational overhead (75% reduction in deployable units)
- Clear path to extract services if future needs require it (via provider abstractions)

**The best architecture is the simplest one that meets current requirements while allowing for future growth.** For FaultMaven today, that's a modular monolith with a background worker for CPU-intensive tasks.

---

## Appendix A: Architecture Decision Record (ADR)

### ADR-001: Adopt Modular Monolith with Background Worker

**Status**: Proposed

**Context**: FaultMaven currently uses a microservices architecture with 8 deployable units. This creates operational overhead for self-hosted users and development friction for the small team. Analysis shows that 7 services share the same failure domain and operational characteristics. The Agent Service, originally thought to need separation for "heavy compute," actually just orchestrates calls to external LLM providers.

**Decision**:
1. Consolidate 7 services into a single Modular Monolith: API Gateway (as middleware), Auth, Session, Case, Evidence, Knowledge (query path only), and Agent
2. Split Knowledge Service: Vector search → Monolith module, Embedding generation → Job Worker
3. Keep Job Worker as the only separate service for CPU-intensive background tasks

**Consequences**:
- (+) Simpler deployment for Core users (8 → 2 containers, 75% reduction)
- (+) Faster development for all platform features including AI
- (+) LLMProvider abstraction handles local vs cloud LLMs via configuration
- (+) Knowledge Service split aligns with actual operational characteristics
- (+) Agent in monolith eliminates unnecessary network hop on critical path
- (-) Migration effort required (~5-8 weeks)
- (-) Less granular scaling for all user-facing operations (acceptable - same failure domain anyway)

---

## Appendix B: References

- Fowler, M. (2015). "MonolithFirst" - https://martinfowler.com/bliki/MonolithFirst.html
- Newman, S. (2019). "Monolith to Microservices" - O'Reilly Media
- Richardson, C. (2018). "Microservices Patterns" - Manning Publications
- Dehghani, Z. (2020). "How to Move Beyond a Monolithic Data Lake to a Distributed Data Mesh"
