---
title: "Implementation Plan: Data Flow Standardization"
description: "Remediate 14 identified data flow inconsistencies across frontend hooks and backend endpoints to achieve full compliance with the canonical data flow standard"
audience: [ai-agents, developers]
tags: [implementation, refactor, data-flow, caching, frontend, backend, standardization]
created: 2026-02-04
updated: 2026-02-04
category: "refactors"
status: draft
complexity: Medium
total_effort: "10-14 hours (Phases 1-2)"
related:
  - /docs/project_plans/reports/data-flow-standardization-report.md
  - /docs/project_plans/implementation_plans/refactors/tag-management-architecture-fix-v1.md
  - /docs/project_plans/implementation_plans/refactors/tag-storage-consolidation-v1.md
  - /docs/project_plans/implementation_plans/refactors/refresh-metadata-extraction-v1.md
  - /docs/project_plans/implementation_plans/refactors/artifact-metadata-cache-v1.md
---

# Implementation Plan: Data Flow Standardization

**Plan ID**: `IMPL-2026-02-04-DATA-FLOW-STD`
**Date**: 2026-02-04
**Author**: Claude Opus 4.5 (AI-generated)
**Source Report**: `/docs/project_plans/reports/data-flow-standardization-report.md`

**Complexity**: Medium
**Total Estimated Effort**: 10-14 hours
**Target Timeline**: Single PR per phase

---

## Executive Summary

The Data Flow Standardization Report identified 14 inconsistencies across SkillMeat's data flow patterns. This implementation plan remediates those inconsistencies across two phases:

- **Phase 1**: Frontend standardization (11 tasks, 4-6h) -- hook stale times and cache invalidation
- **Phase 2**: Backend cache-first reads (6 tasks, 6-8h) -- router cache refresh and API client migration

**Prerequisites (Phase 0)**: Four in-flight plans must complete first:
1. Tag FK mismatch fix (`tag-management-architecture-fix-v1.md` Phase 1)
2. Tag write-back durability (`tag-management-architecture-fix-v1.md` Phases 2-4)
3. Tag storage consolidation (`tag-storage-consolidation-v1.md`)
4. Refresh metadata extraction (`refresh-metadata-extraction-v1.md`)

**Out of Scope**: Phase 3 from the report (deployment/project DB caching, WebSocket push) requires a separate PRD.

### Issues Addressed

| Issue # | Severity | Description | Phase |
|---------|----------|-------------|-------|
| 4 | Medium | `useArtifacts()` stale time 30sec (should be 5min) | 1 |
| 5 | Medium | `useArtifact()` no stale time (should be 5min) | 1 |
| 6 | High | `useRollback()` missing `['deployments']`, `['projects']` invalidation | 1 |
| 7 | Medium | Context sync hooks missing `['deployments']` invalidation | 1 |
| 8 | Medium | Tag artifact hooks missing `['artifacts']` invalidation | 1 |
| 9 | Low | `useSync()` uses raw `fetch()` instead of `apiRequest()` | 2 |
| 10 | Medium | `useInstallListing()` missing `['artifacts']` invalidation | 1 |
| 11 | Medium | `useDeleteTag()` missing per-artifact tag prefix invalidation | 1 |
| 12 | Low | `useCacheRefresh()` missing `['artifacts']` invalidation | 1 |
| 13 | Low | `useProject()` no stale time (should be 5min) | 1 |
| 14 | Medium | `useDeleteArtifact()` missing cross-domain invalidation | 1 |
| 1 | High | `GET /artifacts` list reads FS, not DB cache | 2 |
| 2 | High | `GET /artifacts/{id}` detail reads FS, not DB cache | 2 |
| 3 | High | File create/update/delete missing cache refresh | 2 |

---

## Phase 0: Prerequisites

**Status**: Must complete before this plan executes

These in-flight plans address foundational issues that block Phase 1-2 work:

| Prerequisite | Implementation Plan | Resolves |
|--------------|-------------------|----------|
| Tag FK mismatch | `tag-management-architecture-fix-v1.md` Phase 1 | Tag counts show 0 |
| Tag write-back | `tag-management-architecture-fix-v1.md` Phases 2-4 | Tag changes revert on refresh |
| Tag storage | `tag-storage-consolidation-v1.md` | Duplicate tag sources |
| Metadata extraction | `refresh-metadata-extraction-v1.md` | Stale metadata in cache |

**Verification**: Before starting Phase 1, confirm:
- [ ] `artifact_tags` table has FK constraint removed
- [ ] Tag rename/delete persists across cache refresh
- [ ] `refresh_single_artifact_cache()` extracts current metadata

---

## Phase 1: Frontend Standardization

**Priority**: HIGH
**Duration**: 4-6 hours
**Dependencies**: Phase 0 complete
**Risk**: Low (frontend-only changes, no backend modifications)
**Assigned Subagent(s)**: `ui-engineer-enhanced`

### Overview

Quick wins that only require frontend hook changes. All changes are to TanStack Query configuration in React hooks.

### Task Table

| Task ID | Task Name | File | Line(s) | Issue # | Estimate |
|---------|-----------|------|---------|---------|----------|
| TASK-1.1 | Fix `useArtifacts()` stale time | `hooks/useArtifacts.ts` | 345 | #4 | 15m |
| TASK-1.2 | Add `useArtifact()` stale time | `hooks/useArtifacts.ts` | 353-360 | #5 | 15m |
| TASK-1.3 | Add `useProject()` stale time | `hooks/useProjects.ts` | 241-248 | #13 | 15m |
| TASK-1.4 | Fix `useRollback()` invalidation | `hooks/use-snapshots.ts` | 229-232 | #6 | 20m |
| TASK-1.5 | Fix context sync invalidation | `hooks/use-context-sync.ts` | 59, 82, 109 | #7 | 30m |
| TASK-1.6 | Fix tag artifact hooks invalidation | `hooks/use-tags.ts` | 206-210, 232-237 | #8 | 30m |
| TASK-1.7 | Fix `useDeleteTag()` invalidation | `hooks/use-tags.ts` | 176-182 | #11 | 20m |
| TASK-1.8 | Fix `useInstallListing()` invalidation | `hooks/useMarketplace.ts` | 160-162 | #10 | 15m |
| TASK-1.9 | Fix `useCacheRefresh()` invalidation | `hooks/useCacheRefresh.ts` | 66-77 | #12 | 15m |
| TASK-1.10 | Fix `useDeleteArtifact()` invalidation | `hooks/useArtifacts.ts` | 413-416 | #14 | 20m |
| TASK-1.11 | Document stale time strategy | `web/CLAUDE.md` | new section | -- | 30m |

### Implementation Details

#### TASK-1.1: Fix `useArtifacts()` stale time

**File**: `skillmeat/web/hooks/useArtifacts.ts`
**Line**: 345

Change stale time from 30sec to 5min to match `useInfiniteArtifacts()`:

```typescript
// Before (line 345):
staleTime: 30000,

// After:
staleTime: 5 * 60 * 1000, // 5 min - standard browsing stale time
```

**Acceptance Criteria**:
- `useArtifacts()` uses 5-minute stale time
- No refetch on component remount within 5 minutes

---

#### TASK-1.2: Add `useArtifact()` stale time

**File**: `skillmeat/web/hooks/useArtifacts.ts`
**Lines**: 353-360

Add explicit stale time (currently missing, defaults to 0):

```typescript
// Before:
export function useArtifact(id: string | null) {
  return useQuery({
    queryKey: ['artifacts', 'detail', id],
    queryFn: () => fetchArtifact(id!),
    enabled: !!id,
  });
}

// After:
export function useArtifact(id: string | null) {
  return useQuery({
    queryKey: ['artifacts', 'detail', id],
    queryFn: () => fetchArtifact(id!),
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // 5 min - matches useArtifacts()
  });
}
```

**Acceptance Criteria**:
- `useArtifact()` has explicit 5-minute stale time
- Artifact detail modal doesn't trigger refetch on reopen within 5 minutes

---

