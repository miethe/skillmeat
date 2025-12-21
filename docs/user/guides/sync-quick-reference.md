---
title: Sync System Quick Reference
description: Quick lookup tables, state transitions, and implementation details for the sync system including drift detection, deployment tracking, and merge strategies
audience: developers
tags:
  - sync
  - deployment
  - drift-detection
  - quick-reference
category: guides
created: 2025-12-18
updated: 2025-12-18
status: active
related:
  - /docs/user/guides/phase-2-quick-start.md
---

# Sync System Quick Reference

Quick lookup tables for understanding the current sync implementation.

---

## File Locations

| Component | File | Purpose |
|-----------|------|---------|
| Sync Manager | `skillmeat/core/sync.py` | Drift detection, sync operations |
| Deployment Manager | `skillmeat/core/deployment.py` | Deploy/undeploy artifacts |
| Deployment Tracker | `skillmeat/storage/deployment.py` | Read/write deployment metadata |
| Context Sync Service | `skillmeat/core/services/context_sync.py` | Bi-directional sync (contexts) |
| Data Models | `skillmeat/models.py` | DriftDetectionResult, SyncResult, etc. |
| Deployment Metadata | `.claude/.skillmeat-deployed.toml` | Artifact baseline tracking |

---

## Core Classes

### SyncManager

| Method | Purpose | Input | Output |
|--------|---------|-------|--------|
| `check_drift()` | Detect changes | project_path | DriftDetectionResult[] |
| `sync_from_project()` | Pull sync (project→collection) | project_path, strategy | SyncResult |
| `sync_from_project_with_rollback()` | Pull with snapshot safety | project_path, strategy | SyncResult |
| `update_deployment_metadata()` | Record deployment | artifact_name, paths | - |
| `_compute_artifact_hash()` | SHA-256 hash | artifact_path | str (64 hex chars) |
| `_load_deployment_metadata()` | Read baseline | project_path | DeploymentMetadata |
| `_sync_artifact()` | Sync single artifact | drift, strategy | ArtifactSyncResult |
| `_sync_overwrite()` | Strategy: overwrite | source, dest | - |
| `_sync_merge()` | Strategy: merge | source, dest | ArtifactSyncResult |
| `_sync_fork()` | Strategy: fork | source, dest, name | Path |

### DeploymentManager

| Method | Purpose | Input | Output |
|--------|---------|-------|--------|
| `deploy_artifacts()` | Deploy artifacts | names, collection, project | Deployment[] |
| `deploy_all()` | Deploy entire collection | collection, project | Deployment[] |
| `undeploy()` | Remove artifact | name, type, project | - |
| `list_deployments()` | List deployed artifacts | project | Deployment[] |
| `check_deployment_status()` | Sync status | project | Dict[key → status] |

### DeploymentTracker (Static)

| Method | Purpose | Input | Output |
|--------|---------|-------|--------|
| `read_deployments()` | Load metadata | project_path | Deployment[] |
| `write_deployments()` | Save metadata | project_path, deployments | - |
| `record_deployment()` | Record artifact | project_path, artifact, hash | - |
| `get_deployment()` | Get single record | project_path, name, type | Deployment \| None |
| `remove_deployment()` | Remove record | project_path, name, type | - |
| `detect_modifications()` | Check if modified | project_path, name, type | bool |

---

## Data Models

### Deployment (storage unit)

```python
artifact_name: str                    # e.g., "my-skill"
artifact_type: str                    # "skill", "command", "agent"
from_collection: str                  # "default"
deployed_at: datetime
artifact_path: Path                   # Relative: "skills/my-skill"
content_hash: str                     # SHA-256 (baseline)
local_modifications: bool = False     # ⚠️ Placeholder
parent_hash: Optional[str] = None     # ⚠️ Placeholder
version_lineage: List[str] = []       # ⚠️ Placeholder
last_modified_check: Optional[datetime] = None  # ⚠️ Placeholder
modification_detected_at: Optional[datetime] = None  # ⚠️ Placeholder
```

### DriftDetectionResult (analysis)

