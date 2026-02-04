---
type: progress
prd: sync-diff-modal-standardization-v1
phase: 1
title: Fix Frontend Validation
status: completed
started: '2026-02-04'
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
contributors: []
tasks:
- id: TASK-1.1
  description: Update hasValidUpstreamSource() signature and logic in sync-status-tab.tsx
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 2 pts
  priority: high
  model: opus
- id: TASK-1.2
  description: 'Update upstream-diff query enablement and add retry: false'
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-1.1
  estimated_effort: 1 pt
  priority: high
  model: opus
- id: TASK-1.3
  description: Remove duplicate hasValidUpstreamSource() from artifact-operations-modal.tsx
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-1.1
  estimated_effort: 1 pt
  priority: medium
  model: opus
- id: TASK-1.4
  description: Verify validation fix with marketplace, GitHub, and local artifacts
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - TASK-1.2
  - TASK-1.3
  estimated_effort: 1 pt
  priority: high
  model: opus
parallelization:
  batch_1:
  - TASK-1.1
  batch_2:
  - TASK-1.2
  - TASK-1.3
  batch_3:
  - TASK-1.4
  critical_path:
  - TASK-1.1
  - TASK-1.2
  - TASK-1.4
  estimated_total_time: 5 pts
blockers: []
success_criteria:
- id: SC-1
  description: Zero 400 errors on /manage for any artifact type
  status: pending
- id: SC-2
  description: GitHub artifacts with tracking show upstream diff
  status: pending
- id: SC-3
  description: Marketplace/local artifacts show no upstream state
  status: pending
- id: SC-4
  description: No TanStack Query retry loops
  status: pending
files_modified:
- web/components/sync-status/sync-status-tab.tsx
- web/components/manage/artifact-operations-modal.tsx
- web/lib/sync-utils.ts
progress: 100
updated: '2026-02-04'
---

# sync-diff-modal-standardization-v1 - Phase 1: Fix Frontend Validation

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/sync-diff-modal-standardization/phase-1-progress.md -t TASK-1.1 -s completed
```

---

## Objective

Fix the frontend-backend source validation mismatch that causes 400 errors on `/manage` for marketplace artifacts. Align `hasValidUpstreamSource()` with backend expectations by checking `origin` and `upstream.tracking_enabled`.

---

## Implementation Notes

### Key Changes

1. `hasValidUpstreamSource()` at `sync-status-tab.tsx:98-104` changes from `(source: string)` to `(entity: Artifact)`
2. Checks `entity.origin === 'github'` AND `entity.upstream?.tracking_enabled`
3. Duplicate function at `artifact-operations-modal.tsx:435-441` removed; import shared util
4. Query enablement at `sync-status-tab.tsx:238-239` updated to use new signature

### Known Gotchas

- The function is called in two places: `sync-status-tab.tsx` and `artifact-operations-modal.tsx`
- Backend also checks `artifact.upstream` is not null (line 4166-4170)
- TanStack Query defaults to 3 retries; add `retry: false` to prevent 400 retry loops
- Marketplace artifacts have `origin: "marketplace"` but `origin_source: "github"` -- do NOT use `origin_source`

---

## Completion Notes

_(fill in when phase is complete)_
