# FaultMaven PR #27 - Architecture Diagrams

## 1. Provider Abstraction Enhancement

### Before PR #27

```mermaid
graph TB
    subgraph "LLM Provider Interface (Before)"
        A[LLMProvider Protocol] --> B[chat method]
        B --> C[messages: List]
        B --> D[model: str]
        B --> E[temperature: float]
        B --> F[**kwargs]
    end

    subgraph "Response"
        G[ChatResponse] --> H[content: str]
        G --> I[usage: dict]
        G --> J[tool_calls: Optional]
    end

    A --> G
```

### After PR #27 (Enhanced)

```mermaid
graph TB
    subgraph "LLM Provider Interface (After)"
        A[LLMProvider Protocol] --> B[chat method]
        B --> C[messages: List]
        B --> D[model: str]
        B --> E[temperature: float]
        B --> F[tools: Optional[List[ToolDefinition]]]
        B --> G[response_format: Optional[ResponseFormat]]
        B --> H[**kwargs]
    end

    subgraph "New Classes"
        I[ToolDefinition] --> J[name: str]
        I --> K[description: str]
        I --> L[parameters: dict]
        I --> M[to_openai_format]

        N[ResponseFormat] --> O[type: str]
        N --> P[json_schema: Optional]
        N --> Q[to_openai_format]
    end

    subgraph "Enhanced Response"
        R[ChatResponse] --> S[content: str]
        R --> T[usage: dict]
        R --> U[tool_calls: Optional]
        R --> V[parsed: Optional[dict]]
    end

    F --> I
    G --> N
    A --> R

    style F fill:#90ee90
    style G fill:#90ee90
    style V fill:#90ee90
```

## 2. HypothesisManager Integration Flow

### Investigation Turn Processing

```mermaid
sequenceDiagram
    participant U as User
    participant R as Router
    participant MS as MilestoneEngine
    participant EX as _extract_investigation_updates
    participant HM as HypothesisManager
    participant LLM as LLM Provider

    U->>R: POST /cases/{id}/messages
    R->>MS: process_turn()
    MS->>LLM: chat(messages)
    LLM-->>MS: llm_response

    MS->>EX: _extract_investigation_updates(llm_response)

    Note over EX: Tier 1: Try structured JSON
    EX->>EX: regex search for ```json blocks
    alt JSON found
        EX->>EX: json.loads()
        EX-->>MS: structured result
    else No JSON
        Note over EX: Tier 2: Keyword extraction
        EX->>EX: keyword search (symptom, root cause, etc)
        EX-->>MS: keyword result
    end

    MS->>HM: create_hypothesis(statement, category, likelihood)
    HM-->>MS: HypothesisModel

    MS->>HM: link_evidence(hypothesis, evidence_id, supports)
    HM-->>MS: updated hypothesis

    MS->>HM: detect_anchoring(hypotheses, iteration)
    alt Anchoring detected
        HM->>HM: force_alternative_generation()
    end

    MS-->>R: updated InvestigationState
    R-->>U: 200 OK
