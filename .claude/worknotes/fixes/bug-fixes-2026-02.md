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

**Commits**: 0ba10070

**Status**: RESOLVED

---

## Sync Status Tab 404 Errors - Collection Name Normalization and Case Sensitivity

**Date Fixed**: 2026-02-12
**Severity**: high
**Component**: collection-core, artifacts-api

**Issue**: Continued 404 errors for some artifacts in ArtifactOperationsModal (Contents tab and Sync Status tab) despite previous normalization fixes in API and DeploymentTracker layers.

Example errors:
- `GET /api/v1/artifacts/agent:prd-writer/files?collection=470c5a19e5054768adf543c6fcfadcef` → 404
- `GET /api/v1/artifacts/agent:supabase-realtime-optimizer.md/files?collection=default` → 404

**Root Causes**:

1. **Collection.find_artifact() lacked name normalization**: While `parse_artifact_id()` in the API layer stripped extensions from incoming requests, `Collection.find_artifact()` did exact string matching. Stored name `"supabase-realtime-optimizer.md"` didn't match normalized search `"supabase-realtime-optimizer"`.

2. **Case-sensitive collection name matching**: When `resolve_collection_name()` resolved a UUID to a collection name via DB lookup, it returned the DB name (e.g., `"Test"`), but filesystem has `"test"` (lowercase). The subsequent check `collection_record.name in collection_names` failed due to case mismatch.

**Fix**:

1. **Collection.find_artifact() normalization** (`skillmeat/core/collection.py`):
   - Added `_ARTIFACT_EXTENSIONS` tuple matching API layer
   - Added `_normalize_name()` helper that strips common extensions
   - Modified `find_artifact()` to normalize both search term and stored artifact.name

2. **Case-insensitive collection matching** (`skillmeat/api/routers/artifacts.py`):
   - Modified `resolve_collection_name()` to create lowercase lookup dictionary
   - Matches DB name (lowercased) against filesystem names (lowercased)
   - Returns filesystem name (preserves original case on disk)

**Files Modified**:
- `skillmeat/core/collection.py`:
  - Added `_ARTIFACT_EXTENSIONS` constant (line 20)
  - Added `_normalize_name()` helper (lines 23-43)
  - Modified `find_artifact()` to use normalization (lines 80-84)
- `skillmeat/api/routers/artifacts.py`:
  - Modified `resolve_collection_name()` for case-insensitive matching (lines 333-348)

**Testing**:
- All 14 collection unit tests pass
- Normalization handles: `foo.md` → `foo`, case mismatch `Test` → `test`

**Commits**: ddbbaca5

**Status**: RESOLVED (normalization layer; see below for remaining lookup issue)

---

## Artifact 404 Errors - Collection-Scoped Lookup with No Fallback

**Date Fixed**: 2026-02-12
**Severity**: high
**Component**: artifacts-api, entity-mapper

**Issue**: After normalization and case-insensitive collection matching were fixed, 404s persisted. `agent:prd-writer/files` still 404'd despite collection UUID resolving correctly to "test". `/diff` endpoints also still 404'd for artifacts with `.md` extensions.

**Root Cause**: Three compounding issues:

1. **No fallback across collections**: 8 endpoints only searched the specified collection. When the frontend sent a collection UUID that resolved to "test" but the artifact only existed in "default" (stale DB association), lookup failed with no fallback.

2. **UUID used as filesystem path**: After `resolve_collection_name()` resolved the UUID, some endpoints still used the raw UUID string as the collection path (e.g., `~/.skillmeat/collections/470c5a19.../`) instead of the resolved name.

3. **Frontend sends collection UUID**: `extractPrimaryCollection()` in `entity-mapper.ts` returns `collections[0].id` (DB UUID), not the filesystem name.

**Fix**:

Added `_find_artifact_in_collections()` helper:
- Accepts optional `preferred_collection` (name or UUID)
- Tries preferred collection first (resolving UUID as needed)
- Falls back to searching ALL collections when not found
- Returns `(artifact, collection_name)` tuple with filesystem collection name
- Logs warning when fallback is triggered (identifies stale associations)

