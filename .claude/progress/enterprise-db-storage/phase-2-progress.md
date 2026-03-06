---
type: progress
schema_version: 2
doc_type: progress
prd: enterprise-db-storage
feature_slug: enterprise-db-storage
prd_ref: docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1.md
phase: 2
title: Enterprise Repository Implementation
status: completed
started: '2026-03-06'
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 14
completed_tasks: 14
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors:
- data-layer-expert
- backend-architect
tasks:
- id: ENT-2.1
  description: Create EnterpriseRepositoryBase extending BaseRepository with automatic
    tenant_id filtering mixin
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies: []
  estimated_effort: 3h
  priority: critical
- id: ENT-2.2
  description: Implement artifact lookup methods (get, get_by_uuid) with tenant scoping
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ENT-2.1
  estimated_effort: 2h
  priority: high
- id: ENT-2.3
  description: Implement list() and search_by_tags() with pagination, filtering, and
    JSONB operators
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ENT-2.1
  estimated_effort: 3h
  priority: high
- id: ENT-2.4
  description: Implement artifact creation with automatic initial version and update
    with version tracking
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ENT-2.1
  estimated_effort: 3h
  priority: high
- id: ENT-2.5
  description: Implement soft and hard delete with cascade handling for collection
    references
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ENT-2.1
  estimated_effort: 2h
  priority: high
- id: ENT-2.6
  description: Implement get_content() and list_versions() for version history retrieval
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ENT-2.1
  estimated_effort: 2h
  priority: high
- id: ENT-2.7
  description: Implement collection CRUD (create, get, list, update, delete) with
    tenant scoping
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ENT-2.1
  estimated_effort: 3h
  priority: high
- id: ENT-2.8
  description: Implement add_artifact(), remove_artifact(), list_artifacts(), reorder_artifacts()
    for collection membership
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ENT-2.1
  estimated_effort: 2h
  priority: high
- id: ENT-2.9
  description: Create RepositoryFactory returning Local or Enterprise repo based on
    config/edition; wire into FastAPI DI. Uses DEFAULT_TENANT_ID in bootstrap/single-tenant
    mode; will switch to AuthContext-derived tenant when PRD 2 is available.
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ENT-2.1
  estimated_effort: 3h
  priority: high
- id: ENT-2.10
  description: Implement request-scoped audit logging for all repository calls with
    tenant context
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - ENT-2.1
  estimated_effort: 2h
  priority: medium
- id: ENT-2.11
  description: Write unit tests covering all ArtifactRepository methods including
    negative cross-tenant tests
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ENT-2.1
  - ENT-2.2
  - ENT-2.3
  - ENT-2.4
  - ENT-2.5
  - ENT-2.6
  estimated_effort: 3h
  priority: high
- id: ENT-2.12
  description: Write unit tests for CollectionRepository CRUD, membership, ordering,
    and multi-tenant isolation
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ENT-2.1
  - ENT-2.7
  - ENT-2.8
  estimated_effort: 2h
  priority: high
- id: ENT-2.13
  description: Write integration tests against docker-compose PostgreSQL verifying
    tenant isolation, concurrency, and constraints
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - ENT-2.1
  - ENT-2.2
  - ENT-2.3
  - ENT-2.4
  - ENT-2.5
  - ENT-2.6
  - ENT-2.7
  - ENT-2.8
  - ENT-2.9
  - ENT-2.10
  estimated_effort: 3h
  priority: high
- id: ENT-2.14
  description: Establish baseline performance benchmarks for all repository operations
    (get <1ms, list(1000) <10ms, search <5ms)
  status: completed
  assigned_to:
  - data-layer-expert
  dependencies:
  - ENT-2.13
  estimated_effort: 2h
  priority: medium
parallelization:
  batch_1:
  - ENT-2.1
  batch_2:
  - ENT-2.2
  - ENT-2.3
  - ENT-2.4
  - ENT-2.5
  - ENT-2.6
  - ENT-2.7
  - ENT-2.8
  - ENT-2.9
  - ENT-2.10
  batch_3:
  - ENT-2.11
  - ENT-2.12
  batch_4:
  - ENT-2.13
  batch_5:
  - ENT-2.14
  critical_path:
  - ENT-2.1
  - ENT-2.2
  - ENT-2.11
  - ENT-2.13
  - ENT-2.14
  estimated_total_time: 13h
blockers: []
success_criteria:
- id: SC-1
  description: All 14 tasks marked complete
  status: pending
- id: SC-2
  description: EnterpriseArtifactRepository fully implements all IArtifactRepository
    methods
  status: pending
- id: SC-3
  description: EnterpriseCollectionRepository fully implements all ICollectionRepository
    methods
  status: pending
- id: SC-4
  description: 100% of repository methods apply automatic tenant_id filtering
  status: pending
- id: SC-5
  description: Unit test coverage >90% for enterprise repositories
  status: pending
- id: SC-6
  description: Integration tests pass against docker-compose PostgreSQL
  status: pending
- id: SC-7
  description: Performance benchmarks established and within targets (overhead <5%)
  status: pending
- id: SC-8
  description: Multi-tenant isolation verified with negative cross-tenant tests
  status: pending
- id: SC-9
  description: Code reviewed by python-backend-engineer and data-layer-expert
  status: pending
files_modified:
- skillmeat/cache/repositories/enterprise_base.py
- skillmeat/cache/repositories/enterprise_artifact.py
- skillmeat/cache/repositories/enterprise_collection.py
- skillmeat/cache/repositories/enterprise_factory.py
- skillmeat/cache/repositories/audit.py
- skillmeat/api/dependencies.py
- tests/unit/cache/test_enterprise_artifact_repository.py
- tests/unit/cache/test_enterprise_collection_repository.py
- tests/integration/test_enterprise_repositories.py
- tests/performance/test_enterprise_benchmarks.py
progress: 100
updated: '2026-03-06'
---

