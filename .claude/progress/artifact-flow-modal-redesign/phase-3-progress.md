# Phase 3 Progress: Integration into Unified Entity Modal

**Status:** PENDING
**Last Updated:** 2025-11-29
**Completion:** 0% (0 of 1 tasks)
**Total Effort:** ~100 lines of integration code
**Priority:** Medium

**Related Documents:**
- PRD: `/docs/project_plans/PRDs/enhancements/artifact-flow-modal-redesign.md`
- Implementation Plan: `/docs/project_plans/artifact-flow-modal/artifact-flow-modal-implementation-plan.md`
- Phase 1 Progress: `.claude/progress/artifact-flow-modal-redesign/phase-1-progress.md`
- Phase 2 Progress: `.claude/progress/artifact-flow-modal-redesign/phase-2-progress.md`

**Subagent Assignments:**
- **TASK-3.1:** ui-engineer-enhanced

**Dependencies Map:**
- **TASK-3.1:** Depends on TASK-2.1 (SyncStatusTab must be complete)
- **TASK-4.1, 4.2:** Depend on TASK-3.1 (blocked until this phase completes)

---

## Phase Overview

**Phase Title:** Integration into Unified Entity Modal

**Duration:** 30-60 minutes
**Assigned Subagent(s):** ui-engineer-enhanced
**Code Domains:** Web

**Objective:** Replace the existing "Sync Status" tab content in `unified-entity-modal.tsx` with the new `SyncStatusTab` component. Wire entity data, mode, and project path from the modal to the new component. Ensure tab switching and modal lifecycle work correctly.

**Integration Points:**
```
unified-entity-modal.tsx
├── Tab Structure (preserve)
│   ├── Overview Tab (unchanged)
│   ├── Edit Tab (unchanged)
│   ├── Sync Status Tab ← REPLACE CONTENT
│   └── History Tab (unchanged)
├── Modal Props (update)
│   ├── entity: Entity (pass to SyncStatusTab)
│   ├── mode: 'collection' | 'project' (pass to SyncStatusTab)
│   └── projectPath?: string (pass to SyncStatusTab)
└── Modal State (preserve)
    ├── activeTab state
    ├── open/close state
    └── entity refresh on close
```

---

## Phase 3: Integration

### Sub-Task Breakdown

- **TASK-3.1:** Integrate SyncStatusTab into unified-entity-modal.tsx

### Completion Checklist

- [ ] **TASK-3.1: Integrate SyncStatusTab into unified-entity-modal.tsx** (High priority) ⏳
  - **Assigned To:** ui-engineer-enhanced
  - **Dependencies:** TASK-2.1 (SyncStatusTab component)
  - **File:** `skillmeat/web/components/entity/unified-entity-modal.tsx`
  - **Size:** ~100 lines of changes (imports + tab content replacement)
  - **Acceptance Criteria:**
    - [ ] Import SyncStatusTab component
      ```typescript
      import { SyncStatusTab } from './sync-status/sync-status-tab';
      ```
    - [ ] Locate "Sync Status" tab content section in unified-entity-modal.tsx
    - [ ] Replace existing tab content with SyncStatusTab component:
      ```tsx
      <TabsContent value="sync-status">
        <SyncStatusTab
          entity={entity}
          mode={mode}
          projectPath={projectPath}
          onClose={onClose}
        />
      </TabsContent>
      ```
    - [ ] Ensure modal props include required data:
      - [ ] `entity` prop is available
      - [ ] `mode` prop is available ('collection' or 'project')
      - [ ] `projectPath` prop is available (optional, only when mode='project')
    - [ ] Verify tab structure remains intact:
      - [ ] Overview tab still works
      - [ ] Edit tab still works
      - [ ] Sync Status tab now shows new component
      - [ ] History tab still works
    - [ ] Verify modal lifecycle:
      - [ ] Modal opens correctly
      - [ ] Tab switching works
      - [ ] Modal closes via SyncStatusTab's onClose callback
      - [ ] Entity data refreshes on modal close (if needed)
    - [ ] Remove old Sync Status tab implementation:
      - [ ] Delete or comment out old sync status content
      - [ ] Remove unused imports related to old implementation
      - [ ] Clean up any orphaned state variables
    - [ ] Update modal height/width if needed:
      - [ ] SyncStatusTab requires sufficient height for 3-panel layout
      - [ ] Suggest: `min-h-[600px]` for modal content area
      - [ ] Suggest: `w-full max-w-7xl` for modal width
    - [ ] Verify responsive behavior:
      - [ ] Modal is scrollable if content exceeds viewport
      - [ ] Tab content uses full modal width
      - [ ] 3-panel layout adapts to modal size
    - [ ] Test dark mode:
      - [ ] Tab switcher works in dark mode
      - [ ] SyncStatusTab renders correctly in dark mode
    - [ ] TypeScript compilation passes:
      - [ ] No type errors in unified-entity-modal.tsx
      - [ ] All props correctly typed
    - [ ] Manual verification:
      - [ ] Open modal from collection page → Sync Status tab loads
      - [ ] Open modal from project page → Sync Status tab loads with project context
      - [ ] Switch between tabs → no errors
      - [ ] Close modal via SyncStatusTab actions → modal closes
      - [ ] Close modal via X button → modal closes
  - **Dependencies:**
    - TASK-2.1: SyncStatusTab component must exist
    - unified-entity-modal.tsx must be functional
    - Entity type must include all required fields
  - **Key Files:**
    - Modified: `skillmeat/web/components/entity/unified-entity-modal.tsx`
    - Import: `skillmeat/web/components/entity/sync-status/sync-status-tab.tsx`
  - **Notes:**
    - This is a straightforward swap - replace old content with new component
    - Preserve all other tabs and modal functionality
    - Ensure modal size is sufficient for 3-panel layout (suggest 1400px width, 600px height)
    - Old sync status content should be removed to avoid confusion
    - Consider feature flag if gradual rollout is needed (optional)

