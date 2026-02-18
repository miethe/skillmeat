---
title: "Phase 5: UUID Migration for Existing Join Tables (Backend)"
description: "Migrate collection_artifacts, group_artifacts, and artifact_tags join tables from type:name string references to UUID foreign keys, establishing full referential integrity across the artifact identity layer"
audience: [ai-agents, developers]
tags: [implementation, phase-5, database, migration, uuid, orm, repository]
created: 2026-02-18
updated: 2026-02-18
category: "product-planning"
status: planning
related:
  - /docs/project_plans/implementation_plans/features/composite-artifact-infrastructure-v1.md
  - /docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md
---

# Phase 5: UUID Migration for Existing Join Tables (Backend)

**Phase ID**: CAI-P5
**Duration**: 4-6 days
**Dependencies**: Phase 4 complete (CAI-P4-08 — all prior phases complete)
**Assigned Subagent(s)**: data-layer-expert, python-backend-engineer
**Owners**: data-layer-expert, python-backend-engineer
**Estimated Effort**: 15 story points

---

## Phase Overview

Phase 5 is the deferred ADR-007 Phase 2 migration. It completes the UUID identity work begun in Phase 1 by migrating the three legacy join tables — `collection_artifacts`, `group_artifacts`, and `artifact_tags` — from bare `type:name` string references (no FK constraints) to proper UUID foreign keys pointing at `artifacts.uuid`.

This phase delivers:

1. Referential integrity on all three legacy join tables (cascade deletes, no orphaned rows)
2. Repository layer updated to query by UUID instead of string identity
3. Service and API layer verified for correctness with no external API surface change
4. Decision documented on whether `artifacts.id` (`type:name`) remains PK or becomes a unique index
5. Retirement of any Phase 1 compatibility shims

After this phase, every relational reference to a `CachedArtifact` goes through `artifacts.uuid`. The `type:name` identifier (`artifacts.id`) remains as the external-facing, filesystem-facing, and lookup-facing identifier — it is not removed.

**ADR Reference**: `docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md` — Phase 2 section.

---

## Task Breakdown

### CAI-P5-01: Migrate `collection_artifacts` to `artifact_uuid` FK

**Description**: Add an `artifact_uuid` column to `collection_artifacts` with a proper FK to `artifacts.uuid`, backfill from existing `artifact_id` string values, then drop the `artifact_id` column. Single Alembic migration, fully reversible.

**Acceptance Criteria**:
- [ ] New column `artifact_uuid VARCHAR NOT NULL` added to `collection_artifacts`
- [ ] FK constraint: `ForeignKey("artifacts.uuid", ondelete="CASCADE")`
- [ ] Data backfill: for each row, look up `artifacts.uuid` where `artifacts.id = collection_artifacts.artifact_id`; rows with no match are logged and deleted (orphan cleanup)
- [ ] Old `artifact_id` column dropped after backfill
- [ ] All existing indexes on `artifact_id` recreated on `artifact_uuid`
- [ ] Alembic `upgrade()` applies cleanly: `alembic upgrade head`
- [ ] Alembic `downgrade()` restores `artifact_id` from a temp backup column created during `upgrade()`
- [ ] No existing collection data lost; only orphaned references removed
- [ ] `CollectionArtifact` ORM model updated: `artifact_uuid` column, FK, relationship to `CachedArtifact`

**Key Files to Modify**:
- `skillmeat/cache/models.py` — `CollectionArtifact`: replace `artifact_id` with `artifact_uuid` + FK
- `skillmeat/cache/migrations/versions/{timestamp}_migrate_collection_artifacts_to_uuid.py` — New migration

**Implementation Notes**:
- The down migration must restore the `artifact_id` string column. Strategy: during `upgrade()`, keep `artifact_id` as a shadow column renamed to `_artifact_id_backup`; in `downgrade()`, rename it back and drop `artifact_uuid`. This avoids data loss on rollback.
- `CollectionArtifact` has many cached metadata fields (description, author, license, tags_json, etc.) — these columns are unaffected.
- `collection_id` FK to `collections.id` is also present; leave untouched.
- Update the `Collection.artifacts` relationship `secondary`/`primaryjoin` to use `artifact_uuid`.
- Orphan rows (artifact_id references no artifact in cache) should be deleted with a warning log, not fail the migration.

**Estimate**: 2 story points

---

