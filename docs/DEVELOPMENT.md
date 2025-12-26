# FaultMaven Development Guide

**Architecture**: Modular Monolith
**Last Updated**: 2025-12-26

This guide will help you set up a local development environment for contributing to FaultMaven.

---

## Prerequisites

### Required

- **Git** - Version control
- **Python 3.11+** - Primary development language
- **Poetry** or **pip** - Python package management
- **Docker** - For infrastructure dependencies (Redis, ChromaDB)

### Recommended

- **VSCode** or **PyCharm** - IDEs with Python support
- **Postman** or **HTTPie** - For API testing
- **Redis Insight** - For Redis debugging (optional)
- **SQLite Browser** - For database inspection (optional)

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/FaultMaven/faultmaven.git
cd faultmaven
```

**Note**: FaultMaven is now a **single repository** with all modules in one codebase.

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .              # Install FaultMaven
pip install -e ".[dev]"       # Install dev dependencies (pytest, ruff, etc.)
```

### 3. Start Infrastructure

Start Redis and ChromaDB using Docker Compose:

```bash
# Option 1: Use provided docker-compose.yml
docker-compose up -d redis chromadb

# Option 2: Infrastructure only
docker-compose -f docker-compose.infra.yml up -d
```

**Services started**:
- Redis: `localhost:6379` (sessions, cache)
- ChromaDB: `localhost:8000` (vector store)

### 4. Configure Environment

Create `.env` file in project root:

```bash
# Copy example configuration
cp .env.example .env

# Edit with your API keys
nano .env
```

**Minimum Configuration**:

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./data/faultmaven.db

# LLM Provider (choose one)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Redis (sessions/cache)
REDIS_HOST=localhost
REDIS_PORT=6379

# ChromaDB (vectors)
CHROMA_HOST=localhost
CHROMA_PORT=8000
```

### 5. Initialize Database

```bash
# Run database migrations
alembic upgrade head

# Or let the app create tables automatically on first run
python -m faultmaven.main
```

### 6. Run FaultMaven

```bash
# Development mode (auto-reload)
uvicorn faultmaven.app:app --reload --port 8000

# Or use the provided script
python -m faultmaven.main
```

**Access Points**:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

---

## Project Structure

```
faultmaven/
├── src/faultmaven/          # Main application code
│   ├── modules/             # 6 domain modules
│   │   ├── auth/           # Authentication
│   │   ├── session/        # Session management
│   │   ├── case/           # Investigation management
│   │   │   └── engines/    # Investigation framework
│   │   ├── evidence/       # File upload
│   │   ├── knowledge/      # Knowledge base (RAG)
│   │   └── agent/          # AI agent orchestration
│   ├── providers/          # Infrastructure abstractions
│   │   ├── interfaces.py  # Provider protocols
│   │   ├── llm/           # LLM providers
│   │   ├── data.py        # Database provider
│   │   ├── files.py       # File storage provider
│   │   └── vectors.py     # Vector store provider
│   ├── infrastructure/     # Concrete implementations
│   │   ├── redis_impl.py  # Redis session store
│   │   └── memory_impl.py # In-memory fallback
│   ├── app.py             # FastAPI application
│   ├── dependencies.py    # Dependency injection
│   └── models.py          # ORM model registry
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── docs/                   # Documentation
├── scripts/               # Utility scripts
├── alembic/               # Database migrations
├── .env.example           # Environment template
├── pyproject.toml         # Python dependencies
└── README.md
```

---

## Development Workflow

### Working on a Module

Each module follows vertical slice architecture:

```python
# Example: Working on case module
src/faultmaven/modules/case/
├── routers.py      # HTTP endpoints
├── service.py      # Business logic
├── models.py       # ORM models
├── investigation.py # Domain models
└── engines/        # Framework engines
```

**Typical workflow**:
1. Add/modify endpoint in `routers.py`
2. Implement logic in `service.py`
3. Update models if needed
4. Write tests in `tests/unit/modules/case/`
5. Run tests: `pytest tests/unit/modules/case/`

### Adding a New Endpoint

Example: Add `GET /cases/{case_id}/summary`

```python
# 1. Add route in routers.py
@router.get("/{case_id}/summary")
async def get_case_summary(
    case_id: str,
    case_service: CaseService = Depends(get_case_service),
) -> Dict[str, Any]:
    return await case_service.get_summary(case_id)

