# Migration Phase 5: Dashboard Integration - Implementation Plan

**Status:** 🔜 **READY TO START** (2024-12-24)

**Goal:** Bundle the React dashboard into the monolith for single-container deployment.

---

## Overview

Integrate the faultmaven-dashboard React application into the faultmaven monolith repository, enabling a single Docker container to serve both the API and the web UI.

### Architecture Change

| Aspect | Before | After |
|--------|--------|-------|
| **Deployable Units** | 2 (API + Dashboard) | 1 (Bundled) |
| **Containers** | 2 | 1 |
| **Build Process** | Separate builds | Multi-stage Dockerfile |
| **Static Files** | Nginx/separate server | FastAPI StaticFiles |
| **Deployment** | 2 services in docker-compose | 1 service |

---

## Prerequisites

- ✅ Phase 1: Provider Abstraction (Complete)
- ✅ Phase 2: Module Migration (Complete)
- ✅ Phase 3: API Layer (Complete - 88 endpoints)
- ✅ Phase 4: Job Worker Cleanup (Complete)
- ⏳ Phase 3.1: Testing (In progress with testing agent)

---

## Implementation Tasks

### 5.1 Copy Dashboard Source ✅

**Goal:** Move dashboard source into monolith repository

**Tasks:**
1. Create `faultmaven/dashboard/` directory
2. Copy entire `faultmaven-dashboard/` contents to `faultmaven/dashboard/`
3. Verify dashboard builds independently
4. Update dashboard API endpoint configuration

**Commands:**
```bash
cd /home/swhouse/product/faultmaven
mkdir -p dashboard
cp -r ../faultmaven-dashboard/* dashboard/
cd dashboard
pnpm install
pnpm run build
```

**Success Criteria:**
- ✅ Dashboard builds successfully
- ✅ `dashboard/dist/` or `dashboard/build/` contains static files
- ✅ No build errors

---

### 5.2 Create Multi-Stage Dockerfile ✅

**Goal:** Build dashboard and Python API in single Docker image

**File:** `Dockerfile`

**Implementation:**

```dockerfile
# Stage 1: Build React Dashboard
FROM node:20-alpine AS dashboard-builder

WORKDIR /app/dashboard

# Copy dashboard source
COPY dashboard/package.json dashboard/pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install --frozen-lockfile

COPY dashboard/ .

# Build production bundle
RUN pnpm run build

# Stage 2: Python API + Static Files
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy dashboard build artifacts
COPY --from=dashboard-builder /app/dashboard/dist /app/static/dashboard

# Copy Python source
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run application
CMD ["uvicorn", "faultmaven.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Success Criteria:**
- ✅ Docker image builds successfully
- ✅ Image contains both API and dashboard files
- ✅ Image size is reasonable (<500MB)

---

### 5.3 Configure FastAPI Static File Serving ✅

**Goal:** Serve dashboard from FastAPI

**File:** [src/faultmaven/app.py](../src/faultmaven/app.py)

**Implementation:**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = create_app()

# Serve dashboard static files
dashboard_path = Path(__file__).parent.parent.parent / "static" / "dashboard"
if dashboard_path.exists():
    app.mount("/dashboard", StaticFiles(directory=str(dashboard_path), html=True), name="dashboard")

    # Serve dashboard at root (/)
    app.mount("/", StaticFiles(directory=str(dashboard_path), html=True), name="dashboard-root")
```

**Routing Strategy:**
- `/api/*` - FastAPI routes (already exist)
- `/dashboard` - Dashboard static files
- `/` - Dashboard (index.html)

**Success Criteria:**
- ✅ Dashboard accessible at `http://localhost:8000/`
- ✅ API accessible at `http://localhost:8000/api/*`
- ✅ Static assets (JS, CSS, images) load correctly

---

### 5.4 Update Dashboard API Configuration ✅

**Goal:** Point dashboard to bundled API

**File:** `dashboard/.env.production` or `dashboard/vite.config.ts`

**Implementation:**

```javascript
// vite.config.ts
export default defineConfig({
  // ...
  define: {
    // Use relative URLs (same origin)
    'process.env.VITE_API_BASE_URL': JSON.stringify('/api')
  }
})
```

Or update dashboard code to use relative API paths:
```typescript
// Before
const API_BASE = 'http://localhost:8001/api'

// After
const API_BASE = '/api'  // Same origin
```

**Success Criteria:**
- ✅ Dashboard makes API calls to `/api/*` (same origin)
- ✅ No CORS errors
- ✅ Authentication works end-to-end

---

### 5.5 Update docker-compose.yml ✅

**Goal:** Single service deployment

**File:** [docker-compose.yml](../docker-compose.yml)

**Implementation:**

