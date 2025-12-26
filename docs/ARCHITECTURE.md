# FaultMaven Architecture Overview

**Architecture**: Modular Monolith
**Status**: Production Ready
**Last Updated**: 2025-12-26

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

### 1. **Modular Monolith Design**
- Single deployable unit with clear module boundaries
- Each module owns its domain logic, routes, and services
- Modules communicate through well-defined interfaces
- Shared infrastructure layer (no duplication)

### 2. **Vertical Slice Architecture**
Each module contains:
- **Router** (`routers.py`) - HTTP endpoints
- **Service** (`service.py`) - Business logic
- **Models** (`models.py`) - ORM entities
- **Dependencies** - Module-specific DI

### 3. **Provider Abstraction**
Infrastructure accessed through provider interfaces:
- `LLMProvider` - Multi-provider LLM support (7 providers)
- `DataProvider` - Database abstraction (SQLite/PostgreSQL)
- `FileProvider` - File storage (local/S3)
- `VectorProvider` - Vector store (ChromaDB/Pinecone)
- `IdentityProvider` - Auth (JWT/OAuth)

---

## Module Architecture

### Module Structure

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

## Module Responsibilities

### Auth Module
**Purpose**: User authentication and authorization

**Capabilities**:
- User registration and login
- JWT token generation and validation
- Password hashing (bcrypt)
- User profile management

**Data Store**: SQLite/PostgreSQL (users table)

**Endpoints**:
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

---

### Session Module
**Purpose**: Multi-session management with client-based resumption

**Capabilities**:
- Create and manage user sessions
- Client-based session resumption (device continuity)
- Session timeout with configurable TTL (60-480 minutes)
- Session cleanup and recovery
- Heartbeat tracking

**Data Store**: Redis (key-value with TTL)

**Endpoints**:
- `POST /sessions` - Create with client_id resumption
- `GET /sessions/{session_id}`
- `POST /sessions/{session_id}/heartbeat`
- `POST /sessions/{session_id}/cleanup`

**Key Feature**: Multiple concurrent sessions per user with device-specific resumption

---

### Case Module
**Purpose**: Investigation lifecycle management with advanced AI framework

**Capabilities**:
- Case CRUD operations
- Investigation state tracking
- Message history
- Hypothesis management
- Solution tracking
- Report generation

**Investigation Framework** (80% integrated):
- ✅ **MemoryManager** - Hierarchical memory (64% token reduction)
- ✅ **WorkingConclusionGenerator** - Continuous progress tracking
- ✅ **PhaseOrchestrator** - Intelligent phase progression
- ✅ **OODAEngine** - Adaptive investigation intensity
- ⏳ **HypothesisManager** - (Pending: requires structured LLM output)

**Data Store**: SQLite/PostgreSQL (cases, messages, hypotheses tables)

**Endpoints**:
- `POST /cases` - Create case
- `GET /cases/{case_id}`
- `POST /cases/{case_id}/messages`
- `POST /cases/{case_id}/hypotheses`
- `POST /cases/{case_id}/solutions`

**Status**: See [INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md](INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md) for detailed framework status

---

### Evidence Module
**Purpose**: File upload and evidence management

**Capabilities**:
- File upload (logs, configs, screenshots)
- Evidence metadata tracking
- Evidence-case association
- File download and retrieval

**Data Store**:
- SQLite/PostgreSQL (evidence metadata)
- Local filesystem or S3 (file content)

**Endpoints**:
- `POST /evidence/upload`
- `GET /evidence/{evidence_id}`
- `GET /evidence/{evidence_id}/download`
- `DELETE /evidence/{evidence_id}`

---

### Knowledge Module
**Purpose**: Knowledge base with semantic search (RAG)

**Capabilities**:
- Document ingestion and embedding
- Semantic search via vector similarity
- Three knowledge collections:
  - **User KB**: Personal runbooks
  - **Global KB**: System-wide documentation
  - **Case KB**: Case-specific knowledge (auto-cleanup)
- Document management (create, delete, list)

**Data Store**:
- ChromaDB (vector embeddings)
- SQLite/PostgreSQL (document metadata)

**Endpoints**:
- `POST /knowledge/documents` - Ingest document
- `POST /knowledge/search` - Semantic search
- `GET /knowledge/documents`
- `DELETE /knowledge/documents/{doc_id}`

**Embedding Model**: BGE-M3 (multilingual, multi-granularity)

---

### Agent Module
**Purpose**: AI agent orchestration with multi-turn conversations

**Capabilities**:
- Multi-turn troubleshooting conversations
- Context-aware responses
- RAG integration (knowledge retrieval)
- Multi-provider LLM support (7 providers)
- Response type system (9 types)

**Response Types**:
1. `ANSWER` - Direct answer
2. `PLAN_PROPOSAL` - Investigation plan
3. `CLARIFICATION_REQUEST` - Request more info
4. `CONFIRMATION_REQUEST` - Confirm action
5. `SOLUTION_READY` - Solution proposal
6. `NEEDS_MORE_DATA` - Request evidence
7. `ESCALATION_REQUIRED` - Human escalation
8. `STATUS_UPDATE` - Progress update
9. `ERROR` - Error handling

**LLM Providers**: Fireworks, OpenAI, Anthropic, Google Gemini, HuggingFace, OpenRouter, Local (Ollama/vLLM)

**Endpoints**:
- `POST /agent/chat/{case_id}` - Send message
- `GET /agent/health`

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

## Deployment Profiles

### Core Profile (Default)
- SQLite database
- Local file storage
- In-memory fallback for sessions
- ChromaDB (local)
- JWT authentication

### Team Profile
- PostgreSQL database
- Shared Redis for sessions
- ChromaDB (shared)
- JWT authentication

### Enterprise Profile
- PostgreSQL database (HA)
- Redis cluster
- S3 file storage
- Pinecone vector store
- OAuth/SAML authentication

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

## Testing Strategy

### Unit Tests
- Service layer mocked with provider interfaces
- 148/148 tests passing (100%)
- 47% code coverage

### Integration Tests
- Full stack with test database
- Redis integration tests
- LLM provider integration (mock mode)

### Test Command
```bash
pytest tests/
pytest tests/unit/           # Unit tests only
pytest tests/integration/    # Integration tests only
```

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

For detailed comparison: See [INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md](INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md)

---

## Related Documentation

- **[MODULAR_MONOLITH_DESIGN.md](MODULAR_MONOLITH_DESIGN.md)** - Detailed design rationale
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Developer setup guide
- **[API Documentation](api/)** - Auto-generated OpenAPI specs
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide
- **[INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md](INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md)** - Framework integration status

---

**Last Updated**: 2025-12-26
**Architecture**: Modular Monolith
**Status**: ✅ Production Ready (80% investigation framework integrated)
