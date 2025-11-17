# FaultMaven Deploy

**One-command deployment for self-hosted FaultMaven**

Deploy a complete AI-powered troubleshooting platform on your own infrastructure with Docker Compose.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://hub.docker.com/u/faultmaven)

---

## Quick Start (3 Steps)

### Step 1: Clone Repository

```bash
git clone https://github.com/FaultMaven/faultmaven-deploy.git
cd faultmaven-deploy
```

### Step 2: Configure

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your LLM API key
nano .env  # or vim, code, etc.
```

Required: Add ONE of these API keys to `.env`:
- `OPENAI_API_KEY=sk-...`
- `ANTHROPIC_API_KEY=sk-ant-...`
- `FIREWORKS_API_KEY=fw-...`

### Step 3: Deploy

```bash
# Option A: Use initialization script (recommended)
bash scripts/init.sh

# Option B: Manual start
docker compose up -d
```

**That's it!** Access FaultMaven at:
- **Dashboard:** http://localhost:3000
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

---

## What's Included

FaultMaven deploys 7 services via Docker Compose:

| Service | Port | Purpose |
|---------|------|---------|
| **API Gateway** | 8000 | Unified entry point with auth & routing |
| **Auth Service** | 8001 | JWT authentication |
| **Session Service** | 8002 | Conversation history (Redis) |
| **Case Service** | 8003 | Troubleshooting case management |
| **Knowledge Service** | 8004 | RAG-powered knowledge base |
| **Evidence Service** | 8005 | File uploads & attachments |
| **Dashboard** | 3000 | Web UI for KB management |

Plus:
- **Redis** (6379) - Session storage

---

## Architecture

```
┌─────────────────────────────────────────┐
│   Browser Extension (Chat)              │
│   + Dashboard (KB Management)           │
└───────────────┬─────────────────────────┘
                │ HTTP
                ▼
┌─────────────────────────────────────────┐
│   API Gateway (8000)                    │
│   Capabilities API + Auth               │
└─────┬──────┬──────┬──────┬──────────────┘
      │      │      │      │
      ▼      ▼      ▼      ▼
   Auth  Session Case  Knowledge  Evidence
   8001   8002   8003    8004       8005
```

All data persists in Docker volumes (SQLite + Redis).

---

## Configuration

### Required Environment Variables

```bash
# .env file

# LLM Provider (choose ONE)
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...
# OR
FIREWORKS_API_KEY=fw-...

# Security (generate with: openssl rand -hex 32)
JWT_SECRET=your-random-32-char-string
```

### Optional Configuration

```bash
# Ports (defaults shown)
API_PORT=8000
DASHBOARD_PORT=3000

# Authentication
JWT_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# File Uploads
MAX_FILE_SIZE_MB=10
MAX_FILES_PER_CASE=20

# Logging
LOG_LEVEL=INFO
DEBUG_MODE=false
```

See `.env.example` for all options.

---

## Usage

### Start Services

```bash
docker compose up -d
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f gateway
docker compose logs -f case-service
```

### Stop Services

```bash
docker compose down
```

### Restart After Config Changes

```bash
docker compose restart
```

### Update to Latest Version

```bash
docker compose pull
docker compose up -d
```

---

## Health Checks

Verify all services are running:

```bash
# API Gateway
curl http://localhost:8000/health

# Capabilities (feature detection)
curl http://localhost:8000/v1/meta/capabilities

# Individual services
curl http://localhost:8001/health  # Auth
curl http://localhost:8002/health  # Session
curl http://localhost:8003/health  # Case
curl http://localhost:8004/health  # Knowledge
curl http://localhost:8005/health  # Evidence
```

Expected response: `{"status":"healthy"}`

---

## Browser Extension

Install the FaultMaven Copilot extension:

1. **Chrome:** [Chrome Web Store](https://chrome.google.com/webstore) *(coming soon)*
2. **Firefox:** [Firefox Add-ons](https://addons.mozilla.org/) *(coming soon)*

Configure extension settings:
- **API Endpoint:** `http://localhost:8000`
- **Enable Auto-Connect:** Yes

---

## Data Management

### Backup Data

```bash
# Backup all volumes
docker run --rm -v faultmaven-deploy_case-data:/data -v $(pwd)/backup:/backup alpine tar czf /backup/cases-$(date +%Y%m%d).tar.gz -C /data .
docker run --rm -v faultmaven-deploy_knowledge-data:/data -v $(pwd)/backup:/backup alpine tar czf /backup/knowledge-$(date +%Y%m%d).tar.gz -C /data .
docker run --rm -v faultmaven-deploy_auth-data:/data -v $(pwd)/backup:/backup alpine tar czf /backup/auth-$(date +%Y%m%d).tar.gz -C /data .
docker run --rm -v faultmaven-deploy_evidence-data:/data -v $(pwd)/backup:/backup alpine tar czf /backup/evidence-$(date +%Y%m%d).tar.gz -C /data .

# Backup Redis
docker exec fm-redis redis-cli SAVE
docker cp fm-redis:/data/dump.rdb ./backup/redis-$(date +%Y%m%d).rdb
```

### Restore Data

