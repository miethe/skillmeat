---
title: Artifact State Transitions in SkillMeat
description: Documentation of artifact state transitions during deploy, sync, and update operations with detailed transition tables and conflict resolution strategies
audience: developers
tags:
  - versioning
  - artifact-states
  - sync
  - deployment
  - state-machine
  - conflict-resolution
created: 2025-12-17
updated: 2025-12-18
category: Architecture
status: stable
related_documents:
  - versioning-diagrams.md
  - sync-implementation-analysis.md
---

# Artifact State Transitions in SkillMeat

**Quick Reference**: Artifact state changes and transitions during deploy, sync, and update operations.

---

## State Diagram

```
                    Collection Artifact
                           ↓
                    [DEPLOY_ARTIFACT]
                    (copy + hash)
                           ↓
        ┌──────────────────────────────────────────┐
        │                                          │
        ↓                                          ↓
  Project Artifact                    .skillmeat-deployed.toml
  (.claude/skills/name/)              (baseline: content_hash)
        │                                          │
        │ ← Edited locally (git/manual)            │
        │                                          │
        ↓                                          ↓
  Modified Project Artifact           Baseline (unchanged)
  (hash_A ≠ deployed.sha)
        │                                          │
        └──────────────────┬───────────────────────┘
                           ↓
                      [CHECK_DRIFT]
                    (compare 3 SHAs)
                           ↓
          ┌────────────────────────────────┐
          ↓                                 ↓
    Project Only Changed            Collection Also Changed?
    [MODIFIED drift]                      ↓
          ↓                       ┌───────────────────┐
     [PULL_SYNC] ←────────────→   │    [CONFLICT]    │
    (project→collection)           │      drift       │
          ↓                        └───────────────────┘
     Updated Collection                  ↓
     (+ auto-snapshot)            User reviews & chooses
```

---

## State Transition Table

### State Definition

Each artifact has a **3-tuple state**: `(deployed_sha, collection_sha, project_sha)`

- **deployed_sha**: From `.skillmeat-deployed.toml` (baseline)
- **collection_sha**: Current SHA of collection artifact
- **project_sha**: Current SHA of project artifact

### Transitions

| State | deployed | collection | project | Drift Type | Recommendation | Action |
|-------|----------|------------|---------|-----------|-----------------|--------|
| 1. Synced | A | A | A | (none) | none | No sync needed |
| 2. Project Modified | A | A | B | `modified` | pull_from_project | Pull to collection |
| 3. Collection Updated | A | B | A | `outdated` | push_to_collection | Deploy to project |
| 4. Conflict | A | B | C | `conflict` | review_manually | Manual resolution |
| 5. New (not deployed) | ∅ | A | ∅ | `added` | deploy_to_project | Deploy new artifact |
| 6. Removed | A | ∅ | A | `removed` | remove_from_project | Clean up project |
| 7. Both Modified | A | B | B | `modified` | pull_from_project | Pull identical changes |
| 8. Project Diverged | A | B | C | `conflict` | review_manually | Conflict marker merge |

### Example Transitions

#### Scenario 1: Deploy → Modify → Pull

```
Initial (deployed):
  deployed_sha = abc123
  collection_sha = abc123
  project_sha = abc123
  → State 1: Synced

User edits project artifact:
  deployed_sha = abc123 (unchanged)
  collection_sha = abc123 (unchanged)
  project_sha = def456 (changed)
  → State 2: Modified
  → Drift Type: "modified"
  → Recommendation: "pull_from_project"

Pull sync with "overwrite":
  1. Copy project → collection
  2. deployed_sha = abc123 (old baseline)
  3. collection_sha = def456 (updated)
  4. project_sha = def456 (unchanged)
  → Back to State 1: Synced
```

#### Scenario 2: Collection Update → Outdated

