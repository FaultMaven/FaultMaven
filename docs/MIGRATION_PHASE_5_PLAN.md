# Migration Phase 5: Dashboard Integration & FaultMaven Core Deployment

**Status:** 🔜 **READY TO START** (2024-12-24)

**Goal:** Create the simplest possible self-hosted deployment for FaultMaven Core with bundled dashboard, SQLite database, and one-command startup.

---

## Philosophy: Maximum Utility, Minimum Friction

FaultMaven Core is designed for **individual engineers** who want an AI troubleshooting assistant running on their laptop or personal server. The deployment must be:

- ✅ **One command to start:** `./faultmaven start`
- ✅ **Zero database setup:** SQLite embedded (no PostgreSQL container)
- ✅ **Portable data:** Zip `./data/` folder = complete backup
- ✅ **Minimal containers:** 3 total (app, redis, chromadb)
- ✅ **Single port:** 8000 for both API + Dashboard
- ✅ **Deployment neutral:** Same code runs Core (SQLite) and Enterprise (PostgreSQL)

---

## Architecture Change

### Before: Microservices (12 containers)

```
fm-auth-service:8001, fm-session-service:8002, fm-case-service:8003,
fm-knowledge-service:8004, fm-evidence-service:8005, fm-agent-service:8006,
fm-api-gateway:8090, fm-job-worker, fm-job-worker-beat,
faultmaven-dashboard:3000, postgres:5432, redis:6379, chromadb:8007
```

**Issues:**
- 12 containers to manage
- 10+ ports exposed
- Complex networking
- PostgreSQL overkill for single user
- Slow startup (2-3 minutes)

### After: Modular Monolith (3 containers)

```
faultmaven:8000 (API + Dashboard bundled)
redis:6379 (sessions/cache)
chromadb:8000 (vector search)
```

**Benefits:**
- 3 containers only (75% reduction)
- 1 port (8000) - API and dashboard
- SQLite embedded (no database container)
- Fast startup (30 seconds)
- Portable `./data/` folder

---

## Deployment Neutrality Strategy

**Core Principle:** The same Docker image and codebase runs both FaultMaven Core (SQLite) and FaultMaven Enterprise (PostgreSQL). Infrastructure choice is made via environment variable.

### Layer-by-Layer Abstraction

| Layer | Core (Self-Hosted) | Enterprise (Kubernetes) | Abstraction |
|-------|-------------------|------------------------|-------------|
| **Database** | SQLite (embedded) | PostgreSQL (managed RDS) | SQLAlchemy ORM + `DATABASE_URL` |
| **Vector DB** | ChromaDB (local container) | ChromaDB (distributed) or Weaviate | VectorProvider interface |
| **Cache** | Redis (local container) | Redis Cluster / ElastiCache | CacheProvider interface |
| **Storage** | Local disk (`./data/uploads`) | S3 / Blob Storage | FileProvider interface |
| **Config** | `.env` file | Kubernetes ConfigMap/Secrets | Environment variables |

### Deployment Neutrality Implementation

#### 1. Database Abstraction (SQLAlchemy ORM)

**Rule:** Write ALL queries using SQLAlchemy ORM syntax, NEVER raw SQL.

```python
# ✅ CORRECT: Works on SQLite AND PostgreSQL
from sqlalchemy import select
result = await session.execute(select(Case).limit(5))

# ❌ WRONG: SQLite vs PostgreSQL have different SQL dialects
await session.execute("SELECT * FROM cases LIMIT 5")
```

**Why:** SQLAlchemy translates high-level queries into the correct SQL dialect automatically.

#### 2. Migration Compatibility (Batch Mode)

**Problem:** SQLite has limited `ALTER TABLE` support. It cannot drop columns or change constraints directly. PostgreSQL supports these natively.

**Solution:** Configure Alembic to use "batch mode" (move-and-copy pattern).

**File:** `alembic/env.py`

```python
def run_migrations_offline():
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,  # ✅ CRITICAL: Enables SQLite compatibility
    )

def run_migrations_online():
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # ✅ CRITICAL: Enables SQLite compatibility
        )
```

