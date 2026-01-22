# Phase 4 Infrastructure Patterns Discovery

**Date**: 2026-01-22
**Status**: Complete
**Task**: Identify existing patterns for Phase 4 implementation (Tags Imported Meta field handling)

---

## 1. SyncManager Class (check_drift Method)

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/sync.py`
**Lines**: 34-273 (check_drift), 102-273 (method)

### SyncManager Overview

```python
class SyncManager:
    """Manages synchronization between collections and project deployments."""

    def __init__(
        self,
        collection_manager=None,
        artifact_manager=None,
        snapshot_manager=None,
        version_manager=None,
    ):
```

### check_drift Method Signature

```python
def check_drift(
    self,
    project_path: Path,
    collection_name: Optional[str] = None,
) -> List[DriftDetectionResult]:
    """Check for drift between deployed and collection versions.

    Returns:
        List of DriftDetectionResult objects describing detected drift
    """
```

### Key Behavior Patterns

1. **Returns List[DriftDetectionResult]**: Each result contains:
   - `artifact_name`, `artifact_type` (identifier)
   - `drift_type` (modified, outdated, conflict, added, removed)
   - `collection_sha`, `project_sha` (hashes for comparison)
   - `modification_detected_at` (timestamp for tracking)
   - `change_origin` (local_modification, sync, deployment)

2. **Drift Detection Flow**:
   - Loads deployment metadata via `DeploymentTracker.read_deployments()`
   - Computes SHA-256 hashes for comparison
   - Three-way conflict detection (baseline, upstream, local)
   - Tracks modification timestamps on detection

3. **Integration Points**:
   - Uses `DeploymentTracker` for metadata persistence
   - Calls `_compute_artifact_hash()` for SHA generation
   - Can create version records via `_create_local_modification_version()`

---

## 2. CollectionRefresher Class

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/refresher.py`
**Lines**: 262-1110

### CollectionRefresher Overview

```python
class CollectionRefresher:
    """Refreshes artifact metadata from upstream GitHub sources."""

    def __init__(
        self,
        collection_manager: CollectionManager,
        metadata_extractor: Optional[GitHubMetadataExtractor] = None,
        github_client: Optional[GitHubClient] = None,
    ):
```

### Refresh Modes (RefreshMode Enum)

```python
class RefreshMode(str, Enum):
    METADATA_ONLY = "metadata_only"      # Update metadata fields only
    CHECK_ONLY = "check_only"            # Detect changes, don't apply
    SYNC = "sync"                        # Full synchronization
```

### Core Refresh Process

**Main Methods**:

1. **refresh_metadata(artifact, mode, dry_run, fields) → RefreshEntryResult**
   - Orchestrates single artifact refresh
   - Parse → Fetch → Detect → Apply pattern
   - Returns status ("refreshed", "unchanged", "skipped", "error")

2. **refresh_collection(collection_name, mode, dry_run, artifact_filter) → RefreshResult**
   - Batch refresh for all artifacts in collection
   - Applies filtering by type/name pattern
   - Returns aggregated results with per-artifact entries

### Field Mapping Configuration

```python
REFRESH_FIELD_MAPPING: Dict[str, str] = {
    "description": "description",
    "tags": "topics",
    "author": "author",
    "license": "license",
    "origin_source": "url",
}
```

### RefreshEntryResult Structure

```python
@dataclass
class RefreshEntryResult:
    artifact_id: str              # "type:name" format
    status: str                   # refreshed|unchanged|skipped|error
    changes: List[str]            # Modified field names
    old_values: Optional[Dict]    # Previous values
    new_values: Optional[Dict]    # New values from upstream
    error: Optional[str]          # Error message if failed
    reason: Optional[str]         # Skip/error reason
    duration_ms: float            # Timing metadata
```

### RefreshResult Structure

```python
@dataclass
class RefreshResult:
    refreshed_count: int          # Successfully updated
    unchanged_count: int          # No changes detected
    skipped_count: int            # Skipped (no source, etc.)
    error_count: int              # Failed with errors
    entries: List[RefreshEntryResult]  # Per-artifact results
    duration_ms: float            # Total operation time

    @property
    def total_processed(self) -> int
    @property
    def success_rate(self) -> float   # (refreshed + unchanged) / total
```

### Lazy Initialization Pattern

