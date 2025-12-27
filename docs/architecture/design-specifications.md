# FaultMaven System Design

**Version**: 1.0
**Last Updated**: 2025-12-26
**Status**: Design of Record

---

## Purpose

This document defines the **target design** (desired state) for FaultMaven's modular monolith architecture. It describes what the system SHOULD do, not what has been implemented.

**Implementation status** is tracked separately in [../TECHNICAL_DEBT.md](../TECHNICAL_DEBT.md).

---

## Architecture Overview

### Design Principle: Modular Monolith

**Desired State**: Single deployable unit with clear module boundaries

- 6 domain modules with vertical slice architecture
- Shared infrastructure layer (providers)
- Single database with module-owned tables
- Single deployment artifact (Docker container)

**Benefits**:
- Simplified deployment and operations
- Easier development and testing
- Clear module boundaries without distributed systems complexity
- Better developer experience

---

## Module Specifications

### 1. Authentication Module

**Purpose**: User authentication and authorization

**Required Capabilities**:
- User registration with email/password
- Secure login with JWT tokens
- Token refresh mechanism
- User profile management
- Password reset workflow
- Role-based access control (RBAC)

**API Endpoints**:
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `POST /auth/refresh` - Token refresh
- `GET /auth/me` - Current user profile
- `POST /auth/reset-password` - Password reset request
- `PUT /auth/password` - Update password

**Security Requirements**:
- bcrypt password hashing (cost factor 12)
- JWT with HS256 algorithm
- Token expiration (access: 30min, refresh: 7 days)
- Rate limiting on auth endpoints

---

### 2. Session Module

**Purpose**: Multi-session management with device continuity

**Required Capabilities**:
- Multiple concurrent sessions per user
- Client-based session resumption (device continuity)
- Session timeout with configurable TTL (60-480 minutes)
- Heartbeat tracking for active sessions
- Session cleanup for expired sessions
- Session recovery information

**API Endpoints**:
- `POST /sessions` - Create session (with client_id for resumption)
- `GET /sessions/{session_id}` - Get session details
- `PATCH /sessions/{session_id}` - Update session
- `DELETE /sessions/{session_id}` - Delete session
- `GET /sessions` - List user sessions
- `POST /sessions/{session_id}/heartbeat` - Update session activity
- `POST /sessions/{session_id}/cleanup` - Cleanup session data

**Data Storage**:
- Redis for active sessions (TTL-based expiration)
- Session metadata: user_id, client_id, created_at, last_activity, ttl

**Design Requirement**: Sessions must survive backend restarts via Redis persistence

---

### 3. Case Module

**Purpose**: Investigation lifecycle management with AI framework

**Required Capabilities**:
- Case CRUD operations
- Investigation state tracking (consulting, diagnosing, analyzing, resolved, closed)
- Message history with role-based messages (user, assistant, system)
- Hypothesis management with lifecycle tracking
- Solution tracking and validation
- Report generation (PDF, Markdown)
- Case search and filtering
- Case analytics and statistics

**API Endpoints**:
- `POST /cases` - Create case
- `GET /cases/{case_id}` - Get case details
- `PATCH /cases/{case_id}` - Update case
- `DELETE /cases/{case_id}` - Delete case
- `POST /cases/{case_id}/messages` - Add message
- `GET /cases/{case_id}/messages` - Get message history
- `POST /cases/{case_id}/hypotheses` - Add hypothesis
- `GET /cases/{case_id}/hypotheses` - List hypotheses
- `PATCH /cases/{case_id}/hypotheses/{hypothesis_id}` - Update hypothesis
- `POST /cases/{case_id}/solutions` - Propose solution
- `GET /cases/{case_id}/report` - Generate report
- `POST /cases/search` - Search cases

**Investigation Framework** (5 engines):

#### 3.1 MemoryManager

**Purpose**: Hierarchical memory management for token optimization

**Design**:
- 3-tier memory: Hot (recent), Warm (relevant), Cold (archive)
- Hot memory: Last N messages (configurable, default 10)
- Warm memory: Semantically relevant messages (retrieved via similarity)
- Cold memory: Archived older messages (not sent to LLM)
- Automatic promotion/demotion based on relevance
- 64% token reduction target (4500 → 1600 tokens)

**Algorithm**:
```python
def organize_memory(messages, context_window=8000):
    # Hot: Recent messages (always included)
    hot = messages[-10:]

    # Warm: Semantically similar to current context
    warm = retrieve_similar(messages[:-10], current_query, top_k=5)

    # Cold: Remaining messages (excluded from LLM input)
    cold = [m for m in messages if m not in hot and m not in warm]

    return {"hot": hot, "warm": warm, "cold": cold}
```

#### 3.2 WorkingConclusionGenerator

**Purpose**: Continuous progress tracking and intermediate conclusions

