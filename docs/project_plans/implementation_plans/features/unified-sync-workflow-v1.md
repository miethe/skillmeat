---
title: "Implementation Plan: Unified Sync Workflow Enhancement"
description: "Phased implementation for conflict-aware sync flows across all three directions (Source->Collection->Project) with integrated diff viewer"
audience: [ai-agents, developers]
tags: [implementation, planning, phases, tasks, web-ui, sync, conflict-resolution]
created: 2025-02-04
updated: 2025-02-04
category: "product-planning"
status: draft
related:
  - /skillmeat/web/components/sync-status/sync-status-tab.tsx
  - /skillmeat/web/components/sync-status/artifact-flow-banner.tsx
  - /skillmeat/web/components/entity/diff-viewer.tsx
---

# Implementation Plan: Unified Sync Workflow Enhancement

**Plan ID**: `IMPL-2025-02-04-UNIFIED-SYNC-WORKFLOW`

**Date**: 2025-02-04

**Author**: Claude Code (Implementation Orchestrator)

**Complexity**: Medium (M)

**Total Estimated Effort**: 13 story points

**Target Timeline**: 2-3 weeks

**Workflow Track**: Standard (Haiku + Sonnet agents with dependency mapping)

---

## Executive Summary

This implementation plan enhances the SkillMeat sync workflow to provide a complete, conflict-aware experience across all three sync directions from the Sync Status Tab. The solution integrates the existing Diff Viewer into all sync operations (Deploy, Push, Pull) with pre-operation conflict detection, ensuring users understand and confirm changes before execution.

**Current State Analysis**:
- Pull from Source -> Collection: Fully implemented
- Deploy Collection -> Project: Implemented with overwrite (no pre-check for conflicts)
- Push Project -> Collection: Backend ready, UI incomplete (dashed arrow, no confirmation)
- Diff Viewer: Fully functional but not integrated into deploy/push flows
- Merge Workflow Dialog: 5-step conflict resolution exists

**Key Outcomes**:
- Pre-operation conflict detection for Deploy (Collection -> Project)
- Pre-operation conflict detection for Push (Project -> Collection)
- Unified flow pattern: Check -> Show Diff -> Confirm Strategy -> Execute -> Invalidate
- Solid arrow for Push when project deployment exists
- Action buttons integrated into flow banner connectors
- Persistent drift dismissal (localStorage-backed)
- Source vs Project direct comparison option

---

## Architecture Overview

### Implementation Strategy

**Progressive Enhancement Approach**:

1. **Phase 1**: Enhance Deploy flow with pre-conflict check and diff integration
2. **Phase 2**: Enhance Push flow with solid banner, confirmation, and diff integration
3. **Phase 3**: Unify patterns into shared hooks/utilities, add Source vs Project comparison
4. **Phase 4**: Polish, testing, and persistent drift dismissal

**No Backend Changes Required**: All APIs exist and are production-ready:
- `POST /artifacts/{id}/sync` - Supports both directions with strategy parameter
- `POST /artifacts/{id}/deploy` - Supports overwrite flag
- `GET /artifacts/{id}/diff` - Returns project diff
- `GET /artifacts/{id}/upstream-diff` - Returns upstream diff

### Data Flow Pattern (Target State)

```
User clicks sync action (Deploy/Push/Pull)
  |
  v
Pre-operation diff check (API call)
  |
  v
[If changes exist]
  |
  +---> Show Diff Viewer in confirmation dialog
  |       - Display file changes
  |       - Show resolution options (Overwrite/Merge/Cancel)
  |
  v
User confirms strategy
  |
  v
Execute operation (API call)
  |
  v
Cache invalidation (TanStack Query)
  |
  v
Toast notification + UI update
```

### Component Architecture

```
SyncStatusTab (orchestrator)
  |
  +-- ArtifactFlowBanner (visualization)
  |     +-- SourceNode, CollectionNode, ProjectNode
  |     +-- ConnectorWithAction (x3)
  |
  +-- ComparisonSelector
  +-- DriftAlertBanner
  +-- DiffViewer
  +-- SyncActionsFooter
  |
  +-- ConflictAwareDeployDialog (NEW)
  +-- ConflictAwarePushDialog (NEW)
  +-- SyncDialog (existing, for merge workflow)
```

