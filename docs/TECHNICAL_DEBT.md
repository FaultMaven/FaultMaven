# Technical Debt Tracking

**Last Updated**: 2025-12-27
**Baseline**: FaultMaven-Mono (Original Reference Implementation)

---

## Purpose

This document tracks **implementation gaps** between the [System Design](architecture/design-specifications.md) (desired state) and the current implementation (actual state).

**Design specifications** are defined in [architecture/design-specifications.md](architecture/design-specifications.md).

---

## Recently Resolved Items

### Structured LLM Output Support

**Status**: ✅ RESOLVED (2025-12-27)

**Implementation**:
- Added `ToolDefinition` class for function calling definitions
- Added `ResponseFormat` class for JSON mode / structured output
- Updated `LLMProvider` protocol with explicit `tools` and `response_format` parameters
- Updated `CoreLLMProvider.chat()` to handle structured output and parse JSON responses
- `ChatResponse` now includes `parsed` field for JSON output

**Files Changed**:
- `src/faultmaven/providers/interfaces.py` - Added ToolDefinition, ResponseFormat classes
- `src/faultmaven/providers/core.py` - Updated CoreLLMProvider.chat() method

---

### HypothesisManager Integration

**Status**: ✅ RESOLVED (2025-12-27)

**Implementation**:
- Integrated HypothesisManager with MilestoneEngine for hypothesis extraction
- Added `_extract_investigation_updates()` method for structured/keyword-based extraction
- Added `_infer_hypothesis_category()` for automatic categorization
- Connected hypothesis creation, evidence linking, and anchoring prevention
- Investigation framework now at 100% engine integration (5/5 engines)

**Files Changed**:
- `src/faultmaven/modules/case/engines/milestone_engine.py` - Full HypothesisManager integration

---

### Case Search & Filter

**Status**: ✅ RESOLVED (2025-12-27)

**Implementation**:
- Added `search_cases()` method to CaseService with multi-criteria filtering
- Added `get_case_statistics()` for aggregate statistics
- Added `POST /cases/search` endpoint with CaseSearchRequest schema
- Added `GET /cases/statistics` endpoint
- Supports: text search, status/priority/category filters, date range, pagination

**Files Changed**:
- `src/faultmaven/modules/case/service.py` - Added search_cases, get_case_statistics
- `src/faultmaven/modules/case/router.py` - Added search and statistics endpoints

---

### Session Advanced Features

**Status**: ✅ RESOLVED (2025-12-27)

**Implementation**:
- Added `get_aggregate_statistics()` method to SessionService
- Added `search_sessions_advanced()` with multiple filter criteria
- Added `GET /sessions/statistics` endpoint for aggregate stats
- Enhanced `POST /sessions/search` with advanced filtering

**Files Changed**:
- `src/faultmaven/modules/session/service.py` - Added statistics and advanced search
- `src/faultmaven/modules/session/router.py` - Added statistics endpoint, enhanced search

---

### Report Generation

**Status**: ✅ ALREADY IMPLEMENTED (discovered 2025-12-27)

**Note**: This was incorrectly marked as "Not implemented" in the original document.

**Existing Implementation**:
- Full ReportService with template-based and LLM-based generation
- Three report types: Incident Report, Runbook, Post-Mortem
- Version management (max 5 versions per type)
- Markdown export with download endpoint
- Report recommendations based on case status

**Files**:
- `src/faultmaven/modules/report/service.py` - Complete implementation (634 lines)
- `src/faultmaven/modules/report/router.py` - Full API endpoints (331 lines)

---

## Critical Gaps 🔴

### 1. Data Processing Pipeline

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

**Reference**: FaultMaven-Mono `faultmaven/core/preprocessing/`

---

### 2. Agent Tools Framework

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

**Note**: Structured LLM output (required dependency) is now implemented.

**Estimated Effort**: 4 weeks
- Week 1: Tool execution framework + sandboxing
- Week 2: 4 tools (Command, File operations)
- Week 3: 3 tools (Network, HTTP, Database)
- Week 4: Permission system + audit logging

