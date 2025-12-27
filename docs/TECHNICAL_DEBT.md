# Technical Debt Tracking

**Last Updated**: 2025-12-26
**Baseline**: FaultMaven-Mono (Original Reference Implementation)

---

## Purpose

This document tracks **implementation gaps** between the [System Design](architecture/design-specifications.md) (desired state) and the current implementation (actual state).

**Design specifications** are defined in [architecture/design-specifications.md](architecture/design-specifications.md).

---

## Critical Gaps 🔴

### 1. Structured LLM Output Support

**Design Requirement**: [architecture/design-specifications.md - LLMProvider](architecture/design-specifications.md#provider-abstraction-layer)

**Current State**: ❌ Not implemented

**Gap Description**:
- LLM providers do not support structured output modes (JSON mode or function calling)
- Required for HypothesisManager to extract hypotheses from LLM responses
- Required for Agent Tools to parse tool calls from LLM

**Impact**:
- HypothesisManager cannot be completed (investigation framework stuck at 80%)
- Agent Tools framework cannot be implemented
- Manual prompt engineering required for structured data extraction (unreliable)

**Architectural Change Required**:
```python
# Current: Only supports text completion
class LLMProvider(Protocol):
    async def chat(self, messages: List[Message]) -> str:
        ...

# Required: Add structured output support
class LLMProvider(Protocol):
    async def chat(
        self,
        messages: List[Message],
        response_format: Optional[Dict] = None,  # JSON schema
        tools: Optional[List[Tool]] = None        # Function calling
    ) -> Union[str, Dict, ToolCall]:
        ...
```

**Estimated Effort**: 2 weeks
- 1 week: Refactor LLMProvider abstraction
- 1 week: Update all provider implementations (OpenAI, Anthropic, etc.)

**Priority**: 🔴 CRITICAL - Blocks multiple features

**Tracking**: Issue #5

---

### 2. Data Processing Pipeline

**Design Requirement**: [architecture/design-specifications.md - Evidence Module](architecture/design-specifications.md#4-evidence-module)

**Current State**: ❌ Not implemented (0% coverage)

**Gap Description**:

**Missing Components**:
1. Data type detection (8 types)
2. Data extractors (11 extractors - all missing):
   - ❌ LogExtractor
   - ❌ YAMLConfigExtractor
   - ❌ JSONConfigExtractor
   - ❌ TOMLConfigExtractor
   - ❌ ENVConfigExtractor
   - ❌ TraceExtractor
   - ❌ MetricExtractor
   - ❌ CodeExtractor
   - ❌ MarkdownExtractor
   - ❌ ImageExtractor
   - ❌ GenericTextExtractor
3. Data transformation and enrichment
4. Integration with knowledge base for RAG retrieval

**Impact**:
- Uploaded evidence files are stored but not processed
- Agent cannot query structured data from evidence
- No semantic search across uploaded logs/configs
- Limited troubleshooting capability

**Code Size Gap**: ~8,000 lines (estimated from FaultMaven-Mono)

**Estimated Effort**: 3 weeks
- Week 1: Data type detection + 4 extractors (Log, JSON, YAML, Text)
- Week 2: 4 extractors (Config, Trace, Metric, Code)
- Week 3: 3 extractors (Markdown, Image, Generic) + integration

**Priority**: 🔴 CRITICAL - Core troubleshooting functionality

**Reference**: FaultMaven-Mono `faultmaven/data_processing/`

---

### 3. Agent Tools Framework

**Design Requirement**: [architecture/design-specifications.md - Agent Module](architecture/design-specifications.md#6-agent-module)

**Current State**: ❌ Not implemented (0% coverage)

**Gap Description**:

**Missing Components**:
1. Tool execution framework
2. 8+ required tools:
   - ❌ CommandExecutor - Run safe system commands
   - ❌ ProcessInspector - Inspect processes
   - ❌ NetworkAnalyzer - Network diagnostics
   - ❌ FileReader - Read file contents
   - ❌ FileSearcher - Search files
   - ❌ HTTPClient - Make HTTP requests
   - ❌ DatabaseQuery - Query databases
   - ❌ KnowledgeSearch - Semantic search (partial - RAG exists)
3. Sandboxed execution environment
4. Tool permission system
5. Audit logging

**Impact**:
- Agent cannot execute troubleshooting actions autonomously
- Limited to passive Q&A (no active investigation)
- Reduced troubleshooting effectiveness

**Architectural Dependency**: Requires structured LLM output for function calling

**Estimated Effort**: 4 weeks
- Week 1: Tool execution framework + sandboxing
- Week 2: 4 tools (Command, File operations)
- Week 3: 3 tools (Network, HTTP, Database)
- Week 4: Permission system + audit logging

**Priority**: 🔴 CRITICAL - Core agent capability

**Blockers**: Depends on structured LLM output (#1)

---

### 4. HypothesisManager Integration

**Design Requirement**: [architecture/design-specifications.md - Case Module](architecture/design-specifications.md#35-hypothesismanager)

**Current State**: ⏳ Pending (code exists, not integrated)

**Gap Description**:
- HypothesisManager code exists in `src/faultmaven/modules/case/engines/hypothesis_manager.py`
- Cannot be activated without structured LLM output
- Investigation framework stuck at 80% completion (4/5 engines)

**Impact**:
- No automatic hypothesis extraction
- Manual hypothesis tracking required
- Investigation framework incomplete

**Architectural Dependency**: Requires structured LLM output for hypothesis extraction

**Estimated Effort**: 1 week (after structured output is available)

**Priority**: 🔴 CRITICAL - Completes investigation framework

**Blockers**: Depends on structured LLM output (#1)

**Tracking**: Issue #5

---

## High Priority Gaps 🟡

### 5. Report Generation

**Design Requirement**: [architecture/design-specifications.md - Case Module](architecture/design-specifications.md#3-case-module)

**Current State**: ❌ Not implemented

**Gap Description**:
- Cannot export investigation results
- No PDF or Markdown report generation
- Missing API endpoint: `GET /cases/{case_id}/report`

**Impact**:
- Cannot share investigation results
- No audit trail for closed cases
- Reduced usability

**Estimated Effort**: 1 week
- Report template design
- PDF generation (weasyprint or reportlab)
- Markdown generation
- API endpoint implementation

**Priority**: 🟡 HIGH - Required for case lifecycle completion

---

### 6. Case Search & Filter

**Design Requirement**: [architecture/design-specifications.md - Case Module](architecture/design-specifications.md#3-case-module)

**Current State**: ❌ Not implemented

**Gap Description**:
- Missing API endpoint: `POST /cases/search`
- No filtering by status, date, user
- No full-text search across case messages
- Missing 62% of advanced case management endpoints

**Impact**:
- Difficult to find past cases
- Poor user experience for case management
- Cannot analyze historical cases

**Estimated Effort**: 1 week
- Search query parser
- Database query optimization
- Pagination support
- API endpoint implementation

**Priority**: 🟡 HIGH - User experience

---

### 7. Session Advanced Features

**Design Requirement**: [architecture/design-specifications.md - Session Module](architecture/design-specifications.md#2-session-module)

**Current State**: ⚠️ Partially implemented (95%)

**Missing Features**:
- ❌ Session search
- ❌ Session statistics
- ⚠️ Heartbeat endpoint exists but needs testing

**Impact**:
- Cannot search historical sessions
- No analytics on session usage
- Minor UX gaps

**Estimated Effort**: 3 days
- Session search API
- Statistics aggregation
- Heartbeat testing

**Priority**: 🟡 MEDIUM - Nice to have

---

## Low Priority Gaps 🟢

### 8. Knowledge Base Advanced Features

**Design Requirement**: [architecture/design-specifications.md - Knowledge Module](architecture/design-specifications.md#5-knowledge-module)

**Current State**: ⚠️ Core complete (90%), advanced features missing

**Missing Features**:
- ❌ Document versioning
- ❌ Knowledge graph
- ❌ Smart indexing/auto-tagging

**Impact**:
- Limited to basic RAG
- No document history
- Manual tagging required

**Estimated Effort**: 2 weeks
- Document versioning: 3 days
- Knowledge graph: 5 days
- Smart indexing: 5 days

**Priority**: 🟢 LOW - Enhancement

---

### 9. OAuth/SAML Authentication

**Design Requirement**: [architecture/design-specifications.md - Deployment Profiles](architecture/design-specifications.md#enterprise-profile-production)

**Current State**: ❌ Not implemented (Enterprise feature)

**Gap Description**:
- Only JWT authentication implemented
- No OAuth 2.0 providers (Google, GitHub, etc.)
- No SAML for enterprise SSO

**Impact**:
- Cannot integrate with enterprise identity providers
- Limited to email/password authentication

**Estimated Effort**: 2 weeks

**Priority**: 🟢 LOW - Enterprise feature, not in MVP

---

## Implementation Status Summary

### By Module

| Module | Design Coverage | Implementation | Status |
|--------|----------------|----------------|--------|
| Authentication | 100% | 100% | ✅ Complete |
| Session | 100% | 95% | ✅ Nearly complete |
| Case (Basic) | 100% | 85% | ⚠️ Core complete |
| Case (Framework) | 100% | 80% | ⚠️ 4/5 engines |
| Evidence (Upload) | 100% | 100% | ✅ Complete |
| Evidence (Processing) | 100% | 0% | ❌ Critical gap |
| Knowledge (Core) | 100% | 100% | ✅ Complete |
| Knowledge (Advanced) | 100% | 10% | 🟢 Optional features |
| Agent (Chat) | 100% | 100% | ✅ Complete |
| Agent (Tools) | 100% | 12.5% | ❌ Critical gap (1/8 tools) |

### By Priority

| Priority | Count | Total Effort | Impact |
|----------|-------|--------------|--------|
| 🔴 Critical | 4 | 10 weeks | Blocks core features |
| 🟡 High | 3 | 2.5 weeks | UX and completeness |
| 🟢 Low | 2 | 4 weeks | Optional enhancements |
| **Total** | **9** | **16.5 weeks** | |

---

## Code Size Analysis

### Current vs Reference

```
FaultMaven-Mono (Baseline):  23,456 lines of Python
Current Monolith:             3,684 lines of Python
Coverage:                     15.7%
Gap:                         19,772 lines (84.3%)
```

### Gap Breakdown by Component

| Component | Lines (est.) | Priority | Effort |
|-----------|--------------|----------|--------|
| Data Processing Pipeline | ~8,000 | 🔴 Critical | 3 weeks |
| Agent Tools Framework | ~4,000 | 🔴 Critical | 4 weeks |
| Advanced Knowledge Features | ~3,000 | 🟢 Low | 2 weeks |
| Report Generation | ~2,000 | 🟡 High | 1 week |
| Case Search/Analytics | ~1,500 | 🟡 High | 1 week |
| Other Features | ~1,272 | Mixed | Variable |

---

## Implementation Roadmap

### Phase 1: Critical Gaps (10 weeks)

**Priority**: Unblock core features

1. **Structured LLM Output** (2 weeks) - Unblocks everything
   - Refactor LLMProvider abstraction
   - Add JSON mode and function calling support
   - Update all provider implementations

2. **Data Processing Pipeline** (3 weeks) - Core evidence processing
   - Implement 11 data extractors
   - Add data type detection
   - Integrate with knowledge base

3. **Agent Tools Framework** (4 weeks) - Agent capabilities
   - Build tool execution framework
   - Implement 8+ required tools
   - Add sandboxing and permissions

4. **HypothesisManager** (1 week) - Complete investigation framework
   - Integrate structured output
   - Activate hypothesis tracking
   - Add hypothesis lifecycle management

**Deliverables**: 100% investigation framework, full evidence processing, autonomous agent

---

### Phase 2: High Priority (2.5 weeks)

**Priority**: User experience and completeness

5. **Report Generation** (1 week) - Case lifecycle completion
   - PDF and Markdown export
   - Report templates
   - API endpoint

6. **Case Search & Filter** (1 week) - Case management UX
   - Search API
   - Filtering and pagination
   - Full-text search

7. **Session Features** (3 days) - Session management polish
   - Session search
   - Statistics

**Deliverables**: Complete case lifecycle, improved UX

---

### Phase 3: Enhancements (4 weeks) - Optional

**Priority**: Advanced features, not MVP

8. **Knowledge Base Advanced** (2 weeks)
   - Document versioning
   - Knowledge graph
   - Smart indexing

9. **OAuth/SAML** (2 weeks)
   - Enterprise authentication
   - Identity provider integration

**Deliverables**: Enterprise-ready features

---

## Decision Points

### Should We Implement All Gaps?

**Option A: Full Parity** (16.5 weeks)
- Implement all features from FaultMaven-Mono
- Achieve 100% feature parity
- Total effort: 16.5 weeks

**Option B: MVP Focus** (12.5 weeks)
- Implement only Critical + High priority (Phases 1-2)
- Skip Low priority enhancements
- Total effort: 12.5 weeks
- Recommended: **✅ Yes**

**Option C: Critical Only** (10 weeks)
- Implement only Critical gaps (Phase 1)
- Skip High and Low priority
- Total effort: 10 weeks
- Risk: Incomplete user experience

**Recommendation**: **Option B (MVP Focus)** - Implement Phases 1-2 for functional completeness without optional features.

---

## Tracking

### Active Issues

- **Issue #5**: HypothesisManager integration (blocked by structured LLM output)

### GitHub Project Board

Track implementation progress at: <https://github.com/FaultMaven/faultmaven/projects>

(Create project board with 3 columns: Critical, High Priority, Low Priority)

---

## Related Documents

**Design Specification**: [architecture/design-specifications.md](architecture/design-specifications.md)

**Architecture**: [architecture/](architecture/)

**Feature Parity** (deprecated): [working/FEATURE_PARITY_TRACKING.md](working/FEATURE_PARITY_TRACKING.md)

---

**Last Updated**: 2025-12-27
**Next Review**: After Phase 1 completion
**Total Estimated Effort**: 16.5 weeks (all gaps), 12.5 weeks (MVP)
