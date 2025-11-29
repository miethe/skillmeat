# Phase 4 Progress: Polish & Action Wiring

**Status:** PENDING
**Last Updated:** 2025-11-29
**Completion:** 0% (0 of 2 tasks)
**Total Effort:** ~150 lines of polish code
**Priority:** Medium

**Related Documents:**
- PRD: `/docs/project_plans/PRDs/enhancements/artifact-flow-modal-redesign.md`
- Implementation Plan: `/docs/project_plans/artifact-flow-modal/artifact-flow-modal-implementation-plan.md`
- Phase 1 Progress: `.claude/progress/artifact-flow-modal-redesign/phase-1-progress.md`
- Phase 2 Progress: `.claude/progress/artifact-flow-modal-redesign/phase-2-progress.md`
- Phase 3 Progress: `.claude/progress/artifact-flow-modal-redesign/phase-3-progress.md`

**Subagent Assignments:**
- **TASK-4.1:** ui-engineer-enhanced
- **TASK-4.2:** ui-engineer-enhanced

**Dependencies Map:**
- **TASK-4.1:** Depends on TASK-3.1 (integration must be complete)
- **TASK-4.2:** Depends on TASK-3.1 (integration must be complete)
- **TASK-4.1 and 4.2:** Can run in parallel (no dependencies between them)

---

## Phase Overview

**Phase Title:** Polish & Action Wiring

**Duration:** 1-2 hours
**Assigned Subagent(s):** ui-engineer-enhanced
**Code Domains:** Web

**Objective:** Complete the feature by wiring all action buttons to their corresponding API hooks, adding error handling and success notifications, and implementing "Coming Soon" states with tooltips for unimplemented features.

**Polish Areas:**
```
Action Wiring
├── Pull from Source → useSync (upstream direction)
├── Deploy to Project → useDeploy
├── Sync from Collection → useSync (downstream direction)
├── Merge Conflicts → MergeWorkflow component integration
├── Resolve All → Batch conflict resolution
├── Apply → Execute pending actions queue
└── Cancel → Clear actions and close modal

Coming Soon States
├── Push to Collection → Tooltip: "Coming Soon: Push local changes"
├── Push Local Changes (footer) → Tooltip: "Coming Soon"
├── Rollback → Tooltip: "Coming Soon: Rollback to previous version"
└── Advanced Merge → Tooltip: "Coming in next release"
```

---

## Phase 4: Polish

### Sub-Task Breakdown

- **TASK-4.1:** Wire all action buttons to API hooks
- **TASK-4.2:** Add Coming Soon tooltips for unimplemented features

### Completion Checklist

#### TASK-4.1: Wire All Action Buttons

