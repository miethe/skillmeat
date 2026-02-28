---
feature: Execution Quick Actions & Multi-Select
status: completed
created: 2026-02-28
scope: frontend-only
files_affected:
- skillmeat/web/app/workflows/executions/page.tsx
- skillmeat/web/lib/workflow-action-utils.ts (new)
- skillmeat/web/components/workflow/execution-row-actions.tsx (new)
- skillmeat/web/components/workflow/execution-bulk-actions.tsx (new)
- skillmeat/web/hooks/use-execution-selection.ts (new)
tasks:
- id: QF-1
  title: Create status-to-action mapping utility
  status: completed
  assigned_to: ui-engineer-enhanced
- id: QF-2
  title: Create row actions column + bulk action bar + selection hook
  status: completed
  assigned_to: ui-engineer-enhanced
- id: QF-3
  title: Integrate into executions page
  status: completed
  assigned_to: ui-engineer-enhanced
total_tasks: 3
completed_tasks: 3
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
updated: '2026-02-28'
---

## Quick Plan

### QF-1: Status-Action Mapping Utility
New file `skillmeat/web/lib/workflow-action-utils.ts`:
- `EXECUTION_ACTION_MAP`: Maps each ExecutionStatus to available actions
- `getAvailableActions(status)`: Returns action list for a single execution
- `getBulkActions(executions)`: Returns union of all actions across selected items
- `getApplicableExecutions(executions, action)`: Filters to only those supporting the action

### QF-2: UI Components
- `ExecutionRowActions`: Action buttons (icon buttons) for a single row
- `ExecutionBulkActions`: Floating bar with bulk action buttons + selection count
- `useExecutionSelection`: Hook managing selection state, hover behavior, select all/clear

### QF-3: Integration
- Add checkbox column (left) and actions column (right) to executions table
- Wire up Select All / Clear Selection above table
- Wire floating bulk action bar at bottom
- Checkbox hover-reveal: show on hover when nothing selected, always show when >= 1 selected
