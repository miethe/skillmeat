---
title: SkillMeat Versioning Architecture - Visual Reference
description: Visual diagrams and data flow documentation for the SkillMeat versioning system including deployment tracking, snapshots, and three-way merge architecture
audience: developers
tags:
  - versioning
  - architecture
  - diagrams
  - sync
  - deployment
  - snapshots
created: 2025-12-17
updated: 2025-12-18
category: Architecture
status: stable
related_documents:
  - artifact-state-transitions.md
  - sync-implementation-analysis.md
---

# SkillMeat Versioning Architecture - Visual Reference

## High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER OPERATIONS                          │
├─────────────────────────────────────────────────────────────────┤
│  deploy artifact  │  sync project  │  rollback  │  check-drift  │
└──────────┬────────────────┬─────────────────┬────────────────────┘
           │                │                 │
           ▼                ▼                 ▼
    ┌──────────────┐ ┌────────────────┐ ┌──────────────┐
    │  Deployment  │ │  SyncManager   │ │  VersionMgr  │
    │  Recording   │ │  (drift check) │ │  (rollback)  │
    └──────┬───────┘ └────────┬───────┘ └──────┬───────┘
           │                  │                 │
           │ SHA records      │ SHA compare     │ safety snapshot
           │ metadata         │                 │ merge operations
           ▼                  ▼                 ▼
    ┌──────────────────────────────────────────────────┐
    │  SnapshotManager (Tarball Storage)              │
    │  ~/.skillmeat/snapshots/{collection}/            │
    │  ├── snapshots.toml (metadata)                   │
    │  ├── snapshot_*.tar.gz (point-in-time backups)   │
    │  └── ...                                         │
    └──────┬───────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────────────────────────────────────┐
    │  RollbackAuditTrail (Operation History)          │
    │  ~/.skillmeat/audit/{collection}_rollback_*.toml │
    │  Stores: files merged, conflicts, timestamps     │
    └──────────────────────────────────────────────────┘
```

---

## Deployment Tracking - Current Implementation (Phase 1)

```
Project Directory Structure:
  .claude/
    └── .skillmeat-deployed.toml
        │
        ├── [deployment section]
        │   ├── collection = "default"
        │   ├── deployed_at = "2025-12-17T14:30:22Z"
        │   └── skillmeat_version = "0.3.0"
        │
        └── [[deployed]] (array of artifacts)
            ├── name = "canvas-design"
            ├── type = "skill"
            ├── source = "github:user/repo"
            ├── version = "v1.2.0"
            ├── sha = "abc123def456..."  ← Content hash (BASELINE)
            └── deployed_at = "2025-12-17T14:30:22Z"


Drift Detection Logic:

  baseline (deployed.sha)
         ↓
         ├──→ Compare with collection_sha (upstream)
         │    │
         │    ├── Equal → No upstream changes
         │    └── Different → Upstream modified ("outdated")
         │
         └──→ Compare with project_sha (local)
              │
              ├── Equal → No local changes
              └── Different → Local modified ("modified")

  Both different? → CONFLICT (three-way merge needed)
```

---

## Snapshot System - Current Implementation (Phase 1)

```
Snapshot Storage:
  ~/.skillmeat/snapshots/
    └── {collection_name}/
        ├── snapshots.toml
        │   │
        │   ├── [[snapshots]]
        │   │   ├── id = "20251217_143022_abc"
        │   │   ├── timestamp = 2025-12-17T14:30:22Z
        │   │   ├── message = "Before upgrade"
        │   │   ├── collection_name = "default"
        │   │   ├── artifact_count = 42
        │   │   └── tarball_path = "20251217_143022_abc.tar.gz"
        │   │
        │   └── [[snapshots]]
        │       └── ... (more snapshots)
        │
        ├── 20251217_143022_abc.tar.gz    ← Tarball 1
        ├── 20251217_143100_def.tar.gz    ← Tarball 2
        ├── 20251217_144500_ghi.tar.gz    ← Tarball 3
        └── ...


Snapshot Lifecycle:

  User creates snapshot:
    skillmeat snapshot "Before upgrade"
         ↓
    1. Tarball entire collection
    2. Store as {timestamp}_{random}.tar.gz
    3. Record metadata in snapshots.toml
    4. Return Snapshot object with id

  Automatic snapshots (Phase 1):

    Before merge/rollback:
         ↓
    VersionManager.create_safety_snapshot()
         ↓
    Stored with special message: "Safety snapshot before [operation]"
    Referenced in RollbackResult.safety_snapshot_id