---

## Phase Breakdown

### Phase 1: Conflict-Aware Deploy Dialog

**Duration**: 3-4 days

**Dependencies**: None (all backend APIs ready)

**Assigned Subagent(s)**: ui-engineer-enhanced (primary)

**Goal**: Before deploying Collection -> Project, check for conflicts. If project has local changes, show diff and ask user to confirm overwrite OR open merge workflow.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| SYNC-001 | Create ConflictAwareDeployDialog | New dialog component with diff preview | Dialog fetches diff before showing, displays DiffViewer, has Overwrite/Merge/Cancel buttons | 2 pts | ui-engineer-enhanced | None |
| SYNC-002 | Add usePreDeployCheck hook | Hook to check for conflicts before deploy | Returns { hasConflicts, diffData, isLoading } for given artifact+project | 1 pt | ui-engineer-enhanced | None |
| SYNC-003 | Integrate with SyncStatusTab | Replace direct deployMutation.mutate() with dialog flow | Deploy button opens ConflictAwareDeployDialog instead of direct mutation | 1 pt | ui-engineer-enhanced | SYNC-001, SYNC-002 |
| SYNC-004 | Handle no-conflict fast path | Skip dialog when no changes detected | If diff shows no changes, proceed directly with deploy | 0.5 pts | ui-engineer-enhanced | SYNC-003 |
| SYNC-005 | Connect to Merge Workflow | "Merge" button opens existing SyncDialog | Clicking Merge in ConflictAwareDeployDialog opens SyncDialog with proper context | 0.5 pts | ui-engineer-enhanced | SYNC-001 |
| SYNC-006 | Unit tests for dialog and hook | Jest tests for ConflictAwareDeployDialog and usePreDeployCheck | Tests cover loading, diff display, button actions, error states | 1.5 pts | ui-engineer-enhanced | SYNC-001, SYNC-002 |

**Phase 1 Subtotal**: 6.5 story points

**Phase 1 Quality Gates**:
- [ ] ConflictAwareDeployDialog renders with proper loading skeleton
- [ ] DiffViewer correctly displays project vs collection changes
- [ ] Overwrite button triggers deploy with overwrite=true
- [ ] Merge button opens SyncDialog
- [ ] Cancel button closes dialog without action
- [ ] No-conflict path skips dialog and deploys directly
- [ ] Unit tests pass with >85% coverage
- [ ] No TypeScript errors

---

### Phase 2: Conflict-Aware Push Enhancement

**Duration**: 3-4 days

**Dependencies**: Phase 1 patterns established

**Assigned Subagent(s)**: ui-engineer-enhanced (primary)

**Goal**: Make Push (Project -> Collection) a first-class citizen with solid arrow visualization, proper confirmation dialog, and pre-conflict checking.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| SYNC-007 | Update banner arrow styling | Make Project->Collection arrow solid when deployment exists | Arrow is solid (not dashed) when projectInfo is present and has changes | 0.5 pts | ui-engineer-enhanced | None |
| SYNC-008 | Create ConflictAwarePushDialog | Dialog with diff preview for push operations | Similar to deploy dialog but for push direction, shows collection vs project diff | 2 pts | ui-engineer-enhanced | SYNC-001 pattern |
| SYNC-009 | Add usePrePushCheck hook | Hook to check if collection has upstream changes not in project | Returns { hasUpstreamChanges, diffData, isLoading } | 1 pt | ui-engineer-enhanced | None |
| SYNC-010 | Integrate with SyncStatusTab | Replace direct pushToCollectionMutation.mutate() | Push button opens ConflictAwarePushDialog, handles all strategies | 1 pt | ui-engineer-enhanced | SYNC-008, SYNC-009 |
| SYNC-011 | Add action button to banner connector | Optional inline action on Project->Collection connector | Small button on connector arrow for quick push action | 0.5 pts | ui-engineer-enhanced | SYNC-007 |
| SYNC-012 | Unit tests for push dialog and hook | Jest tests for ConflictAwarePushDialog and usePrePushCheck | Tests cover all user paths and edge cases | 1 pt | ui-engineer-enhanced | SYNC-008, SYNC-009 |

**Phase 2 Subtotal**: 6 story points

