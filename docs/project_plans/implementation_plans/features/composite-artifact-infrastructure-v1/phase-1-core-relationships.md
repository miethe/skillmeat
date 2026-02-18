---
title: "Phase 1: Core Relationships (Database & ORM)"
description: "Database foundation for composite memberships: schema, ORM models, repository layer"
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
2. Defines collection-scoped composite entity + membership metadata ORM models
3. Exposes parent/child linkage via repository DTOs (without mutating atomic artifact schema)
4. Generates and applies Alembic migration for composite entity + membership tables
5. Implements repository CRUD methods for managing memberships
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

### CAI-P1-02: Define Composite Entity + Membership ORM Models

**Description**: Create collection-scoped composite entity + membership metadata models in `skillmeat/cache/models.py` following the `GroupArtifact` pattern. These models represent "Plugin contains Artifact" as metadata without changing child artifact schema.

**Acceptance Criteria**:
- [x] `CompositeArtifact` class defined with:
  - Scoped identity including `collection_id`
  - Composite type (`plugin`) and manifest/meta fields
- [x] `CompositeMembership` class defined with:
  - Scoped key including `collection_id`, `composite_id`, `child_artifact_id`
  - Child artifact references by collection artifact identifier (`type:name`)
  - `relationship_type: String` column (default `"contains"`, allow `"requires"`, `"extends"` for future)
  - `pinned_version_hash: Optional[String]` column for version pinning at association time
  - Timestamps: `created_at`, `updated_at` (inherited from base model)
- [x] Model follows existing ORM patterns (inherits from `Base`, uses `Mapped` types)
- [x] Docstring explains parent/child semantics, collection scope, and version pinning
- [x] No validation errors when running `python -m sqlalchemy.engine.inspectionEngine`
- [x] Model can be imported without errors

**Key Files to Modify**:
- `skillmeat/cache/models.py` — Add composite entity + membership models

**Reference Patterns**:
- Study existing association table: `GroupArtifact` in `models.py` for relationship patterns
- Use `mapped_column()` with `ForeignKey()` for constraint definition
- Use `Mapped[List[...]]` syntax for relationships (SQLAlchemy 2.0+)

**Implementation Notes**:
- Scoped key ensures one relationship per parent-child pair per collection
- `pinned_version_hash` is nullable because some relationships might not require version pinning
- `relationship_type` defaults to `"contains"` (the primary v1 use case); architecture supports `"requires"`, `"extends"`, `"depends_on"` for future phases
- Use scoped constraints to clean up memberships when composite entity is deleted

**Estimate**: 2 story points

---

### CAI-P1-03: Add Metadata Linkage Query Surface

**Description**: Expose parent/child membership lookups via repository DTOs and query helpers while keeping atomic `Artifact` schema unchanged.

**Acceptance Criteria**:
- [x] Query surfaces support child -> parents (Part of) and composite -> children (Contains)
- [x] Atomic `Artifact` schema remains unchanged (no direct parent/child relationship fields required)
- [x] Repository returns DTO-oriented structures for API/UI use
- [x] No circular import issues

**Key Files to Modify**:
- `skillmeat/cache/repositories.py` — Add/extend query helpers for parent/child membership traversal

**Implementation Notes**:
- Keep atomic artifact schema stable; represent linkage in metadata tables only
- Consider cascade behavior for composite deletion and collection deletion
- Use `selectinload`/joined queries in repository methods as needed to avoid N+1

**Estimate**: 1 story point

---

### CAI-P1-04: Generate & Apply Alembic Migration

**Description**: Generate an Alembic migration that creates composite entity + membership tables and apply it to the development database. The migration must be reversible and must not break existing artifact rows.

**Acceptance Criteria**:
- [x] Alembic migration file generated in `skillmeat/cache/migrations/versions/`
- [x] Migration creates composite entity + membership tables with correct schema:
  - Membership columns include `collection_id`, `composite_id`, `child_artifact_id`, `relationship_type`, `pinned_version_hash`, timestamps
  - Composite key prevents duplicate membership rows within the same collection
  - Indexes support parent and child lookup performance
- [x] Migration applies cleanly to fresh database: `alembic upgrade head`
- [x] Migration rolls back cleanly: `alembic downgrade -1` leaves DB in pre-migration state
- [x] No existing artifact rows are affected or deleted
- [x] Database integrity constraints enforced
- [x] Migration file includes descriptive docstring and down() migration

**Key Files to Modify**:
- `skillmeat/cache/migrations/versions/{timestamp}_add_composite_membership_tables.py` — New migration

**Implementation Steps**:
1. Update `models.py` with composite entity + membership model definitions
2. Run `alembic revision --autogenerate -m "Add composite entity and membership tables"` from skillmeat root
3. Review generated migration for correctness
4. Manually add down() migration if not auto-generated
5. Test on fresh DB: `alembic upgrade head`
6. Test rollback: `alembic downgrade -1`
7. Verify table exists and schema is correct

**Estimate**: 2 story points

---

### CAI-P1-05: Implement Membership Repository Methods

**Description**: Implement CRUD methods in the membership repository (or primary repository module) to handle membership creation, querying, and deletion.

