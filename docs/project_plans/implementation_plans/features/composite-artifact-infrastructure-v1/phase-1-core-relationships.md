---
title: 'Phase 1: Core Relationships (Database & ORM)'
description: 'Database foundation for composite memberships: UUID identity column,
  schema, ORM models, repository layer'
audience:
- ai-agents
- developers
tags:
- implementation
- phase-1
- database
- orm
- repository
- uuid
- migrations
created: 2026-02-17
updated: 2026-02-18
category: product-planning
status: inferred_complete
related:
- /docs/project_plans/implementation_plans/features/composite-artifact-infrastructure-v1.md
- /docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md
---
# Phase 1: Core Relationships (Database & ORM)

**Phase ID**: CAI-P1
**Duration**: 3-4 days
**Dependencies**: None
**Assigned Subagent(s)**: data-layer-expert, python-backend-engineer
**Estimated Effort**: 14 story points
**Total Tasks**: 9

---

## Phase Overview

Phase 1 establishes the database foundation for the entire Composite Artifact Infrastructure. This phase:

1. Adds `COMPOSITE` to the `ArtifactType` enum and introduces `CompositeType` enum (initial value: `PLUGIN`), auditing all call sites for exhaustiveness
2. Adds a stable `uuid` column to `CachedArtifact` (ADR-007) and migrates existing rows
3. Defines `CompositeArtifact` (with `composite_type` field referencing `CompositeType`) and `CompositeMembership` ORM models using UUID FK for relational integrity
4. Generates two separate Alembic migrations (UUID column, composite tables) for clean rollback
5. Implements repository CRUD and service-layer `type:name` -> UUID resolution
6. Writes UUID into filesystem manifests (`.skillmeat-deployed.toml`, `manifest.toml`) additively
7. Provides comprehensive unit and integration tests

This phase incorporates the design from **ADR-007: Internal UUID Identity for Artifacts**, which introduces a `uuid` column on `CachedArtifact` as the stable relational identity for `CompositeMembership`, replacing the fragile `type:name` string FK pattern used in existing join tables.

This is a critical phase because all downstream work (discovery, import orchestration, API endpoints, UI) depends on these database structures being stable and well-tested.

---

## Parallelization Strategy

```yaml
parallelization:
  batch_1:
    tasks: [CAI-P1-01, CAI-P1-02]
    note: "Independent — enum addition and UUID column are separate concerns"
  batch_2:
    tasks: [CAI-P1-03]
    note: "UUID migration must apply before composite tables reference artifacts.uuid"
  batch_3:
    tasks: [CAI-P1-04, CAI-P1-07]
    note: "Composite ORM model + filesystem UUID writes are independent after migration"
  batch_4:
    tasks: [CAI-P1-05, CAI-P1-06]
    note: "Composite migration runs after model defined; repository runs after migration"
  batch_5:
    tasks: [CAI-P1-08, CAI-P1-09]
    note: "Unit and integration tests run after repository complete"
  critical_path: [CAI-P1-02, CAI-P1-03, CAI-P1-04, CAI-P1-05, CAI-P1-06, CAI-P1-08]
```

---

## Task Breakdown

### CAI-P1-01: Add COMPOSITE to ArtifactType Enum + CompositeType Enum

**Assigned**: data-layer-expert
**Effort**: 1 story point
**Priority**: critical
**Dependencies**: none

**Description**: Add `COMPOSITE` value to the `ArtifactType` enum. Create a new `CompositeType` enum with initial value `PLUGIN = "plugin"`. Add `composite_types()` class method to `ArtifactType`. Update `deployable_types()` to include `COMPOSITE`. Audit all call sites to ensure exhaustive handling of the new enum value.

