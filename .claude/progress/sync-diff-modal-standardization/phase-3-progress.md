---
type: progress
prd: sync-diff-modal-standardization-v1
phase: 3
title: Extract BaseArtifactModal Foundation
status: completed
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- ui-engineer-enhanced
contributors:
- codebase-explorer
tasks:
- id: TASK-3.1
  description: Analyze shared patterns between ArtifactOperationsModal and UnifiedEntityModal
  status: completed
  assigned_to:
  - codebase-explorer
  dependencies: []
  estimated_effort: 2 pts
  priority: medium
  model: haiku
- id: TASK-3.2
  description: Create BaseArtifactModal component with composition pattern
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-3.1
  estimated_effort: 5 pts
  priority: medium
  model: opus
- id: TASK-3.3
  description: Refactor ArtifactOperationsModal to compose from BaseArtifactModal
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-3.2
  estimated_effort: 5 pts
  priority: medium
  model: opus
- id: TASK-3.4
  description: Verify modal refactor - test all tabs on both pages
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-3.3
  estimated_effort: 1 pt
  priority: high
  model: opus
parallelization:
  batch_1:
  - TASK-3.1
  batch_2:
  - TASK-3.2
  batch_3:
  - TASK-3.3
  batch_4:
  - TASK-3.4
  critical_path:
  - TASK-3.1
  - TASK-3.2
  - TASK-3.3
  - TASK-3.4
  estimated_total_time: 13 pts
blockers: []
success_criteria:
- id: SC-1
  description: BaseArtifactModal handles 60%+ of modal boilerplate
  status: pending
- id: SC-2
  description: ArtifactOperationsModal reduced by 30%+ lines
  status: pending
- id: SC-3
  description: All tabs function correctly on both pages
  status: pending
- id: SC-4
  description: No TypeScript errors (pnpm tsc --noEmit)
  status: pending
files_modified:
- web/components/shared/BaseArtifactModal.tsx
- web/components/manage/artifact-operations-modal.tsx
progress: 100
updated: '2026-02-04'
schema_version: 2
doc_type: progress
feature_slug: sync-diff-modal-standardization-v1
---

# sync-diff-modal-standardization-v1 - Phase 3: Extract BaseArtifactModal Foundation

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/sync-diff-modal-standardization/phase-3-progress.md -t TASK-3.1 -s completed
```

---

## Objective

Extract shared modal patterns into `BaseArtifactModal` for future convergence. Refactor `ArtifactOperationsModal` to compose from base, reducing code by 30%+.

---

## Implementation Notes

### Extraction Targets

Shared patterns between both modals:
- Modal container (Dialog shell, backdrop, sizing)
- Header with artifact name/type/version
- Tab bar navigation
- `EntityLifecycleProvider` wrapping
- Close handling / keyboard shortcuts
- Query setup for artifact data

### Composition Pattern

Use render props or slots pattern for tab content:
```tsx
<BaseArtifactModal
  artifact={artifact}
  open={open}
  onClose={onClose}
  initialTab="status"
  mode="collection"
  tabs={[
    { id: 'status', label: 'Status', content: <StatusTab /> },
    { id: 'sync', label: 'Sync', content: <SyncStatusTab /> },
  ]}
/>
```

### Known Gotchas

- TASK-3.1 analysis MUST complete before coding to confirm extraction boundaries
- `UnifiedEntityModal` is NOT refactored in this phase (deferred to future PR)
- Both modals have different tab configurations -- base must be flexible
- Lifecycle provider wrapping differs between collection/project mode
- Ensure `onClose` cleanup logic (URL params, state reset) is preserved

---

## Completion Notes

_(fill in when phase is complete)_