---

## Task Status Legend

- ⏳ **Pending:** Not started
- 🔄 **In Progress:** Currently being worked on
- ✅ **Completed:** Done and tested
- 🐛 **Blocked:** Waiting on dependencies
- ⚠️  **Needs Review:** Completed but review pending

---

## Component Size Estimates

| Task | Estimated Changes | Agent | Dependencies | Status |
|------|-------------------|-------|--------------|--------|
| Integration | ~100 lines | ui-engineer-enhanced | TASK-2.1 | ⏳ |
| **Phase 3 Total** | **~100** | — | — | **0%** |

---

## Critical Dependencies

### Blocked By (Must Complete First)

**Phase 2:**
- ✗ TASK-2.1: SyncStatusTab component

**Existing Files (Must Exist):**
- ✓ `components/entity/unified-entity-modal.tsx`
- ✓ Entity type definition
- ✓ Mode type definition

### Blocks (Waiting on This Phase)

- TASK-4.1: Wire all action buttons (Phase 4)
- TASK-4.2: Add Coming Soon tooltips (Phase 4)

---

## Integration Design

### Before (Old Implementation)

```tsx
<TabsContent value="sync-status">
  <div className="p-4">
    {/* Old sync status content */}
    <div>
      <h3>Sync Status</h3>
      <p>Version: {entity.version}</p>
      <p>Last synced: {entity.lastSync}</p>
      <Button onClick={handleSync}>Sync Now</Button>
    </div>
  </div>
</TabsContent>
```

### After (New Implementation)

```tsx
<TabsContent value="sync-status" className="h-full">
  <SyncStatusTab
    entity={entity}
    mode={mode}
    projectPath={projectPath}
    onClose={handleClose}
  />
</TabsContent>
```

### Modal Props Update

Ensure `unified-entity-modal.tsx` accepts and forwards these props:

```typescript
interface UnifiedEntityModalProps {
  entity: Entity;
  mode: 'collection' | 'project';
  projectPath?: string;  // Required when mode='project'
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onClose?: () => void;
}
```

---

## Modal Size Recommendations

### Current Size (Estimate)

```tsx
<Dialog>
  <DialogContent className="max-w-4xl">
    {/* Current modal content */}
  </DialogContent>
</Dialog>
```

### Recommended Size for 3-Panel Layout

```tsx
<Dialog>
  <DialogContent className="w-full max-w-7xl h-full max-h-[90vh]">
    <Tabs className="h-full">
      <TabsList>...</TabsList>
      <TabsContent value="sync-status" className="flex-1 overflow-hidden">
        <SyncStatusTab {...props} />
      </TabsContent>
    </Tabs>
  </DialogContent>
</Dialog>
```

**Reasoning:**
- `max-w-7xl`: ~1280px width for comfortable 3-panel layout (240 + 640 + 320)
- `max-h-[90vh]`: Full viewport height minus some margin
- `overflow-hidden` on TabsContent: Prevents double scrollbars
- SyncStatusTab manages internal scrolling in FileTree and Preview panes

---

## Data Flow Verification

### Entity Data Flow

```
Parent Component (page/component)
    ↓ [passes entity]
UnifiedEntityModal
    ↓ [forwards entity]
TabsContent[value="sync-status"]
    ↓ [renders with entity prop]
SyncStatusTab
    ↓ [uses entity for queries]
API Hooks (useUpstreamDiff, useProjectDiff)
```

### Mode Context Flow