**Acceptance Criteria**:
- [ ] `COMPOSITE = "composite"` added to `ArtifactType` enum
- [ ] `CompositeType` enum created with `PLUGIN = "plugin"` (same module or new `skillmeat/core/composite_types.py`)
- [ ] `composite_types()` class method added to `ArtifactType` returning types that are composites
- [ ] `deployable_types()` updated to include `COMPOSITE`
- [ ] Enum values serialize/deserialize correctly (JSON, database)
- [ ] All match/if-elif chains checking `ArtifactType` are exhaustive and handle `COMPOSITE`
- [ ] Type-checking passes: `mypy skillmeat --ignore-missing-imports`
- [ ] All existing tests pass with no regressions
- [ ] Docstring updated noting that `COMPOSITE` is a deployable composite type; `CompositeType` determines variant-specific behavior; `STACK`/`SUITE` reserved for future `CompositeType` values

**Key Files to Modify**:
- `skillmeat/core/artifact_detection.py` — Add `COMPOSITE` to `ArtifactType` enum, add `composite_types()`, update `deployable_types()`
- `skillmeat/core/composite_types.py` (or same module) — Define `CompositeType` enum
- All callers (search for `ArtifactType.` in codebase):
  - `skillmeat/core/importer.py`
  - `skillmeat/core/sync.py`
  - `skillmeat/core/sharing/bundle.py`
  - `skillmeat/api/schemas/` — Response DTOs
  - `skillmeat/cache/models.py` — Column type definitions
  - Any controller/service code handling artifact type switches

