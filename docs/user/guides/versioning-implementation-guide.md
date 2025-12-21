---
title: SkillMeat Versioning Implementation Guide
description: Navigation guide and overview for Phase 2 versioning implementation. Covers current state, critical file paths, key concepts, and Phase 2 requirements.
audience: developers
tags:
  - implementation
  - versioning
  - phase-2
  - guide
category: guides
status: stable
created: 2025-12-17
updated: 2025-12-17
related_documents:
  - docs/dev/architecture/versioning-infrastructure.md
  - .claude/worknotes/VERSIONING_ARCHITECTURE_DIAGRAM.md
  - .claude/worknotes/VERSIONING_IMPLEMENTATION_QUICK_START.md
---

# SkillMeat Versioning Implementation Guide

## Overview

This guide serves as a navigation document for understanding SkillMeat's versioning infrastructure and implementing Phase 2 features. Phase 1 (three-way merge, snapshots, drift detection) is complete. Phase 2 requires implementing the ArtifactVersion model with parent/child relationships.

## Current Contents

### Versioning & Sync Infrastructure Exploration

Three comprehensive documents analyzing the existing codebase infrastructure for versioning, deployment tracking, snapshots, and three-way merge support:

1. **versioning-infrastructure.md** - Complete codebase exploration
   - What exists (Phase 1 - completed)
   - What's missing (Phase 2+ - planned)
   - File locations and integration points
   - Phase-based design overview
   - Database schema analysis
   - 11 sections covering every aspect

2. **VERSIONING_ARCHITECTURE_DIAGRAM.md** - Visual architecture reference
   - Data flow diagrams
   - Deployment tracking system
   - Snapshot system details
   - Three-way merge process
   - Sync flow with safety snapshots
   - Database schema relationships
   - Component interaction matrix
   - Complete scenario walkthrough

3. **VERSIONING_IMPLEMENTATION_QUICK_START.md** - Implementation guide for Phase 2
   - TL;DR of current state
   - Critical file paths
   - Understanding version tracking
   - Artifact model version fields ready for use
   - Key integration points
   - Dataclasses for Phase 2
   - Testing checklist
   - Common queries needed

## Quick Facts

- **No ArtifactVersion model exists yet** - version tracking is file-based (snapshots, TOML)
- **Phase 1 is complete** - three-way merge, snapshots, drift detection, audit trails (commit e00864c)
- **Phase 2 needs**: ArtifactVersion model with parent/child relationships
- **Database schema ready**: Artifact model has version fields prepared but not yet used
- **Migrations exist**: 6 current migrations, ready for versioning migration

## Key Locations

### Core Versioning
- `skillmeat/core/version.py` - VersionManager, RollbackAuditTrail
- `skillmeat/core/sync.py` - SyncManager (uses VersionManager)
- `skillmeat/core/merge_engine.py` - Three-way merge
- `skillmeat/core/diff_engine.py` - File diffing

### Storage
- `skillmeat/storage/snapshot.py` - Snapshot, SnapshotManager
- `skillmeat/storage/deployment.py` - DeploymentTracker

### Database
- `skillmeat/cache/models.py` - ORM models with version fields
- `skillmeat/cache/migrations/versions/` - Migration files

### Data Models
- `skillmeat/models.py` - Dataclasses (lines 109-1050)

## Reading Order for Phase 2 Implementation

### 1. Get Oriented (15 minutes)
Start with **VERSIONING_IMPLEMENTATION_QUICK_START.md** to understand:
- TL;DR of current state
- Critical file paths for versioning
- What fields are ready for use
- Key integration points

### 2. Understand System Design (20 minutes)
Review **VERSIONING_ARCHITECTURE_DIAGRAM.md** to visualize:
- Data flow through the system
- Component relationships
- Deployment and snapshot tracking
- Three-way merge process
- Complete scenario walkthrough

### 3. Deep Dive (45 minutes)
Read **versioning-infrastructure.md** section by section:
- Section 1: Current architecture overview
- Section 2: Database schema and migrations
- Section 3: Data models and dataclasses
- Section 4: Integration points and flows
- Section 5: Phase-based design
- Section 6: File locations quick reference
- Section 7: Key patterns and conventions
- Section 8: Database schema current state
- Section 9: Phase 2 recommendations
- Section 10: What exists vs what's missing

### 4. Review Actual Implementation (1+ hours)
Read the actual files in this order:
- `skillmeat/core/version.py` - VersionManager and RollbackAuditTrail
- `skillmeat/models.py` - All versioning dataclasses (lines 109-1050)
- `skillmeat/cache/models.py` - ORM models with version fields
- `skillmeat/cache/migrations/versions/001_initial_schema.py` - Example migration
- `skillmeat/storage/snapshot.py` - Snapshot storage
- `skillmeat/storage/deployment.py` - Deployment tracking
- `skillmeat/core/sync.py` - Sync and drift detection
- `skillmeat/core/merge_engine.py` - Three-way merge implementation

## Phase 1 Features (Completed)

✅ Snapshot creation and management
✅ Deployment tracking with SHA hashing
✅ Drift detection (three-way analysis)
✅ Three-way merge support
✅ Rollback with change preservation
✅ Safety snapshots
✅ Audit trails

## Phase 2 Requirements

