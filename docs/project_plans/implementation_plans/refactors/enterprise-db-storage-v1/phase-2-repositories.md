---
title: "Phase 2: Enterprise Repository Implementation"
schema_version: 2
doc_type: phase_plan
status: draft
created: 2026-03-06
updated: 2026-03-06
feature_slug: "enterprise-db-storage"
phase: 2
phase_title: "Enterprise Repository Implementation"
prd_ref: docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1.md
entry_criteria:
  - "Phase 1 (Schema) 100% complete with all migrations tested"
  - "PRD 1 repository interfaces finalized (IArtifactRepository, ICollectionRepository, etc.)"
  - "Python-backend-engineer and data-layer-expert allocated"
exit_criteria:
  - "EnterpriseArtifactRepository fully implementing IArtifactRepository"
  - "EnterpriseCollectionRepository fully implementing ICollectionRepository"
  - "All repository methods apply automatic tenant_id filtering"
  - "DI factory enables seamless switching between Local and Enterprise repos"
  - "Unit test coverage >90% for enterprise repositories"
  - "Performance benchmarks established (<5ms overhead per query)"
---

# Phase 2: Enterprise Repository Implementation

## Overview

Phase 2 implements the repository layer for the enterprise edition, fulfilling the abstract interfaces defined in PRD 1. This includes EnterpriseArtifactRepository, EnterpriseCollectionRepository, and supporting repositories, all with automatic tenant_id filtering via RequestContext threading.

**Duration:** 2 weeks | **Effort:** 16-20 story points | **Subagents:** python-backend-engineer, data-layer-expert

**Key Outputs:**
- EnterpriseArtifactRepository with all CRUD + search operations
- EnterpriseCollectionRepository with all collection operations
- Automatic tenant filtering on all queries
- Repository factory for DI-based backend swapping
- Unit tests with 100% interface coverage

---

## Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| ENT-2.1 | Enterprise repository base class | Create EnterpriseRepositoryBase extending BaseRepository with automatic tenant_id filtering; accepts `tenant_id` constructor param defaulting to `DEFAULT_TENANT_ID` | Base class filters all queries with tenant_id; works with DEFAULT_TENANT_ID when AuthContext absent; works with AuthContext.tenant_id when PRD 2 available; type-safe DDL helpers | 3 | data-layer-expert | Phase 1 complete |
| ENT-2.2 | EnterpriseArtifactRepository: get/get_by_uuid | Implement artifact lookup methods with tenant scoping | get() and get_by_uuid() return ArtifactDTO with automatic WHERE tenant_id filtering, null returns for non-existent | 2 | python-backend-engineer | ENT-2.1 |
| ENT-2.3 | EnterpriseArtifactRepository: list/search | Implement list() and search_by_tags() with pagination and filtering | list() supports filters dict, offset/limit, sort_by, search_by_tags() uses JSONB operators | 3 | python-backend-engineer | ENT-2.1 |
| ENT-2.4 | EnterpriseArtifactRepository: create/update | Implement artifact creation and updates with version tracking | create() inserts artifact + initial version, update() creates new version with content_hash | 3 | python-backend-engineer | ENT-2.1 |
| ENT-2.5 | EnterpriseArtifactRepository: delete/archive | Implement soft and hard delete with cascade handling | delete() soft-deletes (marks deleted_at), hard_delete() removes versions, collection references cleaned up | 2 | python-backend-engineer | ENT-2.1 |
| ENT-2.6 | EnterpriseArtifactRepository: content operations | Implement get_content() and list_versions() for version history | get_content(artifact_id, version_hash?) returns markdown_payload, list_versions() returns all ArtifactVersionDTO | 2 | python-backend-engineer | ENT-2.1 |
| ENT-2.7 | EnterpriseCollectionRepository: CRUD operations | Implement collection create, read, update, delete with tenant scoping | All methods apply tenant_id filtering, create() handles is_default logic, update() modifies metadata | 3 | python-backend-engineer | ENT-2.1 |
| ENT-2.8 | EnterpriseCollectionRepository: membership operations | Implement add_artifact(), remove_artifact(), list_artifacts() for collection contents | add_artifact() maintains order_index, remove_artifact() cleans up junction table, list_artifacts() respects order | 2 | python-backend-engineer | ENT-2.1 |
| ENT-2.9 | Repository DI factory and wiring | Create RepositoryFactory that returns Local or Enterprise repo based on config/edition; wires DEFAULT_TENANT_ID in bootstrap mode, swaps to AuthContext.tenant_id when PRD 2 available | Factory checks DATABASE_URL/edition; enterprise repos receive DEFAULT_TENANT_ID in bootstrap mode; switching to multi-tenant is a DI-level change only; wired in dependencies.py for FastAPI | 3 | python-backend-engineer | ENT-2.1, Phase 1 complete |
| ENT-2.10 | Tenant filtering audit layer | Implement request-scoped logging that logs all queries with tenant_id context | Every repository call logs: operation, table, tenant_id, execution time, used for debugging/auditing | 2 | data-layer-expert | ENT-2.1 |
| ENT-2.11 | Unit tests: artifact repository | Write unit tests covering all ArtifactRepository methods with mocking | Tests verify: get(), list(), create(), update(), delete(), search() all apply tenant_id filtering, no cross-tenant leakage | 3 | python-backend-engineer | ENT-2.1, ENT-2.2 through ENT-2.6 |
| ENT-2.12 | Unit tests: collection repository | Write unit tests for CollectionRepository operations | Tests cover: CRUD operations, membership management, order preservation, multi-tenant isolation | 2 | python-backend-engineer | ENT-2.1, ENT-2.7, ENT-2.8 |
| ENT-2.13 | Integration tests: repositories with PostgreSQL | Write integration tests against real PostgreSQL (docker-compose) | Tests verify: tenant isolation (negative tests), concurrent writes, performance baselines, constraints enforcement | 3 | data-layer-expert | ENT-2.1 through ENT-2.10, Phase 1 complete |
| ENT-2.14 | Performance benchmarks | Establish baseline performance metrics for all repository operations | Benchmarks: get() <1ms, list(1000 artifacts) <10ms, search() <5ms, multitenancy overhead <5% | 2 | data-layer-expert | ENT-2.13 |

