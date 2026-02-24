---
type: progress
schema_version: 2
doc_type: progress
prd: deployment-sets-v1
feature_slug: deployment-sets
prd_ref: docs/project_plans/PRDs/features/deployment-sets-v1.md
plan_ref: docs/project_plans/implementation_plans/features/deployment-sets-v1.md
phase: 1
title: Database + Repository Layer
status: pending
started: '2026-02-23'
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 3
completed_tasks: 1
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- data-layer-expert
- python-backend-engineer
contributors: []
tasks:
- id: DS-001
  description: ORM models + Alembic migration for DeploymentSet/DeploymentSetMember
    with string UUID IDs, DB CHECK constraint, and indexes (set_id/member_set_id/set+position)
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies: []
  estimated_effort: 2 pts
  priority: high
- id: DS-002
  description: DeploymentSet CRUD repository with owner scoping hooks and FR-10 parent-reference
    cleanup on delete
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - DS-001
  estimated_effort: 2 pts
  priority: high
- id: DS-003
  description: 'Member management repo: add_member/remove/reorder/get with repo validation
    backed by DB CHECK for exactly-one member reference'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - DS-002
  estimated_effort: 1 pt
  priority: high
parallelization:
  batch_1:
  - DS-001
  batch_2:
  - DS-002
  batch_3:
  - DS-003
  critical_path:
  - DS-001
  - DS-002
  - DS-003
  estimated_total_time: 1-2 days
blockers: []
success_criteria:
- id: SC-1
  description: alembic upgrade/downgrade succeeds cleanly
  status: pending
- id: SC-2
  description: CHECK constraint + indexes (set_id, member_set_id, set_id+position)
    confirmed
  status: pending
- id: SC-3
  description: Unit tests for repo CRUD pass (SQLite in-memory)
  status: pending
- id: SC-4
  description: FR-10 delete semantics validated (inbound parent references removed)
  status: pending
files_modified:
- skillmeat/cache/models.py
- skillmeat/cache/repositories.py
- skillmeat/cache/migrations/
progress: 33
updated: '2026-02-24'
---

# deployment-sets-v1 - Phase 1: Database + Repository Layer

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/deployment-sets-v1/phase-1-progress.md -t DS-001 -s completed
```

---

## Objective

Create the foundational database tables (DeploymentSet, DeploymentSetMember) with Alembic migration, and implement the repository layer for CRUD operations and member management. This phase establishes the data model that all subsequent phases build upon.

---

## Orchestration Quick Reference

```python
# Batch 1: DB models + migration
Task("data-layer-expert", "Create DeploymentSet and DeploymentSetMember ORM models in skillmeat/cache/models.py and write Alembic migration. Follow existing Group/GroupArtifact pattern. See implementation plan: docs/project_plans/implementation_plans/features/deployment-sets-v1.md Phase 1, task DS-001.", model="sonnet", mode="acceptEdits")

# Batch 2: CRUD repo (after DS-001)
Task("python-backend-engineer", "Implement DeploymentSetRepository in skillmeat/cache/repositories.py with create/get/list/update/delete plus FR-10 parent-reference cleanup on delete and owner scope hooks. Follow existing repository patterns. See implementation plan Phase 1, task DS-002.", model="sonnet", mode="acceptEdits")

# Batch 3: Member repo (after DS-002)
Task("python-backend-engineer", "Add member management to DeploymentSetRepository: add_member, remove_member, update_member_position, get_members. Validate polymorphic constraint in repo and backstop with DB CHECK constraint. See implementation plan Phase 1, task DS-003.", model="sonnet", mode="acceptEdits")
```

---

## Implementation Notes

### Patterns to Follow
- Follow `Group` / `GroupArtifact` pattern in `skillmeat/cache/models.py` for table structure
- Use `artifact_uuid` (ADR-007) as FK for artifact members, not `artifact.id`
- Position-based ordering like `GroupArtifact.position`

### Known Gotchas
- Polymorphic constraint: exactly one of `artifact_uuid`, `group_id`, `member_set_id` must be non-null per row
- `group_id` and `member_set_id` are string UUIDs, consistent with existing `Group.id`
- Migration needs both upgrade AND downgrade
- Add indexes on `set_id`, `member_set_id`, and `(set_id, position)` for resolution/reordering performance
