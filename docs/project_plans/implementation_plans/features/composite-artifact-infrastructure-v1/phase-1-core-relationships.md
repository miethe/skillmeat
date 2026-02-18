---
title: "Phase 1: Core Relationships (Database & ORM)"
description: "Database foundation for artifact associations: schema, ORM models, repository layer"
audience: [ai-agents, developers]
tags: [implementation, phase-1, database, orm, repository]
created: 2026-02-17
updated: 2026-02-17
category: "product-planning"
status: draft
related:
  - /docs/project_plans/implementation_plans/features/composite-artifact-infrastructure-v1.md
---

# Phase 1: Core Relationships (Database & ORM)

**Phase ID**: CAI-P1
**Duration**: 3-4 days
**Dependencies**: None
**Assigned Subagent(s)**: data-layer-expert, python-backend-engineer
**Estimated Effort**: 10 story points

---

## Phase Overview

Phase 1 establishes the database foundation for the entire Composite Artifact Infrastructure. This phase:

1. Adds `PLUGIN` to the `ArtifactType` enum and audits all call sites for exhaustiveness
2. Defines the `ArtifactAssociation` ORM model with composite primary key and foreign keys
3. Adds bidirectional relationships to the `Artifact` ORM model
4. Generates and applies Alembic migration for the `artifact_associations` table
5. Implements repository CRUD methods for managing associations
6. Provides comprehensive unit and integration tests

This is a critical phase because all downstream work (discovery, import orchestration, API endpoints, UI) depends on these database structures being stable and well-tested.

---

## Task Breakdown

### CAI-P1-01: Add PLUGIN to ArtifactType Enum

**Description**: Add `PLUGIN` value to the `ArtifactType` enum in `skillmeat/core/artifact_detection.py` and audit all call sites to ensure exhaustive handling of the new enum value.

**Acceptance Criteria**:
- [x] `PLUGIN = "plugin"` added to `ArtifactType` enum
- [x] Enum value serializes/deserializes correctly (JSON, database)
- [x] All match/if-elif chains checking `ArtifactType` are exhaustive and handle `PLUGIN`
- [x] Type-checking passes without errors in IDE and CI (mypy, pyright)
- [x] All existing tests pass with no regressions
- [x] Docstring updated noting that `PLUGIN` is a composite type; `STACK`/`SUITE` reserved for future

**Key Files to Modify**:
- `skillmeat/core/artifact_detection.py` — Add `PLUGIN` to enum
- `skillmeat/core/enums.py` (if separate) — Sync if enums split
- All callers (search for `ArtifactType.` in codebase):
  - `skillmeat/core/importer.py`
  - `skillmeat/core/sync.py`
  - `skillmeat/core/sharing/bundle.py`
  - `skillmeat/api/schemas/` — Response DTOs
  - `skillmeat/cache/models.py` — Column type definitions
  - Any controller/service code handling artifact type switches

**Implementation Notes**:
- Use exhaustive match/if-elif checking to catch all sites
- Run `mypy skillmeat --ignore-missing-imports` before considering complete
- Document that `PLUGIN` artifacts are composite and cannot currently be deployed directly without their children
- No UI changes in this task; purely type layer

**Estimate**: 1 story point

---

### CAI-P1-02: Define ArtifactAssociation ORM Model

**Description**: Create the `ArtifactAssociation` ORM model in `skillmeat/cache/models.py` following the `GroupArtifact` pattern. This model represents the many-to-many relationship between a parent artifact (usually a Plugin) and child artifacts (Skills, Commands, etc.).

**Acceptance Criteria**:
- [x] `ArtifactAssociation` class defined with:
  - Composite primary key: `(parent_id, child_id)`
  - Foreign keys to `Artifact` table for both `parent_id` and `child_id` with cascade delete rules
  - `relationship_type: String` column (default `"contains"`, allow `"requires"`, `"extends"` for future)
  - `pinned_version_hash: Optional[String]` column for version pinning at association time
  - Timestamps: `created_at`, `updated_at` (inherited from base model)