**Implementation Notes**:
- `COMPOSITE` is a deployable artifact type — it appears in `deployable_types()`. Deployment of a composite deploys its children.
- `CompositeType` determines variant-specific deployment behavior (e.g., `PLUGIN` composites install all children into a project's `.claude/` directory).
- Run `mypy skillmeat --ignore-missing-imports` before considering complete
- No UI changes in this task; purely type layer

---

### CAI-P1-02: Add uuid Column to CachedArtifact

**Assigned**: data-layer-expert
**Effort**: 1 story point
**Priority**: critical
**Dependencies**: none

**Description**: Add a `uuid` column to the `CachedArtifact` ORM model in `skillmeat/cache/models.py`. This column provides the stable relational identity required by ADR-007 for `CompositeMembership` FK constraints.

**Acceptance Criteria**:
- [ ] `uuid` column defined with `String`, `unique=True`, `nullable=False`, `index=True`
- [ ] Default is `lambda: uuid.uuid4().hex` (32-char hex string)
- [ ] Column does not replace `id` (type:name remains primary key)
- [ ] Model can be imported without errors
- [ ] No schema validation errors

**Key Files to Modify**:
- `skillmeat/cache/models.py` — Add `uuid` column to `CachedArtifact`

**Reference (from ADR-007)**:
```python
class CachedArtifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Keep: type:name
    uuid: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, default=lambda: uuid.uuid4().hex, index=True
    )
    # ... existing fields unchanged
```

**Implementation Notes**:
- Do not generate or apply the Alembic migration in this task; that is CAI-P1-03
- The `uuid` import (`import uuid`) must be added to models.py if not present

---

### CAI-P1-03: Alembic Migration — Add uuid Column + Backfill

**Assigned**: data-layer-expert
**Effort**: 2 story points
**Priority**: critical
**Dependencies**: CAI-P1-02

**Description**: Generate and validate an Alembic migration that adds the `uuid` column to `artifacts`, backfills all existing rows with generated UUIDs, and creates the unique index. This migration is separate from the composite tables migration (CAI-P1-05) to allow clean rollback of each change independently.

**Acceptance Criteria**:
- [ ] Migration file generated in `skillmeat/cache/migrations/versions/`
- [ ] Migration name clearly indicates purpose: e.g., `add_artifact_uuid_column`
- [ ] `upgrade()` adds column as nullable, backfills existing rows, then applies NOT NULL + unique index
- [ ] `downgrade()` drops column and index cleanly
- [ ] `alembic upgrade head` succeeds on fresh DB
- [ ] `alembic upgrade head` succeeds on DB with pre-existing artifact rows (backfill works)
- [ ] `alembic downgrade -1` leaves DB in pre-migration state
- [ ] No existing artifact rows are deleted or corrupted

**Key Files to Modify**:
- `skillmeat/cache/migrations/versions/{timestamp}_add_artifact_uuid_column.py` — New migration

**Implementation Steps**:
1. Ensure CAI-P1-02 model change is in place
2. Run `alembic revision --autogenerate -m "add artifact uuid column"`
3. Review generated migration; the autogenerate may not handle the backfill
4. Manually add backfill logic in `upgrade()`:
   ```python
   # Add as nullable first
   op.add_column("artifacts", sa.Column("uuid", sa.String(), nullable=True))
   # Backfill existing rows
   op.execute("UPDATE artifacts SET uuid = lower(hex(randomblob(16))) WHERE uuid IS NULL")
   # Apply NOT NULL constraint and unique index
   op.alter_column("artifacts", "uuid", nullable=False)
   op.create_index("ix_artifacts_uuid", "artifacts", ["uuid"], unique=True)
   ```
   Adjust `UPDATE` SQL to match the target DB dialect (SQLite vs PostgreSQL)
5. Write reversible `downgrade()`:
   ```python
   op.drop_index("ix_artifacts_uuid", table_name="artifacts")
   op.drop_column("artifacts", "uuid")
   ```
6. Test both directions on a DB with existing rows

**Gotcha**: The backfill SQL differs by dialect. For PostgreSQL use `gen_random_uuid()` or `uuid_generate_v4()`; for SQLite use `hex(randomblob(16))`. Detect dialect in migration if targeting both.

---

### CAI-P1-04: Define CompositeArtifact and CompositeMembership ORM Models

**Assigned**: data-layer-expert
**Effort**: 2 story points
**Priority**: high
**Dependencies**: CAI-P1-01, CAI-P1-03

**Description**: Define `CompositeArtifact` and `CompositeMembership` ORM models in `skillmeat/cache/models.py` using UUID FK to `artifacts.uuid`. The `CompositeArtifact` model includes a `composite_type` field referencing the `CompositeType` enum (default `PLUGIN`). The `child_artifact_uuid` FK must use `ondelete="CASCADE"` so memberships are automatically removed when a child artifact is deleted.

**Acceptance Criteria**:
- [ ] `CompositeArtifact` model defined with:
  - `id: str` — `type:name` primary key (e.g., `composite:my-plugin`)
  - `collection_id: str` — non-null, identifies owning collection
  - `composite_type: str` — references `CompositeType` enum, default `"plugin"`
  - Metadata fields: `display_name`, `description`, `metadata_json` (optional)
  - Timestamps: `created_at`, `updated_at`
  - Bidirectional relationship to `CompositeMembership`
- [ ] `CompositeMembership` model defined per ADR-007 schema:
  - `collection_id: str` — primary key component
  - `composite_id: str` — FK to `composite_artifacts.id`, primary key component, `ondelete="CASCADE"`
  - `child_artifact_uuid: str` — FK to `artifacts.uuid`, primary key component, `ondelete="CASCADE"`
  - `child_artifact` relationship with `foreign_keys=[child_artifact_uuid]`, `lazy="joined"` for eager loading
  - `relationship_type: str` — default `"contains"`; allow `"requires"`, `"extends"` for future
  - `pinned_version_hash: Optional[str]` — nullable
  - `membership_metadata: Optional[str]` — nullable Text for future extension
  - `created_at: datetime`
- [ ] Bidirectional relationship on `CachedArtifact`: `composite_memberships` collection
- [ ] Models use `Mapped` types and `mapped_column()` (SQLAlchemy 2.0+)
- [ ] Models import without errors
- [ ] Docstrings explain FK semantics, cascade rules, UUID identity rationale, and `CompositeType` usage

**Key Files to Modify**:
- `skillmeat/cache/models.py` — Add `CompositeArtifact`, `CompositeMembership`, relationship on `CachedArtifact`

**Reference (from ADR-007)**:
```python
class CompositeMembership(Base):
    __tablename__ = "composite_memberships"

    collection_id: Mapped[str] = mapped_column(String, primary_key=True)
    composite_id: Mapped[str] = mapped_column(
        ForeignKey("composite_artifacts.id", ondelete="CASCADE"), primary_key=True
    )
    child_artifact_uuid: Mapped[str] = mapped_column(
        String,
        ForeignKey("artifacts.uuid", ondelete="CASCADE"),
        primary_key=True,
    )
    relationship_type: Mapped[str] = mapped_column(String, default="contains")
    pinned_version_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    membership_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    child_artifact: Mapped["CachedArtifact"] = relationship(
        "CachedArtifact",
        foreign_keys=[child_artifact_uuid],
        lazy="joined"
    )
```

**Gotcha**: Bidirectional relationships with non-standard FKs need explicit `foreign_keys=` on both sides. SQLAlchemy will raise `AmbiguousForeignKeysError` if `CachedArtifact` has multiple FKs to `composite_memberships` without explicit specification.

---

### CAI-P1-05: Alembic Migration — Composite Tables

**Assigned**: data-layer-expert
**Effort**: 1 story point
**Priority**: high
**Dependencies**: CAI-P1-04

**Description**: Generate and validate a second Alembic migration that creates the `composite_artifacts` and `composite_memberships` tables. This is a separate migration from CAI-P1-03 so each can be rolled back independently.

**Acceptance Criteria**:
- [ ] Migration file generated in `skillmeat/cache/migrations/versions/`
- [ ] Migration name clearly indicates purpose: e.g., `add_composite_artifact_tables`
- [ ] `upgrade()` creates `composite_artifacts` then `composite_memberships` (FK order matters)
- [ ] `composite_memberships.child_artifact_uuid` has FK to `artifacts.uuid` (not `artifacts.id`)
- [ ] Composite PK on `composite_memberships` prevents duplicate membership rows
- [ ] Indexes support parent (`composite_id`) and child (`child_artifact_uuid`) lookups
- [ ] `downgrade()` drops tables in reverse order (memberships before composites)
- [ ] `alembic upgrade head` succeeds on fresh DB
- [ ] `alembic downgrade -1` leaves DB in pre-migration state

**Key Files to Modify**:
- `skillmeat/cache/migrations/versions/{timestamp}_add_composite_artifact_tables.py` — New migration

**Implementation Notes**:
- Review autogenerated migration carefully; ensure FK target is `artifacts.uuid`, not `artifacts.id`
- Run `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` to verify idempotence

---

### CAI-P1-06: Composite Membership Repository and Service-Layer Resolution

**Assigned**: python-backend-engineer
**Effort**: 2 story points
**Priority**: high
**Dependencies**: CAI-P1-05

**Description**: Implement CRUD operations for `CompositeMembership` in the repository layer and implement `type:name` -> UUID resolution in the service layer. The external API surface (and CLI) continues to use `type:name`; the service layer resolves to UUID internally before writing to DB.

**Acceptance Criteria**:
- [ ] Repository methods in `skillmeat/cache/repositories.py` (or new `composite_repository.py`):
  - `get_children_of(composite_id: str, collection_id: str) -> List[MembershipRecord]`
  - `get_parents_of(child_artifact_uuid: str, collection_id: str) -> List[MembershipRecord]`
  - `create_membership(collection_id, composite_id, child_artifact_uuid, relationship_type, pinned_version_hash) -> MembershipRecord`
  - `delete_membership(composite_id, child_artifact_uuid) -> bool`
  - All methods return DTOs, not raw ORM objects
  - All methods handle `IntegrityError` and raise domain exceptions
- [ ] Service-layer function (new file: `skillmeat/core/services/composite_service.py`):
  - `add_composite_member(collection_id, composite_id, child_artifact_id: str, pinned_version_hash) -> MembershipRecord`
  - Resolves `child_artifact_id` (type:name) -> `child_artifact.uuid` via `artifacts_repo.get_by_id()`
  - Raises `ArtifactNotFoundError` if type:name does not resolve
  - Calls repository `create_membership` with resolved UUID
- [ ] `get_associations(artifact_type_name: str, collection_id: str) -> AssociationResult` returning `{"parents": [...], "children": [...]}` (for artifact detail view)
- [ ] No circular import issues

**Key Files to Modify/Create**:
- `skillmeat/cache/repositories.py` (or `skillmeat/cache/composite_repository.py`) — Add membership CRUD
- `skillmeat/core/services/composite_service.py` — New service file with type:name -> UUID resolution

**Reference (from ADR-007)**:
```python
def add_composite_member(
    collection_id: str,
    composite_id: str,
    child_artifact_id: str,  # type:name from API
    pinned_version_hash: Optional[str] = None
) -> CompositeMembership:
    child_artifact = artifacts_repo.get_by_id(child_artifact_id, collection_id)
    if not child_artifact:
        raise ArtifactNotFoundError(child_artifact_id)
    membership = CompositeMembership(
        collection_id=collection_id,
        composite_id=composite_id,
        child_artifact_uuid=child_artifact.uuid,
        pinned_version_hash=pinned_version_hash
    )
    return membership
```

**Implementation Notes**:
- Follow existing repository patterns: SQLAlchemy `Session`, transaction handling
- Use `selectinload` or `joinedload` to avoid N+1 queries when loading membership children
- External API callers always pass `type:name`; UUID is an internal DB concern only

---

### CAI-P1-07: Write UUID into Filesystem Manifests

**Assigned**: python-backend-engineer
**Effort**: 1 story point
**Priority**: medium
**Dependencies**: CAI-P1-03

**Description**: Extend deployment and collection operations to write the artifact `uuid` field into `.skillmeat-deployed.toml` and `manifest.toml`. These changes are additive (backward-compatible): old code that reads the files ignores the new field.

**Acceptance Criteria**:
- [ ] During `skillmeat deploy`, the deployed artifact's `uuid` is written to `.skillmeat-deployed.toml`:
  ```toml
  [[deployed]]
  artifact_name = "canvas-design"
  artifact_type = "skill"
  artifact_uuid = "a1b2c3d4e5f6..."  # NEW
  from_collection = "default"
  content_hash = "..."
  ```
- [ ] During collection sync/add, the artifact `uuid` is written to `manifest.toml`:
  ```toml
  [[artifacts]]
  name = "canvas-design"
  type = "skill"
  uuid = "a1b2c3d4e5f6..."  # NEW
  path = "skills/canvas-design/"
  ```
- [ ] Artifacts that have a UUID in DB use it; newly added artifacts get UUID auto-generated on first cache
- [ ] Existing `.skillmeat-deployed.toml` files without `artifact_uuid` are read without error (field optional on read)
- [ ] Existing `manifest.toml` files without `uuid` are read without error (field optional on read)
- [ ] No existing CLI workflows are broken

**Key Files to Modify**:
- `skillmeat/storage/` — Deployment manifest manager (find the module that writes `.skillmeat-deployed.toml`)
- `skillmeat/storage/` — Manifest manager (find the module that writes `manifest.toml`)

**Implementation Notes**:
- Locate the exact write paths by searching for `deployed` TOML write calls and manifest TOML write calls
- The UUID must be fetched from `CachedArtifact.uuid` via the DB cache (not generated fresh)
- If an artifact is not yet in the cache, skip the UUID field (it will be populated on next cache refresh)

---

### CAI-P1-08: Unit Tests — UUID Generation and CompositeMembership CRUD

**Assigned**: python-backend-engineer
**Effort**: 2 story points
**Priority**: medium
**Dependencies**: CAI-P1-06

**Description**: Write unit tests for UUID generation, uniqueness, and `CompositeMembership` CRUD operations. Target >80% coverage for all new code in Phase 1.

**Acceptance Criteria**:
- [ ] Test file: `tests/test_composite_memberships.py`
- [ ] UUID tests:
  - `test_cached_artifact_uuid_generation`: artifact auto-generates 32-char hex UUID on insert
  - `test_uuid_uniqueness`: two artifacts get distinct UUIDs
  - `test_uuid_unique_constraint`: inserting duplicate UUID raises `IntegrityError`
- [ ] `CompositeMembership` model tests:
  - Valid membership creates correctly with correct FK
  - Composite PK prevents duplicate parent-child pairs
  - `relationship_type` defaults to `"contains"`
  - `created_at` auto-set on creation
- [ ] Repository method tests:
  - `create_membership()` creates and returns correct record
  - `create_membership()` raises error on duplicate
  - `get_children_of()` returns correct children
  - `get_parents_of()` returns correct parents
  - `delete_membership()` removes records, returns True
  - `delete_membership()` on non-existent record returns False
  - Methods raise domain exceptions (not raw DB errors)
- [ ] Service-layer tests:
  - `add_composite_member()` resolves type:name to UUID before write
  - `add_composite_member()` raises `ArtifactNotFoundError` for unknown type:name
- [ ] Code coverage >80% for all new membership + UUID code

**Key Files to Create/Modify**:
- `tests/test_composite_memberships.py` — New test file
- `tests/conftest.py` — Add fixtures for test artifacts with UUID

**Reference test patterns from ADR-007**:
```python
def test_cached_artifact_uuid_generation():
    artifact = CachedArtifact(id="skill:test", collection_id="default", ...)
    session.add(artifact)
    session.commit()
    assert artifact.uuid is not None
    assert len(artifact.uuid) == 32
    assert artifact.uuid.isalnum()
```

---

### CAI-P1-09: Integration Tests — FK Constraints, Cascades, Resolution

**Assigned**: python-backend-engineer
**Effort**: 2 story points
**Priority**: medium
**Dependencies**: CAI-P1-08

**Description**: Write integration tests verifying FK constraints are enforced by the database, cascading deletes work correctly, and the service-layer `type:name` -> UUID resolution functions end-to-end.

**Acceptance Criteria**:
- [ ] Test file: `tests/integration/test_composite_memberships_integration.py`
- [ ] FK constraint tests:
  - Attempt to create `CompositeMembership` with non-existent `child_artifact_uuid` -> DB raises FK violation
  - Attempt to create `CompositeMembership` with non-existent `composite_id` -> DB raises FK violation
- [ ] Cascading delete tests:
  - Delete child artifact -> membership rows for that artifact cascade-deleted automatically
  - Delete composite artifact -> membership rows for that composite cascade-deleted automatically
  - Other artifacts' memberships are unaffected
- [ ] type:name -> UUID resolution tests:
  - End-to-end: create artifact, create composite, call service `add_composite_member("skill:canvas-design")`, verify `child_artifact_uuid` stored in DB equals `child_artifact.uuid`
  - Rename scenario: artifact `id` updated (type:name changes), UUID unchanged, membership still resolves correctly via UUID FK
- [ ] Migration round-trip test:
  - DB with pre-existing artifact rows: apply migrations, verify all rows have non-null unique UUIDs
  - Rollback: verify UUID column removed, original data intact
- [ ] No regression in existing artifact queries: `pytest tests/api/test_artifacts.py` passes

**Key Files to Create/Modify**:
- `tests/integration/test_composite_memberships_integration.py` — New test file

**Reference test patterns from ADR-007**:
```python
def test_cascade_delete_on_child_removal():
    child = CachedArtifact(id="skill:child", collection_id="default", ...)
    session.add(child)
    session.commit()

    membership = CompositeMembership(
        collection_id="default", composite_id="composite:test",
        child_artifact_uuid=child.uuid
    )
    session.add(membership)
    session.commit()

    session.delete(child)
    session.commit()

    assert session.query(CompositeMembership).filter_by(
        child_artifact_uuid=child.uuid
    ).count() == 0
```

---

## Success Criteria

- **SC-P1-1**: All existing `CachedArtifact` rows have non-null unique UUID after migration
- **SC-P1-2**: `CompositeMembership` FK constraint enforced by database (insert with bad UUID rejected)
- **SC-P1-3**: Cascading delete removes memberships when child artifact deleted
- **SC-P1-4**: `type:name` -> UUID resolution works correctly in service layer
- **SC-P1-5**: UUID appears in `.skillmeat-deployed.toml` and `manifest.toml` (additive, backward-compatible)
- **SC-P1-6**: Both Alembic migrations apply and rollback cleanly and independently
- **SC-P1-7**: No regression in existing artifact queries/imports (`pytest tests/api/test_artifacts.py`)
- **SC-P1-8**: Repository CRUD >80% test coverage

---

## Phase 1 Quality Gates

Before Phase 2 can begin, all the following must pass:

- [ ] `COMPOSITE` added to `ArtifactType`, `CompositeType` enum created with `PLUGIN`
- [ ] `composite_types()` and `deployable_types()` class methods updated
- [ ] `mypy skillmeat --ignore-missing-imports` passes (enum + model changes)
- [ ] Migration 1 (UUID column) applies cleanly: `alembic upgrade head` on fresh DB
- [ ] Migration 1 backfills existing rows: all `artifacts.uuid` are non-null after upgrade
- [ ] Migration 1 rolls back: `alembic downgrade -1` leaves DB in pre-migration state
- [ ] Migration 2 (composite tables) applies cleanly after Migration 1
- [ ] Migration 2 rolls back independently without affecting Migration 1
- [ ] FK constraint enforced: insert `CompositeMembership` with bad UUID raises DB error
- [ ] Cascade delete verified: deleting artifact removes its memberships
- [ ] Repository CRUD tests pass: `pytest tests/test_composite_memberships.py -v`
- [ ] Integration tests pass: `pytest tests/integration/test_composite_memberships_integration.py -v`
- [ ] No regression: `pytest tests/api/test_artifacts.py -v`
- [ ] Coverage >80%: `pytest --cov=skillmeat --cov-report=term-missing`

---

## Files Modified

- `skillmeat/core/artifact_detection.py` (or wherever `ArtifactType` enum lives) — Add `COMPOSITE`, `composite_types()`, update `deployable_types()`
- `skillmeat/core/composite_types.py` (or same module) — Define `CompositeType` enum with `PLUGIN`
- `skillmeat/cache/models.py` — `CachedArtifact.uuid` column, `CompositeArtifact` (with `composite_type`), `CompositeMembership`, bidirectional relationships
- `skillmeat/cache/migrations/versions/{ts1}_add_artifact_uuid_column.py` — Migration 1: UUID column + backfill
- `skillmeat/cache/migrations/versions/{ts2}_add_composite_artifact_tables.py` — Migration 2: composite tables
- `skillmeat/cache/repositories.py` (or new `composite_repository.py`) — Composite membership CRUD
- `skillmeat/core/services/composite_service.py` — New: type:name -> UUID resolution service
- `skillmeat/storage/` — Deployment manifest UUID writes (`.skillmeat-deployed.toml`)
- `skillmeat/storage/` — Collection manifest UUID writes (`manifest.toml`)
- `tests/test_composite_memberships.py` — New: unit tests
- `tests/integration/test_composite_memberships_integration.py` — New: integration tests
- `tests/conftest.py` — UUID-aware artifact fixtures

---

## Key Gotchas

- **Backfill migration**: UUID column must be added as nullable, backfilled, then made non-null. The SQL for UUID generation differs between SQLite (`hex(randomblob(16))`) and PostgreSQL (`gen_random_uuid()`). Handle both dialects or document the target.
- **Two separate migrations**: One for the UUID column, one for composite tables. Never combine them. Clean rollback of each requires independent migration files.
- **FK target is `artifacts.uuid`, not `artifacts.id`**: `CompositeMembership.child_artifact_uuid` references `artifacts.uuid`. Autogenerated migrations may default to `artifacts.id` — verify manually.
- **Bidirectional relationships**: `CachedArtifact.composite_memberships` <-> `CompositeMembership.child_artifact` require explicit `foreign_keys=` specification on both sides to avoid `AmbiguousForeignKeysError`.
- **Filesystem writes are additive**: `.skillmeat-deployed.toml` and `manifest.toml` gain new optional fields. Old code that reads these files must not break when the field is absent.
- **Service layer owns resolution**: UUID is an internal DB concern. Service functions accept `type:name` from callers and resolve to UUID before any DB write. Repository methods never accept `type:name` as FK input.

---

## Implementation Notes & References

### ADR-007 Design

The full UUID identity design is in `docs/dev/architecture/decisions/ADR-007-artifact-uuid-identity.md`. This ADR defines:
- Exact `CachedArtifact.uuid` column specification
- `CompositeMembership` schema with UUID FK
- Service-layer `type:name` -> UUID resolution pattern
- Filesystem manifest format for UUID fields
- Phase 2 (future): migrate existing join tables (`collection_artifacts`, `group_artifacts`, `artifact_tags`) to UUID FKs

### Existing Patterns to Follow

- **ArtifactVersion UUID pattern**: `skillmeat/cache/models.py` — `ArtifactVersion` already uses `uuid.uuid4().hex` as PK with FK to `artifacts.id`. Same pattern applies here.
- **Timestamp pattern**: Use existing `created_at`, `updated_at` columns from base model or as explicit `mapped_column()` defaults.
- **Repository DTOs**: All public repository methods return DTOs, not ORM objects.
- **Alembic style**: Review existing migrations in `skillmeat/cache/migrations/versions/` for column definitions and index patterns.

### API Surface Unchanged

The external API continues to use `type:name` identifiers in URLs and request/response payloads. UUID is never exposed to API consumers in Phase 1 (optional observability field may be added later). Service layer is the only place UUID resolution occurs.

---

## Orchestration Quick Reference

```python
# Batch 1 — parallel, no dependencies
Task("data-layer-expert",
    "Add COMPOSITE to ArtifactType enum and create CompositeType enum with PLUGIN value. "
    "Add composite_types() class method and update deployable_types() to include COMPOSITE. "
    "Audit all call sites. File: skillmeat/core/artifact_detection.py. "
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
    "Define CompositeArtifact (with composite_type field referencing CompositeType enum, "
    "default PLUGIN) and CompositeMembership ORM models. "
    "Use UUID FK (child_artifact_uuid -> artifacts.uuid, ondelete=CASCADE). "
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
    "Implement composite membership repository CRUD and type:name -> UUID resolution service. "
    "Files: skillmeat/cache/repositories.py and new skillmeat/core/services/composite_service.py. "
    "See phase-1-core-relationships.md CAI-P1-06.")

# Batch 5 — after Batch 4 (parallel)
Task("python-backend-engineer",
    "Write unit tests for UUID generation, uniqueness, CompositeMembership CRUD, "
    "and service-layer resolution. Target >80% coverage. "
    "File: tests/test_composite_memberships.py. See phase-1-core-relationships.md CAI-P1-08.")

Task("python-backend-engineer",
    "Write integration tests: FK constraints, cascading deletes, type:name -> UUID resolution. "
    "File: tests/integration/test_composite_memberships_integration.py. "
    "See phase-1-core-relationships.md CAI-P1-09.")
```

---

## Deliverables Checklist

- [ ] `ArtifactType.COMPOSITE` enum value added and all call sites audited (CAI-P1-01)
- [ ] `CompositeType` enum created with `PLUGIN` value (CAI-P1-01)
- [ ] `composite_types()` and `deployable_types()` class methods updated (CAI-P1-01)
- [ ] `CachedArtifact.uuid` column defined in models.py (CAI-P1-02)
- [ ] Alembic migration 1: UUID column + backfill applied and tested (CAI-P1-03)
- [ ] `CompositeArtifact` (with `composite_type`) and `CompositeMembership` ORM models defined (CAI-P1-04)
- [ ] Alembic migration 2: composite tables applied and tested (CAI-P1-05)
- [ ] Composite membership repository CRUD implemented (CAI-P1-06)
- [ ] Service-layer type:name -> UUID resolution implemented (CAI-P1-06)
- [ ] UUID written to `.skillmeat-deployed.toml` and `manifest.toml` (CAI-P1-07)
- [ ] Unit tests with >80% coverage (CAI-P1-08)
- [ ] Integration tests: FK constraints, cascades, resolution (CAI-P1-09)
- [ ] All Phase 1 quality gates passing

---

**Phase 1 Status**: Ready for implementation
**Estimated Completion**: 3-4 days from start
**Next Phase**: Phase 2 - Enhanced Discovery (depends on Phase 1 completion)
