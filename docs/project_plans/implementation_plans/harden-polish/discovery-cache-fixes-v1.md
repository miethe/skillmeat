---
title: 'Bug Fix Plan: Discovery Cache & Invalidation Fixes'
description: Implementation plan for fixing stale discovery count display and over-broad
  cache invalidation in SkillMeat web UI
audience:
- ai-agents
- developers
tags:
- bug-fix
- implementation-plan
- harden-polish
- caching
- discovery
- frontend
created: 2025-12-03
updated: 2025-12-03
category: harden-polish
status: done
schema_version: 2
doc_type: implementation_plan
feature_slug: discovery-cache-fixes
prd_ref: null
---

# Bug Fix Plan: Discovery Cache & Invalidation Fixes

**Type:** Critical Bug Fixes
**Complexity Level:** Medium (M)
**Total Estimated Effort:** 16-20 story points
**Target Timeline:** 1 week
**Priority:** High (affects user-visible accuracy)

---

## Executive Summary

Two interconnected caching issues impact user experience in the SkillMeat discovery feature:

1. **Discovery Banner Shows Stale Count**: After importing artifacts, the discovery banner still shows the original count instead of the remaining unimported artifacts.
2. **Overly Broad Cache Invalidation**: When importing artifacts to one project, ALL projects get invalidated, causing slow page reloads.

Both issues stem from race conditions and incomplete invalidation strategies. The fixes involve:
- Backend filtering of already-imported artifacts
- Correcting async/await patterns in cache invalidation
- Implementing granular query key invalidation instead of broad key patterns

---

## Bug 1: Discovery Banner Shows Stale Count

### Problem Statement

After importing 6 of 13 discovered artifacts, the discovery banner still displays "Found 13 Artifacts" instead of "Found 7 Artifacts". This misleads users about how many unimported artifacts remain.

### Root Cause Analysis

**Backend Issue (Primary)**
- File: `skillmeat/core/discovery.py:233-238`
- The `discover_artifacts()` method returns ALL artifacts in `.claude/` directory without filtering against the collection's already-imported artifacts
- No awareness of which artifacts are already in the manifest

**Frontend Issue (Secondary Race Condition)**
- File: `skillmeat/web/hooks/useProjectDiscovery.ts:57-65`
- File: `skillmeat/web/app/projects/[id]/page.tsx:185`
- Cache invalidation uses `invalidateQueries()` without awaiting
- Component re-renders with stale cached data before backend returns fresh results
- 5-minute `staleTime` keeps old data marked as "fresh"

### Affected Files

```
skillmeat/core/discovery.py              - discover_artifacts() method
skillmeat/api/routers/artifacts.py       - /discover endpoint, no collection awareness
skillmeat/web/hooks/useProjectDiscovery.ts - invalidation not awaited
skillmeat/web/app/projects/[id]/page.tsx   - refetch not awaited
```

### Fix Strategy

**Option A (Recommended): Backend Filtering**
- Modify `discover_artifacts()` to accept a manifest parameter
- Filter returned artifacts against already-imported sources
- Return `discovered_count` vs `importable_count` separately
- Update API endpoint to calculate the difference

**Option B (Frontend Filter)**
- Frontend compares discovered artifacts against loaded collection state
- Less efficient, requires collection data fetch first

**Implementation: Pursue Option A + Frontend Race Condition Fix**

---

## Bug 2: Cache Invalidation Invalidates All Projects

### Problem Statement

After importing artifacts to Project A, navigating to Project B shows a slow reload and re-scans. This indicates the cache key `['projects', 'list']` was invalidated globally instead of just invalidating Project A's cache.

### Root Cause Analysis

**Frontend Query Key Design Issue**
- File: `skillmeat/web/hooks/useProjectDiscovery.ts:63`
- File: `skillmeat/web/hooks/useCacheRefresh.ts:65`
- File: `skillmeat/web/hooks/useDeploy.ts:75`
- Uses: `queryClient.invalidateQueries({ queryKey: ['projects', 'list'] })`
- This invalidates ALL queries with keys starting with `['projects', 'list']`
- Results in unnecessary re-fetches for unrelated projects

