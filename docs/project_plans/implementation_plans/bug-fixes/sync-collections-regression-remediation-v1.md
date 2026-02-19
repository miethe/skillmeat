---
title: Sync + Collections Regression Remediation Implementation Plan
type: implementation_plan
status: ready
priority: critical
source_document: docs/project_plans/reports/sync-collections-regression-followup-2026-01-11.md
created: 2026-01-11
complexity: medium
estimated_effort: 8-12 hours
phases: 3
schema_version: 2
doc_type: implementation_plan
feature_slug: sync-collections-regression-remediation
prd_ref: null
---

# Sync + Collections Regression Remediation - Implementation Plan

## Executive Summary

This implementation plan addresses 5 remaining issues from the Sync + Collections regression analysis:

- **1 Critical (P0)**: Cache migrations not run at runtime - breaks groups/collections for existing users
- **2 High Priority (P1)**: Frontend collection identity issues - breaks multi-collection support
- **2 Medium Priority (P2)**: Technical debt - context sync UI and schema unification

**Total Effort**: 8-12 hours across 3 phases
**Risk Level**: High (P0 blocks collections feature entirely)
**Target Completion**: P0 immediate, P1 within 2 days, P2 within 1 week

---

## Phase 1: Critical Cache Migration Fix (P0)

**Objective**: Fix cache migrations not running at runtime, enabling groups/collections for existing users.

**Effort**: 15 minutes
**Assigned To**: python-backend-engineer (Sonnet)
**Files Modified**: 1

### Tasks

| Task ID | Description | Acceptance Criteria | Estimate |
|---------|-------------|---------------------|----------|
| P0-1.1 | Add migration call to cache initialization | - `run_migrations()` called before `create_tables()` in `initialize_cache()`<br>- Migrations run successfully on existing cache DB<br>- Groups/collections tables created via migrations | 10 min |
| P0-1.2 | Add integration test for cache migrations | - Test creates cache without migrations<br>- Test calls `initialize_cache()`<br>- Test verifies collections/groups tables exist<br>- Test passes on CI | 5 min |

### Implementation Details

#### File: `skillmeat/cache/manager.py`

**Current Code (Line 155-182)**:
```python
def initialize_cache(
    cache_dir: Optional[Path] = None,
    force_recreate: bool = False
) -> None:
    """Initialize cache database with schema."""
    db_path = get_cache_db_path(cache_dir)

    if force_recreate and db_path.exists():
        db_path.unlink()

    # Only creates base tables, doesn't run migrations
    create_tables()
```

**Required Change**:
```python
def initialize_cache(
    cache_dir: Optional[Path] = None,
    force_recreate: bool = False
) -> None:
    """Initialize cache database with schema."""
    from skillmeat.cache.migrations import run_migrations

    db_path = get_cache_db_path(cache_dir)

    if force_recreate and db_path.exists():
        db_path.unlink()

    # Run Alembic migrations first (creates/updates schema)
    run_migrations()

    # Then create any missing base tables (backward compatibility)
    create_tables()
```

**Rationale**:
- `run_migrations()` already exists in `skillmeat/cache/migrations/__init__.py:59`
- Collections and groups tables are defined in migration `20251212_1600_create_collections_schema.py`
- Without migration call, existing databases never get these tables

### Testing Requirements

**Unit Test**: `tests/cache/test_manager.py`
```python
def test_initialize_cache_runs_migrations(tmp_path):
    """Verify initialize_cache() applies Alembic migrations."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Initialize cache (should run migrations)
    initialize_cache(cache_dir)

    # Verify collections/groups tables exist
    session = get_session()
    inspector = inspect(session.bind)
    tables = inspector.get_table_names()

    assert "user_collections" in tables
    assert "artifact_collection_memberships" in tables
    assert "groups" in tables
```

**Manual Test**:
1. Create cache with old code: `skillmeat init`
2. Delete cache DB: `rm ~/.skillmeat/cache/cache.db`
3. Reinstall with new code: `pip install -e .`
4. Run CLI: `skillmeat list`
5. Verify groups/collections work: `skillmeat web dev` → test UI

### Quality Gates

- [ ] Migration call added before `create_tables()`
- [ ] Integration test passes
- [ ] Manual test confirms groups/collections work on fresh install
- [ ] No breaking changes to existing functionality
- [ ] Code review approved

### Rollout Plan