```
Initial (deployed):
  deployed_sha = abc123
  collection_sha = abc123
  project_sha = abc123
  → State 1: Synced

Collection updated (e.g., GitHub update synced):
  deployed_sha = abc123 (old baseline)
  collection_sha = ghi789 (updated)
  project_sha = abc123 (unchanged)
  → State 3: Outdated
  → Drift Type: "outdated"
  → Recommendation: "push_to_collection" [sic - should be "push_to_project"]

Deploy new version:
  1. Copy collection → project
  2. deployed_sha = ghi789 (new baseline)
  3. collection_sha = ghi789 (unchanged)
  4. project_sha = ghi789 (changed to match)
  → State 1: Synced
```

#### Scenario 3: Three-Way Conflict

```
Initial (deployed):
  deployed_sha = abc123
  collection_sha = abc123
  project_sha = abc123
  → State 1: Synced

Collection updated, project also edited:
  deployed_sha = abc123 (baseline)
  collection_sha = ghi789 (updated)
  project_sha = def456 (modified locally)
  → State 4: Conflict
  → Drift Type: "conflict"
  → Recommendation: "review_manually"

Resolution options:
  a) Merge strategy:
     - 3-way merge (base=deployed, local=collection, remote=project)
     - May produce conflict markers
     - User reviews and resolves

  b) Overwrite (keep collection):
     - collection → project (lose local edits)

  c) Overwrite (keep project):
     - project → collection (lose collection updates)

  d) Fork:
     - Create project as new artifact (project-fork)
     - Keep both versions
```

---

## Hash Computation Rules

### File Inclusion

**Included**:
- ✅ All regular files in artifact directory
- ✅ Subdirectories (recursive)
- ✅ Binary files (hashed as-is)
- ✅ Files with any extension

**Excluded**:
- ❌ `.git/` directories (not checked but assumed not in artifact)
- ❌ `.pyc`, `__pycache__` (assumed not in artifact)
- ❌ Unreadable files (skipped with warning, non-fatal)

### Hash Sensitivity

**Detects Changes In**:
- ✅ File content (even single character)
- ✅ File additions (new files)
- ✅ File deletions (removed files)
- ✅ File renames (path change included in hash)
- ✅ File moves (relative path changes)

**Does NOT Detect**:
- ❌ Timestamp changes (only content matters)
- ❌ Permission changes (not included in hash)
- ❌ Symlink vs hardlink (only content)
- ❌ Editor metadata (if same content)

### Hash Stability

**Consistent When**:
- ✅ Content unchanged
- ✅ File order same (hash uses sorted paths)
- ✅ Same platform (path separators normalized)

**Changes When**:
- ❌ Any file content changes
- ❌ Files added/removed
- ❌ File paths change (rename/move)

---

## Deployment Record Lifecycle

### Creation Phase

```
User: "skillmeat deploy my-skill /path/to/project"
  ↓
DeploymentManager.deploy_artifacts()
  ├─ Load collection
  ├─ Find artifact in collection
  ├─ Copy to project (.claude/skills/my-skill/)
  ├─ Compute content_hash = SHA-256(project artifact)
  ├─ Get artifact version (from metadata)
  ├─ Get artifact source (from lock file)
  └─ DeploymentTracker.record_deployment()
      ├─ Load .skillmeat-deployed.toml
      ├─ Create Deployment record:
      │   artifact_name = "my-skill"
      │   artifact_type = "skill"
      │   from_collection = "default"
      │   deployed_at = ISO 8601
      │   artifact_path = "skills/my-skill"
      │   content_hash = "abc123..."
      │   local_modifications = false
      │   parent_hash = (optional)
      │   version_lineage = ["abc123..."]
      └─ Write to .skillmeat-deployed.toml
```

### Update Phase (Re-deploy)

```
User: "skillmeat deploy my-skill /path/to/project"
  ↓ (artifact updated in collection)
DeploymentManager.deploy_artifacts()
  ├─ Copy (replaces project version)
  ├─ Compute new content_hash
  └─ DeploymentTracker.record_deployment()
      ├─ Load .skillmeat-deployed.toml
      ├─ Find existing Deployment record
      ├─ Create new record with:
      │   - new content_hash
      │   - parent_hash = old_content_hash (optional)
      │   - version_lineage = [new_hash, old_hash, ...]
      └─ Replace old record in list
```