- [ ] **TASK-4.1: Wire all action buttons to API hooks** (High priority) ⏳
  - **Assigned To:** ui-engineer-enhanced
  - **Dependencies:** TASK-3.1 (integration complete)
  - **Files:**
    - `skillmeat/web/components/entity/sync-status/sync-status-tab.tsx`
    - `skillmeat/web/components/entity/sync-status/artifact-flow-banner.tsx`
    - `skillmeat/web/components/entity/sync-status/drift-alert-banner.tsx`
    - `skillmeat/web/components/entity/sync-status/sync-actions-footer.tsx`
  - **Size:** ~100 lines (hook integration + error handling)
  - **Acceptance Criteria:**
    - [ ] **Pull from Source** button wired:
      - [ ] Triggers `useSync` mutation with `direction: 'upstream'`
      - [ ] Shows loading spinner during operation
      - [ ] Success toast: "Successfully synced from upstream"
      - [ ] Error toast: "Failed to sync: {error.message}"
      - [ ] Refetches upstream diff query on success
      - [ ] Disables button during loading
      - [ ] Button location: ArtifactFlowBanner (Source → Collection connector)
    - [ ] **Deploy to Project** button wired:
      - [ ] Triggers `useDeploy` mutation with projectPath
      - [ ] Shows loading spinner during operation
      - [ ] Success toast: "Successfully deployed to project"
      - [ ] Error toast: "Failed to deploy: {error.message}"
      - [ ] Refetches project diff query on success
      - [ ] Validates projectPath exists before deploying
      - [ ] Disables button during loading
      - [ ] Button location: ArtifactFlowBanner (Collection → Project connector)
    - [ ] **Sync from Collection** button wired:
      - [ ] Triggers `useSync` mutation with `direction: 'downstream'`
      - [ ] Shows loading spinner during operation
      - [ ] Success toast: "Synced changes from collection"
      - [ ] Error toast: "Failed to sync: {error.message}"
      - [ ] Refetches project diff query on success
      - [ ] Disables button during loading
      - [ ] Button location: DriftAlertBanner "Pull Updates" action
    - [ ] **Merge Conflicts** button wired:
      - [ ] Opens existing `MergeWorkflow` component
      - [ ] Passes entity and diff data to workflow
      - [ ] Workflow closes on completion
      - [ ] Refetches diff query after merge
      - [ ] Button location: DriftAlertBanner (visible when conflicts exist)
    - [ ] **Resolve All** button wired:
      - [ ] Batch resolves all conflicts (auto-take upstream or local)
      - [ ] Confirmation dialog: "Resolve all conflicts by taking {source}?"
      - [ ] Shows progress during batch operation
      - [ ] Success toast: "Resolved {count} conflicts"
      - [ ] Error toast: "Failed to resolve conflicts: {error.message}"
      - [ ] Refetches diff query on success
      - [ ] Button location: DriftAlertBanner (visible when multiple conflicts)
    - [ ] **Apply** button wired:
      - [ ] Executes all pending actions in queue
      - [ ] Shows loading spinner: "Applying {count} actions..."
      - [ ] Executes actions sequentially (not parallel)
      - [ ] Stops on first error and displays which action failed
      - [ ] Success toast: "All actions applied successfully"
      - [ ] Error toast: "Failed at action {N}: {error.message}"
      - [ ] Clears pending actions queue on success
      - [ ] Closes modal on success
      - [ ] Button location: SyncActionsFooter
    - [ ] **Cancel** button wired:
      - [ ] Clears pending actions queue
      - [ ] Closes modal immediately
      - [ ] No confirmation needed (non-destructive)
      - [ ] Button location: SyncActionsFooter
    - [ ] **Error Handling:**
      - [ ] All mutations include onError handler
      - [ ] Error messages are user-friendly (not raw API errors)
      - [ ] Network errors show retry option
      - [ ] Validation errors show specific field issues
    - [ ] **Loading States:**
      - [ ] Buttons show spinner when mutation is loading
      - [ ] Button text changes during loading: "Pull from Source" → "Pulling..."
      - [ ] Buttons are disabled during loading
      - [ ] Other buttons remain enabled (can cancel)
    - [ ] **Success Feedback:**
      - [ ] Toast notifications for all successful operations
      - [ ] Toast auto-dismisses after 3 seconds
      - [ ] Toast includes success icon (checkmark)
      - [ ] Queries refetch to show updated data
    - [ ] **Query Invalidation:**
      - [ ] Pull from Source → invalidates `['upstream-diff', entity.id]`
      - [ ] Deploy to Project → invalidates `['project-diff', entity.id, projectPath]`
      - [ ] Sync from Collection → invalidates `['project-diff', entity.id, projectPath]`
      - [ ] Merge → invalidates all diff queries
    - [ ] **TypeScript:**
      - [ ] All hooks are properly typed
      - [ ] Mutation functions have correct parameter types
      - [ ] Error types are handled (not `any`)
  - **Dependencies:**
    - `hooks/useSync.ts`
    - `hooks/useDeploy.ts`
    - `components/entity/merge-workflow.tsx`
    - `hooks/use-toast.tsx`
    - React Query (useQueryClient for invalidation)
  - **Key Files:**
    - Modified: `sync-status-tab.tsx` (hook integration)
    - Modified: `artifact-flow-banner.tsx` (button handlers)
    - Modified: `drift-alert-banner.tsx` (button handlers)
    - Modified: `sync-actions-footer.tsx` (button handlers)
  - **Notes:**
    - All buttons should have consistent loading/error/success patterns
    - Use React Query's mutation states: `isLoading`, `isError`, `isSuccess`
    - Consider optimistic updates for better UX (optional)
    - Network errors should suggest checking connection
    - Validation errors should point to specific fields