**Total: 35 hours / 16-20 story points**

---

## Detailed Task Descriptions

### ENT-2.1: Enterprise Repository Base Class

**Description:**

Create the base class that all enterprise repositories inherit from, providing automatic tenant_id filtering. In Phase 2 (single-tenant bootstrap mode), the base class accepts `tenant_id` as a constructor parameter defaulting to `DEFAULT_TENANT_ID`. When PRD 2 lands, the DI container swaps this to `AuthContext.tenant_id` — no changes to the base class or repository implementations are required.

**File:** `skillmeat/cache/repositories/enterprise_base.py`

**Key Features:**
```python
from skillmeat.cache.config import DEFAULT_TENANT_ID

class EnterpriseRepositoryBase(BaseRepository[T]):
    """Base class for enterprise repositories with automatic tenant filtering.

    All queries automatically apply WHERE tenant_id = self._tenant_id.
    In single-tenant bootstrap mode, tenant_id defaults to DEFAULT_TENANT_ID.
    When PRD 2 is available, DI wires AuthContext.tenant_id instead.
    """

    def __init__(self, session: Session, tenant_id: str = DEFAULT_TENANT_ID):
        super().__init__(session)
        self._tenant_id = tenant_id

    def _apply_tenant_filter(self, query: Select) -> Select:
        """Apply tenant_id filter to any query."""
        return query.where(self.model_class.tenant_id == self._tenant_id)

    def get(self, id: str) -> DTO | None:
        """Get single entity with automatic tenant filtering."""
        query = select(self.model_class).where(self.model_class.id == id)
        query = self._apply_tenant_filter(query)
        return self._execute_query(query)
```

**Acceptance Criteria:**
- Base class accepts `tenant_id` as constructor parameter with `DEFAULT_TENANT_ID` as default
- All queries apply tenant filter automatically via `_apply_tenant_filter()`
- Works with `DEFAULT_TENANT_ID` when no AuthContext is configured (single-tenant bootstrap)
- Works with `AuthContext.tenant_id` when PRD 2 is available and DI is updated
- Tenant filter applied after main WHERE clauses (allows query optimizer to use indexes)
- Type-safe DDL helpers (ORM-compatible, no raw SQL)
- Inherits from BaseRepository to reuse session management
- Logging at repository level tracks all tenant filtering

**Design Notes:**
- `tenant_id` constructor param enables DI-level swapping without changing repo code
- Single-tenant bootstrap: `DEFAULT_TENANT_ID` is wired at factory level (ENT-2.9)
- Multi-tenant upgrade path: DI factory reads `AuthContext.tenant_id` and passes to constructor