```yaml
version: '3.8'

services:
  faultmaven:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/faultmaven
      - REDIS_URL=redis://redis:6379/0
      - LLM_PROVIDER=openai
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - JWT_SECRET=${JWT_SECRET:-dev-secret-key}
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: faultmaven
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

**Changes from OLD:**
- ❌ Removed `faultmaven-dashboard` service
- ❌ Removed `fm-job-worker` service (Phase 4)
- ❌ Removed `nginx` service (if it existed)
- ✅ Single `faultmaven` service serves API + Dashboard

**Success Criteria:**
- ✅ `docker-compose up` starts 3 containers (API, Postgres, Redis)
- ✅ Dashboard accessible at `http://localhost:8000/`
- ✅ API accessible at `http://localhost:8000/api/*`

---

### 5.6 Test Bundled Deployment ✅

**Goal:** Verify end-to-end functionality

**Test Scenarios:**

1. **Local Build Test**
   ```bash
   docker build -t faultmaven:latest .
   docker run -p 8000:8000 faultmaven:latest
   ```
   - ✅ Image builds without errors
   - ✅ Container starts successfully
   - ✅ Dashboard loads at http://localhost:8000
   - ✅ API responds at http://localhost:8000/api/health

2. **Docker Compose Test**
   ```bash
   docker-compose up --build
   ```
   - ✅ All services start
   - ✅ Dashboard loads and is functional
   - ✅ Login/authentication works
   - ✅ API calls succeed (cases, sessions, knowledge)

3. **Production Build Test**
   ```bash
   docker build -t faultmaven:prod --target production .
   ```
   - ✅ Production optimizations applied
   - ✅ No source maps in production
   - ✅ Minified assets

**Success Criteria:**
- ✅ All test scenarios pass
- ✅ No console errors in browser
- ✅ No API errors in server logs
- ✅ End-to-end user flow works (login → create case → add evidence)

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
│       ├── modules/
│       └── providers/
├── static/                      # NEW: Copied during Docker build
│   └── dashboard/              # Dashboard build artifacts
├── Dockerfile                   # NEW: Multi-stage build
├── docker-compose.yml          # MODIFIED: Single service
├── pyproject.toml
└── README.md
```

---

## Implementation Strategy

### Option A: Progressive Integration (Recommended)

**Week 1:**
1. Day 1: Copy dashboard source, verify builds independently
2. Day 2: Create multi-stage Dockerfile, test image builds
3. Day 3: Configure FastAPI static files, test local serving
4. Day 4: Update dashboard API config, test end-to-end
5. Day 5: Update docker-compose, test full deployment

### Option B: Big Bang (Faster but Riskier)

**3 Days:**
1. Day 1: Copy dashboard + create Dockerfile + configure FastAPI
2. Day 2: Test and debug integration issues
3. Day 3: Update docker-compose + documentation

**Recommendation:** Use Option A for production, Option B if time-constrained.

---

## Risk Assessment

### Low Risk
- ✅ Dashboard already exists and works
- ✅ FastAPI StaticFiles is well-documented
- ✅ Multi-stage Docker builds are standard

### Medium Risk
- ⚠️ **API endpoint configuration** - Dashboard may need URL updates
- ⚠️ **CORS issues** - May need middleware configuration
- ⚠️ **Routing conflicts** - FastAPI routes vs static file paths

### High Risk
- 🔴 **Build size** - Docker image may be large (mitigation: multi-stage build)
- 🔴 **Environment variables** - Dashboard may have different env var names

**Mitigation:**
- Test locally before Docker build
- Use `.dockerignore` to reduce build size
- Document all environment variables

---

## Dependencies

### Required Tools
- ✅ Docker (installed)
- ✅ Node.js 20+ (for dashboard build)
- ✅ pnpm (for dashboard dependencies)

### Installation (if needed)
```bash
# Install pnpm
npm install -g pnpm

# Verify versions
node --version    # Should be 20+
pnpm --version    # Should be 8+
docker --version  # Should be 24+
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| **Docker Image Size** | <500MB |
| **Build Time** | <5 minutes |
| **Startup Time** | <30 seconds |
| **Dashboard Load Time** | <2 seconds |
| **API Response Time** | <500ms (p95) |

---

## Documentation Updates Needed

After Phase 5 completion:

1. **README.md** - Update deployment instructions
2. **DEPLOYMENT.md** - Single container deployment guide
3. **DEVELOPMENT.md** - Local development with bundled dashboard
4. **docker-compose.yml** - Comments explaining single service

---

## Rollback Plan

If Phase 5 fails:

1. **Keep separate deployments** - Dashboard and API as separate containers
2. **Use Nginx reverse proxy** - Traditional separation of concerns
3. **Defer to Phase 6** - Focus on other improvements first

**Rollback Time:** <1 hour (revert docker-compose.yml)

---

## Next Phase Preview

**Phase 6: Deployment Consolidation**
- CI/CD workflow consolidation (8 workflows → 1)
- Kubernetes manifest updates (8 deployments → 1)
- Helm chart simplification
- Documentation consolidation

---

**Created:** 2024-12-24
**Ready to Start:** Yes ✅
**Estimated Effort:** 3-5 days
**Previous Phase:** Phase 4 (Job Worker Cleanup - Complete)
**Next Phase:** Phase 6 (Deployment Consolidation)
