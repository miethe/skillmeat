# Phase 2 Progress: SyncStatusTab Composite Component

**Status:** PENDING
**Last Updated:** 2025-11-29
**Completion:** 0% (0 of 1 tasks)
**Total Effort:** ~300 lines of component code
**Priority:** Medium

**Related Documents:**
- PRD: `/docs/project_plans/PRDs/enhancements/artifact-flow-modal-redesign.md`
- Implementation Plan: `/docs/project_plans/artifact-flow-modal/artifact-flow-modal-implementation-plan.md`
- Phase 1 Progress: `.claude/progress/artifact-flow-modal-redesign/phase-1-progress.md`

**Subagent Assignments:**
- **TASK-2.1:** ui-engineer-enhanced

**Dependencies Map:**
- **TASK-2.1:** Depends on TASK-1.1, 1.2, 1.3, 1.4, 1.5 (all Phase 1 components must be complete)
- **TASK-3.1:** Depends on TASK-2.1 (blocked until this phase completes)

---

## Phase Overview

**Phase Title:** SyncStatusTab Composite Component

**Duration:** 1-2 hours
**Assigned Subagent(s):** ui-engineer-enhanced
**Code Domains:** Web

**Objective:** Create the orchestrating parent component that brings together all 5 sub-components from Phase 1 into a complete 3-panel layout with state management, API integration, and event handling.

**Component Architecture:**
```
SyncStatusTab (orchestrator)
├── State Management
│   ├── Comparison scope (collection-vs-project, source-vs-collection, source-vs-project)
│   ├── Selected file path
│   └── Pending actions queue
├── Query Hooks
│   ├── useUpstreamDiff (source vs collection)
│   ├── useProjectDiff (collection vs project)
│   └── useFileContent (preview pane)
├── Mutation Hooks
│   ├── useSync (pull from source)
│   ├── useDeploy (deploy to project)
│   └── usePushToCollection (coming soon)
└── Layout Structure
    ├── ArtifactFlowBanner (top banner)
    ├── 3-Panel Main Content
    │   ├── FileTree (left, 240px)
    │   ├── Comparison + Diff (center, flex-1)
    │   │   ├── ComparisonSelector
    │   │   ├── DriftAlertBanner
    │   │   └── DiffViewer
    │   └── FilePreviewPane (right, 320px)
    └── SyncActionsFooter (bottom)
```

---

## Phase 2: Composite Component

### Sub-Task Breakdown

- **TASK-2.1:** Create SyncStatusTab orchestration component

### Completion Checklist

