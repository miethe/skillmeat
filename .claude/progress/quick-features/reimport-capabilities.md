# Existing Reimport, Refresh, Re-index, and Bulk Update Capabilities

## Summary

SkillMeat has several existing capabilities for reimporting, refreshing, and updating marketplace artifacts across multiple layers:

1. **Individual artifact reimport** (API endpoint)
2. **Source rescanning** (API endpoint)
3. **Auto-tags refresh** (single + bulk endpoints)
4. **Collection-level refresh** (metadata from upstream + cache operations)
5. **Cache refresh** (projects, cache layer)
6. **CLI refresh commands** (collection, project cache)

---

## API Endpoints (skillmeat/api/routers/)

### Marketplace Sources Router
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/marketplace_sources.py`

#### 1. Rescan Source (Reindex)
- **HTTP Method**: POST
- **Path**: `/{source_id}/rescan`
- **Function**: `rescan_source()` (line 2811)
- **Route Decorator**: `@router.post("/{source_id}/rescan", ...)` (line 2752)
- **Purpose**: Trigger a full rescan of GitHub repository to discover new/updated artifacts
- **Process**:
  1. Fetches repository tree from GitHub
  2. Applies heuristic detection for artifact types
  3. Applies manual_map overrides if configured
  4. Deduplicates within source and against existing collection
  5. Updates catalog with unique artifacts
- **Returns**: `ScanResultDTO` with:
  - `artifacts_found`, `new_count`, `updated_count`, `removed_count`, `unchanged_count`
  - `duplicates_within_source`, `duplicates_cross_source`
  - `total_detected`, `total_unique`
  - `scan_duration_ms`, `scanned_at`
- **Error Handling**: 404 if source not found, 500 on scan failure

#### 2. Reimport Catalog Entry
- **HTTP Method**: POST
- **Path**: `/{source_id}/entries/{entry_id}/reimport`
- **Function**: `reimport_catalog_entry()` (line 3827)
- **Route Decorator**: `@router.post("/{source_id}/entries/{entry_id}/reimport", ...)` (line 3783)
- **Purpose**: Force re-import artifact from upstream, resetting catalog entry status
- **Handles scenarios**:
  - Artifacts with `status="imported"` that need refresh
  - Artifacts deleted but catalog still shows "imported"
  - Broken/missing artifacts in collection
- **Request Body**: `ReimportRequest` with optional `keep_deployments` flag
- **Workflow**:
  1. Validates catalog entry exists and belongs to source
  2. If `keep_deployments=True` and artifact exists:
     - Saves deployment records
     - Deletes existing artifact
     - Re-imports from upstream
     - Restores deployment records
  3. If `keep_deployments=False` or artifact missing:
     - Resets catalog entry status to "new"
     - Performs fresh import
- **Returns**: `ReimportResponse` with success flag, new artifact ID, restoration count
- **Error Handling**: 404 if source/entry not found, 500 on reimport failure

#### 3. Refresh Source Auto-Tags (Single)
- **HTTP Method**: POST
- **Path**: `/{source_id}/refresh-auto-tags`
- **Function**: `refresh_source_auto_tags()` (line 5436)
- **Route Decorator**: `@router.post("/{source_id}/refresh-auto-tags", ...)` (line 5423)
- **Purpose**: Refresh auto-tags by fetching GitHub topics for a single source
- **Process**:
  - Calls internal `_refresh_auto_tags_for_source()` helper (line 5349)
  - Fetches current GitHub topics
  - Updates `auto_tags` field
  - Preserves existing tag approval status
- **Use cases**:
  - Sources created before auto-tags feature
  - Syncing with updated GitHub topics
- **Returns**: `AutoTagRefreshResponse` with:
  - `source_id`, `tags_found`, `tags_added`, `tags_updated`
  - `segments` (tag breakdown)
- **Error Handling**:
  - 404 if source not found
  - 503 if GitHub rate limited
  - 500 for other errors

#### 4. Refresh Auto-Tags (Bulk)
- **HTTP Method**: POST
- **Path**: `/bulk-refresh-auto-tags`
- **Function**: `bulk_refresh_auto_tags()` (line 5534)
- **Route Decorator**: `@router.post("/bulk-refresh-auto-tags", ...)` (line 5520)
- **Purpose**: Refresh auto-tags for multiple sources in single request
- **Request Body**: `BulkAutoTagRefreshRequest` with list of `source_ids`
- **Process**:
  - Each source processed independently
  - Failures for one source don't affect others
  - Graceful rate-limit handling:
    - If rate-limited, remaining sources marked failed with rate-limit error
- **Returns**: `BulkAutoTagRefreshResponse` with:
  - Individual results for each source
  - Summary stats (total succeeded, total failed, rate limit info)
- **Error Handling**: Graceful degradation for individual failures

---

### User Collections Router
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/user_collections.py`

