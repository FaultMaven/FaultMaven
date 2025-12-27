# Technical Debt Tracking

**Last Updated**: 2025-12-27
**Baseline**: FaultMaven-Mono (Original Reference Implementation)

---

## Purpose

This document tracks **implementation gaps** between the [System Design](SYSTEM_DESIGN.md) (desired state) and the current implementation (actual state).

**Design specifications** are defined in [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md).

---

## Critical Gaps 🔴

### 1. Structured LLM Output Support

**Design Requirement**: [SYSTEM_DESIGN.md - LLMProvider](SYSTEM_DESIGN.md#provider-abstraction-layer)

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

**Design Requirement**: [SYSTEM_DESIGN.md - Evidence Module](SYSTEM_DESIGN.md#4-evidence-module)

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

**Design Requirement**: [SYSTEM_DESIGN.md - Agent Module](SYSTEM_DESIGN.md#6-agent-module)

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

**Design Requirement**: [SYSTEM_DESIGN.md - Case Module](SYSTEM_DESIGN.md#35-hypothesismanager)

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

### 5. Notification System

**Design Requirement**: FR-NOTIF (SRS)

**Current State**: ❌ Not implemented (0% coverage)

**Gap Description**:
- No notification infrastructure exists in the codebase
- Missing components:
  - ❌ NotificationService
  - ❌ WebSocket for real-time updates
  - ❌ Email integration
  - ❌ Push notification support
  - ❌ Notification queue/dispatch

**Impact**:
- Users miss case updates, escalations, and resolution status changes
- No real-time collaboration capability
- Poor user experience for multi-user scenarios

**Estimated Effort**: 2 weeks
- Week 1: NotificationService + WebSocket infrastructure
- Week 2: Email integration + queue-based dispatch

**Priority**: 🔴 CRITICAL - Core user experience requirement

---

### 6. Response Type Classification

**Design Requirement**: FR-RT (SRS) - Seven response types

**Current State**: ❌ Not implemented

**Gap Description**:
- Agent generates responses without type classification
- Missing response types:
  - ❌ ANSWER
  - ❌ PLAN_PROPOSAL
  - ❌ CLARIFICATION_REQUEST
  - ❌ CONFIRMATION_REQUEST
  - ❌ SOLUTION_READY
  - ❌ NEEDS_MORE_DATA
  - ❌ ESCALATION_REQUIRED
- No type-aware prompt generation
- No UI behavior signals based on response type

**Current Implementation** (`modules/agent/service.py`):
```python
# Current: Generic prompt without type classification
base_prompt = """You are FaultMaven AI, an expert debugging assistant..."""
```

**Impact**:
- Cannot adapt agent behavior based on response type
- No structured conversation flow
- UI cannot display type-specific affordances

**Estimated Effort**: 1 week
- 3 days: ResponseType enum + classification logic
- 2 days: Type-aware prompt generation + API response metadata

**Priority**: 🔴 CRITICAL - Required for intelligent conversation flow

**Blockers**: Benefits from structured LLM output (#1) but can use prompt engineering initially

---

### 7. Agent ↔ Investigation Framework Connection

**Design Requirement**: Investigation-aware agent responses

**Current State**: ❌ Not connected

**Gap Description**:
- AgentService directly calls LLM without routing through MilestoneEngine
- Investigation state not used to inform prompts
- Case status transitions not triggered by agent responses
- Progress tracking disconnected from conversation

**Current Flow**:
```
User Message → AgentService → LLM → Response (no investigation awareness)
```

**Required Flow**:
```
User Message → AgentService → MilestoneEngine → LLM → Response
                                    ↓
                            Update investigation state
                                    ↓
                            Trigger status transitions
```

**Impact**:
- Investigation framework (4/5 engines) bypassed during chat
- No automatic hypothesis extraction from responses
- Case never progresses through investigation lifecycle
- MilestoneEngine, MemoryManager, OODAEngine unused

**Estimated Effort**: 1 week
- 3 days: Route agent through MilestoneEngine
- 2 days: Connect state updates to case lifecycle

**Priority**: 🔴 CRITICAL - Investigation framework unusable without this

**Blockers**: None (can implement independently)

---

## High Priority Gaps 🟡

### 8. Report Generation

**Design Requirement**: [SYSTEM_DESIGN.md - Case Module](SYSTEM_DESIGN.md#3-case-module)

**Current State**: ⚠️ Partially implemented

**Gap Description**:
- ReportService exists with templates but not connected to investigation state
- Cannot export investigation results with full context
- Reports don't populate from investigation_state in case_metadata

**Impact**:
- Cannot share investigation results
- No audit trail for closed cases
- Reduced usability

**Estimated Effort**: 1 week
- Connect ReportService to investigation state
- PDF generation (weasyprint or reportlab)
- Markdown generation
- API endpoint enhancement

**Priority**: 🟡 HIGH - Required for case lifecycle completion

---

### 9. Case Search & Filter

**Design Requirement**: [SYSTEM_DESIGN.md - Case Module](SYSTEM_DESIGN.md#3-case-module)

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

### 10. Session Advanced Features

**Design Requirement**: [SYSTEM_DESIGN.md - Session Module](SYSTEM_DESIGN.md#2-session-module)

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

### 11. DOCUMENTING Case State

**Design Requirement**: FR-CM-006 (SRS) - Case lifecycle states

**Current State**: ❌ Not implemented

**Gap Description**:
- Current states: CONSULTING, INVESTIGATING, RESOLVED, CLOSED
- Missing DOCUMENTING state that restricts new investigations after resolution
- No state transition validation/enforcement

**Current Implementation** (`modules/case/orm.py`):
```python
class CaseStatus(str, Enum):
    CONSULTING = "consulting"
    VERIFYING = "verifying"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    RESOLVED = "resolved"
    CLOSED = "closed"
    # Missing: DOCUMENTING
```

**Impact**:
- Cannot enforce post-resolution documentation phase
- Invalid state transitions possible
- Incomplete case lifecycle

**Estimated Effort**: 3 days
- Add DOCUMENTING state to enum
- Implement state transition validation
- Update StatusManager

**Priority**: 🟡 HIGH - Case lifecycle completeness

---

### 12. Rate Limiting

**Design Requirement**: NFR-SEC (Security requirements)

**Current State**: ⚠️ Interface exists, not wired

**Gap Description**:
- RateLimiter interface defined in `infrastructure/interfaces.py`
- Not connected to any API endpoints
- No protection against abuse

**Impact**:
- DoS vulnerability
- No abuse prevention
- Resource exhaustion possible

**Estimated Effort**: 2 days
- Wire RateLimiter to FastAPI middleware
- Configure rate limits per endpoint
- Add Redis-based rate tracking

**Priority**: 🟡 HIGH - Security requirement

---

### 13. Circular Dialogue Detection

**Design Requirement**: FR-CNV (Conversation Management)

**Current State**: ❌ Not implemented

**Gap Description**:
- No detection of repetitive conversation patterns
- Agent may repeat same questions/suggestions
- No similarity check on recent messages

**Impact**:
- Wasted user interactions
- Poor user experience
- Inefficient troubleshooting

**Estimated Effort**: 3 days
- Implement message similarity detection
- Add conversation pattern tracking
- Integrate with AgentService to prevent loops

**Priority**: 🟡 HIGH - Required by SRS

---

## Low Priority Gaps 🟢

### 14. Knowledge Base Advanced Features

**Design Requirement**: [SYSTEM_DESIGN.md - Knowledge Module](SYSTEM_DESIGN.md#5-knowledge-module)

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

### 15. OAuth/SAML Authentication

**Design Requirement**: [SYSTEM_DESIGN.md - Deployment Profiles](SYSTEM_DESIGN.md#enterprise-profile-production)

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
| Case (Framework) | 100% | 80% | ⚠️ 4/5 engines (not connected to Agent) |
| Evidence (Upload) | 100% | 100% | ✅ Complete |
| Evidence (Processing) | 100% | 0% | ❌ Critical gap |
| Knowledge (Core) | 100% | 100% | ✅ Complete |
| Knowledge (Advanced) | 100% | 10% | 🟢 Optional features |
| Agent (Chat) | 100% | 70% | ⚠️ Missing response types, investigation connection |
| Agent (Tools) | 100% | 12.5% | ❌ Critical gap (1/8 tools) |
| Notification | 100% | 0% | ❌ Critical gap |

### By Priority

| Priority | Count | Total Effort | Impact |
|----------|-------|--------------|--------|
| 🔴 Critical | 7 | 14 weeks | Blocks core features |
| 🟡 High | 6 | 4 weeks | UX and completeness |
| 🟢 Low | 2 | 4 weeks | Optional enhancements |
| **Total** | **15** | **22 weeks** | |

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

### Phase 1: Critical Gaps (14 weeks)

**Priority**: Unblock core features

1. **Structured LLM Output** (2 weeks) - Unblocks everything
   - Refactor LLMProvider abstraction
   - Add JSON mode and function calling support
   - Update all provider implementations

2. **Agent ↔ Investigation Framework Connection** (1 week) - Enable investigation
   - Route AgentService through MilestoneEngine
   - Connect state updates to case lifecycle
   - Enable investigation-aware prompts

3. **Response Type Classification** (1 week) - Intelligent responses
   - Add ResponseType enum (7 types)
   - Implement classification logic
   - Type-aware prompt generation

4. **Notification System** (2 weeks) - User awareness
   - NotificationService + WebSocket infrastructure
   - Email integration + queue-based dispatch

5. **Data Processing Pipeline** (3 weeks) - Core evidence processing
   - Implement 11 data extractors
   - Add data type detection
   - Integrate with knowledge base

6. **Agent Tools Framework** (4 weeks) - Agent capabilities
   - Build tool execution framework
   - Implement 8+ required tools
   - Add sandboxing and permissions

7. **HypothesisManager Integration** (1 week) - Complete investigation framework
   - Integrate structured output
   - Activate hypothesis tracking
   - Add hypothesis lifecycle management

**Deliverables**: 100% investigation framework, full evidence processing, autonomous agent, notifications

---

### Phase 2: High Priority (4 weeks)

**Priority**: User experience and completeness

8. **Report Generation** (1 week) - Case lifecycle completion
   - Connect to investigation state
   - PDF and Markdown export
   - API endpoint enhancement

9. **Case Search & Filter** (1 week) - Case management UX
   - Search API
   - Filtering and pagination
   - Full-text search

10. **DOCUMENTING Case State** (3 days) - Complete state machine
    - Add DOCUMENTING state
    - State transition validation
    - Update StatusManager

11. **Rate Limiting** (2 days) - Security
    - Wire RateLimiter to endpoints
    - Redis-based tracking

12. **Circular Dialogue Detection** (3 days) - Conversation quality
    - Message similarity detection
    - Pattern tracking

13. **Session Features** (3 days) - Session management polish
    - Session search
    - Statistics

**Deliverables**: Complete case lifecycle, improved UX, security hardening

---

### Phase 3: Enhancements (4 weeks) - Optional

**Priority**: Advanced features, not MVP

14. **Knowledge Base Advanced** (2 weeks)
    - Document versioning
    - Knowledge graph
    - Smart indexing

15. **OAuth/SAML** (2 weeks)
    - Enterprise authentication
    - Identity provider integration

**Deliverables**: Enterprise-ready features

---

## Decision Points

### Should We Implement All Gaps?

**Option A: Full Parity** (22 weeks)
- Implement all features from FaultMaven-Mono
- Achieve 100% feature parity
- Total effort: 22 weeks

**Option B: MVP Focus** (18 weeks)
- Implement only Critical + High priority (Phases 1-2)
- Skip Low priority enhancements
- Total effort: 18 weeks
- Recommended: **✅ Yes**

**Option C: Critical Only** (14 weeks)
- Implement only Critical gaps (Phase 1)
- Skip High and Low priority
- Total effort: 14 weeks
- Risk: Incomplete user experience, missing security features

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

**Design Specification**: [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md)

**Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)

**Feature Parity** (deprecated): [FEATURE_PARITY_TRACKING.md](FEATURE_PARITY_TRACKING.md)

---

**Last Updated**: 2025-12-27
**Next Review**: After Phase 1 completion
**Total Estimated Effort**: 22 weeks (all gaps), 18 weeks (MVP)
