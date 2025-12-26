---
title: SkillMeat Versioning Infrastructure
description: Complete analysis of existing versioning, deployment tracking, snapshot management, and sync infrastructure in SkillMeat. Documents Phase 1 implementation and roadmap for Phase 2+.
audience: developers
tags:
  - architecture
  - versioning
  - snapshots
  - deployment
  - sync
category: architecture
status: stable
created: 2025-12-17
updated: 2025-12-17
related_documents:
  - docs/user/guides/versioning-implementation-guide.md
  - .claude/worknotes/VERSIONING_ARCHITECTURE_DIAGRAM.md
  - .claude/worknotes/VERSIONING_IMPLEMENTATION_QUICK_START.md
---

# SkillMeat Codebase Exploration: Versioning & Sync Infrastructure

## Executive Summary

Explored the SkillMeat codebase to understand existing versioning, deployment tracking, snapshot management, and sync infrastructure. **No ArtifactVersion model exists yet** - version tracking is currently file-based (snapshots/TOML) with phase-based design planned.

**Key Finding**: The Phase 1 implementation (merged in `e00864c`) already implements core infrastructure for three-way merge support and versioning concepts. The database schema is prepared for future versioning fields but not yet used.

---

## 1. Current Architecture Overview

### 1.1 Version/Snapshot Infrastructure

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/storage/snapshot.py`

The `Snapshot` dataclass tracks collection snapshots:
```python
@dataclass
class Snapshot:
    id: str                      # timestamp-based ID
    timestamp: datetime          # When snapshot was created
    message: str                 # Description of snapshot
    collection_name: str         # Which collection
    artifact_count: int          # Number of artifacts in snapshot
    tarball_path: Path          # Path to compressed tarball
```

**SnapshotManager** manages:
- Creating tarballs of collection state (point-in-time snapshots)
- Metadata storage in `snapshots.toml` per collection
- Cursor-based pagination for snapshot listing
- Per-collection snapshot directories

**Key Integration Point**: Used by `VersionManager` for automatic version capture during deployments and syncs.

### 1.2 Deployment Tracking

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/storage/deployment.py`

The `DeploymentTracker` maintains `.skillmeat-deployed.toml` files:
```python
@dataclass
class DeploymentRecord:
    name: str                 # Artifact name
    artifact_type: str        # Type: skill, command, agent
    source: str               # Source identifier (e.g., "github:user/repo")
    version: str              # Version deployed
    sha: str                  # Content hash at deployment time
    deployed_at: str          # ISO 8601 timestamp
    deployed_from: str        # Path (collection name)
```

**Metadata Structure**:
```python
@dataclass
class DeploymentMetadata:
    collection: str           # Source collection name
    deployed_at: str          # Last deployment timestamp
    skillmeat_version: str    # Version of SkillMeat used
    artifacts: List[DeploymentRecord]
```

**Location on Disk**: `.claude/.skillmeat-deployed.toml` (per project)

### 1.3 Sync Manager

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/sync.py`

The `SyncManager` class provides:
- **Drift Detection**: Compares deployed SHA vs current collection SHA vs project local modifications
- **Three-way conflict detection**: Identifies conflicts when both collection and project changed
- **Deployment metadata reading/writing**
- **Lazy-loads VersionManager** for automatic version capture

**Key Methods**:
- `check_drift()`: Detects collection/project/local changes
- Integration with `version_mgr` property for automatic version tracking

### 1.4 Version Manager

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/version.py`

The `VersionManager` class provides:
- Automatic snapshot creation before/after operations
- Rollback operations with intelligent merge to preserve local changes
- Pre-merge/rollback safety analysis
- Audit trail recording in TOML

**Related Classes**:
- `RollbackAuditTrail`: Per-collection TOML audit logs at `{storage_path}/{collection_name}_rollback_audit.toml`
- `RollbackAuditEntry`: Individual rollback records with full metadata

---

## 2. Database Schema (Alembic Migrations)

### 2.1 Migration Files

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/migrations/versions/`

Current migrations:
1. `001_initial_schema.py` - Base schema (projects, artifacts, metadata, marketplace)
2. `20251212_1537_add_description_notes_to_marketplace_sources.py` - Marketplace fields
3. `20251212_1600_create_collections_schema.py` - Collections & groups (user-defined)
4. `20251214_0900_add_context_entity_columns.py` - Context entity support
5. `20251215_1200_add_project_templates_and_template_entities.py` - Template support
6. `20251215_1400_add_collection_type_fields.py` - Collection type categorization

**No migration for versioning fields yet** - prepared for Phase 2+

### 2.2 ORM Models

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/models.py`