**Backend Already Supports Targeted Invalidation**
- `POST /cache/invalidate` accepts optional `project_id` parameter
- `POST /cache/refresh` accepts optional `project_id` parameter
- Not being utilized from frontend

**React Query Key Structure**
- Current: `['projects', 'list']` → affects all projects
- Optimal: `['projects', 'detail', projectId]` → affects specific project

### Affected Files

```
skillmeat/web/hooks/useProjectDiscovery.ts  - invalidates entire list
skillmeat/web/hooks/useCacheRefresh.ts      - uses root ['projects'] key
skillmeat/web/hooks/useDeploy.ts            - same pattern
skillmeat/api/routers/cache.py              - already supports project_id filtering
```

### Fix Strategy

1. Update `useCacheRefresh` hook to accept optional `projectId` parameter
2. Change invalidation to use specific project key: `['projects', 'detail', projectId]`
3. Pass `projectId` to `/cache/invalidate` endpoint when available
4. Update all call sites to provide `projectId` in deployment context

---

## Tasks

### Task 1: Backend Discovery Filtering (BUG1-001)

**Assigned To:** `python-backend-engineer`
**Story Points:** 5
**Dependencies:** None
**Estimated Time:** 2-3 hours

**Description:**
Modify `skillmeat/core/discovery.py` to filter discovered artifacts against already-imported artifacts in the manifest.

**Acceptance Criteria:**
- ✓ `discover_artifacts()` accepts optional manifest/collection parameter
- ✓ Filters artifacts: returns only those NOT in manifest
- ✓ Returns both `discovered_count` (all artifacts) and `importable_count` (unimported)
- ✓ No artifacts imported during discovery run
- ✓ Unit tests verify filtering logic (>80% coverage)
- ✓ Performance remains <2s for 50+ artifacts

**Files to Modify:**
- `skillmeat/core/discovery.py` - Add filtering logic to `discover_artifacts()`

**Code Changes:**
```python
# Current (line 233-238)
def discover_artifacts(self) -> DiscoveryResult:
    """Scan .claude/artifacts/ directory"""
    # Returns ALL artifacts

# Modified
def discover_artifacts(self, manifest: Optional[Manifest] = None) -> DiscoveryResult:
    """Scan .claude/artifacts/ directory, optionally filtering imported artifacts"""
    all_artifacts = [...]  # Scan logic unchanged

    if manifest:
        imported_sources = {artifact.source for artifact in manifest.artifacts}
        importable = [a for a in all_artifacts if a.source not in imported_sources]
    else:
        importable = all_artifacts

    return DiscoveryResult(
        discovered_count=len(all_artifacts),
        importable_count=len(importable),
        artifacts=importable,
        # ...
    )
```

**Related Schemas to Update:**
- `DiscoveryResult` - add `importable_count` field

---

### Task 2: API Endpoint Update (BUG1-002)

**Assigned To:** `python-backend-engineer`
**Story Points:** 3
**Dependencies:** BUG1-001
**Estimated Time:** 1-2 hours

**Description:**
Update the `/discover` endpoint to pass manifest to discovery service and return filtered results.

**Acceptance Criteria:**
- ✓ `POST /api/v1/artifacts/discover` passes collection/manifest to service
- ✓ Response includes both `discovered_count` and `importable_count`
- ✓ Endpoint properly handles missing manifest gracefully
- ✓ Integration tests verify filtered results
- ✓ Status codes correct (200, 400, 401, 500)

**Files to Modify:**
- `skillmeat/api/routers/artifacts.py` - Update discover endpoint

**Code Changes:**
```python
@router.post("/discover", response_model=DiscoveryResult)
async def discover_artifacts(
    request: DiscoveryRequest,
    artifact_mgr: ArtifactManagerDep,
) -> DiscoveryResult:
    """
    Scan .claude/ directory for artifacts not yet in collection.

    Returns both discovered_count (all artifacts found) and importable_count
    (artifacts not yet imported).
    """
    service = ArtifactDiscoveryService(artifact_mgr.collection_path)
    manifest = artifact_mgr.load_manifest()  # Load existing manifest
    result = service.discover_artifacts(manifest=manifest)
    return result
```

---

### Task 3: Frontend Cache Invalidation Fix (BUG2-001)

