# FaultMaven

**The AI-Powered Troubleshooting Copilot for Modern Engineering**

Stop context-switching between dashboards, logs, and documentation. FaultMaven gives you a single AI copilot that understands your full stack—from application traces to infrastructure metrics—and learns from every incident your team resolves.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Docker Hub](https://img.shields.io/badge/docker-ready-blue.svg)](https://hub.docker.com/u/faultmaven)
[![GitHub](https://img.shields.io/badge/github-FaultMaven-blue.svg)](https://github.com/FaultMaven)

---

## Quick Start

Get FaultMaven running locally in under 5 minutes:

```bash
# Clone the deployment repo
git clone https://github.com/FaultMaven/faultmaven-deploy.git
cd faultmaven-deploy

# Configure your LLM provider (OpenAI, Anthropic, or local via Ollama)
cp .env.example .env
# Edit .env and add your API key: OPENAI_API_KEY=sk-...

# Launch all services
docker compose up -d

# Verify it's running
curl http://localhost:8090/health
```

**Access Points:**
- **Dashboard:** http://localhost:3000
- **API Gateway:** http://localhost:8090
- **Browser Extension:** Install from [Chrome Web Store](https://chromewebstore.google.com) or load unpacked from [faultmaven-copilot](https://github.com/FaultMaven/faultmaven-copilot)

**Default credentials:** `admin@localhost` / `changeme`

> **Full deployment guide:** [faultmaven-deploy](https://github.com/FaultMaven/faultmaven-deploy)

---

## Why FaultMaven?

### Full-Stack Analysis, Not Just Log Parsing

Most "AI observability" tools throw logs at an LLM and hope for the best. FaultMaven is different:

| Traditional Tools | FaultMaven |
|-------------------|------------|
| Parse logs in isolation | Correlate logs, metrics, traces, and configs |
| Generic AI responses | Context-aware suggestions from YOUR infrastructure |
| Start fresh every incident | Learn from past resolutions in your knowledge base |
| Vendor lock-in | Open core, run anywhere |

### Unified Knowledge Base

Your team's troubleshooting expertise shouldn't live in Slack threads and personal notes. FaultMaven's knowledge base:

- **Captures** runbooks, post-mortems, and tribal knowledge
- **Indexes** with semantic search (find solutions by describing the problem)
- **Surfaces** relevant context automatically during incidents
- **Grows** smarter with every resolved case

### Privacy-First Architecture

Your data never leaves your infrastructure unless you choose to send it:

- All evidence (logs, screenshots, configs) stored locally
- Sensitive data sanitized before LLM processing
- Works with local LLMs (Ollama, vLLM, LM Studio) for air-gapped environments
- You control what context goes to external APIs

---

## Open Core Model

FaultMaven follows an **Open Box / Black Box** philosophy:

### Open Source (This Repository)
**The "Open Box"** — Full transparency and control.

Everything you need for individual troubleshooting:
- All 7 core microservices (Apache 2.0)
- Browser extension + web dashboard
- Multi-provider LLM support
- Knowledge base with semantic search
- Case tracking and evidence management
- Docker Compose deployment

**Best for:** Individual SREs, small teams, air-gapped environments, contributors.

### Enterprise SaaS
**The "Black Box"** — Zero ops, team-scale features.

Same core platform, plus:
- **Team Collaboration:** Shared cases and knowledge bases
- **Enterprise Auth:** SSO/SAML (Okta, Azure AD, Google)
- **Integrations:** Slack, PagerDuty, ServiceNow
- **Managed Infrastructure:** HA PostgreSQL, Redis, S3
- **SLA Guarantees:** 99.9% uptime

**Best for:** Teams needing collaboration, compliance, or managed infrastructure.

**[Try Enterprise Free →](https://faultmaven.ai)**

---

## Feature Comparison

| Capability | Open Source | Enterprise |
|------------|:-----------:|:----------:|
| AI Troubleshooting Chat | ✅ | ✅ |
| Knowledge Base (Semantic Search) | ✅ | ✅ |
| Case Tracking | ✅ | ✅ |
| Evidence Management | ✅ | ✅ |
| Multi-Provider LLM Support | ✅ | ✅ |
| Local LLM Support (Ollama, vLLM) | ✅ | ✅ |
| Browser Extension | ✅ | ✅ |
| Web Dashboard | ✅ | ✅ |
| Docker Self-Hosting | ✅ | — |
| Team Workspaces | — | ✅ |
| Shared Knowledge Bases | — | ✅ |
| SSO / SAML | — | ✅ |
| Slack / PagerDuty Integration | — | ✅ |
| Managed Infrastructure | — | ✅ |
| Priority Support | — | ✅ |

---

## Architecture

```mermaid
flowchart TB
    subgraph Clients
        EXT[Browser Extension]
        DASH[Web Dashboard]
    end

    subgraph Gateway
        GW[API Gateway :8090]
        CAP[Capabilities API]
    end

    subgraph Core Services
        AUTH[Auth :8001]
        SESS[Session :8002]
        CASE[Case :8003]
        KB[Knowledge :8004]
        EVID[Evidence :8005]
        AGENT[Agent :8006]
    end

    subgraph Data Layer
        SQL[(SQLite/PostgreSQL)]
        REDIS[(Redis)]
        CHROMA[(ChromaDB)]
        FILES[(File Storage)]
    end

    subgraph External
        LLM[LLM Providers]
    end

    EXT --> GW
    DASH --> GW
    GW --> CAP
    GW --> AUTH
    GW --> SESS
    GW --> CASE
    GW --> KB
    GW --> EVID
    GW --> AGENT

    AUTH --> SQL
    SESS --> REDIS
    CASE --> SQL
    KB --> CHROMA
    EVID --> FILES
    AGENT --> LLM
    AGENT --> KB
```

### How It Works

1. **Browser Extension** captures context (errors, logs, stack traces) from your current page
2. **API Gateway** routes requests and handles authentication
3. **Agent Service** orchestrates AI conversations, pulling relevant context from the Knowledge Base
4. **Knowledge Service** performs semantic search across your runbooks and past cases
5. **Case Service** tracks investigations and links evidence to resolutions

---

## Repositories

This organization contains the microservices foundation:

| Layer | Repository | Purpose |
|-------|------------|---------|
| **Gateway** | [fm-api-gateway](https://github.com/FaultMaven/fm-api-gateway) | Request routing, auth, capabilities API |
| **Services** | [fm-agent-service](https://github.com/FaultMaven/fm-agent-service) | AI troubleshooting engine |
| | [fm-knowledge-service](https://github.com/FaultMaven/fm-knowledge-service) | Semantic search, RAG |
| | [fm-case-service](https://github.com/FaultMaven/fm-case-service) | Investigation tracking |
| | [fm-evidence-service](https://github.com/FaultMaven/fm-evidence-service) | File/log uploads |
| | [fm-auth-service](https://github.com/FaultMaven/fm-auth-service) | Authentication |
| | [fm-session-service](https://github.com/FaultMaven/fm-session-service) | Session management |
| **Workers** | [fm-job-worker](https://github.com/FaultMaven/fm-job-worker) | Background processing |
| **Shared** | [fm-core-lib](https://github.com/FaultMaven/fm-core-lib) | Common utilities |
| **Clients** | [faultmaven-copilot](https://github.com/FaultMaven/faultmaven-copilot) | Browser extension |
| | [faultmaven-dashboard](https://github.com/FaultMaven/faultmaven-dashboard) | Web UI |
| **Deploy** | [faultmaven-deploy](https://github.com/FaultMaven/faultmaven-deploy) | Docker Compose setup |

---

## LLM Support

Works with your preferred provider:

| Provider | Models | Notes |
|----------|--------|-------|
| **OpenAI** | GPT-4o, GPT-4 Turbo | Recommended for best results |
| **Anthropic** | Claude 3.5 Sonnet, Claude 3 Opus | Excellent for complex reasoning |
| **Google** | Gemini Pro | Good balance of speed/quality |
| **Groq** | Llama 3, Mixtral | Fast inference |
| **Local** | Ollama, vLLM, LM Studio, LocalAI | Air-gapped / privacy-first |

Configure in `.env`:
```bash
LLM_PROVIDER=openai          # or: anthropic, google, groq, ollama
OPENAI_API_KEY=sk-...        # Provider-specific key
OLLAMA_BASE_URL=http://host.docker.internal:11434  # For local LLMs
```

---

## Contributing

We welcome contributions. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Fork and clone a service repo
git clone https://github.com/YOUR_USERNAME/fm-agent-service.git

# Run the full stack locally
cd faultmaven-deploy && docker compose up -d

# Make changes, test, submit PR
```

---

## Documentation

- **[Deployment Guide](https://github.com/FaultMaven/faultmaven-deploy)** — Self-hosting setup
- **[Architecture](./docs/ARCHITECTURE.md)** — System design details
- **[API Reference](./docs/API.md)** — REST endpoints
- **[Development](./docs/DEVELOPMENT.md)** — Local dev setup

---

## Support

- **Issues:** [GitHub Issues](https://github.com/FaultMaven/FaultMaven/issues)
- **Discussions:** [GitHub Discussions](https://github.com/FaultMaven/FaultMaven/discussions)
- **Enterprise:** [faultmaven.ai](https://faultmaven.ai)

---

## License

**Apache 2.0** — Use commercially, fork freely, no strings attached.

Same license as Kubernetes, TensorFlow, and Apache Kafka.

---

<p align="center">
  <strong>FaultMaven</strong> — Your AI copilot for incident response.
</p>
