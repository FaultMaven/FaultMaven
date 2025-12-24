# Complete API Gap Analysis - Monolith vs Microservices

**Date**: 2025-12-21
**Microservices Spec**: 88 endpoints
**Monolith Implemented**: 39 endpoints
**Gap**: 49 missing endpoints (44.3% coverage)

---

## Summary

❌ **SIGNIFICANT GAPS IDENTIFIED**

The modular monolith has only implemented **39 out of 88 endpoints** (44.3% coverage). There are **49 missing endpoints** that need to be implemented for full API parity.

### Coverage by Module

| Module | Microservices | Monolith | Coverage | Status |
|--------|--------------|----------|----------|--------|
| **Agent** | 2 | 2 | 100% | ✅ Complete |
| **Auth** | 7 | 6 | 85.7% | ⚠️ Missing 1 |
| **Sessions** | 16 | 7 | 43.8% | ❌ Missing 9 |
| **Cases** | 32 | 10 | 31.3% | ❌ Missing 22 |
| **Evidence** | 8 | 6 | 75% | ⚠️ Missing 2 |
| **Knowledge** | 15 | 6 | 40% | ❌ Missing 9 |
| **Gateway** | 8 | 2 | 25% | ❌ Missing 6 |

---

## Detailed Gap Analysis

### 1. Agent Service ✅ (2/2 - 100%)

| Endpoint | Monolith | Status |
|----------|----------|--------|
| `POST /agent/chat/{case_id}` | ✅ | Implemented |
| `GET /agent/health` | ✅ | Implemented |

**Notes**: Agent service is complete.

---

### 2. Auth Service ⚠️ (6/7 - 85.7%)

| Microservices Endpoint | Monolith | Status |
|----------------------|----------|--------|
| `POST /auth/register` | ✅ `POST /auth/register` | Implemented |
| `POST /auth/login` | ✅ `POST /auth/login` | Implemented |
| `GET /auth/me` | ✅ `GET /auth/me` | Implemented |
| `POST /auth/logout` | ✅ `POST /auth/logout` | Implemented |
| `POST /auth/refresh` | ✅ `POST /auth/refresh` | Implemented |
| `GET /auth/health` | ✅ `GET /auth/health` | Implemented |
| `GET /.well-known/jwks.json` | ❌ | **MISSING** |
| `GET /.well-known/openid-configuration` | ❌ | **MISSING** |

**Missing Endpoints** (2):
- ❌ `GET /.well-known/jwks.json` - JWKS for JWT validation
- ❌ `GET /.well-known/openid-configuration` - OpenID Connect discovery

**Priority**: Medium (needed for external JWT validation)

---

### 3. Session Service ❌ (7/16 - 43.8%)

| Microservices Endpoint | Monolith | Status |
|----------------------|----------|--------|
| `POST /sessions` | ✅ `POST /sessions` | Implemented |
| `GET /sessions/{session_id}` | ✅ `GET /sessions/{session_id}` | Implemented |
| `PUT /sessions/{session_id}` | ✅ `PATCH /sessions/{session_id}` | Implemented (method diff) |
| `DELETE /sessions/{session_id}` | ✅ `DELETE /sessions/{session_id}` | Implemented |
| `GET /sessions` | ✅ `GET /sessions` | Implemented |
| `DELETE /sessions` | ✅ `DELETE /sessions` | Implemented |
| `GET /sessions/health` | ✅ `GET /sessions/health` | Implemented |
| `POST /sessions/{session_id}/heartbeat` | ❌ | **MISSING** |
| `POST /sessions/{session_id}/messages` | ❌ | **MISSING** |
| `GET /sessions/{session_id}/messages` | ❌ | **MISSING** |
| `GET /sessions/{session_id}/cases` | ❌ | **MISSING** |
| `GET /sessions/{session_id}/stats` | ❌ | **MISSING** |
| `POST /sessions/search` | ❌ | **MISSING** |
| `POST /sessions/{session_id}/archive` | ❌ | **MISSING** |
| `POST /sessions/{session_id}/restore` | ❌ | **MISSING** |
| `POST /sessions/cleanup` | ❌ | **MISSING** |
| `POST /sessions/{session_id}/cleanup` | ❌ | **MISSING** |
| `GET /sessions/{session_id}/recovery-info` | ❌ | **MISSING** |

