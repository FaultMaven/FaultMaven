# Architecture Documentation

**Complete architectural documentation for the FaultMaven modular monolith.**

This folder contains all architecture and design documents. For implementation gaps, see [../TECHNICAL_DEBT.md](../TECHNICAL_DEBT.md).

---

## 📐 Architecture Documents

### [design-specifications.md](design-specifications.md) - **What to Build**

**Purpose**: Defines the **target design** (desired state) for FaultMaven

**Contains**:

- Module specifications (6 modules: auth, session, case, evidence, knowledge, agent)
- API endpoint definitions
- Required capabilities for each module
- Infrastructure design (LLM providers, databases, vector stores)
- Deployment profiles (Core/Team/Enterprise)
- Performance requirements
- Security requirements
- **Implementation Status** section (summary of what's implemented vs. what's not)

**Use this when**: You need to understand what the system SHOULD do and what features are required

---

### [overview.md](overview.md) - **How It's Built**

**Purpose**: Describes the **current architecture** (how it's structured)

**Contains**:

- System architecture diagrams
- Architecture principles (modular monolith, vertical slices, provider abstraction)
- Module structure and file organization
- Shared infrastructure layer
- Data flow examples
- Configuration details
- Performance characteristics
- Migration history

**Use this when**: You need to understand how the system IS built and how components interact

---

### [modular-monolith-rationale.md](modular-monolith-rationale.md) - **Why This Design**

**Purpose**: Explains design decisions and architectural patterns

**Contains**:

- Why modular monolith vs. microservices
- Trade-offs and benefits
- Design patterns used
- Module boundary principles

**Use this when**: You need to understand the reasoning behind architectural decisions

---

## 🗺️ Quick Navigation

### "I want to understand..."

**...what features the system should have**
→ Read [design-specifications.md](design-specifications.md)

**...how the system is structured**
→ Read [overview.md](overview.md)

**...why we chose this architecture**
→ Read [modular-monolith-rationale.md](modular-monolith-rationale.md)

**...what's not yet implemented**
→ Read [../TECHNICAL_DEBT.md](../TECHNICAL_DEBT.md)

---

## 📊 Key Differences

| Document | Focus | Perspective | Content Type |
| -------- | ----- | ----------- | ------------ |
| **design-specifications.md** | Requirements | Should/Must | Specifications, API contracts, requirements |
| **overview.md** | Implementation | Is/How | Architecture diagrams, patterns, structure |
| **modular-monolith-rationale.md** | Decisions | Why | Rationale, trade-offs, principles |

---

## 🔄 Relationship Between Documents

```
design-specifications.md (WHAT to build)
         ↓
    Guides design
         ↓
overview.md (HOW it's built)
         ↓
    Implementation
         ↓
TECHNICAL_DEBT.md (WHAT's missing)
```

**Example workflow**:

1. Read **design-specifications.md** to understand what the Evidence module SHOULD do
2. Read **overview.md** to understand how the Evidence module IS currently structured
3. Read **TECHNICAL_DEBT.md** to see what's missing (e.g., data processing pipeline at 0%)

---

## 📝 Module-Specific Documentation

Future: This folder may contain module-specific design documents:

- `auth.md` - Authentication module design
- `case.md` - Case/investigation module design
- `agent.md` - AI agent module design
- etc.

---

**Last Updated**: 2025-12-27
**Architecture**: Modular Monolith
**Status**: Production Ready (with known gaps in [../TECHNICAL_DEBT.md](../TECHNICAL_DEBT.md))
