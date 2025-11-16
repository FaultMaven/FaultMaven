# FaultMaven

**AI-Powered Troubleshooting Copilot for DevOps and SRE Teams**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Docker Hub](https://img.shields.io/badge/docker-ready-blue.svg)](https://hub.docker.com/u/faultmaven)
[![GitHub](https://img.shields.io/badge/github-FaultMaven-blue.svg)](https://github.com/FaultMaven)

---

## Overview

FaultMaven is an open-source troubleshooting copilot that helps DevOps and SRE teams diagnose, document, and resolve production incidents faster. It combines AI-powered analysis with structured troubleshooting workflows to reduce MTTR and build institutional knowledge.

**Key Features:**
- 🤖 **AI-Powered Root Cause Analysis** - Structured 5-phase SRE troubleshooting doctrine
- 📚 **Knowledge Base with RAG** - Learn from past incidents and documentation
- 🔐 **Privacy-First** - All sensitive data sanitized before AI processing
- 🐳 **Zero-Configuration Deployment** - Docker Compose for single-user setups
- 🌐 **Browser Extension** - Troubleshoot directly from your browser
- 🔄 **Session Management** - Track investigation progress across sessions

---

## Quick Start

### Prerequisites
- Docker and Docker Compose
- 8GB RAM minimum
- Ports 8001-8005, 8090, 6379 available

### Deploy FaultMaven

```bash
# Clone the deployment repository
git clone https://github.com/FaultMaven/faultmaven-deploy.git
cd faultmaven-deploy

# Start all services
docker compose up -d

# Verify all services are healthy
curl http://localhost:8090/health  # API Gateway
curl http://localhost:8001/health  # Auth Service
curl http://localhost:8002/health  # Session Service
curl http://localhost:8003/health  # Case Service
curl http://localhost:8004/health  # Knowledge Service
curl http://localhost:8005/health  # Evidence Service
```

All images will be automatically pulled from Docker Hub. No configuration required!

---

## Architecture

FaultMaven uses a **microservices architecture** with the following components:

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser Extension                        │
│              (Chrome/Firefox Troubleshooting UI)             │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTPS
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway (8090)                      │
│                    Unified Entry Point                       │
└─────┬────────┬──────────┬──────────┬──────────┬─────────────┘
      │        │          │          │          │
      ▼        ▼          ▼          ▼          ▼
┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────┐
│   Auth   │ │Session │ │  Case  │ │Evidence│ │ Knowledge  │
│ Service  │ │Service │ │Service │ │Service │ │  Service   │
│  (8001)  │ │ (8002) │ │ (8003) │ │ (8005) │ │   (8004)   │
└────┬─────┘ └───┬────┘ └───┬────┘ └───┬────┘ └─────┬──────┘
     │           │          │          │            │
     │           │          │          │            │
     ▼           ▼          ▼          ▼            ▼
┌─────────┐  ┌──────┐  ┌──────┐  ┌──────┐    ┌──────────┐
│ SQLite  │  │Redis │  │SQLite│  │ File │    │ChromaDB  │
│  Auth   │  │Session  │ Cases│  │Upload│    │Vector DB │
└─────────┘  └──────┘  └──────┘  └──────┘    └──────────┘
```

### Services

| Service | Port | Description | Repository |
|---------|------|-------------|------------|
| **API Gateway** | 8090 | Unified entry point, request routing | [fm-api-gateway](https://github.com/FaultMaven/fm-api-gateway) |
| **Auth Service** | 8001 | JWT authentication, user management | [fm-auth-service](https://github.com/FaultMaven/fm-auth-service) |
| **Session Service** | 8002 | Redis-backed session management | [fm-session-service](https://github.com/FaultMaven/fm-session-service) |
| **Case Service** | 8003 | Troubleshooting case tracking | [fm-case-service](https://github.com/FaultMaven/fm-case-service) |
| **Knowledge Service** | 8004 | RAG-powered knowledge base | [fm-knowledge-service](https://github.com/FaultMaven/fm-knowledge-service) |
| **Evidence Service** | 8005 | File upload and attachment handling | [fm-evidence-service](https://github.com/FaultMaven/fm-evidence-service) |

---

## Technology Stack

**Backend:**
- FastAPI (async Python web framework)
- SQLAlchemy 2.0 (async ORM)
- SQLite (zero-config database)
- Redis (session storage)
- ChromaDB (vector database for RAG)
- BGE-M3 embeddings (multilingual text embeddings)

**Frontend:**
- React 19+ with TypeScript
- WXT Framework (modern WebExtension toolkit)
- Tailwind CSS (utility-first styling)

**Infrastructure:**
- Docker & Docker Compose
- Apache 2.0 License

---

## Use Cases

### 1. Production Incident Investigation
Track symptoms, hypothesis, evidence, and resolution in structured cases.

### 2. Knowledge Base Building
Store runbooks, documentation, and past incident learnings in searchable knowledge base.

### 3. Root Cause Analysis
AI-powered analysis following SRE best practices:
- Define blast radius
- Establish timeline
- Formulate hypothesis
- Validate with evidence
- Propose solution

### 4. Team Collaboration
Share troubleshooting sessions and build institutional knowledge.

---

## Development

### Repository Structure

```
FaultMaven/
├── fm-auth-service/          # Authentication microservice
├── fm-session-service/       # Session management
├── fm-case-service/          # Case tracking
├── fm-knowledge-service/     # Knowledge base + RAG
├── fm-evidence-service/      # File uploads
├── fm-api-gateway/           # API gateway
├── faultmaven-deploy/        # Docker Compose deployment
└── faultmaven-copilot/       # Browser extension
```

### Contributing

We welcome contributions! Each microservice has its own repository with detailed README and development instructions.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Roadmap

### Current (v1.0) - Single-User Personal Assistant
- ✅ JWT authentication
- ✅ SQLite database
- ✅ Redis sessions
- ✅ ChromaDB knowledge base
- ✅ Docker Compose deployment
- ✅ Browser extension

### Future (v2.0) - Team Platform
- [ ] Multi-tenancy (organizations and teams)
- [ ] PostgreSQL for production scale
- [ ] Advanced collaboration features
- [ ] Integrations (Slack, PagerDuty, etc.)
- [ ] Enterprise SSO

---

## Documentation

- [Deployment Guide](https://github.com/FaultMaven/faultmaven-deploy)
- [Architecture Overview](./docs/ARCHITECTURE.md) *(coming soon)*
- [API Documentation](./docs/API.md) *(coming soon)*
- [Development Setup](./docs/DEVELOPMENT.md) *(coming soon)*

---

## Docker Images

All services are published to Docker Hub:
- [faultmaven/fm-auth-service](https://hub.docker.com/r/faultmaven/fm-auth-service)
- [faultmaven/fm-session-service](https://hub.docker.com/r/faultmaven/fm-session-service)
- [faultmaven/fm-case-service](https://hub.docker.com/r/faultmaven/fm-case-service)
- [faultmaven/fm-knowledge-service](https://hub.docker.com/r/faultmaven/fm-knowledge-service)
- [faultmaven/fm-evidence-service](https://hub.docker.com/r/faultmaven/fm-evidence-service)
- [faultmaven/fm-api-gateway](https://hub.docker.com/r/faultmaven/fm-api-gateway)

---

## Support

- **Issues**: [GitHub Issues](https://github.com/FaultMaven/FaultMaven/issues)
- **Discussions**: [GitHub Discussions](https://github.com/FaultMaven/FaultMaven/discussions)
- **Website**: *Coming soon*

---

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [ChromaDB](https://www.trychroma.com/)
- [Redis](https://redis.io/)
- [React](https://react.dev/)
- [WXT](https://wxt.dev/)

---

**FaultMaven** - Making troubleshooting faster, smarter, and more collaborative.