#### 5. Refresh Collection Cache (Single Collection)
- **HTTP Method**: POST
- **Path**: `/{collection_id}/refresh-cache`
- **Function**: `refresh_collection_cache()` (line 2194)
- **Route Decorator**: `@router.post("/{collection_id}/refresh-cache", ...)` (line 2173)
- **Purpose**: Refresh CollectionArtifact metadata cache for specific DB collection
- **Note**: Separate from file-based collection refresh
- **Process**:
  1. Validates collection exists in database
  2. Reads current file-based artifact metadata
  3. Updates CollectionArtifact cache rows
  4. Commits all updates atomically
- **Returns**: dict with:
  - `collection_id`, `updated_count`, `skipped_count`
  - `errors` list (per-artifact errors)
- **Error Handling**:
  - 404 if collection not found
  - 500 on commit failure with rollback

#### 6. Refresh All Collections Cache (Bulk)
- **HTTP Method**: POST
- **Path**: `/refresh-cache` (batch endpoint)
- **Function**: `refresh_all_collections_cache()` (line 797)
- **Route Decorator**: `@router.post("/refresh-cache", ...)` (line 780)
- **Purpose**: Refresh metadata cache across all DB collections
- **Process**:
  1. Queries all Collection rows from database
  2. Refreshes cached metadata for each collection
  3. Gracefully handles empty database
- **Returns**: dict with:
  - `success`, `collections_refreshed`, `total_updated`, `total_skipped`
  - `errors` list with per-collection errors
  - `duration_seconds`
- **Note**: This is a bulk operation; may take time for large collections

#### 7. Refresh Collection Artifact Metadata (File-Based)
- **HTTP Method**: POST
- **Path**: `/{collection_id}/refresh`
- **Function**: `refresh_collection()` (line 2414)
- **Route Decorator**: `@router.post("/{collection_id}/refresh", ...)` (line 2370)
- **Purpose**: Refresh artifact metadata for collection from upstream GitHub sources
- **Request Body**: `RefreshRequest` with mode, filters, dry_run options
- **Supported modes**:
  - `metadata_only`: Update metadata fields without version changes (default)
  - `check_only`: Detect available updates without applying changes
  - `sync`: Full synchronization including version updates (reserved)
- **Query params**:
  - `mode`: Optional override for request body mode
- **Filtering options**:
  - By artifact type
  - By name pattern
  - By specific fields (description, tags, author, etc.)
  - Dry-run preview
- **Returns**:
  - `RefreshResponse` for metadata_only/sync (with refreshed_count, unchanged_count)
  - `UpdateCheckResponse` for check_only (with updates_available, up_to_date)
- **Error Handling**:
  - 400 for invalid field names
  - 404 if collection not found
  - 500 on refresh failure

#### 8. Helper: Refresh Single Collection Cache
- **Function**: `_refresh_single_collection_cache()` (line 650, internal helper)
- **Purpose**: Internal helper for bulk refresh operations
- **Used by**: `refresh_all_collections_cache()`

---

### Cache Router
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/cache.py`

#### 9. Refresh Cache (Projects)
- **HTTP Method**: POST
- **Path**: `/refresh`
- **Function**: `refresh_cache()` (line 118)
- **Route Decorator**: `@router.post("/refresh", ...)` (line 107)
- **Purpose**: Manually trigger cache refresh for projects
- **Request Body**: `CacheRefreshRequest` with optional project_id and force flag
- **Behavior**:
  - By default, only refreshes stale projects (past TTL)
  - Use `force=true` to refresh regardless of staleness
  - Can target all projects or specific project
- **Returns**: `CacheRefreshResponse` with refresh stats
- **Helper**: `get_refresh_job()` (line 72) - dependency for RefreshJob

#### 10. Helper: Get Refresh Job
- **Function**: `get_refresh_job()` (line 72, internal dependency)
- **Purpose**: Provides RefreshJob dependency for cache refresh operations
- **Initializes**: RefreshJob with configurable interval_hours (6.0) and max_concurrent (3)

---

### Projects Router
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/projects.py`

#### 11. Refresh Project Cache
- **HTTP Method**: POST
- **Path**: `/cache/refresh`
- **Function**: `refresh_cache()` (line 2042)
- **Route Decorator**: `@router.post("/cache/refresh", ...)` (line 2032)
- **Purpose**: Force full refresh of project discovery cache
- **Use cases**:
  - After making changes outside the API
  - If cache seems stale
