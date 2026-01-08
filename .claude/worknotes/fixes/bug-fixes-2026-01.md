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
