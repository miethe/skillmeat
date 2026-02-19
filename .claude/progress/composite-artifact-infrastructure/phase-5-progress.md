---
type: progress
prd: composite-artifact-infrastructure
phase: 5
title: UUID Migration for Existing Join Tables (Backend)
status: in_progress
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 8
completed_tasks: 3
in_progress_tasks: 2
blocked_tasks: 0
at_risk_tasks: 0
owners:
- data-layer-expert
- python-backend-engineer
contributors:
- code-reviewer
tasks:
- id: CAI-P5-01
  description: 'Migrate collection_artifacts to artifact_uuid FK: add column, backfill
    from artifacts.uuid, drop artifact_id, update CollectionArtifact ORM and Collection.artifacts
    relationship'
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - CAI-P4-08
  estimated_effort: 2pt
  priority: critical
- id: CAI-P5-02
  description: 'Migrate group_artifacts to artifact_uuid FK: same shadow-column pattern
    as P5-01; preserve position/CheckConstraint; composite PK becomes (group_id, artifact_uuid)'
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - CAI-P5-01
  estimated_effort: 2pt
  priority: high
- id: CAI-P5-03
  description: 'Migrate artifact_tags to artifact_uuid FK: PK becomes (artifact_uuid,
    tag_id); update Artifact.tags and Tag.artifacts relationships at models.py:299-308,
    1132-1134'
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - CAI-P5-02
  estimated_effort: 2pt
  priority: high
- id: CAI-P5-04
  description: 'Update repository layer to query via artifact_uuid: all CollectionArtifact/GroupArtifact/ArtifactTag
    queries use UUID join; external DTOs still return type:name'
  status: in_progress
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CAI-P5-03
  estimated_effort: 3pt
  priority: high
- id: CAI-P5-05
  description: 'Verify service and API layer correctness post-migration: smoke test
    all collection, group, and tag endpoints; no API surface changes permitted'
  status: in_progress
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CAI-P5-03
  estimated_effort: 2pt
  priority: high
- id: CAI-P5-06
  description: 'Assess and implement (or defer) PK change: artifacts.id type:name
    → unique index, artifacts.uuid → PK; document outcome in ADR-007 regardless of
    decision'
  status: pending
  assigned_to:
  - data-layer-expert
  dependencies:
  - CAI-P5-04
  - CAI-P5-05
  estimated_effort: 3pt
  priority: medium
- id: CAI-P5-07
  description: 'Comprehensive regression tests: tests/test_uuid_migration_regression.py
    covering all three join tables, cascade deletes, API endpoints, and alembic downgrade
    -3'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CAI-P5-04
  - CAI-P5-05
  estimated_effort: 2pt
  priority: high
- id: CAI-P5-08
  description: 'Retire Phase 1 compatibility layer: remove _migrate_artifact_tags_fk()
    if superseded, remove dual-path shims, update ADR-007 Phase 2 checklist'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CAI-P5-06
  - CAI-P5-07
  estimated_effort: 1pt
  priority: low
parallelization:
  batch_1:
  - CAI-P5-01
  batch_2:
  - CAI-P5-02
  batch_3:
  - CAI-P5-03
  batch_4:
  - CAI-P5-04
  - CAI-P5-05
  batch_5:
  - CAI-P5-06
  - CAI-P5-07
  batch_6:
  - CAI-P5-08
  critical_path:
  - CAI-P5-01
  - CAI-P5-02
  - CAI-P5-03
  - CAI-P5-04
  - CAI-P5-07
  estimated_total_time: 4-6 days
blockers: []
success_criteria:
- id: SC-P5-1
  description: All three join tables (collection_artifacts, group_artifacts, artifact_tags)
    use artifact_uuid FK with ondelete=CASCADE
  status: pending
- id: SC-P5-2
  description: 'Cascading deletes verified: deleting a CachedArtifact removes all
    join table rows across all three tables'
  status: pending
- id: SC-P5-3
  description: All Alembic migrations apply cleanly (alembic upgrade head) and roll
    back cleanly (alembic downgrade -3)
  status: pending
- id: SC-P5-4
  description: No API surface changes — external consumers continue to receive type:name
    identifiers
  status: pending
- id: SC-P5-5
  description: No regression in collection management, tagging, or grouping features
    (all endpoint tests pass)
  status: pending