```

---

## Three-Way Merge Architecture (Phase 1)

```
Conflict Resolution Flow:

  User wants to sync/merge after detecting conflict:

    A (Base/Ancestor)           B (Local/Project)       C (Remote/Collection)
    ┌──────────────┐           ┌──────────────┐         ┌──────────────┐
    │ deployed.sha │           │ project_sha  │         │ collection   │
    │              │           │              │         │ _sha         │
    │ (from        │           │ (current     │         │ (current)    │
    │ baseline)    │           │ project)     │         │              │
    └──────┬───────┘           └──────┬───────┘         └──────┬───────┘
           │                          │                        │
           └──────────────┬───────────┴────────────────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │  DiffEngine.three_way_diff() │
           │  (skillmeat/core/diff_engine.py)
           └──────────────┬───────────────┘
                          │
                ┌─────────┴─────────┐
                │                   │
                ▼                   ▼
        ┌──────────────┐   ┌─────────────┐
        │ Auto-merge   │   │ Conflicts   │
        │ candidates   │   │ (manual)    │
        │ (files)      │   │ (files)     │
        └──────┬───────┘   └─────────────┘
               │                  │
               │            ┌─────▼────────┐
               │            │ ConflictMeta │
               │            │ - file_path  │
               │            │ - base_cont  │
               │            │ - local_cont │
               │            │ - rem_cont   │
               │            │ - merge_strat
               │            └──────────────┘
               │
               ▼
        ┌──────────────────────────┐
        │ MergeEngine.merge()      │
        │ (skillmeat/core/merge_   │
        │  engine.py)              │
        └──────────────┬───────────┘
                       │
                       ▼
              ┌────────────────┐
              │ MergeResult    │
              │ - success      │
              │ - auto_merged[]│
              │ - conflicts[]  │
              │ - merged_cont  │
              └────────┬───────┘
                       │
         ┌─────────────┴──────────────┐
         │                            │
         ▼ (success)                  ▼ (conflicts)
    Write merged                 Show to user for
    content                      manual resolution
         │                            │
         ▼                            ▼
    Post-merge snapshot       Offer rollback or
    Create AuditEntry         manual conflict resolution
```

---

## Sync Flow with Safety Snapshots (Phase 1)

```
User: skillmeat sync project

  ┌─────────────────────────────┐
  │ SyncManager.check_drift()   │
  └──────────┬──────────────────┘
             │
             ▼
   ┌──────────────────────┐
   │ Detect drift type:   │
   │ - modified           │────→ Local changes only → Auto-update OK
   │ - outdated           │────→ Upstream changes → Sync available
   │ - conflict           │────→ Both changed → Need merge
   │ - added              │────→ New in collection
   │ - removed            │────→ Removed from collection
   └──────────┬───────────┘
              │
              ▼
   ┌────────────────────────┐
   │ If conflict detected:  │
   └──────────┬─────────────┘
              │
              ▼
   ┌──────────────────────────────┐
   │ VersionManager creates       │
   │ SAFETY SNAPSHOT              │
   │ (stored in ~/.skillmeat/     │
   │  snapshots/)                 │
   └──────────┬───────────────────┘
              │
              ▼
   ┌──────────────────────────────┐
   │ DiffEngine.three_way_diff()  │
   │ (base, local, remote)        │
   └──────────┬───────────────────┘
              │
              ├─→ Auto-mergeable files
              │
              └─→ Conflicts (needs manual resolution)
                   │
                   ▼
              ┌──────────────────┐
              │ User decides:    │
              │ 1. Auto-merge    │
              │ 2. Manual merge  │
              │ 3. Rollback      │
              └──────────────────┘


Rollback with Merge (Intelligent):

  User: rollback to snapshot_id (but preserve local changes)

   ┌────────────────────────────────┐
   │ VersionManager.rollback()      │
   │ preserve_changes=True          │
   └──────────┬───────────────────┘
              │
              ▼
   ┌─────────────────────────────┐
   │ Create safety snapshot of   │
   │ current state (pre-rollback)│
   └──────────┬──────────────────┘
              │
              ▼
   ┌──────────────────────────────┐
   │ Three-way merge:             │
   │ - Base: snapshot (target)    │
   │ - Local: current project     │
   │ - Remote: (same as base)     │
   │                              │
   │ Result: Files restored to    │
   │ snapshot BUT local changes   │
   │ merged in where safe         │
   └──────────┬───────────────────┘
              │
              ▼
   ┌──────────────────────────────┐
   │ Record RollbackAuditEntry    │
   │ - files_restored: [...]      │
   │ - files_merged: [...]        │
   │ - conflicts: [...]           │
   │ - timestamp, success, error  │
   │                              │
   │ Stored in:                   │
   │ ~/.skillmeat/audit/          │
   │ {collection}_rollback_*.toml │
   └──────────────────────────────┘
```

---

## Database Schema - Versioning Fields (Phase 1 Ready)

```
Artifact Table (from skillmeat/cache/models.py):

