# FaultMaven Architecture

**Architecture**: Modular Monolith
**Status**: Production Ready (with known gaps)
**Last Updated**: 2025-12-27

---

## Overview

This folder contains architectural documentation for the FaultMaven system and its modules.

**High-level design**: See [design-specifications.md](design-specifications.md) for target design specifications
**Implementation gaps**: See [../TECHNICAL_DEBT.md](../TECHNICAL_DEBT.md) for what's not yet implemented

---

## System Overview

FaultMaven is built as a **modular monolith** - a single codebase organized into well-defined modules with clear boundaries. This architecture provides the simplicity of a monolith with the maintainability of microservices.

```
┌─────────────────────────────────────────────────────┐
│         Browser Extension / Dashboard                │
└────────────────────┬────────────────────────────────┘
                     │ HTTPS
                     ▼
┌─────────────────────────────────────────────────────┐
│              FaultMaven Monolith (8000)              │
│                                                       │
│  ┌───────────────────────────────────────────────┐  │
│  │              Module Layer                      │  │
│  ├───────┬────────┬──────┬────────┬────────┬─────┤  │
│  │ Auth  │Session │ Case │Evidence│Knowledge│Agent│  │
│  │       │        │      │        │         │     │  │
│  └───┬───┴────┬───┴──┬───┴────┬───┴────┬────┴─┬───┘  │
│      │        │      │        │        │      │      │
│  ┌───▼────────▼──────▼────────▼────────▼──────▼───┐  │
│  │          Shared Infrastructure Layer          │  │
│  │  Providers | ORM | Redis | ChromaDB | LLM    │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │    Infrastructure           │
        │  SQLite/PostgreSQL          │
        │  Redis (sessions/cache)     │
        │  ChromaDB (vectors)         │
        │  LLM Providers (7 supported)│
        └────────────────────────────┘
```

---

## Architecture Principles

### 1. Modular Monolith Design

- Single deployable unit with clear module boundaries
- Each module owns its domain logic, routes, and services
- Modules communicate through well-defined interfaces
- Shared infrastructure layer (no duplication)

### 2. Vertical Slice Architecture

Each module contains:

- **Router** (`routers.py`) - HTTP endpoints
- **Service** (`service.py`) - Business logic
- **Models** (`models.py`) - ORM entities
- **Dependencies** - Module-specific DI

### 3. Provider Abstraction

Infrastructure accessed through provider interfaces:

- `LLMProvider` - Multi-provider LLM support (7 providers)
- `DataProvider` - Database abstraction (SQLite/PostgreSQL)
- `FileProvider` - File storage (local/S3)
- `VectorProvider` - Vector store (ChromaDB/Pinecone)
- `IdentityProvider` - Auth (JWT/OAuth)

---

## Module Structure

```
src/faultmaven/modules/
├── auth/               # Authentication & authorization
│   ├── routers.py     # /auth/* endpoints
│   ├── service.py     # AuthService
│   └── models.py      # User ORM model
├── session/           # Session management
│   ├── routers.py     # /sessions/* endpoints
│   ├── service.py     # SessionService
│   └── models.py      # Session ORM model
├── case/              # Investigation management
│   ├── routers.py     # /cases/* endpoints
│   ├── service.py     # CaseService
│   ├── models.py      # Case, Message ORM models
│   ├── investigation.py  # Investigation domain models
│   └── engines/       # Investigation framework
│       ├── milestone_engine.py
│       ├── hypothesis_manager.py
│       ├── ooda_engine.py
│       ├── memory_manager.py           # ✅ Integrated
│       ├── working_conclusion_generator.py  # ✅ Integrated
│       └── phase_orchestrator.py       # ✅ Integrated
├── evidence/          # File upload & evidence
│   ├── routers.py     # /evidence/* endpoints
│   ├── service.py     # EvidenceService
│   └── models.py      # Evidence ORM model
├── knowledge/         # Knowledge base (RAG)
│   ├── routers.py     # /knowledge/* endpoints
│   ├── service.py     # KnowledgeService
│   └── models.py      # Document ORM model
└── agent/             # AI agent orchestration
    ├── routers.py     # /agent/* endpoints
    ├── service.py     # AgentService
    └── response_types.py  # Response type system
```

---

## Shared Infrastructure

### Provider Layer (`src/faultmaven/providers/`)

**Purpose**: Abstract infrastructure dependencies behind interfaces

**Providers**:

- **LLM Provider** (`llm/`) - Multi-provider LLM routing with fallback
- **Data Provider** (`data.py`) - SQLAlchemy ORM wrapper
- **File Provider** (`files.py`) - Local/S3 file storage
- **Vector Provider** (`vectors.py`) - ChromaDB/Pinecone abstraction

