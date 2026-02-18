---
type: progress
prd: "composite-artifact-infrastructure"
phase: 1
title: "Core Relationships (Backend)"
status: "planning"
started: "2026-02-17"
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 7
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["data-layer-expert", "python-backend-engineer"]
contributors: ["code-reviewer"]

tasks:
  - id: "CAI-P1-01"
    description: "Add PLUGIN to ArtifactType enum; audit all call sites for exhaustiveness"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: []
    estimated_effort: "1pt"
    priority: "critical"

  - id: "CAI-P1-02"
    description: "Define ArtifactAssociation ORM model with composite PK, FKs, relationship_type, pinned_version_hash"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["CAI-P1-01"]
    estimated_effort: "2pt"
    priority: "high"

  - id: "CAI-P1-03"
    description: "Add parent_associations and child_associations bidirectional relationships to Artifact ORM"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["CAI-P1-02"]
    estimated_effort: "1pt"
    priority: "high"

  - id: "CAI-P1-04"
    description: "Generate and apply Alembic migration for artifact_associations table with reversible down()"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["CAI-P1-03"]
    estimated_effort: "2pt"
    priority: "high"

  - id: "CAI-P1-05"
    description: "Implement association repository: get_associations(), create_association(), delete methods"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["CAI-P1-04"]
    estimated_effort: "2pt"
    priority: "high"

  - id: "CAI-P1-06"
    description: "Unit tests for association repository CRUD and queries (>80% coverage)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["CAI-P1-05"]
    estimated_effort: "1pt"
    priority: "medium"

  - id: "CAI-P1-07"
    description: "Integration tests for model + repository layer; FK constraints enforced"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["CAI-P1-06"]
    estimated_effort: "1pt"
    priority: "medium"

parallelization:
  batch_1: ["CAI-P1-01", "CAI-P1-02", "CAI-P1-03"]
  batch_2: ["CAI-P1-04"]
  batch_3: ["CAI-P1-05", "CAI-P1-06", "CAI-P1-07"]
  critical_path: ["CAI-P1-01", "CAI-P1-02", "CAI-P1-04", "CAI-P1-05"]
  estimated_total_time: "3-4 days"

blockers: []

success_criteria: [
  { id: "SC-P1-1", description: "Enum change does not break existing type-checking", status: "pending" },
  { id: "SC-P1-2", description: "Alembic migration applies cleanly to fresh DB", status: "pending" },
  { id: "SC-P1-3", description: "Alembic migration rolls back cleanly", status: "pending" },
  { id: "SC-P1-4", description: "FK constraints enforced by database", status: "pending" },
  { id: "SC-P1-5", description: "Repository CRUD methods pass unit tests (>80% coverage)", status: "pending" },
  { id: "SC-P1-6", description: "No regression in existing artifact queries/imports", status: "pending" }
]

files_modified: [
  "skillmeat/core/enums.py",
  "skillmeat/cache/models.py",
  "skillmeat/cache/migrations/versions/",
  "skillmeat/cache/repositories/"
]
---

# composite-artifact-infrastructure - Phase 1: Core Relationships (Backend)

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/composite-artifact-infrastructure/phase-1-progress.md -t CAI-P1-01 -s completed
python .claude/skills/artifact-tracking/scripts/update-batch.py -f .claude/progress/composite-artifact-infrastructure/phase-1-progress.md --updates "CAI-P1-01:completed,CAI-P1-02:completed"
```

---

## Objective

Establish the database schema, ORM models, and repository layer for artifact associations. This foundation enables all downstream phases (discovery, import, UI).

---

## Orchestration Quick Reference

```text
# Batch 1: ORM model work (data-layer-expert)
Task("data-layer-expert", "Add PLUGIN enum + ArtifactAssociation model + Artifact relationships.
  Files: skillmeat/core/enums.py, skillmeat/cache/models.py
  Tasks: CAI-P1-01, CAI-P1-02, CAI-P1-03
  Pattern: Follow GroupArtifact association pattern in models.py
  Acceptance: Enum added, model validates, backrefs work")

# Batch 2: Migration (data-layer-expert)
Task("data-layer-expert", "Generate Alembic migration for artifact_associations table.
  Files: skillmeat/cache/migrations/versions/
  Task: CAI-P1-04
  Acceptance: Migration applies/rolls back cleanly on fresh DB")

# Batch 3: Repository + tests (python-backend-engineer)
Task("python-backend-engineer", "Implement association repository with CRUD + unit/integration tests.
  Files: skillmeat/cache/repositories/, tests/
  Tasks: CAI-P1-05, CAI-P1-06, CAI-P1-07
  Acceptance: CRUD methods work, >80% coverage, FK constraints enforced")
```

---

## Implementation Notes

### Key Files

- `skillmeat/cache/models.py` — Add `ArtifactAssociation`, update `Artifact` relationships
- `skillmeat/core/enums.py` — Add `PLUGIN` to `ArtifactType`
- `skillmeat/cache/repositories/` — Association CRUD repository
- Implementation plan details: `docs/project_plans/implementation_plans/features/composite-artifact-infrastructure-v1/phase-1-core-relationships.md`

### Known Gotchas

- Audit ALL `ArtifactType` switch/match statements when adding PLUGIN enum value
- Use composite primary key (parent_id, child_id) not a surrogate ID
- Bidirectional relationships need careful `foreign_keys` specification to avoid ambiguity

---

## Completion Notes

_Fill in when phase is complete._
