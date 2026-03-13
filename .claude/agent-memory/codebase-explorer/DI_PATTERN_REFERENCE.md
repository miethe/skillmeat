---
name: Complete Repository DI Pattern Reference
description: Comprehensive guide to SkillMeat's Hexagonal Architecture DI pattern, including all RepoDep types, interfaces, implementations, and usage examples
type: reference
---

# Dependency Injection Pattern for SkillMeat Enterprise Router Migration

**Last Updated**: 2026-03-12

## Overview

SkillMeat uses **Hexagonal Architecture** with abstract repository interfaces (ABCs) between routers and storage backends. FastAPI dependency injection wires concrete implementations (Local vs Enterprise) at runtime based on the `edition` setting.

**Key Invariant**: All *RepoDep aliases follow the same pattern:
```python
AliasNameRepoDep = Annotated[IInterface, Depends(get_concrete_provider)]
```

---

## 1. SettingsDep & Edition Mode

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/dependencies.py:1170`

```python
SettingsDep = Annotated[APISettings, Depends(get_settings)]
```

**Usage in routers**:
```python
async def my_endpoint(settings: SettingsDep) -> Response:
    if settings.edition == "enterprise":
        # Enterprise-specific logic
        pass
    elif settings.edition == "local":
        # Local-specific logic
        pass
```

**Available edition values**: `"local"` or `"enterprise"`

**Key Settings Fields**:
- `edition: str` - Deployment edition (controls repository selection)
- `auth_enabled: bool` - Master enforcement switch for authentication
- `auth_provider: str` - Provider selection (`"local"` or `"clerk"`)
- `cors_enabled: bool` - CORS enablement
- `port: int` - Server port
- `host: str` - Server bind address

---

## 2. All 19 RepoDep Type Aliases

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/dependencies.py:1170-1330`

### Standard Interface-Based (Interface → Concrete Implementation)

| Alias | Type | Getter Function | Local Implementation | Enterprise Implementation |
|-------|------|-----------------|----------------------|--------------------------|
| `ArtifactRepoDep` | `IArtifactRepository` | `get_artifact_repository` | LocalArtifactRepository | EnterpriseArtifactRepository |
| `ProjectRepoDep` | `IProjectRepository` | `get_project_repository` | LocalProjectRepository | EnterpriseProjectRepository |
| `CollectionRepoDep` | `ICollectionRepository` | `get_collection_repository` | LocalCollectionRepository | EnterpriseCollectionRepository |
| `DeploymentRepoDep` | `IDeploymentRepository` | `get_deployment_repository` | LocalDeploymentRepository | EnterpriseDeploymentRepository |
| `TagRepoDep` | `ITagRepository` | `get_tag_repository` | LocalTagRepository | EnterpriseTagRepository |
| `SettingsRepoDep` | `ISettingsRepository` | `get_settings_repository` | LocalSettingsRepository | EnterpriseSettingsRepository |
| `GroupRepoDep` | `IGroupRepository` | `get_group_repository` | LocalGroupRepository | EnterpriseGroupRepository |
| `ContextEntityRepoDep` | `IContextEntityRepository` | `get_context_entity_repository` | LocalContextEntityRepository | EnterpriseContextEntityRepository |
| `MarketplaceSourceRepoDep` | `IMarketplaceSourceRepository` | `get_marketplace_source_repository` | LocalMarketplaceSourceRepository | EnterpriseMarketplaceSourceRepository |
| `ProjectTemplateRepoDep` | `IProjectTemplateRepository` | `get_project_template_repository` | LocalProjectTemplateRepository | EnterpriseProjectTemplateRepository (stub) |
| `DbUserCollectionRepoDep` | `IDbUserCollectionRepository` | `get_db_user_collection_repository` | DbUserCollectionRepository | EnterpriseUserCollectionAdapter |
| `DbCollectionArtifactRepoDep` | `IDbCollectionArtifactRepository` | `get_db_collection_artifact_repository` | DbCollectionArtifactRepository | EnterpriseDbCollectionArtifactRepository |
| `DbArtifactHistoryRepoDep` | `IDbArtifactHistoryRepository` | `get_db_artifact_history_repository` | DbArtifactHistoryRepository | EnterpriseArtifactHistoryStub |

### Concrete Implementation-Based (Direct Classes)

| Alias | Type | Getter Function | Implementation |
|-------|------|-----------------|-----------------|
| `DeploymentSetRepoDep` | `DeploymentSetRepository` | `get_deployment_set_repository` | DeploymentSetRepository (or EnterpriseDeploymentSetRepository) |
| `DeploymentProfileRepoDep` | `DeploymentProfileRepository` | `get_deployment_profile_repository` | DeploymentProfileRepository (or EnterpriseDeploymentProfileRepository) |
| `MarketplaceCatalogRepoDep` | `MarketplaceCatalogRepository` | `get_marketplace_catalog_repository` | MarketplaceCatalogRepository (shared across editions) |
| `DuplicatePairRepoDep` | `DuplicatePairRepository` | `get_duplicate_pair_repository` | DuplicatePairRepository |

