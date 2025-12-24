# **Phase 4: Edge Cases & Error Handling - Implementation Plan**

**Status:** ⏸️ **PARTIALLY COMPLETE - PAUSED FOR FEATURE DEVELOPMENT** (2025-12-24)

**Completed:** 19 error handling tests (18 passing, 1 xfailed) - See [TESTING_IMPLEMENTATION_ROADMAP.md](TESTING_IMPLEMENTATION_ROADMAP.md#phase-4-edge-cases--error-handling-week-4-)

**Remaining Work:** Security tests, external service failures, concurrent operations (resume after MVP features stabilize)

**Goal:** Test error scenarios, edge cases, and security vulnerabilities to ensure robust system behavior.

---

## **Prerequisites - COMPLETE** ✅

- ✅ Phase 1: Testing foundation established
- ✅ Phase 2: Service layer tests complete
- ✅ Phase 3: All API contract tests complete (144 tests)
- ✅ Test infrastructure: Database fixtures, factories, client fixtures
- ✅ Current coverage: ~42% overall

---

## **Phase 4 Objectives**

### **Primary Goals:**

1. **Error Handling Coverage** - Test all failure scenarios
2. **Security Testing** - Validate security controls
3. **Boundary Conditions** - Test edge cases and limits
4. **Concurrent Operations** - Test race conditions and data integrity
5. **Achieve 75%+ overall coverage**

### **Non-Goals:**

- Performance/load testing (separate phase)
- UI/E2E browser testing (separate phase)
- Integration with external services (mocked)

---

---

## ✅ **COMPLETED SECTIONS** (2025-12-24)

### **4.1 Error Handling Tests - Basic Coverage**

**File:** `tests/api/test_error_handling.py` ✅ **IMPLEMENTED**

**Completed Tests:**
- ✅ Database errors (duplicate email, foreign key violations) - 2 tests
- ✅ Invalid input handling (missing fields, invalid enums, wrong types) - 4 tests
- ✅ Resource not found (404 responses) - 3 tests
- ✅ Boundary conditions (empty lists, long strings, pagination) - 4 tests
- ✅ File upload errors (size limits, type validation) - 2 tests
- ✅ Authentication/authorization (no token, invalid token, cross-user) - 3 tests
- 🔍 Concurrent operations (1 xfailed - transaction handling limitation)

**Total:** 18 passing / 1 xfailed

---

## ⏸️ **REMAINING WORK** (Resume After Feature Development)

### **4.1 Error Handling Tests - Advanced Coverage**

### **Database Errors** ⏸️ **FUTURE**

**File:** `tests/error_handling/test_database_errors.py` (NOT YET CREATED)

**Test Scenarios:**

```python
@pytest.mark.error_handling
class TestDatabaseErrors:
    """Test database constraint violations and error handling."""

    async def test_duplicate_user_email(self, db_session):
        """Test creating user with duplicate email fails gracefully."""
        # Create first user
        user1 = await UserFactory.create_async(
            _session=db_session,
            email="duplicate@example.com"
        )
        await db_session.commit()

        # Try to create second user with same email
        with pytest.raises(IntegrityError):
            user2 = await UserFactory.create_async(
                _session=db_session,
                email="duplicate@example.com"
            )
            await db_session.commit()

    async def test_foreign_key_constraint(self, db_session):
        """Test foreign key constraint violations."""
        from faultmaven.modules.case.service import CaseService

        service = CaseService(session=db_session)

        with pytest.raises(ValueError, match="User not found"):
            await service.create_case(
                owner_id="00000000-0000-0000-0000-000000000000",
                title="Test Case",
                description="Test"
            )

    async def test_null_constraint(self, db_session):
        """Test NOT NULL constraint violations."""
        # Should fail when required field is missing
        pass

    async def test_check_constraint(self, db_session):
        """Test CHECK constraint violations."""
        # Test enum values, range checks, etc.
        pass
```

**Coverage Target:** All database constraints tested

---

### **External Service Failures**

**File:** `tests/error_handling/test_external_failures.py`

**Test Scenarios:**

```python
@pytest.mark.error_handling
class TestExternalServiceFailures:
    """Test handling of external service failures."""

    async def test_llm_timeout(self, authenticated_client, db_session):
        """Test LLM provider timeout handling."""
        # Mock LLM to timeout
        # Verify graceful error response
        # Verify error logged
        pass

    async def test_vector_db_unavailable(self, authenticated_client):
        """Test ChromaDB unavailable."""
        # Mock ChromaDB to be unreachable
        # Verify search returns empty results
        # Verify error logged
        pass

    async def test_redis_connection_failure(self, authenticated_client):
        """Test Redis connection failure."""
        # Mock Redis to fail
        # Verify session operations degrade gracefully
        pass

    async def test_postgres_connection_loss(self, db_session):
        """Test database connection loss mid-transaction."""
        # Simulate connection drop
        # Verify retry logic
        pass
```

**Coverage Target:** All external dependencies mocked to fail

---

### **Invalid Input Handling**

**File:** `tests/error_handling/test_invalid_inputs.py`

**Test Scenarios:**

```python
@pytest.mark.error_handling
class TestInvalidInputs:
    """Test validation and error handling for invalid inputs."""

    async def test_malformed_json(self, authenticated_client):
        """Test malformed JSON returns 422."""
        client, user = authenticated_client

        response = await client.post(
            "/cases",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    async def test_missing_required_fields(self, authenticated_client):
        """Test missing required fields returns 422."""
        client, user = authenticated_client

        response = await client.post("/cases", json={})
        assert response.status_code == 422
        assert "title" in response.json()["detail"]

    async def test_invalid_uuid_format(self, authenticated_client):
        """Test invalid UUID format returns 400."""
        client, user = authenticated_client

        response = await client.get("/cases/not-a-uuid")
        assert response.status_code in [400, 404, 422]

    async def test_sql_injection_attempt(self, authenticated_client):
        """Test SQL injection attempts are sanitized."""
        client, user = authenticated_client

        response = await client.post(
            "/cases",
            json={
                "title": "'; DROP TABLE users; --",
                "description": "SQL injection test"
            }
        )

        # Should create case normally (input sanitized)
        assert response.status_code == 201

        # Verify no SQL injection occurred
        # (users table still exists)

    async def test_xss_attempt(self, authenticated_client):
        """Test XSS attempts are sanitized."""
        client, user = authenticated_client

        response = await client.post(
            "/cases",
            json={
                "title": "<script>alert('XSS')</script>",
                "description": "XSS test"
            }
        )

        assert response.status_code == 201
        data = response.json()
        # Verify script tags are escaped or removed
        assert "<script>" not in data["title"]
```

**Coverage Target:** All input validation paths tested

---

## **4.2 Security Tests**

**File:** `tests/security/test_authentication.py`

**Test Scenarios:**

```python
@pytest.mark.security
class TestAuthenticationSecurity:
    """Test authentication security controls."""

    async def test_expired_token_rejected(self, unauthenticated_client):
        """Test expired JWT tokens are rejected."""
        # Create expired token
        # Attempt to use it
        # Verify 401 response
        pass

    async def test_invalid_signature_rejected(self, unauthenticated_client):
        """Test tokens with invalid signatures rejected."""
        # Create token with wrong secret
        # Verify 401 response
        pass

    async def test_missing_token_rejected(self, unauthenticated_client):
        """Test requests without tokens rejected."""
        response = await unauthenticated_client.get("/cases")
        assert response.status_code == 401

    async def test_token_blacklist(self, authenticated_client, mock_cache):
        """Test blacklisted tokens are rejected."""
        # Logout (blacklist token)
        # Try to use blacklisted token
        # Verify 401 response
        pass

    async def test_rate_limiting(self, unauthenticated_client):
        """Test rate limiting on login endpoint."""
        # Make multiple failed login attempts
        # Verify rate limit kicks in
        pass
```

**File:** `tests/security/test_authorization.py`

**Test Scenarios:**

```python
@pytest.mark.security
class TestAuthorizationSecurity:
    """Test authorization security controls."""

    async def test_user_cannot_access_others_cases(
        self,
        authenticated_client,
        second_user_client,
        db_session
    ):
        """Test users cannot access each other's cases."""
        client1, user1 = authenticated_client
        client2, user2 = second_user_client

        # User 1 creates case
        response = await client1.post(
            "/cases",
            json={"title": "Private", "description": "Test"}
        )
        case_id = response.json()["id"]

        # User 2 tries to access it
        response = await client2.get(f"/cases/{case_id}")
        assert response.status_code == 404  # Should not exist for user2

    async def test_user_cannot_modify_others_cases(
        self,
        authenticated_client,
        second_user_client,
        db_session
    ):
        """Test users cannot modify each other's cases."""
        # Similar to above, but test PUT/PATCH/DELETE
        pass

    async def test_privilege_escalation_blocked(self, authenticated_client):
        """Test users cannot escalate privileges."""
        # Try to modify user role
        # Verify blocked
        pass
```

**Coverage Target:** All authorization paths tested

---

## **4.3 Boundary Conditions**

**File:** `tests/boundary/test_limits.py`

**Test Scenarios:**

```python
@pytest.mark.boundary
class TestBoundaryConditions:
    """Test system behavior at boundaries and limits."""

    async def test_empty_string_inputs(self, authenticated_client):
        """Test empty strings handled correctly."""
        client, user = authenticated_client

        response = await client.post(
            "/cases",
            json={"title": "", "description": ""}
        )
        # Should fail validation
        assert response.status_code == 422

    async def test_very_long_inputs(self, authenticated_client):
        """Test very long strings handled correctly."""
        client, user = authenticated_client

        # 10,000 character title
        response = await client.post(
            "/cases",
            json={
                "title": "A" * 10000,
                "description": "Test"
            }
        )
        # Should either accept (if within limit) or reject gracefully
        assert response.status_code in [201, 422]

    async def test_large_file_upload(self, authenticated_client):
        """Test large file upload handling."""
        # Test file size limits
        # Verify 413 or graceful handling
        pass

    async def test_null_values(self, authenticated_client):
        """Test null value handling."""
        # Test optional fields with null
        # Verify correct behavior
        pass

    async def test_unicode_inputs(self, authenticated_client):
        """Test Unicode/emoji inputs."""
        client, user = authenticated_client

        response = await client.post(
            "/cases",
            json={
                "title": "Test Case 🚀 with émojis and ユニコード",
                "description": "Unicode test"
            }
        )
        assert response.status_code == 201
```

**Coverage Target:** All input boundaries tested

---

## **4.4 Concurrent Operations**

**File:** `tests/concurrency/test_race_conditions.py`

**Test Scenarios:**

```python
@pytest.mark.concurrency
class TestConcurrentOperations:
    """Test concurrent operation handling."""

    async def test_concurrent_case_updates(self, authenticated_client, db_session):
        """Test concurrent updates to same case."""
        # Create case
        # Update from two different requests simultaneously
        # Verify no data corruption
        pass

    async def test_concurrent_session_access(self, authenticated_client):
        """Test concurrent session operations."""
        # Access same session from multiple requests
        # Verify session state consistency
        pass

    async def test_optimistic_locking(self, db_session):
        """Test optimistic locking prevents lost updates."""
        # If using version fields
        # Test concurrent updates with version check
        pass
```

**Coverage Target:** Critical race conditions tested

---

## **Success Criteria**

### **Coverage Metrics:**

- ✅ Overall coverage: **75%+** (from current ~42%)
- ✅ Service layer coverage: **90%+**
- ✅ Router coverage: **80%+**
- ✅ Error paths covered

### **Test Quality:**

- ✅ All error scenarios have dedicated tests
- ✅ All security controls verified
- ✅ All boundary conditions tested
- ✅ No flaky tests
- ✅ All tests pass reliably

### **Documentation:**

- ✅ Phase 4 completion document created
- ✅ Security test results documented
- ✅ Known limitations documented

---

## **Implementation Strategy**

### **Week 1: Error Handling**

- Day 1-2: Database error tests
- Day 3-4: External service failure tests
- Day 5: Invalid input tests

### **Week 2: Security & Boundaries**

- Day 1-2: Authentication security tests
- Day 3: Authorization security tests
- Day 4-5: Boundary condition tests

### **Week 3: Concurrency & Polish**

- Day 1-2: Concurrent operation tests
- Day 3-4: Coverage gap analysis and filling
- Day 5: Documentation and review

---

## **Risk Assessment**

### **Low Risk:**

- Database error tests (straightforward)
- Input validation tests (straightforward)
- Boundary condition tests (straightforward)

### **Medium Risk:**

- External service failure tests (mocking complexity)
- Concurrent operation tests (timing sensitive)

### **High Risk:**

- Security tests (false positives/negatives)
- Coverage target (may need refactoring)

---

## **Dependencies**

### **Required:**

- ✅ pytest-asyncio (installed)
- ✅ pytest-mock (installed)
- ✅ httpx (installed)
- ⚠️ pytest-timeout (for timeout tests) - **NEED TO INSTALL**
- ⚠️ pytest-xdist (for concurrent tests) - **NEED TO INSTALL**

### **Installation:**

```bash
pip install pytest-timeout pytest-xdist
```

---

## **Notes**

- **Performance testing** is OUT OF SCOPE for Phase 4 (separate phase)
- **Load testing** is OUT OF SCOPE for Phase 4 (separate phase)
- **UI testing** is OUT OF SCOPE for Phase 4 (separate phase)
- Focus on **correctness** and **security**, not performance

---

**Created:** 2025-12-22
**Ready to Start:** Yes ✅
**Estimated Effort:** 2-3 weeks
**Previous Phase:** Phase 3 (Complete - 144 tests)
**Next Phase:** Phase 5 (Performance & Load Testing)
