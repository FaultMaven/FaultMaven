# FaultMaven Modular Monolith Architecture

## Overview

FaultMaven is an AI-powered troubleshooting platform built as a **modular monolith with a background worker**. This architecture consolidates 7 logical services into a single deployable application while keeping CPU-intensive background processing separate.

### Architecture Summary

| Component | Description |
|-----------|-------------|
| **FaultMaven Monolith** | Single application containing all user-facing functionality |
| **Job Worker** | Separate service for CPU-intensive background tasks |
| **Deployable Units** | 2 (monolith + worker) |

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FaultMaven Monolith                              │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Modules: Auth │ Session │ Case │ Evidence │ Knowledge │ Agent   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Providers: Data │ Files │ Vector │ Identity │ LLM                │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                          Redis (Queue/Cache)
                                    │
                                    ▼
              ┌───────────────────────────────────────────┐
              │              Job Worker                    │
              │  • Embedding generation                    │
              │  • Document extraction                     │
              │  • Scheduled tasks                         │
              └───────────────────────────────────────────┘
```

---

## 1. System Architecture

### 1.1 Application Structure

```
faultmaven/
├── src/faultmaven/
│   ├── main.py                    # FastAPI application entry
│   ├── middleware/
│   │   └── gateway.py             # JWT, CORS, rate limiting
│   ├── api/
│   │   ├── auth.py                # /v1/auth/*
│   │   ├── sessions.py            # /v1/sessions/*
│   │   ├── cases.py               # /v1/cases/*
│   │   ├── evidence.py            # /v1/evidence/*
│   │   ├── knowledge.py           # /v1/knowledge/*
│   │   └── agent.py               # /v1/agent/*
│   ├── modules/
│   │   ├── auth/
│   │   ├── session/
│   │   ├── case/
│   │   ├── evidence/
│   │   ├── knowledge/             # Query path only
│   │   └── agent/                 # LLM orchestration
│   ├── providers/
│   │   ├── data/                  # SQLite, PostgreSQL
│   │   ├── files/                 # Local, S3
│   │   ├── vectors/               # ChromaDB, Pinecone
│   │   ├── identity/              # JWT, Auth0
│   │   └── llm/                   # OpenAI, Anthropic, Ollama
│   └── infrastructure/
│       ├── interfaces.py          # SessionStore, JobQueue, Cache, ResultStore
│       └── redis_impl.py
├── tests/
├── deploy/
│   ├── docker-compose.yml
│   └── kubernetes/helm/
├── Dockerfile
└── pyproject.toml
```

### 1.2 Module Inventory

| Module | Responsibility | Key Dependencies |
|--------|----------------|------------------|
| **Auth** | User registration, login, JWT | IdentityProvider |
| **Session** | Session lifecycle management | SessionStore (Redis) |
| **Case** | Case CRUD, message history | DataProvider |
| **Evidence** | File uploads, attachments | FileProvider |
| **Knowledge** | Vector search (query path only) | VectorProvider |
| **Agent** | LLM orchestration, chat | LLMProvider, KnowledgeService |

### 1.3 Background Worker

The Job Worker handles CPU-intensive tasks that don't require user-facing latency:

| Task | Description | Trigger |
|------|-------------|---------|
| **Embedding Generation** | Generate vectors for documents | Document upload |
| **Text Extraction** | Extract text from PDFs, images | Document upload |
| **Scheduled Cleanup** | Remove expired sessions, orphaned files | Cron |
| **Post-Mortem Generation** | Generate case summaries | Case close |

---

## 2. Module Design

### 2.1 Module Structure

Each module follows a consistent internal structure:

```python
modules/auth/
├── __init__.py        # Public interface ONLY
├── service.py         # Business logic
├── repository.py      # Data access
├── models.py          # DTOs (Pydantic models)
└── orm.py             # Internal ORM models (not exported)
```

### 2.2 Public Interface Pattern

Modules expose only their public interface through `__init__.py`:

```python
# modules/auth/__init__.py
from .service import AuthService
from .models import UserDTO, TokenPair, CreateUserRequest

__all__ = ["AuthService", "UserDTO", "TokenPair", "CreateUserRequest"]

# NEVER export: orm.py, repository.py internals, SQLAlchemy models
```

### 2.3 Module Boundaries

**The Golden Rule**: A module may NEVER directly query another module's database tables.

```python
# FORBIDDEN: Cross-module database access
from modules.auth.orm import UserORM  # Don't import ORM models
db.query(Case, UserORM).join(...)     # Don't join across modules

# REQUIRED: Access through public interface
from modules.auth import AuthService, UserDTO

