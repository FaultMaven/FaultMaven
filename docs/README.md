# FaultMaven Documentation

**Central documentation index for the FaultMaven modular monolith.**

This guide organizes all **permanent documentation** by purpose and audience. Temporary planning/status documents are in [working/](working/).

---

## 🚀 Getting Started

**New to FaultMaven? Start here:**

1. **[Main README](../README.md)** - Project overview, quick start, installation
2. **[DEVELOPMENT.md](DEVELOPMENT.md)** - Local development setup and workflow
3. **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide

---

## 📐 Architecture & Design

**Core architectural documentation:**

| Document | Purpose | Audience |
| -------- | ------- | -------- |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | 🎯 System architecture with inline status | All developers |
| **[SYSTEM_DESIGN.md](SYSTEM_DESIGN.md)** | Detailed design specifications | All developers |
| **[TECHNICAL_DEBT.md](TECHNICAL_DEBT.md)** | 🔴 Implementation gaps and roadmap | Developers, PM |
| **[MODULAR_MONOLITH_DESIGN.md](MODULAR_MONOLITH_DESIGN.md)** | Modular monolith rationale and patterns | Architects |

**Investigation Framework:**

| Document | Purpose |
| -------- | ------- |
| **[INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md](INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md)** | Framework overview and integration status |

---

## 💻 Development

**Building and contributing to FaultMaven:**

| Document | Purpose |
| -------- | ------- |
| **[DEVELOPMENT.md](DEVELOPMENT.md)** | Complete development guide and workflows |
| **[TESTING_STRATEGY.md](TESTING_STRATEGY.md)** | Testing approach and patterns |
| **[api/README.md](api/README.md)** | Auto-generated API documentation |

---

## 🚢 Deployment & Operations

**Running FaultMaven in production:**

| Document | Purpose |
| -------- | ------- |
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | Production deployment guide |
| **[SECURITY.md](SECURITY.md)** | Security guidelines and best practices |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Common issues and solutions |

---

## 📚 Reference

| Document | Purpose |
| -------- | ------- |
| **[FAQ.md](FAQ.md)** | Frequently asked questions |
| **[ROADMAP.md](ROADMAP.md)** | Product roadmap and future plans |

---

## 📖 Documentation by Role

### I'm a Developer

**Essential reading:**

1. [DEVELOPMENT.md](DEVELOPMENT.md) - Setup and workflow
2. [ARCHITECTURE.md](ARCHITECTURE.md) - System structure
3. [TESTING_STRATEGY.md](TESTING_STRATEGY.md) - Testing approach

**Optional:**

- [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) - Detailed specifications
- [api/README.md](api/README.md) - API documentation

### I'm an Architect

**Essential reading:**

1. [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
2. [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) - Design specifications
3. [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md) - Implementation gaps
4. [MODULAR_MONOLITH_DESIGN.md](MODULAR_MONOLITH_DESIGN.md) - Design rationale

**Optional:**

- [INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md](INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md) - Framework details

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
3. [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md) - Implementation priorities
4. [FAQ.md](FAQ.md) - Common questions

---

## 🔍 Documentation by Task

### Understanding System Architecture

→ [ARCHITECTURE.md](ARCHITECTURE.md) → [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md)

### Tracking Implementation Gaps 🔴

→ [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md)

### Setting Up Development Environment

→ [DEVELOPMENT.md](DEVELOPMENT.md)

### Deploying to Production

→ [DEPLOYMENT.md](DEPLOYMENT.md) → [SECURITY.md](SECURITY.md)

### Writing Tests

→ [TESTING_STRATEGY.md](TESTING_STRATEGY.md)

### Debugging Issues

→ [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### Understanding Investigation Framework

→ [INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md](INVESTIGATION_FRAMEWORK_INTEGRATION_COMPLETE.md)

### API Integration

→ [api/README.md](api/README.md)

### Contributing to FaultMaven

→ [DEVELOPMENT.md](DEVELOPMENT.md) → [TESTING_STRATEGY.md](TESTING_STRATEGY.md)

---

## 🗂️ Document Organization

### Long-term Documentation (This Directory)

All files in `docs/` (excluding `working/` and `archive/`) are **permanent reference documentation**:

- **Architecture & Design** (5 files)
- **Development** (3 files)
- **Operations** (3 files)
- **Reference** (2 files)
- **Framework** (1 file)

**Total**: 14 permanent documents

### Short-term Documentation ([working/](working/))

Temporary planning, status tracking, and work-in-progress documents:

- Documentation cleanup tracking
- Integration status reports
- Test coverage reports
- Feature parity tracking (superseded by TECHNICAL_DEBT.md)
- Implementation roadmaps

**Purpose**: Active planning and status tracking. These documents may be deleted or archived when work is complete.

### Historical Documentation ([archive/](archive/))

Archived documents from completed work or deprecated approaches:

- Migration plans and status (microservices → monolith)
- Completed design audits
- Historical architecture evaluations
- Gap analyses (superseded by current tracking)

**Purpose**: Historical reference. Not relevant to current development.

---

## 📝 Documentation Standards

### Document Types

1. **Guide** (DEVELOPMENT.md, DEPLOYMENT.md) - Step-by-step instructions
2. **Reference** (ARCHITECTURE.md, SYSTEM_DESIGN.md) - Comprehensive technical details
3. **Strategy** (TESTING_STRATEGY.md, ROADMAP.md) - Approaches and plans
4. **Tracker** (TECHNICAL_DEBT.md) - Current state and gaps

### Lifecycle Management

**Long-term Documents** (`docs/*.md`):

- Permanent reference documentation
- Updated as system evolves
- Versioned with code (git)
- Listed in this documentation map

**Short-term Documents** (`docs/working/*.md`):

- Temporary planning and status tracking
- May include `<!-- DELETE WHEN: condition -->` markers
- Moved to archive or deleted when work completes
- NOT listed in main documentation map

**Archived Documents** (`docs/archive/YYYY/MM/*.md`):

- Historical reference only
- Kept if valuable for understanding system evolution
- Deleted if purely transient status tracking

---

## 🔗 Cross-References

### Design → Implementation

- [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) defines requirements
- [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md) tracks what's NOT implemented
- [ARCHITECTURE.md](ARCHITECTURE.md) shows current state with inline status

### Architecture → Development

- [ARCHITECTURE.md](ARCHITECTURE.md) explains system structure
- [DEVELOPMENT.md](DEVELOPMENT.md) shows how to work with that structure
- [TESTING_STRATEGY.md](TESTING_STRATEGY.md) defines testing approach

### Development → Deployment

- [DEVELOPMENT.md](DEVELOPMENT.md) for local setup
- [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
- [SECURITY.md](SECURITY.md) for production security

---

## 🔗 External Resources

- **Main Repository**: <https://github.com/FaultMaven/faultmaven>
- **Copilot Extension**: <https://github.com/FaultMaven/faultmaven-copilot>
- **API Docs (Interactive)**: <http://localhost:8000/docs> (when running locally)
- **Dashboard**: <http://localhost:3000> (when running locally)

---

**Last Updated**: 2025-12-26
**Total Long-term Documents**: 14
**Architecture**: Modular Monolith (Single Repository)
**Status**: ✅ Production Ready (with known gaps in TECHNICAL_DEBT.md)
