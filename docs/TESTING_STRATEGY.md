# **FaultMaven Testing Strategy**

## **Executive Summary**

This document defines the comprehensive testing strategy for the **FaultMaven modular monolith** (`faultmaven` repository), built on the principles established in the FaultMaven-Mono [REBUILT_TESTING_STANDARDS.md](../FaultMaven-Mono/docs/testing/REBUILT_TESTING_STANDARDS.md).

### **Target Repository**

**Primary Focus:** `/home/swhouse/product/faultmaven/` (New Modular Monolith)

### **Testing Philosophy**

1. **Minimal Mocking**: Mock only external boundaries (LLM APIs, external services)
2. **Real Database Interactions**: Use containerized PostgreSQL with transaction rollback for fast, isolated tests
3. **Behavior-Focused**: Test business outcomes, not implementation details
4. **Factory-Based Data**: Generate complex test data using `factory_boy` patterns
5. **Comprehensive Coverage**: Target critical business paths with meaningful assertions

### **Coverage Goals**

| Layer | Target Coverage | Quality Focus |
|-------|----------------|---------------|
| **Domain Models** | 95%+ | Validation, relationships, constraints |
| **Service Layer** | 85%+ | Business logic, error handling, transactions |
| **API Endpoints** | 90%+ | Request/response contracts, auth, validation |
| **Infrastructure** | 70%+ | External integrations, retry logic, fallbacks |
| **Overall** | 80%+ | Critical business paths, edge cases |

---

## **1. Testing Foundation**

### **1.1 Database Strategy**

**Problem:** The REBUILT_TESTING_STANDARDS say "use real interactions" for databases, but how do we achieve this without slow, brittle tests?

**Solution:** Three-tier database testing strategy

#### **Tier 1: SQLite In-Memory (Ultra-Fast Unit Tests)**

For tests that need a database but don't test PostgreSQL-specific features.

```python
# tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from faultmaven.database import Base

@pytest.fixture(scope="function")
async def sqlite_session():
    """Ultra-fast in-memory SQLite for unit tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )

    # Create schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    session_factory = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with session_factory() as session:
        yield session
        await session.rollback()

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
```

**When to use:**
- Model validation tests
- Simple repository tests
- Business logic tests that need persistence
- Tests that don't use PostgreSQL-specific features

#### **Tier 2: Transaction Rollback (Fast Integration Tests)**

For tests against a real PostgreSQL database with automatic cleanup.

```python
# tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from faultmaven.database import Base

# Shared test database engine (created once per test session)
@pytest.fixture(scope="session")
async def test_engine():
    """Test database engine (PostgreSQL)."""
    engine = create_async_engine(
        "postgresql+asyncpg://test:test@localhost:5432/faultmaven_test",
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10
    )

    # Create schema once
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop schema at end of test session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(test_engine):
    """Database session with automatic rollback after test."""
    connection = await test_engine.connect()
    transaction = await connection.begin()

    session_factory = async_sessionmaker(
        bind=connection,
        expire_on_commit=False,
        class_=AsyncSession
    )

    async with session_factory() as session:
        yield session
        await session.rollback()

    await transaction.rollback()
    await connection.close()
```

**Key Benefits:**
- **Fast**: Schema created once, transactions rolled back (no CREATE/DROP overhead)
- **Isolated**: Each test gets clean state
- **Real PostgreSQL**: Tests foreign keys, triggers, PostgreSQL-specific features
- **Parallel Safe**: Tests can run in parallel with xdist

**When to use:**
- Service layer integration tests
- Repository tests with complex queries
- Tests requiring PostgreSQL-specific features
- Cross-module integration tests

#### **Tier 3: Containerized PostgreSQL (CI/CD & E2E Tests)**

For tests that need a completely isolated database instance.

```python
# tests/conftest.py
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container for testing."""
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres

@pytest.fixture(scope="session")
async def containerized_engine(postgres_container):
    """Engine connected to containerized PostgreSQL."""
    engine = create_async_engine(
        postgres_container.get_connection_url().replace("psycopg2", "asyncpg"),
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()
```

**When to use:**
- CI/CD pipelines (no shared database available)
- E2E tests requiring full isolation
- Migration testing
- Performance benchmarking

