---
title: 'Implementation Plan: Fix Push to Collection and Pull from Source Sync Operations'
description: Rewire frontend sync mutations to use working artifact-level sync endpoint
  instead of stubbed context-sync service
audience:
- ai-agents
- developers
tags:
- sync
- push-to-collection
- pull-from-source
- bug-fix
- frontend
- mutations
created: 2026-02-04
updated: 2026-02-04
category: product-planning
status: inferred_complete
related:
- /docs/project_plans/PRDs/refactors/sync-diff-modal-standardization-v1.md
- /docs/project_plans/implementation_plans/refactors/artifact-flow-modal-implementation-plan.md
---
# Implementation Plan: Fix Push to Collection & Pull from Source

**Plan ID**: `IMPL-2026-02-04-SYNC-PUSH-PULL-WIRING`
**Date**: 2026-02-04
**Author**: Claude (Opus 4.5)
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/refactors/sync-diff-modal-standardization-v1.md`

**Complexity**: Medium
**Total Estimated Effort**: 13 story points
**Scope**: Frontend-only (backend endpoints already working)

## Executive Summary

"Push to Collection" has no effect because the frontend routes through the stubbed `ContextSyncService` (`POST /context-sync/pull`) instead of the fully implemented `SyncManager` (`POST /artifacts/{id}/sync`). The fix rewires the frontend mutation to use the working artifact-level sync endpoint, adds confirmation dialogs before destructive operations, and surfaces conflict information from the backend response.

## Root Cause Analysis

### Two Sync Systems

| System | Endpoint | Backend Service | Status |
|--------|----------|-----------------|--------|
| Artifact-level sync | `POST /artifacts/{id}/sync` | `SyncManager.sync_from_project()` | **Fully implemented** -- writes FS, updates DB, creates versions |
| Context-entity sync | `POST /context-sync/pull\|push` | `ContextSyncService` | **Stubbed** -- logs "Would update" but never writes |

### Current Broken Flow

```
User clicks "Push to Collection"
  → handlePushToCollection() [sync-status-tab.tsx:487]
  → pushToCollectionMutation [sync-status-tab.tsx:368]
  → pullChanges(projectPath, [entity.id]) [lib/api/context-sync.ts:62]
  → POST /api/v1/context-sync/pull
  → ContextSyncService.pull_changes() [core/services/context_sync.py:282]
  → Logs "Would update collection entity" (line 323)
  → Returns success result WITHOUT writing anything
```

### Target Fixed Flow

```
User clicks "Push to Collection"
  → handlePushToCollection() - shows confirmation dialog
  → User confirms
  → pushToCollectionMutation
  → apiRequest('/artifacts/{id}/sync', { project_path, strategy: 'theirs' })
  → POST /api/v1/artifacts/{id}/sync
  → SyncManager.sync_from_project() [core/sync.py]
  → Actually writes to filesystem, updates DB cache, creates version
  → Returns ArtifactSyncResponse with conflicts if any
  → Frontend handles conflicts or shows success
