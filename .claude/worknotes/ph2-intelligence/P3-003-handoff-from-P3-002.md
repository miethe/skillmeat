# P3-003 Handoff: SyncManager Pull

**From**: P3-002 (Sync Metadata & Detection)
**To**: P3-003 (SyncManager Pull)
**Date**: 2025-11-15
**Status**: READY FOR P3-003

---

## What P3-002 Delivers

### 1. Data Models (COMPLETE)

**Location**: `/home/user/skillmeat/skillmeat/models.py`

#### DeploymentRecord
Tracks individual artifact deployment to a project:
```python
@dataclass
class DeploymentRecord:
    name: str
    artifact_type: str  # "skill", "command", "agent"
    source: str  # e.g., "github:user/repo/path" or "local:/path"
    version: str
    sha: str  # Content hash at deployment time
    deployed_at: str  # ISO 8601 timestamp
    deployed_from: str  # Collection path (as string for TOML)
```

#### DeploymentMetadata
Container for `.skillmeat-deployed.toml` file:
```python
@dataclass
class DeploymentMetadata:
    collection: str
    deployed_at: str  # ISO 8601 timestamp
    skillmeat_version: str
    artifacts: List[DeploymentRecord]
```

#### DriftDetectionResult
Result of drift detection between collection and project:
```python
@dataclass
class DriftDetectionResult:
    artifact_name: str
    artifact_type: str
    drift_type: Literal["modified", "added", "removed", "version_mismatch"]
    collection_sha: Optional[str]
    project_sha: Optional[str]
    collection_version: Optional[str]
    project_version: Optional[str]
    last_deployed: Optional[str]  # ISO 8601
    recommendation: str  # Default: "review_manually"
```

**Drift Types**:
- `modified`: Artifact content changed in collection
- `added`: New artifact in collection (not in project)
- `removed`: Artifact removed from collection
- `version_mismatch`: Version tag changed but content may be same

### 2. SyncManager Core (COMPLETE)

**Location**: `/home/user/skillmeat/skillmeat/core/sync.py`

#### Initialization
```python
from skillmeat.core.sync import SyncManager
from skillmeat.core.collection import CollectionManager

collection_mgr = CollectionManager()
sync_mgr = SyncManager(collection_manager=collection_mgr)
```

#### Key Methods

**check_drift()**
```python
drift_results = sync_mgr.check_drift(
    project_path=Path("/path/to/project"),
    collection_name="default"  # Optional, reads from metadata
)
# Returns: List[DriftDetectionResult]
```

**update_deployment_metadata()**
```python
sync_mgr.update_deployment_metadata(
    project_path=Path("/path/to/project"),
    artifact_name="my-skill",
    artifact_type="skill",
    collection_path=Path("/path/to/collection"),
    collection_name="default"
)
```

**_compute_artifact_hash()**
```python
sha = sync_mgr._compute_artifact_hash(artifact_path)
# Returns: SHA-256 hex digest (64 chars)
```

**_load_deployment_metadata()**
```python
metadata = sync_mgr._load_deployment_metadata(project_path)
# Returns: DeploymentMetadata or None
```

**_save_deployment_metadata()**
```python
sync_mgr._save_deployment_metadata(metadata_file, metadata)
# Writes .skillmeat-deployed.toml with TOML format
```

#### Helper Methods (Internal)
- `_get_collection_artifacts()`: Scans collection for artifacts
- `_find_artifact()`: Finds artifact in list by name/type
- `_is_deployed()`: Checks if artifact is in deployment metadata
- `_recommend_sync_direction()`: Recommends sync direction (currently always "push_from_collection")
- `_get_artifact_type_plural()`: Converts "skill" → "skills", etc.
- `_get_artifact_source()`: Returns source identifier
- `_get_artifact_version()`: Extracts version from metadata file

### 3. Deployment Metadata File Schema

**File**: `.claude/.skillmeat-deployed.toml` in each project

**Schema** (TOML format):
```toml
# SkillMeat Deployment Tracking
# Version: 1.0.0

[deployment]
collection = "default"
deployed-at = "2025-11-15T10:30:00Z"
skillmeat-version = "0.2.0-alpha"

[[artifacts]]
name = "my-skill"
type = "skill"
source = "github:user/repo/path/to/skill"
version = "1.2.0"
sha = "abc123def456..."  # Content hash from collection
deployed-at = "2025-11-15T10:30:00Z"
deployed-from = "/home/user/.skillmeat/collections/default"

[[artifacts]]
name = "another-skill"
type = "skill"
source = "local:/path/to/skill"
version = "2.0.0"
sha = "789ghi012jkl..."
deployed-at = "2025-11-14T15:45:00Z"
deployed-from = "/home/user/.skillmeat/collections/default"
```

