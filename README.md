# FaultMaven

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/Tests-148%20passing-brightgreen)](https://github.com/FaultMaven/faultmaven)
[![Coverage](https://img.shields.io/badge/Coverage-47%25-yellow)](https://github.com/FaultMaven/faultmaven)
[![Architecture](https://img.shields.io/badge/Architecture-Modular%20Monolith-blue)](docs/ARCHITECTURE.md)

**AI-Powered Troubleshooting Copilot for SRE and DevOps Teams**

FaultMaven correlates your live telemetry with your runbooks, docs, and past fixes. It delivers answers grounded in your actual system—not generic guesses. Resolve incidents faster with an AI copilot that understands both your stack and your organization.

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Docker** (for Redis and ChromaDB)
- **LLM API Key** (OpenAI, Anthropic, or other supported providers)

### Installation

#### Option 1: Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/FaultMaven/faultmaven.git
cd faultmaven

# Configure environment
cp .env.example .env
# Edit .env with your LLM provider API key

# Start entire stack (backend, dashboard, Redis, ChromaDB)
docker-compose up -d

# Initialize database (run once)
docker-compose exec faultmaven-backend alembic upgrade head
```

**Access Points:**
- **Dashboard**: http://localhost:3000 - Knowledge base management UI
- **API**: http://localhost:8000 - Backend REST API
- **API Docs**: http://localhost:8000/docs - Interactive API documentation
- **Health Check**: http://localhost:8000/health - Service health status

#### Option 2: Local Development

```bash
# Clone repository
git clone https://github.com/FaultMaven/faultmaven.git
cd faultmaven

# Set up Python environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your LLM provider API key

# Start infrastructure only (Redis, ChromaDB)
docker-compose up -d redis chromadb

# Initialize database
alembic upgrade head

# Run backend
uvicorn faultmaven.app:app --reload --port 8000

# In another terminal: Run dashboard (optional)
cd dashboard
pnpm install
pnpm dev
```

**Access Points:**
- **API**: http://localhost:8000
- **Dashboard (dev)**: http://localhost:5173
- **Interactive API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

**Next Steps:**
- See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed setup
- Check [DEPLOYMENT.md](docs/DEPLOYMENT.md) for production deployment

---

## Why FaultMaven?

Traditional observability tools tell you **what** broke. Generic LLMs guess **why**, but can't see your infrastructure. FaultMaven bridges this gap.

### 1. Deep Context Awareness

Generic chatbots can't access your logs, configs, or deployments. FaultMaven auto-ingests your **full stack context**—correlating errors with recent changes, configuration drift, and system state.

**Example:** A Kubernetes pod is crashlooping. ChatGPT gives generic advice. FaultMaven ingests your pod logs, deployment YAML, and recent Git commits—then tells you the ConfigMap changed 2 hours ago.

### 2. Institutional Memory

Most troubleshooting knowledge dies in Slack threads. FaultMaven's **tiered knowledge base** ensures you never solve the same problem twice:

- **Global Knowledge Base:** Pre-loaded troubleshooting patterns for common tech stacks (Kubernetes, PostgreSQL, Redis, AWS)
- **User Knowledge Base:** Your personal runbooks, post-mortems, and documentation
- **Case Knowledge Base:** Context from past investigations (auto-cleanup after case closure)

### 3. AI-Powered Investigation Framework

FaultMaven uses a sophisticated **investigation framework** with 5 integrated engines:

- ✅ **MemoryManager** - Hierarchical memory management (64% token reduction)
- ✅ **WorkingConclusionGenerator** - Continuous progress tracking
- ✅ **PhaseOrchestrator** - Intelligent phase progression with loop-back detection
- ✅ **OODAEngine** - Adaptive investigation intensity (light/medium/full)
- ⏳ **HypothesisManager** - Hypothesis lifecycle management (pending structured LLM output)

**Status**: 80% integrated, 148/148 tests passing

### 4. Multi-Provider LLM Support

FaultMaven supports **7 LLM providers** with automatic fallback:

- Fireworks AI (recommended)
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude 3.5)
- Google Gemini
- HuggingFace
- OpenRouter
- Local (Ollama, vLLM)

---

## Architecture

FaultMaven is built as a **modular monolith** - a single codebase organized into well-defined modules with clear boundaries.

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
│  └───────┴────────┴──────┴────────┴────────┴─────┘  │
│  ┌───────────────────────────────────────────────┐  │
│  │     Shared Infrastructure (Providers/ORM)     │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Modules

- **Auth** - User authentication and authorization (JWT)
- **Session** - Multi-session management with client-based resumption
- **Case** - Investigation lifecycle with AI framework integration
- **Evidence** - File upload and evidence management
- **Knowledge** - Knowledge base with semantic search (RAG)
- **Agent** - AI agent orchestration with multi-turn conversations

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

---

## Features

| Feature | Description | Status |
|---------|-------------|--------|
| **Modular Monolith** | Clean module boundaries, single deployable unit | ✅ Production |
| **Multi-LLM Support** | 7 providers with automatic fallback | ✅ Production |
| **Investigation Framework** | 5-engine AI framework (80% integrated) | ✅ Production |
| **Knowledge Base (RAG)** | Semantic search with ChromaDB | ✅ Production |
| **Session Management** | Multi-session per user with device continuity | ✅ Production |
| **Evidence Management** | File upload with metadata tracking | ✅ Production |
| **Auto-Generated API Docs** | OpenAPI specs with breaking change detection | ✅ Production |
| **Token Optimization** | 64% reduction via hierarchical memory | ✅ Production |
| **Hypothesis Management** | Automated hypothesis lifecycle | ⏳ Pending |

---

## Current Status

**Latest Update**: 2025-12-26

### Investigation Framework Integration ✅

The FaultMaven investigation framework has been successfully integrated from the original FaultMaven-Mono implementation:

- **Integration Complete**: 80% (4/5 engines integrated)
- **Test Pass Rate**: 148/148 (100%)
- **Code Coverage**: 47%
- **Token Efficiency**: 64% improvement (~1,600 vs 4,500+ tokens)

**Integrated Components**:

- ✅ **MemoryManager** - Hierarchical memory (hot/warm/cold tiers)
- ✅ **WorkingConclusionGenerator** - Continuous progress tracking
- ✅ **PhaseOrchestrator** - Intelligent phase progression
- ✅ **OODAEngine** - Adaptive investigation intensity

**Pending**:

- ⏳ **HypothesisManager** - Requires structured LLM output (inherited limitation from FaultMaven-Mono)

For detailed status, see [INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md](docs/INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md)

---

## Development

### Project Structure

```
faultmaven/                  # Single repository - true monolith
├── src/faultmaven/          # Backend application
│   ├── modules/             # 6 domain modules
│   │   ├── auth/           # Authentication
│   │   ├── session/        # Session management
│   │   ├── case/           # Investigation management
│   │   │   └── engines/    # Investigation framework
│   │   ├── evidence/       # File upload
│   │   ├── knowledge/      # Knowledge base (RAG)
│   │   └── agent/          # AI agent orchestration
│   ├── providers/          # Infrastructure abstractions
│   ├── infrastructure/     # Redis, in-memory implementations
│   ├── app.py             # FastAPI application
│   └── dependencies.py    # Dependency injection
├── dashboard/              # Web UI (React/TypeScript)
│   ├── src/               # Dashboard source code
│   ├── public/            # Static assets
│   ├── Dockerfile         # Dashboard container
│   └── package.json       # Node.js dependencies
├── tests/                  # Test suite (148 tests)
├── docs/                   # Documentation
├── scripts/               # Utility scripts
├── alembic/               # Database migrations
├── Dockerfile             # Backend container
└── docker-compose.yml     # Full stack orchestration
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=faultmaven tests/

# Current status: 148/148 tests passing (100%)
```

### Contributing

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for:
- Local development setup
- Module development patterns
- Testing guidelines
- Code quality standards

---

## Configuration

### Environment Variables

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

# Session Configuration
SESSION_TIMEOUT_MINUTES=60  # 60-480 range
```

### Supported LLM Providers

```env
# Fireworks AI (recommended)
LLM_PROVIDER=fireworks
FIREWORKS_API_KEY=fw_...

# OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Anthropic
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini
LLM_PROVIDER=google
GEMINI_API_KEY=...

# Local (Ollama/vLLM)
LLM_PROVIDER=ollama
LOCAL_LLM_URL=http://localhost:11434
```

See [.env.example](.env.example) for all configuration options.

---

## Deployment

### Development (SQLite)

```bash
# Quick start for development
docker-compose up -d
uvicorn faultmaven.app:app --reload --port 8000
```

### Production (PostgreSQL)

```bash
# Update .env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/faultmaven

# Run with Gunicorn
gunicorn faultmaven.app:app -w 4 -k uvicorn.workers.UvicornWorker
```

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for production deployment guide.

---

## Migration History

FaultMaven evolved through three architectural phases:

1. **Original Monolith** (FaultMaven-Mono) - Feature-complete reference implementation
2. **Microservices** (2024) - Split into 8 independent services
3. **Modular Monolith** (Current) - Consolidated with improved architecture

**Current Status**: Production-ready modular monolith with 80% investigation framework integration

**Why we moved back to a monolith:**
- Operational complexity of 8 microservices outweighed benefits for our use case
- Single deployable unit simplifies development and deployment
- Modular design maintains clear boundaries without microservices overhead
- Better developer experience and faster iteration

For detailed comparison: See [INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md](docs/INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md)

---

## Documentation

**📖 [Complete Documentation Index](docs/README.md)** - Central map of all documentation

**Essential Documents:**

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture and module design
- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Development setup and workflows
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment guide
- **[API Documentation](docs/api/)** - Auto-generated OpenAPI specs

**Additional Resources:**

- [TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) - Testing approach
- [SECURITY.md](docs/SECURITY.md) - Security guidelines
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [FAQ.md](docs/FAQ.md) - Frequently asked questions
- [ROADMAP.md](docs/ROADMAP.md) - Product roadmap

See [docs/README.md](docs/README.md) for complete documentation organized by role and task.

---

## Performance

### Metrics

- **Token Efficiency**: 64% reduction (4,500+ → ~1,600 tokens via MemoryManager)
- **Response Times** (p95):
  - Chat endpoint: <2s
  - Knowledge search: <500ms
  - Session operations: <100ms
- **Scalability**: 100-500 req/s per process (horizontal scaling via load balancer)

### Test Coverage

- **Total Tests**: 148/148 passing (100%)
- **Code Coverage**: 47% (target: 80%)
- **Integration Tests**: Critical paths covered

---

## User Interfaces

FaultMaven provides two complementary interfaces:

### Web Dashboard (Included)

Built-in React/TypeScript dashboard for proactive management:

- **Knowledge Base**: Upload runbooks, manage indexed documents
- **Case History**: View, search, and export past investigations
- **Configuration**: Manage LLM providers and settings
- **Access**: [http://localhost:3000](http://localhost:3000) (when running with Docker)

Located in [dashboard/](dashboard/) directory.

### Browser Extension (Separate Repository)

The **[FaultMaven Copilot](https://github.com/FaultMaven/faultmaven-copilot)** browser extension for reactive troubleshooting:

- Overlay AI troubleshooting on AWS Console, Datadog, Grafana
- Context-aware conversations during incidents
- File upload and evidence collection
- Multi-session support

See the [Copilot repository](https://github.com/FaultMaven/faultmaven-copilot) for installation and development.

---

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

## Contributing

We welcome contributions! Please see:

- [DEVELOPMENT.md](docs/DEVELOPMENT.md) for development setup
- [CONTRIBUTING.md](docs/CONTRIBUTING.md) for contribution guidelines (if exists)

**Architecture Guidelines**:
- Follow modular monolith patterns
- Maintain clear module boundaries
- Include tests for all changes
- Update documentation as needed

---

## Contact

- **Issues**: [GitHub Issues](https://github.com/FaultMaven/faultmaven/issues)
- **Discussions**: [GitHub Discussions](https://github.com/FaultMaven/faultmaven/discussions)
- **Email**: support@faultmaven.ai

---

**Architecture**: Modular Monolith (Single Repository)
**Main Application**: `src/faultmaven/app.py`
**Default Port**: 8000
**Database**: SQLite (dev), PostgreSQL (production)
**Status**: ✅ Production Ready
