# FaultMaven Modular Monolith Architecture

## Overview

FaultMaven is an AI-powered troubleshooting platform built as a **true modular monolith**. All functionality runs in a single process - no microservices required.

### Architecture Summary

| Aspect | Value |
|--------|-------|
| **Repositories** | 2 (faultmaven + faultmaven-copilot) |
| **Deployable Units** | 1 |
| **Processes** | 1 |
| **Containers** | 1 |

```
┌─────────────────────────────────────────────────────────────────┐
│                    FaultMaven (One Monolith)                    │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Middleware: JWT, CORS, Rate Limiting                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  API: /auth │ /sessions │ /cases │ /evidence │ /knowledge │  │
│  │       /agent                                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Modules: Auth │ Session │ Case │ Evidence │ Knowledge │  │  │
│  │           Agent                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Providers: Data │ Files │ Vector │ Identity │ LLM │     │  │
│  │             Embedding                                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Dashboard: Static files served at /                      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Why No Microservices?

Every component was evaluated against the microservice checklist:

| Criterion | Must Pass to Justify Microservice |
|-----------|-----------------------------------|
| Distinct scaling profile | Different CPU/memory/QPS needs |
| Independent deployment reduces risk | Can deploy without affecting others |
| Failure can be isolated | Blast radius is contained |
| Owns its data | No shared DB tables |
| Security/compliance boundary | Isolation required |
| Different rate of change | Evolves independently |
| Clear API boundary | Stable contract |
| Different operational profile | Different monitoring needs |
| Latency tolerance | Can tolerate network calls |
| Clear domain boundary | DDD bounded context |

**No component scored above 3/10.** All share the same failure domain, same scaling profile, and same operational characteristics.

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
│   │   ├── knowledge/
│   │   └── agent/
│   ├── providers/
│   │   ├── data/                  # SQLite, PostgreSQL
│   │   ├── files/                 # Local, S3
│   │   ├── vectors/               # ChromaDB, Pinecone
│   │   ├── identity/              # JWT, Auth0
│   │   ├── llm/                   # OpenAI, Anthropic, Ollama
│   │   └── embedding/             # OpenAI, Cohere, local
│   └── infrastructure/
│       ├── config.py
│       └── scheduler.py           # In-process scheduled tasks
├── dashboard/                     # React frontend source
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── tests/
├── deploy/
│   ├── docker-compose.yml
│   └── kubernetes/helm/
├── Dockerfile                     # Multi-stage: dashboard + backend
└── pyproject.toml
```

### 1.2 Module Inventory

| Module | Responsibility | Sync/Async |
|--------|----------------|------------|
| **Auth** | User registration, login, JWT | Sync |
| **Session** | Session lifecycle management | Sync |
| **Case** | Case CRUD, message history | Sync |
| **Evidence** | File uploads, attachments | Sync |
| **Knowledge** | Vector search AND ingestion | Both |
| **Agent** | LLM orchestration, chat | Async (long-running) |

### 1.3 Request Patterns

| Pattern | Example | Implementation |
|---------|---------|----------------|
| **Sync** | GET /cases, POST /auth/login | Await and return |
| **Async (user waiting)** | POST /agent/chat | Return job_id, poll for result |
| **Async (background)** | POST /knowledge/documents | Return immediately, process in background |

All async work runs **in-process** using `asyncio.create_task()`.

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
from modules.auth.orm import UserORM
db.query(Case, UserORM).join(...)

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

from typing import Protocol

class DataProvider(Protocol):
    async def get(self, id: str) -> Optional[T]: ...
    async def save(self, entity: T) -> T: ...
    async def delete(self, id: str) -> bool: ...

class FileProvider(Protocol):
    async def upload(self, key: str, data: bytes) -> str: ...
    async def download(self, key: str) -> bytes: ...
    async def get_url(self, key: str, expires_in: int = 3600) -> str: ...

class VectorProvider(Protocol):
    async def upsert(self, id: str, vector: list[float], metadata: dict): ...
    async def search(self, vector: list[float], top_k: int) -> list[dict]: ...

class IdentityProvider(Protocol):
    async def validate_token(self, token: str) -> Optional[User]: ...
    async def create_token(self, user: User) -> TokenPair: ...

class LLMProvider(Protocol):
    async def chat(self, messages: list[Message], model: str = None) -> ChatResponse: ...

class EmbeddingProvider(Protocol):
    async def embed(self, text: str) -> list[float]: ...
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
```

### 3.3 Provider Implementations

```
providers/
├── data/
│   ├── sqlite.py          # Core
│   └── postgresql.py      # Team/Enterprise
├── files/
│   ├── local.py           # Core
│   └── s3.py              # Enterprise
├── vectors/
│   ├── chromadb.py        # Core
│   └── pinecone.py        # Enterprise
├── identity/
│   ├── jwt.py             # Core
│   └── auth0.py           # Enterprise
├── llm/
│   ├── openai.py
│   ├── anthropic.py
│   └── ollama.py          # Local LLM
└── embedding/
    ├── openai.py          # Cloud embeddings
    ├── cohere.py          # Cloud embeddings
    └── local.py           # Local (sentence-transformers via HTTP)