### Cleanup Phase (Undeploy)

```
User: "skillmeat undeploy my-skill /path/to/project"
  ↓
DeploymentManager.undeploy()
  ├─ Remove project artifact (.claude/skills/my-skill/)
  └─ DeploymentTracker.remove_deployment()
      ├─ Load .skillmeat-deployed.toml
      ├─ Remove Deployment record
      └─ Write updated list
```

---

## Sync Operation State Changes

### Pull Sync (Project → Collection)

**Input State**: Modified artifact in project

```
BEFORE:
  Deployment Record:      deployed_sha = A
  Collection Artifact:    collection_sha = A
  Project Artifact:       project_sha = B (modified)

Operation: pull_sync(strategy="overwrite")
  1. Check drift → drift_type = "modified"
  2. Copy project → collection
  3. Update collection with project version
  4. Create auto-snapshot

AFTER:
  Deployment Record:      deployed_sha = A (OLD - not updated)
  Collection Artifact:    collection_sha = B (UPDATED)
  Project Artifact:       project_sha = B (unchanged)

Next drift check:
  → drift_type = "outdated" (collection updated, project same)
  → recommendation = "push_to_collection"
  → Need to update deployment metadata OR re-deploy

⚠️ KEY ISSUE: Deployment baseline not automatically updated after pull!
```

### Push Sync (Collection → Project)

**Input State**: Outdated project (collection updated)

```
BEFORE:
  Deployment Record:      deployed_sha = A
  Collection Artifact:    collection_sha = B (updated)
  Project Artifact:       project_sha = A

Operation: deploy(artifact)
  1. Copy collection → project
  2. Compute new content_hash = B
  3. Update deployment record

AFTER:
  Deployment Record:      deployed_sha = B (UPDATED)
  Collection Artifact:    collection_sha = B (unchanged)
  Project Artifact:       project_sha = B (updated)

Next drift check:
  → drift_type = (none - all SHAs match)
  → No sync needed
```

---

## Conflict Resolution Strategies

### Strategy 1: Overwrite (Keep Collection)

```
CONFLICT State:
  deployed_sha = A, collection_sha = B, project_sha = C

Overwrite Strategy:
  1. Remove project artifact
  2. Copy collection → project
  3. DO NOT update deployment record

Result:
  deployed_sha = A (OLD)
  collection_sha = B (unchanged)
  project_sha = B (updated to match collection)

Next check:
  → drift_type = "outdated" (deployed_sha outdated)
  → Requires re-deployment to update baseline
```

### Strategy 2: Merge (3-Way Merge)

```
CONFLICT State:
  deployed_sha = A, collection_sha = B, project_sha = C

3-Way Merge:
  base = collection artifact (ISSUE: should use deployed!)
  local = collection
  remote = project
  output = collection (in-place)

Result:
  - Merged content written to collection
  - Conflict markers added to conflicted files
  - deployed_sha = A (OLD)
  - collection_sha = D (merged)
  - project_sha = C (unchanged)

User reviews:
  - Resolves conflict markers manually
  - Commits merged version
  - Next pull sync captures final version
```

### Strategy 3: Fork (Keep Both)

```
CONFLICT State:
  deployed_sha = A, collection_sha = B, project_sha = C

Fork Strategy:
  1. Copy project → collection/{type}/my-artifact-fork
  2. Create new artifact in collection
  3. Keep original my-artifact intact

Result:
  Original:
    deployed_sha = A
    collection_sha = B
    project_sha = C (still conflict)

Fork:
    deployed_sha = ∅ (new artifact)
    collection_sha = C (fork version)
    project_sha = C (unchanged)

Use Case:
  - Preserve both versions
  - Review differences manually
  - Decide which to keep later
```

