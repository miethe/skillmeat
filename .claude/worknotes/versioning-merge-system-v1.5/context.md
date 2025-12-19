---
type: worknotes
prd: versioning-merge-system-v1.5
created: 2025-12-17
updated: 2025-12-17
---

# Versioning Merge System v1.5: Context Notes

## PRD Overview

**PRD**: `docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.5-state-tracking.md`

**Goal**: Fix three-way merge algorithm and add comprehensive version lineage tracking with change attribution.

**Key Problem**: Three-way merge currently defaults to empty baseline, causing false conflicts. Root cause: baseline not stored during deployment.

**Solution**: Store baseline hash in deployment metadata, build complete version chain with parent-child relationships, and implement change attribution logic.

---

## Architecture Summary

### Data Model Changes

**Deployment Metadata** (Phase 1):
- Add `merge_base_snapshot` field (content hash of deployed artifact)
- Becomes baseline for future three-way merges

**ArtifactVersion Model** (Phase 2):
- Add `change_origin` enum: 'deployment', 'sync', 'local_modification'
- Add `parent_hash` field (links to previous version)
- Add `version_lineage` array (all ancestor hashes)
- Add `modification_detected_at` timestamp (Phase 3)

**Database Indexes** (Phase 2):
- Index on `content_hash` (snapshot lookups)
- Index on `parent_hash` (parent chain queries)
- Composite index on `(artifact_id, created_at)` (timeline queries)

### Version Chain Building

**Deployment** (root version):
```python
ArtifactVersion(
    content_hash=hash(artifact),
    parent_hash=None,  # No parent (root)
    change_origin='deployment',
    version_lineage=[hash(artifact)]
)
```

**Sync** (extends chain):
```python
ArtifactVersion(
    content_hash=new_hash,
    parent_hash=current_hash,  # Previous deployed version
    change_origin='sync',
    version_lineage=parent.version_lineage + [new_hash]
)
```

**Local Modification** (branches from deployed):
```python
ArtifactVersion(
    content_hash=local_hash,
    parent_hash=deployed_hash,
    change_origin='local_modification',
    version_lineage=deployed.version_lineage + [local_hash]
)
```

### Change Attribution Algorithm

**determine_change_origin(baseline, deployed, upstream)**:

| Baseline | Deployed | Upstream | Change Origin |
|----------|----------|----------|---------------|
| Same     | Same     | Same     | 'none'        |
| Same     | Same     | Different| 'upstream'    |
| Same     | Different| Same     | 'local'       |
| Different| Different| Different| 'both' (conflict) |

**Implementation**:
1. Compare hashes first (fast)
2. If hashes differ, compare content (slower)
3. Return change origin based on comparison matrix

---

## Key Implementation Decisions

### Phase 1: Baseline Storage

**Decision**: Store baseline hash in deployment metadata (not separate table)
**Reasoning**: Deployment metadata already exists, no schema migration needed (just add field)
**Fallback**: For old deployments without baseline, search for common ancestor in version chain

### Phase 2: Version Lineage Array

**Decision**: Store lineage as array (not just parent pointer)
**Reasoning**: Avoids recursive queries to build full lineage, faster common ancestor search
**Trade-off**: Array grows with chain length, but limited by PostgreSQL array size (should be fine for <10,000 versions)

### Phase 3: Modification Timestamp

**Decision**: Set `modification_detected_at` on first drift detection (not on actual modification)
**Reasoning**: System can't detect exact moment of modification, only when drift detected
**Implication**: Timestamp is approximate (when system noticed, not when user changed)

### Phase 4: Change Origin Calculation

**Decision**: Calculate change origin on-demand (not pre-computed)
**Reasoning**: Requires baseline, deployed, and upstream content - only available during sync
**Trade-off**: Slightly slower API responses, but more accurate and easier to debug

### Phase 5: UI Design

**Decision**: Use color-coded badges (not icons)
**Reasoning**: Colors are universally understood (red=error, amber=warning, blue=info)
**Accessibility**: Tooltips provide text explanation for colorblind users

---

## Technical Patterns

### Hash Computation

All content hashing uses SHA-256 for consistency:
```python
def compute_hash(artifact: Artifact) -> str:
    """Compute SHA-256 hash of artifact content."""
    content = serialize_artifact(artifact)
    return hashlib.sha256(content.encode('utf-8')).hexdigest()
```

### Version Chain Traversal

Walk parent chain to find common ancestor:
```python
def find_common_ancestor(v1: Version, v2: Version) -> Optional[Version]:
    """Find most recent common ancestor of two versions."""
    v1_lineage = set(v1.version_lineage)
    v2_lineage = v2.version_lineage

    # Walk v2 lineage from newest to oldest
    for hash in reversed(v2_lineage):
        if hash in v1_lineage:
            return get_version_by_hash(hash)

    return None
```