**Phase 2 Quality Gates**:
- [ ] Push arrow is solid when project deployment exists with changes
- [ ] ConflictAwarePushDialog shows correct diff direction (project -> collection)
- [ ] Push operation uses correct API parameters (strategy: 'theirs')
- [ ] Inline action button triggers push flow
- [ ] All confirmation dialogs have consistent UX with deploy dialog
- [ ] Unit tests pass with >85% coverage

---

### Phase 3: Unified Flow Integration & Source vs Project

**Duration**: 2-3 days

**Dependencies**: Phase 1 and 2 complete

**Assigned Subagent(s)**: ui-engineer-enhanced (primary)

**Goal**: Extract shared patterns, add Source vs Project direct comparison, ensure all three flows use consistent UX.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| SYNC-013 | Extract shared useConflictCheck pattern | Refactor hooks into shared utility | Single hook with direction parameter handles deploy/push/pull checks | 1 pt | ui-engineer-enhanced | SYNC-002, SYNC-009 |
| SYNC-014 | Create SyncConfirmationDialog base | Shared dialog component for all sync confirmations | Composable dialog accepting diff data, direction, and action handlers | 1 pt | ui-engineer-enhanced | SYNC-001, SYNC-008 |
| SYNC-015 | Add Source vs Project comparison | New comparison scope in ComparisonSelector | "Source vs Project" option available, fetches combined diff data | 1.5 pts | ui-engineer-enhanced | None |
| SYNC-016 | Implement source-vs-project diff API call | Query that combines upstream and project data | New TanStack Query that fetches both diffs and computes transitive changes | 1 pt | ui-engineer-enhanced | SYNC-015 |
| SYNC-017 | Update DiffViewer for all scopes | Ensure DiffViewer handles all three comparison types | Labels and content correct for all comparison scopes | 0.5 pts | ui-engineer-enhanced | SYNC-015 |

**Phase 3 Subtotal**: 5 pts

**Phase 3 Quality Gates**:
- [ ] All three sync directions use consistent hook and dialog patterns
- [ ] Source vs Project comparison shows transitive changes
- [ ] ComparisonSelector enables all valid combinations
- [ ] DiffViewer displays correct labels for each scope
- [ ] Code duplication reduced by >60%

---

### Phase 4: Polish, Testing & Persistent Drift

**Duration**: 2-3 days

**Dependencies**: Phase 3 complete

**Assigned Subagent(s)**: ui-engineer-enhanced (primary), code-reviewer (final validation)

**Goal**: Add persistent drift dismissal, comprehensive E2E tests, accessibility audit, and documentation.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| SYNC-018 | Implement persistent drift dismissal | Store dismissed drift alerts in localStorage | Dismissed alerts persist across sessions, can be reset | 1 pt | ui-engineer-enhanced | None |
| SYNC-019 | E2E test: Deploy with conflicts | Playwright test for deploy flow | Test shows diff, user confirms overwrite, deploy succeeds | 0.75 pts | ui-engineer-enhanced | SYNC-003 |
| SYNC-020 | E2E test: Push with conflicts | Playwright test for push flow | Test shows diff, user confirms push, collection updated | 0.75 pts | ui-engineer-enhanced | SYNC-010 |
| SYNC-021 | E2E test: Full sync cycle | Playwright test for complete workflow | Pull -> Modify -> Push -> Deploy cycle works end-to-end | 1 pt | ui-engineer-enhanced | All |
| SYNC-022 | Accessibility audit | axe-core audit for all new dialogs | Zero accessibility violations, proper focus management | 0.5 pts | ui-engineer-enhanced | All dialogs |
| SYNC-023 | Performance optimization | Ensure dialogs render <100ms | Profile and optimize diff viewer rendering for large diffs | 0.5 pts | ui-engineer-enhanced | All |
| SYNC-024 | Documentation and code comments | JSDoc for all new functions and components | All public APIs documented with examples | 0.5 pts | ui-engineer-enhanced | All |
| SYNC-025 | Code review and merge | Final review and merge to main | Code reviewed, no blocking comments, merged | 0.5 pts | code-reviewer | All |

**Phase 4 Subtotal**: 5.5 pts