#### TASK-1.3: Add `useProject()` stale time

**File**: `skillmeat/web/hooks/useProjects.ts`
**Lines**: 241-248

Add stale time matching `PROJECTS_STALE_TIME`:

```typescript
// Before:
export function useProject(projectPath: string | null) {
  return useQuery({
    queryKey: ['projects', 'detail', projectPath],
    queryFn: () => fetchProject(projectPath!),
    enabled: !!projectPath,
  });
}

// After:
export function useProject(projectPath: string | null) {
  return useQuery({
    queryKey: ['projects', 'detail', projectPath],
    queryFn: () => fetchProject(projectPath!),
    enabled: !!projectPath,
    staleTime: PROJECTS_STALE_TIME, // 5 min - matches useProjects()
  });
}
```

**Acceptance Criteria**:
- `useProject()` uses `PROJECTS_STALE_TIME` constant (5 min)
- Consistent stale time between list and detail queries

---

#### TASK-1.4: Fix `useRollback()` invalidation

**File**: `skillmeat/web/hooks/use-snapshots.ts`
**Lines**: 229-232

Add missing `['deployments']` and `['projects']` invalidation:

```typescript
// Before:
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['snapshots'] });
  queryClient.invalidateQueries({ queryKey: ['collections'] });
  queryClient.invalidateQueries({ queryKey: ['artifacts'] });
},

// After:
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['snapshots'] });
  queryClient.invalidateQueries({ queryKey: ['collections'] });
  queryClient.invalidateQueries({ queryKey: ['artifacts'] });
  queryClient.invalidateQueries({ queryKey: ['deployments'] }); // Rollback changes deployed state
  queryClient.invalidateQueries({ queryKey: ['projects'] }); // Project deployment info may change
},
```

**Acceptance Criteria**:
- Rollback invalidates deployment and project caches
- Deployment views refresh after snapshot rollback

---

#### TASK-1.5: Fix context sync invalidation

**File**: `skillmeat/web/hooks/use-context-sync.ts`
**Lines**: 59, 82, 109

Add `['deployments']` to all three mutation hooks:

```typescript
// usePullContextChanges (line ~59):
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['context-sync-status'] });
  queryClient.invalidateQueries({ queryKey: ['artifact-files'] });
  queryClient.invalidateQueries({ queryKey: ['context-entities'] });
  queryClient.invalidateQueries({ queryKey: ['deployments'] }); // NEW
},

// usePushContextChanges (line ~82):
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['context-sync-status'] });
  queryClient.invalidateQueries({ queryKey: ['artifact-files'] });
  queryClient.invalidateQueries({ queryKey: ['deployments'] }); // NEW
  queryClient.invalidateQueries({ queryKey: ['context-entities'] }); // NEW (was missing from push)
},

// useResolveContextConflict (line ~109):
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['context-sync-status'] });
  queryClient.invalidateQueries({ queryKey: ['artifact-files'] });
  queryClient.invalidateQueries({ queryKey: ['context-entities'] });
  queryClient.invalidateQueries({ queryKey: ['deployments'] }); // NEW
},
```

**Acceptance Criteria**:
- All three context sync hooks invalidate `['deployments']`
- Push also invalidates `['context-entities']`
- Deployment view updates after sync operations

---

#### TASK-1.6: Fix tag artifact hooks invalidation

**File**: `skillmeat/web/hooks/use-tags.ts`
**Lines**: 206-210, 232-237

Add `['artifacts']` invalidation to both hooks:

```typescript
// useAddTagToArtifact (lines 206-210):
onSuccess: (_, variables) => {
  queryClient.invalidateQueries({
    queryKey: ['tags', 'artifact', variables.artifactId],
  });
  queryClient.invalidateQueries({ queryKey: ['artifacts'] }); // NEW - artifact list embeds tags
},

// useRemoveTagFromArtifact (lines 232-237):
onSuccess: (_, variables) => {
  queryClient.invalidateQueries({
    queryKey: ['tags', 'artifact', variables.artifactId],
  });
  queryClient.invalidateQueries({ queryKey: ['artifacts'] }); // NEW - artifact list embeds tags
},
```