**How it works:**
1. Creates new table with correct schema
2. Copies data from old table
3. Deletes old table
4. Renames new table

**Result:** Migrations work seamlessly on both SQLite and PostgreSQL.

#### 3. JSON Type Safety

**Problem:** PostgreSQL has native `JSONB` type (binary, indexed). SQLite stores JSON as text.

**Solution:** Use ORM's generic JSON type, NOT PostgreSQL-specific JSONB.

```python
# ✅ CORRECT: Works on both databases
from sqlalchemy.types import JSON

class Case(Base):
    metadata = Column(JSON)  # SQLAlchemy handles dialect differences

# ❌ WRONG: Crashes on SQLite
from sqlalchemy.dialects.postgresql import JSONB

class Case(Base):
    metadata = Column(JSONB)  # Only works on PostgreSQL
```

#### 4. Environment-Based Configuration

**File:** `src/faultmaven/database.py`

```python
import os
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/faultmaven.db")

# Database-specific engine configuration
if "sqlite" in DATABASE_URL:
    # SQLite specific tweaks
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # Allow multi-threading
        echo=False,
    )
else:
    # PostgreSQL specific tweaks
    engine = create_async_engine(
        DATABASE_URL,
        pool_size=20,           # Connection pooling
        max_overflow=10,
        echo=False,
    )
```

**Environment Variables:**

```bash
# FaultMaven Core (SQLite)
DATABASE_URL=sqlite+aiosqlite:///data/faultmaven.db

# FaultMaven Enterprise (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:pass@db-host:5432/faultmaven
```

---

## Prerequisites

- ✅ Phase 1: Provider Abstraction (Complete)
- ✅ Phase 2: Module Migration (Complete)
- ✅ Phase 3: API Layer (Complete - 88 endpoints)
- ✅ Phase 4: Job Worker Cleanup (Complete - asyncio migration)
- ⏳ Phase 3.1: Testing (In progress with testing agent)

---

## Implementation Tasks

### 5.1: Copy Dashboard Source ✅

**Goal:** Move dashboard into monolith repository

```bash
cd /home/swhouse/product/faultmaven
mkdir -p dashboard
cp -r ../faultmaven-dashboard/* dashboard/

# Verify dashboard builds
cd dashboard
pnpm install
pnpm run build
# Output: dashboard/dist/ with static files
```

**Success Criteria:**
- ✅ Dashboard source copied to `faultmaven/dashboard/`
- ✅ `pnpm run build` succeeds
- ✅ `dashboard/dist/` contains static files

---

### 5.2: Create Multi-Stage Dockerfile ✅

**Goal:** Single Docker image with dashboard bundled

**File:** `Dockerfile`

```dockerfile
# ============================================================================
# Stage 1: Build React Dashboard
# ============================================================================
FROM node:20-alpine AS dashboard-builder

WORKDIR /app/dashboard

# Install pnpm
RUN npm install -g pnpm

# Copy dashboard source
COPY dashboard/package.json dashboard/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY dashboard/ .

# Build production bundle
RUN pnpm run build

# ============================================================================
# Stage 2: Python Application + Dashboard Static Files
# ============================================================================
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dashboard build artifacts from stage 1
COPY --from=dashboard-builder /app/dashboard/dist /app/static

# Copy Python application
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Create non-root user for security
RUN useradd -m -u 1000 faultmaven && \
    chown -R faultmaven:faultmaven /app

# Create data directory with proper permissions
RUN mkdir -p /data && chown -R faultmaven:faultmaven /data

USER faultmaven

# Expose single port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run migrations on startup, then start app
CMD alembic upgrade head && \
    uvicorn faultmaven.app:app --host 0.0.0.0 --port 8000
```

**Key Features:**
- Multi-stage build (dashboard + Python)
- Non-root user (security)
- Health check endpoint
- Auto-run migrations on startup

**Success Criteria:**
- ✅ Image builds successfully
- ✅ Image contains both API and dashboard files
- ✅ Image size <500MB

---

### 5.3: Configure FastAPI to Serve Dashboard ✅