```python
@property
def metadata_extractor(self) -> GitHubMetadataExtractor:
    """Lazy initialization of metadata extractor."""
    if self._metadata_extractor is None:
        from skillmeat.core.cache import MetadataCache
        cache = MetadataCache()
        self._metadata_extractor = GitHubMetadataExtractor(cache)
    return self._metadata_extractor

@property
def github_client(self) -> GitHubClient:
    """Lazy initialization of GitHub client."""
    if self._github_client is None:
        self._github_client = get_github_client()
    return self._github_client
```

---

## 3. SnapshotManager Class

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/storage/snapshot.py`
**Lines**: 40-364

### Snapshot Dataclass

```python
@dataclass
class Snapshot:
    """Collection snapshot metadata."""
    id: str                    # timestamp-based ID (YYYYmmdd-HHMMSS-ffffff)
    timestamp: datetime
    message: str
    collection_name: str
    artifact_count: int
    tarball_path: Path
```

### SnapshotManager Key Methods

1. **create_snapshot(collection_path, collection_name, message) → Snapshot**
   - Creates tarball of collection directory
   - Stores metadata in snapshots.toml
   - Returns Snapshot object with ID

2. **list_snapshots(collection_name, limit=50, cursor=None) → Tuple[List[Snapshot], Optional[str]]**
   - Cursor-based pagination (max 100 items)
   - Returns snapshots sorted newest first
   - Next cursor for pagination

3. **restore_snapshot(snapshot, collection_path) → None**
   - Destructive operation: replaces collection directory
   - Extracts tarball to target path
   - Handles path renaming if needed

4. **get_snapshot(snapshot_id, collection_name=None) → Optional[Snapshot]**
   - Retrieves specific snapshot by ID
   - Searches all collections if collection_name not specified

5. **delete_snapshot(snapshot) → None**
   - Deletes tarball and metadata

6. **cleanup_old_snapshots(collection_name, keep_count=10) → List[Snapshot]**
   - Removes old snapshots, keeps most recent N
   - Uses cursor pagination internally

### Metadata Storage

- **Location**: `{snapshots_dir}/{collection_name}/snapshots.toml`
- **Format**: TOML with snapshots array
- **Atomic Writes**: Uses `atomic_write()` utility

---

## 4. CLI Command Patterns

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cli.py`

### Collection Refresh Command

**Command Structure**:
```bash
skillmeat collection refresh [OPTIONS]
```

**Implementation Pattern**:

```python
@collection.command(name="refresh")
@click.option("--collection", "-c", "collection_name", default=None)
@click.option("--dry-run", is_flag=True)
@click.option("--metadata-only", is_flag=True, default=True)
@click.option("--check", is_flag=True)
@click.option("--type", "-t", "artifact_type",
              type=click.Choice(["skill", "command", "agent", "mcp-server", "hook"]))
@click.option("--name", "-n", "name_pattern", default=None)
@click.option("--fields", "-f", default=None,
              help="Comma-separated field names to refresh")
def collection_refresh(collection_name, dry_run, metadata_only, check,
                       artifact_type, name_pattern, fields):
    """Refresh artifact metadata from upstream GitHub sources."""
```

**Key Flow**:
1. Create CollectionManager and CollectionRefresher
2. Determine refresh mode (check_only vs metadata_only)
3. Build artifact filter from --type and --name
4. Parse --fields into list
5. Execute refresh with progress indicator
6. Display summary table with counts
7. Show dry-run notice if applicable

**Error Handling**: Try/except with sys.exit(1) on failure

---