### CAI-P5-02: Migrate `group_artifacts` to `artifact_uuid` FK

**Description**: Same pattern as CAI-P5-01 applied to `group_artifacts`. Add `artifact_uuid` FK column, backfill, drop `artifact_id`. Sequential to CAI-P5-01 to avoid Alembic chain conflicts.

**Acceptance Criteria**:
- [ ] New column `artifact_uuid VARCHAR NOT NULL` added to `group_artifacts`
- [ ] FK constraint: `ForeignKey("artifacts.uuid", ondelete="CASCADE")`
- [ ] Data backfill: look up `artifacts.uuid` by matching `artifacts.id = group_artifacts.artifact_id`; orphans logged and deleted
- [ ] Old `artifact_id` column dropped after backfill (with `_artifact_id_backup` shadow for rollback)
- [ ] Indexes on `artifact_id` recreated on `artifact_uuid`
- [ ] Alembic `upgrade()` and `downgrade()` both work cleanly
- [ ] `GroupArtifact` ORM model updated: `artifact_uuid` FK column, relationship added
- [ ] `position`, `added_at`, `CheckConstraint` all preserved unchanged
- [ ] `Group.artifacts` relationship updated to join on `artifact_uuid`

**Key Files to Modify**:
- `skillmeat/cache/models.py` — `GroupArtifact`: replace `artifact_id` with `artifact_uuid` + FK
- `skillmeat/cache/migrations/versions/{timestamp}_migrate_group_artifacts_to_uuid.py` — New migration

**Implementation Notes**:
- `GroupArtifact.position` is part of the ordering mechanism; composite indexes `idx_group_artifacts_group_position` must still reference `group_id` and `position` — not `artifact_uuid`.
- The `CheckConstraint("position >= 0", ...)` is unaffected.
- Composite PK becomes `(group_id, artifact_uuid)` after migration.

**Estimate**: 2 story points

---

### CAI-P5-03: Migrate `artifact_tags` to `artifact_uuid` FK

**Description**: Same pattern applied to `artifact_tags`. This table's PK is `(artifact_id, tag_id)` — migration changes `artifact_id` to `artifact_uuid`. A historical migration function `_migrate_artifact_tags_fk()` already exists in `models.py` (line 2931) that removed a previous FK — new migration supersedes it.

**Acceptance Criteria**:
- [ ] New column `artifact_uuid VARCHAR NOT NULL` added to `artifact_tags`
- [ ] FK constraint: `ForeignKey("artifacts.uuid", ondelete="CASCADE")`
- [ ] Data backfill: look up `artifacts.uuid` by `artifacts.id = artifact_tags.artifact_id`; orphans logged and deleted
- [ ] Old `artifact_id` column dropped (with `_artifact_id_backup` shadow for rollback)
- [ ] PK becomes `(artifact_uuid, tag_id)` after migration
- [ ] FK to `tags.id` on `tag_id` preserved
- [ ] All existing `artifact_tags` indexes recreated on `artifact_uuid`
- [ ] Alembic `upgrade()` and `downgrade()` both work cleanly
- [ ] `ArtifactTag` ORM model updated: `artifact_uuid` FK, PK updated, relationship to `CachedArtifact` added
- [ ] `Artifact.tags` and `Tag.artifacts` relationships updated to join via `artifact_uuid`

**Key Files to Modify**:
- `skillmeat/cache/models.py` — `ArtifactTag`: replace `artifact_id` with `artifact_uuid` + FK; update both `Artifact.tags` and `Tag.artifacts` relationships
- `skillmeat/cache/migrations/versions/{timestamp}_migrate_artifact_tags_to_uuid.py` — New migration