- [x] Model follows existing ORM patterns (inherits from `Base`, uses `Mapped` types)
- [x] Docstring explains parent/child semantics and version pinning
- [x] No validation errors when running `python -m sqlalchemy.engine.inspectionEngine`
- [x] Model can be imported without errors

**Key Files to Modify**:
- `skillmeat/cache/models.py` — Add `ArtifactAssociation` class after `Artifact` definition

**Reference Patterns**:
- Study existing association table: `GroupArtifact` in `models.py` for relationship patterns
- Use `mapped_column()` with `ForeignKey()` for constraint definition
- Use `Mapped[List[...]]` syntax for relationships (SQLAlchemy 2.0+)

**Implementation Notes**:
- Composite PK of `(parent_id, child_id)` ensures one relationship per parent-child pair
- `pinned_version_hash` is nullable because some relationships might not require version pinning
- `relationship_type` defaults to `"contains"` (the primary v1 use case); architecture supports `"requires"`, `"extends"`, `"depends_on"` for future phases
- Both foreign keys should have `ondelete="CASCADE"` to clean up associations when parent or child is deleted

**Estimate**: 2 story points

---

### CAI-P1-03: Add Bidirectional Relationships to Artifact

**Description**: Add `parent_associations` and `child_associations` SQLAlchemy relationships to the `Artifact` ORM model to enable bidirectional traversal of associations.

**Acceptance Criteria**:
- [x] `Artifact.parent_associations` relationship defined:
  - Type: `Mapped[List["ArtifactAssociation"]]`
  - Foreign key: `ArtifactAssociation.child_id`
  - Allows querying which Plugins contain this artifact
- [x] `Artifact.child_associations` relationship defined:
  - Type: `Mapped[List["ArtifactAssociation"]]`
  - Foreign key: `ArtifactAssociation.parent_id`
  - Allows querying which children this Plugin contains
- [x] Both relationships work with backrefs or back_populates
- [x] Lazy loading strategy appropriate (select for now; may optimize later)
- [x] Can traverse: `artifact.parent_associations[0].parent` → parent artifact
- [x] Can traverse: `artifact.child_associations[0].child` → child artifact
- [x] No circular import issues

**Key Files to Modify**:
- `skillmeat/cache/models.py` — Update `Artifact` class with relationship definitions

**Implementation Notes**:
- Use `back_populates` to maintain consistency (avoid backref magic)
- Define relationships after `ArtifactAssociation` class to avoid forward reference issues
- Consider cascade behavior: when an `Artifact` is deleted, should its associations also be deleted? (yes, use CASCADE)
- Lazy loading: `select` is safe; consider `selectinload` optimization in repository queries if needed later

**Estimate**: 1 story point

---

### CAI-P1-04: Generate & Apply Alembic Migration

**Description**: Generate an Alembic migration that creates the `artifact_associations` table and apply it to the development database. The migration must be reversible and must not break existing artifact rows.

**Acceptance Criteria**:
- [x] Alembic migration file generated in `skillmeat/cache/migrations/versions/`
- [x] Migration creates `artifact_associations` table with correct schema:
  - Columns: `parent_id`, `child_id`, `relationship_type`, `pinned_version_hash`, `created_at`, `updated_at`
  - Composite primary key: `(parent_id, child_id)`
  - Foreign keys with cascade delete on both parent and child
  - Indexes on foreign key columns for query performance
- [x] Migration applies cleanly to fresh database: `alembic upgrade head`
- [x] Migration rolls back cleanly: `alembic downgrade -1` leaves DB in pre-migration state
- [x] No existing artifact rows are affected or deleted
- [x] Database integrity constraints enforced
- [x] Migration file includes descriptive docstring and down() migration

**Key Files to Modify**:
- `skillmeat/cache/migrations/versions/{timestamp}_add_artifact_associations.py` — New migration