- [ ] **TASK-2.1: Create SyncStatusTab orchestration component** (High priority) ⏳
  - **Assigned To:** ui-engineer-enhanced
  - **Dependencies:** TASK-1.1, 1.2, 1.3, 1.4, 1.5 (all Phase 1 components)
  - **File:** `skillmeat/web/components/entity/sync-status/sync-status-tab.tsx`
  - **Size:** ~300 lines
  - **Acceptance Criteria:**
    - [ ] Component created with TypeScript/TSX
    - [ ] Imports all 5 Phase 1 components (ArtifactFlowBanner, ComparisonSelector, DriftAlertBanner, FilePreviewPane, SyncActionsFooter)
    - [ ] State management implemented:
      - [ ] `comparisonScope` state (ComparisonScope type)
      - [ ] `selectedFile` state (string | null)
      - [ ] `pendingActions` state (action queue)
    - [ ] Query hooks integrated:
      - [ ] `useQuery` for upstream diff data
      - [ ] `useQuery` for project diff data
      - [ ] `useQuery` for file content (conditional on selectedFile)
    - [ ] Mutation hooks integrated:
      - [ ] `useSync` for pull from source
      - [ ] `useDeploy` for deploy to project
      - [ ] `usePushToCollection` stub (Coming Soon)
    - [ ] Layout structure implemented:
      - [ ] Top: ArtifactFlowBanner with flow props
      - [ ] Main: 3-panel layout (FileTree | Comparison+Diff | Preview)
      - [ ] Bottom: SyncActionsFooter with action handlers
    - [ ] Event handlers implemented:
      - [ ] `handleComparisonChange` (updates scope, triggers new diff query)
      - [ ] `handleFileSelect` (updates selectedFile, triggers preview query)
      - [ ] `handlePullFromSource` (triggers sync mutation)
      - [ ] `handleDeployToProject` (triggers deploy mutation)
      - [ ] `handlePushToCollection` (shows Coming Soon toast)
      - [ ] `handleApply` (executes pending actions)
      - [ ] `handleCancel` (clears pending actions, closes modal)
    - [ ] Props interface defined:
      - [ ] `entity: Entity` (current artifact)
      - [ ] `mode: 'collection' | 'project'` (context)
      - [ ] `projectPath?: string` (if mode is project)
      - [ ] `onClose: () => void` (close modal callback)
    - [ ] Data flow wired correctly:
      - [ ] Entity data flows to ArtifactFlowBanner
      - [ ] Comparison scope flows to ComparisonSelector and DiffViewer
      - [ ] Selected file flows to FileTree and FilePreviewPane
      - [ ] Drift status computed from diff data flows to DriftAlertBanner
      - [ ] Action states flow to SyncActionsFooter
    - [ ] Loading states handled:
      - [ ] Show skeletons during query loading
      - [ ] Disable actions during mutations
      - [ ] Loading spinner on Apply button during mutation
    - [ ] Error states handled:
      - [ ] Display error alerts for failed queries
      - [ ] Toast notifications for failed mutations
      - [ ] Graceful degradation if upstream data unavailable
    - [ ] Responsive layout:
      - [ ] 3-panel layout on desktop (>1024px)
      - [ ] 2-panel layout on tablet (768-1024px, hide preview)
      - [ ] 1-panel layout on mobile (<768px, stack vertically)
    - [ ] Dark mode support via Tailwind classes
    - [ ] TypeScript types fully defined (no `any`)
  - **Dependencies:**
    - All Phase 1 components (ArtifactFlowBanner, ComparisonSelector, DriftAlertBanner, FilePreviewPane, SyncActionsFooter)
    - Existing components (FileTree, DiffViewer)
    - API hooks (useSync, useDeploy, useQuery)
    - Entity type from types/entity.ts
  - **Key Files:**
    - New: `skillmeat/web/components/entity/sync-status/sync-status-tab.tsx`
    - Import: All 5 Phase 1 components
    - Import: `components/entity/file-tree.tsx`
    - Import: `components/entity/diff-viewer.tsx`
    - Import: `hooks/useSync.ts`
    - Import: `hooks/useDeploy.ts`
    - Import: `types/entity.ts`
  - **Notes:**
    - This is the critical integration layer that makes Phase 1 components functional
    - State management should be simple (useState, no complex state machine needed)
    - Query keys should include entity.id and comparisonScope for proper caching
    - Mutation success should trigger query refetch to update UI
    - Coming Soon actions should show tooltip, not trigger mutation
    - File selection should debounce if performance issues arise
    - Consider code splitting for heavy components (DiffViewer, FilePreviewPane)

---

## Task Status Legend

- ⏳ **Pending:** Not started
- 🔄 **In Progress:** Currently being worked on
- ✅ **Completed:** Done and tested
- 🐛 **Blocked:** Waiting on dependencies
- ⚠️  **Needs Review:** Completed but review pending

---

## Component Size Estimates

| Component | Estimated Lines | Agent | Dependencies | Status |
|-----------|-----------------|-------|--------------|--------|
| SyncStatusTab | ~300 | ui-engineer-enhanced | TASK-1.1-1.5 | ⏳ |
| **Phase 2 Total** | **~300** | — | — | **0%** |

---

## Critical Dependencies

### Blocked By (Must Complete First)

**Phase 1 Components (All Required):**
- ✗ TASK-1.1: ArtifactFlowBanner
- ✗ TASK-1.2: ComparisonSelector
- ✗ TASK-1.3: DriftAlertBanner
- ✗ TASK-1.4: FilePreviewPane
- ✗ TASK-1.5: SyncActionsFooter

**Existing Components (Must Exist):**
- ✓ FileTree (`components/entity/file-tree.tsx`)
- ✓ DiffViewer (`components/entity/diff-viewer.tsx`)

**API Hooks (Must Exist):**
- ✓ useSync (`hooks/useSync.ts`)
- ✓ useDeploy (`hooks/useDeploy.ts`)

### Blocks (Waiting on This Phase)

- TASK-3.1: Integration into unified-entity-modal.tsx (Phase 3)
- TASK-4.1: Wire all action buttons (Phase 4)
- TASK-4.2: Add Coming Soon tooltips (Phase 4)

---