class CaseService:
    def __init__(self, auth: AuthService):
        self.auth = auth

    async def get_case_with_owner(self, case_id: str) -> CaseWithOwner:
        case = await self.repo.get(case_id)
        owner: UserDTO = await self.auth.get_user(case.owner_id)
        return CaseWithOwner(case=case, owner=owner)
```

### 2.4 Boundary Enforcement

Enforce module boundaries via `import-linter` in CI:

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
    "faultmaven.modules.case.repository",
    "faultmaven.modules.evidence.repository",
    "faultmaven.modules.knowledge.repository",
    "faultmaven.modules.agent.repository",
]
```

---

## 3. Provider Abstraction Layer

### 3.1 Purpose

The provider layer enables the same codebase to run on:
- Developer laptop (SQLite, local files, ChromaDB)
- Small team server (PostgreSQL, local files, ChromaDB)
- Enterprise SaaS (PostgreSQL cluster, S3, Pinecone)

### 3.2 Provider Interfaces

```python
# providers/interfaces.py

from typing import Protocol, TypeVar, Optional
from datetime import timedelta

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

class LLMProvider(Protocol):
    """Abstract interface for LLM calls."""
    async def chat(self, messages: list[Message], model: str = None) -> ChatResponse: ...
    async def embed(self, text: str) -> list[float]: ...
```

### 3.3 Provider Implementations

```
providers/
├── data/
│   ├── sqlite.py          # SQLiteDataProvider (Core)
│   └── postgresql.py      # PostgreSQLDataProvider (Team/Enterprise)
├── files/
│   ├── local.py           # LocalFileProvider (Core)
│   └── s3.py              # S3FileProvider (Enterprise)
├── vectors/
│   ├── chromadb.py        # ChromaDBProvider (Core)
│   └── pinecone.py        # PineconeProvider (Enterprise)
├── identity/
│   ├── jwt.py             # JWTIdentityProvider (Core)
│   └── auth0.py           # Auth0IdentityProvider (Enterprise)
└── llm/
    ├── openai.py          # OpenAIProvider
    ├── anthropic.py       # AnthropicProvider
    └── ollama.py          # OllamaProvider (local LLM)
```

### 3.4 Configuration-Based Selection

```python
# config.py
from pydantic_settings import BaseSettings
from enum import Enum

class DeploymentProfile(str, Enum):
    CORE = "core"           # Self-hosted minimal
    TEAM = "team"           # Self-hosted with PostgreSQL
    ENTERPRISE = "enterprise"  # SaaS

class Settings(BaseSettings):
    PROFILE: DeploymentProfile = DeploymentProfile.CORE

    # Data
    DATABASE_URL: str = "sqlite:///./data/faultmaven.db"

    # Files
    FILE_STORAGE: str = "local"  # local, s3
    FILE_STORAGE_PATH: str = "./data/files"
    S3_BUCKET: Optional[str] = None

    # Vectors
    VECTOR_STORE: str = "chromadb"  # chromadb, pinecone
    CHROMADB_PATH: str = "./data/chromadb"

    # Identity
    IDENTITY_PROVIDER: str = "jwt"  # jwt, auth0
    JWT_SECRET: str = "change-me-in-production"

    # LLM
    LLM_PROVIDER: str = "openai"  # openai, anthropic, ollama
    OPENAI_API_KEY: Optional[str] = None
    OLLAMA_HOST: str = "http://localhost:11434"
```

---

## 4. Infrastructure Abstractions

### 4.1 Purpose

Infrastructure services (Redis) are accessed through abstract interfaces, not directly:

```
Module Layer
    │
    ▼
┌────────────────────────────────────────────────────────┐
│  SessionStore │ JobQueue │ Cache │ ResultStore        │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────┐
│                     Redis                               │
└────────────────────────────────────────────────────────┘
```

### 4.2 Infrastructure Interfaces

```python
# infrastructure/interfaces.py

class SessionStore(Protocol):
    """Abstract session storage."""
    async def get(self, session_id: str) -> Optional[dict]: ...
    async def set(self, session_id: str, data: dict, ttl: timedelta) -> None: ...
    async def delete(self, session_id: str) -> None: ...

class JobQueue(Protocol):
    """Abstract job queue."""
    async def enqueue(self, job_type: str, payload: dict, **options) -> str: ...
    async def get_status(self, job_id: str) -> JobStatus: ...

class Cache(Protocol):
    """Abstract cache."""
    async def get(self, key: str) -> Optional[bytes]: ...
    async def set(self, key: str, value: bytes, ttl: timedelta) -> None: ...
    async def invalidate(self, pattern: str) -> None: ...

class ResultStore(Protocol):
    """Abstract result storage for async operations."""
    async def get(self, job_id: str) -> Optional[Any]: ...
    async def set(self, job_id: str, result: Any, ttl: timedelta = None) -> None: ...
```