**Implementation Notes**:
- The existing `_migrate_artifact_tags_fk()` function (models.py:2931) was a one-time runtime fix that removed an incorrect FK. After this migration, the `artifact_tags` table has a correct FK — the runtime migration function can be removed (or left as a no-op if it guards against the old schema; assess in CAI-P5-08).
- `collection_id` is NOT on `artifact_tags` (it's on `artifact_id` via `collection_artifacts`). The `artifact_uuid` FK already scopes to a single artifact identity globally — no `collection_id` needed here.
- `Artifact.tags` secondaryjoin and `Tag.artifacts` secondaryjoin both reference `artifact_id` in the current ORM (models.py:299-308, 1132-1134). Both must be updated to `artifact_uuid`.

**Estimate**: 2 story points

---

### CAI-P5-04: Update Repository Layer to Query via UUID

**Description**: Update all repository methods in `skillmeat/cache/repositories.py` (and any sibling repository modules) that query `collection_artifacts`, `group_artifacts`, or `artifact_tags` using `artifact_id` string comparisons. After the schema migration these columns no longer exist — all queries must join through `artifacts.uuid`.

**Acceptance Criteria**:
- [ ] All repository query methods referencing `CollectionArtifact.artifact_id`, `GroupArtifact.artifact_id`, or `ArtifactTag.artifact_id` updated to use `*.artifact_uuid`
- [ ] Queries that previously looked up by `artifact_id` string now first resolve `type:name` → UUID via `CachedArtifact.uuid`, then filter on `artifact_uuid`
- [ ] No N+1 queries introduced — use `joinedload()` or `selectinload()` where appropriate
- [ ] Repository methods that return `artifact_id` in DTO output now return the `type:name` string by joining back to `artifacts.id` (external contract unchanged)
- [ ] All existing repository unit tests pass without modification to test expectations
- [ ] `mypy skillmeat --ignore-missing-imports` passes

**Key Files to Modify**:
- `skillmeat/cache/repositories.py` — Update all join table queries
- Any additional repository modules under `skillmeat/cache/` that query these tables

**Implementation Notes**:
- Pattern for UUID resolution: `session.query(CachedArtifact).filter_by(id=artifact_id, collection_id=collection_id).one().uuid` — but prefer joining in a single query to avoid extra round trips.
- Service layer already resolves `type:name` to UUID for `CompositeMembership` (Phase 1 work). The same pattern applies here: repository accepts `artifact_id` (type:name) as input, resolves internally.
- Pagination cursors that encoded `artifact_id` strings must be updated to use `artifact_uuid` as the cursor key (or remain `artifact_id` externally and resolve on decode).

**Estimate**: 3 story points

---

### CAI-P5-05: Verify Service and API Layer Correctness

**Description**: After repository changes, verify all service layer methods and API endpoints that surface collection membership, tags, and groups still return correct results. No API surface changes — all external responses continue to use `type:name` identifiers.

**Acceptance Criteria**:
- [ ] All `/api/v1/artifacts/{artifact_id}` endpoints return correct tag and group membership data
- [ ] All `/api/v1/collections/{collection_id}/artifacts` endpoints return correct artifact lists
- [ ] All `/api/v1/groups/{group_id}/artifacts` endpoints return correct ordered artifact lists
- [ ] Tag assignment and removal endpoints function correctly (POST/DELETE on artifact tags)
- [ ] Group membership add/remove endpoints function correctly
- [ ] Collection artifact add/remove endpoints function correctly
- [ ] Response payloads continue to include `artifact_id` as `type:name` (UUID not exposed externally)
- [ ] No 500 errors from missing column references after schema migration
- [ ] Manual smoke test against running dev API confirms all above

**Key Files to Modify** (verify only, modify if bugs found):
- `skillmeat/core/services/` — Review methods that call updated repository methods
- `skillmeat/api/routers/` — Confirm endpoints still wire correctly to service layer

**Implementation Notes**:
- If service layer already uses repository DTOs (not raw ORM objects), changes may be minimal or zero — verify by reading service method signatures vs repository return types.
- Endpoint smoke test commands to run: see `skillmeat web dev --api-only` and hit relevant endpoints with `curl` or `httpx`.
- Any endpoint that queries `artifact_id` in a URL path must resolve via service layer to UUID before hitting repository — verify this resolution path is still intact.

**Estimate**: 2 story points

---

### CAI-P5-06: Assess and Implement PK Change (type:name → Unique Index)

**Description**: ADR-007 specifies that in Phase 2, `type:name` should become a unique index instead of the primary key on `artifacts`, with UUID becoming the PK candidate. This task assesses feasibility given the SQLAlchemy relationship graph and either implements or defers with documented rationale.

**Acceptance Criteria** (one of two outcomes):

**Outcome A — Implemented**:
- [ ] `artifacts.id` (`type:name`) demoted from PK to `UNIQUE NOT NULL` indexed column
- [ ] `artifacts.uuid` promoted to PK
- [ ] All `ForeignKey("artifacts.id", ...)` references migrated to `ForeignKey("artifacts.uuid", ...)`
- [ ] SQLAlchemy `mapper_registry` and all `Mapped[]` relationship definitions updated
- [ ] Alembic migration applies and rolls back cleanly
- [ ] All existing tests pass

**Outcome B — Deferred**:
- [ ] Written assessment committed to `docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md` under "Phase 2 Assessment" section
- [ ] Assessment covers: FK dependency graph (which models reference `artifacts.id`), risk surface, SQLAlchemy mapper complications, estimated effort
- [ ] Decision: keep `artifacts.id` as PK; `artifacts.uuid` remains unique indexed secondary column
- [ ] ADR status updated to reflect decision

**Key Files to Modify** (if Outcome A):
- `skillmeat/cache/models.py` — `CachedArtifact` PK change + all FK updates
- `skillmeat/cache/migrations/versions/{timestamp}_promote_artifact_uuid_to_pk.py` — New migration

**Implementation Notes**:
- Models known to FK `artifacts.id`: `ArtifactMetadata`, `ArtifactVersion`. After Phase 5, join tables will use `artifacts.uuid`. Check for any remaining `artifacts.id` FKs.
- `ArtifactVersion` already uses `uuid.uuid4().hex` as its own PK — it FKs to `artifacts.id` for the artifact relationship. If `artifacts.id` becomes a non-PK unique column, `ArtifactVersion.artifact_id` FK must be updated.
- Risk: if any query uses `artifacts.id` as the ORM identity column for session identity maps, changing PK will break session caching. Assess carefully.
- Default posture: if >2 days of SQLAlchemy mapper refactoring required, choose Outcome B and document.

**Estimate**: 3 story points

---

### CAI-P5-07: Comprehensive Regression Tests

**Description**: Write and run a full regression test suite covering all three migrated join tables, repository methods, and API endpoints. Can run in parallel with CAI-P5-06.

**Acceptance Criteria**:
- [ ] Test file: `tests/test_uuid_migration_regression.py`
- [ ] Tests cover all three join tables:
  - `collection_artifacts`: add artifact, query collection membership, remove artifact, verify cascade delete
  - `group_artifacts`: add to group, query ordered members, remove, verify cascade delete
  - `artifact_tags`: tag artifact, query by tag, untag, verify cascade delete on artifact deletion
- [ ] Cascade delete verified: deleting `CachedArtifact` cascades to all three join tables
- [ ] Rename-safety verified: changing `artifacts.id` (type:name) does not break UUID-based join table rows
- [ ] Orphan prevention verified: inserting a join table row with a nonexistent `artifact_uuid` raises FK error
- [ ] API integration tests: all relevant endpoints return correct results post-migration
- [ ] Migration integration test: `alembic upgrade head` followed by `alembic downgrade -3` (three steps) leaves DB in pre-Phase-5 state
- [ ] Code coverage >80% for all repository methods touching migrated tables
- [ ] All existing test suites continue to pass: `pytest tests/ -v`

**Key Files to Create/Modify**:
- `tests/test_uuid_migration_regression.py` — New test file
- `tests/conftest.py` — Add fixtures for UUID-based artifact creation if not already present

**Implementation Notes**:
- Use the same pytest SQLAlchemy session fixture pattern established in Phase 1 (`tests/test_composite_memberships.py`)
- Parameterize tests across all three join tables where logic is identical (create/query/delete/cascade)
- API integration tests should use `httpx` against a test FastAPI app instance, not the running dev server

**Estimate**: 2 story points

---

### CAI-P5-08: Retire Phase 1 Compatibility Layer

**Description**: Remove any dual-path code, compatibility shims, or transitional helpers introduced during Phase 1 (or earlier) that are no longer needed now that all join tables use UUID FKs. This is a cleanup task with low risk.

**Acceptance Criteria**:
- [ ] `_migrate_artifact_tags_fk()` function in `models.py` assessed: if it is now a no-op (artifact_tags FK is correct post-Phase-5), remove it and remove the call site in `_run_compatibility_migrations()` (models.py:3022)
- [ ] Any Phase 1 service layer shims that maintained dual type:name/UUID lookup paths reviewed and simplified
- [ ] Dead code paths identified via `mypy` and `flake8` and removed
- [ ] `_run_compatibility_migrations()` function updated or removed if all compatibility migrations are now superseded by proper Alembic migrations
- [ ] ADR-007 "Implementation Timeline" checklist updated to mark all Phase 2 items complete
- [ ] All tests continue to pass after removal

**Key Files to Modify**:
- `skillmeat/cache/models.py` — Remove `_migrate_artifact_tags_fk()` and call site if superseded
- `skillmeat/core/services/` — Remove any UUID/type:name dual-path shims
- `docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md` — Update Phase 2 checklist

**Implementation Notes**:
- Be conservative: if any compatibility function has a guard condition that still fires in some edge case (e.g., old SQLite DBs), keep it with a deprecation warning rather than hard-delete.
- This task cannot start until CAI-P5-06 (PK assessment) and CAI-P5-07 (regression tests) are both complete.

**Estimate**: 1 story point

---

## Parallelization Strategy

```yaml
parallelization:
  batch_1:
    tasks: [CAI-P5-01]
    rationale: "First migration — foundation for subsequent batches"
  batch_2:
    tasks: [CAI-P5-02]
    rationale: "Sequential to batch_1 — avoid Alembic chain conflicts"
  batch_3:
    tasks: [CAI-P5-03]
    rationale: "Sequential to batch_2 — clean Alembic revision chain"
  batch_4:
    tasks: [CAI-P5-04, CAI-P5-05]
    rationale: "Repository and service layer updates can proceed in parallel once schema is stable"
  batch_5:
    tasks: [CAI-P5-06, CAI-P5-07]
    rationale: "PK assessment and regression tests are independent — run in parallel"
  batch_6:
    tasks: [CAI-P5-08]
    rationale: "Cleanup depends on P5-06 (decision) and P5-07 (tests passing)"
  critical_path: [CAI-P5-01, CAI-P5-02, CAI-P5-03, CAI-P5-04, CAI-P5-07]
```

---

## Orchestration Quick Reference

```python
# batch_1
Task("data-layer-expert",
     "Migrate collection_artifacts join table to use artifact_uuid FK. "
     "Follow CAI-P5-01 spec in phase-5-uuid-migration.md. "
     "Files: skillmeat/cache/models.py, skillmeat/cache/migrations/versions/. "
     "Pattern: ADR-007 (docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md). "
     "Shadow-column rollback strategy required for down migration.")

# batch_2 (after batch_1 complete)
Task("data-layer-expert",
     "Migrate group_artifacts join table to use artifact_uuid FK. "
     "Follow CAI-P5-02 spec in phase-5-uuid-migration.md. "
     "Same pattern as CAI-P5-01. Preserve position/CheckConstraint. "
     "Files: skillmeat/cache/models.py, new Alembic migration.")

# batch_3 (after batch_2 complete)
Task("data-layer-expert",
     "Migrate artifact_tags join table to use artifact_uuid FK. "
     "Follow CAI-P5-03 spec in phase-5-uuid-migration.md. "
     "Note: existing _migrate_artifact_tags_fk() at models.py:2931 is superseded. "
     "Update Artifact.tags and Tag.artifacts relationships at models.py:299-308, 1132-1134.")

# batch_4 (after batch_3 complete, tasks in parallel)
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

# batch_5 (after batch_4 complete, tasks in parallel)
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

# batch_6 (after batch_5 complete)
Task("python-backend-engineer",
     "Retire Phase 1 compatibility layer. "
     "Follow CAI-P5-08 spec in phase-5-uuid-migration.md. "
     "Remove _migrate_artifact_tags_fk() if superseded. "
     "Update ADR-007 Phase 2 checklist.")
```

---

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-P5-1 | All three join tables (`collection_artifacts`, `group_artifacts`, `artifact_tags`) use `artifact_uuid` FK with `ondelete="CASCADE"` |
| SC-P5-2 | Cascading deletes verified: deleting a `CachedArtifact` removes all join table rows across all three tables |
| SC-P5-3 | All Alembic migrations apply cleanly (`alembic upgrade head`) and roll back cleanly (`alembic downgrade -3` from head) |
| SC-P5-4 | No API surface changes — external consumers continue to receive `type:name` identifiers |
| SC-P5-5 | No regression in collection management, tagging, or grouping features (all endpoint tests pass) |
| SC-P5-6 | Decision on `artifacts.id` PK demotion documented in ADR-007 with rationale (Outcome A or B) |
| SC-P5-7 | >80% test coverage on all repository methods that touch migrated tables |

---

## Files Modified

```
skillmeat/cache/models.py
  - CollectionArtifact: artifact_id → artifact_uuid with FK
  - GroupArtifact: artifact_id → artifact_uuid with FK
  - ArtifactTag: artifact_id → artifact_uuid with FK; PK updated
  - Artifact.tags, Tag.artifacts relationships: updated secondaryjoin
  - Collection.artifacts relationship: updated primaryjoin
  - _migrate_artifact_tags_fk(): removed if superseded (CAI-P5-08)
  - CachedArtifact: uuid promoted to PK if CAI-P5-06 Outcome A

skillmeat/cache/migrations/versions/
  - {ts}_migrate_collection_artifacts_to_uuid.py   (CAI-P5-01)
  - {ts}_migrate_group_artifacts_to_uuid.py        (CAI-P5-02)
  - {ts}_migrate_artifact_tags_to_uuid.py          (CAI-P5-03)
  - {ts}_promote_artifact_uuid_to_pk.py            (CAI-P5-06, if Outcome A)

skillmeat/cache/repositories.py
  - All query methods on collection_artifacts, group_artifacts, artifact_tags

skillmeat/core/services/
  - Any UUID/type:name dual-path shims (CAI-P5-08 cleanup)

tests/
  - tests/test_uuid_migration_regression.py        (CAI-P5-07)
  - tests/conftest.py                              (UUID-aware fixtures if needed)

docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md
  - Phase 2 checklist updated (CAI-P5-08)
  - PK decision documented (CAI-P5-06)
```

---

## Implementation Notes

### Alembic Migration Chain

Migrations must be strictly sequential (batch_1 → batch_2 → batch_3) because:
- Each migration generates a `revision` with a `down_revision` pointing to the previous
- Parallel Alembic migrations create branching history that requires manual merge
- Three separate migrations (one per table) give clean, reversible steps

Review existing migration style in `skillmeat/cache/migrations/versions/` before generating. Use `op.create_table()` / `op.drop_table()` or `op.add_column()` / `op.drop_column()` as appropriate.

### Shadow-Column Rollback Strategy

Each `upgrade()` must preserve enough data for `downgrade()` to restore the original state:

```python
# In upgrade()
# 1. Rename artifact_id to _artifact_id_backup
op.alter_column("collection_artifacts", "artifact_id",
                new_column_name="_artifact_id_backup")
# 2. Add artifact_uuid column
op.add_column("collection_artifacts",
              sa.Column("artifact_uuid", sa.String(), nullable=True))
# 3. Backfill artifact_uuid from artifacts.uuid via _artifact_id_backup
op.execute("""
    UPDATE collection_artifacts ca
    SET artifact_uuid = a.uuid
    FROM artifacts a
    WHERE a.id = ca._artifact_id_backup
""")
# 4. Delete orphan rows (no matching artifact)
op.execute("""
    DELETE FROM collection_artifacts WHERE artifact_uuid IS NULL
""")
# 5. Set NOT NULL
op.alter_column("collection_artifacts", "artifact_uuid", nullable=False)
# 6. Add FK constraint
op.create_foreign_key("fk_ca_artifact_uuid", "collection_artifacts",
                      "artifacts", ["artifact_uuid"], ["uuid"],
                      ondelete="CASCADE")

# In downgrade()
# 1. Drop FK
op.drop_constraint("fk_ca_artifact_uuid", "collection_artifacts")
# 2. Rename _artifact_id_backup back to artifact_id
op.alter_column("collection_artifacts", "_artifact_id_backup",
                new_column_name="artifact_id")
# 3. Drop artifact_uuid
op.drop_column("collection_artifacts", "artifact_uuid")
```

SQLite note: SQLite does not support `ALTER TABLE ... DROP COLUMN` or `ALTER CONSTRAINT`. If the test database uses SQLite, use the table-rebuild approach (rename → create new → copy → drop old) for each migration step. See `_migrate_artifact_tags_fk()` in `models.py:2965` for the existing SQLite-compatible pattern.

### Repository Query Pattern

After migration, resolve `type:name` → UUID within the repository using a subquery join, not a separate lookup:

```python
# Before (string comparison)
session.query(CollectionArtifact).filter_by(
    collection_id=collection_id,
    artifact_id=artifact_id  # type:name string
)

# After (UUID join)
session.query(CollectionArtifact).join(
    CachedArtifact,
    CachedArtifact.uuid == CollectionArtifact.artifact_uuid
).filter(
    CollectionArtifact.collection_id == collection_id,
    CachedArtifact.id == artifact_id  # resolve type:name via join
)
```

### ORM Relationship Updates

After `CollectionArtifact.artifact_uuid` replaces `artifact_id`, the `Collection.artifacts` relationship `primaryjoin` must be updated:

```python
# Before
primaryjoin="foreign(CollectionArtifact.artifact_id) == Artifact.id"

# After
primaryjoin="CollectionArtifact.artifact_uuid == foreign(Artifact.uuid)"
```

Similarly for `Artifact.tags` (models.py:307-308) and `Tag.artifacts` (models.py:1132-1134).

---

## Known Gotchas

1. **SQLite ALTER TABLE limitations**: SQLite does not support dropping columns or modifying FK constraints in-place. Use the rename/create/copy/drop pattern (same as `_migrate_artifact_tags_fk()` at models.py:2965) for SQLite compatibility in CI tests.

2. **Orphan rows during backfill**: Some `artifact_id` values in join tables may not match any current `CachedArtifact.id` (external marketplace artifacts, stale data). These cannot be given a UUID FK. They must be deleted during migration. Log each deletion with artifact_id so users can recover if needed.

3. **Sequential migration requirement**: All three migrations must form a linear Alembic chain. Generate them one at a time, not in parallel. If two agents generate migrations concurrently, Alembic will create a branch that requires `alembic merge` before `upgrade head` will work.

4. **Collection.artifacts relationship scope**: `CollectionArtifact` is both a join table and a rich metadata table (description, author, tags_json, etc.). The ORM relationship must be updated carefully — the `secondary` and `primaryjoin` are currently string references (lazy-eval). Test relationship loading after model update.

5. **CAI-P5-06 risk**: Promoting `artifacts.uuid` to PK requires updating `ArtifactVersion.artifact_id` FK (currently points to `artifacts.id`). `ArtifactVersion` uses `uuid.uuid4().hex` for its own PK — study this model carefully before attempting PK swap. If `artifacts.id` is used as SQLAlchemy's identity map key, changing PK will invalidate all in-flight session caches.

6. **`_migrate_artifact_tags_fk()` at models.py:2931**: This runtime function was added to fix a schema inconsistency without Alembic. After Phase 5, `artifact_tags` has a correct FK via Alembic. Ensure `_run_compatibility_migrations()` (models.py:3022) no longer calls this function, or that the function safely no-ops when the new schema is detected.

7. **Frontend hooks**: Frontend queries collection membership and tags via API endpoints — they do not touch the DB join tables directly. API surface is unchanged, so frontend impact is zero. Verify with a smoke test of the web UI after migration, but no frontend code changes are expected.

---

## Phase 5 Quality Gates

Before this phase can be marked complete:

- [ ] All three Alembic migrations apply cleanly to a fresh database: `alembic upgrade head`
- [ ] All three Alembic migrations roll back cleanly: `alembic downgrade -3`
- [ ] FK constraint violations are enforced: inserting a row with a nonexistent `artifact_uuid` raises an error
- [ ] Cascade deletes verified: `session.delete(artifact); session.commit()` removes all join table rows for that artifact
- [ ] All existing tests pass: `pytest tests/ -v`
- [ ] Regression test suite passes: `pytest tests/test_uuid_migration_regression.py -v`
- [ ] Code coverage >80% for migrated repository methods: `pytest --cov=skillmeat --cov-report=term-missing`
- [ ] Type checking passes: `mypy skillmeat --ignore-missing-imports`
- [ ] ADR-007 Phase 2 checklist updated with outcome of CAI-P5-06

---

## Completion Notes

_To be filled in after phase execution._

- [ ] Actual duration vs estimate
- [ ] CAI-P5-06 outcome (Outcome A or B, rationale)
- [ ] Orphan rows found and deleted during backfill (count per table)
- [ ] Any gotchas not anticipated above
- [ ] Follow-up work identified (if any)

---

**Phase 5 Status**: Planning
**Estimated Completion**: 4-6 days from start (after Phase 4 complete)
**Previous Phase**: Phase 4 - Web UI Relationship Browsing
**ADR Reference**: `docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md` — Phase 2 section