**Goal:** Serve dashboard at root `/`, API at `/api/*`

**File:** `src/faultmaven/app.py`

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

def create_app() -> FastAPI:
    app = FastAPI(
        title="FaultMaven",
        description="AI-Powered Troubleshooting Copilot",
        version="1.0.0",
    )

    # Include API routers (at /api/v1/*)
    from faultmaven.modules.auth.router import router as auth_router
    from faultmaven.modules.session.router import router as session_router
    from faultmaven.modules.case.router import router as case_router
    from faultmaven.modules.evidence.router import router as evidence_router
    from faultmaven.modules.knowledge.router import router as knowledge_router
    from faultmaven.modules.agent.router import router as agent_router

    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(session_router, prefix="/api/v1/sessions", tags=["sessions"])
    app.include_router(case_router, prefix="/api/v1/cases", tags=["cases"])
    app.include_router(evidence_router, prefix="/api/v1/evidence", tags=["evidence"])
    app.include_router(knowledge_router, prefix="/api/v1/knowledge", tags=["knowledge"])
    app.include_router(agent_router, prefix="/api/v1/agent", tags=["agent"])

    # Health check (top-level)
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": "faultmaven-core",
            "version": "1.0.0"
        }

    # Serve dashboard static files
    dashboard_path = Path(__file__).parent.parent.parent / "static"
    if dashboard_path.exists():
        # Mount static assets (JS, CSS, images)
        app.mount("/assets", StaticFiles(directory=str(dashboard_path / "assets")), name="assets")

        # Serve index.html for all non-API routes (SPA routing)
        @app.get("/{full_path:path}")
        async def serve_dashboard(full_path: str):
            # Skip API routes
            if full_path.startswith("api/"):
                return {"error": "Not found"}

            # Serve index.html for dashboard routes
            index_file = dashboard_path / "index.html"
            if index_file.exists():
                return FileResponse(index_file)

            return {"error": "Dashboard not found"}

    return app