## State Management Design

### State Variables

```typescript
// Comparison state
const [comparisonScope, setComparisonScope] = useState<ComparisonScope>('collection-vs-project');
const [selectedFile, setSelectedFile] = useState<string | null>(null);

// Pending actions (for batch apply)
const [pendingActions, setPendingActions] = useState<PendingAction[]>([]);

// UI state
const [isApplying, setIsApplying] = useState(false);
```

### Query Hooks

```typescript
// Upstream diff (source vs collection)
const { data: upstreamDiff, isLoading: upstreamLoading } = useQuery({
  queryKey: ['upstream-diff', entity.id],
  queryFn: () => api.getUpstreamDiff(entity.id),
  enabled: comparisonScope === 'source-vs-collection',
});

// Project diff (collection vs project)
const { data: projectDiff, isLoading: projectLoading } = useQuery({
  queryKey: ['project-diff', entity.id, projectPath],
  queryFn: () => api.getProjectDiff(entity.id, projectPath),
  enabled: comparisonScope === 'collection-vs-project' && !!projectPath,
});

// File content for preview
const { data: fileContent, isLoading: contentLoading } = useQuery({
  queryKey: ['file-content', entity.id, selectedFile, tier],
  queryFn: () => api.getFileContent(entity.id, selectedFile, tier),
  enabled: !!selectedFile,
});
```

### Mutation Hooks

```typescript
// Pull from source
const pullFromSource = useMutation({
  mutationFn: () => api.syncFromUpstream(entity.id),
  onSuccess: () => {
    toast.success('Synced from upstream');
    queryClient.invalidateQueries(['upstream-diff', entity.id]);
  },
  onError: (error) => {
    toast.error(`Sync failed: ${error.message}`);
  },
});

// Deploy to project
const deployToProject = useMutation({
  mutationFn: () => api.deployToProject(entity.id, projectPath),
  onSuccess: () => {
    toast.success('Deployed to project');
    queryClient.invalidateQueries(['project-diff', entity.id]);
  },
  onError: (error) => {
    toast.error(`Deploy failed: ${error.message}`);
  },
});
```

---

## Layout Structure

### Grid Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      ArtifactFlowBanner (full width)                     │
├────────────┬───────────────────────────────────┬─────────────────────────┤
│            │     ComparisonSelector            │                         │
│  FileTree  ├───────────────────────────────────┤   FilePreviewPane       │
│  (240px)   │     DriftAlertBanner              │      (320px)            │
│            ├───────────────────────────────────┤                         │
│            │        DiffViewer                 │                         │
│            │        (flex-1)                   │                         │
├────────────┴───────────────────────────────────┴─────────────────────────┤
│                    SyncActionsFooter (full width)                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Tailwind Layout Classes

```tsx
<div className="flex flex-col h-full">
  {/* Top Banner */}
  <ArtifactFlowBanner {...} />

  {/* 3-Panel Main */}
  <div className="flex flex-1 overflow-hidden">
    {/* Left: File Tree */}
    <div className="w-60 border-r overflow-y-auto">
      <FileTree {...} />
    </div>

    {/* Center: Comparison + Diff */}
    <div className="flex-1 flex flex-col overflow-hidden">
      <ComparisonSelector {...} />
      <DriftAlertBanner {...} />
      <DiffViewer {...} />
    </div>

    {/* Right: Preview */}
    <div className="w-80 border-l overflow-y-auto">
      <FilePreviewPane {...} />
    </div>
  </div>

  {/* Bottom: Actions */}
  <SyncActionsFooter {...} />
</div>
```

---

## Data Flow Diagram