Current models with version-related fields:

#### Artifact Model (lines 186-322)
```python
class Artifact(Base):
    # Version tracking fields (currently populated but not fully utilized)
    deployed_version: Optional[str]     # Version deployed to project
    upstream_version: Optional[str]     # Latest in collection
    is_outdated: bool                   # Flags when versions differ
    local_modified: bool                # Flags local project changes

    # Additional status fields
    path_pattern: Optional[str]         # Context entity patterns
    auto_load: bool                     # Context entity auto-load flag
    category: Optional[str]             # Content categorization
    content_hash: Optional[str]         # SHA256 for change detection
```

#### Collections, Groups, Templates
- `Collection`: User-defined groups of artifacts (for Phase 3+)
- `Group`: Sub-groups within collections with ordering
- `ProjectTemplate`: Reusable deployment patterns
- `MarketplaceSource` & `MarketplaceCatalogEntry`: Source tracking

---

## 3. Data Models (skillmeat/models.py)

### 3.1 Version-Related Dataclasses

**Three-Way Merge Support** (lines 212-244):
```python
@dataclass
class ThreeWayDiffResult:
    base_path: Path              # Ancestor/base version
    local_path: Path             # Current local state
    remote_path: Path            # Upstream state
    auto_mergeable: List[str]    # Files that can auto-merge
    conflicts: List[ConflictMetadata]  # Files with conflicts
    stats: DiffStats
```

**Conflict Tracking** (lines 110-158):
```python
@dataclass
class ConflictMetadata:
    file_path: str               # File with conflict
    conflict_type: Literal["content", "deletion", "both_modified", "add_add"]
    base_content: Optional[str]  # Base version content
    local_content: Optional[str] # Project version content
    remote_content: Optional[str] # Collection version content
    auto_mergeable: bool
    merge_strategy: Optional[Literal["use_local", "use_remote", "use_base", "manual"]]
```

**Rollback Operations** (lines 787-885):
```python
@dataclass
class RollbackResult:
    success: bool
    snapshot_id: str
    files_restored: List[str]    # Directly restored
    files_merged: List[str]      # Changed via merge
    conflicts: List[ConflictMetadata]
    safety_snapshot_id: Optional[str]  # Pre-rollback snapshot
    error: Optional[str]
```

**Audit Trail** (lines 944-1050):
```python
@dataclass
class RollbackAuditEntry:
    id: str                      # "rb_YYYYMMDD_HHMMSS"
    timestamp: datetime
    collection_name: str
    source_snapshot_id: str      # Safety snapshot
    target_snapshot_id: str      # Target snapshot
    operation_type: Literal["simple", "intelligent", "selective"]
    files_restored: List[str]
    files_merged: List[str]
    conflicts_resolved: List[str]
    conflicts_pending: List[str]
    preserve_changes_enabled: bool
    selective_paths: Optional[List[str]]
    success: bool
    error: Optional[str]
    metadata: Dict[str, Any]
```

### 3.2 Sync & Deployment Models

**Drift Detection** (lines 622-669):
```python
@dataclass
class DriftDetectionResult:
    artifact_name: str
    drift_type: Literal["modified", "outdated", "conflict", "added", "removed", "version_mismatch"]
    collection_sha: Optional[str]
    project_sha: Optional[str]
    collection_version: Optional[str]
    project_version: Optional[str]
    last_deployed: Optional[str]  # ISO timestamp
    recommendation: str
```

**Deployment Records** (lines 582-620):
```python
@dataclass
class DeploymentRecord:
    name: str
    artifact_type: str
    source: str
    version: str
    sha: str                      # Content hash
    deployed_at: str              # ISO timestamp
    deployed_from: str            # Collection path

@dataclass
class DeploymentMetadata:
    collection: str
    deployed_at: str
    skillmeat_version: str
    artifacts: List[DeploymentRecord]
```

---

## 4. Integration Points & Current Flow

### 4.1 Deployment Flow