**Acceptance Criteria**:
- Tag add/remove invalidates `['artifacts']`
- Artifact list view shows updated tags immediately

---

#### TASK-1.7: Fix `useDeleteTag()` invalidation

**File**: `skillmeat/web/hooks/use-tags.ts`
**Lines**: 176-182

Add prefix invalidation for per-artifact tag queries:

```typescript
// Before:
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['tags'] });
  queryClient.invalidateQueries({ queryKey: ['artifacts'] });
},

// After:
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['tags'] });
  queryClient.invalidateQueries({ queryKey: ['artifacts'] });
  // Invalidate all per-artifact tag queries (prefix match)
  queryClient.invalidateQueries({ queryKey: ['tags', 'artifact'] });
},
```

**Acceptance Criteria**:
- Tag deletion invalidates all `['tags', 'artifact', *]` queries
- Per-artifact tag views don't show deleted tags

---

#### TASK-1.8: Fix `useInstallListing()` invalidation

**File**: `skillmeat/web/hooks/useMarketplace.ts`
**Lines**: 160-162

Add `['artifacts']` invalidation:

```typescript
// Before:
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['marketplace', 'listings'] });
},

// After:
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['marketplace', 'listings'] });
  queryClient.invalidateQueries({ queryKey: ['artifacts'] }); // NEW - installed artifact appears in collection
},
```

**Acceptance Criteria**:
- Installed marketplace listing appears in artifact list immediately
- No manual refresh needed after install

---

#### TASK-1.9: Fix `useCacheRefresh()` invalidation

**File**: `skillmeat/web/hooks/useCacheRefresh.ts`
**Lines**: 66-77

Add `['artifacts']` invalidation:

```typescript
// Before:
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['projects'] });
  queryClient.invalidateQueries({ queryKey: ['cache'] });
},

// After:
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['projects'] });
  queryClient.invalidateQueries({ queryKey: ['cache'] });
  queryClient.invalidateQueries({ queryKey: ['artifacts'] }); // NEW - cache refresh updates artifact metadata
},
```

**Acceptance Criteria**:
- Full cache refresh also refreshes artifact data
- Artifact views reflect updated metadata after cache refresh

---

#### TASK-1.10: Fix `useDeleteArtifact()` invalidation

**File**: `skillmeat/web/hooks/useArtifacts.ts`
**Lines**: 413-416

Add `['deployments']` and `['collections']` invalidation:

```typescript
// Before:
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['artifacts'] });
},

// After:
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['artifacts'] });
  queryClient.invalidateQueries({ queryKey: ['deployments'] }); // NEW - artifact may have been deployed
  queryClient.invalidateQueries({ queryKey: ['collections'] }); // NEW - collection membership changes
},
```

**Note**: Consider whether to deprecate `useDeleteArtifact()` in favor of `useArtifactDeletion()` which already has correct invalidation. Add deprecation comment if keeping both.

**Acceptance Criteria**:
- `useDeleteArtifact()` invalidates all related caches
- Deployment and collection views update after artifact deletion

---

#### TASK-1.11: Document stale time strategy

**File**: `skillmeat/web/CLAUDE.md`
**Location**: New section after "API Client Usage" or similar

Add documentation section:

```markdown
## TanStack Query Stale Time Strategy

All query hooks follow standardized stale times per the data flow standard:

| Domain | Stale Time | Rationale |
|--------|-----------|-----------|
| Artifacts (list/detail) | 5 min | Standard browsing, cache-backed |
| Collections | 5 min | Standard browsing |
| Tags (list/detail) | 5 min | Low-frequency changes |
| Tags (search) | 30 sec | Interactive, needs freshness |
| Groups | 5 min | Low-frequency changes |
| Deployments | 2 min | More dynamic, filesystem-backed |
| Projects | 5 min | Low-frequency changes |
| Marketplace listings | 1 min | External, moderately dynamic |
| Marketplace detail | 5 min | Slow-changing |
| Analytics summary | 30 sec | Monitoring dashboard, needs freshness |
| Analytics trends | 5 min | Aggregate, slow-changing |
| Context Entities | 5 min | Low-frequency changes |
| Artifact Search | 30 sec | Interactive search |
| Cache/Sync status | 30 sec | Monitoring |

### Cache Invalidation Graph

Mutations must invalidate all related caches per this graph:

| Mutation | Must Invalidate |
|----------|----------------|
| Artifact CRUD | `['artifacts']`, `['collections']`, `['deployments']` |
| Tag CRUD | `['tags']`, `['artifacts']` |
| Tag add/remove from artifact | `['tags', 'artifact', artifactId]`, `['artifacts']` |
| Collection CRUD | `['collections']`, `['artifacts']` |
| Group CRUD | `['groups']`, `['artifact-groups']` |
| Deploy/Undeploy | `['deployments']`, `['artifacts']`, `['projects']` |
| Snapshot rollback | `['snapshots']`, `['artifacts']`, `['deployments']`, `['collections']`, `['projects']` |
| Context sync | `['context-sync-status']`, `['artifact-files']`, `['context-entities']`, `['deployments']` |
| Cache refresh | `['projects']`, `['cache']`, `['artifacts']` |

Reference: `/docs/project_plans/reports/data-flow-standardization-report.md`
```

**Acceptance Criteria**:
- `web/CLAUDE.md` includes stale time table
- `web/CLAUDE.md` includes cache invalidation graph
- Reference to source report included

---

### Phase 1 Quality Gates

- [ ] All 10 frontend hooks have correct stale times or invalidation
- [ ] `web/CLAUDE.md` includes new stale time documentation
- [ ] TypeScript compilation passes (`pnpm tsc --noEmit`)
- [ ] ESLint passes (`pnpm lint`)
- [ ] Existing tests pass (`pnpm test`)
- [ ] Manual verification: artifact list doesn't refetch within 5 minutes
- [ ] Manual verification: rollback triggers deployment view refresh
- [ ] Manual verification: tag changes appear in artifact list immediately

---

## Phase 2: Backend Cache-First Reads

**Priority**: HIGH
**Duration**: 6-8 hours
**Dependencies**: Phase 1 complete, Phase 0 prerequisites complete
**Risk**: Medium (backend router changes, requires careful testing)
**Assigned Subagent(s)**: `python-backend-engineer` (Tasks 2.1-2.5), `ui-engineer-enhanced` (Task 2.6)

### Overview

Backend changes to ensure write-through pattern compliance. Focus on:
1. Adding `refresh_single_artifact_cache()` calls after file mutations
2. Migrating one frontend hook from raw `fetch()` to `apiRequest()`

**Note**: Tasks 2.1-2.2 (cache-first reads for `GET /artifacts`) are deferred pending further analysis. The current `artifact-metadata-cache-v1.md` plan already addresses DB-first reads for `/user-collections/{id}/artifacts`. Adding cache-first reads to `/artifacts` requires careful consideration of the dual-stack architecture.

### Task Table

| Task ID | Task Name | File | Line(s) | Issue # | Estimate |
|---------|-----------|------|---------|---------|----------|
| TASK-2.1 | DEFERRED: Cache-first `GET /artifacts` list | `api/routers/artifacts.py` | 1680-1800 | #1 | -- |
| TASK-2.2 | DEFERRED: Cache-first `GET /artifacts/{id}` detail | `api/routers/artifacts.py` | 1993-2112 | #2 | -- |
| TASK-2.3 | Add cache refresh after file create | `api/routers/artifacts.py` | ~5350 | #3 | 45m |
| TASK-2.4 | Add cache refresh after file update | `api/routers/artifacts.py` | ~5100 | #3 | 45m |
| TASK-2.5 | Add cache refresh after file delete | `api/routers/artifacts.py` | ~5610 | #3 | 45m |
| TASK-2.6 | Migrate `useSync()` to `apiRequest()` | `hooks/useSync.ts` | 59 | #9 | 30m |

### Implementation Details

#### TASK-2.1 & TASK-2.2: DEFERRED