```

## 3. Three-Tier Response Parsing Strategy

```mermaid
flowchart TD
    A[LLM Response] --> B{Contains ```json block?}

    B -->|Yes| C[Extract JSON content]
    C --> D{Valid JSON?}
    D -->|Yes| E[Parse structured data]
    E --> F[Extract milestones]
    F --> G[Extract hypotheses]
    G --> H[Extract hypothesis_updates]
    H --> Z[Return structured result]

    D -->|No JSONDecodeError| I[Fall through to Tier 2]
    B -->|No| I

    I --> J[Keyword-based extraction]
    J --> K{Contains 'symptom'?}
    K -->|Yes| L[symptom_verified = True]
    K -->|No| M{Contains 'root cause'?}
    M -->|Yes| N[root_cause_identified = True]
    M -->|No| O{Contains 'solution'?}
    O -->|Yes| P[solution_proposed = True]
    O -->|No| Q[No milestones detected]

    L --> R[Check additional patterns]
    N --> R
    P --> R
    Q --> R

    R --> S[Check scope keywords]
    R --> T[Check timeline keywords]
    R --> U[Check changes keywords]

    S --> V[Extract hypotheses via regex]
    T --> V
    U --> V

    V --> Z

    style E fill:#90ee90
    style Z fill:#ffd700
    style J fill:#87ceeb
```

## 4. Module Impact Map

```mermaid
graph TD
    subgraph "Infrastructure Layer (Core Changes)"
        P1[providers/interfaces.py<br/>+57 lines] --> P2[providers/core.py<br/>+51 lines]
        P1 -.implements.-> P2
    end

    subgraph "Case Module (Major Enhancement)"
        C1[case/engines/milestone_engine.py<br/>+222 lines]
        C2[case/service.py<br/>+144 lines]
        C3[case/router.py<br/>+102 lines]

        C1 --> C2
        C2 --> C3
    end

    subgraph "Session Module (New Features)"
        S1[session/service.py<br/>+170 lines]
        S2[session/router.py<br/>+54 lines]

        S1 --> S2
    end

    subgraph "Tests"
        T1[test_error_handling.py<br/>+28/-9 lines]
    end

    P2 -.used by.-> C1
    C1 -.orchestrates.-> HM[HypothesisManager<br/>existing]

    style P1 fill:#ffd700
    style P2 fill:#ffd700
    style C1 fill:#90ee90
    style C2 fill:#ffcccb
    style C3 fill:#ffcccb
    style S1 fill:#ffcccb
    style S2 fill:#ffcccb
    style T1 fill:#87ceeb

    classDef complete fill:#90ee90,stroke:#333,stroke-width:2px
    classDef incomplete fill:#ffcccb,stroke:#333,stroke-width:2px
    classDef infrastructure fill:#ffd700,stroke:#333,stroke-width:2px
```

**Legend**:
- 🟡 Gold: Infrastructure changes (complete, ready to merge)
- 🟢 Green: Complete implementation (ready to merge)
- 🔴 Red: Incomplete/stub implementation (needs work)
- 🔵 Blue: Test changes

## 5. Search Implementation: Current vs Required

### Current (In-Memory Filtering) ❌

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router
    participant S as CaseService
    participant DB as Database

    C->>R: POST /cases/search {status: "investigating"}
    R->>S: list_cases(user_id)
    S->>DB: SELECT * FROM cases WHERE owner_id = ?
    Note over DB: Loads ALL cases for user

    DB-->>S: [case1, case2, ..., case1000]
    S-->>R: [all 1000 cases]

    Note over R: Python in-memory filter
    R->>R: [c for c in cases if c.status == "investigating"]

    R-->>C: {"cases": [filtered], "count": 50}

    Note over R,DB: Problem: Loaded 1000, returned 50<br/>Memory: O(n), Time: O(n)
```

### Required (Database-Level Filtering) ✅

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router
    participant S as CaseService
    participant DB as Database

    C->>R: POST /cases/search {status: "investigating"}
    R->>R: Validate with CaseSearchRequest
    R->>S: search_cases(user_id, status="investigating", limit=20, offset=0)

    Note over S: Build SQL WHERE clause
    S->>S: query = SELECT ... WHERE owner_id = ? AND status = ?

    S->>DB: Execute query with LIMIT 20 OFFSET 0
    Note over DB: Database filters and paginates

    DB-->>S: [case1, case2, ..., case20]

    S->>DB: SELECT COUNT(*) WHERE owner_id = ? AND status = ?
    DB-->>S: total = 50

    S-->>R: (cases=[20 cases], total=50)
    R-->>C: {"cases": [20 cases], "total": 50, "limit": 20, "offset": 0}

    Note over R,DB: Efficient: Only loaded 20 cases<br/>Memory: O(limit), Time: O(log n) with indexes
```

## 6. Hypothesis Lifecycle Integration

```mermaid
stateDiagram-v2
    [*] --> CAPTURED: Opportunistic hypothesis<br/>(from keyword extraction)

    CAPTURED --> ACTIVE: Promoted for testing

    [*] --> ACTIVE: Systematic generation<br/>(from structured JSON)

    ACTIVE --> VALIDATED: Evidence supports<br/>(confidence ≥ 70%,<br/>≥2 supporting evidence)

    ACTIVE --> REFUTED: Evidence refutes<br/>(confidence ≤ 20%,<br/>≥2 refuting evidence)

    ACTIVE --> RETIRED: Low confidence<br/>or anchoring detected

    ACTIVE --> SUPERSEDED: Better hypothesis found

    VALIDATED --> [*]: Root cause confirmed

    REFUTED --> [*]: Hypothesis disproved

    RETIRED --> [*]: Abandoned

    SUPERSEDED --> [*]: Replaced

    note right of ACTIVE
        HypothesisManager tracks:
        - Confidence trajectory
        - Evidence links (support/refute)
        - Testing iterations
        - Anchoring signals
    end note

    note right of CAPTURED
        NEW: Extracted from LLM
        response via keyword
        or structured output
    end note
```

## 7. Anchoring Detection & Prevention

```mermaid
flowchart TD
    A[Check Hypotheses] --> B{4+ hypotheses in<br/>same category?}
    B -->|Yes| C[ANCHORING DETECTED:<br/>Category clustering]
    B -->|No| D{3+ iterations<br/>without progress?}

    D -->|Yes| E[ANCHORING DETECTED:<br/>Stagnation]
    D -->|No| F{Top hypothesis<br/>stagnant 3+ iterations?}

    F -->|Yes| G[ANCHORING DETECTED:<br/>Confirmation bias]
    F -->|No| H[No anchoring]

    C --> I[Mitigation Strategy]
    E --> I
    G --> I

    I --> J[Retire low-progress hypotheses]
    I --> K[Force alternative generation]
    I --> L[Prompt LLM for diverse categories]
    I --> M[Apply confidence decay]

    J --> N[Continue investigation]
    K --> N
    L --> N
    M --> N

    H --> N

    style C fill:#ff6b6b
    style E fill:#ff6b6b
    style G fill:#ff6b6b
    style I fill:#ffd93d
    style N fill:#90ee90
```

## 8. Data Flow: Structured Output to Hypothesis

```mermaid
graph LR
    subgraph "LLM Response"
        A[```json<br/>{<br/> 'hypotheses': [<br/>  {<br/>   'statement': 'DB pool exhausted',<br/>   'category': 'database',<br/>   'likelihood': 0.8<br/>  }<br/> ]<br/>}```]
    end

    subgraph "Extraction"
        B[_extract_investigation_updates]
        B --> C[Regex: r'```json\s*[\s\S]*?\s*```']
        C --> D[json.loads]
        D --> E[Extract 'hypotheses' array]
    end

    subgraph "Processing"
        E --> F[For each hypothesis dict]
        F --> G[HypothesisManager.create_hypothesis]
        G --> H[HypothesisModel]
        H --> I[Append to inv_state.hypotheses]
    end

    subgraph "InvestigationState"
        I --> J[hypotheses: List[HypothesisModel]]
        J --> K[hypothesis_id: hyp_abc123]
        K --> L[statement: 'DB pool exhausted']
        K --> M[category: 'database']
        K --> N[likelihood: 0.8]
        K --> O[status: ACTIVE]
        K --> P[confidence_trajectory: [(1, 0.8)]]
    end

    A --> B

    style A fill:#e3f2fd
    style H fill:#90ee90
    style J fill:#fff9c4
```

## 9. Performance Comparison: Search Implementations

```mermaid
graph TB
    subgraph "Current Implementation (In-Memory)"
        A1[Load ALL cases] --> A2[1000 rows fetched]
        A2 --> A3[Transfer to Python: 10MB]
        A3 --> A4[Python filter loop: 50ms]
        A4 --> A5[Return 20 filtered]
        A5 --> A6[Total: 500ms, 10MB RAM]
    end

    subgraph "Required Implementation (SQL WHERE)"
        B1[SQL with WHERE + LIMIT] --> B2[20 rows fetched]
        B2 --> B3[Transfer to Python: 200KB]
        B3 --> B4[Database indexed filter: 5ms]
        B4 --> B5[Return 20 filtered]
        B5 --> B6[Total: 15ms, 200KB RAM]
    end

    style A6 fill:#ff6b6b
    style B6 fill:#90ee90
```

**Performance at Scale**:

| Cases | In-Memory (Current) | SQL WHERE (Required) | Improvement |
|-------|---------------------|---------------------|-------------|
| 100 | 50ms / 1MB | 10ms / 100KB | 5x faster, 10x less RAM |
| 1,000 | 500ms / 10MB | 15ms / 100KB | 33x faster, 100x less RAM |
| 10,000 | 5s / 100MB | 30ms / 100KB | 167x faster, 1000x less RAM |
| 100,000 | ⚠️ OOM Kill | 100ms / 100KB | ∞ (prevents crash) |

## 10. Module Boundary Verification

```mermaid
graph TD
    subgraph "Auth Module"
        A1[auth/service.py]
        A2[auth/models.py]
    end

    subgraph "Case Module"
        C1[case/router.py]
        C2[case/service.py]
        C3[case/engines/milestone_engine.py]
        C4[case/engines/hypothesis_manager.py]

        C1 --> C2
        C2 --> C3
        C3 --> C4
    end

    subgraph "Session Module"
        S1[session/router.py]
        S2[session/service.py]
    end

    subgraph "Providers (Infrastructure)"
        P1[providers/interfaces.py]
        P2[providers/core.py]

        P1 -.Protocol.-> P2
    end

    C3 -.uses.-> P2
    C1 -.depends on.-> A1
    S1 -.depends on.-> A1

    style P1 fill:#ffd700
    style P2 fill:#ffd700
    style C3 fill:#90ee90
    style C4 fill:#90ee90
```

**Boundary Compliance**: ✅ PASS
- No cross-module implementation dependencies
- All dependencies go through interfaces (Protocol)
- Auth used only for JWT validation at router layer
- Providers used only by engines (proper layering)

---

## Summary

**Architecture Quality**: ✅ Excellent (provider abstraction, HypothesisManager)
**Implementation Status**: ⚠️ Partial (search/stats incomplete)
**Performance Risk**: 🔴 High (in-memory filtering)
**Security Risk**: 🟡 Medium (missing input validation)
**Test Coverage**: 🔴 Critical gap (0% for new code)

**Recommendation**: Split PR and complete search implementation with tests before merge.