### Non-Repository Dependency

| Alias | Type | Getter Function | Implementation |
|-------|------|-----------------|-----------------|
| `MarketplaceTransactionHandlerDep` | `MarketplaceTransactionHandler` | `get_marketplace_transaction_handler` | MarketplaceTransactionHandler |

---

## 3. Repository Interface Signatures

**File**: `/home/miethe/dev/skillmeat/skillmeat/core/interfaces/repositories.py`

### IArtifactRepository (30+ methods)

**Location**: Lines 88-687

**Key Query Methods**:
```python
get(uuid: UUID) -> ArtifactDTO
get_by_uuid(uuid: UUID) -> ArtifactDTO
get_by_type(artifact_type: str) -> List[ArtifactDTO]
list(filters: Optional[dict]) -> List[ArtifactDTO]
count() -> int
search(query: str) -> List[ArtifactDTO]
get_ids_by_uuids(uuids: List[UUID]) -> Dict[str, str]  # UUID → type:name mapping
```

**Key Mutation Methods**:
```python
create(name: str, artifact_type: str, source: str, ...) -> ArtifactDTO
update(uuid: UUID, updates: dict) -> ArtifactDTO
delete(uuid: UUID) -> None
update_content(uuid: UUID, content: Any) -> ArtifactDTO
```

**Key Association Methods**:
```python
get_tags(artifact_uuid: UUID) -> List[str]
set_tags(artifact_uuid: UUID, tags: List[str]) -> None
get_collection_memberships(artifact_uuid: UUID) -> List[UUID]
get_duplicate_cluster_members(artifact_uuid: UUID) -> List[ArtifactDTO]
```

### ICollectionRepository (20+ methods)

**Location**: Lines 882-1270

**Key Query Methods**:
```python
get(collection_id: UUID) -> CollectionDTO
list() -> List[CollectionDTO]
get_artifacts(collection_id: UUID) -> List[ArtifactDTO]
get_stats(collection_id: UUID) -> dict
```

**Key Mutation Methods**:
```python
create(name: str, description: str = "") -> CollectionDTO
update(collection_id: UUID, updates: dict) -> CollectionDTO
delete(collection_id: UUID) -> None
add_artifacts(collection_id: UUID, artifact_uuids: List[UUID]) -> None
remove_artifact(collection_id: UUID, artifact_uuid: UUID) -> None
```

**Key Management Methods**:
```python
list_entities(collection_id: UUID) -> List[dict]
add_entity(collection_id: UUID, entity_dict: dict) -> None
remove_entity(collection_id: UUID, entity_id: str) -> None
```

### ITagRepository (11 methods)

**Location**: Lines 1507-1676

**Key Query Methods**:
```python
get(tag_id: UUID) -> TagDTO
get_by_slug(slug: str) -> TagDTO
list() -> List[TagDTO]
```

**Key Mutation Methods**:
```python
create(name: str, slug: str, ...) -> TagDTO
update(tag_id: UUID, updates: dict) -> TagDTO
delete(tag_id: UUID) -> None
```

**Key Association Methods**:
```python
assign(tag_id: UUID, artifact_uuid: UUID) -> None
unassign(tag_id: UUID, artifact_uuid: UUID) -> None
```

### IDeploymentRepository (10+ methods)

**Location**: Lines 1278-1499

**Key Query Methods**:
```python
get(deployment_id: UUID) -> DeploymentDTO
list() -> List[DeploymentDTO]
get_by_artifact(artifact_uuid: UUID) -> List[DeploymentDTO]
get_status(artifact_uuid: UUID) -> DeploymentStatus
```

**Key Mutation Methods**:
```python
deploy(artifact_uuid: UUID, project_path: str) -> DeploymentDTO
undeploy(artifact_uuid: UUID, project_path: str) -> None
```

**Key Cache Methods**:
```python
sync_deployment_cache() -> None
remove_deployment_cache(artifact_uuid: UUID) -> None
```

---