**Missing Endpoints** (9):
- ❌ `POST /sessions/{session_id}/heartbeat` - Session activity tracking
- ❌ `POST /sessions/{session_id}/messages` - Add messages to session
- ❌ `GET /sessions/{session_id}/messages` - Retrieve session messages
- ❌ `GET /sessions/{session_id}/cases` - Get cases for session
- ❌ `GET /sessions/{session_id}/stats` - Session statistics
- ❌ `POST /sessions/search` - Search sessions
- ❌ `POST /sessions/{session_id}/archive` - Archive session
- ❌ `POST /sessions/{session_id}/restore` - Restore archived session
- ❌ `POST /sessions/cleanup` - Cleanup expired sessions
- ❌ `POST /sessions/{session_id}/cleanup` - Cleanup session data
- ❌ `GET /sessions/{session_id}/recovery-info` - Session recovery info

**Priority**: HIGH (critical for session management features)

---

### 4. Case Service ❌ (10/32 - 31.3%)

| Microservices Endpoint | Monolith | Status |
|----------------------|----------|--------|
| **Core CRUD** |||
| `POST /cases` | ✅ `POST /cases` | Implemented |
| `GET /cases/{case_id}` | ✅ `GET /cases/{case_id}` | Implemented |
| `PUT /cases/{case_id}` | ✅ `PATCH /cases/{case_id}` | Implemented (method diff) |
| `DELETE /cases/{case_id}` | ✅ `DELETE /cases/{case_id}` | Implemented |
| `GET /cases` | ✅ `GET /cases` | Implemented |
| `GET /cases/session/{session_id}` | ❌ | **MISSING** |
| **Status** |||
| `POST /cases/{case_id}/status` | ❌ | **MISSING** |
| **Evidence & Data** |||
| `GET /cases/{case_id}/data` | ❌ | **MISSING** |
| `GET /cases/{case_id}/data/{data_id}` | ❌ | **MISSING** |
| `DELETE /cases/{case_id}/data/{data_id}` | ❌ | **MISSING** |
| `POST /cases/{case_id}/data` | ❌ | **MISSING** |
| `GET /cases/{case_id}/evidence/{evidence_id}` | ❌ | **MISSING** |
| `GET /cases/{case_id}/uploaded-files` | ❌ | **MISSING** |
| `GET /cases/{case_id}/uploaded-files/{file_id}` | ❌ | **MISSING** |
| **Hypotheses** |||
| `POST /cases/{case_id}/hypotheses` | ✅ `POST /cases/{case_id}/hypotheses` | Implemented |
| `PUT /cases/{case_id}/hypotheses/{hypothesis_id}` | ❌ | **MISSING** |
| **Solutions** |||
| `POST /cases/{case_id}/solutions` | ✅ `POST /cases/{case_id}/solutions` | Implemented |
| **Messages & Queries** |||
| `POST /cases/{case_id}/queries` | ❌ | **MISSING** |
| `GET /cases/{case_id}/queries` | ❌ | **MISSING** |
| `GET /cases/{case_id}/messages` | ✅ `GET /cases/{case_id}/messages` | Implemented |
| `POST /cases/{case_id}/messages` | ✅ `POST /cases/{case_id}/messages` | Implemented (via add_message) |
| **Reports & Analytics** |||
| `GET /cases/{case_id}/analytics` | ❌ | **MISSING** |
| `GET /cases/{case_id}/report-recommendations` | ❌ | **MISSING** |
| `POST /cases/{case_id}/reports` | ❌ | **MISSING** |
| `GET /cases/{case_id}/reports` | ❌ | **MISSING** |
| `GET /cases/{case_id}/reports/{report_id}/download` | ❌ | **MISSING** |
| `GET /cases/analytics/summary` | ❌ | **MISSING** |
| `GET /cases/analytics/trends` | ❌ | **MISSING** |
| **Utility** |||
| `GET /cases/{case_id}/ui` | ❌ | **MISSING** |
| `POST /cases/{case_id}/title` | ❌ | **MISSING** |
| `POST /cases/{case_id}/close` | ❌ | **MISSING** |
| `POST /cases/search` | ❌ | **MISSING** |
| `GET /cases/health` | ✅ `GET /cases/health` | Implemented |
| `GET /cases/schema.json` | ❌ | **MISSING** |