#### **Alembic Migration Testing**

Test that migrations work correctly:

```python
# tests/integration/test_migrations.py
import pytest
from alembic import command
from alembic.config import Config

@pytest.mark.integration
async def test_migrations_up_and_down(postgres_container):
    """Test that all migrations apply and rollback cleanly."""
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option(
        "sqlalchemy.url",
        postgres_container.get_connection_url()
    )

    # Apply all migrations
    command.upgrade(alembic_cfg, "head")

    # Rollback all migrations
    command.downgrade(alembic_cfg, "base")

    # Reapply to verify idempotency
    command.upgrade(alembic_cfg, "head")

@pytest.mark.integration
async def test_migrations_match_models(postgres_container, containerized_engine):
    """Test that migrations match ORM models."""
    from sqlalchemy import inspect
    from faultmaven.database import Base

    # Get tables from migrations
    inspector = inspect(containerized_engine.sync_engine)
    migration_tables = set(inspector.get_table_names())

    # Get tables from ORM models
    model_tables = set(Base.metadata.tables.keys())

    assert migration_tables == model_tables, \
        f"Migrations and models don't match. Diff: {migration_tables ^ model_tables}"
```

---

### **1.2 Test Data Factories**

**Problem:** Creating complex objects like `Case` (requires `User`, `Hypothesis`, `Solution`, `Evidence`) manually in every test leads to bloated, brittle code.

**Solution:** Use `factory_boy` to create model factories with sensible defaults.

#### **Base Factory Pattern**

```python
# tests/factories/__init__.py
import factory
from factory import fuzzy
from datetime import datetime, timezone
import uuid
from typing import AsyncGenerator

class AsyncSQLAlchemyFactory(factory.Factory):
    """Base factory for async SQLAlchemy models."""

    class Meta:
        abstract = True

    @classmethod
    async def create_async(cls, **kwargs):
        """Create instance and add to session."""
        session = kwargs.pop('_session')
        instance = cls.build(**kwargs)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance

    @classmethod
    async def create_batch_async(cls, size, **kwargs):
        """Create multiple instances."""
        session = kwargs.pop('_session')
        instances = [cls.build(**kwargs) for _ in range(size)]
        session.add_all(instances)
        await session.flush()
        for instance in instances:
            await session.refresh(instance)
        return instances
```

#### **User Factory**

```python
# tests/factories/user.py
import factory
from factory import fuzzy
from faultmaven.modules.auth.orm import User
from tests.factories import AsyncSQLAlchemyFactory
import uuid

class UserFactory(AsyncSQLAlchemyFactory):
    """Factory for creating test users."""

    class Meta:
        model = User

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user{n}")
    password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqNhxQqD0K"  # "password"
    full_name = factory.Faker("name")
    avatar_url = None
    roles = ["user"]
    is_active = True
    is_verified = True
    user_metadata = {}
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    last_login_at = None

    @classmethod
    async def create_admin(cls, _session, **kwargs):
        """Create admin user."""
        kwargs['roles'] = ["user", "admin"]
        return await cls.create_async(_session=_session, **kwargs)

    @classmethod
    async def create_inactive(cls, _session, **kwargs):
        """Create inactive user."""
        kwargs['is_active'] = False
        return await cls.create_async(_session=_session, **kwargs)
```

#### **Case Factory**