# 2. Implement in service.py
async def get_summary(self, case_id: str) -> Dict[str, Any]:
    case = await self.db_session.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")

    return {
        "case_id": case.case_id,
        "status": case.status,
        "message_count": len(case.messages),
        "created_at": case.created_at,
    }

# 3. Add test
async def test_get_case_summary(case_service):
    case = await case_service.create_case(user_id="user123")
    summary = await case_service.get_summary(case.case_id)

    assert summary["case_id"] == case.case_id
    assert summary["status"] == "consulting"
```

### Adding a New Module

```bash
# 1. Create module structure
mkdir -p src/faultmaven/modules/mymodule
touch src/faultmaven/modules/mymodule/{__init__.py,routers.py,service.py,models.py}

# 2. Define ORM models (models.py)
from sqlalchemy import Column, String
from faultmaven.models import Base

class MyModel(Base):
    __tablename__ = "my_table"
    id = Column(String, primary_key=True)
    # ... fields

# 3. Create service (service.py)
class MyModuleService:
    def __init__(self, db_session):
        self.db_session = db_session

# 4. Add routes (routers.py)
from fastapi import APIRouter
router = APIRouter(prefix="/mymodule", tags=["mymodule"])

# 5. Register in app.py
from faultmaven.modules.mymodule.routers import router as mymodule_router
app.include_router(mymodule_router)

# 6. Register model in models.py
from faultmaven.modules.mymodule.models import MyModel
```

---

## Testing

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/unit/modules/case/

# Specific test file
pytest tests/unit/modules/case/test_service.py

# With coverage
pytest --cov=faultmaven tests/

# Watch mode (requires pytest-watch)
ptw tests/
```

### Test Structure

```python
# tests/unit/modules/case/test_service.py
import pytest
from faultmaven.modules.case.service import CaseService

@pytest.fixture
async def case_service(db_session):
    return CaseService(db_session=db_session)

async def test_create_case(case_service):
    case = await case_service.create_case(user_id="user123")
    assert case.case_id is not None
    assert case.status == "consulting"
```

### Test Coverage Goals

- **Unit tests**: 80%+ coverage
- **Integration tests**: Critical paths
- **Current**: 47% coverage (target: 80%)

---

## Code Quality

### Linting and Formatting

```bash
# Format code with ruff
ruff format .

# Lint code
ruff check .

# Type checking with mypy
mypy src/

# Run all checks
./scripts/lint.sh
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## Database Management

### Migrations with Alembic

```bash
# Create new migration
alembic revision --autogenerate -m "Add new column to cases table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Database Inspection

```bash
# SQLite (development)
sqlite3 data/faultmaven.db
.tables
.schema cases

# Or use GUI tool
sqlitebrowser data/faultmaven.db
```

---

## Debugging

### VSCode Launch Configuration

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FaultMaven FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "faultmaven.app:app",
        "--reload",
        "--port", "8000"
      ],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src"
      }
    },
    {
      "name": "Pytest Current File",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}", "-v"]
    }
  ]
}
```

### Logging

```python
# Add logging to your module
import logging
logger = logging.getLogger(__name__)

# Use in code
logger.info("Processing case %s", case_id)
logger.error("Failed to process: %s", error)

# Configure log level in .env
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

### API Testing

```bash
# HTTPie examples
http POST localhost:8000/auth/register email=test@example.com password=test123

http POST localhost:8000/sessions Authorization:"Bearer <token>"

http POST localhost:8000/cases Authorization:"Bearer <token>" \
  user_message="My app is crashing"

# Curl examples
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'
```

---

## Working with Investigation Framework

### Understanding the Framework

The investigation framework consists of 5 engines in `src/faultmaven/modules/case/engines/`:

