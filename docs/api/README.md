# FaultMaven API Documentation

This directory contains auto-generated OpenAPI specifications for the FaultMaven API.

---

## Files

- **`openapi.locked.yaml`** - Versioned API specification (committed to git)
- **`openapi.current.yaml`** - Current working specification (generated, not committed to git)

---

## Generating API Specs

```bash
python scripts/generate_openapi_spec.py
```

This script:
1. Generates current OpenAPI spec from the FastAPI application
2. Compares with the locked spec to detect API changes
3. Reports breaking vs non-breaking changes
4. Helps maintain API compatibility

---

## Breaking Change Detection

The script automatically detects:

- 🔴 **Breaking Changes**:
  - Removed endpoints
  - Removed HTTP methods
  - Removed response codes
  - Removed fields from schemas
  - New required parameters
  - New required fields in schemas

- 🟢 **Non-Breaking Changes**:
  - New endpoints
  - New HTTP methods
  - New optional parameters
  - New optional fields
  - Deprecated features

---

## Workflow

### After Making API Changes

```bash
# 1. Generate current spec
python scripts/generate_openapi_spec.py

# 2. Review changes reported by the script
# - If breaking changes: Plan migration strategy
# - If non-breaking: Proceed with update

# 3. Update locked spec (after review)
cp docs/api/openapi.current.yaml docs/api/openapi.locked.yaml

# 4. Commit the updated locked spec
git add docs/api/openapi.locked.yaml
git commit -m "api: Update OpenAPI spec to v<version>"
```

### Before Merging PRs

```bash
# Always run the spec generator to detect API changes
python scripts/generate_openapi_spec.py

# If breaking changes detected:
# - Document the migration path
# - Update API version if needed
# - Notify users of breaking changes
```

---

## Interactive API Documentation

When running FaultMaven locally, you can access interactive API documentation:

- **Swagger UI**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>

These provide:
- Interactive API explorer
- Request/response examples
- Schema definitions
- Authentication testing

---

## API Versioning

FaultMaven uses URL-based versioning for breaking changes:

- **v1**: `/api/v1/*` - Current stable version
- **v2**: `/api/v2/*` - Future version (when breaking changes accumulate)

**Current version**: v1

---

## CI/CD Integration

The API spec generation should be integrated into CI/CD:

```yaml
# .github/workflows/api-validation.yml
- name: Validate API changes
  run: |
    python scripts/generate_openapi_spec.py
    # Exit with error if breaking changes detected on main branch
```

---

## Related Documentation

- [ARCHITECTURE.md](../ARCHITECTURE.md) - API architecture and design
- [DEVELOPMENT.md](../DEVELOPMENT.md) - Development workflow
- [API.md](../API.md) - Manual API documentation (deprecated - use auto-generated specs)

---

**Auto-Generated**: Yes
**Last Manual Update**: 2025-12-26
**Specification Format**: OpenAPI 3.1.0
