---
type: progress
prd: "composite-artifact-infrastructure"
phase: 1
title: "Core Relationships (Database & ORM)"
status: "planning"
started: "2026-02-17"
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 9
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
    description: "Add uuid column to CachedArtifact ORM model (String, unique, non-null, indexed, default=uuid4().hex)"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: []
    estimated_effort: "1pt"
    priority: "critical"

  - id: "CAI-P1-03"
    description: "Alembic migration 1: add uuid column to artifacts table, backfill existing rows, apply NOT NULL + unique index"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["CAI-P1-02"]
    estimated_effort: "2pt"
    priority: "critical"

  - id: "CAI-P1-04"
    description: "Define CompositeArtifact and CompositeMembership ORM models with UUID FK (child_artifact_uuid → artifacts.uuid, ondelete=CASCADE)"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["CAI-P1-01", "CAI-P1-03"]
    estimated_effort: "2pt"
    priority: "high"

  - id: "CAI-P1-05"
    description: "Alembic migration 2: create composite_artifacts and composite_memberships tables (separate from UUID migration)"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["CAI-P1-04"]
    estimated_effort: "1pt"
    priority: "high"

  - id: "CAI-P1-06"
    description: "Implement composite membership repository CRUD and service-layer type:name → UUID resolution (composite_service.py)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["CAI-P1-05"]
    estimated_effort: "2pt"
    priority: "high"

  - id: "CAI-P1-07"
    description: "Write CachedArtifact.uuid into filesystem manifests (.skillmeat-deployed.toml and manifest.toml) additively"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["CAI-P1-03"]
    estimated_effort: "1pt"
    priority: "medium"

  - id: "CAI-P1-08"
    description: "Unit tests: UUID generation, uniqueness, CompositeMembership CRUD, service-layer resolution (>80% coverage)"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["CAI-P1-06"]
    estimated_effort: "2pt"
    priority: "medium"

  - id: "CAI-P1-09"
    description: "Integration tests: FK constraints, cascading deletes, type:name → UUID resolution end-to-end, migration round-trip"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["CAI-P1-08"]
    estimated_effort: "2pt"
    priority: "medium"

parallelization:
  batch_1:
    tasks: ["CAI-P1-01", "CAI-P1-02"]
    note: "Independent — enum addition and UUID column are separate concerns"
  batch_2:
    tasks: ["CAI-P1-03"]
    note: "UUID migration must apply before composite tables reference artifacts.uuid"
  batch_3:
    tasks: ["CAI-P1-04", "CAI-P1-07"]
    note: "Composite ORM model + filesystem UUID writes are independent after migration"
  batch_4:
    tasks: ["CAI-P1-05", "CAI-P1-06"]
    note: "Composite migration runs after model defined; repository runs after migration"
  batch_5:
    tasks: ["CAI-P1-08", "CAI-P1-09"]
    note: "Unit and integration tests run after repository complete"
  critical_path: ["CAI-P1-02", "CAI-P1-03", "CAI-P1-04", "CAI-P1-05", "CAI-P1-06", "CAI-P1-08"]
  estimated_total_time: "3-4 days"

blockers: []

success_criteria: [
  { id: "SC-P1-1", description: "All existing CachedArtifact rows have non-null unique UUID after migration", status: "pending" },
  { id: "SC-P1-2", description: "CompositeMembership FK constraint enforced by database (insert with bad UUID rejected)", status: "pending" },
  { id: "SC-P1-3", description: "Cascading delete removes memberships when child artifact deleted", status: "pending" },
  { id: "SC-P1-4", description: "type:name → UUID resolution works correctly in service layer", status: "pending" },
  { id: "SC-P1-5", description: "UUID appears in .skillmeat-deployed.toml and manifest.toml (additive, backward-compatible)", status: "pending" },
  { id: "SC-P1-6", description: "Both Alembic migrations apply and rollback cleanly and independently", status: "pending" },
  { id: "SC-P1-7", description: "No regression in existing artifact queries/imports (pytest tests/api/test_artifacts.py)", status: "pending" },
  { id: "SC-P1-8", description: "Repository CRUD >80% test coverage", status: "pending" }
]

files_modified: [
  "skillmeat/core/artifact_detection.py",
  "skillmeat/cache/models.py",
  "skillmeat/cache/migrations/versions/{ts1}_add_artifact_uuid_column.py",
  "skillmeat/cache/migrations/versions/{ts2}_add_composite_artifact_tables.py",
  "skillmeat/cache/repositories.py",
  "skillmeat/core/services/composite_service.py",
  "skillmeat/storage/",
  "tests/test_composite_memberships.py",
  "tests/integration/test_composite_memberships_integration.py",
  "tests/conftest.py"
]
---

