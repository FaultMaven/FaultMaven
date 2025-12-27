# Contributing to FaultMaven

Thank you for your interest in contributing to FaultMaven! This guide will help you get started.

---

## 🚀 Quick Start

**New to FaultMaven?** Follow these steps:

1. **Fork and clone** the repository
2. **Setup**: Follow [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) to get the project running locally
3. **Understand**: Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) to learn the system structure
4. **Find work**: See "What to Work On" below
5. **Make changes**: Create a feature branch, make your changes, add tests
6. **Submit**: Open a pull request with a clear description

---

## 📋 Development Workflow

This section answers three critical questions for contributors and AI agents.

### Question 1: What Documents to Read Before Starting Work?

**To understand existing issues and work on them, read in this order:**

1. **[docs/TECHNICAL_DEBT.md](docs/TECHNICAL_DEBT.md)** - START HERE
   - Lists all implementation gaps with priorities (🔴 Critical, 🟡 High, 🟢 Low)
   - Provides detailed specifications for each gap
   - Shows dependencies between tasks
   - Estimated effort for each task

2. **[docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md)** - Understand what it SHOULD be
   - Defines target design (desired state)
   - Complete API specifications
   - Design requirements for each module
   - **Implementation status summary at the end** (gives you current state snapshot)

3. **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Understand system structure
   - System overview and architecture diagrams
   - Module structure and boundaries
   - Architecture principles and patterns

4. **Code location** (specified in TECHNICAL_DEBT.md)
   - Each gap entry tells you which files/directories to read
   - Example: "Read current LLMProvider: `src/faultmaven/infrastructure/providers/llm/`"

**Quick reference flowchart:**

```
START → TECHNICAL_DEBT.md (pick a gap + read spec)
     ↓
     → SYSTEM_DESIGN.md (understand target design + check Implementation Status)
     ↓
     → ARCHITECTURE.md (understand system structure)
     ↓
     → Read code (location specified in TECHNICAL_DEBT.md)
     ↓
     → Implement fix
```

### Question 2: How to Ask a Developer or Agent to Work on a Task?

**For human developers:**

```markdown
"Please work on [TECHNICAL_DEBT.md#2](docs/TECHNICAL_DEBT.md#2-data-processing-pipeline) - Data Processing Pipeline.

Start by reading:
1. docs/TECHNICAL_DEBT.md#2 for the spec
2. docs/SYSTEM_DESIGN.md (Evidence Module section)
3. FaultMaven-Mono reference: faultmaven/data_processing/

Create a feature branch and submit a PR when done."
```

**For AI agents:**

```markdown
"Implement the Data Processing Pipeline as specified in docs/TECHNICAL_DEBT.md#2.

Context:
- Target design: docs/SYSTEM_DESIGN.md (Evidence Module)
- Current status: 0% complete (11 extractors missing)
- Reference implementation: FaultMaven-Mono faultmaven/data_processing/

Deliverables:
1. Data type detection (8 types)
2. 11 extractors (LogExtractor, JSONConfigExtractor, etc.)
3. Integration with knowledge base
4. Unit tests (target: 80% coverage)
5. Update docs/TECHNICAL_DEBT.md to mark gap as completed"
```

**Standard task assignment template:**

```markdown
Task: [Gap Name from TECHNICAL_DEBT.md]
Priority: [🔴 Critical | 🟡 High | 🟢 Low]
Effort: [X weeks/days]

Read before starting:
- docs/TECHNICAL_DEBT.md#[N] (specification)
- docs/SYSTEM_DESIGN.md ([module section])
- [Code location if applicable]

Deliverables:
- [ ] Implementation
- [ ] Tests (80% coverage target)
- [ ] Update TECHNICAL_DEBT.md (mark completed)
- [ ] Update SYSTEM_DESIGN.md (Implementation Status section)
```

### Question 3: What Documents to Create/Update After Implementation?

**After implementing a feature or closing a gap, update these documents in order:**

#### 1. Update TECHNICAL_DEBT.md (REQUIRED)

**Location**: `docs/TECHNICAL_DEBT.md`

**What to update**:

- Mark the gap as ✅ Complete in the summary table
- Update percentage complete for the affected module
- If gap is fully closed, remove it from "Critical Gaps" section or move to "Recently Closed" section

**Example**:

```diff
### 2. Data Processing Pipeline

- **Current State**: ❌ Not implemented (0% coverage)
+ **Current State**: ✅ Implemented (100% coverage)

**Gap Description**:
- Missing Components:
-   - ❌ LogExtractor
-   - ❌ JSONConfigExtractor
+   - ✅ LogExtractor (PR #123)
+   - ✅ JSONConfigExtractor (PR #124)
```