**Configuration**:

- Protocol-based interfaces (PEP 544)
- Deployment profile support (Core/Team/Enterprise)
- Automatic provider selection based on configuration

### Infrastructure Layer (`src/faultmaven/infrastructure/`)

**Purpose**: Concrete implementations of infrastructure services

**Components**:

- **Redis** (`redis_impl.py`) - Session storage, caching
- **In-Memory** (`memory_impl.py`) - Fallback session storage
- **SQLAlchemy** - ORM for all modules

---

## Data Flow Examples

### 1. User Login Flow

```
Browser → POST /auth/login
       → AuthService.login()
       → DataProvider.query(User, email=...)
       → JWT token generation
       → Response with access_token
```

### 2. Investigation Chat Flow

```
Browser → POST /agent/chat/{case_id}
       → AgentService.process_message()
       → KnowledgeService.search() [RAG retrieval]
       → LLMProvider.chat() [LLM inference]
       → CaseService.add_message()
       → MilestoneEngine.process_turn()
         ├─→ MemoryManager.organize_memory()
         ├─→ WorkingConclusionGenerator.generate()
         ├─→ PhaseOrchestrator.detect_loopback()
         └─→ OODAEngine.get_current_intensity()
       → Response with answer + updated state
```

### 3. Knowledge Base Search

```
Browser → POST /knowledge/search
       → KnowledgeService.search()
       → VectorProvider.search() [ChromaDB]
       → Semantic similarity ranking
       → Response with relevant documents
```

---

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///./data/faultmaven.db

# LLM Provider (7 supported)
LLM_PROVIDER=openai  # fireworks, anthropic, google, ollama, etc.
OPENAI_API_KEY=sk-...

# Redis (sessions/cache)
REDIS_HOST=localhost
REDIS_PORT=6379

# ChromaDB (vectors)
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Session Configuration
SESSION_TIMEOUT_MINUTES=60  # 60-480 range
```

### Feature Flags

- `ENABLE_RAG`: Enable knowledge base search (default: true)
- `ENABLE_STREAMING`: Enable streaming responses (default: false)
- `DEBUG_MODE`: Enhanced logging (default: false)

---

## Performance Characteristics

### Token Efficiency

- **Before**: 4,500+ tokens per investigation turn
- **After**: ~1,600 tokens (64% reduction via MemoryManager)

### Response Times

- Chat endpoint: <2s (p95)
- Knowledge search: <500ms (p95)
- Session operations: <100ms (p95)

### Scalability

- Single process: 100-500 req/s
- Horizontal scaling: Multiple processes behind load balancer
- Database: SQLite (dev), PostgreSQL (production)

---

## Migration History

FaultMaven evolved through three architectural phases:

1. **Original Monolith** (FaultMaven-Mono) - Feature-complete reference implementation
2. **Microservices** (2024) - Split into 8 independent services
3. **Modular Monolith** (Current) - Consolidated with improved architecture

**Current Status**: Production-ready modular monolith with 80% investigation framework integration

---

## Module Documentation

Detailed documentation for each module:

- [auth.md](auth.md) - Authentication module
- [session.md](session.md) - Session management module
- [case.md](case.md) - Case/investigation module
- [evidence.md](evidence.md) - Evidence management module
- [knowledge.md](knowledge.md) - Knowledge base module
- [agent.md](agent.md) - AI agent module

---

## Implementation Gaps

For current implementation status and gaps, see:

- **Module Implementation Summary**: [design-specifications.md#implementation-status](design-specifications.md#implementation-status)
- **Detailed Gap Analysis**: [../TECHNICAL_DEBT.md](../TECHNICAL_DEBT.md)

**Quick Status** (as of 2025-12-27):

- **Authentication**: ✅ Complete
- **Session**: ✅ 95% (minor features missing)
- **Case**: ⚠️ 80% (report generation, search missing)
- **Evidence**: ❌ 0% advanced (data processing pipeline missing)
- **Knowledge**: ⚠️ 10% advanced
- **Agent**: ❌ 12.5% advanced (tools framework missing)

---

## Related Documentation

- **[modular-monolith-rationale.md](modular-monolith-rationale.md)** - Design rationale and patterns
- **[design-specifications.md](design-specifications.md)** - Target design specifications
- **[../TECHNICAL_DEBT.md](../TECHNICAL_DEBT.md)** - Implementation gaps and roadmap
- **[../DEVELOPMENT.md](../DEVELOPMENT.md)** - Developer setup guide
- **[../DEPLOYMENT.md](../DEPLOYMENT.md)** - Production deployment guide

---

**Last Updated**: 2025-12-27
**Architecture**: Modular Monolith
**Status**: ✅ Production Ready (80% investigation framework integrated)