```
User runs: skillmeat deploy artifact
  ↓
Deployment recorded in .skillmeat-deployed.toml
  ├─ artifact name, type, version
  ├─ SHA hash of content
  ├─ deployment timestamp
  └─ source collection name
  ↓
Version snapshot created (automatic - Phase 1)
  ├─ tarball of collection state
  ├─ snapshot metadata in snapshots.toml
  └─ used for rollback/merge operations
```

### 4.2 Sync/Drift Detection Flow

```
User runs: skillmeat sync project
  ↓
SyncManager.check_drift()
  ├─ Read deployment metadata
  ├─ Compute current collection SHA
  ├─ Compute current project SHA
  ├─ Compare: deployed.sha vs collection vs project
  └─ Return DriftDetectionResult[]
      ├─ "modified" (local changes only)
      ├─ "outdated" (upstream changes only)
      ├─ "conflict" (both changed)
      ├─ "added" (new in collection)
      └─ "removed" (removed from collection)
  ↓
If conflicts, offer merge options
  ├─ Use three-way diff/merge
  ├─ Or rollback with merge to preserve changes
  └─ Create safety snapshot before operation
```

### 4.3 Merge/Rollback Flow

```
User requests: skillback to snapshot or merge versions
  ↓
VersionManager creates safety snapshot (Phase 1 feature)
  ↓
DiffEngine.three_way_diff()
  ├─ base_path: snapshot state
  ├─ local_path: current project state
  ├─ remote_path: current collection state
  └─ Returns: auto-mergeable list + conflicts
  ↓
MergeEngine.merge()
  ├─ Auto-merge compatible files
  ├─ Flag conflicts for manual resolution
  └─ Return MergeResult
  ↓
If successful:
  ├─ Write merged content
  ├─ Create post-merge snapshot
  └─ Record audit entry
```

---

## 5. Phase-Based Design (From PRDs)

### Phase 1: Core Baseline (COMPLETED - commit e00864c)
- [x] Three-way merge support (DiffEngine, MergeEngine)
- [x] Snapshot management with tarball storage
- [x] Deployment metadata tracking (.skillmeat-deployed.toml)
- [x] Drift detection (modified/outdated/conflict)
- [x] Safety snapshots before operations
- [x] Rollback with merge-based preservation
- [x] Audit trail recording

### Phase 2-11: Planned Features (from CLAUDE.md context)
**Not yet implemented - reserved for future work**:
- Artifact version history tracking
- Parent/child version relationships
- Automatic version capture on deployment
- Version tagging/branching
- Cross-project version sync
- Version merge strategies
- Advanced conflict resolution UI

---

## 6. File Locations - Quick Reference

| Component | Location | Purpose |
|-----------|----------|---------|
| **Snapshots** | `~/.skillmeat/snapshots/{collection}/*.tar.gz` | Point-in-time backups |
| **Snapshot Metadata** | `~/.skillmeat/snapshots/{collection}/snapshots.toml` | Snapshot catalog |
| **Deployments** | `./.claude/.skillmeat-deployed.toml` | Per-project tracking |
| **Audit Trail** | `~/.skillmeat/audit/{collection}_rollback_audit.toml` | Rollback history |
| **ORM Models** | `skillmeat/cache/models.py` (lines 186-1418) | Database schema |
| **Migrations** | `skillmeat/cache/migrations/versions/*.py` | Schema evolution |
| **Sync Logic** | `skillmeat/core/sync.py` | Drift detection |
| **Version Logic** | `skillmeat/core/version.py` | Snapshots, rollback, audit |
| **Merge Logic** | `skillmeat/core/merge_engine.py` | Three-way merge |
| **Diff Logic** | `skillmeat/core/diff_engine.py` | File comparison |
| **Data Models** | `skillmeat/models.py` (lines 109-1050) | Dataclasses |

---

## 7. Key Patterns & Conventions

### 7.1 Content Hashing
- **SHA256 used throughout** for content verification
- Computed at deployment time and stored in `.skillmeat-deployed.toml`
- Used for drift detection by comparing SHAs across three points:
  1. Deployed SHA (baseline)
  2. Current collection SHA (upstream)
  3. Current project SHA (local)

### 7.2 Snapshot Metadata
- Snapshots stored as tarballs with TOML metadata
- Metadata format includes: id, timestamp, message, collection_name, artifact_count, tarball_path
- Supports cursor-based pagination