**Missing Endpoints** (22):
- ❌ `GET /cases/session/{session_id}` - Get cases by session
- ❌ `POST /cases/{case_id}/status` - Update case status
- ❌ `GET /cases/{case_id}/data` - List case data
- ❌ `GET /cases/{case_id}/data/{data_id}` - Get case data
- ❌ `DELETE /cases/{case_id}/data/{data_id}` - Delete case data
- ❌ `POST /cases/{case_id}/data` - Add case data
- ❌ `GET /cases/{case_id}/evidence/{evidence_id}` - Get specific evidence
- ❌ `GET /cases/{case_id}/uploaded-files` - List uploaded files
- ❌ `GET /cases/{case_id}/uploaded-files/{file_id}` - Get file details
- ❌ `PUT /cases/{case_id}/hypotheses/{hypothesis_id}` - Update hypothesis
- ❌ `POST /cases/{case_id}/queries` - Submit query
- ❌ `GET /cases/{case_id}/queries` - Get query history
- ❌ `GET /cases/{case_id}/analytics` - Case analytics
- ❌ `GET /cases/{case_id}/report-recommendations` - Report recommendations
- ❌ `POST /cases/{case_id}/reports` - Generate reports
- ❌ `GET /cases/{case_id}/reports` - List reports
- ❌ `GET /cases/{case_id}/reports/{report_id}/download` - Download report
- ❌ `GET /cases/analytics/summary` - Analytics summary
- ❌ `GET /cases/analytics/trends` - Case trends
- ❌ `GET /cases/{case_id}/ui` - UI-optimized data
- ❌ `POST /cases/{case_id}/title` - Generate case title
- ❌ `POST /cases/{case_id}/close` - Close case
- ❌ `POST /cases/search` - Search cases
- ❌ `GET /cases/schema.json` - Schema metadata

**Priority**: CRITICAL (major functionality gaps)

---

### 5. Evidence Service ⚠️ (6/8 - 75%)

| Microservices Endpoint | Monolith | Status |
|----------------------|----------|--------|
| `POST /evidence` | ✅ `POST /evidence/upload` | Implemented (path diff) |
| `GET /evidence/{evidence_id}` | ✅ `GET /evidence/{evidence_id}` | Implemented |
| `GET /evidence/{evidence_id}/download` | ✅ `GET /evidence/{evidence_id}/download` | Implemented |
| `DELETE /evidence/{evidence_id}` | ✅ `DELETE /evidence/{evidence_id}` | Implemented |
| `GET /evidence` | ❌ | **MISSING** |
| `GET /evidence/case/{case_id}` | ✅ `GET /evidence/case/{case_id}` | Implemented |
| `POST /evidence/{evidence_id}/link` | ❌ | **MISSING** |
| `GET /evidence/health` | ✅ `GET /evidence/health` | Implemented |

**Missing Endpoints** (2):
- ❌ `GET /evidence` - List evidence with query params
- ❌ `POST /evidence/{evidence_id}/link` - Link evidence to case

**Priority**: Medium

---

### 6. Knowledge Service ❌ (6/15 - 40%)

| Microservices Endpoint | Monolith | Status |
|----------------------|----------|--------|
| **Document Management** |||
| `POST /knowledge/documents` | ✅ `POST /knowledge/ingest` | Implemented (path diff) |
| `GET /knowledge/documents/{document_id}` | ✅ `GET /knowledge/documents/{document_id}` | Implemented |
| `PUT /knowledge/documents/{document_id}` | ❌ | **MISSING** |
| `DELETE /knowledge/documents/{document_id}` | ✅ `DELETE /knowledge/documents/{document_id}` | Implemented |
| `GET /knowledge/documents` | ✅ `GET /knowledge/documents` | Implemented |
| `GET /knowledge/documents/stats` | ✅ `GET /knowledge/stats` | Implemented (path diff) |
| `POST /knowledge/documents/bulk-update` | ❌ | **MISSING** |
| `POST /knowledge/documents/search` | ✅ `POST /knowledge/search` | Implemented (path diff) |
| `POST /knowledge/documents/batch-delete` | ❌ | **MISSING** |
| `GET /knowledge/documents/collections` | ❌ | **MISSING** |
| `POST /knowledge/documents/collections` | ❌ | **MISSING** |
| **Semantic Search** |||
| `POST /search` | ❌ | **MISSING** |
| `GET /search/similar/{document_id}` | ❌ | **MISSING** |
| **Health** |||
| `GET /health` | ✅ Exists as `/knowledge/health` (path diff) | Implemented |
| `GET /` | ❌ | **MISSING** |