┌─────────────────────────────────────────────────────┐
│ artifacts                                           │
├─────────────────────────────────────────────────────┤
│ id (PK)                                             │
│ project_id (FK) ──→ projects.id                     │
│ name: str                                           │
│ type: str (skill|command|agent|...)                 │
│ source: str (e.g., "github:user/repo")              │
│                                                      │
│ ✓ VERSION FIELDS (READY FOR PHASE 2):              │
│ ├─ deployed_version: Optional[str]  ← "v1.2.0"    │
│ ├─ upstream_version: Optional[str]  ← Latest       │
│ ├─ is_outdated: bool                ← version check│
│ ├─ local_modified: bool              ← local edits  │
│ ├─ content_hash: Optional[str]       ← SHA256       │
│                                                      │
│ created_at, updated_at (timestamps)                 │
└─────────────────────────────────────────────────────┘

PHASE 2 ADDITIONS NEEDED:
┌─────────────────────────────────────────────────────┐
│ artifact_versions (NEW TABLE)                       │
├─────────────────────────────────────────────────────┤
│ id (PK)                 ← "av_{artifact}_{sha}"    │
│ artifact_id (FK)        ──→ artifacts.id            │
│ version_tag (str)       ← "v1.2.0" or snapshot ID   │
│ version_sha (str)       ← Content hash              │
│ parent_version_id (FK)  ──→ artifact_versions.id    │
│ created_at (datetime)                               │
│ created_by (str)        ← "system" or user          │
│ snapshot_id (str)       ← Link to tarball           │
│ merge_strategy (str)    ← How it was created        │
│ metadata (json)         ← Additional data           │
└─────────────────────────────────────────────────────┘
```

---

## Component Interaction Matrix

```
┌───────────────┬──────────┬──────────┬──────────┬──────────┐
│ Component     │ Reads    │ Writes   │ Creates  │ Uses     │
├───────────────┼──────────┼──────────┼──────────┼──────────┤
│ SyncManager   │ Deploy   │ Drift    │ —        │ Version  │
│               │ metadata │ results  │          │ Manager  │
├───────────────┼──────────┼──────────┼──────────┼──────────┤
│ Version       │ Snap     │ Snap     │ Safety   │ Diff     │
│ Manager       │ metadata │ metadata │ snapshots│ Engine   │
│               │ Artifact │ Artifact │ Audit    │ Merge    │
│               │ versions │ versions │ entries  │ Engine   │
├───────────────┼──────────┼──────────┼──────────┼──────────┤
│ Snapshot      │ TOML     │ TOML     │ Tarballs │ Paths    │
│ Manager       │ metadata │ metadata │ Metadata │ only     │
├───────────────┼──────────┼──────────┼──────────┼──────────┤
│ Diff Engine   │ Files    │ —        │ Conflicts│ —        │
│               │ Content  │          │ Metadata │          │
├───────────────┼──────────┼──────────┼──────────┼──────────┤
│ Merge Engine  │ Files    │ —        │ Merged   │ —        │
│               │ Conflicts│          │ Content  │          │
├───────────────┼──────────┼──────────┼──────────┼──────────┤
│ Deployment    │ .toml    │ .toml    │ Metadata │ SHA      │
│ Tracker       │ file     │ file     │ records  │ hashing  │
└───────────────┴──────────┴──────────┴──────────┴──────────┘
```

---

## Data Flow: Complete Sync + Merge Scenario

```
SCENARIO: User syncs project with conflict

1. USER INPUT
   └─ skillmeat sync ~/my-project

2. SYNC MANAGER
   ├─ Read .skillmeat-deployed.toml
   │  └─ Get deployed SHA (baseline)
   │
   ├─ Compute collection SHA
   │  └─ Hash current collection state
   │
   ├─ Compute project SHA
   │  └─ Hash current project state
   │
   └─ Compare: baseline vs collection vs project
      ├─ If only collection changed:
      │  └─ Drift type: "outdated"
      │     └─ Recommend: Update from collection
      │
      ├─ If only project changed:
      │  └─ Drift type: "modified"
      │     └─ Recommend: Local edits, preserve
      │
      └─ If both changed:
         └─ Drift type: "conflict"
            └─ Trigger merge process:

3. VERSION MANAGER (on conflict)
   ├─ Create SAFETY SNAPSHOT
   │  ├─ Tarball current collection state
   │  ├─ Store at ~/.skillmeat/snapshots/{collection}/
   │  ├─ Record metadata in snapshots.toml
   │  └─ Return snapshot_id
   │
   └─ Prepare for merge

4. DIFF ENGINE
   ├─ Get base path (from safety snapshot)
   ├─ Get local path (from project)
   ├─ Get remote path (from collection)
   │
   └─ Compare three-way
      ├─ Files that only changed in one place:
      │  └─ Mark as auto-mergeable
      │
      └─ Files changed in both places:
         ├─ Analyze changes
         └─ Mark as ConflictMetadata if different

