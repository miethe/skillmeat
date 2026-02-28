---
feature: workflow-detail-modals
status: in-progress
created: 2026-02-28
complexity: moderate
files_affected: ~8
---

# Quick Feature: Workflow & Execution Detail Modals

## Goal

Refactor workflow and execution detail views from full-page navigation to modal-based UX,
consistent with the rest of the app (which uses `BaseArtifactModal` / `UnifiedEntityModal`).
Keep full pages available via "Expand" links for complex views (execution live dashboard).

## Design Decisions

1. **WorkflowDetailModal**: Shows all 3 tabs (Stages, Executions, Settings) in a Dialog.
   - Reuses existing components: StageCard, StageConnector, TabNavigation
   - Has "Open Full Page" expand button in header
   - Execution rows in the Executions tab open ExecutionDetailModal

2. **ExecutionDetailModal**: Shows execution summary (header, progress, stage list).
   - Reuses: ExecutionHeader (adapted), ExecutionProgress, stage summary
   - Has prominent "Open Live Dashboard" button linking to full page
   - Full page needed for: SSE streaming, LogViewer, split layout
   - Clicking workflow name opens WorkflowDetailModal

3. **Card/ListItem changes**: Add `onClick` prop for modal opening (keep Link for
   accessibility/SEO, but intercept click to open modal instead).

4. **Full pages kept**: Routes remain for direct linking, "Expand" targets, and
   the execution dashboard SSE experience.

## Tasks

- TASK-1: Create WorkflowDetailModal component
- TASK-2: Create ExecutionDetailModal component
- TASK-3: Update WorkflowCard and WorkflowListItem with onClick support
- TASK-4: Update workflows/page.tsx with modal state management
- TASK-5: Wire cross-linking between modals (execution ↔ workflow)

## Files

### New
- `components/workflow/workflow-detail-modal.tsx`
- `components/workflow/execution-detail-modal.tsx`

### Modified
- `components/workflow/workflow-card.tsx` - Add onClick prop
- `components/workflow/workflow-list-item.tsx` - Add onClick prop
- `app/workflows/page.tsx` - Modal state, onClick handlers
- `hooks/index.ts` - Export new hooks if needed