**Immediate deployment** (no feature flag needed):
- Change is backward compatible (adds functionality, doesn't remove)
- Migrations are idempotent (safe to run multiple times)
- Low risk of regression

---

## Phase 2: Frontend Collection Identity Fixes (P1)

**Objective**: Wire collection IDs through frontend, fix artifact-to-deployment matching.

**Effort**: 3-4 hours
**Assigned To**: ui-engineer (Sonnet)
**Files Modified**: 4

### Tasks

| Task ID | Description | Acceptance Criteria | Estimate |
|---------|-------------|---------------------|----------|
| P1-2.1 | Fix artifact-to-deployment matching (add type) | - Matching uses `(name, type)` tuple in `projects/[id]/page.tsx`<br>- Matching uses `(name, type)` tuple in `collection/page.tsx`<br>- Test with same-name artifacts of different types<br>- No false positives in deployment status | 30 min |
| P1-2.2 | Wire collection IDs through useEntityLifecycle | - Remove hard-coded `'default'` at line 236<br>- Accept `collection_id` parameter in hook<br>- Pass collection ID to API calls at lines 714, 727, 740<br>- Update mock data to use dynamic collection ID | 1 hour |
| P1-2.3 | Update deploy dialog to pass collection context | - Accept `collection_id` prop in `deploy-from-collection-dialog.tsx`<br>- Pass `?collection={id}` to deploy API call (line 111-119)<br>- Remove hard-coded `'default'` at line 66<br>- Dialog displays selected collection name | 1 hour |
| P1-2.4 | Add integration test for multi-collection deploy | - Test creates 2 collections<br>- Test deploys artifact from collection A<br>- Test verifies deployment linked to collection A (not default)<br>- Test deploys from collection B, verifies separate tracking | 1 hour |

### Implementation Details

#### Task P1-2.1: Fix Artifact Matching

**File**: `skillmeat/web/app/projects/[id]/page.tsx` (Lines 136-166)

**Current Code**:
```typescript
const artifactWithStatus = artifacts.map(artifact => {
  const deployedArtifact = deployedArtifacts.find(
    d => d.artifact_name === artifact.name
  );
  // ...
});
```

**Required Change**:
```typescript
const artifactWithStatus = artifacts.map(artifact => {
  const deployedArtifact = deployedArtifacts.find(
    d => d.artifact_name === artifact.name && d.artifact_type === artifact.type
  );
  // ...
});
```

**File**: `skillmeat/web/app/collection/page.tsx` (Lines 39-84)

**Current Code**:
```typescript
const matchingDeployment = deploymentSummaries.find(
  summary => a.name === summary.name
);
```

**Required Change**:
```typescript
const matchingDeployment = deploymentSummaries.find(
  summary => a.name === summary.name && a.type === summary.artifact_type
);
```

#### Task P1-2.2: Wire Collection IDs (useEntityLifecycle)

**File**: `skillmeat/web/hooks/useEntityLifecycle.tsx` (Line 236, 714-740)

**Current Code**:
```typescript
// Line 236
const entity = {
  collection: 'default',
  // ...
};

// Lines 714, 727, 740 (mock data)
collection: 'default'
```

**Required Change**:
```typescript
// Add parameter to hook
export function useEntityLifecycle(collection_id?: string) {
  const effectiveCollection = collection_id || 'default';

  // Line 236
  const entity = {
    collection: effectiveCollection,
    // ...
  };

  // Update API calls to include collection param
  const response = await fetch(`/api/v1/artifacts?collection=${effectiveCollection}`);
}
```

#### Task P1-2.3: Deploy Dialog Collection Context

**File**: `skillmeat/web/app/projects/[id]/manage/components/deploy-from-collection-dialog.tsx` (Lines 66, 111-119)

**Current Code**:
```typescript
// Line 66
const collectionId = 'default';

// Line 111-119
const response = await fetch('/api/v1/deploy', {
  method: 'POST',
  body: JSON.stringify({
    artifact_name: selectedArtifact.name,
    project_path: projectPath,
  }),
});
```

**Required Change**:
```typescript
// Add prop to component
interface DeployFromCollectionDialogProps {
  collection_id: string;
  // ...
}

// Use prop instead of hard-coded value
const { collection_id, ... } = props;

// Pass collection to API
const response = await fetch('/api/v1/deploy', {
  method: 'POST',
  body: JSON.stringify({
    artifact_name: selectedArtifact.name,
    project_path: projectPath,
    collection: collection_id,
  }),
});
```

### Testing Requirements

**Integration Test**: `tests/web/integration/test_multi_collection_deploy.spec.ts`
```typescript
test('deploys artifact from specific collection', async ({ page }) => {
  // Setup: Create 2 collections
  const collectionA = await createCollection({ name: 'Collection A' });
  const collectionB = await createCollection({ name: 'Collection B' });

  // Add same artifact to both collections
  await addArtifact(collectionA.id, { name: 'test-skill', type: 'skill' });
  await addArtifact(collectionB.id, { name: 'test-skill', type: 'skill' });

  // Deploy from collection A
  await page.goto(`/projects/test-project/manage`);
  await page.click('[data-testid="deploy-from-collection"]');
  await page.selectOption('[data-testid="collection-select"]', collectionA.id);
  await page.click('[data-testid="artifact-test-skill"]');
  await page.click('[data-testid="deploy-button"]');

  // Verify deployment linked to collection A
  const deployment = await getDeployment('test-skill', 'skill');
  expect(deployment.collection_id).toBe(collectionA.id);
});
```

**Manual Test**:
1. Create 2 collections in UI
2. Add artifact "test-skill" (type: skill) to both collections
3. Add command "test-skill" (type: command) to collection A (same name, different type)
4. Deploy from collection A → verify correct artifact deployed
5. Check deployment status → verify no false positives

### Quality Gates

- [ ] All 4 tasks completed
- [ ] Integration test passes
- [ ] Manual test confirms multi-collection deploy works
- [ ] No hard-coded `'default'` references remain
- [ ] Artifact matching includes type check
- [ ] Code review approved

---

## Phase 3: Technical Debt Resolution (P2)

**Objective**: Add preview badge to context sync UI, unify deployment metadata schema.

**Effort**: 3-4 hours
**Assigned To**:
- ui-engineer (Sonnet) for P2-3.1
- python-backend-engineer (Sonnet) for P2-3.2

**Files Modified**: 2

### Tasks

| Task ID | Description | Acceptance Criteria | Estimate |
|---------|-------------|---------------------|----------|
| P2-3.1 | Add preview badge to context sync UI | - Badge displays "Preview" or "Beta" near context sync status<br>- Badge has tooltip explaining feature is incomplete<br>- Badge links to documentation/GitHub issue<br>- Visual design matches app theme | 30 min |
| P2-3.2 | Migrate sync.py to unified Deployment class | - `sync.py` uses `DeploymentTracker` from `storage/deployment.py`<br>- `_load_deployment_metadata()` reads via `DeploymentTracker`<br>- `_save_deployment_metadata()` writes via `DeploymentTracker`<br>- Old schema migration path tested (backward compatibility)<br>- No breaking changes to sync functionality | 3 hours |

### Implementation Details

#### Task P2-3.1: Preview Badge

**File**: `skillmeat/web/components/entity/context-sync-status.tsx`

**Current Code**:
```typescript
export function ContextSyncStatus({ entity }: Props) {
  return (
    <div className="context-sync-status">
      <Badge variant={statusVariant}>{statusText}</Badge>
    </div>
  );
}
```

**Required Change**:
```typescript
export function ContextSyncStatus({ entity }: Props) {
  return (
    <div className="context-sync-status">
      <div className="flex items-center gap-2">
        <Badge variant={statusVariant}>{statusText}</Badge>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              <Badge variant="outline" className="text-xs">
                Preview
              </Badge>
            </TooltipTrigger>
            <TooltipContent>
              Context sync detection works, but pull/push/resolve are not yet implemented.
              <a href="https://github.com/user/repo/issues/123" className="underline">
                Track progress
              </a>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>
  );
}
```

**Design Notes**:
- Use `variant="outline"` for subtle appearance
- Position badge inline with status badge
- Tooltip provides context without cluttering UI
- Link to GitHub issue for transparency

#### Task P2-3.2: Unify Deployment Schema

**File**: `skillmeat/core/sync.py` (Lines 320-420)

**Current Code**:
```python
def _load_deployment_metadata(self, project_path: Path) -> Dict[str, Any]:
    """Load deployment metadata from project .claude directory."""
    metadata_file = project_path / ".claude" / "deployment.toml"
    if not metadata_file.exists():
        return {}

    import tomllib
    with open(metadata_file, "rb") as f:
        data = tomllib.load(f)

    # Old schema: [deployment] + [[artifacts]]
    return data

def _save_deployment_metadata(self, project_path: Path, metadata: Dict[str, Any]) -> None:
    """Save deployment metadata to project .claude directory."""
    metadata_file = project_path / ".claude" / "deployment.toml"
    metadata_file.parent.mkdir(parents=True, exist_ok=True)

    import tomli_w
    with open(metadata_file, "wb") as f:
        tomli_w.dump(metadata, f)
```

**Required Change**:
```python
from skillmeat.storage.deployment import DeploymentTracker

def _load_deployment_metadata(self, project_path: Path) -> List[Deployment]:
    """Load deployment metadata using unified tracker."""
    tracker = DeploymentTracker(project_path)
    deployments = tracker.list_deployments()
    return deployments

def _save_deployment_metadata(
    self,
    project_path: Path,
    deployments: List[Deployment]
) -> None:
    """Save deployment metadata using unified tracker."""
    tracker = DeploymentTracker(project_path)

    # Clear existing deployments
    existing = tracker.list_deployments()
    for deployment in existing:
        tracker.remove_deployment(deployment.artifact_name, deployment.artifact_type)

    # Add new deployments
    for deployment in deployments:
        tracker.add_deployment(deployment)
```

**Migration Strategy**:
1. `DeploymentTracker.__init__()` already handles backward compatibility (reads old schema)
2. First save operation will write new schema
3. No data loss - old TOML files remain readable
4. Gradual migration as sync operations occur

**Testing**:
```python
def test_sync_uses_unified_schema(tmp_path):
    """Verify sync.py uses DeploymentTracker for metadata."""
    project_path = tmp_path / "project"
    project_path.mkdir()

    # Create old-format deployment.toml
    old_metadata = {
        "deployment": {"project_path": str(project_path)},
        "artifacts": [
            {"name": "test-skill", "type": "skill", "version": "1.0.0"}
        ]
    }
    deployment_file = project_path / ".claude" / "deployment.toml"
    deployment_file.parent.mkdir(parents=True)
    with open(deployment_file, "wb") as f:
        tomli_w.dump(old_metadata, f)

    # Load via sync.py (should read old format)
    sync = SyncService()
    deployments = sync._load_deployment_metadata(project_path)
    assert len(deployments) == 1
    assert deployments[0].artifact_name == "test-skill"

    # Save via sync.py (should write new format)
    sync._save_deployment_metadata(project_path, deployments)

    # Verify new format
    with open(deployment_file, "rb") as f:
        import tomllib
        data = tomllib.load(f)
    assert "deployed" in data  # New schema key
    assert "deployment" not in data  # Old schema key gone
```

### Testing Requirements

**Manual Test (P2-3.1)**:
1. Open web UI → navigate to collection page
2. Verify preview badge appears next to sync status
3. Hover over badge → verify tooltip content
4. Click tooltip link → verify GitHub issue opens

**Integration Test (P2-3.2)**:
```python
def test_sync_backward_compatibility(tmp_path):
    """Verify sync.py reads old deployment format and writes new format."""
    # Test scenario above
```

### Quality Gates

- [ ] Preview badge visible in UI
- [ ] Tooltip provides clear explanation
- [ ] sync.py uses DeploymentTracker
- [ ] Backward compatibility verified
- [ ] Integration test passes
- [ ] Code review approved

---

## Risk Assessment

### Phase 1 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Migration fails on existing DB | Low | High | Alembic handles failures gracefully; migration is idempotent |
| Breaking change to cache init | Low | High | Change is additive (adds migration call, doesn't remove create_tables) |
| Performance impact | Low | Low | Migrations run once per cache initialization (rare operation) |

### Phase 2 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing deploy flows | Medium | Medium | Backward compatibility: default to 'default' collection if not specified |
| Type mismatch in artifact matching | Low | Medium | Test with multi-type artifacts; add type validation |
| Collection ID not passed correctly | Medium | Medium | Integration test verifies end-to-end flow |

### Phase 3 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Schema migration breaks sync | Low | High | DeploymentTracker already handles backward compatibility |
| Preview badge confuses users | Low | Low | Tooltip explains feature status clearly |
| Data loss during migration | Very Low | High | Old files remain readable; no destructive operations |

---

## Dependencies

### Phase 1 Dependencies
- **External**: None
- **Internal**: Alembic migration system (already implemented)

### Phase 2 Dependencies
- **External**: None
- **Internal**:
  - Backend API collection parameter support (already implemented)
  - `DeploymentTracker` tuple matching (already implemented)

### Phase 3 Dependencies
- **External**: None
- **Internal**:
  - `DeploymentTracker` class (already implemented)
  - UI tooltip components (already available)

---

## Rollout Strategy

### Phase 1: Immediate Deployment
- **Target**: Next patch release (v0.3.1)
- **Feature Flag**: Not needed (backward compatible)
- **Rollback**: Revert single line change if issues arise

### Phase 2: Gradual Rollout
- **Target**: Within 2 days of Phase 1
- **Feature Flag**: Optional (`ENABLE_MULTI_COLLECTION_DEPLOY`)
- **Rollback**: Feature flag disable, fallback to 'default' collection

### Phase 3: Low-Priority Deployment
- **Target**: Within 1 week of Phase 2
- **Feature Flag**: Not needed (UI badge is cosmetic, backend is backward compatible)
- **Rollback**: Easy (revert UI badge, revert sync.py changes independently)

---

## Success Metrics

### Phase 1
- [ ] Zero failures in cache initialization on existing databases
- [ ] Groups/collections tables exist after initialization
- [ ] No increase in cache initialization time (< 50ms overhead)

### Phase 2
- [ ] Multi-collection deploy works in UI
- [ ] No artifact matching false positives (same name, different type)
- [ ] Collection ID passed correctly in 100% of deploy operations

### Phase 3
- [ ] Preview badge visible to 100% of users
- [ ] Zero schema migration failures
- [ ] Sync operations continue working with new schema

---

## Post-Implementation Validation

### Phase 1 Validation
1. **Fresh Install**: Create new cache → verify migrations run
2. **Existing Install**: Upgrade existing cache → verify migrations run
3. **Collections Feature**: Test groups/collections UI → verify tables accessible

### Phase 2 Validation
1. **Single Collection**: Deploy from default collection → verify works
2. **Multi Collection**: Deploy from collection A, then collection B → verify separate tracking
3. **Same Name Artifacts**: Deploy skill "test" and command "test" → verify no collision

### Phase 3 Validation
1. **Preview Badge**: Check UI → verify badge appears with tooltip
2. **Schema Migration**: Sync project with old schema → verify reads correctly
3. **Schema Write**: Perform sync operation → verify writes new schema

---

## Appendix: File Reference

### Phase 1 Files
- `skillmeat/cache/manager.py` (1 line change)
- `skillmeat/cache/migrations/__init__.py` (reference only)
- `tests/cache/test_manager.py` (new test)

### Phase 2 Files
- `skillmeat/web/app/projects/[id]/page.tsx` (~5 lines)
- `skillmeat/web/app/collection/page.tsx` (~3 lines)
- `skillmeat/web/hooks/useEntityLifecycle.tsx` (~10 lines)
- `skillmeat/web/app/projects/[id]/manage/components/deploy-from-collection-dialog.tsx` (~15 lines)
- `tests/web/integration/test_multi_collection_deploy.spec.ts` (new test)

### Phase 3 Files
- `skillmeat/web/components/entity/context-sync-status.tsx` (~20 lines)
- `skillmeat/core/sync.py` (~40 lines refactor)
- `tests/core/test_sync_schema_migration.py` (new test)

---

## Estimated Timeline

| Phase | Task | Effort | Cumulative |
|-------|------|--------|------------|
| **Phase 1** | Cache migration fix | 15 min | 15 min |
| | Testing | 15 min | 30 min |
| **Phase 2** | Artifact matching fix | 30 min | 1 hour |
| | Wire collection IDs (hook) | 1 hour | 2 hours |
| | Wire collection IDs (dialog) | 1 hour | 3 hours |
| | Integration test | 1 hour | 4 hours |
| **Phase 3** | Preview badge | 30 min | 4.5 hours |
| | Schema unification | 3 hours | 7.5 hours |
| | Testing | 1 hour | 8.5 hours |
| **Total** | | **8.5 hours** | |

**Buffer**: Add 50% for unforeseen issues → **12-13 hours total**

---

## Conclusion

This implementation plan systematically addresses all 5 remaining regression findings:

1. **Phase 1 (P0)**: Fixes critical cache migration bug (15 min)
2. **Phase 2 (P1)**: Enables multi-collection support (4 hours)
3. **Phase 3 (P2)**: Resolves technical debt (4 hours)

All phases are well-scoped, testable, and backward compatible. The plan prioritizes critical fixes while allowing lower-priority tasks to be deferred if needed.
