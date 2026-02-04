---
type: progress
prd: sync-diff-modal-standardization-v1
phase: 2
title: Add Project Context to /manage
status: completed
started: '2026-02-04'
completed: '2026-02-04'
overall_progress: 100
completion_estimate: on-track
total_tasks: 5
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- ui-engineer-enhanced
contributors: []
tasks:
- id: TASK-2.1
  description: Add selectedProjectForDiff state to ArtifactOperationsModal with auto-detection
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 2 pts
  priority: high
  model: opus
- id: TASK-2.2
  description: Integrate ProjectSelectorForDiff component in /manage sync tab
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-2.1
  estimated_effort: 3 pts
  priority: high
  model: opus
- id: TASK-2.3
  description: Pass projectPath to SyncStatusTab in ArtifactOperationsModal
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-2.2
  estimated_effort: 2 pts
  priority: high
  model: opus
- id: TASK-2.4
  description: Update ComparisonSelector enablement for hasProject flag
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-2.3
  estimated_effort: 1 pt
  priority: medium
  model: opus
- id: TASK-2.5
  description: Verify project context with deployed artifacts on /manage
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-2.4
  estimated_effort: 1 pt
  priority: high
  model: opus
parallelization:
  batch_1:
  - TASK-2.1
  batch_2:
  - TASK-2.2
  batch_3:
  - TASK-2.3
  - TASK-2.4
  batch_4:
  - TASK-2.5
  critical_path:
  - TASK-2.1
  - TASK-2.2
  - TASK-2.3
  - TASK-2.5
  estimated_total_time: 9 pts
blockers: []
success_criteria:
- id: SC-1
  description: Project selector visible on /manage sync tab
  status: pending
- id: SC-2
  description: Auto-detection works for single-deployment artifacts
  status: pending
- id: SC-3
  description: All three comparison scopes available when applicable
  status: pending
- id: SC-4
  description: Flow banner shows accurate deployment status
  status: pending
files_modified:
- web/components/manage/artifact-operations-modal.tsx
- web/components/sync-status/comparison-selector.tsx
progress: 100
updated: '2026-02-04'
---

# sync-diff-modal-standardization-v1 - Phase 2: Add Project Context to /manage

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/sync-diff-modal-standardization/phase-2-progress.md -t TASK-2.1 -s completed
```

---

## Objective

Enable collection-vs-project diffs on `/manage` by adding project selector and auto-detection. Reuse existing `ProjectSelectorForDiff` component from `web/components/entity/project-selector-for-diff.tsx`.

---

## Implementation Notes

### Pattern Reference

`UnifiedEntityModal` already implements this pattern at lines 619-622:
```typescript
const [selectedProjectForDiff, setSelectedProjectForDiff] = useState<string | undefined>();
```

And passes it at lines 2111-2116:
```tsx
<SyncStatusTab
  entity={entity}
  mode={entity.projectPath ? 'project' : 'collection'}
  projectPath={entity.projectPath || selectedProjectForDiff || undefined}
  onClose={onClose}
/>
```

### Auto-Detection Logic

```typescript
// Derive initial project from deployments
const initialProject = useMemo(() => {
  if (artifact.deployments?.length === 1) {
    return artifact.deployments[0].projectPath;
  }
  return undefined;
}, [artifact.deployments]);
```

### Known Gotchas

- `ProjectSelectorForDiff` needs `entityId`, `entityName`, `entityType`, `collection`, `onProjectSelected` props
- The component fetches deployments internally -- verify it works with collection-mode data
- Keep `mode="collection"` even when projectPath is provided (project context is for diff comparison only)
- `ComparisonSelector` uses `hasProject` boolean -- verify it reads from correct prop

---

## Completion Notes

_(fill in when phase is complete)_