❌ ArtifactVersion ORM model
❌ Parent/child version relationships
❌ Version tagging and branching
❌ Automatic version capture on deployment
❌ Version graph navigation
❌ Advanced merge strategy selection

## File Structure

The versioning documentation is organized as:

```
docs/
├── architecture/
│   └── versioning-infrastructure.md        ← Complete exploration (11 sections)
└── guides/
    └── versioning-implementation-guide.md  ← This guide

.claude/worknotes/
├── VERSIONING_IMPLEMENTATION_QUICK_START.md ← Phase 2 guide
├── VERSIONING_ARCHITECTURE_DIAGRAM.md     ← Visual reference
└── (other exploration files)
```

## Key Insights from Exploration

1. **Phase 1 is solid** - Three-way merge and snapshots provide good foundation
2. **Database ready** - Schema prepared, just needs new model
3. **Integration points clear** - VersionManager hooks exist, SyncManager uses it
4. **Testing clear** - Phase 1 patterns can be extended
5. **Migration path clear** - Add ArtifactVersion table, populate on operations

## Frequently Asked Questions

**Q: Where are snapshots stored?**
A: ~/.skillmeat/snapshots/{collection_name}/ as tarballs + TOML metadata

**Q: How is drift detected?**
A: Compare three SHAs: deployed (baseline), collection (upstream), project (local)

**Q: How does merge work?**
A: Three-way merge using base + local + remote, with conflict detection

**Q: What's the audit trail?**
A: Per-collection TOML files in ~/.skillmeat/audit/ tracking rollback operations

**Q: When should I implement ArtifactVersion?**
A: Phase 2, after Phase 1 is proven stable in production

**Q: What database fields are ready for versioning?**
A: In the Artifact model:
- `deployed_version: Optional[str]`
- `upstream_version: Optional[str]`
- `is_outdated: bool`
- `local_modified: bool`
- `content_hash: Optional[str]`

**Q: How does VersionManager integrate with SyncManager?**
A: SyncManager lazy-loads VersionManager via a property. When sync operations need to preserve state, VersionManager creates safety snapshots and records operations in audit trails.

## Phase 2 Implementation Roadmap

### Step 1: Create ArtifactVersion Model
Create Alembic migration and ORM model:
```python
class ArtifactVersion(Base):
    id: str
    artifact_id: str          # FK to artifacts
    version_tag: str
    version_sha: str
    parent_version_id: Optional[str]
    created_at: datetime
    created_by: str
    snapshot_id: str
    metadata: json
```

### Step 2: Update VersionManager
Modify to populate version records:
- On snapshot creation
- When merge succeeds
- When rollback completes
- Track parent/child relationships

### Step 3: Add Repository Methods
Implement queries for:
- Get version history
- Find common ancestor
- Query version tree
- Filter by date range

### Step 4: Update SyncManager
Enhance to use version history:
- Query ArtifactVersion for merge strategy
- Use parent/child relationships
- Track version relationships

### Step 5: Add API Endpoints
Create REST endpoints:
- GET /api/v1/artifacts/{id}/versions
- GET /api/v1/artifacts/{id}/versions/{version_id}
- GET /api/v1/artifacts/{id}/versions/{version_id}/diff
- POST /api/v1/artifacts/{id}/versions/{version_id}/restore

### Step 6: Write Tests
Comprehensive test coverage:
- Version creation
- Parent/child relationships
- Version history queries
- Merge strategy selection
- API endpoints

## Common Queries During Implementation

### Find all snapshots for a collection
```python
snapshot_mgr = SnapshotManager(storage_path)
snapshots = snapshot_mgr.list_snapshots(collection_name)
```

### Check deployment metadata
```python
deployment_tracker = DeploymentTracker(project_path)
metadata = deployment_tracker.read()
```

### Detect drift
```python
sync_mgr = SyncManager(storage_path, project_path)
drift_results = sync_mgr.check_drift()
```

### Create version record (Phase 2)
```python
# After implementing ArtifactVersion model
version_record = ArtifactVersion(
    artifact_id=artifact.id,
    version_tag="v1.2.0",
    version_sha=content_hash,
    snapshot_id=snapshot.id,
)
session.add(version_record)
session.commit()
```

## Testing Checklist

- [ ] Version creation on deployment
- [ ] Parent/child relationship tracking
- [ ] Version history retrieval
- [ ] Merge strategy selection
- [ ] Version graph navigation
- [ ] Rollback using version history
- [ ] Cross-project version queries
- [ ] API endpoint functionality
- [ ] Error handling for missing versions
- [ ] Performance with large version histories

## Integration Points

### With Deployment System
- VersionManager auto-creates versions on deployment
- DeploymentRecord stores initial version info
- Linked via snapshot_id

### With Sync System
- SyncManager uses version history for merge decisions
- Queries ArtifactVersion for common ancestors
- Creates new versions on successful sync

### With Rollback System
- RollbackAuditEntry references ArtifactVersion
- Preserves parent/child relationships
- Enables version tree restoration

## Next Steps

For Phase 2 implementation:
1. Review all documentation files in order
2. Understand current Phase 1 implementation
3. Create migration file for ArtifactVersion model
4. Update VersionManager to populate version records
5. Add repository methods for version queries
6. Update SyncManager to use version history
7. Add API endpoints for version management
8. Write comprehensive tests

---

**Generated by codebase-explorer agent**
**Documentation date: 2025-12-17**
