# Implementation Plan: Simplify Sync Status Tab Layout

**PRD**: N/A (simple UI cleanup)
**Scope**: Remove side panes from Sync Status tab
**Effort**: ~30 minutes
**Risk**: Low

---

## Summary

Remove the FileTree (left pane) and FilePreviewPane (right pane) from the Sync Status tab, expanding the DiffViewer to fill the full width. The DiffViewer already has its own file tree and content viewer, making the side panes redundant.

---

## Current Layout

```
┌────────────────────────────────────────────────────────────────┐
│  ArtifactFlowBanner (3-tier: Source → Collection → Project)   │
└────────────────────────────────────────────────────────────────┘
┌──────────┬───────────────────────┬──────────────────────────────┐
│ FileTree │ ComparisonSelector    │ FilePreviewPane              │
│ (240px)  │ DriftAlertBanner      │ (320px)                      │
│          │ DiffViewer (flex-1)   │                              │
│          │                       │                              │
└──────────┴───────────────────────┴──────────────────────────────┘
┌────────────────────────────────────────────────────────────────┐
│  SyncActionsFooter (action buttons)                            │
└────────────────────────────────────────────────────────────────┘
```

## Target Layout

```
┌────────────────────────────────────────────────────────────────┐
│  ArtifactFlowBanner (3-tier: Source → Collection → Project)   │
└────────────────────────────────────────────────────────────────┘
┌────────────────────────────────────────────────────────────────┐
│  ComparisonSelector                                            │
│  DriftAlertBanner                                              │
│  DiffViewer (full width, expanded)                             │
└────────────────────────────────────────────────────────────────┘
┌────────────────────────────────────────────────────────────────┐
│  SyncActionsFooter (action buttons)                            │
└────────────────────────────────────────────────────────────────┘
```

---

## Implementation Tasks

### TASK-1: Remove side panes from sync-status-tab.tsx

**File**: `skillmeat/web/components/sync-status/sync-status-tab.tsx`

**Changes**:

1. **Remove left pane JSX** (FileTree wrapper ~lines 778-781):
   ```tsx
   // DELETE this entire block:
   <div className="w-60 flex-shrink-0 border-r min-h-0 overflow-auto">
     <FileTree {...fileTreeProps} />
   </div>
   ```

2. **Remove right pane JSX** (FilePreviewPane wrapper ~lines 793-796):
   ```tsx
   // DELETE this entire block:
   <div className="w-80 flex-shrink-0 border-l min-h-0 overflow-auto">
     <FilePreviewPane {...previewProps} />
   </div>
   ```

3. **Simplify middle container** - The remaining center pane can now be simplified since it no longer needs to share space:
   ```tsx
   // Before: 3-panel flex container
   <div className="flex flex-1 overflow-hidden min-h-0">
     {/* left pane */}
     {/* center pane */}
     {/* right pane */}
   </div>

   // After: Single full-width panel
   <div className="flex flex-1 min-w-0 flex-col overflow-hidden min-h-0">
     {/* ComparisonSelector + DriftAlertBanner */}
     {/* DiffViewer */}
   </div>
   ```

4. **Remove unused state/props** (if no longer needed):
   - `selectedFile` state - may be used by DiffViewer internally, verify before removing
   - `fileContent` query - only used by FilePreviewPane
   - FileTree props assembly
   - FilePreviewPane props assembly

5. **Remove imports** (if components no longer used):
   - `FileTree` from `@/components/entity/file-tree`
   - `FilePreviewPane` from `./file-preview-pane`

---

## Validation Checklist

- [ ] Sync Status tab renders without errors
- [ ] DiffViewer fills full width of modal
- [ ] ComparisonSelector and DriftAlertBanner still visible at top
- [ ] SyncActionsFooter still visible at bottom
- [ ] ArtifactFlowBanner still visible at top
- [ ] Other modal tabs (Overview, Files, etc.) unaffected
- [ ] No console errors or TypeScript warnings
- [ ] No orphaned imports or dead code

---

## Files Affected

| File | Change Type |
|------|-------------|
| `skillmeat/web/components/sync-status/sync-status-tab.tsx` | Modify (remove side panes) |

---

## Agent Assignment

| Task | Agent | Model |
|------|-------|-------|
| TASK-1 | ui-engineer | Sonnet |

---

## Rollback

If issues arise, revert the single file change:
```bash
git checkout HEAD -- skillmeat/web/components/sync-status/sync-status-tab.tsx
```