```

### 3.4 Configuration-Based Selection

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Data
    DATABASE_URL: str = "sqlite:///./data/faultmaven.db"

    # Files
    FILE_STORAGE: str = "local"  # local, s3
    FILE_STORAGE_PATH: str = "./data/files"

    # Vectors
    VECTOR_STORE: str = "chromadb"  # chromadb, pinecone

    # Identity
    IDENTITY_PROVIDER: str = "jwt"  # jwt, auth0

    # LLM
    LLM_PROVIDER: str = "openai"  # openai, anthropic, ollama

    # Embeddings
    EMBEDDING_PROVIDER: str = "openai"  # openai, cohere, local
```

---

## 4. Knowledge Module

### 4.1 Overview

The Knowledge module handles both **query** (vector search) and **ingestion** (embedding generation). Both operations are in the same module, same process.

### 4.2 Endpoints

```python
# api/knowledge.py

@router.get("/v1/knowledge/search")
async def search(query: str, knowledge: KnowledgeService = Depends()):
    """Sync - user waiting for results"""
    return await knowledge.search(query)

@router.post("/v1/knowledge/documents")
async def upload_document(file: UploadFile, knowledge: KnowledgeService = Depends()):
    """Async - return immediately, process in background"""
    doc_id = await knowledge.start_ingestion(file)
    return {"id": doc_id, "status": "processing"}

@router.get("/v1/knowledge/documents/{doc_id}")
async def get_document_status(doc_id: str, knowledge: KnowledgeService = Depends()):
    """Check ingestion status"""
    return await knowledge.get_status(doc_id)
```

### 4.3 Implementation

```python
# modules/knowledge/service.py

class KnowledgeService:
    def __init__(
        self,
        vector_provider: VectorProvider,
        embedding_provider: EmbeddingProvider,
        file_provider: FileProvider,
    ):
        self.vectors = vector_provider
        self.embeddings = embedding_provider
        self.files = file_provider

    async def search(self, query: str) -> list[Document]:
        """Query path - sync, fast"""
        query_vector = await self.embeddings.embed(query)
        return await self.vectors.search(query_vector, top_k=10)

    async def start_ingestion(self, file: UploadFile) -> str:
        """Start background ingestion, return immediately"""
        doc_id = str(uuid4())

        # Save file
        await self.files.upload(f"docs/{doc_id}", await file.read())

        # Start background processing
        asyncio.create_task(self._process_ingestion(doc_id, file))

        return doc_id

    async def _process_ingestion(self, doc_id: str, file: UploadFile):
        """Background task - runs in same process"""
        try:
            # Extract text
            text = await extract_text(file)

            # Chunk
            chunks = chunk_text(text, chunk_size=512, overlap=50)

            # Embed (calls cloud API like OpenAI)
            vectors = await self.embeddings.embed_batch(chunks)

            # Store
            for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                await self.vectors.upsert(
                    id=f"{doc_id}_{i}",
                    vector=vector,
                    metadata={"doc_id": doc_id, "text": chunk}
                )

            await self._set_status(doc_id, "completed")
        except Exception as e:
            await self._set_status(doc_id, "failed", error=str(e))
```

---

## 5. Agent Module

### 5.1 Overview

The Agent module orchestrates LLM calls. All LLM inference is **external** (OpenAI, Anthropic, or Ollama running as infrastructure). The Agent just makes HTTP calls.

### 5.2 Async Pattern

LLM calls take 10-60+ seconds. Use async pattern:

```python
# modules/agent/service.py

class AgentService:
    def __init__(
        self,
        llm_provider: LLMProvider,
        knowledge: KnowledgeService,
    ):
        self.llm = llm_provider
        self.knowledge = knowledge
        self.results: dict[str, ChatResult] = {}  # Or Redis-backed

    async def submit_chat(self, case_id: str, message: str) -> str:
        """Return job_id immediately, process in background"""
        job_id = str(uuid4())
        asyncio.create_task(self._process_chat(job_id, case_id, message))
        return job_id

    async def _process_chat(self, job_id: str, case_id: str, message: str):
        """Background task"""
        try:
            # RAG: search knowledge base
            sources = await self.knowledge.search(message)

            # Call LLM (external API)
            response = await self.llm.chat(
                messages=self._build_messages(message, sources)
            )

            self.results[job_id] = ChatResult(status="completed", response=response)
        except Exception as e:
            self.results[job_id] = ChatResult(status="failed", error=str(e))

    async def get_result(self, job_id: str) -> Optional[ChatResult]:
        return self.results.get(job_id)
```

### 5.3 API Endpoints

```python
# api/agent.py

@router.post("/v1/agent/chat")
async def submit_chat(request: ChatRequest, agent: AgentService = Depends()):
    job_id = await agent.submit_chat(request.case_id, request.message)
    return {"job_id": job_id, "status": "processing"}

@router.get("/v1/agent/chat/{job_id}")
async def get_result(job_id: str, agent: AgentService = Depends()):
    result = await agent.get_result(job_id)
    if result:
        return {"status": result.status, "result": result}
    return {"status": "processing"}
```