```python
artifact_name: str
artifact_type: str
drift_type: Literal["modified", "outdated", "conflict", "added", "removed"]
collection_sha: Optional[str]
project_sha: Optional[str]
collection_version: Optional[str]
project_version: Optional[str]
last_deployed: Optional[str]
recommendation: str  # "pull_from_project", "push_to_collection", etc.
```

### ArtifactSyncResult (per-artifact result)

```python
artifact_name: str
success: bool
has_conflict: bool = False
error: Optional[str] = None
conflict_files: List[str] = []
```

### SyncResult (batch result)

```python
status: str  # "success", "partial", "cancelled", "no_changes", "dry_run"
artifacts_synced: List[str] = []
conflicts: List[ArtifactSyncResult] = []
message: str = ""
```

---

## Drift Types and Transitions

### State Matrix

```
         Collection SHA  Project SHA  Deployed SHA  Drift Type
State 1  A               A           A             (none)
State 2  A               B           A             modified
State 3  B               A           A             outdated
State 4  B               C           A             conflict
State 5  A               ∅           ∅             added
State 6  ∅               A           A             removed
```

### Transitions

```
State 1 (Synced)
  ↓ User edits project
  State 2 (Modified)
    ↓ Pull sync (overwrite)
    State 3 (Outdated) ← Now collection updated, baseline old
    ↓ Re-deploy OR update baseline
    State 1 (Synced)

State 1 (Synced)
  ↓ Collection updated (upstream)
  State 3 (Outdated)
    ↓ Deploy
    State 1 (Synced)

State 1 (Synced)
  ↓ Both collection and project changed
  State 4 (Conflict)
    ↓ Merge/Overwrite/Fork/Manual
    State 1, 2, or 3 (depends on strategy)
```

---

## Hash Computation Rules

### What Gets Hashed

✅ **Included**:
- All regular files
- Subdirectories (recursive)
- Binary files (raw bytes)
- Files with any extension

❌ **Excluded**:
- `.git/` (not in artifacts)
- `__pycache__`, `.pyc`
- Unreadable files (skipped with warning)

### Hash Changes When

✅ File content modified (even 1 char)
✅ File added
✅ File deleted
✅ File renamed (path changes)
✅ File moved to subdirectory

❌ Timestamps change
❌ Permissions change
❌ Editor metadata changes
❌ Only line ending changes (content same)

### Hash Formula

```python
hash = SHA256(
    for each file (sorted by path):
        relative_path_string +
        file_contents_bytes
)
```

---

## Sync Strategies

### Overwrite
- Replace collection with project version
- **Use when**: Project has correct changes, collection should be ignored
- **Risk**: Loses collection updates
- **Result**: Collection = Project after

### Merge
- 3-way merge (base, local, remote)
- **Base**: Current collection ⚠️ (should be deployed baseline)
- **Local**: Collection
- **Remote**: Project
- **Use when**: Want to combine changes from both
- **Risk**: Merge conflicts need manual resolution
- **Result**: Collection = merged; may have conflict markers

### Fork
- Create new artifact with `-fork` suffix
- **Use when**: Want to keep both versions
- **Risk**: Creates duplicate artifact
- **Result**: Original + projectname-fork both exist

### Prompt
- Ask user for each artifact
- **Use when**: Interactive sync, different strategies per artifact
- **Risk**: Time-consuming for many artifacts
- **Result**: User chooses per-artifact

---

## Change Detection Examples

### Example 1: Single File Edit

```
Before:
  artifact/SKILL.md (10 lines)
  deployed_sha = abc123

After:
  artifact/SKILL.md (11 lines - added 1 line)
  new_sha = def456

Hash changes because:
  - File content is different
  - File path same (relative path same)
  - Result: Different hash ✓
```

### Example 2: New File

```
Before:
  artifact/SKILL.md
  deployed_sha = abc123

After:
  artifact/SKILL.md
  artifact/new_file.txt
  new_sha = def456

Hash changes because:
  - New file added
  - Hash includes all files
  - Result: Different hash ✓
```

### Example 3: File Rename