1. **MilestoneEngine** - Orchestrator
2. **MemoryManager** - Hierarchical memory (✅ integrated)
3. **WorkingConclusionGenerator** - Progress tracking (✅ integrated)
4. **PhaseOrchestrator** - Phase progression (✅ integrated)
5. **OODAEngine** - Adaptive intensity (✅ integrated)
6. **HypothesisManager** - Hypothesis lifecycle (⏳ pending)

**Status**: See [INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md](INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md)

### Testing Framework Engines

```bash
# Run investigation framework tests
pytest tests/unit/modules/case/test_milestone_engine.py -v
pytest tests/unit/modules/case/test_ooda_engine_business_logic.py -v
pytest tests/unit/modules/case/test_hypothesis_manager_business_logic.py -v

# All framework tests
pytest tests/unit/modules/case/ -k engine -v
```

---

## LLM Provider Development

### Adding a New LLM Provider

See FaultMaven-Mono reference:

1. Create provider class in `src/faultmaven/providers/llm/`
2. Implement `LLMProvider` protocol
3. Register in provider factory
4. Add configuration to `.env.example`
5. Update documentation

**Example**: `src/faultmaven/providers/llm/groq.py`

```python
from faultmaven.providers.interfaces import LLMProvider

class GroqProvider(LLMProvider):
    async def chat(self, messages, **kwargs):
        # Implementation
        pass
```

---

## Common Tasks

### Reset Database

```bash
rm data/faultmaven.db
alembic upgrade head
```

### Clear Redis

```bash
redis-cli FLUSHDB
```

### Reset ChromaDB

```bash
docker-compose down chromadb
docker volume rm faultmaven_chromadb-data
docker-compose up -d chromadb
```

### Generate API Documentation

```bash
# Generate OpenAPI spec
python scripts/generate_openapi_spec.py

# View at
open http://localhost:8000/docs
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Import Errors

```bash
# Ensure PYTHONPATH includes src/
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"

# Or install in editable mode
pip install -e .
```

### Database Lock Errors

```bash
# SQLite is locked (multiple connections)
# Solution: Use PostgreSQL for multi-process development

# Update .env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/faultmaven
```

### Redis Connection Failed

```bash
# Check Redis is running
docker ps | grep redis

# Check connection
redis-cli ping
```

---

## Performance Profiling

### Profile API Endpoints

```python
# Add profiling middleware
from fastapi_profiler import PyInstrumentProfilerMiddleware

app.add_middleware(PyInstrumentProfilerMiddleware)

# Access profiler at /__profiler__
```

### Memory Profiling

```bash
# Install memory profiler
pip install memory-profiler

# Profile function
python -m memory_profiler script.py
```

---

## Contributing Guidelines

### Branch Naming

```bash
# Feature branches
git checkout -b feature/add-hypothesis-validation

# Bug fixes
git checkout -b fix/session-timeout-bug

# Documentation
git checkout -b docs/update-api-guide
```

### Commit Messages

Follow conventional commits:

```bash
feat: Add hypothesis confidence tracking
fix: Resolve session cleanup race condition
docs: Update development guide for monolith
test: Add integration tests for case service
refactor: Extract memory manager to separate class
```

### Pull Request Process

1. Create feature branch from `main`
2. Make changes and add tests
3. Ensure all tests pass: `pytest`
4. Run linters: `ruff check .`
5. Update documentation if needed
6. Create PR with descriptive title and summary
7. Wait for CI checks to pass
8. Request review from maintainers

---

## IDE Setup

### VSCode Extensions

Recommended:
- Python (Microsoft)
- Pylance
- Ruff
- SQLite Viewer
- REST Client
- Docker

### PyCharm Configuration

1. Set interpreter to `.venv/bin/python`
2. Mark `src` as Sources Root
3. Enable pytest as test runner
4. Configure run configuration for `uvicorn`

---

## Additional Resources

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture
- **[API Documentation](api/)** - OpenAPI specs
- **[TESTING_STRATEGY.md](TESTING_STRATEGY.md)** - Testing approach
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues

---

**Architecture**: Modular Monolith (Single Repository)
**Main Application**: `src/faultmaven/app.py`
**Default Port**: 8000
**Database**: SQLite (dev), PostgreSQL (production)

For questions, see [FAQ.md](FAQ.md) or open an issue on GitHub.