---

## 6. Dashboard

### 6.1 Overview

Dashboard is a React SPA that:
- Is built into static files (HTML/JS/CSS)
- Is bundled into the Docker image
- Is served by the monolith at `/`

### 6.2 Build Process

```dockerfile
# Dockerfile

# Stage 1: Build dashboard
FROM node:20 AS dashboard
WORKDIR /app/dashboard
COPY dashboard/ .
RUN npm ci && npm run build

# Stage 2: Python app
FROM python:3.12-slim
WORKDIR /app
COPY --from=dashboard /app/dashboard/dist /app/static/dashboard
COPY src/ /app/src/
RUN pip install .
CMD ["uvicorn", "faultmaven.main:app", "--host", "0.0.0.0"]
```

### 6.3 Serving Static Files

```python
# main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# API routes
app.include_router(auth_router, prefix="/v1")
app.include_router(cases_router, prefix="/v1")
# ... other routers

# Dashboard static files (must be last)
app.mount("/", StaticFiles(directory="static/dashboard", html=True), name="dashboard")
```

---

## 7. Scheduled Tasks

### 7.1 In-Process Scheduler

Background tasks like cleanup run in-process using APScheduler or similar:

```python
# infrastructure/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=3)  # 3 AM daily
async def cleanup_expired_sessions():
    """Delete expired sessions"""
    await session_service.cleanup_expired()

@scheduler.scheduled_job('cron', hour=4)  # 4 AM daily
async def cleanup_orphaned_files():
    """Delete orphaned files"""
    await evidence_service.cleanup_orphaned()

# Start with app
@app.on_event("startup")
async def start_scheduler():
    scheduler.start()
```

---

## 8. Deployment

### 8.1 Single Container

```yaml
# deploy/docker-compose.yml

services:
  faultmaven:
    image: faultmaven:latest
    environment:
      DATABASE_URL: sqlite:///data/faultmaven.db
      FILE_STORAGE: local
      VECTOR_STORE: chromadb
      LLM_PROVIDER: openai
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    volumes:
      - ./data:/data
    ports:
      - "8000:8000"
```

### 8.2 Running Without Docker

```bash
# From source
pip install -e .
uvicorn faultmaven.main:app --host 0.0.0.0 --port 8000

# Or
python -m faultmaven
```

### 8.3 Deployment Profiles

| Profile | Database | Files | Vectors | LLM |
|---------|----------|-------|---------|-----|
| **Dev** | SQLite | Local | ChromaDB | Ollama |
| **Core** | SQLite | Local | ChromaDB | OpenAI |
| **Team** | PostgreSQL | Local | ChromaDB | OpenAI |
| **Enterprise** | PostgreSQL (managed) | S3 | Pinecone | OpenAI |

Same Docker image, different environment variables.

---

## 9. Testing

### 9.1 Module Isolation

Each module is testable in isolation:

```python
# tests/modules/test_case_service.py

async def test_get_case_with_owner():
    mock_auth = AsyncMock(spec=AuthService)
    mock_auth.get_user.return_value = UserDTO(id="user-1", name="Test")

    mock_repo = AsyncMock(spec=CaseRepository)
    mock_repo.get.return_value = Case(id="case-1", owner_id="user-1")

    service = CaseService(auth=mock_auth, repo=mock_repo)
    result = await service.get_case_with_owner("case-1")

    assert result.owner.name == "Test"
```

### 9.2 Architecture Tests

```python
# tests/test_architecture.py

def test_no_cross_module_imports():
    """Modules don't import each other's internals"""
    # Enforced by import-linter in CI
    pass
```

### 9.3 Provider Contract Tests

```python
# tests/providers/test_data_provider.py

@pytest.mark.parametrize("provider", [
    SQLiteDataProvider(":memory:"),
    PostgreSQLDataProvider("postgresql://test@localhost/test"),
])
async def test_crud_operations(provider):
    """All providers implement the same contract"""
    entity = await provider.save(User(name="Test"))
    assert entity.id is not None

    found = await provider.get(entity.id)
    assert found.name == "Test"
```

---

## 10. Repository Structure

### 10.1 Final Layout

```
FaultMaven/
├── faultmaven/                  # Everything in one repo
│   ├── docs/                    # Architecture docs
│   ├── src/faultmaven/          # Backend (Python)
│   ├── dashboard/               # Frontend (React)
│   ├── tests/
│   ├── deploy/
│   ├── Dockerfile
│   └── pyproject.toml
│
└── faultmaven-copilot/          # Browser extension (separate distribution)
```

### 10.2 Summary

| Metric | Before | After |
|--------|--------|-------|
| Repositories | 12+ | 2 |
| Deployable Units | 8 | 1 |
| Containers | 8+ | 1 |
| Processes | 8+ | 1 |

**One repo. One image. One container. One process.**
