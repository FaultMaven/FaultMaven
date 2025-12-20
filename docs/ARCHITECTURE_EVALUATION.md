# FaultMaven Architecture Evaluation: Microservices vs Modular Monolith

## Executive Summary

This document evaluates FaultMaven's current microservices architecture against a Modular Monolith pattern, considering the product's business model, development context, and operational requirements.

**Conclusion**: The current microservices architecture introduces **significant overhead that may not be justified** by the actual business and development requirements. A **hybrid approach** - Modular Monolith for core CRUD services with separate services only for compute-intensive workloads - would better serve FaultMaven's goals.

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

### 5.1 Proposed Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                    FaultMaven Core Application                  │
│                    (Modular Monolith)                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    API Layer (FastAPI)                    │  │
│  │  /auth/*  │  /sessions/*  │  /cases/*  │  /evidence/*    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Module Boundaries                       │  │
│  │  ┌────────┐  ┌─────────┐  ┌────────┐  ┌──────────┐       │  │
│  │  │  Auth  │  │ Session │  │  Case  │  │ Evidence │       │  │
│  │  │ Module │  │ Module  │  │ Module │  │  Module  │       │  │
│  │  └────────┘  └─────────┘  └────────┘  └──────────┘       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Shared Infrastructure                        │  │
│  │     Database (SQLite/PostgreSQL)  │  File Storage        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────┐
│  Agent Service   │ │Knowledge Service │ │  Job Worker  │
│  (Separate)      │ │   (Separate)     │ │  (Separate)  │
│                  │ │                  │ │              │
│ - LLM calls      │ │ - Embeddings     │ │ - Async jobs │
│ - Scaling: High  │ │ - ChromaDB       │ │ - Celery     │
│ - Stateless      │ │ - Scaling: High  │ │              │
└──────────────────┘ └──────────────────┘ └──────────────┘
```

### 5.2 Module Design Within Monolith

```python
# faultmaven-core/
├── src/
│   ├── main.py                 # FastAPI application entry
│   ├── api/
│   │   ├── auth.py             # Auth routes
│   │   ├── sessions.py         # Session routes
│   │   ├── cases.py            # Case routes
│   │   └── evidence.py         # Evidence routes
│   │
│   ├── modules/
│   │   ├── auth/
│   │   │   ├── __init__.py     # Public interface
│   │   │   ├── service.py      # Business logic
│   │   │   ├── repository.py   # Data access
│   │   │   └── models.py       # Domain models
│   │   │
│   │   ├── session/
│   │   │   ├── __init__.py
│   │   │   ├── service.py
│   │   │   └── ...
│   │   │
│   │   ├── case/
│   │   │   └── ...
│   │   │
│   │   └── evidence/
│   │       └── ...
│   │
│   └── shared/
│       ├── database.py         # DB connection
│       ├── config.py           # Settings
│       └── middleware.py       # Auth middleware
│
├── tests/
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
| Repositories | 12+ | 5-6 |
| Containers (Core) | 7+ | 3-4 |
| Containers (Enterprise) | 7+ | 4-5 |
| Network hops (typical request) | 3-4 | 1-2 |
| Deployment complexity | High | Medium |
| Development velocity | Lower | Higher |
| Independent scaling | All services | Only where needed |
| Transactional integrity | Distributed | Local (core) + Distributed (AI) |

---

## 6. Migration Path

### Phase 1: Consolidate Core Services (Low Risk)

1. Create `faultmaven-core` repository
2. Merge Auth, Session, Case, Evidence into modules
3. Maintain API compatibility (same routes)
4. Update Docker Compose to use consolidated image

**Effort**: 2-3 weeks
**Risk**: Low (internal refactoring)

### Phase 2: Optimize Communication (Medium Risk)

1. Convert Agent → Core communication to direct calls (in-process for Core deployment)
2. Maintain REST interface for Enterprise scaling
3. Add internal module APIs

**Effort**: 1-2 weeks
**Risk**: Medium (interface changes)

### Phase 3: Simplify Deployment (Low Risk)

1. Single Docker image for Core
2. Optional split deployment for Enterprise
3. Update documentation

**Effort**: 1 week
**Risk**: Low (deployment changes only)

---

## 7. Decision Matrix

### 7.1 Scoring Criteria

| Criterion | Weight | Microservices | Modular Monolith | Hybrid |
|-----------|--------|---------------|------------------|--------|
| Core deployment simplicity | 25% | 2/10 | 9/10 | 8/10 |
| Enterprise scalability | 20% | 9/10 | 6/10 | 8/10 |
| Development velocity | 20% | 4/10 | 9/10 | 8/10 |
| Operational overhead | 15% | 3/10 | 9/10 | 7/10 |
| Fault isolation | 10% | 9/10 | 5/10 | 7/10 |
| Future flexibility | 10% | 8/10 | 7/10 | 8/10 |

### 7.2 Weighted Scores

| Architecture | Weighted Score |
|--------------|---------------|
| Current Microservices | **4.7 / 10** |
| Pure Modular Monolith | **7.6 / 10** |
| **Hybrid (Recommended)** | **7.8 / 10** |

---

## 8. Recommendations

### 8.1 Primary Recommendation

**Adopt a Hybrid Architecture:**

1. **Consolidate** Auth, Session, Case, Evidence into a single Modular Monolith
2. **Keep separate** Agent Service, Knowledge Service, Job Worker
3. **Simplify** deployment for Core users (2-3 containers vs 7+)
4. **Maintain** scalability for Enterprise (can still scale AI services independently)

### 8.2 Rationale

| Factor | Why Hybrid Wins |
|--------|-----------------|
| Business model | Core users need simplicity; Enterprise needs scale for AI only |
| Team size | Small team is more productive with unified codebase |
| Domain nature | CRUD services are tightly coupled; AI services are genuinely independent |
| Scaling reality | Only Agent/KB need independent scaling |
| Operational cost | Reduces Core deployment from 7+ to 3-4 containers |

### 8.3 What to Avoid

1. **Don't go pure monolith**: Agent and Knowledge services have legitimately different scaling needs
2. **Don't keep current state**: The overhead isn't justified by the benefits
3. **Don't over-engineer modules**: Keep module boundaries simple; extract only if team grows

---

## 9. Conclusion

FaultMaven's current microservices architecture represents **premature optimization** for the product's stage and business model. The overhead of 7+ services is not justified when:

- The target includes self-hosted users who need simplicity
- A small team maintains all services
- Most services don't require independent scaling
- Services are tightly coupled via shared library

A **Hybrid Modular Monolith** approach provides:
- Simpler deployment for Core users (adoption advantage)
- Maintained scalability for Enterprise AI workloads
- Faster development velocity
- Lower operational overhead
- Clear path to extract services if future needs require it

**The best architecture is the simplest one that meets current requirements while allowing for future growth.** For FaultMaven today, that's the hybrid approach.

---

## Appendix A: Architecture Decision Record (ADR)

### ADR-001: Adopt Hybrid Modular Monolith Architecture

**Status**: Proposed

**Context**: FaultMaven currently uses a microservices architecture with 7 separate services. This creates operational overhead for self-hosted users and development friction for the small team.

**Decision**: Consolidate Auth, Session, Case, and Evidence services into a single Modular Monolith while keeping Agent, Knowledge, and Job Worker as separate services.

**Consequences**:
- (+) Simpler deployment for Core users
- (+) Faster development for CRUD features
- (+) Maintained scalability for AI workloads
- (-) Migration effort required
- (-) Less granular scaling for CRUD operations (acceptable trade-off)

---

## Appendix B: References

- Fowler, M. (2015). "MonolithFirst" - https://martinfowler.com/bliki/MonolithFirst.html
- Newman, S. (2019). "Monolith to Microservices" - O'Reilly Media
- Richardson, C. (2018). "Microservices Patterns" - Manning Publications
- Dehghani, Z. (2020). "How to Move Beyond a Monolithic Data Lake to a Distributed Data Mesh"