**Schema Features**:
- Multiple artifacts tracked in single file
- ISO 8601 timestamps (UTC)
- Content hashes for drift detection
- Source tracking (GitHub, local, etc.)
- Version tracking

### 4. CLI Integration (COMPLETE)

**Command**: `skillmeat sync-check`

**Location**: `/home/user/skillmeat/skillmeat/cli.py` (lines 2795-2945)

**Usage**:
```bash
# Check drift in project
skillmeat sync-check /path/to/project

# Check against specific collection
skillmeat sync-check /path/to/project --collection my-collection

# JSON output
skillmeat sync-check /path/to/project --json
```

**Exit Codes**:
- `0`: No drift detected
- `1`: Drift detected or error

**Output Modes**:

1. **Rich Table Format** (default):
```
Drift Detection Results: 2 artifacts
Project: /path/to/project

┌────────────┬──────┬─────────────┬──────────────────────┬───────────────┐
│ Artifact   │ Type │ Drift Type  │ Recommendation       │ Last Deployed │
├────────────┼──────┼─────────────┼──────────────────────┼───────────────┤
│ my-skill   │ skill│ Modified    │ Push From Collection │ 2025-11-15    │
│ new-skill  │ skill│ Added       │ Deploy To Project    │ Never         │
└────────────┴──────┴─────────────┴──────────────────────┴───────────────┘

Drift Details:
my-skill (skill)
  Drift Type: modified
  Recommendation: push_from_collection
  Collection SHA: abc123def456...
  Project SHA: xyz789abc123...
```

2. **JSON Format** (`--json`):
```json
{
  "drift_detected": true,
  "drift_count": 2,
  "artifacts": [
    {
      "name": "my-skill",
      "type": "skill",
      "drift_type": "modified",
      "collection_sha": "abc123...",
      "project_sha": "xyz789...",
      "collection_version": "1.2.0",
      "project_version": "1.1.0",
      "last_deployed": "2025-11-15T10:30:00Z",
      "recommendation": "push_from_collection"
    }
  ]
}
```

### 5. Test Coverage (COMPLETE)

**Location**: `/home/user/skillmeat/tests/test_sync.py`

**Test Suite**: 26 tests (all passing)

**Test Classes**:
1. **TestComputeArtifactHash** (7 tests):
   - Hash computation for single/multiple files
   - Hash consistency
   - Hash changes with content/new files
   - Nonexistent paths
   - Unreadable files

2. **TestLoadDeploymentMetadata** (4 tests):
   - Loading nonexistent file
   - Loading valid metadata
   - Loading multiple artifacts
   - Corrupted metadata handling

3. **TestSaveDeploymentMetadata** (2 tests):
   - Directory creation
   - Save/load roundtrip

4. **TestUpdateDeploymentMetadata** (3 tests):
   - Creating new metadata
   - Replacing existing artifact
   - Adding multiple artifacts

5. **TestCheckDrift** (6 tests):
   - No drift scenarios
   - Detecting modified artifacts
   - Detecting added artifacts
   - Detecting removed artifacts
   - Custom collection name

6. **TestDataModels** (4 tests):
   - DeploymentRecord creation
   - DeploymentMetadata creation
   - DriftDetectionResult creation
   - Validation

**Test Performance**: All tests complete in <1s

---

## What P3-003 Needs to Implement

### 1. Sync Pull Operation

**Goal**: Pull changes from project back to collection (reverse of deploy)

**Recommended Implementation**:
```python
class SyncManager:
    def sync_pull(
        self,
        artifact_name: str,
        artifact_type: str,
        project_path: Path,
        collection_name: str = "default",
        strategy: str = "prompt",  # "overwrite", "merge", "prompt"
        interactive: bool = True,
        auto_resolve: str = "abort",  # "abort", "ours", "theirs"
    ) -> SyncPullResult:
        """Pull changes from project back to collection.

        Steps:
        1. Detect drift (local modifications vs deployed_hash)
        2. Get recommendation (use _recommend_strategy from P3-001)
        3. Show preview (use _show_update_preview from P3-001)
        4. Apply strategy (project → collection)
        5. Update deployment metadata with new hash
        6. Update collection lock file
        """
```