**Acceptance Criteria**:
- [x] `get_associations(artifact_id: str) -> AssociationQueryResult`:
  - Returns both parent associations (where artifact is child) and child associations (where artifact is parent)
  - Returns structure: `{"parents": [...], "children": [...]}`
- [x] `create_membership(composite_id: str, child_artifact_id: str, relationship_type: str, pinned_version_hash: Optional[str]) -> MembershipRecord`:
  - Creates and returns membership record
  - Validates that composite and child artifact identifiers exist in collection scope
  - Raises `IntegrityError` if membership already exists
- [x] `delete_membership(composite_id: str, child_artifact_id: str) -> bool`:
  - Deletes membership
  - Returns True if deleted, False if not found
- [x] `get_children_of(composite_id: str) -> List[MembershipRecord]`:
  - Query helper for plugins listing their children
  - Optional: support filtering by relationship_type
- [x] `get_parents_of(child_id: str) -> List[MembershipRecord]`:
  - Query helper for artifacts listing which plugins contain them
- [x] Methods use cursor pagination if returning large result sets (not expected for v1, but pattern should be present)
- [x] All methods properly handle database errors and raise domain exceptions

**Key Files to Modify**:
- `skillmeat/cache/repositories.py` (or primary repository module) — Add membership methods

**Implementation Notes**:
- Follow existing repository patterns in the codebase (use SQLAlchemy Session, transaction handling)
- `get_associations()` should return a DTO, not ORM objects, to decouple DB from API layer
- Consider query optimization: use `joinedload()` if needed to avoid N+1 queries
- Pagination: even though v1 plugins likely have <50 children, use cursor pagination pattern for future-proofing

**Estimate**: 2 story points

---

### CAI-P1-06: Unit Tests for Membership Model & Repository

**Description**: Write comprehensive unit tests for the `CompositeMembership` ORM model and repository methods to ensure correct behavior, error handling, and database constraints.

**Acceptance Criteria**:
- [x] Test file: `tests/test_composite_memberships.py` (or similar)
- [x] Model validation tests:
  - Valid membership creates correctly
  - Composite PK prevents duplicate parent-child pairs
  - Foreign key constraints prevent orphaned references
  - `relationship_type` defaults to `"contains"`
  - Timestamps auto-set on creation
- [x] Repository method tests:
  - `create_membership()` creates and returns correct record
  - `create_membership()` raises error on duplicate
  - `get_associations()` returns both parents and children
  - `delete_membership()` removes records
  - `get_children_of()` returns correct children
  - `get_parents_of()` returns correct parents
  - Methods handle non-existent artifacts gracefully
- [x] Integration tests:
  - Create membership → query → delete workflow
  - Cascade delete: deleting parent removes memberships
  - Cascade delete: deleting child removes memberships
- [x] Code coverage >80% for all membership code
- [x] Tests use fixtures or factories for creating test artifacts

**Key Files to Create/Modify**:
- `tests/test_composite_memberships.py` — New test file
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
- [x] Test file: `tests/integration/test_composite_memberships_integration.py`
- [x] End-to-end workflow tests:
  - Create test artifacts in DB
  - Create memberships between them
  - Query memberships via repository
  - Verify no orphaned records
  - Delete memberships
  - Verify cleanup
- [x] Migration tests:
  - Verify migration creates table with correct schema
  - Verify rollback leaves DB clean
  - No existing artifact data is lost
- [x] Error scenarios:
  - Attempt to create membership with non-existent parent (should fail)
  - Attempt to create membership with non-existent child (should fail)
  - Attempt duplicate membership (should fail)
- [x] Performance baseline test (create/query 100 memberships, verify <100ms)
- [x] Tests run against real PostgreSQL (or SQLite for CI)

**Key Files to Create/Modify**:
- `tests/integration/test_composite_memberships_integration.py` — New test file

**Estimate**: 1 story point

---

## Phase 1 Quality Gates

Before Phase 2 can begin, all the following must pass:

- [ ] Enum change does not break existing type-checking: `mypy skillmeat --ignore-missing-imports` passes
- [ ] Alembic migration applies cleanly to fresh DB: `alembic upgrade head` succeeds
- [ ] Alembic migration rolls back cleanly: `alembic downgrade -1` leaves DB in pre-migration state
- [ ] Foreign key constraints enforced: attempting to create membership with non-existent artifact raises error
- [ ] Repository CRUD methods pass unit tests: `pytest tests/test_composite_memberships.py -v` passes
- [ ] Integration tests pass: `pytest tests/integration/test_composite_memberships_integration.py -v` passes
- [ ] No regression in existing artifact tests: `pytest tests/api/test_artifacts.py -v` passes
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
- Reference existing repository code in `skillmeat/cache/repositories.py`

### Testing Patterns

- Use pytest fixtures for test data setup
- Use `pytest.mark.parametrize` for testing multiple scenarios
- Test both happy path and error scenarios
- Integration tests should use real DB (SQLite or test PostgreSQL container)

---

## Deliverables Checklist

- [ ] `ArtifactType.PLUGIN` enum value added and all call sites audited
- [ ] Composite entity + membership metadata ORM models defined in `models.py`
- [ ] Metadata linkage query surface implemented without mutating atomic `Artifact` schema
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