app = create_app()
```

**Routing Strategy:**
- `/health` → Health check
- `/api/v1/*` → API endpoints
- `/assets/*` → Static files (JS, CSS, images)
- `/*` → Dashboard (index.html) for SPA routing

**Success Criteria:**
- ✅ Dashboard accessible at `http://localhost:8000/`
- ✅ API accessible at `http://localhost:8000/api/v1/*`
- ✅ Static assets load correctly
- ✅ SPA routing works (refresh preserves route)

---

### 5.4: Update Dashboard API Configuration ✅

**Goal:** Point dashboard to bundled API (same origin)

**File:** `dashboard/.env.production`

```bash
# Use relative URL (same origin as dashboard)
VITE_API_BASE_URL=/api/v1
```

**Or update:** `dashboard/vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  define: {
    // Use relative URL for API (same origin)
    'import.meta.env.VITE_API_BASE_URL': JSON.stringify('/api/v1')
  },
  build: {
    outDir: 'dist',
    sourcemap: false,  // Disable source maps in production
  }
})
```

**Dashboard API Client:**

```typescript
// Before (separate servers)
const API_BASE = 'http://localhost:8090/api/v1'

// After (bundled)
const API_BASE = '/api/v1'  // Same origin
```

**Success Criteria:**
- ✅ Dashboard makes API calls to `/api/v1/*`
- ✅ No CORS errors
- ✅ Authentication works end-to-end

---

### 5.5: Create Ultra-Simple docker-compose.yml ✅

**Goal:** 3-container deployment with SQLite embedded

**File:** `docker-compose.yml`

```yaml
version: '3.8'

services:
  # ============================================================================
  # FaultMaven Core - Modular Monolith (API + Dashboard)
  # ============================================================================
  faultmaven:
    build: .
    image: ghcr.io/faultmaven/faultmaven:latest
    container_name: faultmaven

    ports:
      - "8000:8000"

    environment:
      # Database (SQLite - embedded, no container needed)
      - DATABASE_URL=sqlite+aiosqlite:///data/faultmaven.db

      # Cache/Sessions (Redis)
      - REDIS_URL=redis://redis:6379/0

      # Vector DB (ChromaDB)
      - CHROMA_URL=http://chromadb:8000

      # LLM Provider (user configures via .env)
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - LLM_PROVIDER=${LLM_PROVIDER:-openai}

      # Storage (local files)
      - STORAGE_PROVIDER=local
      - STORAGE_PATH=/data/uploads

      # Environment
      - ENVIRONMENT=production

    volumes:
      # Single volume for EVERYTHING (database + uploads)
      - ./data:/data

    depends_on:
      redis:
        condition: service_healthy
      chromadb:
        condition: service_started

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

    restart: unless-stopped

  # ============================================================================
  # Redis - Sessions & Cache
  # ============================================================================
  redis:
    image: redis:7-alpine
    container_name: faultmaven-redis

    command: redis-server --appendonly yes

    ports:
      - "6379:6379"

    volumes:
      - redis_data:/data

    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

    restart: unless-stopped

  # ============================================================================
  # ChromaDB - Vector Database for Semantic Search
  # ============================================================================
  chromadb:
    image: chromadb/chroma:latest
    container_name: faultmaven-chromadb

    ports:
      - "8001:8000"

    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE

    volumes:
      - chroma_data:/chroma/chroma

    restart: unless-stopped

volumes:
  redis_data:
  chroma_data:
```

**Key Features:**
- 3 containers only (was 12)
- SQLite embedded (no PostgreSQL container)
- Health checks on all services
- Single data volume (`./data/`)
- Environment variable configuration

**Data Persistence:**

```
./data/
├── faultmaven.db          # SQLite database (all metadata)
└── uploads/               # User-uploaded files
    ├── documents/
    │   └── user_001/
    │       └── abc123_error.log
    └── evidence/
        └── case_456/
            └── screenshot.png
```

**Backup Strategy:**
```bash
# Backup entire FaultMaven state
zip -r faultmaven-backup-$(date +%Y%m%d).zip ./data

# Restore on another machine
unzip faultmaven-backup-20241224.zip
./faultmaven start
```

**Success Criteria:**
- ✅ `docker-compose up -d` works
- ✅ All 3 services start healthy
- ✅ Dashboard accessible at http://localhost:8000
- ✅ API accessible at http://localhost:8000/api/v1/*
- ✅ Data persists in `./data/` folder

---

### 5.6: Create ./faultmaven CLI Wrapper ✅

**Goal:** One-command deployment with validation

**File:** `faultmaven` (executable script)

```bash
#!/bin/bash
#
# FaultMaven Core - CLI Wrapper
# Simplifies deployment with pre-flight checks and resource management
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}✗ Docker is not running${NC}"
        echo "Please start Docker and try again"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker is running${NC}"
}

# Check system RAM
check_ram() {
    total_ram=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$total_ram" -lt 4 ]; then
        echo -e "${YELLOW}⚠️  Warning: System has ${total_ram}GB RAM (4GB+ recommended)${NC}"
    else
        echo -e "${GREEN}✅ System has ${total_ram}GB RAM${NC}"
    fi
}

# Check .env file exists
check_env() {
    if [ ! -f .env ]; then
        echo -e "${YELLOW}⚠️  No .env file found. Copying from .env.example...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}⚠️  Please edit .env and add your LLM API key${NC}"
        exit 1
    fi

    # Check if API key is set
    if ! grep -q "OPENAI_API_KEY=sk-" .env && ! grep -q "ANTHROPIC_API_KEY=sk-ant-" .env; then
        echo -e "${YELLOW}⚠️  No LLM API key found in .env${NC}"
        echo "Please add OPENAI_API_KEY or ANTHROPIC_API_KEY to .env"
        exit 1
    fi

    echo -e "${GREEN}✅ Environment file configured${NC}"
}

# Start services
start() {
    echo "Starting FaultMaven Core..."
    check_docker
    check_ram
    check_env

    echo ""
    echo "Starting containers..."
    docker-compose up -d

    echo ""
    echo -e "${GREEN}✅ FaultMaven started successfully!${NC}"
    echo ""
    echo "Access FaultMaven at: http://localhost:8000"
    echo ""
    echo "Next steps:"
    echo "  - Check status: ./faultmaven status"
    echo "  - View logs:    ./faultmaven logs"
    echo "  - Stop:         ./faultmaven stop"
}

# Stop services
stop() {
    echo "Stopping FaultMaven..."
    docker-compose down
    echo -e "${GREEN}✅ FaultMaven stopped${NC}"
}

# Show status
status() {
    docker-compose ps
    echo ""
    echo "Health check:"
    curl -s http://localhost:8000/health | python3 -m json.tool || echo "Service not responding"
}

# Show logs
logs() {
    if [ -z "$2" ]; then
        docker-compose logs -f faultmaven
    else
        docker-compose logs -f "$2"
    fi
}

# Backup data
backup() {
    backup_file="faultmaven-backup-$(date +%Y%m%d-%H%M%S).zip"
    echo "Creating backup: $backup_file"
    zip -r "$backup_file" ./data
    echo -e "${GREEN}✅ Backup created: $backup_file${NC}"
}

# Clean everything (WARNING: deletes data)
clean() {
    echo -e "${RED}WARNING: This will delete ALL data${NC}"
    read -p "Are you sure? (type 'yes' to confirm): " confirm
    if [ "$confirm" = "yes" ]; then
        docker-compose down -v
        rm -rf ./data
        echo -e "${GREEN}✅ All data deleted${NC}"
    else
        echo "Cancelled"
    fi
}

# Show help
help() {
    cat << EOF
FaultMaven Core - CLI Wrapper

Usage: ./faultmaven <command>

Commands:
  start      Start all services
  stop       Stop all services
  status     Show service status and health
  logs       View logs (optionally specify service name)
  backup     Create backup of data folder
  clean      Delete all data (WARNING: irreversible)
  help       Show this help message

Examples:
  ./faultmaven start
  ./faultmaven logs
  ./faultmaven logs faultmaven
  ./faultmaven backup
EOF
}

# Main command dispatcher
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
        status
        ;;
    logs)
        logs "$@"
        ;;
    backup)
        backup
        ;;
    clean)
        clean
        ;;
    help|--help|-h|"")
        help
        ;;
    *)
        echo "Unknown command: $1"
        echo "Run './faultmaven help' for usage"
        exit 1
        ;;
esac
```

**Make executable:**
```bash
chmod +x faultmaven
```

**Success Criteria:**
- ✅ `./faultmaven start` checks Docker, RAM, .env
- ✅ `./faultmaven status` shows health check
- ✅ `./faultmaven logs` follows container logs
- ✅ `./faultmaven backup` creates zip file

---

### 5.7: Create .env.example Template ✅

**File:** `.env.example`

```bash
# FaultMaven Core Configuration
# Copy this file to .env and configure

# ============================================================================
# LLM Provider - REQUIRED (configure at least one)
# ============================================================================
# Get API keys:
#   OpenAI: https://platform.openai.com/api-keys
#   Anthropic: https://console.anthropic.com/

# Cloud LLM (recommended - best performance)
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...

# LLM Provider (openai, anthropic, etc.)
LLM_PROVIDER=openai

# ============================================================================
# Database Configuration (DO NOT CHANGE for Core)
# ============================================================================
# SQLite is embedded - no configuration needed
DATABASE_URL=sqlite+aiosqlite:///data/faultmaven.db

# ============================================================================
# Optional: Advanced Settings
# ============================================================================
# Environment (development, production)
ENVIRONMENT=production

# Log Level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

---

## File Structure After Phase 5

```
faultmaven/
├── dashboard/                    # NEW: React dashboard source
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   └── dist/                    # Build output (gitignored)
├── src/
│   └── faultmaven/
│       ├── app.py              # MODIFIED: Serve static files
│       ├── database.py         # MODIFIED: Deployment-neutral config
│       ├── modules/
│       └── providers/
├── alembic/
│   ├── env.py                  # MODIFIED: render_as_batch=True
│   └── versions/
├── data/                        # NEW: Persistent data (gitignored)
│   ├── faultmaven.db           # SQLite database
│   └── uploads/                # User files
├── Dockerfile                   # NEW: Multi-stage build
├── docker-compose.yml          # NEW: 3-container setup
├── faultmaven                  # NEW: CLI wrapper (executable)
├── .env.example                # NEW: Configuration template
├── pyproject.toml
└── README.md
```

---

## Implementation Strategy

### Progressive Approach (Recommended)

**Week 1: Dashboard Integration**
- Day 1: Copy dashboard source, verify builds
- Day 2: Create multi-stage Dockerfile
- Day 3: Configure FastAPI static file serving
- Day 4: Test bundled deployment locally
- Day 5: Fix issues, optimize

**Week 2: Deployment Simplification**
- Day 1: Create docker-compose.yml (3 containers)
- Day 2: Create `./faultmaven` CLI wrapper
- Day 3: Test end-to-end deployment
- Day 4: Update Alembic for deployment neutrality
- Day 5: Documentation and validation

---

## Deployment Neutrality Checklist

### Code Level
- ✅ Use SQLAlchemy ORM (not raw SQL)
- ✅ Use `sqlalchemy.types.JSON` (not `JSONB`)
- ✅ Configure Alembic `render_as_batch=True`
- ✅ Environment-based engine configuration

### Infrastructure Level
- ✅ `DATABASE_URL` env var determines database
- ✅ Provider interfaces for all external services
- ✅ Same Docker image for Core and Enterprise

### Migration Level
- ✅ All migrations work on SQLite AND PostgreSQL
- ✅ Test migrations on both databases
- ✅ No PostgreSQL-specific SQL in migrations

---

## Success Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| **Containers** | 3 | TBD |
| **Ports** | 1 (8000) | TBD |
| **Docker Image Size** | <500MB | TBD |
| **Build Time** | <5 minutes | TBD |
| **Startup Time** | <30 seconds | TBD |
| **Dashboard Load Time** | <2 seconds | TBD |

---

## Testing Strategy

### Local Testing
```bash
# Build and start
docker-compose build
./faultmaven start

# Verify services
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/auth/health

# Test dashboard
open http://localhost:8000

# Test data persistence
./faultmaven stop
./faultmaven start
# Verify data still exists

# Test backup
./faultmaven backup
```

### Deployment Neutrality Testing
```bash
# Test SQLite (Core)
DATABASE_URL=sqlite+aiosqlite:///data/faultmaven.db
./faultmaven start
# Run tests

# Test PostgreSQL (Enterprise simulation)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/test
docker-compose up -d
# Run same tests
```

---

## Risk Assessment

### Low Risk ✅
- Dashboard bundling (well-documented pattern)
- SQLite usage (proven for single-user)
- Docker multi-stage build (standard)

### Medium Risk ⚠️
- Static file serving with FastAPI (need proper caching)
- Dashboard API URL configuration (CORS/routing)
- File permissions in Docker (Linux user ID mapping)

### High Risk 🔴
- Database migration compatibility (SQLite vs PostgreSQL)
- **Mitigation:** Test ALL migrations on both databases before deploy

---

## Rollback Plan

If Phase 5 fails:

1. **Keep microservices temporarily**
   - Continue using faultmaven-deploy repo
   - Delay monolith migration

2. **Hybrid approach**
   - API as monolith
   - Dashboard as separate container (Nginx)

3. **Use PostgreSQL instead of SQLite**
   - Add postgres container (4 total)
   - Simplifies migration compatibility

**Rollback Time:** <2 hours (revert docker-compose.yml)

---

## Next Phase

**Phase 6: CI/CD & Deployment Consolidation**
- Consolidate GitHub workflows (40+ → 1)
- Create GitHub Container Registry workflow
- Update Kubernetes manifests (for Enterprise)
- Archive old microservice repositories

---

**Created:** 2024-12-24
**Ready to Start:** Yes ✅
**Estimated Effort:** 1-2 weeks
**Previous Phase:** Phase 4 (Job Worker Cleanup - Complete)
**Next Phase:** Phase 6 (CI/CD Consolidation)