#### 2. Update SYSTEM_DESIGN.md (REQUIRED)

**Location**: `docs/SYSTEM_DESIGN.md` (Implementation Status section at end)

**What to update**:

- Update module implementation summary table
- Update investigation framework status if applicable
- Remove from "Critical Missing Components" list

**Example**:

```diff
### Module Implementation Summary

- **Evidence**: ✅ Complete (core), ❌ 0% (advanced) - **Data processing pipeline missing**
+ **Evidence**: ✅ Complete (core), ✅ 100% (advanced) - Fully implemented
```

#### 3. Update ARCHITECTURE.md (if applicable)

**Location**: `docs/ARCHITECTURE.md`

**When to update**: If you added new components or changed system structure

**What to update**:

- Add new components to architecture diagrams
- Update module descriptions
- Update implementation status inline markers

#### 4. Create/Update Module Documentation (OPTIONAL)

**Location**: `docs/modules/[module-name].md` (if it exists)

**When to create**: For significant new modules or complex features

**What to include**:

- Module purpose and responsibilities
- API endpoints (if applicable)
- Usage examples
- Configuration options

#### 5. Update tests/README.md (if testing patterns changed)

**Location**: `tests/README.md` or `docs/testing-strategy.md`

**When to update**: If you introduced new testing patterns or utilities

**Checklist After Implementation:**

```markdown
After closing a gap or implementing a feature:

- [ ] Code merged to main branch
- [ ] Tests passing (verify with pytest)
- [ ] Coverage ≥ 80% for new code
- [ ] docs/TECHNICAL_DEBT.md updated (mark gap completed)
- [ ] docs/SYSTEM_DESIGN.md updated (Implementation Status section)
- [ ] docs/ARCHITECTURE.md updated (if structure changed)
- [ ] CHANGELOG.md updated (add entry for next release)
- [ ] Close related GitHub issues (if any)
```

---

## 🎯 What to Work On

### Critical Gaps (Start Here)

We have **4 critical implementation gaps** that block core functionality. These are the highest priority:

#### 1. Structured LLM Output Support (2 weeks) 🔴 CRITICAL

**Why**: Unblocks HypothesisManager and Agent Tools framework

**What to do**:
1. Read current LLMProvider abstraction: `src/faultmaven/infrastructure/providers/llm/`
2. Refactor to support JSON mode and function calling
3. Update all provider implementations (OpenAI, Anthropic, etc.)