**Design**:
- Generate working conclusions after each turn
- Track confidence levels (low, medium, high)
- Update conclusions as new evidence emerges
- Provide investigation progress visibility

**Output Schema**:
```python
{
    "conclusion": str,           # Current understanding
    "confidence": str,           # low | medium | high
    "supporting_evidence": List[str],
    "next_steps": List[str],
    "updated_at": datetime
}
```

#### 3.3 PhaseOrchestrator

**Purpose**: Intelligent phase progression with loop-back detection

**Design**:
- 4 investigation phases: Consulting, Diagnosing, Analyzing, Resolved
- Automatic phase transitions based on investigation state
- Loop-back detection to prevent infinite cycles
- Configurable max iterations per phase (default: 5)

**Phase Transition Rules**:
- Consulting → Diagnosing: Initial problem understanding complete
- Diagnosing → Analyzing: Root cause identified
- Analyzing → Resolved: Solution validated
- Any → Previous phase: New evidence contradicts current understanding (loop-back)

**Loop-back Detection**:
```python
def detect_loopback(phase_history, max_loops=3):
    # Detect if same phase appears > max_loops times
    phase_counts = Counter(phase_history[-10:])
    return any(count > max_loops for count in phase_counts.values())
```

#### 3.4 OODAEngine

**Purpose**: Adaptive investigation intensity

**Design**:
- 3 intensity levels: Light, Medium, Full
- Automatic intensity adjustment based on:
  - Case complexity
  - Number of failed hypotheses
  - Time spent in current phase
  - Evidence volume

**Intensity Levels**:
- **Light**: Quick triage, basic diagnostics (1-2 LLM calls)
- **Medium**: Standard investigation (3-5 LLM calls)
- **Full**: Deep analysis with all tools (5+ LLM calls)

#### 3.5 HypothesisManager

**Purpose**: Hypothesis lifecycle management

**Design Requirements**:
- **Requires**: Structured LLM output (JSON mode or function calling)
- Automatic hypothesis extraction from LLM responses
- Hypothesis states: Proposed, Testing, Validated, Rejected
- Confidence scoring (0.0-1.0)
- Supporting/contradicting evidence tracking

**Hypothesis Schema**:
```python
{
    "hypothesis": str,
    "state": str,              # proposed | testing | validated | rejected
    "confidence": float,       # 0.0 - 1.0
    "supporting_evidence": List[str],
    "contradicting_evidence": List[str],
    "created_at": datetime,
    "updated_at": datetime
}
```

**Architectural Requirement**: LLM provider must support structured output parsing

---

### 4. Evidence Module

**Purpose**: File upload and evidence management with data processing

**Required Capabilities**:
- File upload (logs, configs, screenshots, traces, metrics)
- File download and retrieval
- Evidence metadata tracking
- Evidence-case association
- **Data processing pipeline** (8 data types)
- Multi-file analysis and correlation
- Evidence timeline visualization

**API Endpoints**:
- `POST /evidence/upload` - Upload evidence file
- `GET /evidence/{evidence_id}` - Get evidence metadata
- `GET /evidence/{evidence_id}/download` - Download file
- `DELETE /evidence/{evidence_id}` - Delete evidence
- `GET /cases/{case_id}/evidence` - List case evidence
- `POST /evidence/{evidence_id}/process` - Trigger data processing

**Data Processing Pipeline** (Required):

#### 4.1 Data Type Detection
Automatic detection of 8 data types:
1. **Logs** - Application/system logs
2. **Configs** - Configuration files (YAML, JSON, TOML, ENV)
3. **Traces** - Distributed traces (Jaeger, Zipkin)
4. **Metrics** - Time-series metrics (Prometheus, CloudWatch)
5. **Profiles** - Performance profiles (CPU, memory)
6. **Code** - Source code snippets
7. **Text** - Documentation, runbooks
8. **Visual** - Screenshots, diagrams

#### 4.2 Data Extractors (11 Required)

**Design Requirement**: One extractor per common format

1. **LogExtractor** - Structured log parsing (JSON, syslog, common formats)
2. **YAMLConfigExtractor** - YAML configuration parsing
3. **JSONConfigExtractor** - JSON configuration parsing
4. **TOMLConfigExtractor** - TOML configuration parsing
5. **ENVConfigExtractor** - Environment variable parsing
6. **TraceExtractor** - Distributed trace parsing
7. **MetricExtractor** - Metrics time-series extraction
8. **CodeExtractor** - Source code analysis (syntax, imports)
9. **MarkdownExtractor** - Markdown document parsing
10. **ImageExtractor** - OCR and image analysis
11. **GenericTextExtractor** - Fallback plain text extraction

