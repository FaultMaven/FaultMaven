# FaultMaven Documentation

**Central documentation index for the FaultMaven monolith.**

This guide helps you find the right documentation for your needs, organized by purpose and audience.

---

## 🚀 Getting Started

**New to FaultMaven? Start here:**

1. **[Main README](../README.md)** - Project overview, quick start, installation
2. **[DEVELOPMENT.md](DEVELOPMENT.md)** - Local development setup and workflow
3. **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide

---

## 📐 Architecture & Design

**Understanding FaultMaven's structure:**

| Document | Purpose | Audience |
|----------|---------|----------|
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | System architecture overview, modular monolith design | All developers |
| **[MODULAR_MONOLITH_DESIGN.md](MODULAR_MONOLITH_DESIGN.md)** | Detailed modular monolith rationale and patterns | Architects, senior developers |
| **[evaluation-modular-monolith-design.md](evaluation-modular-monolith-design.md)** | Design evaluation and decision rationale | Architects |

**Investigation Framework:**

| Document | Purpose |
|----------|---------|
| **[INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md](INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md)** | Integration status and framework overview |
| **[AUTO_WIRE_INVESTIGATION_DESIGN.md](AUTO_WIRE_INVESTIGATION_DESIGN.md)** | Auto-wire investigation design |
| **[INVESTIGATION_FRAMEWORK_DESIGN_AUDIT.md](INVESTIGATION_FRAMEWORK_DESIGN_AUDIT.md)** | Framework design audit |
| **[INVESTIGATION_FRAMEWORK_GAP_ANALYSIS.md](INVESTIGATION_FRAMEWORK_GAP_ANALYSIS.md)** | Gap analysis between implementations |

---

## 💻 Development

**Building and contributing to FaultMaven:**

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **[DEVELOPMENT.md](DEVELOPMENT.md)** | Complete development guide | Setting up local environment, adding features |
| **[TESTING_STRATEGY.md](TESTING_STRATEGY.md)** | Testing approach and patterns | Writing tests, understanding test coverage |
| **[TESTING_IMPLEMENTATION_ROADMAP.md](TESTING_IMPLEMENTATION_ROADMAP.md)** | Testing roadmap and future work | Planning test improvements |
| **[API Documentation](api/)** | Auto-generated OpenAPI specs | API integration, breaking change detection |

**Test Coverage Documentation:**

- [MILESTONE_ENGINE_TEST_COVERAGE.md](MILESTONE_ENGINE_TEST_COVERAGE.md)
- [HYPOTHESIS_MANAGER_TEST_COVERAGE.md](HYPOTHESIS_MANAGER_TEST_COVERAGE.md)
- [OODA_ENGINE_TEST_COVERAGE.md](OODA_ENGINE_TEST_COVERAGE.md)

---

## 🚢 Deployment & Operations

**Running FaultMaven in production:**

| Document | Purpose |
|----------|---------|
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | Production deployment guide (Docker, Kubernetes) |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Common issues and solutions |
| **[SECURITY.md](SECURITY.md)** | Security guidelines and best practices |

---

## 📚 Reference

**Deep dives and technical references:**

| Document | Purpose |
|----------|---------|
| **[FEATURE_PARITY_TRACKING.md](FEATURE_PARITY_TRACKING.md)** | 🔴 **Feature parity gaps** vs FaultMaven-Mono (CRITICAL) |
| **[FAQ.md](FAQ.md)** | Frequently asked questions |
| **[ROADMAP.md](ROADMAP.md)** | Product roadmap and future plans |
| **[ENGINE_INTEGRATION_STATUS.md](ENGINE_INTEGRATION_STATUS.md)** | Framework engine integration status |
| **[INTEGRATION_COMPLETION_SUMMARY.md](INTEGRATION_COMPLETION_SUMMARY.md)** | Integration completion summary |
| **[DESIGN_AUDIT_RESOLUTION.md](DESIGN_AUDIT_RESOLUTION.md)** | Design audit findings and resolutions |

---

## 🗂️ Historical Documentation

**Archived documentation from the microservices era and migration:**

Located in [archive/2025/12/](archive/2025/12/):

- Migration plans (MIGRATION_PLAN.md, MIGRATION_PHASE_*.md)
- Architecture evaluations (ARCHITECTURE_EVALUATION.md)
- Implementation task briefs
- Phase completion reports

**Note:** Archived documents are kept for historical reference but do not reflect the current architecture.

---

## 📖 Documentation by Role