**Data Model** (add to `models.py`):
```python
@dataclass
class SyncPullResult:
    artifact_name: str
    success: bool
    direction: str = "pull"  # Always "pull" for this operation
    strategy_used: str
    conflicts_resolved: int = 0
    conflicts_remaining: int = 0
    previous_hash: Optional[str] = None
    new_hash: Optional[str] = None
    error: Optional[str] = None
```

### 2. Integration with P3-001 Update Helpers

**Leverage Existing Methods** from `/home/user/skillmeat/skillmeat/core/artifact.py`:

**Preview Changes**:
```python
from skillmeat.core.artifact import ArtifactManager

artifact_mgr = ArtifactManager()

# Show preview (project → collection direction)
preview_data = artifact_mgr._show_update_preview(
    artifact_ref=f"{artifact_type}/{artifact_name}",
    current_path=collection_artifact_path,  # Current = collection
    update_path=project_artifact_path,  # Update = project
    strategy=strategy,
    console=console
)
```

**Get Recommendation**:
```python
recommended_strategy, reason = artifact_mgr._recommend_strategy(
    diff_result=preview_data["diff_result"],
    has_local_modifications=has_drift,
    three_way_diff=preview_data.get("three_way_diff")
)
```

**Apply Strategy**:
- Use existing `DiffEngine` and `MergeEngine` from P3-001
- Reverse direction: project → collection instead of collection → project
- Create snapshot before applying (rollback safety)

### 3. Three-Way Merge for Sync Pull

**Base Version**: Use `deployed_hash` from `.skillmeat-deployed.toml` to get base version

**Three-Way Diff**:
```python
from skillmeat.core.diff_engine import DiffEngine

diff_engine = DiffEngine()

# Get base version from deployed_hash
base_path = get_base_version_from_hash(deployed.sha)

# Three-way diff
three_way_result = diff_engine.three_way_diff(
    base_path=base_path,
    local_path=project_artifact_path,  # Project is "local"
    remote_path=collection_artifact_path,  # Collection is "remote"
)
```

**Conflict Scenarios**:
1. **Both Modified**: Project and collection both changed since deployment
   - Requires three-way merge or manual resolution
   - Use MergeEngine with conflict markers

2. **Project Modified Only**: Simple pull (overwrite collection)
   - Use "overwrite" strategy

3. **Collection Modified Only**: No pull needed
   - Inform user collection is ahead
   - Recommend `skillmeat deploy` instead

### 4. CLI Integration

**Command**: `skillmeat sync-pull`

**Recommended Signature**:
```python
@main.command(name="sync-pull")
@click.argument("artifact_name")
@click.option("--project", required=True, type=click.Path(exists=True))
@click.option("--collection", default="default")
@click.option(
    "--strategy",
    type=click.Choice(["prompt", "merge", "overwrite"]),
    default="prompt"
)
@click.option(
    "--auto-resolve",
    type=click.Choice(["abort", "ours", "theirs"]),
    default="abort"
)
@click.option("--preview", is_flag=True, help="Show preview without applying")
@click.option("--json", "output_json", is_flag=True)
def sync_pull_cmd(artifact_name, project, collection, strategy, auto_resolve, preview, output_json):
    """Pull changes from project back to collection."""
```

**Usage Examples**:
```bash
# Preview sync pull
skillmeat sync-pull my-skill --project /path/to/project --preview

# Pull with prompt strategy (default)
skillmeat sync-pull my-skill --project /path/to/project

# Pull with merge strategy (auto-merge)
skillmeat sync-pull my-skill --project /path/to/project --strategy merge

# Pull with overwrite (replace collection)
skillmeat sync-pull my-skill --project /path/to/project --strategy overwrite

# Non-interactive (abort on conflict)
skillmeat sync-pull my-skill --project /path/to/project --strategy merge --auto-resolve abort

# JSON output
skillmeat sync-pull my-skill --project /path/to/project --json
```

### 5. Deployment Metadata Updates

After successful sync pull, update both:

1. **Project Metadata** (`.skillmeat-deployed.toml`):
```python
# Update deployed_hash to new collection hash
sync_mgr.update_deployment_metadata(
    project_path=project_path,
    artifact_name=artifact_name,
    artifact_type=artifact_type,
    collection_path=collection_path,
    collection_name=collection_name
)
```