- **Process**: Triggers full filesystem scan to update cached project list
- **Returns**: Cache status after refresh

---

## CLI Commands (skillmeat/cli.py)

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cli.py`

### 12. Collection Refresh
- **Command**: `skillmeat collection refresh [COLLECTION_NAME]`
- **Function**: `collection_refresh()` (line 2593)
- **Purpose**: Refresh artifact metadata from upstream GitHub sources
- **Options**:
  - `--dry-run`: Preview changes without applying
  - `--check`: Check for updates only
  - `--check-only`: Check version updates (faster)
  - `-t, --artifact-type`: Filter by artifact type (skill, command, etc.)
  - `-n, --name-pattern`: Filter by name pattern (glob)
  - `--fields`: Refresh specific fields (description, tags, author, license)
  - `--rollback`: Restore pre-refresh snapshot
  - `-y, --yes`: Skip confirmation
  - `-m, --metadata-only`: Update metadata without version changes
- **Examples**:
  ```bash
  skillmeat collection refresh                           # Refresh all
  skillmeat collection refresh --dry-run                 # Preview
  skillmeat collection refresh --check                   # Check updates
  skillmeat collection refresh -t skill                  # By type
  skillmeat collection refresh -n "canvas-*"             # By pattern
  skillmeat collection refresh --fields tags             # Specific fields
  skillmeat collection refresh --rollback                # Restore snapshot
  ```
- **Snapshot support**: Uses `SnapshotManager` for pre-refresh backups

### 13. Cache Refresh
- **Command**: `skillmeat cache refresh [PROJECT_ID]`
- **Function**: `refresh()` (line 3823)
- **Purpose**: Refresh cache data
- **Options**:
  - `--force`: Force refresh all (regardless of TTL)
- **Behavior**:
  - Without args: Refreshes all stale projects
  - With PROJECT_ID: Refreshes only that project
- **Examples**:
  ```bash
  skillmeat cache refresh              # Refresh stale projects
  skillmeat cache refresh --force      # Force refresh all
  skillmeat cache refresh proj-123     # Refresh specific project
  ```
- **Returns**: Result with success flag, changes_detected, errors

### 14. Helper: Refresh API Cache (Single Collection)
- **Function**: `_refresh_api_cache()` (line 660)
- **Purpose**: Trigger API cache refresh if API server running
- **Makes HTTP call to**: `POST /api/v1/user-collections/{collection_id}/refresh-cache`
- **Behavior**:
  - Gracefully degrades if API not running
  - Uses 3-second timeout
  - Non-critical operation (never fails)

### 15. Helper: Refresh API Cache (Batch)
- **Function**: `_refresh_api_cache_batch()` (line 700)
- **Purpose**: Trigger batch API cache refresh for all collections
- **Makes HTTP call to**: `POST /api/v1/user-collections/refresh-cache`
- **Behavior**:
  - Gracefully degrades if API not running
  - Uses 10-second timeout (longer for batch)
  - Non-critical operation (never fails)

---

## Core Library Functions (skillmeat/core/marketplace/)

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/marketplace/import_coordinator.py`

### 16. Batch Import Coordinator
- **Class**: `ImportCoordinator` (line 121)
- **Method**: `import_entries()` (line 150)
- **Purpose**: Import multiple catalog entries to local collection with batch handling
- **Parameters**:
  - `entries`: List of catalog entry dicts (id, artifact_type, name, upstream_url, path, etc.)
  - `source_id`: Marketplace source ID
  - `strategy`: Conflict resolution (`SKIP`, `OVERWRITE`, `RENAME`)
  - `source_ref`: Optional branch/ref override
- **Process**:
  1. Generates unique import_id (UUID)
  2. Gets existing artifacts to detect conflicts
  3. Processes each entry (download, extract, parse metadata)
  4. Tracks status for each entry (success, skipped, conflict, error)
  5. Returns comprehensive ImportResult
- **Returns**: `ImportResult` with:
  - `import_id`, `source_id`, `started_at`, `completed_at`
  - `entries` list with status for each
  - Computed properties: `success_count`, `skipped_count`, `conflict_count`, `error_count`, `summary`

### 17. Import from Catalog (Convenience Function)
- **Function**: `import_from_catalog()` (line 728)
- **Purpose**: Convenience function wrapping ImportCoordinator
- **Parameters**:
  - `entries`: Catalog entries to import
  - `source_id`: Marketplace source ID
  - `strategy`: Conflict strategy ("skip", "overwrite", "rename")
  - `collection_path`: Optional override
- **Returns**: `ImportResult`

