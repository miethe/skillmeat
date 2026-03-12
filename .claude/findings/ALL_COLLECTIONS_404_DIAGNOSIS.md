# "All Collections" 404 Investigation - Complete Diagnosis

## Issue Summary

In containerized deployment:
- **"Default Collection" WORKS** when navigated to directly
- **"All Collections" view RETURNS 404**
- **Log shows**: `Skipping project 'Collection Artifacts' — path does not exist: ~/.skillmeat/collections`

## Root Cause: Literal Tilde in Database

### The Problem

A sentinel `Project` row is created with a **literal tilde string** that never gets expanded:

```
path = "~/.skillmeat/collections"  # LITERAL TILDE STRING
```

This is stored in the database as-is, and when the code later tries to validate project paths using `Path.exists()`, it fails because the tilde isn't expanded.

### Code Locations (Tilde Bug)

**Primary issue (2 locations creating sentinel projects):**

1. **`skillmeat/api/services/artifact_cache_service.py:199`**
   - Function: `_ensure_sentinel_project_row()`
   - Creates sentinel project with path `"~/.skillmeat/collections"`
   - Used during marketplace import operations

2. **`skillmeat/cache/repositories.py:6466`**
   - Function: `DbUserCollectionRepository.ensure_sentinel_project()`
   - Creates sentinel project with path `"~/.skillmeat/collections"`
   - Used during collection artifact bootstrap

**Secondary issues (using tilde in paths but less critical):**

3. `skillmeat/core/repositories/local_context_entity.py:106` - context entities sentinel
4. `skillmeat/core/services/composite_service.py:633` - composite service sentinel
5. `skillmeat/core/services/workflow_artifact_sync_repository.py:143` - workflow artifacts sentinel
6. `skillmeat/core/sharing/vault/config.py:116` - vault config path

### How It Breaks the Flow

1. **Startup**: `ensure_sentinel_project()` creates a `Project` with `path="~/.skillmeat/collections"`
2. **Cache population**: `populate_collection_artifact_metadata()` is called
3. **Project discovery**: Code calls `project_repo.list()` which returns all projects from DB
4. **Path validation**: For each project, checks `if proj_path.exists()`
5. **Failure**: `Path("~/.skillmeat/collections").exists()` returns `False` (tilde not expanded)
6. **Skipping**: Project gets logged and skipped: `"Skipping project 'Collection Artifacts' — path does not exist: ~/.skillmeat/collections"`
7. **Result**: No deployments are scanned for "All Collections" view

### Why "Default Collection" Still Works

The default collection isn't stored as a project path - it's accessed directly via `collection_mgr.config.get_collection_path()` which properly expands `~` using `Path.home() / ".skillmeat"`.

The "All Collections" endpoint calls `list_user_collections()` which internally calls `populate_collection_artifact_metadata()` to fetch deployment information from projects. This is where it fails.

## Execution Flow Breakdown

### list_user_collections() flow (FAILS)
```
GET /api/v1/user-collections
  ↓
list_user_collections() [user_collections.py:1236]
  ↓
collection_repo.list() — returns collection DTOs ✓
  ↓
For each collection, needs deployment info via:
populate_collection_artifact_metadata() [user_collections.py:586]
  ↓
project_repo.list() — returns Project objects
  - Sentinel project has path="~/.skillmeat/collections" (LITERAL TILDE)
  ↓
For each project: Path(proj_path).exists()
  - Path("~/.skillmeat/collections").exists() → False ✗
  ↓
logger.debug("Skipping project...")
  ↓
No deployments populated
  ↓
Return incomplete collection data
```

### get_user_collection() flow (WORKS)
```
GET /api/v1/user-collections/{collection_id}
  ↓
get_user_collection() [user_collections.py:1424]
  ↓
collection_repo.get_by_id() — returns single collection ✓
  ↓
collection_to_response_with_groups() [user_collections.py:180]
  ↓
Doesn't require project path validation
  ↓
Returns collection data directly ✓
```

## Affected Endpoints

1. **`GET /api/v1/user-collections`** - LIST all collections (BROKEN)
   - Calls `populate_collection_artifact_metadata()` which needs valid project paths
   - Gets 404 or incomplete data

2. **`GET /api/v1/user-collections/{collection_id}`** - GET single collection (WORKS)
   - Doesn't require project path validation
   - Returns collection data directly

3. **`POST /api/v1/user-collections/refresh-cache`** - Refresh metadata (BROKEN)
   - Calls `populate_collection_artifact_metadata()` internally
   - Fails to scan deployments

## Database Impact in Container

In a containerized environment:
- `Path.home()` returns container user's home (e.g., `/home/app`)
- Expected path: `/home/app/.skillmeat/collections`
- Database contains: `~/.skillmeat/collections` (literal string)
- When validated: Path comparison fails

## Fix Required

All 6 locations creating sentinel projects need to expand tilde using `Path.expanduser()`:

### Correct approach:
```python
# Instead of:
path="~/.skillmeat/collections"

# Use:
path=str(Path("~/.skillmeat/collections").expanduser())
# or
path=str(Path.home() / ".skillmeat" / "collections")
```

## Files Requiring Fixes

**MUST FIX (breaks list endpoint):**
1. `skillmeat/api/services/artifact_cache_service.py:199`
2. `skillmeat/cache/repositories.py:6466`

**SHOULD FIX (preventive):**
3. `skillmeat/core/repositories/local_context_entity.py:106`
4. `skillmeat/core/services/composite_service.py:633`
5. `skillmeat/core/services/workflow_artifact_sync_repository.py:143`
6. `skillmeat/core/sharing/vault/config.py:116`

## Testing Recommendations

1. **Container test**: Run API in container, call `GET /api/v1/user-collections`
2. **Path expansion test**: Verify sentinel project path exists after creation
3. **Empty deployment list test**: Verify empty deployments list doesn't cause 404
4. **Integration test**: Test both list and get endpoints return consistent results