2. **Collection Lock File** (if applicable):
```python
# Update lock file with new hash
collection_mgr.lock_mgr.update_entry(
    artifact_name=artifact_name,
    artifact_type=artifact_type,
    resolved_sha=new_hash,
    resolved_version=new_version
)
```

### 6. Snapshot Integration

**Create Snapshot Before Pull**:
```python
from skillmeat.core.version import VersionManager

version_mgr = VersionManager(collection_mgr)
snapshot = version_mgr.auto_snapshot(
    collection_name=collection_name,
    message=f"Before sync pull: {artifact_name}"
)
```

**Rollback on Failure**:
```python
if not result.success:
    snapshot_mgr.restore_snapshot(snapshot, collection_path)
```

---

## Integration Patterns

### 1. Drift Detection Workflow

**For Sync Pull**:
```python
# Step 1: Check for drift
drift_results = sync_mgr.check_drift(project_path, collection_name)

# Step 2: Filter for pullable artifacts
pullable = [
    d for d in drift_results
    if d.drift_type in ["modified"]  # Only pull modified artifacts
]

# Step 3: For each pullable artifact
for drift in pullable:
    # Check if both sides modified (conflict)
    has_conflict = both_sides_modified(drift)

    if has_conflict:
        # Recommend three-way merge or manual resolution
        strategy = "merge"  # or "prompt"
    else:
        # Simple pull (overwrite)
        strategy = "overwrite"
```

### 2. Direction Detection

**Determine Sync Direction**:
```python
def get_sync_direction(drift: DriftDetectionResult) -> str:
    """Determine which direction to sync.

    Returns:
        "pull": Project → Collection
        "push": Collection → Project
        "conflict": Both modified (requires resolution)
        "none": No changes needed
    """
    if drift.drift_type == "added":
        return "push"  # Deploy new artifact to project

    if drift.drift_type == "removed":
        return "none"  # Artifact removed, nothing to pull

    if drift.drift_type == "modified":
        # Check if project has local modifications
        if has_project_modifications(drift):
            return "pull"
        else:
            return "push"

    return "none"
```

### 3. Preview Integration

**Show Preview Before Pull**:
```python
# Reuse P3-001 preview helper
artifact_mgr = ArtifactManager()

preview_data = artifact_mgr._show_update_preview(
    artifact_ref=f"{artifact_type}/{artifact_name}",
    current_path=collection_artifact_path,  # What we have
    update_path=project_artifact_path,  # What we want to pull
    strategy=strategy,
    console=console
)

# Display recommendation
recommended_strategy, reason = artifact_mgr._recommend_strategy(
    diff_result=preview_data["diff_result"],
    has_local_modifications=True,  # Project has modifications
    three_way_diff=preview_data.get("three_way_diff")
)

console.print(f"\n[yellow]Recommendation:[/yellow] {recommended_strategy}")
console.print(f"[dim]{reason}[/dim]")
```

---

## Testing Requirements

### 1. Sync Pull Tests

**Recommended Test Structure**:
```python
# tests/test_sync_pull.py

class TestSyncPull:
    """Tests for sync_pull method."""

    def test_pull_simple_overwrite(self, tmp_path):
        """Test simple pull with no conflicts."""

    def test_pull_with_merge(self, tmp_path):
        """Test pull with auto-merge."""

    def test_pull_with_conflicts(self, tmp_path):
        """Test pull with conflicts (prompt strategy)."""

    def test_pull_non_interactive_abort(self, tmp_path):
        """Test pull aborts on conflict in non-interactive mode."""

    def test_pull_non_interactive_ours(self, tmp_path):
        """Test pull keeps collection version (--auto-resolve ours)."""

    def test_pull_non_interactive_theirs(self, tmp_path):
        """Test pull takes project version (--auto-resolve theirs)."""

    def test_pull_updates_metadata(self, tmp_path):
        """Test pull updates .skillmeat-deployed.toml."""

    def test_pull_updates_lock_file(self, tmp_path):
        """Test pull updates collection lock file."""

    def test_pull_rollback_on_failure(self, tmp_path):
        """Test pull rolls back collection on failure."""

    def test_pull_preview_mode(self, tmp_path):
        """Test preview mode doesn't modify collection."""
```

**Coverage Target**: ≥75% for new code

### 2. CLI Tests