---

## 5. Agent Module Design

### 5.1 Overview

The Agent module orchestrates LLM calls for the chat functionality. LLM inference happens externally (OpenAI, Anthropic, or local Ollama)—the Agent just orchestrates HTTP calls.

### 5.2 Module Structure

```python
modules/agent/
├── __init__.py        # Public interface
├── service.py         # Chat orchestration
├── router.py          # Model selection logic
├── models.py          # Request/response DTOs
└── prompts/           # Prompt templates
```

### 5.3 LLMProvider Abstraction

The Agent module calls LLM providers through a common interface:

```python
# providers/llm/base.py

class LLMProvider(Protocol):
    async def chat(
        self,
        messages: list[Message],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
    ) -> ChatResponse: ...

# providers/llm/openai.py
class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def chat(self, messages, model="gpt-4", **kwargs):
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
        return ChatResponse(content=response.choices[0].message.content)

# providers/llm/ollama.py
class OllamaProvider(LLMProvider):
    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host

    async def chat(self, messages, model="llama2", **kwargs):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.host}/api/chat",
                json={"model": model, "messages": messages}
            )
        return ChatResponse(content=response.json()["message"]["content"])
```

**Key Point**: Local vs cloud LLM is configuration, not architecture. The monolith makes HTTP calls either way.

### 5.4 Async Pattern for Long-Running Calls

LLM calls take 10-60+ seconds. Use async pattern to avoid blocking:

```python
# modules/agent/service.py

class AgentService:
    def __init__(
        self,
        llm_provider: LLMProvider,
        knowledge: KnowledgeService,
        result_store: ResultStore,
    ):
        self.llm = llm_provider
        self.knowledge = knowledge
        self.results = result_store

    async def submit_chat(self, case_id: str, message: str, context: dict) -> str:
        """Submit chat request, return job ID immediately."""
        job_id = str(uuid4())

        # Start background task
        asyncio.create_task(
            self._process_chat(job_id, case_id, message, context)
        )

        return job_id

    async def _process_chat(self, job_id: str, case_id: str, message: str, context: dict):
        """Background task for LLM processing."""
        try:
            # RAG: Search knowledge base
            kb_results = await self.knowledge.search(message)

            # Call LLM
            response = await self.llm.chat(
                messages=self._build_messages(message, context, kb_results)
            )

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
        return await self.results.get(job_id)
```

### 5.5 API Endpoints

```python
# api/agent.py

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

### 5.6 Agent Evolution Path

The Agent module has internal boundaries for future complexity:

```
┌─────────────────────────────────────────────────────────────────┐
│                      Agent Module                                │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │   Router     │  │   Executor   │  │      Optimizer         │ │
│  │              │  │              │  │                        │ │
│  │ • Model      │  │ • LLM calls  │  │ • Response caching     │ │
│  │   selection  │  │ • Retry      │  │ • Cost optimization    │ │
│  │ • Fallback   │  │   logic      │  │ • Prompt compression   │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Extraction triggers** (unlikely for most deployments):
- CPU contention with other modules
- 3+ dedicated AI engineers
- Agent needs independent deployment cadence

---

## 6. Event Contracts

### 6.1 Job Queue Events

Events between monolith and Job Worker use versioned schemas:

```yaml
# events/schemas/embedding_request.v1.yaml (AsyncAPI)
asyncapi: 2.6.0
info:
  title: FaultMaven Job Events
  version: 1.0.0

channels:
  jobs.embedding:
    publish:
      message:
        name: EmbeddingRequest
        payload:
          type: object
          required: [version, job_id, document_id, content]
          properties:
            version:
              type: string
              enum: ["1.0"]
            job_id:
              type: string
              format: uuid
            document_id:
              type: string
            content:
              type: string
            metadata:
              type: object
```

### 6.2 Versioning Rules

| Change Type | Action | Example |
|-------------|--------|---------|
| Add optional field | Minor bump | Add `priority` field |
| Add required field | Major bump, migration | Add `tenant_id` required |
| Remove field | Major bump, deprecation | Remove `legacy_field` |
| Change field type | Major bump | `id: int` → `string` |

---

## 7. Deployment

### 7.1 Container Configuration

