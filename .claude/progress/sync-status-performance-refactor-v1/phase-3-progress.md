---
type: progress
schema_version: 2
doc_type: progress
prd: "sync-status-performance-refactor-v1"
feature_slug: "sync-status-performance-refactor-v1"
prd_ref: null
plan_ref: "docs/project_plans/implementation_plans/refactors/sync-status-performance-refactor-v1.md"
phase: 3
title: "Diff API Contract Refactor (Summary First)"
status: "planning"
started: "2026-02-20"
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: "on-track"
blockers: []

owners:
  - "backend-architect"
  - "python-backend-engineer"
contributors: []

tasks:
  - id: "TASK-3.1"
    title: "Add query flags"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: []
    estimated_effort: "2pts"
    priority: "high"
  - id: "TASK-3.2"
    title: "Summary-first execution path"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-3.1"]
    estimated_effort: "3pts"
    priority: "critical"
  - id: "TASK-3.3"
    title: "Lazy file-detail endpoint or mode"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-3.1"]
    estimated_effort: "3pts"
    priority: "high"
  - id: "TASK-3.4"
    title: "Contract tests"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-3.2", "TASK-3.3"]
    estimated_effort: "2pts"
    priority: "high"

task_counts:
  total_tasks: 4
  completed_tasks: 0
  in_progress_tasks: 0
  blocked_tasks: 0
  at_risk_tasks: 0

parallelization:
  batch_1: ["TASK-3.1"]
  batch_2: ["TASK-3.2", "TASK-3.3"]
  batch_3: ["TASK-3.4"]
  critical_path: ["TASK-3.1", "TASK-3.2", "TASK-3.4"]
  estimated_total_time: "5pts"

success_criteria:
  - id: "SC-3.1"
    description: "Existing clients remain compatible with default behavior"
    status: "pending"
  - id: "SC-3.2"
    description: "Summary-first mode returns quickly without full unified diff"
    status: "pending"

files_modified:
  - "skillmeat/api/routers/artifacts.py"
  - "skillmeat/core/artifact.py"
---

# sync-status-performance-refactor-v1 - Phase 3: Diff API Contract Refactor (Summary First)

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/sync-status-performance-refactor-v1/phase-3-progress.md -t TASK-3.X -s completed
```

---

## Objective

Introduce a summary-first mode to the diff API so that the frontend can display lightweight diff metadata before requesting full file-level details, reducing time-to-first-meaningful-content in the sync tab.

---

## Orchestration Quick Reference

```python
# Batch 1 (sequential - contract design first)
Task("backend-architect", "Design and add query flags to the diff API contract (e.g. ?summary_only=true). Update OpenAPI schema. Files: skillmeat/api/routers/artifacts.py, skillmeat/api/openapi.json", model="sonnet", mode="acceptEdits")

# Batch 2 (parallel, after batch 1)
Task("python-backend-engineer", "Implement summary-first execution path in the diff endpoint using the query flags from TASK-3.1. Return only counts/metadata when summary mode is active, skipping full unified diff generation. Files: skillmeat/api/routers/artifacts.py, skillmeat/core/artifact.py", model="sonnet", mode="acceptEdits")
Task("python-backend-engineer", "Implement lazy file-detail endpoint or mode for on-demand full diff retrieval, using query flags from TASK-3.1. Files: skillmeat/api/routers/artifacts.py, skillmeat/core/artifact.py", model="sonnet", mode="acceptEdits")

# Batch 3 (after batch 2)
Task("python-backend-engineer", "Write contract tests for the diff API: verify backward compatibility, summary-first response shape, and lazy file-detail mode. Files: tests/", model="sonnet", mode="acceptEdits")
```

---

## Implementation Notes

_To be filled during execution._

---

## Completion Notes

_To be filled when phase is complete._