**Recommended Test Structure**:
```python
# tests/test_cli_sync_pull.py

class TestSyncPullCLI:
    """Tests for sync-pull CLI command."""

    def test_cli_pull_basic(self, tmp_path):
        """Test basic sync pull command."""

    def test_cli_pull_with_strategy(self, tmp_path):
        """Test sync pull with --strategy flag."""

    def test_cli_pull_preview(self, tmp_path):
        """Test sync pull --preview flag."""

    def test_cli_pull_json_output(self, tmp_path):
        """Test sync pull --json flag."""

    def test_cli_pull_error_handling(self, tmp_path):
        """Test error handling and messages."""
```

---

## Known Limitations (from P3-002)

### 1. Base Version Tracking

**Current State**: P3-002 does NOT store base versions in snapshots

**Impact**: Three-way merge must use `deployed_hash` to retrieve base

**Workaround for P3-003**:
- Option 1: Find snapshot matching `deployed_hash`
- Option 2: Use collection lock file to get GitHub SHA and fetch from source
- Option 3: Store base version in `.skillmeat-deployed.toml` (requires schema update)

### 2. Recommendation Logic

**Current State**: `_recommend_sync_direction()` always returns `"push_from_collection"`

**For P3-003**: Implement smarter logic:
```python
def _recommend_sync_direction(
    self,
    collection_artifact: Dict[str, Any],
    deployed: DeploymentRecord,
    has_project_modifications: bool
) -> str:
    """Recommend sync direction."""
    if has_project_modifications:
        # Project has changes → pull
        return "pull_from_project"
    else:
        # Collection has changes → push
        return "push_from_collection"
```

### 3. Source Tracking

**Current State**: `_get_artifact_source()` returns placeholder `"local:{path}"`

**For P3-003**: Enhance to read from lock file or metadata:
```python
def _get_artifact_source(self, artifact_path: Path) -> str:
    """Get real source from lock file or metadata."""
    # Try lock file first
    # Try metadata second
    # Fall back to local path
```

---

## Performance Considerations

### 1. Hash Computation

**Current Performance**: ~0.01s per artifact (tested with 26 tests in <1s)

**For P3-003**: No changes needed, performance is acceptable

### 2. Snapshot Creation

**From P0-003**: Snapshot creation <1s for typical artifact

**For P3-003**: Create snapshot before sync pull (safety net)

### 3. Preview Generation

**From P3-001**: Preview overhead ~0.5s (acceptable)

**For P3-003**: Reuse existing preview helpers from P3-001

---

## Success Criteria for P3-003

Based on P3-002 completion, P3-003 should aim for:

1. ✅ `sync pull` command implemented with preview
2. ✅ Three-way merge support (project ↔ collection)
3. ✅ Conflict handling strategies work (overwrite, merge, fork)
4. ✅ Updates collection + lock file atomically
5. ✅ Updates deployment metadata with new hash
6. ✅ Rollback works on sync pull failure
7. ✅ Non-interactive mode supported for CI/CD
8. ✅ Test coverage ≥75%

---

## Files to Reference

**P3-002 Deliverables**:
- Data models: `/home/user/skillmeat/skillmeat/models.py`
- SyncManager: `/home/user/skillmeat/skillmeat/core/sync.py`
- CLI integration: `/home/user/skillmeat/skillmeat/cli.py` (lines 2795-2945)
- Tests: `/home/user/skillmeat/tests/test_sync.py` (26 tests, all passing)

**P3-001 Helpers** (to reuse):
- Update preview: `ArtifactManager._show_update_preview()`
- Strategy recommendation: `ArtifactManager._recommend_strategy()`
- Strategy application: `ArtifactManager.apply_update_strategy()`

**Existing Infrastructure**:
- DiffEngine: `/home/user/skillmeat/skillmeat/core/diff_engine.py`
- MergeEngine: `/home/user/skillmeat/skillmeat/core/merge_engine.py`
- VersionManager: `/home/user/skillmeat/skillmeat/core/version.py`
- SnapshotManager: `/home/user/skillmeat/skillmeat/storage/snapshot.py`

---

## Ready to Proceed

P3-002 is **COMPLETE** and ready for P3-003 to begin.

All acceptance criteria met, tests passing, integrations verified.

**Next Steps**:
1. Implement `sync_pull()` method in SyncManager
2. Integrate with P3-001 preview and recommendation helpers
3. Add `skillmeat sync-pull` CLI command
4. Implement three-way merge with base version retrieval
5. Add comprehensive tests (≥75% coverage)
6. Update documentation

**Estimated Effort for P3-003**: 4 pts (as planned)

**Risk Assessment**: LOW (all dependencies complete and tested)

Good luck with P3-003!
