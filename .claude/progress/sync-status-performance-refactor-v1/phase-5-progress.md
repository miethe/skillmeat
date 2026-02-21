---
type: progress
schema_version: 2
doc_type: progress
prd: "sync-status-performance-refactor-v1"
feature_slug: "sync-status-performance-refactor-v1"
prd_ref: null
plan_ref: "docs/project_plans/implementation_plans/refactors/sync-status-performance-refactor-v1.md"
phase: 5
title: "Frontend Query Orchestration Refactor"
status: "planning"
started: "2026-02-20"
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: "on-track"
blockers: []

owners:
  - "frontend-developer"
  - "react-performance-optimizer"
contributors: []

tasks:
  - id: "TASK-5.1"
    title: "Gate fanout deployment queries"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: []
    estimated_effort: "3pts"
    priority: "critical"
  - id: "TASK-5.2"
    title: "Remove duplicate deployment sources"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["TASK-5.1"]
    estimated_effort: "2pts"
    priority: "high"
  - id: "TASK-5.3"
    title: "Scope-aware diff loading"
    status: "pending"
    assigned_to: ["react-performance-optimizer"]
    dependencies: []
    estimated_effort: "3pts"
    priority: "high"
  - id: "TASK-5.4"
    title: "Stale/gc tuning for heavy sync queries"
    status: "pending"
    assigned_to: ["react-performance-optimizer"]
    dependencies: ["TASK-5.1", "TASK-5.3"]
    estimated_effort: "1pt"
    priority: "medium"

task_counts:
  total_tasks: 4
  completed_tasks: 0
  in_progress_tasks: 0
  blocked_tasks: 0
  at_risk_tasks: 0

parallelization:
  batch_1: ["TASK-5.1", "TASK-5.3"]
  batch_2: ["TASK-5.2", "TASK-5.4"]
  critical_path: ["TASK-5.1", "TASK-5.2"]
  estimated_total_time: "5pts"

success_criteria:
  - id: "SC-5.1"
    description: "Modal open no longer triggers deployment fanout from unrelated tabs"
    status: "pending"
  - id: "SC-5.2"
    description: "Time-to-initial-diff improved"
    status: "pending"

files_modified:
  - "skillmeat/web/components/manage/artifact-operations-modal.tsx"
  - "skillmeat/web/components/sync-status/sync-status-tab.tsx"
---

# sync-status-performance-refactor-v1 - Phase 5: Frontend Query Orchestration Refactor

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/sync-status-performance-refactor-v1/phase-5-progress.md -t TASK-5.X -s completed
```

---

## Objective

Refactor frontend query orchestration to gate unnecessary deployment fanout queries and load diffs scope-aware, reducing the number of API calls made when interacting with the sync status tab and artifact modals.

---

## Orchestration Quick Reference

```python
# Batch 1 (parallel)
Task("frontend-developer", "Gate fanout deployment queries so they only fire when the sync tab or relevant panel is active. Prevent modal open from triggering deployment queries for all artifacts. File: skillmeat/web/components/manage/artifact-operations-modal.tsx", model="sonnet", mode="acceptEdits")
Task("react-performance-optimizer", "Implement scope-aware diff loading: only load diffs for the active comparison scope (source-vs-collection, collection-vs-project, source-vs-project). Reference hook selection: .claude/context/key-context/hook-selection-and-deprecations.md. File: skillmeat/web/components/sync-status/sync-status-tab.tsx", model="sonnet", mode="acceptEdits")

# Batch 2 (parallel, after batch 1)
Task("frontend-developer", "Remove duplicate deployment data sources now that fanout is gated (TASK-5.1). Consolidate to single query path. File: skillmeat/web/components/sync-status/sync-status-tab.tsx", model="sonnet", mode="acceptEdits")
Task("react-performance-optimizer", "Tune staleTime and gcTime for heavy sync queries (deployment status, diff data). Apply 30s interactive stale time per data-flow-patterns. Reference: .claude/context/key-context/data-flow-patterns.md. File: skillmeat/web/components/sync-status/sync-status-tab.tsx", model="sonnet", mode="acceptEdits")
```

---

## Implementation Notes

_To be filled during execution._

---

## Completion Notes

_To be filled when phase is complete._