```

## Implementation Strategy

### Architecture Sequence

This is a **frontend-only fix**. The backend `POST /artifacts/{id}/sync` endpoint is already fully implemented and working. Changes are limited to:

1. **Mutation rewiring** -- Point at the correct API endpoint
2. **UX improvement** -- Add confirmation dialogs
3. **Conflict handling** -- Surface backend conflict data in the UI
4. **Cleanup** -- Remove dead context-sync batch mutations
5. **Testing** -- Update test mocks and add new test cases

### Parallel Work Opportunities

- Steps 1-2 (mutation + dialogs) can be implemented together as they're in the same file
- Step 5 (testing) runs after all code changes

### Critical Path

Step 1 (rewire mutation) is the critical fix. All other steps are UX enhancements.

## Phase Breakdown

### Phase 1: Rewire Mutations and Add Confirmation Dialogs

**Duration**: Single session
**Dependencies**: None
**Assigned Subagent(s)**: ui-engineer-enhanced

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| FE-001 | Rewire pushToCollectionMutation | Change mutation to call `POST /artifacts/{id}/sync` with `project_path` instead of `POST /context-sync/pull` | Clicking "Push to Collection" triggers artifact sync endpoint; collection files are actually updated on disk | 3 pts | ui-engineer-enhanced | None |
| FE-002 | Add Push confirmation dialog | Show AlertDialog before executing push with warning about overwriting collection | Confirmation dialog appears; cancel aborts; confirm executes | 2 pts | ui-engineer-enhanced | FE-001 |
| FE-003 | Add Pull confirmation dialog | Show AlertDialog before executing "Pull from Source" upstream sync | Confirmation dialog appears; cancel aborts; confirm executes | 1 pt | ui-engineer-enhanced | None |
| FE-004 | Handle sync conflicts | Process `ArtifactSyncResponse.conflicts` array; show conflict toast; surface in DiffViewer | Conflicts from backend are visible to user; conflict resolution re-calls sync with force | 3 pts | ui-engineer-enhanced | FE-001 |
| FE-005 | Remove dead batch mutations | Remove `batchPushMutation` and `batchPullMutation` that use stubbed context-sync; route `handleApplyActions` through artifact endpoint | Batch actions in footer work through artifact endpoint | 2 pts | ui-engineer-enhanced | FE-001 |
| FE-006 | Update cache invalidation | Align invalidation keys with data-flow-patterns.md for artifact sync operations | Correct query keys invalidated after push/pull | 1 pt | ui-engineer-enhanced | FE-001 |

**Phase 1 Quality Gates:**
- [ ] "Push to Collection" shows confirmation dialog
- [ ] "Pull from Source" shows confirmation dialog
- [ ] Push actually writes changes to collection on filesystem
- [ ] Conflicts from backend are surfaced in UI
- [ ] Batch operations route through working endpoint
- [ ] No imports remain from `@/lib/api/context-sync` in sync-status-tab.tsx
- [ ] `pnpm typecheck` passes
- [ ] `pnpm lint` passes
- [ ] `pnpm build` passes

---

### Phase 2: Testing

**Duration**: Single session
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: ui-engineer-enhanced

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| TEST-001 | Update existing sync tests | Update mocks in `sync-modal-integration.test.tsx` to match new API call patterns | Existing tests pass with new mock structure | 1 pt | ui-engineer-enhanced | FE-006 |
| TEST-002 | Add confirmation dialog tests | Test that push/pull show dialogs; cancel aborts; confirm executes | Dialog flow tests pass | 1 pt | ui-engineer-enhanced | TEST-001 |

**Phase 2 Quality Gates:**
- [ ] `pnpm test` passes with updated mocks
- [ ] Confirmation dialog flows tested
- [ ] All existing sync tests still pass

## Key Files

### Files to Modify

| File | Lines | Change Type | Description |
|------|-------|-------------|-------------|
| `skillmeat/web/components/sync-status/sync-status-tab.tsx` | 767 | Major | Rewire mutations, add confirmation state/dialogs, handle conflicts, remove dead code, update imports |
| `skillmeat/web/__tests__/sync-modal-integration.test.tsx` | ~200 | Update | Update mocks for artifact endpoint; add confirmation dialog tests |

### Files for Reference (No Changes)

| File | Purpose |
|------|---------|
| `skillmeat/api/routers/artifacts.py:3037-3420` | Working `sync_artifact` endpoint |
| `skillmeat/api/schemas/artifacts.py:540-570` | `ArtifactSyncRequest` schema (project_path, force, strategy) |
| `skillmeat/web/sdk/models/ArtifactSyncResponse.ts` | TypeScript type for sync response |
| `skillmeat/web/sdk/models/ConflictInfo.ts` | TypeScript type for conflict data |
| `skillmeat/web/components/ui/alert-dialog.tsx` | shadcn AlertDialog component |
| `skillmeat/web/components/entity/diff-viewer.tsx` | DiffViewer with resolution support |
| `skillmeat/core/sync.py` | `SyncManager` (fully working backend) |
| `skillmeat/core/services/context_sync.py` | Stubbed service (root cause reference) |
| `skillmeat/web/lib/api/context-sync.ts` | Context-sync API client (being replaced) |

### Key Types (SDK)

```typescript
// ArtifactSyncResponse - returned by POST /artifacts/{id}/sync
type ArtifactSyncResponse = {
  success: boolean;
  message: string;
  artifact_name: string;
  artifact_type: string;
  conflicts?: ConflictInfo[] | null;
  updated_version?: string | null;
  synced_files_count?: number | null;
};

// ConflictInfo
type ConflictInfo = {
  file_path: string;
  conflict_type: string;
};

