---
type: progress
schema_version: 2
doc_type: progress
prd: "deployment-sets-v1"
feature_slug: "deployment-sets"
prd_ref: docs/project_plans/PRDs/features/deployment-sets-v1.md
plan_ref: docs/project_plans/implementation_plans/features/deployment-sets-v1.md
phase: 2
title: "Service Layer"
status: "planning"
started: "2026-02-23"
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: "on-track"
total_tasks: 3
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners: ["python-backend-engineer", "backend-architect"]
contributors: []
tasks:
  - id: "DS-004"
    description: "Resolution service: DFS traversal, depth limit 20, deduplication by artifact_uuid"
    status: "pending"
    assigned_to: ["backend-architect", "python-backend-engineer"]
    dependencies: ["DS-003"]
    estimated_effort: "3 pts"
    priority: "critical"
  - id: "DS-005"
    description: "Circular-reference detection on add_member via descendant reachability from candidate member set"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["DS-004"]
    estimated_effort: "2 pts"
    priority: "high"
  - id: "DS-006"
    description: "Batch deploy service: resolve set, adapt artifact_uuid/project identifiers to deploy contract, deploy each artifact, collect per-artifact results"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["DS-005"]
    estimated_effort: "2 pts"
    priority: "high"
parallelization:
  batch_1: ["DS-004"]
  batch_2: ["DS-005"]
  batch_3: ["DS-006"]
  critical_path: ["DS-004", "DS-005", "DS-006"]
  estimated_total_time: "1-2 days"
blockers: []
success_criteria:
  - { id: "SC-1", description: "Resolution unit tests >90% branch coverage", status: "pending" }
  - { id: "SC-2", description: "Cycle detection covers direct, transitive, self-reference cases", status: "pending" }
  - { id: "SC-3", description: "Batch deploy adapter path validated (artifact_uuid -> deploy request + project path)", status: "pending" }
  - { id: "SC-4", description: "Domain exceptions defined: DeploymentSetResolutionError, DeploymentSetCycleError", status: "pending" }
files_modified: [
  "skillmeat/core/deployment_sets.py",
  "skillmeat/core/exceptions.py"
]
---

# deployment-sets-v1 - Phase 2: Service Layer

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/deployment-sets-v1/phase-2-progress.md -t DS-004 -s completed
```

---

## Objective

Implement the core business logic: recursive set resolution (DFS with depth limit and deduplication), circular-reference detection at write time, and batch deploy orchestration that calls the existing per-artifact deploy service.

---

## Orchestration Quick Reference

```python
# Batch 1: Resolution service (critical path)
Task("backend-architect", "Implement DeploymentSetService.resolve(set_id) with DFS traversal, depth-20 limit, dedup by artifact_uuid. See implementation plan Phase 2, task DS-004. File: skillmeat/core/deployment_sets.py", model="sonnet", mode="acceptEdits")

# Batch 2: Cycle detection (after DS-004)
Task("python-backend-engineer", "Implement _check_cycle(set_id, candidate_member_set_id) via descendant reachability from candidate set. Called on add_member for set members. Raise DeploymentSetCycleError with traversal path. See implementation plan Phase 2, task DS-005.", model="sonnet", mode="acceptEdits")

# Batch 3: Batch deploy (after DS-005)
Task("python-backend-engineer", "Implement batch_deploy(set_id, project_id, profile_id). Call resolve(), adapt artifact_uuid/project identifiers to existing deploy contract inputs, then deploy each artifact. Never abort on failure. Return list[DeployResultDTO]. See implementation plan Phase 2, task DS-006.", model="sonnet", mode="acceptEdits")
```

---

## Implementation Notes

### Critical Design: Resolution Service
- DS-004 is the highest-risk item and gates all downstream work
- Resolution is stateless — accepts in-memory member maps for testing without DB
- Group members: read GroupArtifact rows for artifact_uuid list
- Set members: recurse into nested set

### Known Gotchas
- Depth limit of 20 is a safety net — normal sets should be <5 levels
- Deduplication must preserve first-seen order
- Cycle detection happens at write time (add_member), not resolve time
- Adapter mismatch risk: resolver outputs `artifact_uuid` while deploy APIs consume `artifact_id`/`artifact_name`/`artifact_type` + `project_path`