**Implementation Steps**:
1. Update `models.py` with `ArtifactAssociation` class definition
2. Run `alembic revision --autogenerate -m "Add artifact_associations table"` from skillmeat root
3. Review generated migration for correctness
4. Manually add down() migration if not auto-generated
5. Test on fresh DB: `alembic upgrade head`
6. Test rollback: `alembic downgrade -1`
7. Verify table exists and schema is correct

**Estimate**: 2 story points

---

### CAI-P1-05: Implement Association Repository Methods

**Description**: Implement CRUD methods in the association repository (or primary repository module) to handle association creation, querying, and deletion.

**Acceptance Criteria**:
- [x] `get_associations(artifact_id: str) -> AssociationQueryResult`:
  - Returns both parent associations (where artifact is child) and child associations (where artifact is parent)
  - Returns structure: `{"parents": [...], "children": [...]}`
- [x] `create_association(parent_id: str, child_id: str, relationship_type: str, pinned_version_hash: Optional[str]) -> ArtifactAssociation`:
  - Creates and returns association record
  - Validates that both parent and child artifacts exist
  - Raises `IntegrityError` if association already exists
- [x] `delete_association(parent_id: str, child_id: str) -> bool`:
  - Deletes association
  - Returns True if deleted, False if not found
- [x] `get_children_of(parent_id: str) -> List[ArtifactAssociation]`:
  - Query helper for plugins listing their children
  - Optional: support filtering by relationship_type
- [x] `get_parents_of(child_id: str) -> List[ArtifactAssociation]`:
  - Query helper for artifacts listing which plugins contain them
- [x] Methods use cursor pagination if returning large result sets (not expected for v1, but pattern should be present)
- [x] All methods properly handle database errors and raise domain exceptions

**Key Files to Modify**:
- `skillmeat/cache/repositories/` (or main repository module) — Add association methods
- May create new file: `skillmeat/cache/repositories/associations.py` or extend existing repo

**Implementation Notes**:
- Follow existing repository patterns in the codebase (use SQLAlchemy Session, transaction handling)
- `get_associations()` should return a DTO, not ORM objects, to decouple DB from API layer
- Consider query optimization: use `joinedload()` if needed to avoid N+1 queries
- Pagination: even though v1 plugins likely have <50 children, use cursor pagination pattern for future-proofing

**Estimate**: 2 story points

---

### CAI-P1-06: Unit Tests for Association Model & Repository

**Description**: Write comprehensive unit tests for the `ArtifactAssociation` ORM model and repository methods to ensure correct behavior, error handling, and database constraints.

**Acceptance Criteria**:
- [x] Test file: `tests/test_artifact_associations.py` (or similar)
- [x] Model validation tests:
  - Valid association creates correctly
  - Composite PK prevents duplicate parent-child pairs
  - Foreign key constraints prevent orphaned references
  - `relationship_type` defaults to `"contains"`
  - Timestamps auto-set on creation
- [x] Repository method tests:
  - `create_association()` creates and returns correct record
  - `create_association()` raises error on duplicate
  - `get_associations()` returns both parents and children
  - `delete_association()` removes records
  - `get_children_of()` returns correct children
  - `get_parents_of()` returns correct parents
  - Methods handle non-existent artifacts gracefully
- [x] Integration tests:
  - Create association → query → delete workflow
  - Cascade delete: deleting parent removes associations
  - Cascade delete: deleting child removes associations
- [x] Code coverage >80% for all association code
- [x] Tests use fixtures or factories for creating test artifacts

**Key Files to Create/Modify**:
- `tests/test_artifact_associations.py` — New test file
- Fixtures in `tests/conftest.py` for test artifacts

**Implementation Notes**:
- Use pytest with database fixtures (SQLAlchemy test DB session)
- Test both happy path and error scenarios
- Verify cascade delete rules work as expected
- Ensure tests are deterministic and can run in parallel

**Estimate**: 1 story point

---

