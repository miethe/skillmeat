# Repository Architecture (Hexagonal Pattern)

**Status**: Active Policy
**Phase**: Complete (gap-closure done)
**Last Updated**: 2026-03-05

---

## Overview

SkillMeat uses **hexagonal architecture** (ports & adapters) with abstract repository interfaces sitting between API routers and all storage backends. This design:

- **Decouples** the API layer from filesystem/SQLite implementation details
- **Enables** multi-backend support (PostgreSQL, S3, cloud stores) in the future
- **Simplifies** testing via mock repositories
- **Enforces** contracts through abstract base classes (ABCs)

The pattern flows:

```
HTTP Request
    ↓
Router (skillmeat/api/routers/*)
    ↓
Repository Dependency (via Annotated + Depends)
    ↓
Repository Implementation (skillmeat/core/repositories/local_*)
    ↓
Filesystem / SQLAlchemy ORM / External Storage
```

---

## Core Invariants (MUST Follow)

### Invariant 1: New Endpoints Use Repository DI

**Rule**: Every new API endpoint MUST use repository dependency injection. No direct `os`, `pathlib`, or `sqlite3` imports in routers.

**Violation Example** (WRONG):
```python
# skillmeat/api/routers/artifacts.py
import os
from pathlib import Path

@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str):
    # WRONG: Direct filesystem access in router
    artifact_path = Path.home() / ".skillmeat" / artifact_id
    if artifact_path.exists():
        return {"content": artifact_path.read_text()}
    raise HTTPException(404, "Not found")
```

**Correct Example** (RIGHT):
```python
# skillmeat/api/routers/artifacts.py
from skillmeat.api.dependencies import ArtifactRepoDep

@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    artifact_repo: ArtifactRepoDep,  # Injected by FastAPI
):
    artifact_dto = artifact_repo.get(artifact_id)
    if not artifact_dto:
        raise HTTPException(404, f"Artifact '{artifact_id}' not found")
    return ArtifactResponse.from_dto(artifact_dto)
```

### Invariant 2: Storage Access via Repository Abstraction

**Rule**: All storage access in routers goes through `Annotated[I*Repository, Depends(get_*_repository)]` dependency parameters.

**Syntax**:
```python
from skillmeat.api.dependencies import (
    ArtifactRepoDep,           # Annotated[IArtifactRepository, Depends(...)]
    ProjectRepoDep,            # Annotated[IProjectRepository, Depends(...)]
    CollectionRepoDep,         # Annotated[ICollectionRepository, Depends(...)]
    DeploymentRepoDep,         # Annotated[IDeploymentRepository, Depends(...)]
    TagRepoDep,                # Annotated[ITagRepository, Depends(...)]
    SettingsRepoDep,           # Annotated[ISettingsRepository, Depends(...)]
    GroupRepoDep,              # Annotated[IGroupRepository, Depends(...)]
    ContextEntityRepoDep,      # Annotated[IContextEntityRepository, Depends(...)]
    MarketplaceSourceRepoDep,  # Annotated[IMarketplaceSourceRepository, Depends(...)]
    ProjectTemplateRepoDep,    # Annotated[IProjectTemplateRepository, Depends(...)]
)

@router.get("/artifacts")
async def list_artifacts(artifact_repo: ArtifactRepoDep) -> List[ArtifactResponse]:
    artifacts = artifact_repo.list()
    return [ArtifactResponse.from_dto(a) for a in artifacts]
```

### Invariant 3: DTOs as Data Contract

**Rule**: DTOs from `skillmeat.core.interfaces.dtos` are the API layer's data contract. Never pass ORM models (SQLAlchemy) or filesystem objects to routers.

**Why**: DTOs enforce a stable boundary between the core and infrastructure. If ORM models leak into routers, future storage backend changes require router rewrites.

**Violation Example** (WRONG):
```python
# skillmeat/api/routers/artifacts.py
from skillmeat.cache.models import CollectionArtifact  # ORM model

@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str):
    orm_model = db.query(CollectionArtifact).filter(...).first()
    return ArtifactResponse.from_orm(orm_model)  # Leaks ORM into router
```