---

## Integration with Versioning System

### Auto-Snapshot Trigger Points

**After Deployment**:
```
User: deploy artifact
  ↓ (deployment successful)
  ↓ → Auto-snapshot AFTER recording in .skillmeat-deployed.toml
Snapshot message: "Auto-deploy: my-skill to /path/to/project at 2025-12-17T10:30:00"
Snapshot content: Collection state at time of deployment
Used for: Rollback if deployment causes issues
```

**After Pull Sync**:
```
User: sync pull (overwrite/merge/fork)
  ↓ (sync successful)
  ↓ → Auto-snapshot AFTER updating collection
Snapshot message: "Auto-sync from project: my-skill at 2025-12-17T10:30:00"
Snapshot content: Collection state after merging project changes
Used for: Rollback if sync produces unwanted results
```

### Version Lineage Tracking

**Current State**: Placeholder fields, not actively maintained

```python
# In Deployment record:
parent_hash: Optional[str] = None
version_lineage: List[str] = field(default_factory=list)

# Should contain:
parent_hash = "abc123..."       # Previous deployment hash
version_lineage = [
    "def456...",  # Current (newest first)
    "abc123...",  # Previous
    "ghi789...",  # Earlier
]
```

**For v1.5 Implementation**:
1. Populate parent_hash when replacing existing deployment
2. Maintain version_lineage as linked list
3. Use for conflict resolution (three-way merge needs baseline)
4. Connect to snapshot system for version browsing

---

## Common Issues and Resolutions

### Issue 1: Deployment Baseline Out of Sync

**Symptom**:
- Pull sync updates collection
- Baseline not updated
- Next drift check shows "outdated"

**Root Cause**:
- Pull sync doesn't update deployment metadata
- Baseline still points to old version

**Resolution**:
- Auto-update deployment metadata after pull sync
- OR re-deploy to update baseline
- OR track version separately in snapshot system

### Issue 2: Lost Local Edits

**Symptom**:
- Project modified (state 2: modified)
- User forgets and deploys new collection version
- Local edits overwritten

**Root Cause**:
- Deploy overwrites project without warning
- Or user chooses "overwrite" in sync

**Prevention**:
- Check for modifications before deploy
- Warn user before overwriting
- Suggest pull sync to capture edits first

### Issue 3: Three-Way Merge Without Baseline

**Symptom**:
- Conflict state (both modified)
- Merge uses current collection as base instead of deployed
- Wrong merge result

**Root Cause**:
- Deployed baseline not stored/accessible
- Merge engine only has two versions, not three

**Resolution**:
- Store deployed baseline in temporary file during deploy
- Pass to merge engine as base
- Or reconstruct from version snapshot

---

## Testing Scenarios

### Test 1: Basic Deploy → Modify → Pull → Check

```
1. Create artifact in collection
   → collection_sha = A

2. Deploy to project
   → deployed_sha = A
   → project_sha = A
   → Drift check: none

3. Modify project file
   → project_sha = B
   → Drift check: "modified"

4. Pull sync (overwrite)
   → Collection updated: collection_sha = B
   → Drift check: "outdated" (deployed still A)

5. Re-deploy
   → deployed_sha = B
   → Drift check: none
```

### Test 2: Conflict Detection

```
1. Deploy artifact
   → deployed_sha = A, project_sha = A, collection_sha = A

2. Update collection
   → collection_sha = B

3. Modify project
   → project_sha = C

4. Check drift
   → Detects: "conflict"
   → deployed_sha = A
   → collection_sha = B
   → project_sha = C
```

### Test 3: Fork Strategy

```
1. Conflict state
   → deployed_sha = A, collection_sha = B, project_sha = C

2. Sync with fork
   → Creates my-skill-fork from project (SHA = C)
   → Original remains at B
   → Original still in conflict state

3. User manually resolves:
   → Deletes fork OR original
   → OR keeps both for reference
```