**Missing Endpoints** (9):
- ❌ `PUT /knowledge/documents/{document_id}` - Update document
- ❌ `POST /knowledge/documents/bulk-update` - Bulk update
- ❌ `POST /knowledge/documents/batch-delete` - Batch delete
- ❌ `GET /knowledge/documents/collections` - List collections
- ❌ `POST /knowledge/documents/collections` - Create collection
- ❌ `POST /search` - Semantic search (different path)
- ❌ `GET /search/similar/{document_id}` - Find similar documents
- ❌ `GET /` - Service info endpoint

**Priority**: HIGH (RAG functionality gaps)

---

### 7. API Gateway ❌ (2/8 - 25%)

| Microservices Endpoint | Monolith | Status |
|----------------------|----------|--------|
| `GET /health` | ✅ `GET /health` | Implemented |
| `GET /health/live` | ❌ | **MISSING** |
| `GET /health/ready` | ❌ | **MISSING** |
| `GET /openapi.json` | ✅ Auto-generated | Implemented |
| `GET /docs` | ✅ Auto-generated | Implemented |
| `GET /redoc` | ❌ | **MISSING** |
| `POST /admin/refresh-openapi` | ❌ | **MISSING** |
| `GET /admin/openapi-health` | ❌ | **MISSING** |

**Missing Endpoints** (6):
- ❌ `GET /health/live` - Kubernetes liveness probe
- ❌ `GET /health/ready` - Kubernetes readiness probe
- ❌ `GET /redoc` - ReDoc UI
- ❌ `POST /admin/refresh-openapi` - Refresh OpenAPI cache
- ❌ `GET /admin/openapi-health` - OpenAPI aggregation health

**Priority**: Medium (infrastructure endpoints)

---

## Priority Categorization

### 🔴 CRITICAL (Must Have for MVP)

**Case Service** (22 missing endpoints):
- Case data/evidence retrieval endpoints
- Analytics and reporting endpoints
- Search functionality
- Case closure and status management

**Session Service** (9 missing endpoints):
- Session message management
- Heartbeat/activity tracking
- Session search and recovery

### 🟡 HIGH (Important for Full Features)

**Knowledge Service** (9 missing endpoints):
- Document updates and batch operations
- Semantic search endpoints
- Collections management

### 🟢 MEDIUM (Nice to Have)

**Auth Service** (2 missing endpoints):
- JWKS and OpenID Connect endpoints

**Evidence Service** (2 missing endpoints):
- Evidence listing and linking

**Gateway** (6 missing endpoints):
- Advanced health checks
- Admin endpoints

---

## Recommendations

### Immediate Actions Required

1. **Re-assess Phase 3.1 Status**: Phase 3.1 is **NOT complete**. Only 44.3% of endpoints are implemented.

2. **Prioritize Critical Gaps**:
   - Implement all 22 missing Case Service endpoints
   - Implement all 9 missing Session Service endpoints
   - These are core to the application functionality

3. **Create Implementation Plan**:
   - Estimated effort: 3-5 days for critical endpoints
   - Estimated effort: 2-3 days for high priority
   - Estimated effort: 1-2 days for medium priority
   - **Total**: 6-10 days to reach full API parity

4. **Update Frontend Integration Plan**:
   - Frontends expecting these endpoints will fail
   - Need to identify which endpoints frontends actually use
   - May need to implement stubs for unused endpoints

### Next Steps

1. **Audit Frontend Dependencies**:
   - Check which of the 49 missing endpoints are actually used by faultmaven-copilot and faultmaven-dashboard
   - Prioritize implementation based on frontend needs

2. **Implement Critical Endpoints First**:
   - Focus on Case and Session endpoints needed for basic functionality
   - Can defer analytics/reporting endpoints if not immediately needed

3. **Document Stubs**:
   - For endpoints not yet implemented, add stub responses with 501 Not Implemented
   - Document which endpoints are stubs vs fully functional

---

## Conclusion

The monolith has **significant API gaps** with only **39/88 endpoints** (44.3% coverage) implemented. The largest gaps are in:

- **Case Service**: Missing 22/32 endpoints (68.75% gap)
- **Session Service**: Missing 9/16 endpoints (56.25% gap)
- **Knowledge Service**: Missing 9/15 endpoints (60% gap)

**Phase 3.1 cannot be considered complete** until these gaps are addressed or explicitly scoped out based on frontend requirements.

**Recommended Action**: Pause and reassess with the project stakeholders whether all 88 endpoints are required, or if we can scope down to the endpoints actually used by the frontends.