---

### ENT-2.2: EnterpriseArtifactRepository: Lookup Methods

**Description:**

Implement single-artifact lookup methods (get, get_by_uuid) with tenant isolation.

**File:** `skillmeat/cache/repositories/enterprise_artifact.py`

**Methods:**
```python
def get(self, id: str, ctx: RequestContext) -> ArtifactDTO | None:
    """Get artifact by ID with tenant filtering.

    Args:
        id: Artifact ID (UUID or "type:name" format)
        ctx: RequestContext with tenant_id

    Returns:
        ArtifactDTO or None if not found or not in tenant
    """

def get_by_uuid(self, uuid: str, ctx: RequestContext) -> ArtifactDTO | None:
    """Get artifact by stable UUID (ADR-007) with tenant filtering."""
```

**Acceptance Criteria:**
- Both methods apply _apply_tenant_filter() automatically
- Returns ArtifactDTO with all metadata populated
- Returns None for non-existent or out-of-tenant artifacts (no error distinction)
- Supports both UUID and "type:name" ID formats
- Queries use indexes (tenant_id, created_at)

---

### ENT-2.3: EnterpriseArtifactRepository: List & Search

**Description:**

Implement collection queries with pagination, filtering, and tag search using JSONB operators.

**Methods:**
```python
def list(
    self,
    filters: dict[str, Any] | None = None,
    offset: int = 0,
    limit: int = 50,
    ctx: RequestContext | None = None,
) -> list[ArtifactDTO]:
    """List artifacts with optional filters and pagination."""
    # Supports filters:
    # - artifact_type: "skill" | "command" | "agent"
    # - project_id: UUID (for deployed artifacts)
    # - scope: "user" | "local"
    # - tags: ["tag1", "tag2"] (any match via JSONB)
    # - created_after: datetime
    # - created_before: datetime

def search_by_tags(
    self,
    tags: list[str],
    match_any: bool = True,
    ctx: RequestContext | None = None,
) -> list[ArtifactDTO]:
    """Search artifacts using JSONB tag containment.

    Args:
        tags: Tags to search for
        match_any: True = OR (any tag matches), False = AND (all tags)
        ctx: RequestContext with tenant_id

    Returns:
        List of matching ArtifactDTOs
    """
```

**JSONB Query Examples:**
```python
# Match any tag
query = query.where(Artifact.tags.contains({"tags": ["skill-building"]}))

# Match all tags (more complex)
for tag in tags:
    query = query.where(Artifact.tags.contains(tag))
```

**Acceptance Criteria:**
- list() supports all documented filters
- search_by_tags() uses JSONB operators (contains, has_key)
- Pagination works correctly (offset/limit)
- Sorting available (default: created_at DESC)
- All queries include tenant_id filter
- Queries use (tenant_id, artifact_type, created_at) composite index for performance

---

### ENT-2.4: EnterpriseArtifactRepository: Create & Update

**Description:**

Implement artifact creation with automatic initial version, and updates that create new versions.

**Methods:**
```python
def create(
    self,
    artifact_dto: ArtifactDTO,
    ctx: RequestContext,
) -> ArtifactDTO:
    """Create new artifact with automatic initial version.

    Args:
        artifact_dto: Artifact metadata (name, type, description, etc.)
        ctx: RequestContext with tenant_id

    Returns:
        Created ArtifactDTO with populated id and created_at

    Behavior:
        1. Insert artifact into enterprise_artifacts table
        2. Compute content_hash from artifact_dto.content
        3. Insert row into artifact_versions table
        4. Return artifact with version info
    """

def update(
    self,
    artifact_id: str,
    artifact_dto: ArtifactDTO,
    ctx: RequestContext,
) -> ArtifactDTO:
    """Update artifact and create new version if content changed.

    Args:
        artifact_id: ID to update
        artifact_dto: Updated metadata and/or content
        ctx: RequestContext with tenant_id

    Returns:
        Updated ArtifactDTO

    Behavior:
        1. Update metadata in artifacts table
        2. If content changed: create new row in artifact_versions
        3. Return updated artifact with new version
    """
```

**Acceptance Criteria:**
- create() inserts artifact and initial version atomically
- create() computes and stores content_hash
- update() creates new version only if content differs
- Both methods apply tenant_id automatically
- Unique constraint (tenant_id, name, type) respected
- Returns complete ArtifactDTO with all fields populated