**Correct Example** (RIGHT):
```python
# skillmeat/api/routers/artifacts.py
from skillmeat.core.interfaces.dtos import ArtifactDTO

@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str, artifact_repo: ArtifactRepoDep):
    artifact_dto: ArtifactDTO | None = artifact_repo.get(artifact_id)
    if not artifact_dto:
        raise HTTPException(404)
    return ArtifactResponse.from_dto(artifact_dto)
```

### Invariant 4: Write-Through Pattern

**Rule**: Mutations write filesystem first, then sync to DB via `refresh_single_artifact_cache()`.

**Pattern**:
```python
@router.post("/artifacts")
async def create_artifact(
    request: ArtifactCreateRequest,
    artifact_repo: ArtifactRepoDep,
):
    # 1. Repository writes to filesystem (via artifact_manager)
    artifact_dto = artifact_repo.create(
        name=request.name,
        artifact_type=request.artifact_type,
        ...
    )

    # 2. Sync DB cache (in service layer or router)
    from skillmeat.cache.refresh import refresh_single_artifact_cache
    refresh_single_artifact_cache(artifact_dto.id)

    # 3. Return to client
    return ArtifactResponse.from_dto(artifact_dto), 201
```

See root `CLAUDE.md` → "Data Flow Principles" for full write-through semantics.

### Invariant 5: Mock Updates

**Rule**: When you change an ABC in `skillmeat/core/interfaces/repositories.py`, update the corresponding mock in `tests/mocks/repositories.py`.

**Pattern**:
```python
# If you add a method to IArtifactRepository:
class IArtifactRepository(abc.ABC):
    @abc.abstractmethod
    def search_by_tag(self, tag: str) -> List[ArtifactDTO]:
        raise NotImplementedError

# Then add the mock:
class MockArtifactRepository(IArtifactRepository):
    def search_by_tag(self, tag: str) -> List[ArtifactDTO]:
        return [a for a in self._artifacts.values() if tag in a.tags]
```

---

## Module Map

### 1. Interfaces Layer
**Location**: `skillmeat/core/interfaces/`

| File | Purpose |
|------|---------|
| `repositories.py` | 10 ABC interfaces: `IArtifactRepository`, `IProjectRepository`, `ICollectionRepository`, `IDeploymentRepository`, `ITagRepository`, `ISettingsRepository`, `IGroupRepository`, `IContextEntityRepository`, `IMarketplaceSourceRepository`, `IProjectTemplateRepository` |
| `dtos.py` | 16 frozen dataclasses: `ArtifactDTO`, `ProjectDTO`, `CollectionDTO`, `DeploymentDTO`, `TagDTO`, `SettingsDTO`, `CollectionMembershipDTO`, `EntityTypeConfigDTO`, `CategoryDTO`, `GroupDTO`, `GroupArtifactDTO`, `ContextEntityDTO`, `MarketplaceSourceDTO`, `CatalogItemDTO`, `ProjectTemplateDTO`, `TemplateEntityDTO` |
| `context.py` | RequestContext (per-request metadata: auth, tracing, etc.) |
| `__init__.py` | Public exports |

**Key Constraint**: No imports from other skillmeat modules except `skillmeat.core.enums` and `skillmeat.core.exceptions`.

### 2. Repository Implementations
**Location**: `skillmeat/core/repositories/`

| File | Implements | Backing Store |
|------|-----------|----------------|
| `local_artifact.py` | IArtifactRepository | Filesystem + SQLAlchemy cache |
| `local_project.py` | IProjectRepository | Filesystem + SQLAlchemy cache |
| `local_collection.py` | ICollectionRepository | Filesystem (CollectionManager) |
| `local_deployment.py` | IDeploymentRepository | Filesystem + SQLAlchemy cache |
| `local_tag.py` | ITagRepository | SQLAlchemy cache only |
| `local_settings_repo.py` | ISettingsRepository | TOML files + SQLAlchemy cache |
| `local_group.py` | IGroupRepository | SQLAlchemy cache only |
| `local_context_entity.py` | IContextEntityRepository | SQLAlchemy cache only |
| `local_marketplace_source.py` | IMarketplaceSourceRepository | SQLAlchemy cache only |
| `local_project_template.py` | IProjectTemplateRepository | SQLAlchemy cache only |