# composite-artifact-infrastructure - Phase 1: Core Relationships (Database & ORM)

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/composite-artifact-infrastructure/phase-1-progress.md -t CAI-P1-01 -s completed
python .claude/skills/artifact-tracking/scripts/update-batch.py -f .claude/progress/composite-artifact-infrastructure/phase-1-progress.md --updates "CAI-P1-01:completed,CAI-P1-02:completed"
```

---

## Objective

Establish the database foundation for the Composite Artifact Infrastructure: UUID identity column on `CachedArtifact`, composite ORM models with UUID FK, two independent Alembic migrations, repository CRUD, service-layer resolution, and filesystem manifest writes. All downstream phases (discovery, import orchestration, API, UI) depend on this foundation being stable and well-tested.

---

## Orchestration Quick Reference

```python
# Batch 1 — parallel, no dependencies
Task("data-layer-expert",
    "Add PLUGIN to ArtifactType enum. Audit all call sites. "
    "File: skillmeat/core/artifact_detection.py. "
    "Run mypy after. See phase-1-core-relationships.md CAI-P1-01 for acceptance criteria.")

Task("data-layer-expert",
    "Add uuid column to CachedArtifact in skillmeat/cache/models.py. "
    "String, unique, non-null, default=lambda: uuid.uuid4().hex, indexed. "
    "Do NOT generate migration yet. See phase-1-core-relationships.md CAI-P1-02.")

# Batch 2 — after Batch 1
Task("data-layer-expert",
    "Generate Alembic migration for CachedArtifact.uuid column. "
    "Add nullable, backfill existing rows, then apply NOT NULL + unique index. "
    "Test apply and rollback. See phase-1-core-relationships.md CAI-P1-03.")

# Batch 3 — after Batch 2 (parallel)
Task("data-layer-expert",
    "Define CompositeArtifact and CompositeMembership ORM models. "
    "Use UUID FK (child_artifact_uuid → artifacts.uuid, ondelete=CASCADE). "
    "Add bidirectional relationship on CachedArtifact. "
    "See ADR-007 at docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md "
    "and phase-1-core-relationships.md CAI-P1-04.")

Task("python-backend-engineer",
    "Write CachedArtifact.uuid into filesystem manifests during deploy and collection ops. "
    "Files: skillmeat/storage/ deploy manifest writer and manifest.toml writer. "
    "Additive field — backward-compatible. See phase-1-core-relationships.md CAI-P1-07.")

# Batch 4 — after Batch 3 (parallel after CAI-P1-04)
Task("data-layer-expert",
    "Generate Alembic migration for composite_artifacts and composite_memberships tables. "
    "Separate from UUID migration. Verify FK targets artifacts.uuid. "
    "See phase-1-core-relationships.md CAI-P1-05.")

Task("python-backend-engineer",
    "Implement composite membership repository CRUD and type:name → UUID resolution service. "
    "Files: skillmeat/cache/repositories.py and new skillmeat/core/services/composite_service.py. "
    "See phase-1-core-relationships.md CAI-P1-06.")

# Batch 5 — after Batch 4 (parallel)
Task("python-backend-engineer",
    "Write unit tests for UUID generation, uniqueness, CompositeMembership CRUD, "
    "and service-layer resolution. Target >80% coverage. "
    "File: tests/test_composite_memberships.py. See phase-1-core-relationships.md CAI-P1-08.")

Task("python-backend-engineer",
    "Write integration tests: FK constraints, cascading deletes, type:name → UUID resolution. "
    "File: tests/integration/test_composite_memberships_integration.py. "
    "See phase-1-core-relationships.md CAI-P1-09.")
```

---

## Implementation Notes

### Key Files

- `skillmeat/core/artifact_detection.py` — Add `PLUGIN` to `ArtifactType` enum
- `skillmeat/cache/models.py` — `CachedArtifact.uuid` column, `CompositeArtifact`, `CompositeMembership`, bidirectional relationships
- `skillmeat/cache/migrations/versions/` — Two independent migration files
- `skillmeat/cache/repositories.py` (or `composite_repository.py`) — Composite membership CRUD
- `skillmeat/core/services/composite_service.py` — New: type:name → UUID resolution service
- `skillmeat/storage/` — Deployment manifest and collection manifest UUID writes
- Implementation plan: `docs/project_plans/implementation_plans/features/composite-artifact-infrastructure-v1/phase-1-core-relationships.md`
- ADR: `docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md`

### Known Gotchas

- **Backfill migration**: UUID column must be added as nullable, backfilled, then made non-null. Backfill SQL differs by dialect: SQLite uses `hex(randomblob(16))`; PostgreSQL uses `gen_random_uuid()`.
- **Two separate migrations**: One for the UUID column (CAI-P1-03), one for composite tables (CAI-P1-05). Never combine them — clean rollback of each requires independent migration files.
- **FK target is `artifacts.uuid`, not `artifacts.id`**: `CompositeMembership.child_artifact_uuid` references `artifacts.uuid`. Autogenerated migrations may default to `artifacts.id` — verify manually.
- **Bidirectional relationships**: `CachedArtifact.composite_memberships` ↔ `CompositeMembership.child_artifact` require explicit `foreign_keys=` on both sides to avoid `AmbiguousForeignKeysError`.
- **Filesystem writes are additive**: `.skillmeat-deployed.toml` and `manifest.toml` gain new optional fields. Old readers must not break when the field is absent.
- **Service layer owns resolution**: UUID is an internal DB concern. Service functions accept `type:name` from callers and resolve to UUID before any DB write. Repository methods never accept `type:name` as FK input.
- Audit ALL `ArtifactType` switch/match statements when adding PLUGIN enum value.

---

## Completion Notes

_Fill in when phase is complete._
