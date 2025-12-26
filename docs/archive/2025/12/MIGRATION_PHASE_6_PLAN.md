# Migration Phase 6: Deployment Consolidation - Implementation Plan

**Status:** 📋 **PLANNED** (2024-12-24)

**Goal:** Consolidate deployment infrastructure, CI/CD workflows, and documentation for single-container architecture.

---

## Overview

Simplify deployment configuration and automation by consolidating 8+ microservice deployments into a single monolith deployment.

### Consolidation Summary

| Component | Before | After | Reduction |
|-----------|--------|-------|-----------|
| **GitHub Workflows** | 8+ (per service) | 1 | 88% fewer files |
| **Kubernetes Deployments** | 8 | 1 | 87.5% reduction |
| **Docker Images** | 8 | 1 | 87.5% reduction |
| **Helm Charts** | 8 | 1 | 87.5% reduction |
| **docker-compose services** | 10+ | 3 (app, db, redis) | 70% reduction |

---

## Prerequisites

- ✅ Phase 1: Provider Abstraction (Complete)
- ✅ Phase 2: Module Migration (Complete)
- ✅ Phase 3: API Layer (Complete)
- ✅ Phase 4: Job Worker Cleanup (Complete)
- ⏳ Phase 5: Dashboard Integration (Next)
- ⏳ Phase 3.1: Testing (In progress)

---

## Implementation Tasks

### 6.1 Consolidate CI/CD Workflows ✅

**Goal:** Replace 8+ service-specific workflows with 1 monolith workflow

#### Current State Analysis

**Existing Workflows (per service):**
- `ci.yml` - Run tests, linting
- `docker-publish.yml` - Build and push Docker image
- `generate-docs.yml` - Generate API documentation
- `policy-no-direct-k8s-deploy.yml` - Deployment policy enforcement
- `cd.yml` - Continuous deployment

**Total:** ~40+ workflow files across 8 services

#### Target Workflow

**File:** `.github/workflows/ci-cd.yml`

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # Job 1: Lint & Test
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -e .[dev]

      - name: Lint with ruff
        run: ruff check src/

      - name: Type check with mypy
        run: mypy src/

      - name: Check module boundaries
        run: import-linter

      - name: Run tests
        run: pytest tests/ -v --cov=faultmaven --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml

  # Job 2: Build Dashboard
  build-dashboard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install pnpm
        run: npm install -g pnpm

      - name: Build dashboard
        run: |
          cd dashboard
          pnpm install --frozen-lockfile
          pnpm run build

      - name: Upload dashboard artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dashboard-build
          path: dashboard/dist/

  # Job 3: Build Docker Image
  build-image:
    needs: [test, build-dashboard]
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # Job 4: Deploy (on main branch only)
  deploy:
    needs: build-image
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/faultmaven \
            faultmaven=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          kubectl rollout status deployment/faultmaven
```

**Success Criteria:**
- ✅ All jobs pass on main branch
- ✅ Docker image builds successfully
- ✅ Tests run and pass
- ✅ Dashboard builds and is bundled
- ✅ Image pushed to registry

---

### 6.2 Update docker-compose.yml ✅

**Goal:** Consolidate 10+ services to 3 core services

**File:** [docker-compose.yml](../docker-compose.yml)

**Implementation:**

```yaml
version: '3.8'

services:
  # Single FaultMaven service (API + Dashboard + All modules)
  faultmaven:
    build:
      context: .
      dockerfile: Dockerfile
    image: faultmaven:latest
    ports:
      - "8000:8000"
    environment:
      # Database
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/faultmaven

      # Cache/Sessions
      - REDIS_URL=redis://redis:6379/0

      # LLM Provider
      - LLM_PROVIDER=${LLM_PROVIDER:-openai}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

      # Vector DB
      - VECTOR_PROVIDER=${VECTOR_PROVIDER:-chromadb}
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8001

      # Security
      - JWT_SECRET=${JWT_SECRET:-dev-secret-change-in-production}
      - JWT_ALGORITHM=HS256
      - JWT_EXPIRY_MINUTES=1440

      # Environment
      - ENVIRONMENT=${ENVIRONMENT:-development}

    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      chromadb:
        condition: service_started

    volumes:
      - ./data:/app/data
      - ./logs:/app/logs

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

    restart: unless-stopped

  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: faultmaven
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_INITDB_ARGS: "-E UTF8"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # Redis (Cache + Sessions)
  redis:
    image: redis:7-alpine
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

  # ChromaDB (Vector Database)
  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chromadb_data:/chroma/chroma
    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  chromadb_data:
```

**Changes from OLD:**
- ❌ Removed 7+ service containers (fm-auth, fm-session, fm-case, etc.)
- ❌ Removed fm-job-worker
- ❌ Removed fm-api-gateway (now middleware)
- ❌ Removed faultmaven-dashboard (now bundled)
- ✅ Added chromadb service (vector database)
- ✅ Single faultmaven service with all modules

**Success Criteria:**
- ✅ `docker-compose up` works
- ✅ All services start healthy
- ✅ Dashboard accessible at http://localhost:8000
- ✅ API accessible at http://localhost:8000/api/*

---

### 6.3 Update Kubernetes Manifests ✅

**Goal:** Consolidate 8 Deployments into 1

#### Current State

**Existing Deployments (faultmaven-deploy repo):**
- fm-auth-service
- fm-session-service
- fm-case-service
- fm-evidence-service
- fm-knowledge-service
- fm-agent-service
- fm-api-gateway
- fm-job-worker
- faultmaven-dashboard

**Total:** 9 Deployment manifests + Services + ConfigMaps

#### Target Manifest

**File:** `deploy/kubernetes/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: faultmaven
  namespace: faultmaven
  labels:
    app: faultmaven
    version: v1
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: faultmaven
  template:
    metadata:
      labels:
        app: faultmaven
        version: v1
    spec:
      containers:
      - name: faultmaven
        image: ghcr.io/faultmaven/faultmaven:latest
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: faultmaven-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: faultmaven-secrets
              key: redis-url
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: faultmaven-secrets
              key: jwt-secret
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: faultmaven-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
        volumeMounts:
        - name: data
          mountPath: /app/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: faultmaven-data

---
apiVersion: v1
kind: Service
metadata:
  name: faultmaven
  namespace: faultmaven
spec:
  type: LoadBalancer
  selector:
    app: faultmaven
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
    name: http

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: faultmaven
  namespace: faultmaven
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: faultmaven
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

**Success Criteria:**
- ✅ Deployment creates pods successfully
- ✅ Health checks pass
- ✅ Service is accessible
- ✅ HPA scales based on load

---

### 6.4 Update Helm Charts ✅

**Goal:** Single chart for monolith

**File:** `deploy/helm/faultmaven/Chart.yaml`

```yaml
apiVersion: v2
name: faultmaven
description: FaultMaven Modular Monolith
type: application
version: 1.0.0
appVersion: "1.0.0"
```

**File:** `deploy/helm/faultmaven/values.yaml`

```yaml
replicaCount: 3

image:
  repository: ghcr.io/faultmaven/faultmaven
  pullPolicy: IfNotPresent
  tag: "latest"

service:
  type: LoadBalancer
  port: 80
  targetPort: 8000

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: faultmaven.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: faultmaven-tls
      hosts:
        - faultmaven.example.com

resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

postgresql:
  enabled: true
  auth:
    username: faultmaven
    password: changeme
    database: faultmaven

redis:
  enabled: true
  auth:
    enabled: false

chromadb:
  enabled: true
  persistence:
    enabled: true
    size: 10Gi
```

**Success Criteria:**
- ✅ `helm install faultmaven ./helm/faultmaven` works
- ✅ All resources created
- ✅ Application is accessible

---

### 6.5 Update Documentation ✅

**Goal:** Document new deployment architecture