**Rationale**: The `artifact-metadata-cache-v1.md` plan already implements DB-first reads for `/user-collections/{id}/artifacts`. Adding cache-first reads to the root `/artifacts` endpoint requires:

1. Determining whether `/artifacts` should return from all collections or just default
2. Ensuring backward compatibility with CLI usage patterns
3. Handling the case where an artifact exists in filesystem but not in cache

These considerations warrant a separate implementation plan. For now, the frontend can use `useCollectionArtifacts()` for DB-backed artifact listing.

---

#### TASK-2.3: Add cache refresh after file create

**File**: `skillmeat/api/routers/artifacts.py`
**Location**: `create_artifact_file()` endpoint (around line 5350)

Add `refresh_single_artifact_cache()` call after successful file creation:

```python
# At end of create_artifact_file(), after file write succeeds:
from skillmeat.api.services.artifact_cache_service import refresh_single_artifact_cache

# After: file_path.write_text(content, encoding="utf-8")
# Add cache refresh:
try:
    refresh_single_artifact_cache(
        session=db_session,
        artifact_mgr=artifact_mgr,
        collection_id=DEFAULT_COLLECTION_ID,  # Or determine from artifact
        artifact_id=artifact_id,
    )
    logger.debug(f"Refreshed cache after file create: {artifact_id}")
except Exception as e:
    # Don't fail the create if cache refresh fails
    logger.warning(f"Cache refresh failed after file create for {artifact_id}: {e}")

return {"created": True, "path": str(file_path)}
```

**Acceptance Criteria**:
- Creating a file triggers artifact cache refresh
- Cache refresh failure doesn't fail the create operation
- `description` field updates when `SKILL.md` content changes

---

#### TASK-2.4: Add cache refresh after file update

**File**: `skillmeat/api/routers/artifacts.py`
**Location**: `update_artifact_file_content()` endpoint (around line 5100)

Add `refresh_single_artifact_cache()` call after successful file update:

```python
# At end of update_artifact_file_content(), after file write succeeds:
from skillmeat.api.services.artifact_cache_service import refresh_single_artifact_cache

# After: file_path.write_text(content, encoding="utf-8")
# Add cache refresh:
try:
    refresh_single_artifact_cache(
        session=db_session,
        artifact_mgr=artifact_mgr,
        collection_id=DEFAULT_COLLECTION_ID,
        artifact_id=artifact_id,
    )
    logger.debug(f"Refreshed cache after file update: {artifact_id}")
except Exception as e:
    logger.warning(f"Cache refresh failed after file update for {artifact_id}: {e}")

return {"updated": True, "path": str(file_path)}
```

**Acceptance Criteria**:
- Updating a file triggers artifact cache refresh
- Editing `SKILL.md` description updates `CollectionArtifact.description`
- Cache refresh failure doesn't fail the update operation

---

#### TASK-2.5: Add cache refresh after file delete

**File**: `skillmeat/api/routers/artifacts.py`
**Location**: `delete_artifact_file()` endpoint (around line 5610)

Add `refresh_single_artifact_cache()` call after successful file deletion:

```python
# At end of delete_artifact_file(), after file delete succeeds:
from skillmeat.api.services.artifact_cache_service import refresh_single_artifact_cache

# After: file_path.unlink()
# Add cache refresh (metadata may change when files are removed):
try:
    refresh_single_artifact_cache(
        session=db_session,
        artifact_mgr=artifact_mgr,
        collection_id=DEFAULT_COLLECTION_ID,
        artifact_id=artifact_id,
    )
    logger.debug(f"Refreshed cache after file delete: {artifact_id}")
except Exception as e:
    logger.warning(f"Cache refresh failed after file delete for {artifact_id}: {e}")

return {"deleted": True, "path": str(file_path)}
```

**Note**: If the deleted file was the main artifact file (e.g., `SKILL.md`), the cache refresh may fail or produce incomplete metadata. This is acceptable -- the artifact is in a degraded state anyway.

