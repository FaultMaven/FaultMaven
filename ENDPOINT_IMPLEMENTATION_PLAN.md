# Endpoint Implementation Plan - 49 Missing Endpoints

**Status**: Ready for implementation
**Estimated Time**: 6-10 days
**Priority**: CRITICAL for frontend compatibility

---

## Implementation Strategy

### Phase A: Critical Frontend Dependencies (Day 1-3)
Endpoints that frontends actively use and will break without them.

### Phase B: High Priority Features (Day 4-6)
Important functionality that enhances the application.

### Phase C: Nice-to-Have (Day 7-8)
Additional endpoints for completeness.

---

## PHASE A: Critical Frontend Dependencies (Priority 1)

### A1. Auth Module - JWKS Endpoints (30 min)

**File**: `src/faultmaven/modules/auth/router.py`

**Missing Endpoints**:
1. `GET /.well-known/jwks.json` - JWKS for JWT validation
2. `GET /.well-known/openid-configuration` - OpenID Connect discovery

**Frontend Impact**: Copilot uses these for OIDC authentication

**Implementation**:
```python
@router.get("/.well-known/jwks.json")
async def get_jwks(auth_service: AuthService = Depends(get_auth_service)):
    """Get JSON Web Key Set for JWT validation."""
    return auth_service.get_jwks()

@router.get("/.well-known/openid-configuration")
async def get_openid_configuration():
    """Get OpenID Connect discovery document."""
    return {
        "issuer": settings.ISSUER_URL,
        "authorization_endpoint": f"{settings.ISSUER_URL}/auth/authorize",
        "token_endpoint": f"{settings.ISSUER_URL}/auth/token",
        "jwks_uri": f"{settings.ISSUER_URL}/.well-known/jwks.json",
        # ... rest of config
    }
```

---

### A2. Case Module - Archive Endpoint (15 min)

**File**: `src/faultmaven/modules/case/router.py`

**Missing**: `POST /cases/{case_id}/archive`

**Frontend Impact**: Copilot uses this to archive cases

**Implementation**:
```python
@router.post("/{case_id}/archive")
async def archive_case(
    case_id: str,
    user_id: str = Depends(require_auth),
    case_service: CaseService = Depends(get_case_service),
):
    """Archive a case."""
    case = await case_service.update_case(
        case_id=case_id,
        user_id=user_id,
        status="archived"
    )
    return {"case_id": case_id, "status": "archived"}
```

---

### A3. Session Module - Core Missing Endpoints (2 hours)

**File**: `src/faultmaven/modules/session/router.py`

**Critical Missing Endpoints** (used by frontend):
1. `POST /sessions/{session_id}/heartbeat` - Session activity tracking
2. `POST /sessions/{session_id}/messages` - Add message to session
3. `GET /sessions/{session_id}/messages` - Get session messages

**Implementation Priority**: HIGH (copilot actively uses these)

---

### A4. Case Module - Status & Data Endpoints (1 hour)

**File**: `src/faultmaven/modules/case/router.py`

**Critical Missing**:
1. `POST /cases/{case_id}/status` - Update case status
2. `GET /cases/{case_id}/data` - List case data
3. `POST /cases/{case_id}/data` - Add case data (already exists, verify)

**Frontend Impact**: Used for case management workflows

---

## PHASE B: High Priority Features (Priority 2)

### B1. Session Module - Extended Features (3 hours)

**File**: `src/faultmaven/modules/session/router.py`

**Missing Endpoints**:
1. `GET /sessions/{session_id}/cases` - Get cases for session
2. `GET /sessions/{session_id}/stats` - Session statistics
3. `POST /sessions/search` - Search sessions
4. `POST /sessions/{session_id}/archive` - Archive session
5. `POST /sessions/{session_id}/restore` - Restore archived session
6. `GET /sessions/{session_id}/recovery-info` - Session recovery info

---

### B2. Case Module - Analytics & Reports (4 hours)

**File**: `src/faultmaven/modules/case/router.py`

**Missing Endpoints**:
1. `GET /cases/{case_id}/analytics` - Case analytics
2. `GET /cases/{case_id}/report-recommendations` - Report recommendations
3. `POST /cases/{case_id}/reports` - Generate reports
4. `GET /cases/{case_id}/reports` - List reports
5. `GET /cases/{case_id}/reports/{report_id}/download` - Download report
6. `GET /cases/analytics/summary` - Analytics summary
7. `GET /cases/analytics/trends` - Case trends

**Frontend Impact**: Report generation features (copilot uses)

---

### B3. Case Module - Advanced Features (2 hours)

**File**: `src/faultmaven/modules/case/router.py`

**Missing Endpoints**:
1. `GET /cases/{case_id}/ui` - UI-optimized data
2. `POST /cases/{case_id}/title` - Generate case title
3. `POST /cases/{case_id}/close` - Close case
4. `POST /cases/search` - Search cases
5. `PUT /cases/{case_id}/hypotheses/{hypothesis_id}` - Update hypothesis

**Frontend Impact**: UI optimization and search (copilot uses)

---

### B4. Knowledge Module - Document Updates (2 hours)

**File**: `src/faultmaven/modules/knowledge/router.py`

**Missing Endpoints**:
1. `PUT /knowledge/documents/{document_id}` - Update document
2. `POST /knowledge/documents/bulk-update` - Bulk update
3. `POST /knowledge/documents/batch-delete` - Batch delete