**Files to Update:**

1. **README.md**
   - Single-container deployment instructions
   - Simplified architecture diagram

2. **DEPLOYMENT.md**
   - Docker deployment guide
   - Kubernetes deployment guide
   - Helm chart usage

3. **DEVELOPMENT.md**
   - Local development with bundled dashboard
   - Running tests

4. **ARCHITECTURE.md**
   - Modular monolith architecture
   - Module boundaries
   - Provider abstraction

**Success Criteria:**
- ✅ All documentation reflects new architecture
- ✅ No references to old microservices
- ✅ Clear deployment instructions

---

## Implementation Strategy

### Week 1: CI/CD Consolidation
- Day 1-2: Create consolidated workflow, test on PR
- Day 3: Migrate secrets, update registry permissions
- Day 4-5: Test full pipeline, debug issues

### Week 2: Deployment Updates
- Day 1: Update docker-compose.yml, test locally
- Day 2: Update Kubernetes manifests
- Day 3: Update Helm charts
- Day 4: Test deployment to staging
- Day 5: Deploy to production

### Week 3: Documentation & Cleanup
- Day 1-2: Update all documentation
- Day 3: Archive old service repositories
- Day 4: Clean up old workflows
- Day 5: Final testing and validation

---

## Success Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Deployment Time** | ~20 min (8 services) | ~5 min (1 service) | 75% faster |
| **CI/CD Runtime** | ~30 min (parallel) | ~10 min | 66% faster |
| **Workflow Files** | 40+ | 1 | 97% reduction |
| **Docker Images** | 8 | 1 | 87.5% reduction |
| **Kubernetes Resources** | 50+ | ~10 | 80% reduction |

---

## Risk Assessment

### Low Risk
- ✅ docker-compose consolidation (straightforward)
- ✅ Documentation updates (manual, reversible)

### Medium Risk
- ⚠️ **CI/CD workflow** - May need iteration to get right
- ⚠️ **Kubernetes deployment** - Need careful rollout strategy

### High Risk
- 🔴 **Production deployment** - Single point of failure
- 🔴 **Rollback complexity** - Harder to rollback monolith than individual services

**Mitigation:**
- Blue/green deployment for zero downtime
- Keep old infrastructure for 30 days as backup
- Comprehensive staging environment testing

---

## Rollback Plan

If Phase 6 fails:

1. **Keep old workflows** - Run in parallel temporarily
2. **Gradual migration** - Migrate one service at a time
3. **Hybrid approach** - API as monolith, dashboard separate

**Rollback Time:** <4 hours (revert to old docker-compose + workflows)

---

## Archive Strategy

After successful Phase 6 completion:

### Repositories to Archive
- fm-auth-service
- fm-session-service
- fm-case-service
- fm-evidence-service
- fm-knowledge-service
- fm-agent-service
- fm-api-gateway
- fm-job-worker
- fm-core-lib (absorbed into monolith)

### Keep Active
- faultmaven (primary)
- faultmaven-copilot (separate distribution)
- faultmaven-website (marketing)

**Archive Message:**
```
This repository has been archived as part of the FaultMaven modular monolith migration.
All functionality has been migrated to: https://github.com/FaultMaven/faultmaven

See migration documentation: https://github.com/FaultMaven/faultmaven/blob/main/docs/MIGRATION.md
```

---

## Next Steps After Phase 6

1. **Performance Optimization**
   - Database query optimization
   - Caching strategy refinement
   - Load testing and tuning

2. **Observability Enhancement**
   - Centralized logging (ELK stack)
   - Distributed tracing (OpenTelemetry)
   - Metrics dashboard (Grafana)

3. **Feature Development**
   - Resume new feature development
   - Leverage simplified architecture

---

**Created:** 2024-12-24
**Ready to Start:** After Phase 5 complete
**Estimated Effort:** 2-3 weeks
**Previous Phase:** Phase 5 (Dashboard Integration)
**Next Phase:** Feature development resumes