**Acceptance Criteria**:
- Deleting a file triggers artifact cache refresh
- Cache refresh failure doesn't fail the delete operation
- Logging indicates success or failure of cache refresh

---

#### TASK-2.6: Migrate `useSync()` to `apiRequest()`

**File**: `skillmeat/web/hooks/useSync.ts`
**Line**: 59

Replace raw `fetch()` with `apiRequest()`:

```typescript
// Before (line 59):
const response = await fetch(`/api/artifacts/${artifactId}/sync`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(syncOptions),
});

if (!response.ok) {
  throw new Error(`Sync failed: ${response.statusText}`);
}

return response.json();

// After:
import { apiRequest } from '@/lib/api/client';

const response = await apiRequest<SyncResponse>(
  `/artifacts/${artifactId}/sync`,
  {
    method: 'POST',
    body: JSON.stringify(syncOptions),
  }
);

return response;
```

**Benefits**:
- Unified error handling from API client
- Automatic base URL construction
- Consistent auth header handling (if/when added)
- Better TypeScript inference

**Acceptance Criteria**:
- `useSync()` uses `apiRequest()` instead of `fetch()`
- Sync functionality unchanged
- Error handling consistent with other hooks

---

### Phase 2 Quality Gates

- [ ] File create/update/delete endpoints call `refresh_single_artifact_cache()`
- [ ] Cache refresh failures are logged but don't fail the operation
- [ ] `useSync()` uses `apiRequest()`
- [ ] Python tests pass (`pytest -v`)
- [ ] TypeScript compilation passes (`pnpm tsc --noEmit`)
- [ ] Manual verification: editing `SKILL.md` updates artifact description in list view
- [ ] Manual verification: sync operation works with new API client

---

## Files Summary

| File | Action | Phase |
|------|--------|-------|
| `skillmeat/web/hooks/useArtifacts.ts` | Modify stale times, invalidation | 1 |
| `skillmeat/web/hooks/useProjects.ts` | Add stale time | 1 |
| `skillmeat/web/hooks/use-snapshots.ts` | Add invalidation | 1 |
| `skillmeat/web/hooks/use-context-sync.ts` | Add invalidation | 1 |
| `skillmeat/web/hooks/use-tags.ts` | Add invalidation | 1 |
| `skillmeat/web/hooks/useMarketplace.ts` | Add invalidation | 1 |
| `skillmeat/web/hooks/useCacheRefresh.ts` | Add invalidation | 1 |
| `skillmeat/web/CLAUDE.md` | Add documentation | 1 |
| `skillmeat/api/routers/artifacts.py` | Add cache refresh calls | 2 |
| `skillmeat/web/hooks/useSync.ts` | Migrate to apiRequest | 2 |

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Stale time changes cause unexpected refetches | Low | Low | Changes increase stale time, reducing refetches |
| Over-invalidation causes performance issues | Low | Medium | Monitor network requests; roll back if excessive |
| Cache refresh slows file operations | Low | Medium | Refresh is async and failure doesn't block |
| `apiRequest()` migration breaks sync | Low | Medium | Test thoroughly; keep fetch as fallback initially |
| Phase 0 prerequisites incomplete | Medium | High | Block Phase 1 start until verified |

---

## Orchestration Quick Reference

### Phase 1 Execution (Single Subagent)