---

### B5. Knowledge Module - Semantic Search (2 hours)

**File**: `src/faultmaven/modules/knowledge/router.py`

**Missing Endpoints**:
1. `POST /search` - Semantic search (different from /knowledge/search)
2. `GET /search/similar/{document_id}` - Find similar documents

**Note**: May need to refactor existing `/knowledge/search` endpoint

---

## PHASE C: Nice-to-Have (Priority 3)

### C1. Case Module - Remaining Data Endpoints (1 hour)

**File**: `src/faultmaven/modules/case/router.py`

**Missing Endpoints**:
1. `GET /cases/{case_id}/data/{data_id}` - Get case data
2. `DELETE /cases/{case_id}/data/{data_id}` - Delete case data
3. `GET /cases/{case_id}/evidence/{evidence_id}` - Get specific evidence
4. `GET /cases/{case_id}/uploaded-files` - List uploaded files
5. `GET /cases/{case_id}/uploaded-files/{file_id}` - Get file details
6. `GET /cases/session/{session_id}` - Get cases by session

---

### C2. Case Module - Queries & Schema (1 hour)

**File**: `src/faultmaven/modules/case/router.py`

**Missing Endpoints**:
1. `POST /cases/{case_id}/queries` - Submit query
2. `GET /cases/{case_id}/queries` - Get query history
3. `GET /cases/schema.json` - Schema metadata

---

### C3. Session Module - Cleanup Endpoints (30 min)

**File**: `src/faultmaven/modules/session/router.py`

**Missing Endpoints**:
1. `POST /sessions/cleanup` - Cleanup expired sessions
2. `POST /sessions/{session_id}/cleanup` - Cleanup session data

---

### C4. Evidence Module - Additional Endpoints (30 min)

**File**: `src/faultmaven/modules/evidence/router.py`

**Missing Endpoints**:
1. `GET /evidence` - List evidence with query params
2. `POST /evidence/{evidence_id}/link` - Link evidence to case

---

### C5. Knowledge Module - Collections & Info (1 hour)

**File**: `src/faultmaven/modules/knowledge/router.py`

**Missing Endpoints**:
1. `GET /knowledge/documents/collections` - List collections
2. `POST /knowledge/documents/collections` - Create collection
3. `GET /` - Service info endpoint

---

### C6. Gateway/App - Advanced Health & Admin (1 hour)

**File**: `src/faultmaven/app.py`

**Missing Endpoints**:
1. `GET /health/live` - Kubernetes liveness probe
2. `GET /health/ready` - Kubernetes readiness probe
3. `GET /redoc` - ReDoc UI
4. `POST /admin/refresh-openapi` - Refresh OpenAPI cache
5. `GET /admin/openapi-health` - OpenAPI aggregation health

---

## Implementation Order (Recommended)

### Day 1: Critical Auth & Case Endpoints
- [ ] A1: JWKS endpoints (30 min)
- [ ] A2: Archive endpoint (15 min)
- [ ] A4: Status & data endpoints (1 hour)
- **Total: ~2 hours**

### Day 2: Critical Session Endpoints
- [ ] A3: Session heartbeat, messages (2 hours)
- [ ] B1: Session extended features (3 hours)
- **Total: ~5 hours**

### Day 3-4: Analytics & Reports
- [ ] B2: Case analytics & reports (4 hours)
- [ ] B3: Case advanced features (2 hours)
- **Total: ~6 hours**

### Day 5-6: Knowledge & Search
- [ ] B4: Knowledge document updates (2 hours)
- [ ] B5: Semantic search (2 hours)
- **Total: ~4 hours**

### Day 7-8: Remaining Endpoints
- [ ] C1-C6: All remaining endpoints (5 hours)
- [ ] Testing all 88 endpoints (3 hours)
- **Total: ~8 hours**

---

## Testing Strategy

After each phase, test:
1. Manual testing with curl
2. Run validation script
3. Check OpenAPI spec updates
4. Verify frontend compatibility

---

## Notes

### Stub vs Full Implementation

For endpoints not immediately needed:
- Implement **functional stubs** that return proper status codes
- Add TODO comments for full implementation
- Return realistic mock data

Example:
```python
@router.get("/{case_id}/analytics")
async def get_case_analytics(case_id: str, user_id: str = Depends(require_auth)):
    """Get case analytics (STUB - returns mock data)."""
    # TODO: Implement real analytics calculation
    return {
        "case_id": case_id,
        "message_count": 0,
        "participant_count": 1,
        "status": "investigating"
    }
```

### Frontend Path Compatibility

Based on frontend-api-consistency-check.md:
- Ensure `/api/v1/documents/*` routes to `/api/v1/knowledge/documents/*`
- Support both `PUT` and `PATCH` for updates
- Handle trailing slashes in session list endpoint

---

## Success Criteria

- [ ] All 88 endpoints return appropriate status codes (not 404)
- [ ] OpenAPI spec shows all 88 endpoints
- [ ] Validation script shows 100% coverage
- [ ] Frontend copilot can make API calls without errors
- [ ] Frontend dashboard can make API calls without errors

---

**Ready to Start Implementation?**

I recommend starting with **Phase A (Critical Frontend Dependencies)** to unblock the frontends immediately, then proceeding to Phase B and C.

Would you like me to:
1. Start implementing Phase A endpoints now?
2. Create a different prioritization?
3. Focus on specific modules first?