Updated 8 endpoints to use this helper:
- `GET /{id}/files`, `GET/PUT/POST/DELETE /{id}/files/{path}`
- `GET /{id}/diff`, `GET /{id}/upstream-diff`, `GET /{id}/source-project-diff`

Net result: -89 lines (311 changes: +116, -205) — consolidated duplicated inline lookup logic.

**Files Modified**:
- `skillmeat/api/routers/artifacts.py`: Added `_find_artifact_in_collections()`, updated 8 endpoints
- `skillmeat/web/lib/api/entity-mapper.ts`: Updated JSDoc for `extractPrimaryCollection()`

**Testing**:
- All 14 collection unit tests pass
- All 31 deployment tests pass
- Python imports validated

**Commits**: 07290bc3

**Status**: RESOLVED

---

## Artifact 404 Errors - Orphaned Deployments and Corrupted Manifest Data

**Date Fixed**: 2026-02-12
**Severity**: high
**Component**: artifacts-api, collection-data

**Issue**: After all code-level fixes (normalization, case-insensitive matching, collection fallback), two specific artifacts still failed:
1. `supabase-realtime-optimizer.md` — diff endpoint returned 404 because deployed file was deleted from project but deployment record remained (orphaned)
2. `prd-writer` — frontend sent "Test" collection UUID (stale DB association) instead of "default"

Working artifacts didn't have these data-level issues, explaining why the problem was isolated.

**Root Causes**:

1. **Corrupted manifest data**: Collection manifest stored `name = "supabase-realtime-optimizer.md"` (extension baked in) and `path = "agents/supabase-realtime-optimizer.md.md"` (double extension) from original import
2. **Orphaned deployment record**: Family-shopping-dashboard had a deployment record but the actual file was deleted
3. **No graceful handling of missing files**: Diff endpoints returned hard 404/500 when one side of the comparison didn't exist

**Data Fixes**:
- Renamed `~/.skillmeat/collections/default/agents/supabase-realtime-optimizer.md.md` → `supabase-realtime-optimizer.md`
- Fixed collection manifest: name `"supabase-realtime-optimizer"`, path `"agents/supabase-realtime-optimizer.md"`
- Fixed deployment record in family-shopping-dashboard: same corrections

**Code Resilience** (`skillmeat/api/routers/artifacts.py`):
- Added `_normalize_artifact_path()` helper to detect and fix double extensions (`.md.md` → `.md`)
- All 3 diff endpoints now handle missing files gracefully:
  - Missing project file → return diff with all collection files as `status: "added"`
  - Missing collection file → return diff with all project files as `status: "deleted"`
  - Both missing → return 404 (truly not found)

**Files Modified**:
- `skillmeat/api/routers/artifacts.py`: +213, -107 lines
- `~/.skillmeat/collections/default/collection.toml`: manifest data fix
- `~/.skillmeat/collections/default/agents/supabase-realtime-optimizer.md`: file rename
- `family-shopping-dashboard/.claude/.skillmeat-deployed.toml`: deployment record fix

**Testing**: All 45 unit tests pass (collection + deployment)

**Commits**: 1311ba04

**Status**: RESOLVED

---

## Marketplace Import Linking - import_id Filter and Sources Tab Navigation

**Date Fixed**: 2026-02-18
**Severity**: medium
**Component**: artifacts-api, artifact-details-modal

**Issue**: Two related issues with Marketplace ↔ Collection bidirectional linking:

1. **Collections Tab blank in Marketplace modal**: When viewing an imported artifact in the Marketplace modal (CatalogEntryModal), the "Collections" tab showed "No collections" even though the artifact was imported and belonged to collections.

2. **Sources Tab links don't navigate in Collection**: In the Collection artifact modal (ArtifactDetailsModal), the "Sources" tab showed the source with clickable styling (cursor-pointer, hover effect, ExternalLink icon) but clicking did nothing.