```
Parent Component
    ↓ [determines mode: 'collection' | 'project']
UnifiedEntityModal
    ↓ [forwards mode]
SyncStatusTab
    ↓ [enables/disables features based on mode]
- Collection mode: Show upstream sync options
- Project mode: Show deploy/pull options
```

### Project Path Flow

```
Parent Component (project page)
    ↓ [provides projectPath]
UnifiedEntityModal
    ↓ [forwards projectPath]
SyncStatusTab
    ↓ [uses for project diff queries]
useQuery(['project-diff', entity.id, projectPath])
```

---

## Testing Strategy

### Unit Tests

- [ ] Modal renders with SyncStatusTab when open=true
- [ ] Switching to "Sync Status" tab renders SyncStatusTab
- [ ] Entity prop is passed correctly to SyncStatusTab
- [ ] Mode prop is passed correctly to SyncStatusTab
- [ ] ProjectPath prop is passed correctly when available
- [ ] OnClose callback is wired correctly

### Integration Tests

- [ ] Opening modal from collection page loads SyncStatusTab
- [ ] Opening modal from project page loads SyncStatusTab with projectPath
- [ ] Switching between tabs preserves modal state
- [ ] Closing modal via SyncStatusTab's onClose triggers parent's onOpenChange
- [ ] Modal closes when X button is clicked
- [ ] Entity data refreshes on modal close (if applicable)

### Manual Testing Checklist

- [ ] Open modal from Collections page → Sync Status tab loads
- [ ] Open modal from Project Manage page → Sync Status tab loads with project context
- [ ] Switch to Overview tab → content loads
- [ ] Switch back to Sync Status tab → content still there
- [ ] Close modal via Apply button in SyncStatusTab → modal closes
- [ ] Close modal via Cancel button in SyncStatusTab → modal closes
- [ ] Close modal via X button → modal closes
- [ ] Reopen modal → previous tab selection preserved (or defaults to Overview)
- [ ] Dark mode → tabs and SyncStatusTab render correctly
- [ ] Responsive → modal and tabs work on smaller screens
- [ ] Keyboard navigation → Tab key switches between tab buttons

---

## Rollback Plan

If integration causes issues, the old implementation can be quickly restored:

1. **Comment out new implementation:**
   ```tsx
   {/* <SyncStatusTab entity={entity} mode={mode} projectPath={projectPath} onClose={onClose} /> */}
   ```

2. **Uncomment old implementation:**
   ```tsx
   <div className="p-4">
     {/* Old sync status content */}
   </div>
   ```

3. **Remove import:**
   ```typescript
   // import { SyncStatusTab } from './sync-status/sync-status-tab';
   ```

4. **Test old content works**

5. **Debug SyncStatusTab separately**

---

## Success Criteria

- [ ] Unified Entity Modal opens without errors
- [ ] "Sync Status" tab displays new SyncStatusTab component
- [ ] All other tabs (Overview, Edit, History) remain functional
- [ ] Modal size accommodates 3-panel layout without excessive scrolling
- [ ] Tab switching works smoothly
- [ ] Modal closes correctly via all methods (Apply, Cancel, X button)
- [ ] Entity data flows correctly to SyncStatusTab
- [ ] Mode and projectPath props are correctly passed
- [ ] Dark mode works
- [ ] Responsive behavior is acceptable
- [ ] TypeScript compiles without errors
- [ ] No console errors or warnings

---

## Next Steps (Phase 4)

**After Phase 3 completion:**

1. **Phase 4: Polish & Actions**
   - **TASK-4.1:** Wire all action buttons to hooks
     - Connect Deploy, Sync, Merge, Rollback buttons to API calls
     - Add error handling with toast notifications
     - Add loading states during operations
   - **TASK-4.2:** Add Coming Soon tooltips
     - Add Tooltip component to disabled/unimplemented actions
     - Consistent messaging: "Coming Soon: Push local changes to collection"
     - Visual indication (ghost button style)

2. **Performance Optimization:**
   - Code split heavy components (DiffViewer, FilePreviewPane)
   - Memoize sub-components with React.memo
   - Lazy load syntax highlighter for FilePreviewPane
   - Optimize query refetch behavior

3. **Accessibility Review:**
   - Ensure keyboard navigation works throughout
   - Screen reader compatibility for all interactive elements
   - ARIA labels for complex UI (flow banner, diff viewer)
   - Focus management on modal open/close

---

## Notes & Observations

- Integration should be straightforward - this is mostly a component swap
- Main risk is modal size constraints for 3-panel layout (solution: increase modal width)
- Old Sync Status content should be removed to avoid confusion and reduce bundle size
- Consider feature flag if gradual rollout is needed (not required for initial implementation)
- Ensure modal's `z-index` is sufficient to overlay other UI elements
- Test with real entity data to ensure all props are available
- Watch for TypeScript errors related to missing props or type mismatches