Each implementation:
- Receives **managers** (ArtifactManager, CollectionManager, etc.) via constructor DI
- Receives **PathResolver** for filesystem navigation
- Returns DTOs, never ORM models
- Delegates to managers for complex logic (filesystem I/O, artifact parsing, etc.)

### 3. Dependency Injection Factory
**Location**: `skillmeat/api/dependencies.py`

| Function | Returns | DI Alias |
|----------|---------|----------|
| `get_artifact_repository()` | IArtifactRepository | `ArtifactRepoDep` |
| `get_project_repository()` | IProjectRepository | `ProjectRepoDep` |
| `get_collection_repository()` | ICollectionRepository | `CollectionRepoDep` |
| `get_deployment_repository()` | IDeploymentRepository | `DeploymentRepoDep` |
| `get_tag_repository()` | ITagRepository | `TagRepoDep` |
| `get_settings_repository()` | ISettingsRepository | `SettingsRepoDep` |
| `get_group_repository()` | IGroupRepository | `GroupRepoDep` |
| `get_context_entity_repository()` | IContextEntityRepository | `ContextEntityRepoDep` |
| `get_marketplace_source_repository()` | IMarketplaceSourceRepository | `MarketplaceSourceRepoDep` |
| `get_project_template_repository()` | IProjectTemplateRepository | `ProjectTemplateRepoDep` |

**Edition-Based Routing** (Future):
```python
def get_artifact_repository(state: AppState) -> IArtifactRepository:
    edition = state.settings.edition if state.settings else "local"
    if edition == "local":
        return LocalArtifactRepository(...)
    elif edition == "postgres":  # Future
        return PostgresArtifactRepository(...)
    else:
        raise HTTPException(503, f"Unsupported edition: {edition}")
```

Currently, only `"local"` edition is implemented.

### 4. Mock Repositories (Testing)
**Location**: `tests/mocks/repositories.py`

| Class | Implements |
|-------|-----------|
| `MockArtifactRepository` | IArtifactRepository |
| `MockProjectRepository` | IProjectRepository |
| `MockCollectionRepository` | ICollectionRepository |
| `MockDeploymentRepository` | IDeploymentRepository |
| `MockTagRepository` | ITagRepository |
| `MockSettingsRepository` | ISettingsRepository |

All mocks are in-memory (no filesystem or DB I/O). `IGroupRepository`, `IContextEntityRepository`, `IMarketplaceSourceRepository`, and `IProjectTemplateRepository` do not yet have dedicated mocks — tests for those interfaces use the DI override pattern with `MagicMock` or `patch.object` directly.

**Use in Tests**:
```python
# Fixture
@pytest.fixture
def artifact_repo():
    repo = MockArtifactRepository()
    yield repo
    repo.reset()

# Test
def test_list_artifacts(artifact_repo):
    repo.create(name="test-skill", artifact_type="skill", ...)
    artifacts = repo.list()
    assert len(artifacts) == 1
```

---

## Quick Recipes

### Recipe 1: Adding a New Endpoint

**Task**: Create `GET /api/v1/artifacts/{id}/metadata` that returns artifact metadata.

**Steps**:

1. **Define the route** with repository dependency:
   ```python
   # skillmeat/api/routers/artifacts.py
   from skillmeat.api.dependencies import ArtifactRepoDep
   from skillmeat.api.schemas.artifacts import ArtifactMetadataResponse

   @router.get("/{artifact_id}/metadata", response_model=ArtifactMetadataResponse)
   async def get_artifact_metadata(
       artifact_id: str,
       artifact_repo: ArtifactRepoDep,
   ) -> ArtifactMetadataResponse:
       # Call repository
       artifact_dto = artifact_repo.get(artifact_id)
       if not artifact_dto:
           raise HTTPException(404, f"Artifact '{artifact_id}' not found")

       # Convert DTO to response schema
       return ArtifactMetadataResponse(
           id=artifact_dto.id,
           name=artifact_dto.name,
           artifact_type=artifact_dto.artifact_type,
           created_at=artifact_dto.created_at,
           updated_at=artifact_dto.updated_at,
       )
   ```

