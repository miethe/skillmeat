# Bug Fixes - February 2026

## Sync Status Tab Performance and 404 Errors

**Date Fixed**: 2026-02-11
**Severity**: high
**Component**: artifacts-api, sync-status-tab

**Issue**: Two related issues affecting the Sync Status tab in ArtifactOperationsModal:

1. **Performance**: Initial load extremely slow (up to 30s) for the `/api/v1/artifacts/{id}/diff` endpoint
2. **404 errors**: Some artifacts fail to load sync status, returning 404 despite existing (e.g., `agent:prd-writer`, `agent:supabase-realtime-optimizer.md`)

**Root Causes**:

1. **Performance bottleneck**: The diff endpoints used `rglob("*")` without exclusion filters, traversing ALL directories including `node_modules`, `.git`, `__pycache__`, etc. For artifacts with dependencies (especially Node.js), this caused massive I/O operations.

2. **404 errors (extension)**: Frontend sometimes sent artifact IDs with file extensions (e.g., `agent:supabase-realtime-optimizer.md`) but backend expected no extension. Lookup failures.

3. **404 errors (collection UUID)**: Frontend sends collection UUID (`470c5a19e5054768adf543c6fcfadcef`) as the `collection` query parameter, but backend only accepted collection names (e.g., "default"). The `useEntityLifecycle.tsx:593` line sets `artifact.collection` to the collection UUID, which then gets passed to `ProjectSelectorForDiff` and sent as `?collection=UUID`. Backend's `list_collections()` returns names only → 404.

**Fix**:

1. Added `iter_artifact_files()` helper with `DIFF_EXCLUDE_DIRS` constant to filter non-content directories. Made configurable via `APISettings.diff_exclude_dirs` for power users.

2. Added `parse_artifact_id()` helper that normalizes artifact names by stripping common file extensions (`.md`, `.txt`, `.json`, `.yaml`, `.yml`). Logs warning when extension stripping occurs.

3. Added `resolve_collection_name()` helper that accepts either a collection name or UUID. Fast path checks names via `list_collections()`. If that fails, queries DB `Collection` table by ID to resolve UUID → name. Updated all 16 collection validation sites.

**Files Modified**:
- `skillmeat/api/routers/artifacts.py`:
  - Added `DIFF_EXCLUDE_DIRS` constant and `iter_artifact_files()` helper (11 locations)
  - Added `parse_artifact_id()` helper (22 locations)
  - Added `resolve_collection_name()` helper (16 locations)
  - Updated `iter_artifact_files()` to accept optional `exclude_dirs` from settings
- `skillmeat/api/config.py`:
  - Added `diff_exclude_dirs: List[str]` field to `APISettings`

**Testing**:
- `parse_artifact_id()` correctly strips extensions and logs warnings
- `iter_artifact_files()` correctly excludes cache/build directories
- `resolve_collection_name()` resolves both names and UUIDs
- Config field loads defaults correctly, env var override works
- All imports and syntax validated

**Performance Improvement**:
- Diff operations on artifacts with node_modules: 30s → <5s

**Configuration** (DIFF_EXCLUDE_DIRS):
- Default: `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, `.tox`, `.pytest_cache`, `.mypy_cache`, `dist`, `build`, `.next`, `.turbo`
- Environment variable: `SKILLMEAT_DIFF_EXCLUDE_DIRS='["vendor", ".cache"]'`

**Commits**: 71dc777d, 8e0c3713

**Status**: PARTIALLY RESOLVED (see below for fourth root cause)

---

## Sync Status Tab 404 Errors - Deployment Name Mismatch

**Date Fixed**: 2026-02-11
**Severity**: high
**Component**: deployment-tracker, sync-status-tab

**Issue**: Continued 404 errors on Sync Status tab after previous fixes. Artifacts with extensions in their names (e.g., `agent:supabase-realtime-optimizer.md`) still failed to load despite `parse_artifact_id()` fix in API layer.

**Root Cause**: The deployment records were stored WITH the `.md` extension in `artifact_name` field (e.g., `artifact_name = "supabase-realtime-optimizer.md"`), but after `parse_artifact_id()` normalizes the request to remove the extension, `DeploymentTracker.get_deployment()` does an exact string match and fails.

Example from `.skillmeat-deployed.toml`:
```toml
artifact_name = "supabase-realtime-optimizer.md"   # Extension in stored name
artifact_path = "agents/supabase-realtime-optimizer.md.md"  # Double extension (corruption)
```

**Fix**:
Added `_normalize_artifact_name()` helper to `skillmeat/storage/deployment.py` that strips common extensions (`.md`, `.txt`, `.json`, `.yaml`, `.yml`) before comparison. Updated 3 locations:

1. `get_deployment()` - Normalizes both search term and stored names before comparison
2. `remove_deployment()` - Same normalization for consistency
3. `save_deployment()` - Normalizes when checking for existing deployments to update

**Files Modified**:
- `skillmeat/storage/deployment.py`:
  - Added `_ARTIFACT_EXTENSIONS` tuple and `_normalize_artifact_name()` helper (lines 29-56)
  - Updated `get_deployment()` to normalize before comparison (lines 254-261)
  - Updated `remove_deployment()` to normalize before comparison (lines 288-298)
  - Updated `save_deployment()` to normalize before comparison (lines 203-208)

**Testing**:
- All 31 deployment-related unit tests pass (`test_deployment_tracker.py`, `test_deployment_manager.py`)
- Normalization correctly handles: `test.md` → `test`, `test.yaml` → `test`, `test` → `test`

**Commits**: (pending)

**Status**: RESOLVED

---