**Phase 4 Quality Gates**:
- [ ] Drift dismissal persists across browser sessions
- [ ] All E2E tests pass in CI
- [ ] Zero axe-core accessibility violations
- [ ] Dialogs render in <100ms
- [ ] All code documented with JSDoc
- [ ] Code review complete

---

## Implementation Detail

### File Changes Summary

**New Files Created**:

1. **`skillmeat/web/components/sync-status/conflict-aware-deploy-dialog.tsx`** (~250 LOC)
   - Dialog component with integrated DiffViewer
   - Overwrite/Merge/Cancel actions
   - Loading and error states

2. **`skillmeat/web/components/sync-status/conflict-aware-push-dialog.tsx`** (~250 LOC)
   - Similar structure to deploy dialog
   - Push-specific messaging and actions

3. **`skillmeat/web/components/sync-status/sync-confirmation-dialog.tsx`** (~200 LOC)
   - Shared base dialog for Phase 3 consolidation
   - Configurable for any sync direction

4. **`skillmeat/web/hooks/use-pre-deploy-check.ts`** (~60 LOC)
   - TanStack Query hook for deploy conflict detection

5. **`skillmeat/web/hooks/use-pre-push-check.ts`** (~60 LOC)
   - TanStack Query hook for push conflict detection

6. **`skillmeat/web/hooks/use-conflict-check.ts`** (~100 LOC)
   - Unified hook (Phase 3) with direction parameter

7. **`skillmeat/web/__tests__/conflict-aware-deploy-dialog.test.tsx`** (~200 LOC)

8. **`skillmeat/web/__tests__/conflict-aware-push-dialog.test.tsx`** (~200 LOC)

9. **`skillmeat/web/tests/sync-workflow.e2e.ts`** (~300 LOC)

**Modified Files**:

1. **`skillmeat/web/components/sync-status/sync-status-tab.tsx`** (+80 LOC)
   - Import and integrate new dialogs
   - Add dialog state management
   - Update button handlers to use dialogs

2. **`skillmeat/web/components/sync-status/artifact-flow-banner.tsx`** (+30 LOC)
   - Update Push arrow to be solid when applicable
   - Add inline action button to connector

3. **`skillmeat/web/components/sync-status/comparison-selector.tsx`** (+20 LOC)
   - Add Source vs Project option

4. **`skillmeat/web/components/sync-status/drift-alert-banner.tsx`** (+15 LOC)
   - Support persistent dismissal via prop callback

5. **`skillmeat/web/hooks/index.ts`** (+5 LOC)
   - Export new hooks

**Total New Code**: ~1,620 LOC
**Total Modified**: ~150 LOC

---

### Component Specifications

#### ConflictAwareDeployDialog

**Location**: `skillmeat/web/components/sync-status/conflict-aware-deploy-dialog.tsx`

**Props Interface**:

```typescript
export interface ConflictAwareDeployDialogProps {
  artifact: Artifact;
  projectPath: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  onMergeRequested?: () => void;
}
```

**Internal State**:

```typescript
const [isDeploying, setIsDeploying] = useState(false);

// Fetch diff data
const { data: diffData, isLoading: isDiffLoading } = usePreDeployCheck(
  artifact.id,
  projectPath,
  { enabled: open }
);
```

**Rendering Structure**:

```tsx
<Dialog open={open} onOpenChange={onOpenChange}>
  <DialogContent className="max-w-4xl max-h-[80vh]">
    <DialogHeader>
      <DialogTitle>Deploy to Project</DialogTitle>
      <DialogDescription>
        Review changes before deploying {artifact.name} to project
      </DialogDescription>
    </DialogHeader>

    {isDiffLoading ? (
      <Skeleton className="h-64" />
    ) : diffData?.has_changes ? (
      <div className="flex flex-col gap-4">
        <Alert variant="warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            The project has local modifications that will be overwritten.
          </AlertDescription>
        </Alert>
        <div className="max-h-96 overflow-auto border rounded">
          <DiffViewer
            files={diffData.files}
            leftLabel="Collection"
            rightLabel="Project"
          />
        </div>
      </div>
    ) : (
      <Alert>
        <CheckCircle className="h-4 w-4" />
        <AlertDescription>
          No conflicts detected. Safe to deploy.
        </AlertDescription>
      </Alert>
    )}

    <DialogFooter className="gap-2">
      <Button variant="outline" onClick={() => onOpenChange(false)}>
        Cancel
      </Button>
      {diffData?.has_changes && (
        <Button variant="secondary" onClick={onMergeRequested}>
          <GitMerge className="mr-2 h-4 w-4" />
          Merge Changes
        </Button>
      )}
      <Button onClick={handleDeploy} disabled={isDeploying}>
        {isDeploying ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Deploying...
          </>
        ) : diffData?.has_changes ? (
          'Overwrite & Deploy'
        ) : (
          'Deploy'
        )}
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

#### usePreDeployCheck Hook

**Location**: `skillmeat/web/hooks/use-pre-deploy-check.ts`

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiRequest } from '@/lib/api';
import type { ArtifactDiffResponse } from '@/sdk/models/ArtifactDiffResponse';

interface UsePreDeployCheckOptions {
  enabled?: boolean;
}

export function usePreDeployCheck(
  artifactId: string,
  projectPath: string,
  options: UsePreDeployCheckOptions = {}
) {
  return useQuery<ArtifactDiffResponse>({
    queryKey: ['pre-deploy-check', artifactId, projectPath],
    queryFn: async () => {
      const params = new URLSearchParams({ project_path: projectPath });
      return await apiRequest<ArtifactDiffResponse>(
        `/artifacts/${encodeURIComponent(artifactId)}/diff?${params}`
      );
    },
    enabled: options.enabled ?? true,
    staleTime: 30 * 1000, // 30 seconds - interactive operation
    gcTime: 60 * 1000,
  });
}
```

#### ArtifactFlowBanner Update (Solid Arrow)

**Location**: `skillmeat/web/components/sync-status/artifact-flow-banner.tsx`

**Change in Connector 3 SVG** (around line 250):

```tsx
{/* CONNECTOR 3: Project -> Collection */}
<div className="flex flex-1 flex-col items-center gap-2">
  <svg width="100%" height="40" className="overflow-visible">
    <path
      d={`M 10 20 Q ${50} 20, ${90} 20`}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      // CHANGE: Only dashed if no project OR no changes to push
      strokeDasharray={projectInfo?.isModified ? undefined : '4 4'}
      className={projectInfo?.isModified ? 'text-muted-foreground' : 'text-muted'}
    />
    {/* Arrow head pointing left */}
    <path
      d={`M ${5} 15 L ${10} 20 L ${5} 25`}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className={projectInfo?.isModified ? 'text-muted-foreground' : 'text-muted'}
    />
  </svg>
  <Button
    size="sm"
    // CHANGE: Use default variant when there are changes to push
    variant={projectInfo?.isModified ? 'default' : 'ghost'}
    onClick={onPushToCollection}
    disabled={!projectInfo || isPushing}
    className="h-7 text-xs"
    title={!projectInfo ? 'No project deployment found' : 'Push local changes back to collection'}
  >
    {isPushing ? (
      <>
        <Loader2 className="mr-1 h-3 w-3 animate-spin" />
        Pushing...
      </>
    ) : (
      <>
        <ArrowRight className="mr-1 h-3 w-3 rotate-180" />
        Push to Collection
      </>
    )}
  </Button>
</div>
```

#### Persistent Drift Dismissal

**Location**: `skillmeat/web/components/sync-status/sync-status-tab.tsx`

**Implementation**:

```typescript
// Storage key format: skillmeat:drift-dismissed:{artifactId}:{scope}
const DRIFT_STORAGE_PREFIX = 'skillmeat:drift-dismissed:';

function getDismissedDriftKey(artifactId: string, scope: ComparisonScope): string {
  return `${DRIFT_STORAGE_PREFIX}${artifactId}:${scope}`;
}

function isDriftDismissed(artifactId: string, scope: ComparisonScope): boolean {
  if (typeof window === 'undefined') return false;
  const key = getDismissedDriftKey(artifactId, scope);
  const stored = localStorage.getItem(key);
  if (!stored) return false;

  // Dismissal expires after 24 hours
  const { timestamp } = JSON.parse(stored);
  const isExpired = Date.now() - timestamp > 24 * 60 * 60 * 1000;
  if (isExpired) {
    localStorage.removeItem(key);
    return false;
  }
  return true;
}

function dismissDrift(artifactId: string, scope: ComparisonScope): void {
  if (typeof window === 'undefined') return;
  const key = getDismissedDriftKey(artifactId, scope);
  localStorage.setItem(key, JSON.stringify({ timestamp: Date.now() }));
}

// In component:
const [localDismissed, setLocalDismissed] = useState(() =>
  isDriftDismissed(entity.id, comparisonScope)
);

const handleKeepLocal = useCallback(() => {
  dismissDrift(entity.id, comparisonScope);
  setLocalDismissed(true);
  toast({
    title: 'Local Version Kept',
    description: 'Drift dismissed for 24 hours',
  });
}, [entity.id, comparisonScope, toast]);
```