- id: SC-P5-6
  description: Decision on artifacts.id PK demotion documented in ADR-007 with rationale
    (Outcome A or B)
  status: pending
- id: SC-P5-7
  description: '>80% test coverage on all repository methods that touch migrated tables'
  status: pending
files_modified:
- skillmeat/cache/models.py
- skillmeat/cache/migrations/versions/
- skillmeat/cache/repositories.py
- skillmeat/core/services/
- tests/test_uuid_migration_regression.py
- tests/conftest.py
- docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md
progress: 37
updated: '2026-02-19'
---

# composite-artifact-infrastructure - Phase 5: UUID Migration for Existing Join Tables (Backend)

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/composite-artifact-infrastructure/phase-5-progress.md -t CAI-P5-01 -s completed
python .claude/skills/artifact-tracking/scripts/update-batch.py -f .claude/progress/composite-artifact-infrastructure/phase-5-progress.md --updates "CAI-P5-01:completed,CAI-P5-02:completed"
```

---

## Objective

Migrate `collection_artifacts`, `group_artifacts`, and `artifact_tags` from bare `type:name` string references (no FK constraints) to proper UUID foreign keys pointing at `artifacts.uuid`. Delivers referential integrity with cascade deletes, updated repository queries, and retirement of Phase 1 compatibility shims. No API surface changes — external identifiers remain `type:name`.

**ADR Reference**: `docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md` — Phase 2 section.

---

## Orchestration Quick Reference

```python
# batch_1: First migration — foundation for subsequent batches
Task("data-layer-expert",
     "Migrate collection_artifacts join table to use artifact_uuid FK. "
     "Follow CAI-P5-01 spec in phase-5-uuid-migration.md. "
     "Files: skillmeat/cache/models.py, skillmeat/cache/migrations/versions/. "
     "Pattern: ADR-007 (docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md). "
     "Shadow-column rollback strategy required for down migration.")

# batch_2: Sequential to batch_1 — avoid Alembic chain conflicts
Task("data-layer-expert",
     "Migrate group_artifacts join table to use artifact_uuid FK. "
     "Follow CAI-P5-02 spec in phase-5-uuid-migration.md. "
     "Same shadow-column pattern as CAI-P5-01. Preserve position/CheckConstraint. "
     "Files: skillmeat/cache/models.py, new Alembic migration.")

# batch_3: Sequential to batch_2 — clean Alembic revision chain
Task("data-layer-expert",
     "Migrate artifact_tags join table to use artifact_uuid FK. "
     "Follow CAI-P5-03 spec in phase-5-uuid-migration.md. "
     "Note: existing _migrate_artifact_tags_fk() at models.py:2931 is superseded. "
     "Update Artifact.tags and Tag.artifacts relationships at models.py:299-308, 1132-1134.")

# batch_4: Repository and service updates in parallel
Task("python-backend-engineer",
     "Update repository layer to query via artifact_uuid. "
     "Follow CAI-P5-04 spec in phase-5-uuid-migration.md. "
     "File: skillmeat/cache/repositories.py. "
     "Resolve type:name to UUID in queries; DTOs still return type:name externally.")

Task("python-backend-engineer",
     "Verify service and API layer correctness post-migration. "
     "Follow CAI-P5-05 spec in phase-5-uuid-migration.md. "
     "Smoke test all collection, group, and tag endpoints. "
     "No API surface changes permitted.")

# batch_5: PK assessment and regression tests in parallel
Task("data-layer-expert",
     "Assess feasibility of promoting artifacts.uuid to PK. "
     "Follow CAI-P5-06 spec in phase-5-uuid-migration.md. "
     "Map FK dependency graph, estimate effort, implement or document deferral decision. "
     "Update ADR-007 with outcome.")

Task("python-backend-engineer",
     "Write regression test suite for UUID migration. "
     "Follow CAI-P5-07 spec in phase-5-uuid-migration.md. "
     "New file: tests/test_uuid_migration_regression.py. "
     "Cover all three join tables, cascade deletes, API endpoints, migration rollback.")

