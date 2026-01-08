# Bug Fixes - January 2026

## Marketplace Scan Fails with CHECK Constraint Error for MCP Artifacts

**Date Fixed**: 2026-01-08
**Severity**: high
**Component**: marketplace-scanner

**Issue**: When adding a new marketplace source with a large number (1000+) of detected artifacts, the scan fails with `CHECK constraint failed: check_catalog_artifact_type` during bulk insert of catalog entries.

**Root Cause**: The `ArtifactType.MCP` enum has value `"mcp"`, but the database CHECK constraint in `marketplace_catalog_entries` table only accepted `"mcp_server"`. This was a naming mismatch between the Python enum definition and the legacy database schema.

The heuristic detector correctly identifies MCP artifacts using `ArtifactType.MCP` (value: `"mcp"`), but when these are inserted into the database, the constraint `artifact_type IN ('skill', 'command', 'agent', 'mcp_server', 'hook', ...)` rejects the value.

**Fix**: Added `'mcp'` to all artifact_type CHECK constraints while keeping `'mcp_server'` for backward compatibility with existing data.

**Files Modified**:
- `skillmeat/cache/models.py` - Updated 3 CHECK constraints:
  - `check_artifact_type` (Artifact model)
  - `check_marketplace_type` (MarketplaceEntry model)
  - `check_catalog_artifact_type` (MarketplaceCatalogEntry model)
- `skillmeat/cache/schema.py` - Updated 3 CHECK constraints in raw schema
- `skillmeat/cache/migrations/versions/20260108_1700_add_mcp_to_type_constraints.py` - New migration to update existing databases

**Testing**:
- All marketplace cache tests pass
- Migration applies cleanly using batch_alter_table for SQLite compatibility
- Verified constraint now accepts both `'mcp'` and `'mcp_server'` values

**Status**: RESOLVED

---

## List Artifacts Endpoint Fails with 500 Error Due to Variable Shadowing

**Date Fixed**: 2026-01-08
**Severity**: high
**Component**: marketplace-sources-api

**Issue**: When viewing low-confidence artifacts in the marketplace, the API returns a 500 error: `AttributeError: 'NoneType' object has no attribute 'HTTP_500_INTERNAL_SERVER_ERROR'`.

**Root Cause**: The `list_artifacts` endpoint had a query parameter named `status` which shadowed the imported `fastapi.status` module. When the query parameter was `None` (no filter provided), the exception handler tried to access `None.HTTP_500_INTERNAL_SERVER_ERROR` instead of `fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR`.

```python
# Line 1302 - query parameter shadows the module
status: Optional[str] = Query(None, ...)

# Line 1471 - exception handler references the shadowed name
raise HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,  # status is None!
    ...
)
```

**Fix**: Renamed the query parameter from `status` to `status_filter` with `alias="status"` to maintain API compatibility.

**Files Modified**:
- `skillmeat/api/routers/marketplace_sources.py`:
  - Renamed parameter `status` → `status_filter` (line 1302)
  - Added `alias="status"` for backwards compatibility
  - Updated all internal references to use `status_filter`

**Testing**: Verified function signature and status module accessibility

**Status**: RESOLVED

---

## CatalogEntryResponse Validation Error for MCP Artifact Type

**Date Fixed**: 2026-01-08
**Severity**: high
**Component**: marketplace-schemas

**Issue**: When viewing low-confidence detected artifacts from a marketplace source, the API fails with Pydantic validation error: `Input should be 'skill', 'command', 'agent', 'mcp_server' or 'hook'`.

**Root Cause**: Continuation of the MCP artifact type naming mismatch. While the database CHECK constraints were updated to accept `'mcp'`, the Pydantic response schema `CatalogEntryResponse` still used a Literal type that only accepted the old values.

```python
# Before fix - rejected 'mcp' values from database
artifact_type: Literal["skill", "command", "agent", "mcp_server", "hook"]
```

**Fix**: Added `'mcp'` to the Literal type annotations in Pydantic schemas.

**Files Modified**:
- `skillmeat/api/schemas/marketplace.py`:
  - Line 1038: `CatalogEntryResponse.artifact_type` - Added 'mcp' to Literal type
  - Line 2132: `ManualMapEntry.artifact_type` - Added 'mcp' to Literal type

**Testing**: Response schema now accepts both 'mcp' and 'mcp_server' values

**Status**: RESOLVED