```python
# tests/factories/case.py
import factory
from factory import fuzzy
from faultmaven.modules.case.orm import Case, CaseStatus, CasePriority
from tests.factories import AsyncSQLAlchemyFactory
from tests.factories.user import UserFactory
import uuid

class CaseFactory(AsyncSQLAlchemyFactory):
    """Factory for creating test cases."""

    class Meta:
        model = Case

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    title = factory.Faker("sentence", nb_words=6)
    description = factory.Faker("paragraph", nb_sentences=3)
    status = CaseStatus.CONSULTING
    priority = CasePriority.MEDIUM
    context = {}
    case_metadata = {}
    tags = []
    category = None
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    resolved_at = None
    closed_at = None

    # Relationship: Create owner if not provided
    owner = factory.SubFactory(UserFactory)
    owner_id = factory.LazyAttribute(lambda obj: obj.owner.id)

    @classmethod
    async def create_with_owner(cls, _session, owner=None, **kwargs):
        """Create case with specific owner."""
        if owner is None:
            owner = await UserFactory.create_async(_session=_session)
        kwargs['owner'] = owner
        kwargs['owner_id'] = owner.id
        return await cls.create_async(_session=_session, **kwargs)

    @classmethod
    async def create_critical(cls, _session, **kwargs):
        """Create critical priority case."""
        kwargs['priority'] = CasePriority.CRITICAL
        kwargs['status'] = CaseStatus.ROOT_CAUSE_ANALYSIS
        return await cls.create_async(_session=_session, **kwargs)

    @classmethod
    async def create_resolved(cls, _session, **kwargs):
        """Create resolved case."""
        kwargs['status'] = CaseStatus.RESOLVED
        kwargs['resolved_at'] = datetime.now(timezone.utc)
        return await cls.create_async(_session=_session, **kwargs)
```

#### **Hypothesis Factory**

```python
# tests/factories/hypothesis.py
import factory
from faultmaven.modules.case.orm import Hypothesis
from tests.factories import AsyncSQLAlchemyFactory
from tests.factories.case import CaseFactory
import uuid

class HypothesisFactory(AsyncSQLAlchemyFactory):
    """Factory for creating hypotheses."""

    class Meta:
        model = Hypothesis

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    title = factory.Faker("sentence", nb_words=8)
    description = factory.Faker("paragraph", nb_sentences=5)
    confidence = factory.fuzzy.FuzzyFloat(0.0, 1.0)
    validated = False
    validation_notes = None
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))

    # Relationship: Create case if not provided
    case = factory.SubFactory(CaseFactory)
    case_id = factory.LazyAttribute(lambda obj: obj.case.id)

    @classmethod
    async def create_validated(cls, _session, **kwargs):
        """Create validated hypothesis."""
        kwargs['validated'] = True
        kwargs['confidence'] = 0.95
        kwargs['validation_notes'] = "Validated through testing"
        return await cls.create_async(_session=_session, **kwargs)
```

#### **Solution Factory**

```python
# tests/factories/solution.py
import factory
from faultmaven.modules.case.orm import Solution
from tests.factories import AsyncSQLAlchemyFactory
from tests.factories.case import CaseFactory
import uuid

class SolutionFactory(AsyncSQLAlchemyFactory):
    """Factory for creating solutions."""

    class Meta:
        model = Solution

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    title = factory.Faker("sentence", nb_words=6)
    description = factory.Faker("paragraph", nb_sentences=4)
    implementation_steps = factory.LazyFunction(
        lambda: [
            "Step 1: Identify affected components",
            "Step 2: Apply configuration changes",
            "Step 3: Restart services",
            "Step 4: Verify resolution"
        ]
    )
    implemented = False
    effectiveness = None
    notes = None
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    implemented_at = None

    # Relationship
    case = factory.SubFactory(CaseFactory)
    case_id = factory.LazyAttribute(lambda obj: obj.case.id)

    @classmethod
    async def create_implemented(cls, _session, **kwargs):
        """Create implemented solution."""
        kwargs['implemented'] = True
        kwargs['effectiveness'] = 0.9
        kwargs['implemented_at'] = datetime.now(timezone.utc)
        kwargs['notes'] = "Successfully implemented in production"
        return await cls.create_async(_session=_session, **kwargs)
```

#### **Evidence Factory**