---

### ENT-2.5: EnterpriseArtifactRepository: Delete & Archive

**Description:**

Implement soft and hard delete with cascade handling for collection references.

**Methods:**
```python
def delete(self, artifact_id: str, ctx: RequestContext) -> bool:
    """Soft-delete artifact (mark deleted_at without removing).

    Args:
        artifact_id: Artifact to soft-delete
        ctx: RequestContext with tenant_id

    Returns:
        True if deleted, False if not found or wrong tenant

    Behavior:
        1. Set deleted_at = NOW()
        2. Remove from all collections (cascade)
        3. Keep artifact_versions for audit trail
    """

def hard_delete(self, artifact_id: str, ctx: RequestContext) -> bool:
    """Permanently remove artifact and all versions.

    DANGEROUS: Removes audit trail. Only use for cleanup or GDPR.
    """
```

**Acceptance Criteria:**
- delete() is idempotent (multiple calls safe)
- delete() removes artifact from all collections
- hard_delete() removes artifact + all versions
- Both methods apply tenant_id filter
- Cascade removes collection_artifacts rows properly
- Soft-deleted artifacts still queryable (include deleted_at in list())

---

### ENT-2.6: EnterpriseArtifactRepository: Content Operations

**Description:**

Implement version history and content retrieval.

**Methods:**
```python
def get_content(
    self,
    artifact_id: str,
    version_hash: str | None = None,
    ctx: RequestContext | None = None,
) -> str:
    """Get artifact markdown content.

    Args:
        artifact_id: Artifact to retrieve
        version_hash: Specific version hash (SHA256). If None, latest.
        ctx: RequestContext with tenant_id

    Returns:
        Markdown content as string
    """

def list_versions(
    self,
    artifact_id: str,
    ctx: RequestContext | None = None,
) -> list[ArtifactVersionDTO]:
    """List all versions of artifact with creation metadata."""
```

**Acceptance Criteria:**
- get_content() returns markdown_payload from artifact_versions
- If version_hash provided, retrieves that specific version
- If not provided, retrieves latest (max created_at)
- list_versions() includes content_hash, created_at, version_label
- Proper error handling for missing artifacts or versions
- Queries use index on (artifact_id, created_at)

---

### ENT-2.7: EnterpriseCollectionRepository: CRUD Operations

**Description:**

Implement collection creation, reading, updating, and deletion with tenant scoping.

**File:** `skillmeat/cache/repositories/enterprise_collection.py`

**Methods:**
```python
def create(
    self,
    name: str,
    description: str = "",
    is_default: bool = False,
    ctx: RequestContext | None = None,
) -> CollectionDTO:
    """Create new collection with tenant scoping."""

def get(
    self,
    collection_id: str,
    ctx: RequestContext | None = None,
) -> CollectionDTO | None:
    """Get collection by ID."""

def list(
    self,
    filters: dict[str, Any] | None = None,
    ctx: RequestContext | None = None,
) -> list[CollectionDTO]:
    """List collections in tenant."""

def update(
    self,
    collection_id: str,
    name: str | None = None,
    description: str | None = None,
    is_default: bool | None = None,
    ctx: RequestContext | None = None,
) -> CollectionDTO:
    """Update collection metadata."""

def delete(
    self,
    collection_id: str,
    ctx: RequestContext | None = None,
) -> bool:
    """Delete collection (cascade to collection_artifacts)."""
```

**Acceptance Criteria:**
- All methods apply tenant_id filtering
- create() sets tenant_id from context
- Unique constraint (tenant_id, name) respected
- is_default logic: only one default per tenant
- delete() removes collection_artifacts rows (cascade)
- Returns complete CollectionDTO

---

### ENT-2.8: EnterpriseCollectionRepository: Membership Operations

**Description:**

Implement collection content management (add/remove artifacts, list with ordering).

**Methods:**
```python
def add_artifact(
    self,
    collection_id: str,
    artifact_id: str,
    order_index: int | None = None,
    ctx: RequestContext | None = None,
) -> CollectionArtifactDTO:
    """Add artifact to collection at specified order."""

def remove_artifact(
    self,
    collection_id: str,
    artifact_id: str,
    ctx: RequestContext | None = None,
) -> bool:
    """Remove artifact from collection."""

def list_artifacts(
    self,
    collection_id: str,
    offset: int = 0,
    limit: int = 50,
    ctx: RequestContext | None = None,
) -> list[ArtifactDTO]:
    """List all artifacts in collection in order."""

def reorder_artifacts(
    self,
    collection_id: str,
    order_map: dict[str, int],
    ctx: RequestContext | None = None,
) -> list[CollectionArtifactDTO]:
    """Reorder artifacts (drag-and-drop support)."""
```