```yaml
# deploy/docker-compose.yml

services:
  faultmaven:
    image: faultmaven/core:latest
    environment:
      PROFILE: core
      DATABASE_URL: sqlite:///data/faultmaven.db
      FILE_STORAGE: local
      VECTOR_STORE: chromadb
      LLM_PROVIDER: openai
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    volumes:
      - ./data:/data
    ports:
      - "8000:8000"

  job-worker:
    image: faultmaven/job-worker:latest
    environment:
      REDIS_URL: redis://redis:6379
      CHROMADB_PATH: /data/chromadb
    volumes:
      - ./data:/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - ./data/chromadb:/chroma/chroma

volumes:
  redis-data:
```

### 7.2 Deployment Profiles

| Profile | Containers | Use Case |
|---------|------------|----------|
| **Core (Minimal)** | faultmaven + redis | Development, small teams |
| **Core (Full)** | faultmaven + redis + chromadb | Self-hosted production |
| **Enterprise** | faultmaven + job-workers + redis-cluster + managed-db | SaaS |

### 7.3 Local LLM (Ollama)

For self-hosted deployments with local LLM:

```yaml
services:
  faultmaven:
    environment:
      LLM_PROVIDER: ollama
      OLLAMA_HOST: http://ollama:11434

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama-models:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

---

## 8. Testing Strategy

### 8.1 Module Isolation Tests

Each module must be testable in isolation with mocked dependencies:

```python
# tests/modules/test_case_service.py

async def test_get_case_with_owner():
    # Mock dependencies
    mock_auth = AsyncMock(spec=AuthService)
    mock_auth.get_user.return_value = UserDTO(id="user-1", name="Test User")

    mock_repo = AsyncMock(spec=CaseRepository)
    mock_repo.get.return_value = Case(id="case-1", owner_id="user-1")

    # Create service with mocks
    service = CaseService(auth=mock_auth, repo=mock_repo)

    # Test
    result = await service.get_case_with_owner("case-1")

    assert result.case.id == "case-1"
    assert result.owner.name == "Test User"
    mock_auth.get_user.assert_called_once_with("user-1")
```

### 8.2 Architecture Tests

```python
# tests/test_architecture.py

def test_no_cross_module_orm_imports():
    """Ensure modules don't import each other's ORM models."""
    import ast
    from pathlib import Path

    modules = ["auth", "session", "case", "evidence", "knowledge", "agent"]

    for module in modules:
        module_path = Path(f"src/faultmaven/modules/{module}")
        for py_file in module_path.glob("**/*.py"):
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    for other in modules:
                        if other != module:
                            assert f"modules.{other}.orm" not in ast.dump(node)
                            assert f"modules.{other}.repository" not in ast.dump(node)
```

### 8.3 Provider Contract Tests

```python
# tests/providers/test_data_provider_contract.py

@pytest.mark.parametrize("provider", [
    SQLiteDataProvider(":memory:"),
    PostgreSQLDataProvider("postgresql://test@localhost/test"),
])
async def test_data_provider_contract(provider):
    """All DataProvider implementations must pass the same tests."""
    # Create
    entity = await provider.save(User(name="Test"))
    assert entity.id is not None

    # Read
    found = await provider.get(entity.id)
    assert found.name == "Test"

    # Delete
    await provider.delete(entity.id)
    assert await provider.get(entity.id) is None
```

---

## 9. Extraction Readiness

### 9.1 Extraction Checklist

Before extracting any module to a separate service, verify:

| Criterion | Check |
|-----------|-------|
| No shared ORM models | `import-linter` passes |
| No shared DB sessions | Module has own session factory |
| DTOs at boundaries | Only Pydantic models in `__init__.py` |
| Async-safe interfaces | All public methods are async |
| Provider abstractions | No direct infrastructure access |

### 9.2 Extraction Process

To extract a module (e.g., Auth) to a separate service:

1. Copy `modules/auth/` to new repository
2. Add HTTP API layer (FastAPI)
3. Replace in-process calls with HTTP client:

```python
# Before (in-process)
from modules.auth import AuthService
user = await auth_service.get_user(user_id)

# After (HTTP client)
from clients.auth import AuthClient
user = await auth_client.get_user(user_id)  # HTTP call
```

4. No database changes required (module owns its schema)

---

## 10. Repository Structure

### 10.1 Final Repository Layout

```
FaultMaven/
├── faultmaven/              # Main monolith + docs + deploy
│   ├── docs/
│   ├── src/faultmaven/
│   ├── tests/
│   ├── deploy/
│   ├── Dockerfile
│   └── pyproject.toml
│
├── fm-job-worker/           # Background processing
│   ├── src/
│   ├── tests/
│   └── Dockerfile
│
├── faultmaven-copilot/      # Browser extension (unchanged)
│
└── faultmaven-dashboard/    # Web UI (unchanged)
```

### 10.2 Repository Count

- **Before**: 12+ repositories
- **After**: 4 repositories
- **Reduction**: 67%
