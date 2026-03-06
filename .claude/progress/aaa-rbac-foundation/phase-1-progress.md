---
type: progress
schema_version: 2
doc_type: progress
prd: "aaa-rbac-foundation"
feature_slug: "aaa-rbac-foundation"
prd_ref: /docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md
plan_ref: /docs/project_plans/implementation_plans/features/aaa-rbac-foundation-v1.md
phase: 1
title: "Database Layer - Authentication Schema & Tenancy Fields"
status: "planning"
started: null
completed: null
commit_refs: []
pr_refs: []

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 7
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["data-layer-expert"]
contributors: ["backend-architect"]

tasks:
  - id: "DB-001"
    description: "Design auth schema (users, teams, team_members, roles tables)"
    status: "pending"
    assigned_to: ["data-layer-expert", "backend-architect"]
    dependencies: []
    estimated_effort: "2 pts"
    priority: "high"

  - id: "DB-002"
    description: "Add owner_id, owner_type, visibility columns to local models (Artifact, Collection, Project, Group)"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["DB-001"]
    estimated_effort: "3 pts"
    priority: "high"

  - id: "DB-003"
    description: "Add owner_id, owner_type, visibility columns to enterprise models"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["DB-001"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "DB-004"
    description: "Create Alembic migration for SQLite schema (users, teams, team_members, column adds)"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["DB-002"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "DB-005"
    description: "Create Alembic migration for PostgreSQL enterprise schema"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["DB-003"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "DB-006"
    description: "Add data migration to populate local_admin user and assign ownership to existing data"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["DB-004"]
    estimated_effort: "1 pt"
    priority: "medium"

  - id: "DB-007"
    description: "Add indexes on owner_id, tenant_id; foreign key constraints for team_members"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["DB-005"]
    estimated_effort: "1 pt"
    priority: "medium"

parallelization:
  batch_1: ["DB-001"]
  batch_2: ["DB-002", "DB-003"]
  batch_3: ["DB-004", "DB-005"]
  batch_4: ["DB-006", "DB-007"]
  critical_path: ["DB-001", "DB-002", "DB-004", "DB-006"]
  estimated_total_time: "5 days"

blockers: []

success_criteria:
  - { id: "SC-1", description: "Database schema validated (ERD doc reviewed)", status: "pending" }
  - { id: "SC-2", description: "Local migration runs successfully on SQLite", status: "pending" }
  - { id: "SC-3", description: "Enterprise migration runs successfully on PostgreSQL", status: "pending" }
  - { id: "SC-4", description: "All constraints and indexes in place", status: "pending" }
  - { id: "SC-5", description: "Existing data defaults to local_admin user", status: "pending" }
  - { id: "SC-6", description: "Down migrations tested and work correctly", status: "pending" }

files_modified:
  - "skillmeat/cache/models.py"
  - "skillmeat/cache/enterprise_models.py"
  - "skillmeat/cache/constants.py"
  - "skillmeat/cache/migrations/versions/*.py"
---

# aaa-rbac-foundation - Phase 1: Database Layer - Authentication Schema & Tenancy Fields

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/aaa-rbac-foundation/phase-1-progress.md -t DB-001 -s completed
```

---

## Objective

Define auth-related database tables (users, teams, team_members) and add ownership/visibility columns to existing local and enterprise models. Create Alembic migrations for both SQLite and PostgreSQL. Default existing data to local_admin user.

---

## Orchestration Quick Reference

```bash
# Batch 1: Schema design (no dependencies)
Task("data-layer-expert", "Design auth schema: users, teams, team_members, roles tables.
  Files: skillmeat/cache/models.py, skillmeat/cache/enterprise_models.py
  Pattern: Follow existing model patterns in models.py (DeclarativeBase, mapped_column)
  Constraints: users PK=UUID; teams PK=UUID; team_members junction with roles enum
  Add LOCAL_ADMIN_USER_ID constant to skillmeat/cache/constants.py (UUID)")

# Batch 2: Model updates (parallel - different files)
Task("data-layer-expert", "Add owner_id, owner_type, visibility to local models.
  File: skillmeat/cache/models.py
  Models: Artifact, Collection, Project, Group
  Columns: owner_id (String, nullable, default=LOCAL_ADMIN_USER_ID), owner_type (String, default='user'), visibility (String, default='private')
  Note: Local models use str PKs, not UUID")

Task("data-layer-expert", "Add owner_id, owner_type, visibility to enterprise models.
  File: skillmeat/cache/enterprise_models.py
  Columns: owner_id (UUID, nullable, default=DEFAULT_TENANT_ID), owner_type (String, default='user'), visibility (String, default='private')
  Note: Enterprise models use UUID PKs")

# Batch 3: Migrations (parallel - different DBs)
Task("data-layer-expert", "Create Alembic migration for local SQLite schema.
  Dir: skillmeat/cache/migrations/versions/
  Include: users, teams, team_members tables; owner_id/owner_type/visibility columns on Artifact, Collection, Project, Group
  Ensure: DOWN migration works; SQLite compatibility")

Task("data-layer-expert", "Create Alembic migration for enterprise PostgreSQL schema.
  Dir: skillmeat/cache/migrations/versions/
  Include: Same tables/columns for enterprise schema
  Ensure: PostgreSQL-specific DDL; idempotent")

# Batch 4: Data defaults + indexes
Task("data-layer-expert", "Add data migration for local_admin defaults and indexes.
  Data: Populate local_admin user row; UPDATE existing rows to set owner_id=LOCAL_ADMIN_USER_ID
  Indexes: owner_id, tenant_id on all modified tables; FK constraints on team_members")
```

---

## Implementation Notes

### Key Files
- `skillmeat/cache/models.py` — Local ORM models (str PKs, SQLite)
- `skillmeat/cache/enterprise_models.py` — Enterprise ORM models (UUID PKs, PostgreSQL)
- `skillmeat/cache/constants.py` — DEFAULT_TENANT_ID already exists; add LOCAL_ADMIN_USER_ID
- `skillmeat/cache/migrations/versions/` — Alembic migrations

### Known Gotchas
- Local models use `str` primary keys; enterprise use `UUID` — owner_id type must match each schema
- SQLite doesn't support `ALTER TABLE ADD COLUMN ... FOREIGN KEY` — may need batch migration mode
- Existing data must default to local_admin without breaking existing queries