**Acceptance Criteria:**
- add_artifact() maintains order_index for UI ordering
- Unique constraint prevents duplicate artifacts
- remove_artifact() is idempotent
- list_artifacts() returns in order_index ASC order
- reorder_artifacts() updates all order_index values atomically
- All queries apply tenant_id filtering to collection_id lookups

---

### ENT-2.9: Repository DI Factory and Wiring

**Description:**

Create a factory that returns the correct repository implementation (Local or Enterprise) based on configuration. In single-tenant bootstrap mode (Phases 1-3), the factory wires `DEFAULT_TENANT_ID` into all enterprise repositories. When PRD 2 is available, the factory is updated to read `AuthContext.tenant_id` from the request context — this is a config-level change only; no changes to repository implementations are required.

**File:** `skillmeat/cache/repositories/enterprise_factory.py`

**Key Features:**
```python
from skillmeat.cache.config import DEFAULT_TENANT_ID

class RepositoryFactory:
    """Factory for repository implementations.

    Returns Local or Enterprise repositories based on edition/database configuration.

    Bootstrap mode (Phases 1-3): Enterprise repos receive DEFAULT_TENANT_ID.
    Multi-tenant mode (Phase 4+ / PRD 2): Enterprise repos receive AuthContext.tenant_id.
    Switching between modes is a DI-level change only.
    """

    @staticmethod
    def create_artifact_repository(
        config: ConfigManager,
        tenant_id: str = DEFAULT_TENANT_ID,  # Overridden by PRD 2 AuthContext
    ) -> IArtifactRepository:
        """Return appropriate artifact repository.

        If DATABASE_URL set → EnterpriseArtifactRepository(tenant_id=tenant_id)
        Otherwise → LocalFileSystemRepository
        """

    @staticmethod
    def create_collection_repository(
        config: ConfigManager,
        tenant_id: str = DEFAULT_TENANT_ID,
    ) -> ICollectionRepository:
        """Return appropriate collection repository."""
```

**Integration with FastAPI DI:**
```python
# In skillmeat/api/dependencies.py

@lru_cache
def get_repository_factory(config: ConfigManager = Depends(get_config)) -> RepositoryFactory:
    return RepositoryFactory(config)

ArtifactRepositoryDep = Annotated[
    IArtifactRepository,
    Depends(lambda factory: factory.create_artifact_repository())
    # Phase 4 / PRD 2: pass tenant_id=auth_context.tenant_id here
]

# Usage in routers (unchanged between bootstrap and multi-tenant modes):
@router.get("/artifacts/{id}")
async def get_artifact(
    id: str,
    repo: ArtifactRepositoryDep,
) -> ArtifactDTO:
    return repo.get(id)  # Works for both Local and Enterprise
```

**Acceptance Criteria:**
- Factory returns LocalFileSystemRepository by default
- Returns EnterpriseArtifactRepository (with `DEFAULT_TENANT_ID`) when DATABASE_URL set
- Repository works with `DEFAULT_TENANT_ID` when AuthContext is not configured (bootstrap mode)
- Repository works with `AuthContext.tenant_id` when PRD 2 is available (pass via `tenant_id` param)
- DI wiring allows seamless backend swapping with no router code changes
- Switching from bootstrap → multi-tenant is a DI-level change only (no repo changes)
- Logging indicates which backend and tenant mode is active at startup

---

### ENT-2.10: Tenant Filtering Audit Layer

**Description:**

Implement request-scoped logging that tracks all repository calls with tenant context.

**File:** `skillmeat/cache/repositories/audit.py`

**Features:**
```python
class RepositoryAuditLogger:
    """Log all repository operations for debugging and security audit."""

    def log_query(
        self,
        operation: str,  # "get", "list", "create", etc.
        entity_type: str,  # "artifact", "collection"
        tenant_id: str,
        execution_time_ms: float,
        row_count: int,
    ) -> None:
        """Log repository operation."""
```