## 4. Router Pattern Example

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/groups.py` (fully migrated)

### Pattern: Dependency Injection in Route Signatures

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
from skillmeat.api.dependencies import (
    ArtifactRepoDep,        # ← Injected artifact repository
    GroupRepoDep,           # ← Injected group repository
    require_auth,           # ← Auth requirement
    get_auth_context,       # ← Auth context extraction
)
from skillmeat.api.schemas.auth import AuthContext

router = APIRouter(prefix="/groups", tags=["groups"])

@router.post("", response_model=GroupResponse, status_code=201)
async def create_group(
    request: GroupCreateRequest,
    group_repo: GroupRepoDep,  # ← FastAPI auto-injects based on type annotation
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> GroupResponse:
    """Create a new group in a collection.

    FastAPI sees the `GroupRepoDep` type annotation and automatically:
    1. Calls the getter function (get_group_repository)
    2. Checks AppState.settings.edition
    3. Returns LocalGroupRepository (if edition=="local")
       or EnterpriseGroupRepository (if edition=="enterprise")
    4. Injects the concrete instance into the route handler
    """
    # Use the repo as if it's the interface type (IGroupRepository)
    try:
        dto = group_repo.create(
            name=request.name,
            collection_id=request.collection_id,
            description=request.description,
            position=request.position,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _dto_to_group_response(dto)


@router.get("", response_model=GroupListResponse)
async def list_groups(
    group_repo: GroupRepoDep,
    collection_id: str = Query(..., description="Collection ID"),
    search: Optional[str] = Query(None),
    artifact_id: Optional[str] = Query(None),
    auth_context: AuthContext = Depends(get_auth_context),
) -> GroupListResponse:
    """List groups in a collection with optional filtering."""
    filters = {}
    if search:
        filters["search"] = search
    if artifact_id:
        filters["artifact_id"] = artifact_id

    try:
        dtos = group_repo.list(collection_id, filters=filters or None)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return GroupListResponse(groups=[_dto_to_group_response(dto) for dto in dtos])


def _dto_to_group_response(dto: GroupDTO) -> GroupResponse:
    """Convert DTO to response schema."""
    return GroupResponse(
        id=dto.id,
        collection_id=dto.collection_id,
        name=dto.name,
        description=dto.description,
        tags=list(dto.tags),
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    )
```

### Pattern: Using Multiple Repositories in One Route

```python
@router.get("/{group_id}", response_model=GroupWithArtifactsResponse)
async def get_group_with_artifacts(
    group_id: str,
    group_repo: GroupRepoDep,       # ← Multiple repos can be injected
    artifact_repo: ArtifactRepoDep, # ← FastAPI injects both
    auth_context: AuthContext = Depends(get_auth_context),
) -> GroupWithArtifactsResponse:
    """Get group with resolved artifact metadata."""
    # Get group from DB/filesystem
    group_dto = group_repo.get(group_id)

    # Get group artifacts with their UUIDs
    artifacts = group_repo.get_artifacts(group_id)

    # Resolve UUIDs to type:name IDs via artifact repo
    uuids = [a.artifact_uuid for a in artifacts]
    uuid_to_id = artifact_repo.get_ids_by_uuids(uuids)

    return GroupWithArtifactsResponse(
        id=group_dto.id,
        artifacts=[
            GroupArtifactResponse(
                artifact_uuid=a.artifact_uuid,
                artifact_id=uuid_to_id.get(a.artifact_uuid),
                position=a.position,
            )
            for a in artifacts
        ],
    )
```

---

## 5. Enterprise Repository Implementations

**File**: `/home/miethe/dev/skillmeat/skillmeat/cache/enterprise_repositories.py`

### Base Class: EnterpriseRepositoryBase

**Location**: Line 271

All enterprise repos inherit from this class, which:
- Takes a SQLAlchemy `session` in `__init__`
- Provides `_apply_tenant_filter()` for automatic tenant scoping
- Manages tenant context via `TenantContext: ContextVar[Optional[UUID]]`

```python
class EnterpriseRepositoryBase(Generic[T_Model]):
    """Base class for all enterprise (PostgreSQL) repositories.

    Provides automatic tenant filtering and session management.
    """
    def __init__(self, session: Session):
        self.session = session

    def _apply_tenant_filter(self, query: Select) -> Select:
        """Automatically filter results to current tenant."""
        from skillmeat.cache.enterprise_repositories import TenantContext
        tenant_id = TenantContext.get()
        if tenant_id:
            query = query.where(Model.tenant_id == tenant_id)
        return query
```

### Key Enterprise Repositories

| Class | Interface | Location | Key Methods |
|-------|-----------|----------|-------------|
| `EnterpriseArtifactRepository` | IArtifactRepository | Line 591 | get, list, create, update, delete, get_tags, set_tags |
| `EnterpriseCollectionRepository` | ICollectionRepository | Line 1482 | get, list, create, update, delete, add_artifacts |
| `EnterpriseTagRepository` | ITagRepository | Line 2382 | get, list, create, update, delete, assign, unassign |
| `EnterpriseGroupRepository` | IGroupRepository | Line 2901 | get, list, create, update, delete, get_artifacts |
| `EnterpriseDeploymentRepository` | IDeploymentRepository | Line 5750 | get, list, deploy, undeploy, sync_deployment_cache |
| `EnterpriseSettingsRepository` | ISettingsRepository | Line 3878 | get, set, delete |
| `EnterpriseContextEntityRepository` | IContextEntityRepository | Line 4639 | get, list, create, update, delete |
| `EnterpriseProjectRepository` | IProjectRepository | Line 5211 | get, list, create, update, delete |