---

## Orchestration & Task Sequencing

### Execution Strategy

**Track Selected**: Standard Track (Haiku + Sonnet agents)

**Parallelization Strategy**:

```
Phase 1: Sequential with parallel tests
  |
  +-- SYNC-001: ConflictAwareDeployDialog (2h)
  +-- SYNC-002: usePreDeployCheck hook (1h) [PARALLEL with SYNC-001]
  |
  +-- SYNC-003: Integrate with SyncStatusTab (1h)
  |     Depends on SYNC-001, SYNC-002
  |
  +-- SYNC-004: No-conflict fast path (0.5h)
  +-- SYNC-005: Connect to Merge Workflow (0.5h)
  |     Depends on SYNC-003
  |
  +-- SYNC-006: Unit tests (1.5h)
        Depends on SYNC-001, SYNC-002

Phase 2: Can start after Phase 1 patterns established
  |
  +-- SYNC-007: Banner arrow styling (0.5h)
  +-- SYNC-008: ConflictAwarePushDialog (2h) [Uses SYNC-001 pattern]
  +-- SYNC-009: usePrePushCheck hook (1h) [PARALLEL with SYNC-008]
  |
  +-- SYNC-010: Integrate with SyncStatusTab (1h)
  +-- SYNC-011: Inline action button (0.5h)
  +-- SYNC-012: Unit tests (1h)

Phase 3: Consolidation after Phase 1 & 2
  |
  +-- SYNC-013: Extract shared hook (1h)
  +-- SYNC-014: Shared dialog base (1h) [PARALLEL with SYNC-013]
  |
  +-- SYNC-015: Source vs Project option (1.5h)
  +-- SYNC-016: Combined diff API (1h)
  +-- SYNC-017: DiffViewer updates (0.5h)

Phase 4: Polish and finalization
  |
  +-- SYNC-018: Persistent drift (1h)
  +-- SYNC-019-021: E2E tests (2.5h)
  +-- SYNC-022-024: Audit, perf, docs (1.5h)
  +-- SYNC-025: Code review (0.5h)
```

### Orchestration Quick Reference

**Phase 1 Delegation Commands**:

```text
# SYNC-001 + SYNC-002: Create dialog and hook in parallel
Task("ui-engineer-enhanced", "SYNC-001: Create ConflictAwareDeployDialog
  Location: skillmeat/web/components/sync-status/conflict-aware-deploy-dialog.tsx
  Props: artifact, projectPath, open, onOpenChange, onSuccess, onMergeRequested
  Features:
  - Fetch diff using usePreDeployCheck hook
  - Show DiffViewer when has_changes=true
  - Overwrite button calls deploy with overwrite=true
  - Merge button calls onMergeRequested callback
  - Loading skeleton while fetching diff
  - Error state handling")

Task("ui-engineer-enhanced", "SYNC-002: Create usePreDeployCheck hook
  Location: skillmeat/web/hooks/use-pre-deploy-check.ts
  Uses TanStack Query useQuery
  Fetches: GET /artifacts/{id}/diff?project_path=...
  Returns: ArtifactDiffResponse with has_changes, files, summary
  Stale time: 30 seconds (interactive operation)
  Export from hooks/index.ts")

# SYNC-003: Integration
Task("ui-engineer-enhanced", "SYNC-003: Integrate ConflictAwareDeployDialog with SyncStatusTab
  File: skillmeat/web/components/sync-status/sync-status-tab.tsx
  Changes:
  - Add state: showDeployDialog
  - Replace handleDeployToProject to open dialog instead of direct mutation
  - Pass artifact, projectPath, handlers to dialog
  - Handle onSuccess to close dialog and show toast
  - Handle onMergeRequested to open SyncDialog")
```