**Log Format:**
```
[REPO] operation=get entity=artifact tenant=<id> rows=1 time=0.5ms
[REPO] operation=list entity=collection tenant=<id> rows=15 time=2.1ms
```

**Acceptance Criteria:**
- Every repository call logs operation, entity, tenant_id, execution time
- Logs can be aggregated to audit: "artifact access on tenant X"
- No performance impact (async logging)
- Respects DEBUG log level (skip in production if needed)

---

### ENT-2.11: Unit Tests: Artifact Repository

**Description:**

Write comprehensive unit tests for EnterpriseArtifactRepository with mocked database.

**File:** `tests/unit/cache/test_enterprise_artifact_repository.py`

**Test Cases:**
```python
def test_get_returns_artifact_for_owned_tenant():
    """Verify get() returns artifact only for correct tenant."""

def test_get_returns_none_for_other_tenant():
    """Verify get() returns None for artifact from different tenant."""
    # SECURITY: Negative test ensuring no cross-tenant leakage

def test_list_filters_by_artifact_type():
    """Verify list(filters={artifact_type: "skill"}) returns only skills."""

def test_search_by_tags_uses_jsonb_operators():
    """Verify search_by_tags() uses PostgreSQL JSONB operators."""

def test_create_generates_content_hash():
    """Verify create() computes and stores SHA256 content_hash."""

def test_create_generates_initial_version():
    """Verify create() automatically creates artifact_versions row."""

def test_update_creates_new_version():
    """Verify update() with new content creates artifact_versions row."""

def test_delete_soft_deletes_only():
    """Verify delete() sets deleted_at, doesn't remove rows."""

def test_get_content_returns_latest_by_default():
    """Verify get_content() retrieves latest version when not specified."""

def test_get_content_returns_specific_version_by_hash():
    """Verify get_content(version_hash=X) retrieves exact version."""

def test_list_versions_returns_all_versions():
    """Verify list_versions() returns complete version history."""
```

**Acceptance Criteria:**
- 100% of public methods have test coverage
- All negative tests (cross-tenant access) pass
- Mocking strategy uses SQLAlchemy fixtures (not hand-mocked)
- Tests run in <5s
- Coverage report shows >90%

---

### ENT-2.12: Unit Tests: Collection Repository

**Description:**

Write comprehensive unit tests for EnterpriseCollectionRepository.

**File:** `tests/unit/cache/test_enterprise_collection_repository.py`

**Test Cases:**
```python
def test_create_sets_tenant_id():
    """Verify create() populates tenant_id from context."""

def test_create_enforces_unique_name_per_tenant():
    """Verify unique constraint on (tenant_id, name)."""

def test_list_isolates_tenants():
    """Verify list() returns only collections for requesting tenant."""

def test_add_artifact_maintains_order():
    """Verify add_artifact() respects order_index."""

def test_remove_artifact_is_idempotent():
    """Verify remove_artifact() succeeds even if already removed."""

def test_list_artifacts_returns_in_order():
    """Verify list_artifacts() returns in order_index ASC."""

def test_reorder_artifacts_updates_indexes():
    """Verify reorder_artifacts() atomically updates all indexes."""

def test_delete_cascades_to_collection_artifacts():
    """Verify delete() removes junction table rows."""
```

**Acceptance Criteria:**
- 100% of public methods have test coverage
- Isolation tests verify no cross-tenant leakage
- Order preservation verified for UI compatibility
- Coverage >90%

---

### ENT-2.13: Integration Tests: PostgreSQL

**Description:**

Write integration tests against real PostgreSQL (docker-compose) to verify multi-tenant isolation, concurrent writes, and performance.

**File:** `tests/integration/test_enterprise_repositories.py`

**Test Cases:**
```python
def test_multi_tenant_isolation(postgres_session):
    """Verify two tenants cannot see each other's artifacts."""
    # Create artifacts in tenant_a and tenant_b
    # Query from tenant_b should not see tenant_a's artifacts
    # SECURITY CRITICAL TEST

def test_concurrent_artifact_creation(postgres_session):
    """Verify no race conditions when creating artifacts concurrently."""
    # Use threading to create multiple artifacts simultaneously
    # Verify all succeed and have unique content_hashes

def test_large_collection_performance(postgres_session):
    """Verify performance with 1000+ artifacts in collection."""
    # Benchmark list_artifacts() with large collection
    # Ensure index usage (explain analyze)

def test_version_history_with_content_changes(postgres_session):
    """Verify version tracking correctly identifies content changes."""
    # Create artifact, update content twice, verify 2 versions exist
    # Update metadata only, verify no new version created

def test_constraint_enforcement(postgres_session):
    """Verify all database constraints are enforced."""
    # Try to insert artifact without tenant_id (should fail)
    # Try to add artifact twice to same collection (should fail)
    # Try to delete non-existent artifact (should succeed silently)
```