```
Entity (props)
    ↓
┌─────────────────────────────────────┐
│        SyncStatusTab                │
│  ┌──────────────────────────────┐   │
│  │  comparisonScope state       │   │
│  │  selectedFile state          │   │
│  │  pendingActions state        │   │
│  └──────────────────────────────┘   │
│                                      │
│  ┌──────────────────────────────┐   │
│  │  Query Hooks                 │   │
│  │  - useUpstreamDiff           │   │
│  │  - useProjectDiff            │   │
│  │  - useFileContent            │   │
│  └──────────────────────────────┘   │
│              ↓                       │
│  ┌──────────────────────────────┐   │
│  │  Derived Data                │   │
│  │  - currentDiff               │   │
│  │  - driftStatus               │   │
│  │  - previewContent            │   │
│  └──────────────────────────────┘   │
│              ↓                       │
│  ┌──────────────────────────────┐   │
│  │  Sub-Components              │   │
│  │  - ArtifactFlowBanner        │   │
│  │  - ComparisonSelector        │   │
│  │  - DriftAlertBanner          │   │
│  │  - FilePreviewPane           │   │
│  │  - SyncActionsFooter         │   │
│  └──────────────────────────────┘   │
│              ↑                       │
│  ┌──────────────────────────────┐   │
│  │  Event Handlers              │   │
│  │  - handleComparisonChange    │   │
│  │  - handleFileSelect          │   │
│  │  - handlePullFromSource      │   │
│  │  - handleDeployToProject     │   │
│  │  - handleApply               │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

---

## Event Handlers Specification

### handleComparisonChange

```typescript
const handleComparisonChange = (scope: ComparisonScope) => {
  setComparisonScope(scope);
  // Query hook will automatically refetch based on new scope
};
```

### handleFileSelect

```typescript
const handleFileSelect = (filePath: string | null) => {
  setSelectedFile(filePath);
  // FileContent query hook will automatically fetch based on new selection
};
```

### handlePullFromSource

```typescript
const handlePullFromSource = () => {
  pullFromSource.mutate();
};
```

### handleDeployToProject

```typescript
const handleDeployToProject = () => {
  if (!projectPath) {
    toast.error('No project path specified');
    return;
  }
  deployToProject.mutate();
};
```

### handlePushToCollection

```typescript
const handlePushToCollection = () => {
  toast.info('Coming Soon: Push local changes to collection');
};
```

### handleApply

```typescript
const handleApply = async () => {
  setIsApplying(true);
  try {
    for (const action of pendingActions) {
      await executeAction(action);
    }
    toast.success('All actions applied successfully');
    setPendingActions([]);
    onClose();
  } catch (error) {
    toast.error(`Failed to apply actions: ${error.message}`);
  } finally {
    setIsApplying(false);
  }
};
```

### handleCancel

```typescript
const handleCancel = () => {
  setPendingActions([]);
  onClose();
};
```

---

## Testing Strategy

### Unit Tests

- [ ] Component renders without errors
- [ ] Props are correctly passed to sub-components
- [ ] State updates trigger re-renders
- [ ] Event handlers are called with correct arguments
- [ ] Query hooks are invoked with correct parameters
- [ ] Mutation hooks trigger on button clicks

### Integration Tests

- [ ] Changing comparison scope updates diff viewer
- [ ] Selecting file updates preview pane
- [ ] Pull from source triggers sync mutation and refetch
- [ ] Deploy to project triggers deploy mutation and refetch
- [ ] Apply executes all pending actions in sequence
- [ ] Cancel clears pending actions and closes modal

### Manual Testing Checklist

- [ ] Visual appearance matches design
- [ ] All sub-components render correctly
- [ ] Comparison selector switches diff views
- [ ] File tree selection updates both diff and preview
- [ ] Action buttons trigger correct operations
- [ ] Loading states display during API calls
- [ ] Error states display on API failures
- [ ] Toast notifications appear on success/error
- [ ] Responsive layout works on different screen sizes
- [ ] Dark mode works correctly
- [ ] Keyboard navigation works (Tab, Enter, Escape)

---

## Next Steps (Phase 3)

**After Phase 2 completion:**

1. **Phase 3:** Integrate SyncStatusTab into unified-entity-modal.tsx
   - Replace existing "Sync Status" tab content
   - Update modal props/types to pass entity and mode
   - Wire entity data to SyncStatusTab
   - Ensure tab switching works correctly

2. **Phase 4:** Polish & Actions
   - Wire all buttons to real API calls
   - Add Coming Soon states with proper tooltips
   - Add success/error toast notifications
   - Implement loading states during operations
   - Performance optimization (code splitting, memoization)

---

## Notes & Observations

- SyncStatusTab is the orchestration layer - it doesn't implement UI, just coordinates sub-components
- State management is intentionally simple (useState) - no need for complex state machines
- Query hooks handle data fetching automatically based on state changes
- Mutation hooks include success/error handling with toast notifications
- Layout uses Tailwind's flex utilities for responsive 3-panel design
- Component should be independently testable by mocking all sub-components and hooks
- Consider lazy loading DiffViewer and FilePreviewPane if bundle size becomes an issue