```
Before:
  artifact/old_name.py
  deployed_sha = abc123

After:
  artifact/new_name.py  (same content as old_name.py)
  new_sha = def456

Hash changes because:
  - File path changes (relative_path in hash)
  - Even though content same, path different
  - Result: Different hash ✓
```

### Example 4: Whitespace Only

```
Before:
  artifact/SKILL.md ("hello world")
  deployed_sha = abc123

After:
  artifact/SKILL.md ("hello world")  (identical)
  new_sha = abc123

Hash does NOT change because:
  - Exact same content
  - Exact same path
  - Result: Same hash ✓
```

---

## Metadata File Format

### Location
`.claude/.skillmeat-deployed.toml`

### Structure
```toml
[[deployed]]
artifact_name = "my-skill"
artifact_type = "skill"
from_collection = "default"
deployed_at = "2025-12-17T10:30:00.000000"
artifact_path = "skills/my-skill"
content_hash = "abc123def456789..."
local_modifications = false

# Optional fields (for v1.5)
parent_hash = "def456ghi789..."
version_lineage = [
    "abc123def456789...",
    "def456ghi789abc...",
    "ghi789abc123def...",
]
last_modified_check = "2025-12-17T12:00:00.000000"
modification_detected_at = "2025-12-17T11:30:00.000000"
```

### Backward Compatibility
- Old files use `collection_sha` instead of `content_hash`
- Code reads `content_hash` first, falls back to `collection_sha`
- New saves include both (for backward compat)

---

## Deployment Recording Lifecycle

### On Deploy

```
1. User: "skillmeat deploy my-skill /path/to/project"
   ↓
2. DeploymentManager.deploy_artifacts()
   ├─ Copy artifact from collection to project
   ├─ Compute content_hash
   └─ Call DeploymentTracker.record_deployment()
      ↓
3. DeploymentTracker.record_deployment()
   ├─ Load .skillmeat-deployed.toml
   ├─ Check if existing deployment for artifact
   ├─ If yes: Replace with new record
   ├─ If no: Append new record
   └─ Write updated list
      ↓
4. File saved:
   .claude/.skillmeat-deployed.toml
   [with new deployment record]
```

### On Redeploy (Artifact Updated)

```
1. User: "skillmeat deploy my-skill /path/to/project"
   (artifact updated in collection since last deploy)
   ↓
2. Copy new version to project
3. Compute new content_hash
4. Load .skillmeat-deployed.toml
5. Find existing deployment
6. Create new record with:
   - content_hash = new hash
   - parent_hash = old hash (NEW)
   - version_lineage = [new_hash, old_hash, ...] (NEW)
   - deployed_at = new timestamp
7. Replace old record
8. Save
```

### On Undeploy

```
1. User: "skillmeat undeploy my-skill /path/to/project"
   ↓
2. Remove artifact from project
3. Load .skillmeat-deployed.toml
4. Find and remove deployment record
5. Save updated list
```

---

## Drift Check Algorithm

```python
def check_drift(project_path):
    # 1. Load baseline
    metadata = load_deployment_metadata(project_path)
    deployed_sha = metadata.artifacts[0].sha  # e.g., "abc123"

    # 2. Get current states
    collection_sha = compute_hash(collection_artifact)  # e.g., "ghi789"
    project_sha = compute_hash(project_artifact)        # e.g., "def456"

    # 3. Compare
    collection_changed = (collection_sha != deployed_sha)  # ghi ≠ abc → True
    project_changed = (project_sha != deployed_sha)        # def ≠ abc → True

    # 4. Categorize
    if collection_changed and project_changed:
        drift_type = "conflict"
    elif collection_changed:
        drift_type = "outdated"
    elif project_changed:
        drift_type = "modified"
    else:
        drift_type = None  # No drift

    # 5. Return
    return DriftDetectionResult(
        drift_type=drift_type,
        collection_sha=collection_sha,
        project_sha=project_sha,
        deployed_sha=deployed_sha,
        recommendation=recommend(drift_type),
    )
```

---

## Pull Sync Flow