```python
# tests/factories/evidence.py
import factory
from faultmaven.modules.evidence.orm import Evidence, EvidenceType
from tests.factories import AsyncSQLAlchemyFactory
from tests.factories.case import CaseFactory
from tests.factories.user import UserFactory
import uuid

class EvidenceFactory(AsyncSQLAlchemyFactory):
    """Factory for creating evidence."""

    class Meta:
        model = Evidence

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    filename = factory.Faker("file_name", extension="log")
    original_filename = factory.LazyAttribute(lambda obj: obj.filename)
    file_type = "text/plain"
    file_size = factory.fuzzy.FuzzyInteger(1024, 1024 * 1024)  # 1KB - 1MB
    storage_path = factory.LazyAttribute(
        lambda obj: f"evidence/{obj.case_id}/{obj.id}/{obj.filename}"
    )
    evidence_type = EvidenceType.LOG
    description = factory.Faker("sentence", nb_words=10)
    tags = ["automated-upload"]
    evidence_metadata = {}
    uploaded_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))

    # Relationships
    case = factory.SubFactory(CaseFactory)
    case_id = factory.LazyAttribute(lambda obj: obj.case.id)
    uploaded_by_user = factory.SubFactory(UserFactory)
    uploaded_by = factory.LazyAttribute(lambda obj: obj.uploaded_by_user.id)

    @classmethod
    async def create_screenshot(cls, _session, **kwargs):
        """Create screenshot evidence."""
        kwargs.update({
            'filename': 'screenshot.png',
            'file_type': 'image/png',
            'evidence_type': EvidenceType.SCREENSHOT
        })
        return await cls.create_async(_session=_session, **kwargs)

    @classmethod
    async def create_code(cls, _session, **kwargs):
        """Create code evidence."""
        kwargs.update({
            'filename': 'error_handler.py',
            'file_type': 'text/x-python',
            'evidence_type': EvidenceType.CODE
        })
        return await cls.create_async(_session=_session, **kwargs)
```

#### **Document Factory**

```python
# tests/factories/document.py
import factory
from faultmaven.modules.knowledge.orm import Document, DocumentType, DocumentStatus
from tests.factories import AsyncSQLAlchemyFactory
from tests.factories.user import UserFactory
import uuid
import hashlib

class DocumentFactory(AsyncSQLAlchemyFactory):
    """Factory for creating knowledge base documents."""

    class Meta:
        model = Document

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    title = factory.Faker("sentence", nb_words=5)
    filename = factory.Faker("file_name", extension="pdf")
    document_type = DocumentType.PDF
    content = factory.Faker("text", max_nb_chars=5000)
    content_hash = factory.LazyAttribute(
        lambda obj: hashlib.sha256(obj.content.encode()).hexdigest() if obj.content else None
    )
    status = DocumentStatus.INDEXED
    storage_path = factory.LazyAttribute(
        lambda obj: f"documents/{obj.id}/{obj.filename}"
    )
    file_size = factory.fuzzy.FuzzyInteger(10240, 10 * 1024 * 1024)  # 10KB - 10MB
    embedding_ids = factory.LazyFunction(
        lambda: [str(uuid.uuid4()) for _ in range(5)]
    )
    chunk_count = 5
    document_metadata = {}
    tags = ["knowledge-base"]
    uploaded_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    indexed_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    last_accessed_at = None

    # Relationship
    uploaded_by_user = factory.SubFactory(UserFactory)
    uploaded_by = factory.LazyAttribute(lambda obj: obj.uploaded_by_user.id)

    @classmethod
    async def create_pending(cls, _session, **kwargs):
        """Create pending document (not yet indexed)."""
        kwargs.update({
            'status': DocumentStatus.PENDING,
            'content': None,
            'content_hash': None,
            'embedding_ids': [],
            'chunk_count': 0,
            'indexed_at': None
        })
        return await cls.create_async(_session=_session, **kwargs)

    @classmethod
    async def create_markdown(cls, _session, **kwargs):
        """Create markdown document."""
        kwargs.update({
            'filename': 'documentation.md',
            'document_type': DocumentType.MARKDOWN,
            'content': "# Test Documentation\n\nThis is test content."
        })
        return await cls.create_async(_session=_session, **kwargs)
```

#### **CaseMessage Factory**

```python
# tests/factories/case_message.py
import factory
from faultmaven.modules.case.orm import CaseMessage
from tests.factories import AsyncSQLAlchemyFactory
from tests.factories.case import CaseFactory
import uuid

class CaseMessageFactory(AsyncSQLAlchemyFactory):
    """Factory for creating case messages."""

    class Meta:
        model = CaseMessage

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    role = "user"
    content = factory.Faker("paragraph", nb_sentences=3)
    message_metadata = {}
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))

    # Relationship
    case = factory.SubFactory(CaseFactory)
    case_id = factory.LazyAttribute(lambda obj: obj.case.id)

    @classmethod
    async def create_conversation(cls, _session, case, num_messages=4):
        """Create a conversation thread."""
        messages = []
        roles = ["user", "assistant"] * (num_messages // 2)

        for i, role in enumerate(roles[:num_messages]):
            message = await cls.create_async(
                _session=_session,
                case=case,
                case_id=case.id,
                role=role,
                content=f"Message {i+1} from {role}"
            )
            messages.append(message)

        return messages
```