### Three-Way Merge

Using stored baseline:
```python
def three_way_merge(artifact_id: str, upstream: Artifact) -> MergeResult:
    """Perform three-way merge using stored baseline."""
    deployment = get_deployment(artifact_id)
    baseline_hash = deployment.merge_base_snapshot

    if not baseline_hash:
        # Old deployment (v1.0): use fallback
        baseline_hash = find_common_ancestor_hash(artifact_id)
        logger.warning(f"No baseline stored, using fallback: {baseline_hash}")

    baseline = get_snapshot(baseline_hash)
    deployed = get_deployed_artifact(artifact_id)

    return merge(baseline, deployed, upstream)
```

---

## Gotchas & Learnings

### 1. Baseline vs Parent Hash

**Gotcha**: Baseline (merge base) is NOT the same as parent hash
- **Baseline**: Snapshot at deployment time (for three-way merge)
- **Parent**: Previous version in chain (for lineage tracking)

**Example**:
```
Deploy v1.0 → baseline=v1.0, parent=NULL
Sync v1.1   → baseline=v1.0 (still), parent=v1.0
Sync v1.2   → baseline=v1.1 (updated on sync), parent=v1.1
```

### 2. Local Modification Detection Timing

**Gotcha**: `modification_detected_at` is set when drift detected, not when user modifies
- User modifies at 10:00 AM
- System detects drift at 10:05 AM
- `modification_detected_at` = 10:05 AM (not 10:00 AM)

**Implication**: Timestamp is approximate, use for "first noticed" not "exact time"

### 3. Version Lineage for Branches

**Gotcha**: Local modifications create a "branch" in version chain
- Deployed version has lineage: [v1.0, v1.1]
- Local mod has lineage: [v1.0, v1.1, local_hash]
- Next sync creates conflict (both branches diverged from v1.1)

**Handling**: Change attribution detects divergence, flags as 'both' (conflict)

### 4. Empty Baseline Fallback

**Gotcha**: Old deployments (v1.0) don't have baseline stored
- System falls back to common ancestor search
- If no common ancestor found, uses empty baseline (same as v1.0 behavior)
- Warning logged to alert user

**Mitigation**: Gradual migration - next sync after upgrade stores baseline

### 5. Performance with Large Chains

**Gotcha**: Version lineage array grows with chain length
- 100 versions → array of 100 hashes
- 1000 versions → array of 1000 hashes (still manageable)
- 10,000+ versions → may hit PostgreSQL limits