**Extractor Interface**:
```python
class DataExtractor(Protocol):
    def detect(self, file_path: Path) -> bool:
        """Detect if this extractor can process the file"""
        ...

    def extract(self, file_path: Path) -> Dict[str, Any]:
        """Extract structured data from file"""
        ...

    def enrich(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add metadata and context"""
        ...
```

#### 4.3 Data Transformation
- Normalize extracted data to common schema
- Enrich with metadata (timestamps, sources, context)
- Index for searchability
- Store in knowledge base for RAG retrieval

**Design Goal**: Agent can query "show me errors from the last hour" and get structured results

---

### 5. Knowledge Module

**Purpose**: Knowledge base with semantic search (RAG)

**Required Capabilities**:
- Document ingestion and embedding
- Semantic search via vector similarity
- 3-tier knowledge collections:
  - **User KB**: Personal runbooks and documentation
  - **Global KB**: System-wide troubleshooting guides
  - **Case KB**: Case-specific knowledge (auto-cleanup on case close)
- Document versioning
- Knowledge graph relationships
- Smart indexing and auto-tagging

**API Endpoints**:
- `POST /knowledge/documents` - Ingest document
- `POST /knowledge/search` - Semantic search
- `GET /knowledge/documents` - List documents
- `GET /knowledge/documents/{doc_id}` - Get document
- `DELETE /knowledge/documents/{doc_id}` - Delete document
- `GET /knowledge/documents/{doc_id}/versions` - Document versions
- `POST /knowledge/documents/{doc_id}/tag` - Add tag

**Embedding Model**: BGE-M3 (multilingual, multi-granularity)

**Vector Store**: ChromaDB (dev), Pinecone (production scale)

**Advanced Features**:
- Document versioning with diff tracking
- Knowledge graph for concept relationships
- Smart indexing based on content type
- Auto-tagging with LLM-generated tags

---

### 6. Agent Module

**Purpose**: AI agent orchestration with tool execution

**Required Capabilities**:
- Multi-turn troubleshooting conversations
- Context-aware responses
- RAG integration (knowledge retrieval)
- Multi-provider LLM support (7 providers)
- **Agent tools framework** (8+ tools)
- Response type system (9 types)
- Streaming responses (optional)

**API Endpoints**:
- `POST /agent/chat/{case_id}` - Send message
- `GET /agent/health` - Health check
- `POST /agent/tools/execute` - Execute tool
- `GET /agent/tools` - List available tools

**Response Types** (9):
1. ANSWER - Direct answer
2. PLAN_PROPOSAL - Investigation plan
3. CLARIFICATION_REQUEST - Request more info
4. CONFIRMATION_REQUEST - Confirm action
5. SOLUTION_READY - Solution proposal
6. NEEDS_MORE_DATA - Request evidence
7. ESCALATION_REQUIRED - Human escalation
8. STATUS_UPDATE - Progress update
9. ERROR - Error handling

**Agent Tools Framework** (Required):

#### 6.1 Tool Categories

**System Commands** (3 tools):
1. **CommandExecutor** - Run safe system commands (read-only)
2. **ProcessInspector** - Inspect running processes
3. **NetworkAnalyzer** - Network diagnostics (ping, traceroute, DNS)

**File Operations** (2 tools):
4. **FileReader** - Read file contents (with size limits)
5. **FileSearcher** - Search files by pattern

**API Queries** (2 tools):
6. **HTTPClient** - Make HTTP requests to external APIs
7. **DatabaseQuery** - Query databases (read-only, parameterized)

**Knowledge Retrieval** (1 tool):
8. **KnowledgeSearch** - Semantic search in knowledge base

**Tool Interface**:
```python
class AgentTool(Protocol):
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON schema

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters"""
        ...

    def validate(self, **kwargs) -> bool:
        """Validate parameters before execution"""
        ...
```

**Safety Requirements**:
- Sandboxed execution environment
- Tool permission system (per-user/per-case)
- Audit logging of all tool executions
- Timeout limits (default: 30s)
- Output size limits (default: 10MB)

**Architectural Requirement**: LLM provider must support function calling

---

## Infrastructure Design

### Provider Abstraction Layer

**Purpose**: Abstract infrastructure dependencies behind interfaces

**Providers Required**:

1. **LLMProvider** - Multi-provider LLM routing
   - Support for: OpenAI, Anthropic, Fireworks, Google, HuggingFace, OpenRouter, Ollama
   - Automatic fallback on provider failure
   - **Structured output support** (JSON mode or function calling)
   - Streaming support (optional)

2. **DataProvider** - Database abstraction
   - SQLite (development)
   - PostgreSQL (production)
   - Async ORM (SQLAlchemy)

3. **FileProvider** - File storage abstraction
   - Local filesystem (development)
   - S3 (production)
   - Size limits and validation

4. **VectorProvider** - Vector store abstraction
   - ChromaDB (development)
   - Pinecone (production scale)
   - Embedding model integration