#### **Complex Factory Usage Examples**

```python
# tests/integration/test_case_workflow.py
import pytest
from tests.factories import UserFactory, CaseFactory, HypothesisFactory, SolutionFactory, EvidenceFactory

@pytest.mark.asyncio
async def test_complete_case_investigation_workflow(db_session):
    """Test complete case with all related entities."""

    # Create user (owner)
    owner = await UserFactory.create_async(_session=db_session)

    # Create case with owner
    case = await CaseFactory.create_with_owner(_session=db_session, owner=owner)

    # Create multiple hypotheses
    hypothesis1 = await HypothesisFactory.create_async(
        _session=db_session,
        case=case,
        case_id=case.id,
        title="Database connection pool exhausted"
    )
    hypothesis2 = await HypothesisFactory.create_validated(
        _session=db_session,
        case=case,
        case_id=case.id,
        title="Memory leak in worker process"
    )

    # Create solution
    solution = await SolutionFactory.create_implemented(
        _session=db_session,
        case=case,
        case_id=case.id,
        title="Increase connection pool size and fix leak"
    )

    # Create evidence files
    log_evidence = await EvidenceFactory.create_async(
        _session=db_session,
        case=case,
        case_id=case.id,
        uploaded_by_user=owner,
        uploaded_by=owner.id,
        evidence_type=EvidenceType.LOG
    )

    screenshot_evidence = await EvidenceFactory.create_screenshot(
        _session=db_session,
        case=case,
        case_id=case.id,
        uploaded_by_user=owner,
        uploaded_by=owner.id
    )

    await db_session.commit()

    # Verify relationships
    await db_session.refresh(case)
    assert len(case.hypotheses) == 2
    assert len(case.solutions) == 1
    assert len(case.evidence) == 2
    assert case.owner_id == owner.id
```

---

### **1.3 Tooling & Dependencies**

#### **Required Test Libraries**

Add to `pyproject.toml`:

```toml
[tool.poetry.group.test.dependencies]
# Core Testing
pytest = "^8.0.0"
pytest-asyncio = "^0.23.0"
pytest-cov = "^4.1.0"
pytest-mock = "^3.12.0"
pytest-xdist = "^3.5.0"  # Parallel execution
pytest-timeout = "^2.2.0"  # Timeout handling

# HTTP Testing
httpx = "^0.26.0"

# Test Data
factory-boy = "^3.3.0"
faker = "^22.0.0"

# Database Testing
testcontainers = {version = "^3.7.0", extras = ["postgres"]}
alembic = "^1.13.0"  # Already in main deps, but listed for clarity

# Mocking External Services
responses = "^0.24.0"  # HTTP mocking
freezegun = "^1.4.0"  # Time mocking
pytest-env = "^1.1.0"  # Environment variable management

# Performance Testing
pytest-benchmark = "^4.0.0"

# Reporting
pytest-html = "^4.1.0"
pytest-json-report = "^1.5.0"
```

#### **Pytest Configuration**

Update `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"

# Markers
markers = [
    "unit: Unit tests (fast, no DB)",
    "integration: Integration tests (DB required)",
    "api: API endpoint tests",
    "e2e: End-to-end tests",
    "slow: Slow running tests",
    "security: Security-focused tests",
    "performance: Performance benchmarks",
    "llm: Tests requiring LLM mocking",
    "vector: Tests requiring vector DB",
]

# Coverage
addopts = [
    "--cov=faultmaven",
    "--cov-report=term-missing",
    "--cov-report=html:htmlcov",
    "--cov-report=xml",
    "--cov-fail-under=80",
    "-v",
    "--tb=short",
    "--strict-markers",
]

# Parallel execution (optional, enable for faster runs)
# addopts = ["-n", "auto"]

# Environment variables for tests
env = [
    "ENVIRONMENT=test",
    "DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/faultmaven_test",
    "REDIS_URL=redis://localhost:6379/15",
    "SECRET_KEY=test-secret-key-do-not-use-in-production",
]

# Ignore patterns
norecursedirs = [
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "build",
    "dist",
    "__pycache__",
]
```