### 7.3 Audit Trail Recording
- Per-collection TOML files
- Each rollback creates RollbackAuditEntry with:
  - Operation type (simple/intelligent/selective)
  - Files affected (restored/merged/conflicts)
  - Timestamp and status
  - Full error messages if failed

### 7.4 Safety Snapshots
- Automatically created BEFORE any merge/rollback operation
- Provides recovery point if operation fails
- Referenced in RollbackResult.safety_snapshot_id

---

## 8. Database Schema - Current State

### 8.1 Tables (from models.py)
- **projects**: Project metadata and status
- **artifacts**: Deployed artifacts with version tracking fields
- **artifact_metadata**: YAML frontmatter from artifact files
- **collections**: User-defined artifact groups
- **groups**: Sub-groups within collections
- **group_artifacts**: Association with ordering
- **collection_artifacts**: Collection membership
- **marketplace**: Cached marketplace listings
- **marketplace_sources**: GitHub repo sources
- **marketplace_catalog_entries**: Discovered artifacts
- **project_templates**: Deployment templates
- **template_entities**: Template artifact associations
- **cache_metadata**: System metadata (schema_version, etc.)

### 8.2 Fields Ready for Versioning (Not Yet Used)
In Artifact model:
- `deployed_version`: Prepared for version tracking
- `upstream_version`: Prepared for version tracking
- `is_outdated`: Boolean flag for version mismatch
- `local_modified`: Boolean flag for local changes

**These fields are populated but versioning logic is still file-based (snapshots/TOML)**

---

## 9. Recommendations for Phase 2 Implementation

### 9.1 ArtifactVersion Model Needed
```python
class ArtifactVersion(Base):
    """Version record for artifact snapshots."""
    id: str              # "av_{artifact_id}_{version_sha}"
    artifact_id: str     # FK to artifacts
    version_tag: str     # e.g., "v1.2.0" or "snapshot_20251217"
    version_sha: str     # Content hash of this version
    parent_version_id: Optional[str]  # FK self-reference
    created_at: datetime
    created_by: str      # VersionManager or user
    snapshot_id: str     # Link to actual tarball
    metadata: json       # Merge strategies, tags, etc.
```

### 9.2 Integration Points
1. **After deployment**: Auto-capture version via VersionManager
2. **On merge success**: Create new ArtifactVersion with parent links
3. **On rollback**: Use ArtifactVersion history instead of manual snapshots
4. **On sync conflict**: Query ArtifactVersion tree for best merge strategy

### 9.3 Migration Strategy
1. Create `ArtifactVersion` model
2. Write migration to create table
3. Update VersionManager to create records on snapshot creation
4. Add parent/child relationship tracking
5. Update sync logic to use version history for better merge strategies

---

## 10. Summary: What Exists vs What's Missing

### What Exists (Phase 1)
✅ Snapshot creation and management (tarballs + TOML metadata)
✅ Deployment tracking (.skillmeat-deployed.toml)
✅ Drift detection (three-way conflict analysis)
✅ Three-way merge support (DiffEngine + MergeEngine)
✅ Rollback with merge-based change preservation
✅ Safety snapshots and audit trails
✅ Database schema with version fields (Artifact model)
✅ Data models for versioning concepts

### What's Missing (Phase 2+)
❌ ArtifactVersion ORM model
❌ Parent/child version relationships in database
❌ Version tagging and branching
❌ Automatic version capture on deployment
❌ Version graph navigation
❌ Advanced merge strategy selection
❌ Cross-project version sync

---

## 11. Phase 1 Commit Analysis

**Commit**: `e00864c` - "feat(sync): implement Phase 1 - core baseline support for three-way merge"

**What Was Merged**:
- Three-way merge capability (core feature)
- Snapshot infrastructure refined
- Deployment tracking enhanced
- Drift detection improved
- All dataclasses for merge/rollback operations
- Audit trail foundation

**Key Integration**: SyncManager now lazy-loads VersionManager for automatic snapshot creation

---

## Conclusion

The codebase has strong foundational infrastructure for versioning:
1. **File-based snapshots** provide point-in-time recovery
2. **Deployment metadata** tracks baseline state
3. **Three-way merge** handles conflicts intelligently
4. **Audit trails** provide full operation history
5. **Database schema** is prepared for version records

The next phase should focus on moving from snapshot-based versioning to structured ArtifactVersion records with parent/child relationships, enabling more sophisticated version management and merge strategies.