**Phase 2 Delegation Commands**:

```text
# SYNC-007: Banner styling update
Task("ui-engineer-enhanced", "SYNC-007: Update ArtifactFlowBanner arrow styling
  File: skillmeat/web/components/sync-status/artifact-flow-banner.tsx
  Changes:
  - Connector 3 (Project->Collection) should be solid when projectInfo?.isModified=true
  - Update strokeDasharray condition
  - Change button variant to 'default' when changes exist")

# SYNC-008 + SYNC-009: Push dialog and hook
Task("ui-engineer-enhanced", "SYNC-008: Create ConflictAwarePushDialog
  Location: skillmeat/web/components/sync-status/conflict-aware-push-dialog.tsx
  Similar to ConflictAwareDeployDialog but:
  - Different messaging (pushing project changes to collection)
  - Check for upstream changes in collection not in project
  - Uses usePrePushCheck hook
  - Diff labels: Project (left) vs Collection (right)")
```

---

## Testing Strategy

### Unit Tests

**Hook Tests** (`__tests__/use-pre-deploy-check.test.ts`):

```typescript
describe('usePreDeployCheck', () => {
  it('fetches diff data for artifact and project', async () => {
    mockApiRequest.mockResolvedValueOnce({
      has_changes: true,
      files: [{ file_path: 'SKILL.md', status: 'modified' }],
    });

    const { result, waitFor } = renderHook(
      () => usePreDeployCheck('artifact-123', '/path/to/project'),
      { wrapper }
    );

    await waitFor(() => result.current.isSuccess);

    expect(mockApiRequest).toHaveBeenCalledWith(
      '/artifacts/artifact-123/diff?project_path=/path/to/project'
    );
    expect(result.current.data?.has_changes).toBe(true);
  });

  it('respects enabled option', () => {
    renderHook(
      () => usePreDeployCheck('artifact-123', '/path', { enabled: false }),
      { wrapper }
    );

    expect(mockApiRequest).not.toHaveBeenCalled();
  });
});
```

**Component Tests** (`__tests__/conflict-aware-deploy-dialog.test.tsx`):

```typescript
describe('ConflictAwareDeployDialog', () => {
  it('shows loading skeleton while fetching diff', () => {
    mockUsePreDeployCheck.mockReturnValue({ isLoading: true, data: null });

    const { container } = render(
      <ConflictAwareDeployDialog {...defaultProps} open />
    );

    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('shows diff viewer when conflicts exist', async () => {
    mockUsePreDeployCheck.mockReturnValue({
      isLoading: false,
      data: {
        has_changes: true,
        files: [{ file_path: 'test.md', status: 'modified', unified_diff: '...' }],
      },
    });

    const { getByText } = render(
      <ConflictAwareDeployDialog {...defaultProps} open />
    );

    expect(getByText(/local modifications that will be overwritten/i)).toBeInTheDocument();
    expect(getByText('Overwrite & Deploy')).toBeInTheDocument();
    expect(getByText('Merge Changes')).toBeInTheDocument();
  });

  it('shows safe to deploy when no conflicts', () => {
    mockUsePreDeployCheck.mockReturnValue({
      isLoading: false,
      data: { has_changes: false, files: [] },
    });

    const { getByText } = render(
      <ConflictAwareDeployDialog {...defaultProps} open />
    );

    expect(getByText(/No conflicts detected/i)).toBeInTheDocument();
    expect(getByText('Deploy')).toBeInTheDocument();
  });

  it('calls onMergeRequested when Merge button clicked', async () => {
    const onMergeRequested = jest.fn();
    mockUsePreDeployCheck.mockReturnValue({
      isLoading: false,
      data: { has_changes: true, files: [] },
    });

    const { getByText } = render(
      <ConflictAwareDeployDialog {...defaultProps} open onMergeRequested={onMergeRequested} />
    );

    await userEvent.click(getByText('Merge Changes'));
    expect(onMergeRequested).toHaveBeenCalled();
  });
});
```

