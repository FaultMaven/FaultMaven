# Manual Test Scripts

**Legacy shell scripts for manual API testing.**

These scripts were used during early development for manual endpoint testing. They are kept for reference but are largely superseded by pytest.

---

## Scripts

### API Testing

- **test_api.sh** - Basic API health check
- **test_auth.sh** - Authentication flow testing
- **test_sessions.sh** - Session management testing
- **test_cases.sh** - Case operations testing
- **test_evidence.sh** - Evidence upload/download testing

---

## Usage

```bash
# Make executable
chmod +x test_api.sh

# Run test
./test_api.sh
```

**Note**: These require a running FaultMaven instance on localhost:8000

---

## Recommendation

**Use pytest instead** for automated testing:

```bash
# Run all tests
pytest

# Run specific module tests
pytest tests/unit/modules/auth/
pytest tests/integration/
```

See [../../docs/TESTING_STRATEGY.md](../../docs/TESTING_STRATEGY.md) for testing approach.

---

## Deprecation Status

These scripts may be removed in a future release once full pytest coverage is verified.

**Current pytest coverage**: 47% (target: 80%)