2. **Define the response schema** (already exists, reuse):
   ```python
   # skillmeat/api/schemas/artifacts.py
   class ArtifactMetadataResponse(BaseModel):
       id: str
       name: str
       artifact_type: str
       created_at: datetime
       updated_at: datetime
   ```

3. **Test it** using the mock:
   ```python
   # skillmeat/api/tests/test_artifacts.py
   from tests.mocks.repositories import MockArtifactRepository

   def test_get_artifact_metadata():
       repo = MockArtifactRepository()
       repo.create(name="test", artifact_type="skill", ...)

       artifact = repo.get("skill:test")
       assert artifact is not None
       assert artifact.name == "test"
   ```

4. **Never**:
   - Import `pathlib.Path` or `os` in the router
   - Query the database directly (no SQLAlchemy ORM models)
   - Access filesystem via `artifact_manager` directly in the router

---

### Recipe 2: Adding a New Storage Backend (e.g., PostgreSQL)

**Task**: Create a PostgreSQL adapter for artifacts.

**Steps**:

1. **Implement all 10 ABCs** (IArtifactRepository, IProjectRepository, ICollectionRepository, IDeploymentRepository, ITagRepository, ISettingsRepository, IGroupRepository, IContextEntityRepository, IMarketplaceSourceRepository, IProjectTemplateRepository):
   ```python
   # skillmeat/core/repositories/postgres_artifact.py
   from skillmeat.core.interfaces.repositories import IArtifactRepository
   from skillmeat.core.interfaces.dtos import ArtifactDTO

   class PostgresArtifactRepository(IArtifactRepository):
       def __init__(self, connection_string: str):
           self.db = create_engine(connection_string)

       def get(self, id: str, ctx=None) -> ArtifactDTO | None:
           # Query PostgreSQL
           result = self.db.query(PostgresArtifact).filter_by(id=id).first()
           if result:
               return ArtifactDTO(...)  # Convert to DTO
           return None

       def list(self, filters=None, ctx=None) -> List[ArtifactDTO]:
           # ... implement other methods
           pass
   ```

2. **Register in factory** (`dependencies.py`):
   ```python
   def get_artifact_repository(state: AppState) -> IArtifactRepository:
       edition = state.settings.edition if state.settings else "local"
       if edition == "local":
           return LocalArtifactRepository(...)
       elif edition == "postgres":
           from skillmeat.core.repositories import PostgresArtifactRepository
           return PostgresArtifactRepository(
               connection_string=state.settings.postgres_dsn
           )
       else:
           raise HTTPException(503, f"Unsupported edition: {edition}")
   ```

3. **Update config** (`skillmeat/api/config.py`):
   ```python
   class APISettings(BaseSettings):
       edition: str = "local"  # New field
       postgres_dsn: Optional[str] = None  # PostgreSQL connection string
   ```

4. **No router changes needed** — the dependency injection handles the swap automatically.

---

### Recipe 3: Updating Mock Repositories After ABC Changes

**Task**: You add a method `search_by_tags()` to IArtifactRepository.

**Steps**:

1. **Add abstract method** to ABC:
   ```python
   # skillmeat/core/interfaces/repositories.py
   class IArtifactRepository(abc.ABC):
       @abc.abstractmethod
       def search_by_tags(
           self,
           tags: List[str],
           ctx: RequestContext | None = None,
       ) -> List[ArtifactDTO]:
           """Return artifacts matching any of the given tags."""
           raise NotImplementedError
   ```

2. **Implement in mock**:
   ```python
   # tests/mocks/repositories.py
   class MockArtifactRepository(IArtifactRepository):
       def search_by_tags(self, tags: List[str], ctx=None) -> List[ArtifactDTO]:
           if not tags:
               return []
           result = []
           for artifact in self._artifacts.values():
               if any(tag in artifact.tags for tag in tags):
                   result.append(artifact)
           return result
   ```