5. MERGE ENGINE
   ├─ Auto-merge compatible files
   │
   └─ Flag conflicts
      ├─ Show base_content (deployed SHA)
      ├─ Show local_content (project version)
      ├─ Show remote_content (collection version)
      └─ Suggest merge_strategy

6. USER DECISION
   ├─ Accept auto-merge ✓
   ├─ Resolve conflicts manually
   └─ Rollback and try again

7. COMMIT (if successful)
   ├─ Write merged files to project
   ├─ Create post-merge snapshot
   │
   └─ Record RollbackAuditEntry
      ├─ operation_type: "intelligent"
      ├─ files_merged: [...]
      ├─ conflicts_resolved: [...]
      ├─ success: true
      └─ timestamp, id, etc.

8. UPDATE METADATA
   └─ Update .skillmeat-deployed.toml
      ├─ New SHA for merged content
      ├─ deployed_at: current timestamp
      └─ version: collection version
```

---

## Phase 1 vs Phase 2 Comparison

```
PHASE 1 (COMPLETED)           PHASE 2 (TODO)
────────────────────────────  ──────────────────────────
Snapshots:                    Snapshots + Versioning:
├─ Tarballs                   ├─ Version tree
├─ TOML metadata              ├─ Parent/child links
└─ Point-in-time recovery     ├─ Merge strategies
                              └─ Version tagging

Deployment:                   Deployment + History:
├─ Current metadata           ├─ Version records
├─ SHA baseline               ├─ Version relationships
└─ Drift detection            ├─ Auto-version capture
                              └─ Version queries

Merge:                        Merge + Strategy:
├─ Three-way diff             ├─ Strategy selection
├─ Conflict detection         ├─ Optimized merge
├─ Manual resolution          ├─ Version recommendation
└─ Safety snapshots           └─ Merge history

Audit:                        Audit + Analysis:
├─ Rollback records           ├─ Version changelog
├─ Operation history          ├─ Impact analysis
└─ TOML logging               ├─ Trend detection
                              └─ Predictive strategies
```

---

## File Organization

```
skillmeat/
├── core/
│   ├── version.py              ← VersionManager (snapshots, rollback, audit)
│   ├── version_merge.py        ← Version merge operations
│   ├── version_graph.py        ← Version DAG navigation
│   ├── sync.py                 ← SyncManager (drift detection)
│   ├── merge_engine.py         ← Three-way merge
│   ├── diff_engine.py          ← File diffing
│   └── ...
│
├── storage/
│   ├── snapshot.py             ← Snapshot, SnapshotManager
│   ├── deployment.py           ← DeploymentTracker
│   └── ...
│
├── cache/
│   ├── models.py               ← ORM models (Artifact, etc.)
│   └── migrations/
│       └── versions/
│           ├── 001_initial_schema.py
│           ├── 20251212_*.py
│           ├── ...
│           └── (Phase 2: NEW_add_artifact_versions.py)
│
├── models.py                   ← Dataclasses
│   ├── ThreeWayDiffResult (line 212)
│   ├── ConflictMetadata (line 110)
│   ├── RollbackResult (line 787)
│   ├── RollbackAuditEntry (line 944)
│   ├── DriftDetectionResult (line 622)
│   └── ...
│
└── ...

Disk Storage:
  ~/.skillmeat/
  ├── snapshots/{collection}/*.tar.gz     ← Tarballs
  ├── snapshots/{collection}/snapshots.toml
  ├── audit/{collection}_rollback_*.toml
  └── cache/cache.db                       ← SQLite
```

---

## Integration Points for Phase 2

```
Phase 2 needs to hook into:

1. VersionManager
   ├─ On snapshot creation: create ArtifactVersion record
   ├─ On rollback success: create new version with parent link
   └─ On merge success: track merge strategy in metadata

2. SyncManager
   ├─ Query version history for better merge strategies
   ├─ Recommend merge based on version relationships
   └─ Create version records on successful sync

3. ORM Models
   ├─ Add ArtifactVersion model
   ├─ Add parent_version_id relationships
   └─ Update Artifact to link to current_version

4. Migrations
   ├─ Create artifact_versions table
   ├─ Add indexes for version queries
   └─ Add constraints for parent relationships

5. API (future)
   ├─ GET /artifacts/{id}/versions
   ├─ POST /artifacts/{id}/versions/{version_id}/merge
   └─ GET /artifacts/{id}/versions/{version_id}/diff
```

---

## Summary

**Phase 1** provides the foundation:
- Snapshots for point-in-time recovery
- Deployment tracking for baselines
- Three-way merge for conflict resolution
- Audit trails for operation history

**Phase 2** will add structure:
- ArtifactVersion model for version history
- Parent/child relationships for version DAG
- Automatic version capture on operations
- Version-based merge strategy selection

Together they create a robust versioning and sync system for artifact management.