### I'm a Developer

**Essential reading:**
1. [DEVELOPMENT.md](DEVELOPMENT.md) - Setup and workflow
2. [ARCHITECTURE.md](ARCHITECTURE.md) - System structure
3. [TESTING_STRATEGY.md](TESTING_STRATEGY.md) - Testing approach

**Optional:**
- [MODULAR_MONOLITH_DESIGN.md](MODULAR_MONOLITH_DESIGN.md) - Design patterns
- [api/](api/) - API specifications

### I'm an Architect

**Essential reading:**
1. [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
2. [MODULAR_MONOLITH_DESIGN.md](MODULAR_MONOLITH_DESIGN.md) - Design rationale
3. [INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md](INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md) - Framework status

**Optional:**
- [evaluation-modular-monolith-design.md](evaluation-modular-monolith-design.md) - Design evaluation
- [DESIGN_AUDIT_RESOLUTION.md](DESIGN_AUDIT_RESOLUTION.md) - Audit findings

### I'm a DevOps Engineer

**Essential reading:**
1. [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
2. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
3. [SECURITY.md](SECURITY.md) - Security practices

**Optional:**
- [../docker-compose.yml](../docker-compose.yml) - Docker orchestration
- [../Dockerfile](../Dockerfile) - Container configuration

### I'm a Product Manager

**Essential reading:**
1. [../README.md](../README.md) - Product overview
2. [ROADMAP.md](ROADMAP.md) - Future plans
3. [FAQ.md](FAQ.md) - Common questions

**Optional:**
- [INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md](INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md) - Current capabilities

---

## 🔍 Documentation by Task

### Tracking Feature Parity vs FaultMaven-Mono 🔴
→ [FEATURE_PARITY_TRACKING.md](FEATURE_PARITY_TRACKING.md) **← CRITICAL GAP TRACKING**

### Setting Up Development Environment
→ [DEVELOPMENT.md](DEVELOPMENT.md)

### Understanding System Architecture
→ [ARCHITECTURE.md](ARCHITECTURE.md) → [MODULAR_MONOLITH_DESIGN.md](MODULAR_MONOLITH_DESIGN.md)

### Deploying to Production
→ [DEPLOYMENT.md](DEPLOYMENT.md) → [SECURITY.md](SECURITY.md)

### Writing Tests
→ [TESTING_STRATEGY.md](TESTING_STRATEGY.md) → [DEVELOPMENT.md](DEVELOPMENT.md)

### Debugging Issues
→ [TROUBLESHOOTING.md](TROUBLESHOOTING.md) → [DEVELOPMENT.md](DEVELOPMENT.md)

### Understanding Investigation Framework
→ [INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md](INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md) → [AUTO_WIRE_INVESTIGATION_DESIGN.md](AUTO_WIRE_INVESTIGATION_DESIGN.md)

### API Integration
→ [api/README.md](api/README.md) → [DEVELOPMENT.md](DEVELOPMENT.md)

### Contributing to FaultMaven
→ [DEVELOPMENT.md](DEVELOPMENT.md) → [TESTING_STRATEGY.md](TESTING_STRATEGY.md)

---

## 📝 Documentation Standards

**Document Types:**

1. **Guide** (DEVELOPMENT.md, DEPLOYMENT.md) - Step-by-step instructions
2. **Reference** (ARCHITECTURE.md, API docs) - Comprehensive technical details
3. **Strategy** (TESTING_STRATEGY.md, ROADMAP.md) - Approaches and plans
4. **Status** (INTEGRATION_COMPLETION_SUMMARY.md) - Current state tracking

**Temporary Documents:**

Documents prefixed with `DRAFT-`, `WIP-`, `PROPOSAL-`, or `RFC-` are works in progress and should include:
- `<!-- DELETE: [condition] -->` trigger for removal
- Target audience and expiration criteria

**Archive Policy:**

- Historical documents → `archive/YYYY/MM/`
- Keep if valuable for understanding system evolution
- Delete if purely transient status tracking

---

## 🔗 External Resources

- **Main Repository**: <https://github.com/FaultMaven/faultmaven>
- **Copilot Extension**: <https://github.com/FaultMaven/faultmaven-copilot>
- **API Docs (Interactive)**: <http://localhost:8000/docs> (when running locally)
- **Dashboard**: <http://localhost:3000> (when running locally)

---

**Last Updated**: 2025-12-26
**Architecture**: Modular Monolith (Single Repository)
**Status**: ✅ Production Ready
