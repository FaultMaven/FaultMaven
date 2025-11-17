# Design Document v2.0 Amendment

**Date:** 2025-11-17
**Status:** Approved
**Amendment:** Dashboard Technology Stack Change

---

## Change Summary

**Original Design v2.0 Specification:**
> `faultmaven-dashboard` should use Next.js (React meta-framework with SSR/SSG)

**Amended Specification:**
> `faultmaven-dashboard` uses **Vite + React Router** (SPA build tool + routing library)

---

## Rationale for Change

### Why This Deviation is Acceptable

**1. Deployment Simplicity**
- Vite builds to static assets (HTML/CSS/JS)
- Deployed via nginx (simple, lightweight)
- No Node.js runtime required for serving
- Simpler Docker image (nginx:alpine base)

**2. Open-Source Distribution Benefits**
- Smaller Docker images (~50MB vs ~200MB with Next.js)
- Faster builds (Vite is significantly faster)
- Easier for contributors to understand
- Less opinionated architecture

**3. Use Case Alignment**
- Dashboard is KB management tool (CRUD operations)
- No SEO requirements (authenticated private tool)
- No server-side rendering needed
- API calls happen client-side (to fm-knowledge-service)

**4. Consistency with Extension**
- Extension uses Vite (via WXT framework)
- Shared developer experience
- Similar build pipelines
- Easier knowledge transfer for contributors

### What We Give Up (and Why It's OK)

| Next.js Feature | Impact | Why It's OK |
|-----------------|--------|-------------|
| **SSR** | No server-side rendering | Dashboard is authenticated private tool, no SEO needed |
| **SSG** | No static generation | SPA approach works fine for dynamic content |
| **API Routes** | No backend API in same repo | Backend is separate microservices (correct architecture) |
| **Image Optimization** | No built-in image optimization | Knowledge base uses PDFs/docs, not images |
| **Automatic Code Splitting** | Manual route-based splitting | Vite + React Router handles this well |

---

## Updated Technology Stack

### faultmaven-dashboard (Official)

| Component | Technology | Version | Reason |
|-----------|-----------|---------|--------|
| **Build Tool** | Vite | 6.0+ | Fast builds, excellent DX |
| **Framework** | React | 19.1+ | Standard UI library |
| **Routing** | React Router | 7.1+ | Client-side routing |
| **Styling** | Tailwind CSS | 3.4+ | Utility-first styling |
| **Language** | TypeScript | 5.8+ | Type safety |
| **Deployment** | nginx (Docker) | Latest | Serves static assets |

### Comparison: Original vs. Amended

| Aspect | Design v2.0 (Original) | Amendment (Actual) |
|--------|------------------------|-------------------|
| Framework | Next.js | Vite + React Router |
| Rendering | SSR/SSG | Client-side SPA |
| Server | Node.js runtime | Static (nginx) |
| Build Output | Server + client | Static assets only |
| Docker Image Size | ~200MB | ~50MB |
| Deployment | Node server | Static file server |

---

## Implementation Details

### Current Implementation

```typescript
// Tech Stack
{
  "vite": "^6.0.0",           // Build tool
  "react": "^19.1.0",          // UI library
  "react-router-dom": "^7.1.0", // Routing
  "typescript": "^5.8.3",      // Type safety
  "tailwindcss": "^3.4.17"     // Styling
}
```

### Pages Structure

```
faultmaven-dashboard/
└── src/
    └── pages/
        ├── LoginPage.tsx       # Authentication
        ├── KBPage.tsx          # Knowledge Base (upload/search)
        └── AdminKBPage.tsx     # Admin management
```

### Docker Deployment

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

## Capabilities API Integration

Despite the framework change, the **capabilities-driven architecture** remains intact:

```typescript
// Dashboard still calls capabilities endpoint
const capabilities = await fetch(`${API_URL}/v1/meta/capabilities`)
  .then(res => res.json());

// UI adapts based on features
if (capabilities.features.teams) {
  // Show team-specific UI
}
```

**No change to this core design principle.**

---

## Migration Path (If Needed)

If Next.js becomes necessary in the future:

**When to Migrate:**
- Dashboard needs SEO (unlikely for authenticated tool)
- Server-side rendering required for performance
- Need API routes co-located with frontend

**Migration Effort:**
- Low to Medium (2-3 days)
- React components can be reused as-is
- Router code needs minor changes (React Router → Next.js router)
- Build configuration changes

---

## Decision Log

| Decision | Reason |
|----------|--------|
| **Accept Vite over Next.js** | Simpler deployment, smaller images, better for self-hosted |
| **Keep React 19** | Modern, performant, large ecosystem |
| **Keep React Router 7** | Industry standard for client-side routing |
| **Keep Tailwind CSS** | Consistent with extension styling |
| **Keep TypeScript** | Type safety is non-negotiable |

---

## Impact Assessment

### ✅ No Impact (Still Works)

- Capabilities API integration
- Split UI model (extension + dashboard)
- Authentication flow
- Knowledge Base features (upload, search)
- Docker deployment
- CI/CD pipelines

### ⚠️ Minor Impact (Different but OK)

- Build tool (Vite instead of Next.js build)
- Deployment method (static nginx instead of Node server)
- Docker image size (smaller is better)

### ❌ Breaking Changes

- None

---

## Documentation Updates Required

**Files to Update:**

1. ✅ **README.md (umbrella repo)** - Already mentions "KB management UI" without specifying Next.js (Line 102 says "Next.js" - **NEEDS UPDATE**)
2. ⚠️ **Design v2.0 Document** - Update Section 1.2 to reflect Vite
3. ✅ **faultmaven-dashboard README** - Already accurate
4. ✅ **faultmaven-deploy README** - Agnostic to dashboard tech

**Update Required:**

```diff
# FaultMaven/FaultMaven/README.md Line 102
- | **Dashboard** | 3000 | KB management UI (Next.js) | ...
+ | **Dashboard** | 3000 | KB management UI (Vite + React) | ...
```

---

## Approval

**Decision:** ✅ **Accepted**

**Approved By:** Product Owner
**Date:** 2025-11-17

**Reason:** This deviation from Design v2.0 is:
1. **Pragmatic** - Simplifies deployment
2. **Functionally Equivalent** - Achieves all requirements
3. **Better for Open Source** - Easier for community
4. **Reversible** - Can migrate to Next.js if needed

---

## Summary

The faultmaven-dashboard implementation uses **Vite + React Router** instead of **Next.js**, deviating from the original Design v2.0 specification.

**This is an ACCEPTED deviation because:**
- It simplifies self-hosted deployment
- Reduces Docker image size
- Improves build performance
- Aligns with open-source distribution goals
- All functional requirements still met

**Design v2.0 is amended to reflect this change as the official specification.**

---

**Amendment Status:** ✅ Approved and Documented