**Acceptance Criteria:**
- All tests pass against docker-compose PostgreSQL
- Tenant isolation verified with explicit multi-tenant scenarios
- Concurrent write tests pass (no deadlocks)
- Performance baselines established
- Constraints enforced at database level

---

### ENT-2.14: Performance Benchmarks

**Description:**

Establish baseline performance metrics for all repository operations to prevent regressions.

**File:** `tests/performance/test_enterprise_benchmarks.py`

**Benchmarks:**
```python
@pytest.mark.benchmark
def test_get_artifact_performance(benchmark):
    """get() should complete in <1ms."""
    # Benchmark: artifact_repo.get(artifact_id)
    # Assertion: result.median < 1.0  # ms

@pytest.mark.benchmark
def test_list_artifacts_1000_performance(benchmark):
    """list() with 1000 artifacts should complete in <10ms."""
    # Benchmark: artifact_repo.list(limit=1000)
    # Assertion: result.median < 10.0  # ms

@pytest.mark.benchmark
def test_search_by_tags_performance(benchmark):
    """search_by_tags() should complete in <5ms."""
    # Benchmark: artifact_repo.search_by_tags(["tag1"])
    # Assertion: result.median < 5.0  # ms

@pytest.mark.benchmark
def test_multitenancy_overhead(benchmark):
    """Multitenancy should add <5% overhead."""
    # Benchmark: single-tenant vs multi-tenant queries
    # Assertion: (multi_tenant - single_tenant) / single_tenant < 0.05
```

**Acceptance Criteria:**
- All benchmarks established as baseline
- Benchmarks integrated into CI/CD (fail if regressions >10%)
- Performance targets documented and achievable with current indexes
- Overhead from tenant filtering <5%

---

## Quality Gates

**Phase 2 Complete When:**

- [ ] All 14 tasks marked complete
- [ ] EnterpriseArtifactRepository implements all IArtifactRepository methods ✓
- [ ] EnterpriseCollectionRepository implements all ICollectionRepository methods ✓
- [ ] 100% of repository methods apply automatic tenant_id filtering ✓
- [ ] Unit test coverage >90% for enterprise repos ✓
- [ ] Integration tests pass against docker-compose PostgreSQL ✓
- [ ] Performance benchmarks established and within targets ✓
- [ ] Multi-tenant isolation verified with negative tests ✓
- [ ] Code reviewed by python-backend-engineer and data-layer-expert ✓

---

## Dependencies & Blockers

**Entry Criteria Met When:**
- Phase 1 schema migrations tested and merged
- PRD 1 repository interfaces finalized
- Python-backend-engineer and data-layer-expert available

**Note: PRD 2 (AuthContext / Multi-Tenancy) is NOT required for Phase 2.** Repositories use `DEFAULT_TENANT_ID` in constructor injection. PRD 2 only affects the DI wiring layer when real per-user tenancy is needed.

**Blocking on:**
- Phase 1 completion (schema must exist before repos)
- PRD 1 interface finalization (repositories must fulfill contracts)

**Exit Blockers for Phase 3:**
- If any repository method fails integration tests, Phase 3 cannot begin
- If tenant isolation tests fail, Phase 2 must be redesigned

---

## References

- **PRD 3:** docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md
- **PRD 1:** docs/project_plans/PRDs/refactors/repo-pattern-refactor-v1.md (defines repository interfaces)
- **Phase 1:** docs/project_plans/implementation_plans/refactors/enterprise-db-storage-v1/phase-1-schema.md
- **Repository Architecture:** `.claude/context/key-context/repository-architecture.md`
- **SQLAlchemy Docs:** https://docs.sqlalchemy.org/
- **Unit Testing:** `.claude/context/key-context/testing-patterns.md`

---

## Success Metrics

- All 14 tasks completed on schedule
- Unit test coverage >90%
- Integration tests passing with docker-compose PostgreSQL
- Performance overhead <5% from multitenancy
- Zero cross-tenant data leakage (all isolation tests pass)
