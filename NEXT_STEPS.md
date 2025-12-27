# Next Steps

**Purpose**: Single source of truth for what to work on next.
**Last Updated**: 2025-12-27
**For**: New developers, agents, and contributors

---

## 🎯 Where to Start

**New to FaultMaven?** Start here:

1. **Setup**: [DEVELOPMENT.md](docs/DEVELOPMENT.md) - Get the project running locally
2. **Understand**: [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Learn the system structure
3. **Gaps**: [TECHNICAL_DEBT.md](docs/TECHNICAL_DEBT.md) - See what needs to be built
4. **Pick a task**: See "Immediate Next Steps" below

---

## 🚀 Immediate Next Steps (Priority Order)

### 1. Structured LLM Output Support (2 weeks) 🔴 CRITICAL

**Why**: Unblocks HypothesisManager and Agent Tools framework

**What to do**:
1. Read current LLMProvider abstraction: `src/faultmaven/infrastructure/providers/llm/`
2. Refactor to support:
   - JSON mode for structured output
   - Function calling for agent tools
3. Update all provider implementations (OpenAI, Anthropic, etc.)

**Detailed spec**: [TECHNICAL_DEBT.md#1](docs/TECHNICAL_DEBT.md#1-structured-llm-output-support)

**Estimated effort**: 2 weeks
**Blocks**: HypothesisManager integration, Agent Tools (4 weeks of work blocked)

---

### 2. Data Processing Pipeline (3 weeks) 🔴 CRITICAL

**Why**: Evidence files are uploaded but not processed - core functionality gap

**What to do**:
1. Implement data type detection (8 types)
2. Build 11 extractors:
   - Week 1: LogExtractor, JSONConfigExtractor, YAMLConfigExtractor, GenericTextExtractor
   - Week 2: TOMLConfigExtractor, ENVConfigExtractor, TraceExtractor, MetricExtractor
   - Week 3: CodeExtractor, MarkdownExtractor, ImageExtractor
3. Integrate with knowledge base for RAG retrieval

**Reference implementation**: FaultMaven-Mono `faultmaven/data_processing/`

**Detailed spec**: [TECHNICAL_DEBT.md#2](docs/TECHNICAL_DEBT.md#2-data-processing-pipeline)

**Estimated effort**: 3 weeks
**Impact**: Enables semantic search across uploaded logs/configs

---

### 3. Agent Tools Framework (4 weeks) 🔴 CRITICAL

**Why**: Agent can only chat, cannot execute troubleshooting actions

**What to do**:
1. Week 1: Build tool execution framework + sandboxing
2. Week 2: Implement CommandExecutor, ProcessInspector, FileReader, FileSearcher
3. Week 3: Implement NetworkAnalyzer, HTTPClient, DatabaseQuery
4. Week 4: Permission system + audit logging

**Depends on**: Structured LLM output (#1)

**Detailed spec**: [TECHNICAL_DEBT.md#3](docs/TECHNICAL_DEBT.md#3-agent-tools-framework)

**Estimated effort**: 4 weeks
**Impact**: Enables autonomous troubleshooting

---

### 4. HypothesisManager Integration (1 week) 🔴 CRITICAL

**Why**: Completes investigation framework from 80% → 100%

**What to do**:
1. Integrate structured LLM output with HypothesisManager
2. Activate hypothesis extraction from LLM responses
3. Add hypothesis lifecycle management to case workflow

**Code location**: `src/faultmaven/modules/case/engines/hypothesis_manager.py` (exists but not integrated)

**Depends on**: Structured LLM output (#1)

**Detailed spec**: [TECHNICAL_DEBT.md#4](docs/TECHNICAL_DEBT.md#4-hypothesismanager-integration)

**Estimated effort**: 1 week
**Impact**: Investigation framework 100% complete

---

## 📋 After Critical Gaps (High Priority)

### 5. Report Generation (1 week) 🟡 HIGH

- PDF and Markdown export for investigation results
- See [TECHNICAL_DEBT.md#5](docs/TECHNICAL_DEBT.md#5-report-generation)

### 6. Case Search & Filter (1 week) 🟡 HIGH

- Search and filter historical cases
- See [TECHNICAL_DEBT.md#6](docs/TECHNICAL_DEBT.md#6-case-search--filter)

### 7. Session Advanced Features (3 days) 🟡 MEDIUM

- Session search, statistics, heartbeat testing
- See [TECHNICAL_DEBT.md#7](docs/TECHNICAL_DEBT.md#7-session-advanced-features)

---

## 📚 Full Roadmap

**Complete breakdown**: [TECHNICAL_DEBT.md](docs/TECHNICAL_DEBT.md#implementation-roadmap)

**Timeline**:
- **Phase 1** (10 weeks): Critical gaps (#1-4) - Unblock core features
- **Phase 2** (2.5 weeks): High priority (#5-7) - User experience
- **Phase 3** (4 weeks): Optional enhancements - Advanced features

**Total to MVP**: 12.5 weeks
**Total to full parity**: 16.5 weeks

---

## 🧪 Testing Strategy

**Before starting work**:
1. Read [TESTING_STRATEGY.md](docs/testing-strategy.md)
2. Understand test structure: `tests/unit/`, `tests/integration/`, `tests/api/`
3. Current coverage: 47% (target: 80%)

**While working**:
- Write tests first (TDD encouraged)
- Run tests: `pytest tests/unit/modules/<module>/`
- Check coverage: `pytest --cov=src/faultmaven --cov-report=term-missing`

---

## 🔍 Finding Your Way Around

**Architecture**:
- System overview: [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Design specifications: [SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md)
- Module structure: `src/faultmaven/modules/<module>/`

**Code Structure**:
```
src/faultmaven/
├── modules/           # 6 domain modules
│   ├── auth/         # Authentication
│   ├── session/      # Session management
│   ├── case/         # Investigation lifecycle
│   ├── evidence/     # File upload
│   ├── knowledge/    # RAG knowledge base
│   └── agent/        # AI agent
├── infrastructure/   # Shared providers
│   └── providers/
│       ├── llm/      # LLM abstraction
│       ├── data/     # Database
│       └── vector/   # Vector store
└── app.py           # FastAPI application
```

---

## 🎯 Quick Decision Tree

**"I want to..."**

→ **Add a new feature**: Check if it's in TECHNICAL_DEBT.md. If yes, follow spec. If no, discuss in issue first.

→ **Fix a bug**: Create issue, write failing test, fix, verify test passes.

→ **Improve tests**: See [TESTING_STRATEGY.md](docs/testing-strategy.md), focus on modules with low coverage.

→ **Update documentation**: See [docs/README.md](docs/README.md) for organization.

→ **Understand investigation framework**: See [docs/working/investigation-framework-status.md](docs/working/investigation-framework-status.md) for current status (80% complete).

---

## ❓ Questions?

**Design questions**: See [SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md)
**Architecture questions**: See [ARCHITECTURE.md](docs/ARCHITECTURE.md)
**Implementation questions**: See [TECHNICAL_DEBT.md](docs/TECHNICAL_DEBT.md)
**Setup questions**: See [DEVELOPMENT.md](docs/DEVELOPMENT.md)
**Common issues**: See [troubleshooting.md](docs/troubleshooting.md)

---

## 📊 Current Status (2025-12-27)

**Tests**: 148/148 passing ✅
**Coverage**: 47% (target: 80%)
**Investigation Framework**: 80% complete (4/5 engines)
**Next Blocker**: Structured LLM output (2 weeks)

---

**Remember**: Always start with the critical gaps (#1-4) before working on nice-to-haves. The investigation framework is 80% complete but blocked - unblocking it is the highest priority.