**Detailed spec**: [docs/TECHNICAL_DEBT.md#1](docs/TECHNICAL_DEBT.md#1-structured-llm-output-support)

**Impact**: Unblocks 4 weeks of additional work

---

#### 2. Data Processing Pipeline (3 weeks) 🔴 CRITICAL

**Why**: Evidence files are uploaded but not processed - core functionality gap

**What to do**:
1. Implement data type detection (8 types)
2. Build 11 extractors (LogExtractor, JSONConfigExtractor, etc.)
3. Integrate with knowledge base for RAG retrieval

**Reference**: FaultMaven-Mono `faultmaven/data_processing/`

**Detailed spec**: [docs/TECHNICAL_DEBT.md#2](docs/TECHNICAL_DEBT.md#2-data-processing-pipeline)

**Impact**: Enables semantic search across uploaded logs/configs

---

#### 3. Agent Tools Framework (4 weeks) 🔴 CRITICAL

**Why**: Agent can only chat, cannot execute troubleshooting actions

**What to do**:
1. Build tool execution framework + sandboxing
2. Implement 8 tools (CommandExecutor, FileReader, NetworkAnalyzer, etc.)
3. Add permission system + audit logging

**Depends on**: Structured LLM output (#1)

**Detailed spec**: [docs/TECHNICAL_DEBT.md#3](docs/TECHNICAL_DEBT.md#3-agent-tools-framework)

**Impact**: Enables autonomous troubleshooting

---

#### 4. HypothesisManager Integration (1 week) 🔴 CRITICAL

**Why**: Completes investigation framework from 80% → 100%

**What to do**:
1. Integrate structured LLM output with HypothesisManager
2. Activate hypothesis extraction from LLM responses

**Code location**: `src/faultmaven/modules/case/engines/hypothesis_manager.py`

**Depends on**: Structured LLM output (#1)

**Detailed spec**: [docs/TECHNICAL_DEBT.md#4](docs/TECHNICAL_DEBT.md#4-hypothesismanager-integration)

---

### High Priority (After Critical Gaps)

5. **Report Generation** (1 week) - PDF/Markdown export ([docs/TECHNICAL_DEBT.md#5](docs/TECHNICAL_DEBT.md#5-report-generation))
6. **Case Search & Filter** (1 week) - Search historical cases ([docs/TECHNICAL_DEBT.md#6](docs/TECHNICAL_DEBT.md#6-case-search--filter))
7. **Session Advanced Features** (3 days) - Session search/stats ([docs/TECHNICAL_DEBT.md#7](docs/TECHNICAL_DEBT.md#7-session-advanced-features))

### Full Roadmap

**Complete breakdown**: [docs/TECHNICAL_DEBT.md](docs/TECHNICAL_DEBT.md#implementation-roadmap)

**Timeline**:
- **Phase 1** (10 weeks): Critical gaps (#1-4) - Unblock core features
- **Phase 2** (2.5 weeks): High priority (#5-7) - User experience
- **Phase 3** (4 weeks): Optional enhancements - Advanced features

**Current Status** (2025-12-27):
- Tests: 148/148 passing ✅
- Coverage: 47% (target: 80%)
- Investigation Framework: 80% complete (4/5 engines)

---

## 🧪 Testing Requirements

**Before starting work**:
1. Read [docs/testing-strategy.md](docs/testing-strategy.md)
2. Understand test structure: `tests/unit/`, `tests/integration/`, `tests/api/`

**While working**:
- Write tests first (TDD encouraged)
- Run tests: `pytest tests/unit/modules/<module>/`
- Check coverage: `pytest --cov=src/faultmaven --cov-report=term-missing`
- Ensure all tests pass before submitting PR

**Coverage target**: 80% (currently 47%)

---

## 🔍 Code Structure

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

## 📝 Pull Request Guidelines

### Before Submitting

- [ ] Code follows project style (use `ruff` for linting)
- [ ] Tests added for new functionality
- [ ] All tests pass locally
- [ ] Documentation updated (if applicable)
- [ ] Commit messages are clear and descriptive

### PR Description Template

```markdown
## Summary
Brief description of what this PR does

## Related Issue
Fixes #123 (or "Addresses TECHNICAL_DEBT.md#1")

## Changes
- Bullet list of key changes

## Testing
- How you tested these changes
- Coverage impact (before/after)

## Screenshots (if applicable)
```

### Review Process

1. **Automated checks**: All tests must pass, coverage should not decrease
2. **Code review**: At least one maintainer approval required
3. **Documentation**: Ensure relevant docs are updated
4. **Merge**: Squash and merge once approved

---

## 🎯 Decision Tree

**"I want to..."**

→ **Add a new feature**: Check if it's in [docs/TECHNICAL_DEBT.md](docs/TECHNICAL_DEBT.md). If yes, follow spec. If no, discuss in issue first.

→ **Fix a bug**: Create issue, write failing test, fix, verify test passes.

→ **Improve tests**: See [docs/testing-strategy.md](docs/testing-strategy.md), focus on modules with low coverage.

→ **Update documentation**: See [docs/README.md](docs/README.md) for organization.

→ **Understand investigation framework**: See [docs/working/investigation-framework-status.md](docs/working/investigation-framework-status.md) (80% complete).

---

## 📚 Documentation

**Architecture & Design**:
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture
- [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) - Design specifications
- [docs/TECHNICAL_DEBT.md](docs/TECHNICAL_DEBT.md) - Implementation gaps (start here!)

**Development**:
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) - Setup and workflow
- [docs/testing-strategy.md](docs/testing-strategy.md) - Testing approach

**Operations**:
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Production deployment
- [docs/troubleshooting.md](docs/troubleshooting.md) - Common issues

---

## 💬 Communication

- **Questions**: Open a [GitHub Discussion](https://github.com/FaultMaven/faultmaven/discussions)
- **Bugs**: Open a [GitHub Issue](https://github.com/FaultMaven/faultmaven/issues)
- **Feature Requests**: Open a [Feature Request](https://github.com/FaultMaven/faultmaven/issues/new?template=feature_request.md)

---

## 📜 Code of Conduct

Please be respectful and constructive in all interactions. We follow the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/).

---

## 📋 License

By contributing to FaultMaven, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).

---

**Remember**: Start with the critical gaps (#1-4) before working on nice-to-haves. The investigation framework is 80% complete but blocked - unblocking it is the highest priority.

**Last Updated**: 2025-12-27