# batch_6: Cleanup depends on P5-06 (decision) and P5-07 (tests passing)
Task("python-backend-engineer",
     "Retire Phase 1 compatibility layer. "
     "Follow CAI-P5-08 spec in phase-5-uuid-migration.md. "
     "Remove _migrate_artifact_tags_fk() if superseded. "
     "Update ADR-007 Phase 2 checklist.")
```

---

## Implementation Notes

### Key Files

- `skillmeat/cache/models.py` — `CollectionArtifact`, `GroupArtifact`, `ArtifactTag` ORM updates; `Artifact.tags`, `Tag.artifacts`, `Collection.artifacts` relationship changes; `_migrate_artifact_tags_fk()` removal (CAI-P5-08)
- `skillmeat/cache/migrations/versions/` — Three new Alembic migrations (CAI-P5-01, -02, -03); optional PK migration (CAI-P5-06 Outcome A)
- `skillmeat/cache/repositories.py` — All query methods on the three migrated join tables (CAI-P5-04)
- `skillmeat/core/services/` — Any UUID/type:name dual-path shims to remove (CAI-P5-08)
- `tests/test_uuid_migration_regression.py` — New regression test file (CAI-P5-07)
- `docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md` — Phase 2 checklist + PK decision (CAI-P5-06, CAI-P5-08)
- Implementation plan details: `docs/project_plans/implementation_plans/features/composite-artifact-infrastructure-v1/phase-5-uuid-migration.md`

### Shadow-Column Rollback Strategy

Each `upgrade()` renames `artifact_id` to `_artifact_id_backup`, adds `artifact_uuid`, backfills, sets NOT NULL, adds FK. Each `downgrade()` drops FK, drops `artifact_uuid`, renames `_artifact_id_backup` back to `artifact_id`. This preserves rollback data without a separate backup table.

### Alembic Chain Requirement

Migrations must be strictly sequential (batch_1 → batch_2 → batch_3). Parallel generation creates Alembic branches requiring `alembic merge`. Generate one migration per batch, verify `alembic upgrade head` succeeds before starting the next.

### Repository Query Pattern

After migration, resolve `type:name` → UUID via a join within the repository, not a separate lookup round-trip:

```python
# After (UUID join — single query)
session.query(CollectionArtifact).join(
    CachedArtifact,
    CachedArtifact.uuid == CollectionArtifact.artifact_uuid
).filter(
    CollectionArtifact.collection_id == collection_id,
    CachedArtifact.id == artifact_id  # resolve type:name via join
)
```

---

## Known Gotchas

1. **SQLite ALTER TABLE limitations**: SQLite does not support dropping columns or modifying FK constraints in-place. Use the rename/create/copy/drop pattern (same as `_migrate_artifact_tags_fk()` at models.py:2965) for SQLite compatibility in CI tests.

2. **Orphan rows during backfill**: `artifact_id` values with no matching `CachedArtifact.id` must be deleted (not failed). Log each deletion with artifact_id before removing.

3. **Sequential migration requirement**: Generate migrations one at a time. Parallel generation creates Alembic branch conflicts requiring `alembic merge` before `upgrade head` will work.

4. **`Collection.artifacts` relationship**: `CollectionArtifact` is a rich metadata table (description, author, tags_json, etc.), not a simple join table. Update `secondary`/`primaryjoin` carefully; test relationship loading after model update.

5. **CAI-P5-06 risk**: `ArtifactVersion.artifact_id` currently FKs to `artifacts.id`. Changing `artifacts.id` PK will invalidate SQLAlchemy session identity maps. If >2 days effort, choose Outcome B (defer) and document.

6. **`_migrate_artifact_tags_fk()` at models.py:2931**: Ensure `_run_compatibility_migrations()` (models.py:3022) no longer calls this after Phase 5, or the function safely no-ops when the new schema is detected.

7. **Frontend impact**: Frontend reads collection/tag/group data via API — no frontend code changes expected. Smoke test web UI post-migration to confirm.

---

## Completion Notes

_Fill in when phase is complete._

- [ ] Actual duration vs estimate (planned: 4-6 days)
- [ ] CAI-P5-06 outcome (Outcome A — UUID promoted to PK, or Outcome B — deferred with rationale)
- [ ] Orphan rows found and deleted during backfill (count per table)
- [ ] Any gotchas not anticipated above
- [ ] Follow-up work identified (if any)