```
Task("ui-engineer-enhanced", "Phase 1: Frontend Standardization - Data Flow Compliance

Execute 11 tasks to standardize frontend hooks:

TASKS 1.1-1.3 (Stale Times):
- useArtifacts.ts:345 - Change staleTime from 30000 to 5 * 60 * 1000
- useArtifacts.ts:353-360 - Add staleTime: 5 * 60 * 1000 to useArtifact()
- useProjects.ts:241-248 - Add staleTime: PROJECTS_STALE_TIME to useProject()

TASKS 1.4-1.10 (Cache Invalidation):
- use-snapshots.ts:229-232 - Add ['deployments'], ['projects'] to useRollback()
- use-context-sync.ts:59,82,109 - Add ['deployments'] to all three hooks; add ['context-entities'] to push
- use-tags.ts:206-210,232-237 - Add ['artifacts'] to useAddTagToArtifact/useRemoveTagFromArtifact
- use-tags.ts:176-182 - Add ['tags', 'artifact'] prefix to useDeleteTag()
- useMarketplace.ts:160-162 - Add ['artifacts'] to useInstallListing()
- useCacheRefresh.ts:66-77 - Add ['artifacts'] to useCacheRefresh()
- useArtifacts.ts:413-416 - Add ['deployments'], ['collections'] to useDeleteArtifact()

TASK 1.11 (Documentation):
- web/CLAUDE.md - Add 'TanStack Query Stale Time Strategy' section with table and invalidation graph

Reference: /docs/project_plans/reports/data-flow-standardization-report.md Section 5 (Principle 5-6)

Reason: Standardize frontend caching to match canonical data flow patterns")
```

### Phase 2 Execution (Backend)

```
Task("python-backend-engineer", "Phase 2: Backend Cache Refresh - Data Flow Compliance

Execute 3 tasks to add cache refresh after file mutations:

TASK 2.3 (File Create):
- artifacts.py:~5350 - Add refresh_single_artifact_cache() after create_artifact_file() writes
- Import from skillmeat.api.services.artifact_cache_service
- Use DEFAULT_COLLECTION_ID, wrap in try/except, log failures

TASK 2.4 (File Update):
- artifacts.py:~5100 - Add refresh_single_artifact_cache() after update_artifact_file_content() writes
- Same pattern as 2.3

TASK 2.5 (File Delete):
- artifacts.py:~5610 - Add refresh_single_artifact_cache() after delete_artifact_file() deletes
- Same pattern as 2.3

Pattern for all three:
```python
try:
    refresh_single_artifact_cache(
        session=db_session,
        artifact_mgr=artifact_mgr,
        collection_id=DEFAULT_COLLECTION_ID,
        artifact_id=artifact_id,
    )
    logger.debug(f'Refreshed cache after file operation: {artifact_id}')
except Exception as e:
    logger.warning(f'Cache refresh failed for {artifact_id}: {e}')
```

Reason: File mutations must sync to DB cache per write-through pattern")
```

### Phase 2 Execution (Frontend - Sync Migration)

```
Task("ui-engineer-enhanced", "Task 2.6: Migrate useSync to apiRequest

File: skillmeat/web/hooks/useSync.ts
Line: 59

Replace raw fetch() with apiRequest():

Before:
const response = await fetch(`/api/artifacts/${artifactId}/sync`, {...})

After:
import { apiRequest } from '@/lib/api/client';
const response = await apiRequest<SyncResponse>(`/artifacts/${artifactId}/sync`, {...})

Benefits: Unified error handling, base URL, auth headers, TypeScript inference

Reason: Standardize API calls to use unified client")
```

---

## Post-Implementation

### Validation Checklist

Phase 1:
- [ ] All stale time changes verified in browser DevTools (Network tab)
- [ ] Cache invalidation verified via React Query DevTools
- [ ] No TypeScript errors
- [ ] All existing tests pass

Phase 2:
- [ ] File create/update/delete log cache refresh attempts
- [ ] Editing SKILL.md updates description in artifact list
- [ ] Sync works with new API client
- [ ] No Python test failures

### Success Metrics

| Metric | Baseline | Target |
|--------|----------|--------|
| Unnecessary refetches | Frequent | Reduced by >50% |
| Stale data after mutations | Common | Rare (<5% of operations) |
| File edit → list update delay | Manual refresh required | Automatic |

### Future Work (Phase 3 - Separate PRD)

From the source report, these items require dedicated planning:

| Item | Effort | Priority |
|------|--------|----------|
| Deployment state DB cache | 4-6h | Medium |
| Project state DB cache | 4-6h | Medium |
| `X-Cache-Age` response header | 2-3h | Low |
| Cache freshness UI indicator | 2-3h | Low |
| WebSocket push for real-time invalidation | 8-12h | Low |

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-04
**Status**: Ready for Phase 0 verification, then Phase 1 execution