```
User: skillmeat sync pull /path/to/project

1. Check drift
   → Find artifacts with "modified" drift

2. Show preview
   → Display artifacts, SHAs, strategy

3. Confirm
   → Ask user "Proceed with sync?"

4. For each artifact:
   a) Apply strategy
      - overwrite: rm collection; cp project → collection
      - merge: 3-way merge
      - fork: cp project → collection-fork
   b) Record result
   c) Track event

5. Update lock files
   → If collection manager available

6. Create auto-snapshot
   → Link to collection state

7. Record analytics
   → Track sync events

8. Return SyncResult
   status="success"
   artifacts_synced=["my-skill", ...]
```

---

## Modification Detection

### detect_modifications(project_path, artifact_name, artifact_type)

```python
# 1. Get deployment record
deployment = get_deployment(project_path, artifact_name, type)

# 2. Compute current hash
artifact_path = project_path / ".claude" / deployment.artifact_path
current_hash = compute_hash(artifact_path)

# 3. Compare
modified = (current_hash != deployment.content_hash)

# 4. Return bool
return modified  # True if different, False if same
```

**Result**:
- `True`: Project file differs from deployed baseline
- `False`: Project file matches deployed baseline

---

## Common Error Scenarios

### Scenario 1: Deployment Metadata Not Found

```
Error: "No deployment metadata found"
Cause: .skillmeat-deployed.toml doesn't exist
Solution: Deploy artifacts first (create metadata)
```

### Scenario 2: Collection Artifact Not Found

```
Error: "Artifact '{name}' not found in collection"
Cause: Artifact removed from collection, still deployed in project
Solution: Check if artifact name/type correct, or use "remove" sync
```

### Scenario 3: Project Path Doesn't Exist

```
Error: "Project path does not exist: /path/to/project"
Cause: Wrong project path provided
Solution: Check path spelling, project must have .claude/ directory
```

### Scenario 4: Three-Way Conflict Without Resolution

```
Conflict State:
  deployed_sha = A
  collection_sha = B
  project_sha = C

Available Resolutions:
  1. Merge (may produce conflict markers)
  2. Overwrite (keep collection, lose project changes)
  3. Overwrite (keep project, lose collection changes)
  4. Fork (keep both as separate artifacts)
  5. Manual (user edits and resolves manually)
```

---

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Hash small artifact (<1MB) | <50ms | Single file, fast I/O |
| Hash large artifact (>100MB) | 1-5s | Multiple files, sequential read |
| Check drift | 100-500ms | Loads metadata, computes hashes, 3-way compare |
| Pull sync (10 artifacts) | 1-10s | Copy + merge + snapshot |
| Deploy (10 artifacts) | 1-10s | Copy + hash + record |
| Merge operation | 100-2000ms | Depends on file sizes and conflicts |

---

## Test Matrix

### Basic Scenarios

```
✓ Test 1: Deploy artifact
  - Verify .skillmeat-deployed.toml created
  - Verify artifact in project
  - Verify content_hash recorded

✓ Test 2: Detect unmodified artifact
  - Verify drift check shows no changes
  - Verify project_sha == deployed_sha

✓ Test 3: Detect project modification
  - Edit project artifact
  - Verify drift type = "modified"
  - Verify project_sha ≠ deployed_sha

✓ Test 4: Detect collection update
  - Update collection artifact
  - Verify drift type = "outdated"
  - Verify collection_sha ≠ deployed_sha

✓ Test 5: Detect conflict
  - Update both collection and project differently
  - Verify drift type = "conflict"
  - Verify all three SHAs different
```

### Sync Scenarios

```
✓ Test 6: Pull sync (overwrite)
  - Modified artifact
  - Pull with overwrite
  - Verify collection updated from project
  - Verify next check shows "outdated" (need re-deploy)

✓ Test 7: Pull sync (merge)
  - Conflict artifact
  - Pull with merge
  - Verify merged content in collection
  - Verify conflict markers if needed

✓ Test 8: Pull sync (fork)
  - Conflict artifact
  - Pull with fork
  - Verify artifact-fork created
  - Verify original unchanged
```