**Assigned To:** `ui-engineer`
**Story Points:** 4
**Dependencies:** None
**Estimated Time:** 2-3 hours

**Description:**
Fix async/await race condition in discovery invalidation and implement granular query key invalidation for projects.

**Acceptance Criteria:**
- ✓ `invalidateQueries()` is awaited before component re-renders
- ✓ `refetchQueries()` is awaited where used
- ✓ Cache invalidation only affects target project
- ✓ No unnecessary re-fetches of unrelated projects
- ✓ Tests verify async behavior

**Files to Modify:**
- `skillmeat/web/hooks/useProjectDiscovery.ts`
- `skillmeat/web/hooks/useCacheRefresh.ts`
- `skillmeat/web/hooks/useDeploy.ts`
- `skillmeat/web/app/projects/[id]/page.tsx`

**Code Changes:**

**Before (useProjectDiscovery.ts:57-65):**
```typescript
const bulkImportMutation = useMutation({
  mutationFn: async (request: BulkImportRequest) => {
    const res = await api.post("/artifacts/discover/import", request);
    return res.data;
  },
  onSuccess: () => {
    // WRONG: Not awaited, re-render happens immediately with stale data
    queryClient.invalidateQueries({ queryKey: ['artifacts'] });
  },
});
```

**After:**
```typescript
const bulkImportMutation = useMutation({
  mutationFn: async (request: BulkImportRequest) => {
    const res = await api.post("/artifacts/discover/import", request);
    return res.data;
  },
  onSuccess: async () => {
    // CORRECT: Await invalidation before marking mutation as done
    await queryClient.invalidateQueries({
      queryKey: ['artifacts', 'discover']
    });
    // Also refetch fresh discovery results
    await queryClient.refetchQueries({
      queryKey: ['artifacts', 'discover']
    });
  },
});
```

**useCacheRefresh.ts Enhancement:**
```typescript
// Add projectId parameter to enable granular invalidation
export function useCacheRefresh(projectId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await api.post(
        '/cache/refresh',
        projectId ? { project_id: projectId } : {}
      );
      return response.data;
    },
    onSuccess: async () => {
      // Invalidate only the specific project, not all projects
      if (projectId) {
        await queryClient.invalidateQueries({
          queryKey: ['projects', 'detail', projectId]
        });
      } else {
        // Only invalidate specific cache keys, not broad patterns
        await queryClient.invalidateQueries({
          queryKey: ['projects', 'list']
        });
      }
    },
  });
}
```

**useDeploy.ts:**
```typescript
// Pass projectId from context to cache refresh
const { projectId } = useParams();
const { mutate: refreshCache } = useCacheRefresh(projectId);

const deployMutation = useMutation({
  mutationFn: async (artifact: ArtifactType) => {
    return api.post(`/deploy/${projectId}`, artifact);
  },
  onSuccess: async () => {
    // Refresh only this project's cache
    await refreshCache();
    // Invalidate specific project's queries
    await queryClient.invalidateQueries({
      queryKey: ['projects', 'detail', projectId]
    });
  },
});
```

---

### Task 4: Frontend UI Update - Show Remaining Count (BUG1-003)

**Assigned To:** `ui-engineer`
**Story Points:** 3
**Dependencies:** BUG1-002, BUG2-001
**Estimated Time:** 1-2 hours

**Description:**
Update DiscoveryBanner component to display remaining unimported artifacts count instead of total discovered.

**Acceptance Criteria:**
- ✓ Banner displays `importable_count` instead of `discovered_count`
- ✓ After importing some artifacts, banner shows correct remaining count
- ✓ After importing all artifacts, banner disappears
- ✓ Text clearly explains "X artifacts remaining to import"
- ✓ Component re-renders only after cache is fresh

**Files to Modify:**
- `skillmeat/web/components/discovery/DiscoveryBanner.tsx`
- `skillmeat/web/hooks/useProjectDiscovery.ts`

**Code Changes:**