// ArtifactSyncRequest - sent to POST /artifacts/{id}/sync
// When project_path provided: sync from project to collection
// When project_path omitted: sync from upstream source to collection
type ArtifactSyncRequest = {
  project_path?: string | null;  // Required for push-to-collection
  force?: boolean;               // Default false
  strategy?: string;             // 'theirs' | 'ours' | 'manual'
};
```

### Important Naming Convention

| UI Action | API Direction | Endpoint |
|-----------|---------------|----------|
| "Push to Collection" | Project → Collection | `POST /artifacts/{id}/sync` with `project_path` in body |
| "Pull from Source" | Upstream → Collection | `POST /artifacts/{id}/sync` with empty body (no project_path) |
| "Deploy to Project" | Collection → Project | `POST /artifacts/{id}/deploy` |

## Detailed Implementation Notes

### FE-001: Rewire pushToCollectionMutation

**Current** (sync-status-tab.tsx lines 368-395):
```typescript
const pushToCollectionMutation = useMutation({
  mutationFn: async () => {
    if (!projectPath) throw new Error('No project path available');
    return await pullChanges(projectPath, [entity.id]);  // STUBBED endpoint
  },
  // ...
});
```

**Target**:
```typescript
const pushToCollectionMutation = useMutation({
  mutationFn: async () => {
    if (!projectPath) throw new Error('No project path available');
    return await apiRequest<ArtifactSyncResponse>(
      `/artifacts/${encodeURIComponent(entity.id)}/sync`,
      {
        method: 'POST',
        body: JSON.stringify({
          project_path: projectPath,
          force: false,
          strategy: 'theirs',
        }),
      }
    );
  },
  onSuccess: (data: ArtifactSyncResponse) => {
    queryClient.invalidateQueries({ queryKey: ['artifacts'] });
    queryClient.invalidateQueries({ queryKey: ['deployments'] });
    queryClient.invalidateQueries({ queryKey: ['upstream-diff', entity.id, entity.collection] });
    queryClient.invalidateQueries({ queryKey: ['project-diff', entity.id] });
    queryClient.invalidateQueries({ queryKey: ['collections'] });
    if (data.conflicts && data.conflicts.length > 0) {
      toast({ title: 'Push completed with conflicts', description: `${data.conflicts.length} conflict(s) detected`, variant: 'destructive' });
    } else {
      toast({ title: 'Push Successful', description: data.message || 'Project changes pushed to collection' });
    }
  },
  onError: (error: Error) => {
    toast({ title: 'Push Failed', description: error.message, variant: 'destructive' });
  },
});
```

**Import changes**:
- Add: `import type { ArtifactSyncResponse } from '@/sdk/models/ArtifactSyncResponse';`
- Remove: `pullChanges, pushChanges` from context-sync import (or remove entire import if unused)

### FE-002/003: Confirmation Dialogs

Add state:
```typescript
const [showPushConfirm, setShowPushConfirm] = useState(false);
const [showPullConfirm, setShowPullConfirm] = useState(false);
```

Modify handlers:
```typescript
const handlePushToCollection = useCallback(() => {
  if (!projectPath) {
    toast({ title: 'Error', description: 'No project path available', variant: 'destructive' });
    return;
  }
  setShowPushConfirm(true);
}, [projectPath, toast]);

const handlePullFromSource = () => { setShowPullConfirm(true); };
```

Add confirmation handlers:
```typescript
const confirmPushToCollection = useCallback(() => {
  setShowPushConfirm(false);
  pushToCollectionMutation.mutate();
}, [pushToCollectionMutation]);

const confirmPullFromSource = useCallback(() => {
  setShowPullConfirm(false);
  syncMutation.mutate();
}, [syncMutation]);
```

Add AlertDialog JSX (import from `@/components/ui/alert-dialog`).

### FE-005: Remove Dead Batch Mutations

Remove `batchPushMutation` (lines 398-424) and `batchPullMutation` (lines 427-453). In `handleApplyActions`:
- Push actions → `pushToCollectionMutation.mutate()`
- Pull actions → `syncMutation.mutate()`

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Artifact sync endpoint expects different ID format than frontend sends | High | Low | Verify `entity.id` format matches what artifact router expects. The frontend uses `entity.id` which is the DB ID; the endpoint parses `artifact_id` to extract name/type. |
| Strategy naming mismatch between frontend and backend | Medium | Medium | Backend maps: `theirs` → overwrite (project wins), `ours` → overwrite, `manual` → merge. Verify these match intended UI behavior. |
| AlertDialog not available or different API | Low | Low | Already confirmed at `components/ui/alert-dialog.tsx` |

## Success Metrics

### Delivery Metrics
- "Push to Collection" actually writes to collection filesystem
- "Pull from Source" shows confirmation before executing
- Conflicts from sync are visible to user
- No regressions in existing sync functionality

### Verification

```bash
# Quality gates
cd skillmeat/web && pnpm test && pnpm typecheck && pnpm lint && pnpm build

# Manual verification
# 1. Start dev servers: skillmeat web dev
# 2. Deploy an artifact to a project
# 3. Modify the deployed artifact in the project directory
# 4. Open sync status tab for that artifact
# 5. Click "Push to Collection" → confirm dialog should appear
# 6. Confirm → collection should be updated (check filesystem)
# 7. Verify "Pull from Source" also shows confirmation
```

---

**Progress Tracking**: See `.claude/progress/sync-push-pull-wiring/phase-1-progress.md` (to be created)

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-04