3. **Implement in local repository**:
   ```python
   # skillmeat/core/repositories/local_artifact.py
   class LocalArtifactRepository(IArtifactRepository):
       def search_by_tags(self, tags: List[str], ctx=None) -> List[ArtifactDTO]:
           # Query the artifact manager or database
           results = []
           for artifact in self._artifacts:
               if any(tag in artifact.tags for tag in tags):
                   results.append(artifact)
           return results
   ```

4. **Implement in PostgreSQL adapter**:
   ```python
   # skillmeat/core/repositories/postgres_artifact.py
   class PostgresArtifactRepository(IArtifactRepository):
       def search_by_tags(self, tags: List[str], ctx=None) -> List[ArtifactDTO]:
           # Query PostgreSQL with JOIN to tags table
           results = self.db.query(PostgresArtifact).join(...).filter(...).all()
           return [ArtifactDTO(...) for result in results]
   ```

---

## Known Remaining Cleanup

### 1. `user_collections.py` — Largest Remaining Footprint

**Status**: Tracked under `db-user-collection-repository-v1` plan
**Note**: `skillmeat/api/routers/user_collections.py` still contains approximately 50 direct `session.query()` calls. This is the largest remaining DI migration target. The `db-user-collection-repository-v1` implementation plan covers the full migration.

### 2. `artifacts.py` + 4 Other Routers — Residual Session Queries

**Status**: Tracked under `db-user-collection-repository-v1` Phase 6
**Note**: 21 residual `session.query()` calls across 5 routers (artifacts.py: 15, artifact_history.py: 2, deployment_profiles.py: 2, projects.py: 1, tags.py: 1). These were over-claimed in gap-closure Phases 4-6 and are now tracked as Phase 6 of the db-user-collection-repository plan.

### 4. Exception Type Imports from `cache.repositories`

**Status**: Whitelisted
**Note**: Imports of `ConstraintError`, `NotFoundError`, and `RepositoryError` from `skillmeat.cache.repositories` are permitted in routers and services. These exception types are not ORM models and carry no data-access coupling.

---

## Design Principles

### Why Hexagonal Architecture?

1. **Testability**: Mock repositories enable fast unit tests without filesystem I/O
2. **Flexibility**: Swap storage backends without touching routers
3. **Clarity**: Explicit data contracts (DTOs) prevent leaky abstractions
4. **Maintainability**: Clear separation of concerns

### DTO Immutability

All DTOs are **frozen dataclasses**:
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ArtifactDTO:
    id: str
    name: str
    # ... other fields
```

This enforces immutability at the boundary — mutations return new DTOs via `dataclasses.replace()`.

### RequestContext (Per-Request Metadata)

Context flows through method calls without threading globals:
```python
# In a router
ctx = RequestContext(
    user_id="john@example.com",
    request_id="req-12345",
    trace_id="trace-abcdef",
)

# Pass to repository
artifacts = artifact_repo.list(ctx=ctx)
```

---

## Related Documentation

- **Router Patterns**: `.claude/context/key-context/router-patterns.md`
- **Data Flow**: `.claude/context/key-context/data-flow-patterns.md`
- **Type Sync**: `.claude/context/key-context/fe-be-type-sync-playbook.md`
- **API Contracts**: `.claude/context/key-context/api-contract-source-of-truth.md`
- **Root Architecture**: `CLAUDE.md` → "Architecture Overview"

---

## Checklist: Adding Repository DI to a Router

Use this checklist when migrating an existing router to repository DI:

- [ ] Read interface ABC in `skillmeat/core/interfaces/repositories.py`
- [ ] Add dependency parameter to route(s): `artifact_repo: ArtifactRepoDep`
- [ ] Replace direct filesystem/DB access with repository method calls
- [ ] Convert returned DTOs to Pydantic response schemas
- [ ] Remove direct imports of `pathlib`, `os`, SQLAlchemy ORM models
- [ ] Update or create mock implementation in `tests/mocks/repositories.py`
- [ ] Write tests using the mock (no filesystem I/O required)
- [ ] Verify endpoint still works end-to-end
- [ ] Commit with message: `refactor(api): migrate <router> to repository DI`

---

**Last Reviewed**: 2026-03-05
**Next Review**: After `db-user-collection-repository-v1` plan completes (user_collections.py + residual router cleanup)