### E2E Tests

**Deploy Flow E2E** (`tests/sync-workflow.e2e.ts`):

```typescript
test('deploy with conflicts shows diff and allows overwrite', async ({ page }) => {
  // Setup: artifact with local project modifications
  await page.goto('/collection/default/artifact/test-skill');
  await page.click('button:has-text("Sync Status")');

  // Click deploy button
  await page.click('button:has-text("Deploy to Project")');

  // Verify dialog opens with diff
  await expect(page.locator('text=Review changes before deploying')).toBeVisible();
  await expect(page.locator('text=local modifications')).toBeVisible();

  // Click overwrite
  await page.click('button:has-text("Overwrite & Deploy")');

  // Verify success
  await expect(page.locator('text=Deploy Successful')).toBeVisible();
});

test('deploy without conflicts proceeds directly', async ({ page }) => {
  // Setup: artifact with no local modifications
  await page.goto('/collection/default/artifact/synced-skill');
  await page.click('button:has-text("Sync Status")');

  await page.click('button:has-text("Deploy to Project")');

  // Should show "safe to deploy"
  await expect(page.locator('text=No conflicts detected')).toBeVisible();

  await page.click('button:has-text("Deploy")');
  await expect(page.locator('text=Deploy Successful')).toBeVisible();
});
```

---

## Risk Assessment & Mitigation

### High-Risk Areas

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Large diffs slow down dialog | Poor UX, user abandons operation | Medium | Implement virtualized diff viewer for >1000 lines, add "Show First N Files" option |
| Race condition between check and execute | Stale data, unexpected overwrite | Low | Use short stale time (30s), refetch on dialog open |
| User confusion about directions | Wrong data overwritten | Medium | Clear labeling (Collection -> Project), visual arrows, confirmation text |

### Medium-Risk Areas

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| localStorage quota exceeded | Drift dismissal fails silently | Low | Limit stored keys, expire after 24h |
| Mobile layout breaks | Dialog unusable on small screens | Medium | Test responsive design, max-width constraints |
| Cache invalidation incomplete | Stale UI after operation | Low | Invalidate broadly, test cache behavior |

---

## Success Metrics

### Quantitative

- **Conflict Detection Rate**: 100% of operations with conflicts show diff before execution
- **User Confirmation Rate**: >90% of users who see conflict dialog complete the operation
- **Performance**: Dialog renders in <200ms including diff fetch
- **Test Coverage**: >85% code coverage for new components

### Qualitative

- **User Clarity**: Users understand what will happen before confirming
- **Consistent UX**: All three sync directions feel similar to use
- **Error Recovery**: Failed operations provide clear next steps

---

## Dependencies & Assumptions

### Hard Dependencies

- Backend APIs: `/artifacts/{id}/diff`, `/artifacts/{id}/upstream-diff`, `/artifacts/{id}/deploy`, `/artifacts/{id}/sync` (all implemented)
- TanStack React Query v5+ (available)
- shadcn Dialog components (available)
- DiffViewer component (exists, functional)

### Assumptions

1. Backend diff APIs return consistent format
2. Overwrite operations are idempotent
3. Users understand collection vs project distinction
4. localStorage is available in all target browsers

### Known Limitations

1. No real-time merge editor (relies on existing SyncDialog)
2. Source vs Project comparison requires two API calls
3. Drift dismissal does not sync across devices/browsers

---

## Timeline Summary

| Phase | Duration | Story Points | Key Deliverables |
|-------|----------|--------------|------------------|
| Phase 1 | 3-4 days | 6.5 pts | Conflict-aware Deploy dialog with diff preview |
| Phase 2 | 3-4 days | 6 pts | Conflict-aware Push dialog, solid banner arrow |
| Phase 3 | 2-3 days | 5 pts | Unified patterns, Source vs Project comparison |
| Phase 4 | 2-3 days | 5.5 pts | Persistent drift, E2E tests, polish |
| **Total** | **10-14 days** | **23 pts** | Complete unified sync workflow |

---

**Document Version**: 1.0

**Created**: 2025-02-04

**Status**: Ready for Implementation

**Next Steps**: Execute Phase 1 task delegation with ui-engineer-enhanced agent