**Root Causes**:

1. **import_id filter queried wrong table**: The `GET /artifacts?import_id=XYZ` endpoint tried to filter filesystem artifacts using `getattr(a, "import_id", None)`, but `import_id` is only stored on `MarketplaceCatalogEntry` in the DB — not on filesystem artifact objects. Every artifact returned `None`, so the filter returned empty results.

2. **Missing onClick handler**: The source card `<div>` at line 1199 in `artifact-details-modal.tsx` had visual affordances but no `onClick` handler to navigate.

**Fix**:

1. **Backend** (`skillmeat/api/routers/artifacts.py`):
   - Added `MarketplaceCatalogEntry` to imports
   - Query `MarketplaceCatalogEntry` table for entries with matching `import_id`
   - Build artifact IDs as `{artifact_type}:{name}` from query results
   - Filter filesystem artifacts using the matching IDs set
   - Graceful degradation: if DB query fails, return empty set with warning log

2. **Frontend** (`skillmeat/web/components/collection/artifact-details-modal.tsx`):
   - Added `onClick` handler to the source card
   - Navigates to `/marketplace/sources/${sourceEntry.sourceId}?entry=${encodeURIComponent(sourceEntry.entryPath)}`
   - Uses existing `router` from Next.js

**Files Modified**:
- `skillmeat/api/routers/artifacts.py`: +35, -3 lines
  - Added `MarketplaceCatalogEntry` import (line 125)
  - Replaced broken `getattr()` filter with DB query (lines 2153-2178)
- `skillmeat/web/components/collection/artifact-details-modal.tsx`: +8, -1 lines
  - Added onClick handler to source card (lines 1201-1205)

**Testing**:
- Python imports validated cleanly
- TypeScript type check passes (pre-existing test file errors unrelated)
- Verified correct table queried (`MarketplaceCatalogEntry.import_id`)

**Commits**: 62ebef0e

**Status**: RESOLVED

---

## Marketplace Source Plugin Detection Missing

**Date Fixed**: 2026-02-20
**Severity**: high
**Component**: marketplace, heuristic-detector

**Issue**: Plugins/composites were not being identified from marketplace sources. Individual member artifacts were detected correctly, but their parent plugins were missing. Example: source `jeremylongshore/claude-code-plugins-plus-skills` has ~21 plugins containing 1545 artifacts - all artifacts found, but 0 plugins detected.

**Root Cause**: The `_is_plugin_directory()` method existed at line 399 of `heuristic_detector.py` but was **never called** in the detection flow. The `detect_artifacts_in_tree()` function processed individual artifacts but skipped plugin/composite detection entirely.

**Fix**: Added plugin detection to the heuristic detector:

1. Created `_detect_plugin_directories()` method with 3 detection signals:
   - `plugin.json` (confidence 95) - definitive manifest
   - `COMPOSITE.md`/`PLUGIN.md`/`composite.json` (confidence 90) - strong manifest
   - 2+ entity-type subdirectories via `_is_plugin_directory()` (confidence 70) - heuristic

2. Modified `analyze_paths()` to:
   - Call plugin detection **first**, before individual artifact detection
   - Filter out member artifacts that fall inside plugin directories
   - Skip individual directory scoring for plugin descendants
   - Prevent double-counting of artifacts

**Files Modified**:
- `skillmeat/core/marketplace/heuristic_detector.py`: +196 lines
  - Added `_detect_plugin_directories()` method
  - Updated `analyze_paths()` to integrate plugin detection
- `tests/core/marketplace/test_heuristic_detector.py`: +278 lines
  - Added `TestPluginDetection` class with 13 comprehensive tests

**Testing**:
- All 223 heuristic detector tests pass
- Tests cover all 3 detection signals
- Tests verify no double-counting of member artifacts
- Tests verify sibling standalone artifacts still detected
- Tests cover multi-plugin repositories

**Commits**: eebf6955

**Status**: RESOLVED

---