**DiscoveryBanner.tsx:**
```typescript
interface DiscoveryBannerProps {
  importableCount: number;      // Unimported count
  discoveredCount?: number;     // Total (for stats)
  onReview: () => void;
  dismissible?: boolean;
}

export function DiscoveryBanner({
  importableCount,
  discoveredCount,
  onReview,
  dismissible = true,
}: DiscoveryBannerProps) {
  // Hide if nothing left to import
  if (importableCount === 0) return null;

  return (
    <Alert variant="default" className="mb-4">
      <Info className="h-4 w-4" />
      <AlertTitle>
        {importableCount === 1
          ? "1 Artifact Ready to Import"
          : `${importableCount} Artifacts Ready to Import`}
      </AlertTitle>
      <AlertDescription>
        {discoveredCount && (
          <p className="text-sm text-muted-foreground mb-2">
            Found {discoveredCount} total • {importableCount} remaining
          </p>
        )}
        Review and import these artifacts to get started quickly.
      </AlertDescription>
      {/* ... rest of component ... */}
    </Alert>
  );
}
```

**useProjectDiscovery.ts:**
```typescript
export function useProjectDiscovery() {
  const discoverQuery = useQuery({
    queryKey: ['artifacts', 'discover'],
    queryFn: async () => {
      const res = await api.post("/artifacts/discover", {});
      return res.data;  // Returns { discovered_count, importable_count, artifacts }
    },
  });

  return {
    importableCount: discoverQuery.data?.importable_count || 0,
    discoveredCount: discoverQuery.data?.discovered_count || 0,
    discoveredArtifacts: discoverQuery.data?.artifacts || [],
    isDiscovering: discoverQuery.isLoading,
    discoverError: discoverQuery.error,
    bulkImport: bulkImportMutation.mutateAsync,
    isImporting: bulkImportMutation.isPending,
  };
}
```

---

### Task 5: Integration Tests for Cache Fixes (BUG2-002)

**Assigned To:** `python-backend-engineer`
**Story Points:** 3
**Dependencies:** BUG1-002, BUG2-001
**Estimated Time:** 1.5-2 hours

**Description:**
Add integration tests verifying correct cache invalidation behavior and discovery filtering.

**Acceptance Criteria:**
- ✓ Test: Discovery filters imported artifacts correctly
- ✓ Test: Importing artifacts updates discovery count
- ✓ Test: Project-specific cache invalidation works
- ✓ Test: Unrelated projects not invalidated
- ✓ Tests verify both backend and frontend behavior

**Files to Create:**
- `skillmeat/api/tests/test_discovery_cache_fixes.py`

**Test Cases:**
```python
def test_discovery_filters_imported_artifacts(client, temp_collection):
    """Discovery returns only unimported artifacts"""
    # Create collection with 2 imported artifacts
    # Discover should return remaining 11 unimported

def test_importable_count_decreases_after_import(client, temp_collection):
    """Discovery count decreases as artifacts are imported"""
    # Initial: importable_count = 13
    # After import 6: importable_count = 7

def test_cache_invalidation_specific_project(client):
    """Cache invalidation only affects target project"""
    # Import to project_a
    # Verify project_a cache invalidated
    # Verify project_b cache NOT invalidated

def test_refetch_waits_for_fresh_data(client, temp_collection):
    """Refetch waits for server before re-render"""
    # Mock intentional delay in discovery endpoint
    # Verify component doesn't show stale data during delay
```

---

### Task 6: Frontend Component Tests (BUG1-004)

**Assigned To:** `ui-engineer`
**Story Points:** 2
**Dependencies:** BUG1-003
**Estimated Time:** 1 hour

**Description:**
Add unit tests for DiscoveryBanner to verify correct count display and hiding behavior.

**Acceptance Criteria:**
- ✓ Banner displays importable count, not total discovered
- ✓ Banner hides when importable count is 0
- ✓ Banner shows "1 Artifact" vs "N Artifacts" correctly
- ✓ >80% component coverage

**Files to Create/Modify:**
- `skillmeat/web/tests/discovery-banner.test.tsx`