#### TASK-4.2: Add Coming Soon Tooltips

- [ ] **TASK-4.2: Add Coming Soon tooltips for unimplemented features** (Medium priority) ⏳
  - **Assigned To:** ui-engineer-enhanced
  - **Dependencies:** TASK-3.1 (integration complete)
  - **Files:**
    - `skillmeat/web/components/entity/sync-status/artifact-flow-banner.tsx`
    - `skillmeat/web/components/entity/sync-status/sync-actions-footer.tsx`
  - **Size:** ~50 lines (tooltip components)
  - **Acceptance Criteria:**
    - [ ] **Push to Collection** button (ArtifactFlowBanner):
      - [ ] Button is visually disabled (ghost variant)
      - [ ] Tooltip on hover: "Coming Soon: Push local changes to collection"
      - [ ] Tooltip appears immediately on hover (no delay)
      - [ ] Tooltip has info icon (ⓘ) or clock icon
      - [ ] Button does NOT trigger action (onClick shows toast)
      - [ ] Toast message: "Coming Soon: Push local changes to collection"
      - [ ] Button location: Project → Collection connector (reverse direction)
    - [ ] **Push Local Changes** button (SyncActionsFooter):
      - [ ] Button is visually disabled (ghost variant)
      - [ ] Tooltip on hover: "Coming Soon"
      - [ ] Tooltip styling matches other tooltips
      - [ ] Button does NOT trigger action
      - [ ] Toast message: "Coming Soon: Push local changes to collection"
      - [ ] Button location: Footer left side
    - [ ] **Rollback** button (SyncActionsFooter - conditional):
      - [ ] Button is visually disabled (ghost variant)
      - [ ] Tooltip on hover: "Coming Soon: Rollback to previous version"
      - [ ] Only visible when entity has version history
      - [ ] Button does NOT trigger action
      - [ ] Toast message: "Coming Soon: Rollback feature"
      - [ ] Button location: Footer left side
    - [ ] **Advanced Merge** option (if added to MergeWorkflow):
      - [ ] Option is disabled in dropdown/menu
      - [ ] Tooltip: "Coming in next release"
      - [ ] Alternative: Not shown at all (preferred)
    - [ ] **Tooltip Component:**
      - [ ] Uses shadcn/ui Tooltip component
      - [ ] Tooltip background: dark gray (dark mode compatible)
      - [ ] Tooltip text: white, 12px font
      - [ ] Tooltip arrow points to button
      - [ ] Tooltip positioning: auto (avoids viewport edges)
      - [ ] Tooltip z-index higher than modal
    - [ ] **Visual Consistency:**
      - [ ] All Coming Soon buttons use same ghost button style
      - [ ] All tooltips use same background/text color
      - [ ] All tooltips have same animation (fade in)
      - [ ] Icon is consistent across Coming Soon buttons (clock or info icon)
    - [ ] **Accessibility:**
      - [ ] Tooltip is keyboard accessible (focus triggers tooltip)
      - [ ] Screen readers announce "Coming Soon" state
      - [ ] Buttons have `aria-disabled="true"`
      - [ ] Buttons have `aria-label` with Coming Soon info
    - [ ] **User Feedback:**
      - [ ] Clicking Coming Soon button shows toast (doesn't just do nothing)
      - [ ] Toast is informative: tells user what feature is coming
      - [ ] Toast includes estimated release (optional): "Coming Soon (v0.4)"
    - [ ] **Documentation:**
      - [ ] Add comment in code indicating feature is placeholder
      - [ ] Link to GitHub issue or PRD for feature (if exists)
      - [ ] Example:
        ```tsx
        {/* Coming Soon: Push to Collection feature
            Backend endpoint not yet implemented
            See: docs/project_plans/PRDs/enhancements/push-to-collection.md */}
        ```
  - **Dependencies:**
    - shadcn/ui Tooltip component
    - `hooks/use-toast.tsx`
  - **Key Files:**
    - Modified: `artifact-flow-banner.tsx` (Push to Collection button)
    - Modified: `sync-actions-footer.tsx` (Push Local Changes, Rollback buttons)
  - **Notes:**
    - Coming Soon tooltips should be non-intrusive but informative
    - Users should understand the feature exists but isn't ready yet
    - Avoid showing too many Coming Soon states (prioritize implemented features)
    - Consider hiding Coming Soon features entirely if too many unimplemented
    - Tooltip should not block user interaction with other elements

---

## Task Status Legend

- ⏳ **Pending:** Not started
- 🔄 **In Progress:** Currently being worked on
- ✅ **Completed:** Done and tested
- 🐛 **Blocked:** Waiting on dependencies
- ⚠️  **Needs Review:** Completed but review pending

---

## Component Size Estimates

| Task | Estimated Lines | Agent | Dependencies | Status |
|------|-----------------|-------|--------------|--------|
| Wire Actions | ~100 | ui-engineer-enhanced | TASK-3.1 | ⏳ |
| Coming Soon Tooltips | ~50 | ui-engineer-enhanced | TASK-3.1 | ⏳ |
| **Phase 4 Total** | **~150** | — | — | **0%** |

---

## Critical Dependencies

### Blocked By (Must Complete First)

**Phase 3:**
- ✗ TASK-3.1: Integration into unified-entity-modal.tsx

**Existing Hooks (Must Exist):**
- ✓ `hooks/useSync.ts`
- ✓ `hooks/useDeploy.ts`
- ✓ `hooks/use-toast.tsx`

**Existing Components (Must Exist):**
- ✓ `components/entity/merge-workflow.tsx`
- ✓ shadcn/ui Tooltip

### Blocks (None - Final Phase)

This is the final phase. No subsequent tasks are blocked by this phase.

---

## Action Wiring Specification

### Pull from Source

**Hook:** `useSync({ direction: 'upstream' })`

**Button Implementation:**
```tsx
const pullFromSource = useMutation({
  mutationFn: () => api.syncFromUpstream(entity.id),
  onSuccess: () => {
    toast.success('Successfully synced from upstream');
    queryClient.invalidateQueries(['upstream-diff', entity.id]);
  },
  onError: (error: Error) => {
    toast.error(`Failed to sync: ${error.message}`);
  },
});

<Button
  onClick={() => pullFromSource.mutate()}
  disabled={pullFromSource.isLoading}
>
  {pullFromSource.isLoading ? 'Pulling...' : 'Pull from Source'}
</Button>
```

### Deploy to Project

**Hook:** `useDeploy()`

**Button Implementation:**
```tsx
const deployToProject = useMutation({
  mutationFn: () => api.deployToProject(entity.id, projectPath!),
  onSuccess: () => {
    toast.success('Successfully deployed to project');
    queryClient.invalidateQueries(['project-diff', entity.id, projectPath]);
  },
  onError: (error: Error) => {
    toast.error(`Failed to deploy: ${error.message}`);
  },
});

<Button
  onClick={() => {
    if (!projectPath) {
      toast.error('No project path specified');
      return;
    }
    deployToProject.mutate();
  }}
  disabled={deployToProject.isLoading || !projectPath}
>
  {deployToProject.isLoading ? 'Deploying...' : 'Deploy to Project'}
</Button>
```

### Apply (Execute Pending Actions)

**Implementation:**
```tsx
const handleApply = async () => {
  setIsApplying(true);
  try {
    for (const [index, action] of pendingActions.entries()) {
      await executeAction(action);
      toast.info(`Completed action ${index + 1} of ${pendingActions.length}`);
    }
    toast.success('All actions applied successfully');
    setPendingActions([]);
    onClose();
  } catch (error) {
    const failedIndex = pendingActions.findIndex(a => !a.completed);
    toast.error(`Failed at action ${failedIndex + 1}: ${error.message}`);
  } finally {
    setIsApplying(false);
  }
};

<Button
  onClick={handleApply}
  disabled={isApplying || pendingActions.length === 0}
>
  {isApplying ? 'Applying...' : `Apply ${pendingActions.length} Actions`}
</Button>
```

---

## Coming Soon Tooltip Specification

### Tooltip Component

```tsx
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

<TooltipProvider>
  <Tooltip>
    <TooltipTrigger asChild>
      <Button
        variant="ghost"
        disabled
        onClick={() => toast.info('Coming Soon: Push local changes to collection')}
        aria-label="Push to Collection (Coming Soon)"
        aria-disabled="true"
      >
        Push to Collection
      </Button>
    </TooltipTrigger>
    <TooltipContent>
      <p>Coming Soon: Push local changes to collection</p>
    </TooltipContent>
  </Tooltip>
</TooltipProvider>
```

### Visual Styling

```tsx
// Ghost button variant for Coming Soon
<Button
  variant="ghost"
  className="text-muted-foreground cursor-not-allowed"
  disabled
>
  <Clock className="mr-2 h-4 w-4" />
  Push to Collection
</Button>

// Tooltip styling (via Tailwind)
<TooltipContent className="bg-gray-800 text-white text-xs">
  Coming Soon: Push local changes to collection
</TooltipContent>
```

---

## Testing Strategy

### Unit Tests

#### TASK-4.1 (Action Wiring)
- [ ] Pull from Source button triggers useSync mutation
- [ ] Deploy to Project button triggers useDeploy mutation
- [ ] Apply button executes pending actions in sequence
- [ ] Cancel button clears pending actions and closes modal
- [ ] Success toast appears on successful mutation
- [ ] Error toast appears on failed mutation
- [ ] Loading state disables button during mutation
- [ ] Query invalidation occurs on success

#### TASK-4.2 (Coming Soon Tooltips)
- [ ] Coming Soon buttons render as disabled
- [ ] Tooltip appears on hover
- [ ] Tooltip content is correct
- [ ] Clicking Coming Soon button shows toast
- [ ] Toast message is informative
- [ ] Buttons have correct aria attributes

### Integration Tests

- [ ] Pull from Source → Success → Upstream diff updates
- [ ] Deploy to Project → Success → Project diff updates
- [ ] Pull from Source → Error → Error toast shown
- [ ] Deploy to Project → Error → Error toast shown
- [ ] Apply with multiple actions → All execute → Modal closes
- [ ] Apply with error mid-sequence → Stops at error → Shows which failed
- [ ] Cancel → Pending actions cleared → Modal closes
- [ ] Coming Soon button click → Toast shown → No API call

### Manual Testing Checklist

- [ ] Click "Pull from Source" → API call triggers → Success toast → Diff updates
- [ ] Click "Deploy to Project" → API call triggers → Success toast → Diff updates
- [ ] Click "Merge Conflicts" → MergeWorkflow opens → Complete merge → Diff updates
- [ ] Click "Apply" with pending actions → All execute → Success toast → Modal closes
- [ ] Click "Cancel" → Modal closes immediately
- [ ] Hover over "Push to Collection" → Tooltip shows "Coming Soon"
- [ ] Click "Push to Collection" → Toast shows "Coming Soon"
- [ ] Hover over "Push Local Changes" → Tooltip shows "Coming Soon"
- [ ] Click "Push Local Changes" → Toast shows "Coming Soon"
- [ ] Test with slow network → Loading spinners appear → Buttons disabled
- [ ] Test with network error → Error toast with retry option
- [ ] Test with validation error → Specific error message shown
- [ ] Keyboard navigation → All tooltips keyboard accessible
- [ ] Screen reader → Coming Soon states announced

---

## Error Handling Patterns

### Network Errors

```tsx
onError: (error: Error) => {
  if (error.message.includes('network') || error.message.includes('fetch')) {
    toast.error('Network error. Please check your connection and try again.', {
      action: {
        label: 'Retry',
        onClick: () => mutation.mutate(),
      },
    });
  } else {
    toast.error(`Failed: ${error.message}`);
  }
}
```

### Validation Errors

```tsx
onError: (error: ApiError) => {
  if (error.status === 422) {
    const fieldErrors = error.body?.errors || [];
    const message = fieldErrors.map(e => `${e.field}: ${e.message}`).join(', ');
    toast.error(`Validation error: ${message}`);
  } else {
    toast.error(`Failed: ${error.message}`);
  }
}
```

### Authentication Errors

```tsx
onError: (error: ApiError) => {
  if (error.status === 401 || error.status === 403) {
    toast.error('Authentication required. Please log in and try again.');
    // Optionally redirect to login
  } else {
    toast.error(`Failed: ${error.message}`);
  }
}
```

---

## Success Criteria

- [ ] All action buttons trigger correct API calls
- [ ] Loading states display during operations
- [ ] Success toasts appear on successful operations
- [ ] Error toasts appear on failed operations with helpful messages
- [ ] Query invalidation refreshes UI with updated data
- [ ] Apply button executes all pending actions sequentially
- [ ] Cancel button clears actions and closes modal
- [ ] Coming Soon buttons show tooltips on hover
- [ ] Coming Soon tooltips have consistent styling
- [ ] Coming Soon buttons show toast on click
- [ ] All buttons are keyboard accessible
- [ ] Screen readers announce button states correctly
- [ ] Dark mode works for all new UI elements
- [ ] No console errors or warnings
- [ ] TypeScript compiles without errors

---

## Performance Optimization Checklist

- [ ] Mutation functions are memoized (useCallback)
- [ ] Toast notifications auto-dismiss (don't accumulate)
- [ ] Query invalidation is specific (not refetch all)
- [ ] Loading states are instant (no delay)
- [ ] Heavy components are code-split (lazy loaded)
- [ ] Tooltip rendering is lightweight (no heavy calculations)
- [ ] Button click handlers are debounced (if needed)

---

## Accessibility Checklist

- [ ] All buttons have clear labels
- [ ] Disabled buttons have aria-disabled="true"
- [ ] Coming Soon buttons have aria-label with context
- [ ] Tooltips are keyboard accessible (focus triggers)
- [ ] Toast notifications are announced by screen readers
- [ ] Loading states are announced ("Loading..." text or aria-live)
- [ ] Error messages are associated with relevant buttons
- [ ] Focus management on modal close (returns to trigger)

---

## Next Steps (Post-Phase 4)

**After Phase 4 completion, the feature is COMPLETE. Optional enhancements:**

1. **Performance Optimization:**
   - Add optimistic updates for faster perceived performance
   - Implement query prefetching for file previews
   - Code split DiffViewer and FilePreviewPane
   - Lazy load syntax highlighter

2. **Enhanced Error Handling:**
   - Add retry logic for transient network errors
   - Implement exponential backoff for repeated failures
   - Add offline detection and queue actions

3. **Advanced Features (Future):**
   - Implement "Push to Collection" backend endpoint
   - Add "Rollback to Version" functionality
   - Enhance conflict resolution with 3-way merge
   - Add real-time sync status updates (WebSocket)

4. **Analytics:**
   - Track action button usage
   - Monitor error rates by action type
   - Measure time-to-completion for sync operations
   - A/B test Coming Soon messaging

---

## Notes & Observations

- Action wiring is straightforward - mostly connecting existing hooks to buttons
- Coming Soon tooltips provide transparency about unimplemented features
- Error handling should be user-friendly and actionable (not raw errors)
- Loading states improve perceived performance during network operations
- Query invalidation ensures UI stays in sync with server state
- Apply button's sequential execution prevents race conditions
- Cancel button provides safe escape hatch (non-destructive)
- Tooltip accessibility is critical for keyboard users
- Toast notifications should auto-dismiss to avoid UI clutter
