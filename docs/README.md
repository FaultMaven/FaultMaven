# FaultMaven Documentation

**Central documentation index for the FaultMaven modular monolith.**

This guide organizes all **permanent documentation** by purpose and audience. Temporary planning/status documents are in [working/](working/).

---

## 🚀 Getting Started

**New to FaultMaven? Start here:**

1. **[Main README](../README.md)** - Project overview, quick start, installation
2. **[Development Setup](development/setup.md)** - Local development environment and workflow
3. **[Deployment Guide](operations/deployment.md)** - Production deployment

---

## 📐 Architecture & Design

**Core architectural documentation:**

| Document | Purpose | Audience |
| -------- | ------- | -------- |
| **[architecture/design-specifications.md](architecture/design-specifications.md)** | Target design specifications with implementation gaps | All developers |
| **[TECHNICAL_DEBT.md](TECHNICAL_DEBT.md)** | 🔴 Detailed gap analysis and roadmap | Developers, PM |
| **[architecture/](architecture/)** | System architecture and module designs | All developers |

---

## 💻 Development

**Building and contributing to FaultMaven:**

| Document | Purpose |
| -------- | ------- |
| **[development/setup.md](development/setup.md)** | Complete development guide and workflows |
| **[development/testing-strategy.md](development/testing-strategy.md)** | Testing approach and patterns |
| **[api/README.md](api/README.md)** | Auto-generated API documentation |

---

## 🚢 Deployment & Operations

**Running FaultMaven in production:**

| Document | Purpose |
| -------- | ------- |
| **[operations/deployment.md](operations/deployment.md)** | Production deployment guide |
| **[operations/security.md](operations/security.md)** | Security guidelines and best practices |
| **[operations/troubleshooting.md](operations/troubleshooting.md)** | Common issues and solutions |

---

## 📚 Reference

| Document | Purpose |
| -------- | ------- |
| **[reference/faq.md](reference/faq.md)** | Frequently asked questions |
| **[reference/roadmap.md](reference/roadmap.md)** | Product roadmap and future plans |

---

## 📖 Documentation by Role

### I'm a Developer

**Essential reading:**

1. [development/setup.md](development/setup.md) - Setup and workflow
2. [architecture/](architecture/) - System architecture
3. [development/testing-strategy.md](development/testing-strategy.md) - Testing approach

**Optional:**

- [architecture/design-specifications.md](architecture/design-specifications.md) - Detailed specifications
- [api/README.md](api/README.md) - API documentation

### I'm an Architect

**Essential reading:**

1. [architecture/](architecture/) - System architecture
2. [architecture/design-specifications.md](architecture/design-specifications.md) - Design specifications
3. [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md) - Implementation gaps
4. [architecture/modular-monolith-rationale.md](architecture/modular-monolith-rationale.md) - Design rationale

**Optional:**

- [working/investigation-framework-status.md](working/investigation-framework-status.md) - Framework integration status

### I'm a DevOps Engineer

**Essential reading:**

1. [operations/deployment.md](operations/deployment.md) - Deployment guide
2. [operations/troubleshooting.md](operations/troubleshooting.md) - Common issues
3. [operations/security.md](operations/security.md) - Security practices

**Optional:**

- [../docker-compose.yml](../docker-compose.yml) - Docker orchestration
- [../Dockerfile](../Dockerfile) - Container configuration

### I'm a Product Manager

**Essential reading:**

1. [../README.md](../README.md) - Product overview
2. [reference/roadmap.md](reference/roadmap.md) - Future plans
3. [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md) - Implementation priorities
4. [reference/faq.md](reference/faq.md) - Common questions

---

## 🔍 Documentation by Task

### Understanding System Architecture

→ [architecture/](architecture/) → [architecture/design-specifications.md](architecture/design-specifications.md)

### Tracking Implementation Gaps 🔴

→ [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md)

### Setting Up Development Environment

→ [development/setup.md](development/setup.md)

### Deploying to Production

→ [operations/deployment.md](operations/deployment.md) → [operations/security.md](operations/security.md)

### Writing Tests

→ [development/testing-strategy.md](development/testing-strategy.md)

### Debugging Issues

→ [operations/troubleshooting.md](operations/troubleshooting.md)

### Understanding Investigation Framework

→ [working/investigation-framework-status.md](working/investigation-framework-status.md)

### API Integration

→ [api/README.md](api/README.md)

### Contributing to FaultMaven

→ [../CONTRIBUTING.md](../CONTRIBUTING.md) → [development/setup.md](development/setup.md)

---

## 🗂️ Folder Organization

### Root Documentation Files

**Long-term (2 files)**:

- **TECHNICAL_DEBT.md** - Implementation gaps and roadmap
- **README.md** - This file (documentation index)

### Folders

- **[architecture/](architecture/)** - System architecture and module designs
- **[development/](development/)** - Developer guides and testing strategy
- **[operations/](operations/)** - Deployment, security, troubleshooting
- **[reference/](reference/)** - FAQ and roadmap
- **[api/](api/)** - Auto-generated API documentation
- **[working/](working/)** - Temporary planning and status tracking
- **[archive/](archive/)** - Historical documentation

---

## 📝 Documentation Lifecycle

### Long-term Documentation

All files in `docs/` (excluding `working/` and `archive/`) are **permanent reference documentation**:

- Updated as system evolves
- Versioned with code (git)
- Listed in this documentation map

### Short-term Documentation ([working/](working/))

Temporary planning, status tracking, and work-in-progress documents:

- May include `<!-- DELETE WHEN: condition -->` markers
- Moved to archive or deleted when work completes
- NOT listed in main documentation map

### Archived Documentation ([archive/](archive/))

Historical reference only:

- Organized by date: `archive/YYYY/MM/`
- Kept if valuable for understanding system evolution
- Deleted if purely transient status tracking

---

## 🔗 Cross-References

### Design → Implementation

- [architecture/design-specifications.md](architecture/design-specifications.md) defines target design with implementation gaps
- [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md) tracks detailed gap analysis and roadmap

### Architecture → Development

- [architecture/](architecture/) explains system structure
- [development/setup.md](development/setup.md) shows how to work with that structure
- [development/testing-strategy.md](development/testing-strategy.md) defines testing approach

### Development → Deployment

- [development/setup.md](development/setup.md) for local setup
- [operations/deployment.md](operations/deployment.md) for production deployment
- [operations/security.md](operations/security.md) for production security

---

## 🔗 External Resources

- **Main Repository**: <https://github.com/FaultMaven/faultmaven>
- **Copilot Extension**: <https://github.com/FaultMaven/faultmaven-copilot>
- **API Docs (Interactive)**: <http://localhost:8000/docs> (when running locally)
- **Dashboard**: <http://localhost:3000> (when running locally)

---

**Last Updated**: 2025-12-27
**Total Long-term Documents**: 2 root files + 4 folders
**Architecture**: Modular Monolith (Single Repository)
**Status**: ✅ Production Ready (with known gaps in TECHNICAL_DEBT.md)