**Test Cases:**
```typescript
it("displays importable count, not total discovered", () => {
  render(
    <DiscoveryBanner
      importableCount={7}
      discoveredCount={13}
      onReview={() => {}}
    />
  );
  expect(screen.getByText(/7 Artifacts Ready to Import/)).toBeInTheDocument();
  expect(screen.getByText(/Found 13 total.*7 remaining/)).toBeInTheDocument();
});

it("hides when importable count is 0", () => {
  const { container } = render(
    <DiscoveryBanner importableCount={0} onReview={() => {}} />
  );
  expect(container.firstChild).toBeNull();
});

it("shows singular 'Artifact' when count is 1", () => {
  render(
    <DiscoveryBanner importableCount={1} onReview={() => {}} />
  );
  expect(screen.getByText("1 Artifact Ready to Import")).toBeInTheDocument();
});
```

---

## Testing Strategy

### Unit Tests (>80% Coverage)

**Backend:**
- `test_discovery_filtering.py` - Verify discovery filters imported artifacts
- `test_cache_refresh.py` - Verify cache invalidation specificity
- `test_api_endpoints.py` - Verify endpoint response schemas

**Frontend:**
- `discovery-banner.test.tsx` - Component rendering and count display
- `useProjectDiscovery.test.ts` - Hook cache invalidation behavior

### Integration Tests (>70% Coverage)

- End-to-end discovery -> import flow with count verification
- Multi-project cache invalidation scenario
- Async/await correctness in mutation flow

### Manual Testing

1. Import 6 of 13 artifacts, verify banner count updates immediately
2. Switch between projects, verify no unnecessary re-fetches
3. Check network tab during import for granular cache requests

---

## Success Metrics

| Metric | Current | Target | Verification |
|--------|---------|--------|--------------|
| Discovery banner accuracy | Shows all artifacts | Shows only unimported | Manual + tests |
| Cache invalidation scope | All projects invalidated | Only target project | Performance profile |
| Component re-render timing | Stale data shown | Fresh data only | Network spy + tests |
| Unrelated project load time | Slow (unnecessary refresh) | Fast (no refresh) | Performance measurement |

---

## Orchestration Quick Reference

### Recommended Execution Order

**Phase 1: Backend Fixes** (Parallel)
```
Task("python-backend-engineer", "BUG1-001: Backend discovery filtering")
Task("python-backend-engineer", "BUG1-002: API endpoint update")
```

**Phase 2: Frontend Cache Fixes** (After Phase 1)
```
Task("ui-engineer", "BUG2-001: Cache invalidation async/await fixes")
Task("ui-engineer", "BUG1-003: DiscoveryBanner count update")
```

**Phase 3: Testing** (Parallel with Phase 2)
```
Task("python-backend-engineer", "BUG2-002: Integration tests")
Task("ui-engineer", "BUG1-004: Component tests")
```

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|-----------|
| Manifest loading fails | HIGH | LOW | Add error handling, graceful fallback to unfiltered discovery |
| Async/await breaks imports | HIGH | MEDIUM | Comprehensive tests, manual testing of import flow |
| Cache keys mismatch | MEDIUM | MEDIUM | Audit all query key patterns, document consistent pattern |
| Performance regression | MEDIUM | LOW | Benchmark discovery before/after, monitor in staging |

---

## Definition of Done

- ✓ All code changes peer-reviewed and approved
- ✓ Unit tests >80% coverage (backend), >70% (frontend)
- ✓ Integration tests passing
- ✓ Manual testing: discovery count accuracy verified
- ✓ Manual testing: cache invalidation scope verified
- ✓ No performance regressions from filtering
- ✓ No regressions in existing discovery/import flow
- ✓ Documentation updated if needed

---

## Timeline

```
Day 1-2: Backend filtering + API update (BUG1-001, BUG1-002)
Day 2-3: Frontend cache fixes + UI update (BUG2-001, BUG1-003)
Day 3-4: Testing (BUG2-002, BUG1-004)
Day 4-5: Manual testing, bug fixes, deployment prep
```

**Total Estimated Effort:** 16-20 story points
**Expected Completion:** 1 week

---

## Implementation Status

**Current:** Draft - Ready for assignment
**Created:** 2025-12-03
**Last Updated:** 2025-12-03

---

## Related Documents

- Progress Tracking: (to be created in `.claude/progress/discovery-cache-fixes/`)
- Original Issues: Issue tracking system
- Discovery Feature PRD: `/docs/project_plans/PRDs/enhancements/smart-import-discovery-v1.md`