## 5. API Endpoint Patterns

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/user_collections.py`
**Lines**: 1500-1594 (refresh_collection endpoint)

### Collection Refresh Endpoint

**Route Definition**:
```python
@router.post(
    "/{collection_id}/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh collection artifact metadata",
)
async def refresh_collection(
    collection_id: str,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    request: RefreshRequest = Body(...),
    mode: Optional[RefreshModeEnum] = Query(None),
) -> RefreshResponse:
```

**Key Patterns**:

1. **Dependency Injection**:
   - `CollectionManagerDep` (typed dependency)
   - `TokenDep` (authentication)

2. **Request/Response Models**:
   - `RefreshRequest` (body) - contains mode, filters, dry_run
   - `RefreshModeEnum` (query override)
   - `RefreshResponse` (typed response)

3. **Error Handling**:
   - Check collection exists (404 if not)
   - Log before raising HTTPException
   - Include error detail in response

4. **Implementation Pattern**:
   ```python
   # 1. Validate collection exists
   if collection_id not in collection_mgr.list_collections():
       raise HTTPException(404, detail=f"Collection not found")

   # 2. Resolve mode (query param overrides body)
   effective_mode = mode if mode is not None else request.mode

   # 3. Create refresher and execute
   refresher = CollectionRefresher(collection_mgr)
   result = refresher.refresh_collection(
       collection_name=collection_id,
       mode=core_mode,
       dry_run=request.dry_run,
       artifact_filter=request.artifact_filter,
   )

   # 4. Convert and return
   return RefreshResponse.from_refresh_result(
       collection_id=collection_id,
       result=result,
       mode=effective_mode,
       dry_run=request.dry_run,
   )
   ```

5. **Status Codes**:
   - 200: Success
   - 400: Invalid request
   - 404: Collection not found
   - 500: Server error

---

## 6. Integration Points for Phase 4

### Tags-Imported-Meta Field Handling

**Current Architecture**:

1. **Artifact Model** has `tags` field (List[str])
2. **Artifact Metadata** has `tags_imported_at` (timestamp)
3. **Collection Refresh** updates tags from GitHub topics

**Phase 4 Opportunities**:

1. **SyncManager Integration**:
   - Track tags modifications via drift detection
   - `modification_detected_at` already tracks first detection
   - Can extend to track field-level changes

2. **CollectionRefresher Integration**:
   - `tags` in REFRESH_FIELD_MAPPING already supported
   - Tags imported from GitHub `topics` field
   - `RefreshEntryResult` tracks old/new tag values

3. **CLI Command**:
   - `--fields tags` filter already supported
   - Can add `--show-imported-meta` option to display timestamps

4. **API Endpoint**:
   - RefreshResponse can include imported metadata
   - Include `tags_imported_at` in response

### Related Components to Consider

1. **Artifact Model** (`skillmeat/core/artifact.py`):
   - `tags` field
   - `metadata.tags_imported_at`
   - `origin`, `origin_source` fields

2. **Metadata Extractor** (`skillmeat/core/github_metadata.py`):
   - Maps `topics` → `tags`
   - Tracks extraction timestamp

3. **Deployment Tracking** (`skillmeat/storage/deployment.py`):
   - DeploymentRecord model
   - Tracks `modification_detected_at`

---

## Recommendations for Phase 4 Implementation

### 1. Extend SyncManager
- Add method to track field-level changes
- Include `tags_imported_at` in DriftDetectionResult
- Create mechanism to update imported timestamps

### 2. Enhance CollectionRefresher
- Add `tags_imported_at` update when tags change
- Track import timestamp in metadata updates
- Return imported metadata in RefreshEntryResult

### 3. CLI Enhancement
- Add `--show-metadata` flag to display import timestamps
- Include imported timestamps in summary output

### 4. API Response Enhancement
- Extend RefreshResponse to include import timestamps
- Add per-artifact `tags_imported_at` in RefreshEntryResult

### 5. Data Persistence
- Ensure `tags_imported_at` persists in artifact metadata
- Add migration if needed for existing artifacts

---

## Files Referenced

1. **Core Logic**:
   - `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/sync.py` (SyncManager)
   - `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/refresher.py` (CollectionRefresher)
   - `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/storage/snapshot.py` (SnapshotManager)

2. **CLI Integration**:
   - `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cli.py` (collection_refresh command)

3. **API Integration**:
   - `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/user_collections.py` (refresh endpoint)

4. **Data Models**:
   - `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/artifact.py`
   - `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/storage/deployment.py`
   - `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/collections.py`

---

## Summary

Phase 4 implementation should focus on:

1. **Tracking when tags are imported** from GitHub
2. **Persisting `tags_imported_at` timestamps** in artifact metadata
3. **Updating timestamps** when CollectionRefresher updates tags
4. **Exposing import metadata** through CLI and API
5. **Maintaining consistency** across sync, refresh, and deployment workflows

The existing infrastructure provides solid foundation:
- SyncManager handles change detection and tracking
- CollectionRefresher handles metadata updates
- SnapshotManager provides rollback capability
- CLI and API already support filtering and mode selection

Extension points are clear and follow established patterns.