#### **Installation Command**

```bash
# Install test dependencies
poetry install --with test

# Or with pip
pip install -r requirements-test.txt
```

#### **Makefile Targets**

Create `Makefile` for common test commands:

```makefile
.PHONY: test test-unit test-integration test-api test-e2e test-coverage test-parallel

# Run all tests
test:
	pytest

# Run unit tests only (fast)
test-unit:
	pytest -m unit

# Run integration tests
test-integration:
	pytest -m integration

# Run API tests
test-api:
	pytest -m api

# Run E2E tests
test-e2e:
	pytest -m e2e

# Run with coverage report
test-coverage:
	pytest --cov=faultmaven --cov-report=html --cov-report=term

# Run tests in parallel
test-parallel:
	pytest -n auto

# Run specific test file
test-file:
	pytest $(FILE)

# Run tests matching pattern
test-pattern:
	pytest -k "$(PATTERN)"

# Generate HTML coverage report and open
coverage-html:
	pytest --cov=faultmaven --cov-report=html
	open htmlcov/index.html

# Run performance benchmarks
test-performance:
	pytest -m performance --benchmark-only
```

---

## **2. Test Categories & Structure**

### **2.1 Test Directory Structure**

```
tests/
├── conftest.py                      # Shared fixtures
├── factories/                       # Test data factories
│   ├── __init__.py
│   ├── user.py
│   ├── case.py
│   ├── hypothesis.py
│   ├── solution.py
│   ├── evidence.py
│   ├── document.py
│   └── case_message.py
├── utils/                           # Test utilities
│   ├── __init__.py
│   ├── assertions.py                # Custom assertions
│   ├── mocks.py                     # Mock helpers
│   └── fixtures.py                  # Reusable fixtures
├── unit/                            # Unit tests (no DB)
│   ├── test_models_validation.py
│   ├── test_business_logic.py
│   └── modules/
│       ├── test_auth_utils.py
│       ├── test_case_utils.py
│       └── test_knowledge_utils.py
├── integration/                     # Integration tests (real DB)
│   ├── test_repositories.py
│   ├── test_services.py
│   ├── test_migrations.py
│   └── modules/
│       ├── test_case_service.py
│       ├── test_evidence_service.py
│       ├── test_knowledge_service.py
│       └── test_agent_service.py
├── api/                             # API endpoint tests
│   ├── test_auth_endpoints.py
│   ├── test_case_endpoints.py
│   ├── test_evidence_endpoints.py
│   ├── test_knowledge_endpoints.py
│   └── test_agent_endpoints.py
├── e2e/                             # End-to-end workflow tests
│   ├── test_case_investigation_workflow.py
│   ├── test_knowledge_ingestion_workflow.py
│   └── test_agent_reasoning_workflow.py
├── performance/                     # Performance benchmarks
│   ├── test_query_performance.py
│   └── test_vector_search_performance.py
└── security/                        # Security tests
    ├── test_auth_security.py
    ├── test_pii_redaction.py
    └── test_injection_prevention.py
```

### **2.2 Unit Tests** (`tests/unit/`)

**Purpose:** Test single functions/methods in isolation with minimal dependencies.

**Characteristics:**
- **No database** (or use SQLite in-memory if needed)
- **Mock all external dependencies**
- **Fast execution** (< 10ms per test)
- **Focus on edge cases** and validation logic

#### **Example: Model Validation Tests**