---

## 6. How Dependency Injection Works in SkillMeat

### Step-by-Step Flow

1. **Route Handler Declares Dependency**:
   ```python
   async def my_endpoint(artifact_repo: ArtifactRepoDep):
   ```

2. **FastAPI Type Annotation Processing**:
   - Recognizes `ArtifactRepoDep` as `Annotated[IArtifactRepository, Depends(get_artifact_repository)]`
   - Extracts the `Depends(get_artifact_repository)` part

3. **Getter Function Called**:
   ```python
   # FastAPI calls this function
   def get_artifact_repository(
       state: Annotated[AppState, Depends(get_app_state)],
       session: Annotated[Session, Depends(get_db_session)],
   ) -> IArtifactRepository:
       edition = state.settings.edition
       if edition == "local":
           return LocalArtifactRepository(...)
       elif edition == "enterprise":
           return EnterpriseArtifactRepository(session=session)
   ```

4. **Concrete Implementation Returned**:
   - Returns either `LocalArtifactRepository` or `EnterpriseArtifactRepository`
   - Both implement `IArtifactRepository` interface

5. **Instance Injected into Handler**:
   - The concrete instance is passed to the route handler
   - Handler code uses the repository through the interface

### Key Architecture Files

| File | Purpose | Line Range |
|------|---------|-----------|
| `/skillmeat/api/dependencies.py` | All getter functions and *RepoDep aliases | 560-1330 |
| `/skillmeat/core/interfaces/repositories.py` | Interface definitions (ABCs) | 77+ |
| `/skillmeat/core/repositories/` | Local implementations | - |
| `/skillmeat/cache/enterprise_repositories.py` | Enterprise implementations | 271+ |
| `/skillmeat/cache/session.py` | SQLAlchemy session management | - |

---

## 7. Tenant Filtering (Enterprise Only)

**File**: `/skillmeat/cache/enterprise_repositories.py:99-138`

All enterprise repositories automatically filter results to the current tenant:

```python
TenantContext: ContextVar[Optional[uuid.UUID]] = ContextVar("tenant_id", default=None)

@contextmanager
def tenant_scope(tenant_id: uuid.UUID):
    """Context manager to set tenant scope for a block of code."""
    token = TenantContext.set(tenant_id)
    try:
        yield
    finally:
        TenantContext.reset(token)
```

**Usage in endpoints**:
```python
with tenant_scope(request_tenant_id):
    # All repo queries automatically filtered to this tenant
    artifacts = artifact_repo.list()  # Only artifacts in this tenant
```

---

## 8. Guidelines for Router Migration

### When Adding a New Endpoint

1. **Check if interface exists**:
   - Search `/skillmeat/core/interfaces/repositories.py` for the interface
   - If not, create it first

2. **Declare RepoDep in route signature**:
   ```python
   async def my_endpoint(
       artifact_repo: ArtifactRepoDep,  # ← Declare here
       settings: SettingsDep,
   ):
   ```

3. **Use repository methods**:
   ```python
   # Don't do this:
   artifact = db.query(Artifact).filter(...).first()

   # Do this instead:
   artifact = artifact_repo.get(uuid)
   ```

4. **Handle exceptions**:
   ```python
   try:
       dto = artifact_repo.create(...)
   except KeyError:
       raise HTTPException(404, "Not found")
   except ValueError as e:
       raise HTTPException(400, str(e))
   ```

### When Migrating Existing Manager-Based Endpoint

1. **Replace manager with repo**:
   ```python
   # OLD:
   async def my_endpoint(artifact_mgr: ArtifactManagerDep):
       artifact = artifact_mgr.get_artifact(artifact_id)

   # NEW:
   async def my_endpoint(artifact_repo: ArtifactRepoDep):
       artifact = artifact_repo.get(artifact_id)
   ```

2. **Verify all access patterns**:
   - Check if interface has a method for what you need
   - If not, add to interface first

3. **Test both editions**:
   - Local: Uses filesystem-backed LocalArtifactRepository
   - Enterprise: Uses DB-backed EnterpriseArtifactRepository

---

## 9. Key Invariants

1. **No direct DB queries in routers** - Always use repository DI
2. **No manager access in new routers** - Use repositories instead
3. **Edition is transparent to routes** - Dependency injection handles it
4. **Tenant filtering automatic** - Enterprise repos handle it in `_apply_tenant_filter()`
5. **DTOs are the data contract** - Never pass ORM models to route handlers
6. **All interfaces are ABCs** - Force implementation of contracts
7. **Getters decide edition** - Central routing logic in `dependencies.py`