```bash
# Stop services first
docker compose down

# Restore volumes (example for cases)
docker run --rm -v faultmaven-deploy_case-data:/data -v $(pwd)/backup:/backup alpine tar xzf /backup/cases-20240101.tar.gz -C /data

# Restart services
docker compose up -d
```

### Reset Everything

```bash
# WARNING: This deletes all data!
docker compose down -v
rm -rf backup/  # Optional: delete backups too
docker compose up -d
```

---

## Troubleshooting

### Port Already in Use

**Problem:** `Error starting userland proxy: listen tcp4 0.0.0.0:8000: bind: address already in use`

**Solution:** Change port in `.env`:
```bash
API_PORT=8080
```

Then restart: `docker compose up -d`

### Service Not Starting

**Check logs:**
```bash
docker compose logs gateway
```

**Common issues:**
- Missing LLM API key in `.env`
- Invalid JWT_SECRET (must be set)
- Docker daemon not running

### Cannot Connect from Extension

**Verify:**
1. API Gateway is running: `curl http://localhost:8000/health`
2. Extension is configured with correct endpoint: `http://localhost:8000`
3. CORS is configured (should be automatic)

### Database Errors

**Reset database (WARNING: deletes data):**
```bash
docker compose down
docker volume rm faultmaven-deploy_case-data
docker compose up -d
```

### Out of Disk Space

**Check volume sizes:**
```bash
docker system df -v
```

**Clean up old images:**
```bash
docker image prune -a
```

---

## Production Deployment

### Recommended Setup

For production use, add:

1. **Reverse Proxy (nginx/Caddy)** with HTTPS
2. **Firewall Rules** (only expose 443/80)
3. **Automated Backups** (cron job)
4. **Monitoring** (Prometheus + Grafana)
5. **Log Aggregation** (ELK stack or similar)

### Example nginx Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name faultmaven.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # API Gateway
    location /v1/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Dashboard
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Security Checklist

- [ ] Strong JWT_SECRET (32+ characters)
- [ ] HTTPS enabled (reverse proxy)
- [ ] Firewall configured (block internal ports)
- [ ] Automated backups configured
- [ ] Log monitoring enabled
- [ ] Regular security updates (`docker compose pull`)

---

## Scaling

### Horizontal Scaling (Multiple Instances)

For high availability, deploy multiple instances behind a load balancer:

```yaml
# docker-compose.scale.yml
services:
  case-service:
    deploy:
      replicas: 3
```

Run: `docker compose -f docker-compose.yml -f docker-compose.scale.yml up -d`

### External Database (PostgreSQL)

For production scale, migrate to PostgreSQL (requires enterprise version).

### Redis Clustering

For high-availability sessions:

```yaml
services:
  redis:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes
```

---

## FAQ

### Q: Do I need a paid LLM API?

**A:** Yes. FaultMaven requires an API key from OpenAI, Anthropic, or Fireworks. Costs vary by provider (~$0.01-0.10 per request).

### Q: Can I use local LLMs (Ollama)?

**A:** Not yet. Local LLM support is on the [roadmap](https://github.com/FaultMaven/FaultMaven#roadmap).

### Q: How much disk space do I need?

**A:** Minimum 10GB. Knowledge base and case files grow over time.

### Q: Can I deploy on ARM (Raspberry Pi)?

**A:** Not officially supported, but multi-arch images may work. File an issue if you try!

### Q: Is this the same as the Enterprise version?

**A:** No. This is the **self-hosted open-source** version. Enterprise adds multi-tenancy, SSO, teams, and managed hosting. See [comparison](https://github.com/FaultMaven/FaultMaven#-architecture-philosophy-enterprise-superset-model).

### Q: Can I contribute improvements?

**A:** Yes! See [CONTRIBUTING.md](https://github.com/FaultMaven/FaultMaven/blob/main/CONTRIBUTING.md).

---

## Support

- **Issues:** [GitHub Issues](https://github.com/FaultMaven/FaultMaven/issues)
- **Discussions:** [GitHub Discussions](https://github.com/FaultMaven/FaultMaven/discussions)
- **Documentation:** [FaultMaven Docs](https://github.com/FaultMaven/FaultMaven)

---

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

## Related Repositories

- [FaultMaven](https://github.com/FaultMaven/FaultMaven) - Main documentation
- [faultmaven-copilot](https://github.com/FaultMaven/faultmaven-copilot) - Browser extension
- [faultmaven-dashboard](https://github.com/FaultMaven/faultmaven-dashboard) - KB management UI
- Backend Services:
  - [fm-api-gateway](https://github.com/FaultMaven/fm-api-gateway)
  - [fm-auth-service](https://github.com/FaultMaven/fm-auth-service)
  - [fm-case-service](https://github.com/FaultMaven/fm-case-service)
  - [fm-session-service](https://github.com/FaultMaven/fm-session-service)
  - [fm-knowledge-service](https://github.com/FaultMaven/fm-knowledge-service)
  - [fm-evidence-service](https://github.com/FaultMaven/fm-evidence-service)

---

**FaultMaven Deploy** - Self-host your AI troubleshooting platform in 3 commands.