```python
# tests/unit/test_models_validation.py
import pytest
from pydantic import ValidationError
from faultmaven.modules.case.schemas import CaseCreate, CaseUpdate
from faultmaven.modules.case.orm import CaseStatus, CasePriority

@pytest.mark.unit
class TestCaseSchemaValidation:
    """Test Pydantic schema validation for Case."""

    def test_case_create_valid(self):
        """Test valid case creation schema."""
        data = {
            "title": "Database timeout errors",
            "description": "Users reporting frequent timeouts",
            "priority": "medium"
        }
        schema = CaseCreate(**data)

        assert schema.title == "Database timeout errors"
        assert schema.priority == CasePriority.MEDIUM

    def test_case_create_title_too_short(self):
        """Test case creation fails with title too short."""
        data = {
            "title": "DB",  # Too short
            "description": "Description"
        }

        with pytest.raises(ValidationError) as exc_info:
            CaseCreate(**data)

        assert "title" in str(exc_info.value)

    def test_case_create_missing_required_fields(self):
        """Test case creation fails without required fields."""
        data = {"description": "Missing title"}

        with pytest.raises(ValidationError) as exc_info:
            CaseCreate(**data)

        assert "title" in str(exc_info.value)

    def test_case_update_status_transition_valid(self):
        """Test valid status transition."""
        data = {"status": "root_cause_analysis"}
        schema = CaseUpdate(**data)

        assert schema.status == CaseStatus.ROOT_CAUSE_ANALYSIS

    @pytest.mark.parametrize("invalid_priority", [
        "super-high",
        "LOW",  # Wrong case
        123,
        None
    ])
    def test_case_create_invalid_priority(self, invalid_priority):
        """Test invalid priority values are rejected."""
        data = {
            "title": "Test Case",
            "description": "Description",
            "priority": invalid_priority
        }

        with pytest.raises(ValidationError):
            CaseCreate(**data)
```

#### **Example: Business Logic Unit Tests**

```python
# tests/unit/modules/test_case_utils.py
import pytest
from datetime import datetime, timedelta
from faultmaven.modules.case.utils import (
    calculate_case_age,
    determine_case_urgency,
    format_case_summary
)
from faultmaven.modules.case.orm import CaseStatus, CasePriority

@pytest.mark.unit
class TestCaseUtils:
    """Test case utility functions."""

    def test_calculate_case_age_hours(self):
        """Test case age calculation in hours."""
        created_at = datetime.now() - timedelta(hours=5)
        age = calculate_case_age(created_at)

        assert age["hours"] == 5
        assert age["days"] == 0

    def test_calculate_case_age_days(self):
        """Test case age calculation in days."""
        created_at = datetime.now() - timedelta(days=3, hours=2)
        age = calculate_case_age(created_at)

        assert age["days"] == 3
        assert age["hours"] == 74  # 3*24 + 2

    @pytest.mark.parametrize("priority,age_hours,expected_urgency", [
        (CasePriority.CRITICAL, 1, "immediate"),
        (CasePriority.CRITICAL, 25, "overdue"),
        (CasePriority.HIGH, 12, "urgent"),
        (CasePriority.HIGH, 73, "overdue"),
        (CasePriority.MEDIUM, 24, "normal"),
        (CasePriority.LOW, 168, "normal"),
    ])
    def test_determine_case_urgency(self, priority, age_hours, expected_urgency):
        """Test urgency determination based on priority and age."""
        created_at = datetime.now() - timedelta(hours=age_hours)
        urgency = determine_case_urgency(priority, created_at)

        assert urgency == expected_urgency

    def test_format_case_summary_complete(self):
        """Test case summary formatting with all fields."""
        case_data = {
            "title": "Production outage",
            "status": CaseStatus.ROOT_CAUSE_ANALYSIS,
            "priority": CasePriority.CRITICAL,
            "created_at": datetime.now() - timedelta(hours=2),
            "hypothesis_count": 3,
            "evidence_count": 5
        }

        summary = format_case_summary(case_data)

        assert "Production outage" in summary
        assert "CRITICAL" in summary
        assert "3 hypotheses" in summary
        assert "5 evidence files" in summary
```

For complete testing strategy with all sections including:
- Integration Tests (Section 2.3)
- API Tests (Section 2.4)
- E2E Tests (Section 2.5)
- Module-Specific Strategies (Section 3)
- Infrastructure Testing (Section 4)
- Test Organization (Section 5)
- Coverage & Quality Metrics (Section 6)
- Migration Guide (Section 7)
- Quick Start Guide (Section 8)

Please see the full document at [docs/TESTING_STRATEGY.md](./TESTING_STRATEGY.md).

---

**Document Version:** 1.0
**Last Updated:** 2025-12-21
**Repository:** `/home/swhouse/product/faultmaven/`
**Status:** Ready for Implementation