5. **CacheProvider** - Caching layer
   - Redis (sessions, short-term cache)
   - In-memory fallback (development)

---

## Deployment Profiles

### Core Profile (Development)
- SQLite database
- Local file storage
- In-memory session fallback
- ChromaDB (local)
- Single container deployment

### Team Profile (Small teams)
- PostgreSQL database
- Shared Redis for sessions
- ChromaDB (shared)
- Docker Compose deployment

### Enterprise Profile (Production)
- PostgreSQL HA cluster
- Redis cluster
- S3 file storage
- Pinecone vector store
- Kubernetes deployment
- OAuth/SAML authentication

---

## Performance Requirements

### Token Efficiency
- **Target**: 64% reduction in LLM token usage
- **Baseline**: 4,500 tokens per investigation turn (no memory management)
- **Target**: ~1,600 tokens per turn (with MemoryManager)

### Response Times (p95)
- Chat endpoint: <2s
- Knowledge search: <500ms
- Session operations: <100ms
- File upload: <3s (10MB file)

### Scalability
- Single process: 100-500 req/s
- Horizontal scaling: Load balancer + multiple backend processes
- Database connection pooling (10-50 connections)

---

## Security Requirements

1. **Authentication**:
   - bcrypt password hashing (cost 12)
   - JWT with short expiration (30 min access, 7 day refresh)
   - Secure token storage (httpOnly cookies or Authorization header)

2. **Authorization**:
   - Role-based access control (user, admin)
   - Resource ownership validation
   - API rate limiting (100 req/min per user)

3. **Data Protection**:
   - TLS 1.3 for all connections
   - Encrypted sensitive data at rest
   - No credentials in logs
   - PII redaction in evidence uploads

4. **Tool Execution**:
   - Sandboxed execution environment
   - Tool permission system
   - Audit logging
   - Timeout and output limits

---

## Implementation Status

This section tracks which parts of the design are implemented and which are not.

**For complete gap details, effort estimates, and roadmap**: See [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md)

### Module Implementation Summary

**Authentication**: ✅ Complete (core), N/A (advanced) - Fully implemented

**Session**: ✅ Complete (core), ⚠️ 95% (advanced) - Minor features missing ([#7](TECHNICAL_DEBT.md#7))

**Case**: ✅ 90% (core), ⚠️ 75% (advanced) - Report generation, search missing ([#5-6](TECHNICAL_DEBT.md#5-6))

**Evidence**: ✅ Complete (core), ❌ 0% (advanced) - **Data processing pipeline missing** ([#2](TECHNICAL_DEBT.md#2))

**Knowledge**: ✅ Complete (core), ⚠️ 10% (advanced) - Advanced features missing ([#8](TECHNICAL_DEBT.md#8))

**Agent**: ✅ Complete (core), ❌ 12.5% (advanced) - **Tools framework missing** ([#3](TECHNICAL_DEBT.md#3))

### Investigation Framework (80% Complete)

**MemoryManager**: ✅ Complete

**WorkingConclusionGenerator**: ✅ Complete

**PhaseOrchestrator**: ✅ Complete

**OODAEngine**: ✅ Complete

**HypothesisManager**: ❌ Not integrated - **Blocked by structured LLM output** ([#1](TECHNICAL_DEBT.md#1))

### Critical Missing Components

**🔴 These gaps block core functionality:**

1. **Structured LLM Output Support** ([#1](TECHNICAL_DEBT.md#1))
   - Blocks: HypothesisManager integration, Agent Tools framework
   - Effort: 2 weeks

2. **Data Processing Pipeline** ([#2](TECHNICAL_DEBT.md#2))
   - Gap: 11 data extractors missing (0% coverage)
   - Impact: Evidence files uploaded but not processed
   - Effort: 3 weeks

3. **Agent Tools Framework** ([#3](TECHNICAL_DEBT.md#3))
   - Gap: 7 of 8 tools missing (12.5% coverage)
   - Impact: Agent cannot execute troubleshooting actions
   - Effort: 4 weeks

4. **HypothesisManager Integration** ([#4](TECHNICAL_DEBT.md#4))
   - Gap: Code exists but not activated
   - Blocks: Investigation framework completion (stuck at 80%)
   - Effort: 1 week

**Total effort to close critical gaps**: 10 weeks

**See [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md) for**:
- Detailed gap descriptions
- Implementation roadmap
- Effort breakdown
- Priority levels
- Code size analysis

---

## Related Documents

**Implementation Gaps**: [../TECHNICAL_DEBT.md](../TECHNICAL_DEBT.md) - What's not yet implemented

**Architecture Overview**: [overview.md](overview.md) - System architecture and diagrams

**Development Guide**: [../development/setup.md](../development/setup.md) - How to build and run

---

**Last Updated**: 2025-12-27
**Version**: 1.0
**Status**: Design of Record