---

## Relationship Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   REIMPORT / REFRESH LAYERS                 │
└─────────────────────────────────────────────────────────────┘

CLI LAYER (skillmeat/cli.py)
├── collection refresh ────────────┐
├── cache refresh                  │
├── _refresh_api_cache             │
└── _refresh_api_cache_batch       │
                                   ↓
API LAYER (skillmeat/api/routers/)
├── POST /marketplace/sources/{id}/rescan
├── POST /marketplace/sources/{id}/entries/{id}/reimport
├── POST /marketplace/sources/{id}/refresh-auto-tags
├── POST /marketplace/sources/bulk-refresh-auto-tags
├── POST /user-collections/{id}/refresh-cache
├── POST /user-collections/refresh-cache (bulk)
├── POST /user-collections/{id}/refresh
├── POST /cache/refresh
└── POST /projects/cache/refresh
                                   ↓
CORE LAYER (skillmeat/core/)
├── ImportCoordinator.import_entries() ← handles batch import
├── import_from_catalog()
├── MarketplaceSourceRepository (scan, catalog updates)
└── [Database models + transaction handling]
```

---

## Key Features

### 1. Batch/Bulk Operations
- **Endpoints**:
  - `/marketplace/sources/bulk-refresh-auto-tags`
  - `/user-collections/refresh-cache`
- **CLI**: `collection refresh` with filters (type, pattern, fields)
- **Core**: `ImportCoordinator.import_entries()` for bulk imports

### 2. Deduplication
- **Within source**: Detects duplicate artifacts in same repo scan
- **Cross-source**: Checks against existing collection during import
- **Reporting**: Returns `duplicates_within_source`, `duplicates_cross_source`, `total_detected`, `total_unique`

### 3. Conflict Resolution
- **Strategies**: SKIP, OVERWRITE, RENAME
- **Apply at**: Bulk import coordinator level
- **Per-entry status**: ImportResult tracks outcome for each entry

### 4. Graceful Degradation
- **Rate limit handling**: Bulk endpoints fail remaining sources gracefully
- **API not running**: CLI cache refresh helpers never fail
- **Per-entry failures**: Batch operations continue despite individual errors

### 5. Atomic Transactions
- **Collection refresh-cache**: All updates committed atomically or rolled back
- **Deployment preservation**: Reimport can optionally preserve deployments

### 6. Filtering & Selective Updates
- **By artifact type**: `-t skill`, `-t command`
- **By name pattern**: `-n "canvas-*"`
- **By specific fields**: `--fields tags`, `--fields description,author`
- **Dry-run**: Preview changes without applying

### 7. History/Snapshots
- **Pre-refresh backup**: Stored via SnapshotManager
- **Rollback support**: `--rollback` to restore previous state

---

## Statistics Tracking

### Scan Statistics (rescan_source)
- `artifacts_found`: Total found in repo
- `new_count`: New artifacts added to catalog
- `updated_count`: Existing updated
- `removed_count`: Marked removed from catalog
- `unchanged_count`: Already in catalog unchanged
- `duplicates_within_source`: Same artifact found multiple times
- `duplicates_cross_source`: Already exists in other sources
- `scan_duration_ms`: How long scan took

### Import Statistics (import_entries, ImportResult)
- `success_count`: Successfully imported
- `skipped_count`: Skipped (conflict strategy)
- `conflict_count`: Conflicts detected
- `error_count`: Errors during import

### Refresh Statistics (refresh_collection, refresh_collection_cache)
- `refreshed_count` / `updated_count`: Updated artifacts
- `unchanged_count` / `skipped_count`: Not updated
- `errors`: Per-artifact errors

### Cache Statistics (refresh_cache, refresh_all_collections_cache)
- `projects_refreshed` / `collections_refreshed`: Collections touched
- `changes_detected`: Metadata changes found
- `duration_seconds`: How long operation took

---

## Error Handling Patterns

1. **HTTP Exceptions**:
   - 400: Invalid request (bad fields, missing params)
   - 404: Resource not found (source, collection, entry)
   - 500: Internal server error (scan failed, import failed, commit failed)
   - 503: Rate limit exceeded (GitHub API rate limit)

2. **Graceful Degradation**:
   - Bulk operations: Individual failures don't stop others
   - API cache refresh: Never fails CLI operations
   - Per-entry tracking: ImportResult tracks each entry status

3. **Atomic Operations**:
   - Cache refresh: All-or-nothing database commit
   - Reimport with keep_deployments: Atomically restore if reimport fails

4. **Logging**:
   - All operations logged with start/end times and stats
   - Errors logged with full stack trace for debugging