**Priority**: 🔴 CRITICAL - Core agent capability

---

## Low Priority Gaps 🟢

### 3. Knowledge Base Advanced Features

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

### 4. OAuth/SAML Authentication

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
| Session | 100% | 100% | ✅ Complete |
| Case (Basic) | 100% | 100% | ✅ Complete |
| Case (Framework) | 100% | 100% | ✅ Complete (5/5 engines) |
| Evidence (Upload) | 100% | 100% | ✅ Complete |
| Evidence (Processing) | 100% | 0% | ❌ Critical gap |
| Knowledge (Core) | 100% | 100% | ✅ Complete |
| Knowledge (Advanced) | 100% | 10% | 🟢 Optional features |
| Agent (Chat) | 100% | 100% | ✅ Complete |
| Agent (Tools) | 100% | 12.5% | ❌ Critical gap (1/8 tools) |
| Report | 100% | 100% | ✅ Complete |

### By Priority

| Priority | Count | Total Effort | Impact |
|----------|-------|--------------|--------|
| 🔴 Critical | 2 | 7 weeks | Blocks core features |
| 🟢 Low | 2 | 4 weeks | Optional enhancements |
| **Total** | **4** | **11 weeks** | |

---

## Resolved Items Summary

| Item | Resolution Date | Effort Saved |
|------|-----------------|--------------|
| Structured LLM Output | 2025-12-27 | 2 weeks |
| HypothesisManager Integration | 2025-12-27 | 1 week |
| Case Search & Filter | 2025-12-27 | 1 week |
| Session Advanced Features | 2025-12-27 | 3 days |
| Report Generation | Already implemented | 1 week |

**Total Effort Saved**: ~5.5 weeks

---

## Implementation Roadmap (Updated)

### Phase 1: Critical Gaps (7 weeks)

**Priority**: Unblock core features

1. **Data Processing Pipeline** (3 weeks) - Core evidence processing
   - Implement 11 data extractors
   - Add data type detection
   - Integrate with knowledge base

2. **Agent Tools Framework** (4 weeks) - Agent capabilities
   - Build tool execution framework
   - Implement 8+ required tools
   - Add sandboxing and permissions

**Deliverables**: Full evidence processing, autonomous agent

---

### Phase 2: Enhancements (4 weeks) - Optional

**Priority**: Advanced features, not MVP

3. **Knowledge Base Advanced** (2 weeks)
   - Document versioning
   - Knowledge graph
   - Smart indexing

4. **OAuth/SAML** (2 weeks)
   - Enterprise authentication
   - Identity provider integration

**Deliverables**: Enterprise-ready features

---

## Decision Points

### Recommended Path Forward

**Option A: Critical Only** (7 weeks) ✅ RECOMMENDED
- Implement Data Processing Pipeline and Agent Tools Framework
- Achieves full troubleshooting capability
- Total effort: 7 weeks

**Option B: Full Implementation** (11 weeks)
- Add Phase 2 enhancements
- Enterprise-ready features
- Total effort: 11 weeks

---

## Tracking

### Completed Issues

- ~~**Issue #5**: HypothesisManager integration~~ ✅ RESOLVED
- ~~Structured LLM Output~~ ✅ RESOLVED
- ~~Case Search & Filter~~ ✅ RESOLVED
- ~~Session Features~~ ✅ RESOLVED

### Remaining Work

- Data Processing Pipeline
- Agent Tools Framework
- Knowledge Base Advanced (optional)
- OAuth/SAML (optional)

---

## Related Documents

**Design Specification**: [architecture/design-specifications.md](architecture/design-specifications.md)

**Architecture**: [architecture/](architecture/)

---

**Last Updated**: 2025-12-27
**Next Review**: After Phase 1 completion
**Total Estimated Effort**: 11 weeks (all gaps), 7 weeks (critical only)