### CAI-P1-07: Integration Tests (Phase 1)

**Description**: Write integration tests verifying model, migration, and repository layer work together correctly in a real database scenario.

**Acceptance Criteria**:
- [x] Test file: `tests/integration/test_artifact_associations_integration.py`
- [x] End-to-end workflow tests:
  - Create test artifacts in DB
  - Create associations between them
  - Query associations via repository
  - Verify no orphaned records
  - Delete associations
  - Verify cleanup
- [x] Migration tests:
  - Verify migration creates table with correct schema
  - Verify rollback leaves DB clean
  - No existing artifact data is lost
- [x] Error scenarios:
  - Attempt to create association with non-existent parent (should fail)
  - Attempt to create association with non-existent child (should fail)
  - Attempt duplicate association (should fail)
- [x] Performance baseline test (create/query 100 associations, verify <100ms)
- [x] Tests run against real PostgreSQL (or SQLite for CI)

**Key Files to Create/Modify**:
- `tests/integration/test_artifact_associations_integration.py` — New test file

**Estimate**: 1 story point

---

## Phase 1 Quality Gates

Before Phase 2 can begin, all the following must pass:

- [ ] Enum change does not break existing type-checking: `mypy skillmeat --ignore-missing-imports` passes
- [ ] Alembic migration applies cleanly to fresh DB: `alembic upgrade head` succeeds
- [ ] Alembic migration rolls back cleanly: `alembic downgrade -1` leaves DB in pre-migration state
- [ ] Foreign key constraints enforced: attempting to create association with non-existent artifact raises error
- [ ] Repository CRUD methods pass unit tests: `pytest tests/test_artifact_associations.py -v` passes
- [ ] Integration tests pass: `pytest tests/integration/test_artifact_associations_integration.py -v` passes
- [ ] No regression in existing artifact tests: `pytest tests/test_artifacts.py -v` passes (or similar existing tests)
- [ ] Code coverage >80% for all new code: `pytest --cov=skillmeat --cov-report=term-missing` shows >80%

---

## Implementation Notes & References

### ORM Patterns to Follow

- **GroupArtifact pattern**: Study `skillmeat/cache/models.py` for existing N:M association examples
- **Timestamp pattern**: Use existing `created_at`, `updated_at` columns inherited from base model
- **Cascade rules**: Use `ForeignKey(..., ondelete="CASCADE")` to ensure cleanup

### Alembic Patterns

- Review existing migrations in `skillmeat/cache/migrations/versions/` for style
- Use `op.create_table()` with explicit column definitions
- Always include reversible `downgrade()` function
- Reference: SQLAlchemy migration guide

### Repository Patterns

- Query pagination: Use cursor pagination pattern (even if not immediately needed, establish pattern)
- Error handling: Raise domain-specific exceptions (not raw DB errors)
- DTOs: Always return DTOs from public methods, not ORM objects
- Reference existing repository code in `skillmeat/cache/repositories/`

### Testing Patterns

- Use pytest fixtures for test data setup
- Use `pytest.mark.parametrize` for testing multiple scenarios
- Test both happy path and error scenarios
- Integration tests should use real DB (SQLite or test PostgreSQL container)

---

## Deliverables Checklist

- [ ] `ArtifactType.PLUGIN` enum value added and all call sites audited
- [ ] `ArtifactAssociation` ORM model defined in `models.py`
- [ ] Bidirectional relationships added to `Artifact` model
- [ ] Alembic migration created and tested (apply & rollback)
- [ ] Repository methods implemented: `create`, `read`, `delete`, `query_helpers`
- [ ] Unit test file created with >80% coverage
- [ ] Integration test file created with end-to-end scenarios
- [ ] All Phase 1 quality gates passing
- [ ] Code reviewed and merged to main branch

---

**Phase 1 Status**: Ready for implementation
**Estimated Completion**: 3-4 days from start
**Next Phase**: Phase 2 - Enhanced Discovery (depends on Phase 1 completion)