**Mitigation**:
- Indexes on parent_hash for efficient traversal
- Cache parent lineage (don't re-walk chain)
- Consider pruning old versions (future enhancement)

---

## Integration Points

### Backend → Frontend

**API Changes** (Phase 4):
- `GET /api/v1/sync/drift` returns:
  - `change_origin` per file ('upstream', 'local', 'both', 'none')
  - `summary` counts (upstream_changes, local_changes, conflicts)
  - `baseline_hash`, `current_hash` for debugging

**Frontend Consumption** (Phase 5):
- `DriftViewer` component displays `ChangeBadge` based on `change_origin`
- `VersionTimeline` component shows change origin labels
- Tooltips explain badge meanings

### Database → Application

**Schema Changes** (Phase 2):
- Alembic migration adds `change_origin` enum
- SQLAlchemy model updated with new field
- Application code populates field on version creation

**Query Patterns**:
- Snapshot lookup: `SELECT * FROM artifact_versions WHERE content_hash = ?` (indexed)
- Parent chain: `SELECT * FROM artifact_versions WHERE parent_hash = ?` (indexed)
- Timeline: `SELECT * FROM artifact_versions WHERE artifact_id = ? ORDER BY created_at DESC` (composite index)

---

## Testing Strategy

### Unit Tests

**Phase 1** (Baseline Storage):
- Deploy artifact → baseline stored
- Retrieve baseline from metadata
- Fallback for old deployments

**Phase 2** (Version Lineage):
- Deploy → parent=NULL, origin='deployment'
- Sync → parent=previous, origin='sync'
- Local mod → parent=previous, origin='local_modification'
- Lineage builds correctly (3+ versions)

**Phase 3-4** (Modification Tracking & Attribution):
- Timestamp set on first drift
- Change origin calculated correctly (all 4 scenarios)
- Summary counts accurate

**Phase 5** (UI):
- Badges render correctly
- Tooltips show on hover
- Responsive design

### Integration Tests

**Deploy→Sync→Drift→Merge** (TASK-6.1):
- Happy path (no conflicts)
- Upstream-only changes
- Multiple syncs (chain building)

**Deploy→Modify→Sync→Conflict** (TASK-6.2):
- Local-only changes
- Conflict (both changed)
- Local mod version record created

**Migration** (TASK-6.4):
- Old deployment (no baseline) → fallback works
- Mixed deployments (old + new) → both work
- Gradual migration (automatic upgrade)

### Performance Tests

**Version Chain Queries** (TASK-6.3):
- Find common ancestor: <50ms (50 versions)
- Build lineage: <100ms (100 versions)
- Drift detection: <200ms (50 versions)

**Load Testing** (TASK-6.6):
- Create large chain: <10s (100 versions)
- Query latest: <50ms (100 versions)
- API response: <500ms (100 versions)

---

## Files Changed by Phase

### Phase 1: Core Baseline Support
- `skillmeat/storage/deployment.py` - Add merge_base_snapshot field, store baseline
- `skillmeat/core/deployment.py` - Compute baseline hash on deploy
- `skillmeat/core/sync.py` - Retrieve baseline from metadata, fallback logic
- `tests/test_three_way_merge.py` - Test merge with baseline
- `tests/test_deployment_baseline.py` - Test baseline storage/retrieval

### Phase 2: Version Lineage Tracking
- `alembic/versions/XXX_add_change_origin.py` - Database migration
- `skillmeat/storage/models.py` - Update ArtifactVersion model
- `skillmeat/storage/deployment.py` - Populate parent_hash on deployment
- `skillmeat/core/sync.py` - Populate parent_hash on sync
- `skillmeat/storage/snapshot.py` - Build version_lineage array
- `tests/test_version_lineage.py` - Test version chain creation

### Phase 3-4: Modification Tracking & Change Attribution
- `skillmeat/core/sync.py` - Set modification_detected_at, determine_change_origin()
- `skillmeat/storage/snapshot.py` - Create version for local mods
- `skillmeat/api/app/schemas/drift.py` - Update schema with attribution fields
- `skillmeat/api/app/routers/sync.py` - Return change_origin in API
- `tests/test_modification_tracking.py` - Test mod timestamp
- `tests/test_change_attribution.py` - Test change origin scenarios

### Phase 5: Web UI Integration
- `skillmeat/web/types/sync.ts` - Update TypeScript types
- `skillmeat/web/types/drift.ts` - Add change_origin field
- `skillmeat/web/components/sync/ChangeBadge.tsx` - Create badge component
- `skillmeat/web/components/sync/DiffViewer.tsx` - Add badges to diff viewer
- `skillmeat/web/components/sync/VersionTimeline.tsx` - Add change origin labels
- `skillmeat/web/__tests__/components/sync/ChangeBadge.test.tsx` - Test badges

### Phase 6: Testing & Validation
- `tests/integration/test_version_workflow.py` - Integration tests (deploy→sync)
- `tests/integration/test_conflict_workflow.py` - Integration tests (conflicts)
- `tests/performance/test_version_chain_performance.py` - Performance benchmarks
- `tests/integration/test_migration_v1_0.py` - Migration tests
- `tests/performance/test_large_version_chains.py` - Load testing
- `docs/api/versioning.md` - API documentation
- `docs/guides/sync-and-merge.md` - User guide
- `CHANGELOG.md` - Release notes

---

## Next Steps

**Immediate**:
1. Review progress tracking files with team
2. Confirm phase breakdown and task assignments
3. Identify any missing tasks or risks

**Phase 1 Kickoff**:
1. Create feature branch: `feat/versioning-merge-system-v1.5`
2. Start with TASK-1.1 (schema change)
3. All Phase 1 tasks can run in parallel (no dependencies)

**Dependencies**:
- Phase 1 blocks Phase 2 (needs baseline storage working)
- Phase 2 blocks Phase 3-4 (needs version lineage)
- Phase 4 blocks Phase 5 (API must return change_origin)
- Phases 1-5 block Phase 6 (testing requires complete implementation)

**Estimated Timeline**:
- Phase 1: 2-3 days
- Phase 2: 1-2 days
- Phase 3-4: 2-3 days
- Phase 5: 2 days
- Phase 6: 2-3 days
- **Total**: 9-13 days (2-3 weeks)

---

## Open Questions

1. **Version Chain Pruning**: Should old versions be pruned after N versions? (Future enhancement)
2. **Conflict Resolution UI**: Should we add a merge editor in the UI? (Out of scope for v1.5)
3. **Binary File Handling**: How to diff binary files for change attribution? (Edge case, defer)
4. **Performance at Scale**: What's the max version chain length before performance degrades? (Test in Phase 6)

---

## References

- **PRD**: `docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.5-state-tracking.md`
- **Progress Tracking**: `.claude/progress/versioning-merge-system-v1.5/phase-*-progress.md`
- **Related Systems**:
  - Sync System: `skillmeat/core/sync.py`
  - Deployment System: `skillmeat/storage/deployment.py`
  - Version History: `skillmeat/storage/snapshot.py`