# enterprise-db-storage - Phase 2: Enterprise Repository Implementation

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/enterprise-db-storage/phase-2-progress.md -t ENT-2.X -s completed
```

---

## Objective

Phase 2 implements the repository layer for the enterprise edition, fulfilling the abstract interfaces defined in PRD 1. All repositories enforce automatic tenant_id filtering via RequestContext threading, with a DI factory enabling seamless switching between Local and Enterprise backends.

---

## Orchestration Quick Reference

Execute batches in order. Within each batch, all tasks can run in parallel.

### Batch 1 — Foundation (sequential, unblocks everything)

```python
Task("data-layer-expert",
     "Implement EnterpriseRepositoryBase with automatic tenant_id filtering mixin. "
     "File: skillmeat/cache/repositories/enterprise_base.py. "
     "Follow patterns in .claude/context/key-context/repository-architecture.md. "
     "ENT-2.1 acceptance criteria in "
     "docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1/phase-2-repositories.md")
```

### Batch 2 — Parallel implementation (all depend on ENT-2.1 only)

```python
# python-backend-engineer handles ENT-2.2 through ENT-2.9:
Task("python-backend-engineer",
     "Implement EnterpriseArtifactRepository: get, get_by_uuid (ENT-2.2), "
     "list + search_by_tags (ENT-2.3), create + update (ENT-2.4), "
     "delete + hard_delete (ENT-2.5), get_content + list_versions (ENT-2.6). "
     "File: skillmeat/cache/repositories/enterprise_artifact.py. "
     "All methods must call _apply_tenant_filter(). "
     "Full specs in phase-2-repositories.md ENT-2.2 through ENT-2.6.")

Task("python-backend-engineer",
     "Implement EnterpriseCollectionRepository: create, get, list, update, delete (ENT-2.7), "
     "add_artifact, remove_artifact, list_artifacts, reorder_artifacts (ENT-2.8). "
     "File: skillmeat/cache/repositories/enterprise_collection.py. "
     "Full specs in phase-2-repositories.md ENT-2.7 and ENT-2.8.")

Task("python-backend-engineer",
     "Implement RepositoryFactory + FastAPI DI wiring (ENT-2.9). "
     "File: skillmeat/cache/repositories/enterprise_factory.py and skillmeat/api/dependencies.py. "
     "Factory returns LocalFileSystemRepository by default, EnterpriseArtifactRepository when DATABASE_URL set. "
     "Full spec in phase-2-repositories.md ENT-2.9.")

Task("data-layer-expert",
     "Implement RepositoryAuditLogger for request-scoped tenant-aware logging (ENT-2.10). "
     "File: skillmeat/cache/repositories/audit.py. "
     "Full spec in phase-2-repositories.md ENT-2.10.")
```

### Batch 3 — Unit tests (depend on ENT-2.1 through ENT-2.8)

```python
Task("python-backend-engineer",
     "Write unit tests for EnterpriseArtifactRepository (ENT-2.11) and "
     "EnterpriseCollectionRepository (ENT-2.12). "
     "Files: tests/unit/cache/test_enterprise_artifact_repository.py, "
     "tests/unit/cache/test_enterprise_collection_repository.py. "
     "Must include negative cross-tenant leakage tests. Coverage >90%. "
     "Full specs in phase-2-repositories.md ENT-2.11 and ENT-2.12.")
```

### Batch 4 — Integration tests (depend on all ENT-2.1 through ENT-2.10)

```python
Task("data-layer-expert",
     "Write integration tests against docker-compose PostgreSQL (ENT-2.13). "
     "File: tests/integration/test_enterprise_repositories.py. "
     "Must verify multi-tenant isolation, concurrent writes, performance baselines, constraints. "
     "Full spec in phase-2-repositories.md ENT-2.13.")
```

### Batch 5 — Performance benchmarks (depend on ENT-2.13)

```python
Task("data-layer-expert",
     "Establish performance benchmarks for all repository operations (ENT-2.14). "
     "File: tests/performance/test_enterprise_benchmarks.py. "
     "Targets: get() <1ms, list(1000) <10ms, search() <5ms, multitenancy overhead <5%. "
     "Integrate into CI so regressions >10% fail the build. "
     "Full spec in phase-2-repositories.md ENT-2.14.")
```

---

## Implementation Notes

### Architectural Decisions

- Tenant filter is applied AFTER main WHERE clauses so the query optimizer can use non-tenant indexes effectively
- RequestContext is mandatory for all enterprise repos (not optional) — raises ValueError if missing
- EnterpriseRepositoryBase extends BaseRepository to reuse session management; adds `_apply_tenant_filter()`
- RepositoryFactory uses `DATABASE_URL` env var as the edition discriminator — no code changes needed to switch backends

### Known Gotchas

- `_apply_tenant_filter()` must be called on every query path, including sub-queries in `search_by_tags()`
- JSONB containment operators differ between match-any (OR) and match-all (AND) — see phase-2-repositories.md ENT-2.3 for examples
- `update()` must compare content hashes before creating a new version row — metadata-only updates must not create versions
- `delete()` (soft) must remove from `collection_artifacts` junction table via cascade or explicit DELETE
- `reorder_artifacts()` must update all `order_index` values atomically in one transaction

### Development Setup

- Phase 1 schema migrations must be applied before any repository tests can run
- Integration tests require docker-compose PostgreSQL: `docker-compose up -d postgres`
- `PRAGMA foreign_keys=ON` must be set per-connection for SQLite test fixtures (see existing pattern in `skillmeat/cache/models.py`)

---

## Completion Notes

*(Fill in when phase is complete)*
