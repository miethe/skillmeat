# `skillmeat.core.interfaces` — Storage Backend Contracts

This package defines the hexagonal-architecture contracts between the application core and its infrastructure adapters. Nothing here may import from other SkillMeat modules except `skillmeat.core.enums` and `skillmeat.core.exceptions`.

## Abstract Repository Interfaces (10 ABCs)

| Interface | Router prefix | Description |
|-----------|---------------|-------------|
| `IArtifactRepository` | `/api/v1/artifacts` | Full artifact lifecycle: CRUD, search, file content, tag associations |
| `IProjectRepository` | `/api/v1/projects` | Projects (directories with deployed artifacts): CRUD, artifact listing, cache refresh |
| `ICollectionRepository` | `/api/v1/user-collections` | The user's personal artifact library: metadata, artifact listing, stats, refresh |
| `IDeploymentRepository` | `/api/v1/deployments` | Deploy/undeploy artifacts, query deployment status and history |
| `ITagRepository` | `/api/v1/tags` | Tag CRUD, slug lookup, artifact tag assignment/removal |
| `ISettingsRepository` | `/api/v1/settings` | Single-record user configuration: get, partial update, token validation |
| `IGroupRepository` | `/api/v1/groups` | Group management: CRUD, artifact membership, position ordering |
| `IContextEntityRepository` | `/api/v1/context-entities` | Context entity lifecycle: CRUD, type filtering, collection listing |
| `IMarketplaceSourceRepository` | `/api/v1/marketplace-sources` | Marketplace source and catalog management: CRUD, scan, catalog sync |
| `IProjectTemplateRepository` | `/api/v1/project-templates` | Project template management: CRUD, entity management, deployment |

## Domain DTOs (Frozen Dataclasses)

Lightweight, immutable transfer objects that cross layer boundaries without leaking ORM models or Pydantic types into the core. All DTOs expose a `from_dict()` classmethod.

`ArtifactDTO`, `ProjectDTO`, `CollectionDTO`, `DeploymentDTO`, `TagDTO`, `SettingsDTO`, `GroupDTO`, `GroupArtifactDTO`, `ContextEntityDTO`, `MarketplaceSourceDTO`, `CatalogItemDTO`, `ProjectTemplateDTO`, `TemplateEntityDTO`, `CollectionMembershipDTO`, `EntityTypeConfigDTO`, `CategoryDTO`

## RequestContext

Carries per-request metadata (auth, tracing, edition) through the call stack without threading globals. Accepted as an optional last argument on every repository method.

```python
from skillmeat.core.interfaces import RequestContext
ctx = RequestContext.create()  # auto-generates UUID request_id
```

## Adding a New Repository Interface

1. **Define the ABC** in `repositories.py` — inherit from `abc.ABC`, decorate all methods with `@abc.abstractmethod`, accept `ctx: RequestContext | None = None` as the last parameter.
2. **Add a DTO** to `dtos.py` if the interface needs a new data shape (frozen dataclass, `from_dict` classmethod).
3. **Export from `__init__.py`** — add both the interface and any new DTO to the `from ... import` block and `__all__`.
4. **Create a local implementation** in `skillmeat/core/repositories/local_<name>.py` — implement every abstract method.
5. **Register in `dependencies.py`** — add a factory provider (`get_<name>_repository`) and a typed DI alias (`<Name>RepoDep = Annotated[I<Name>Repository, Depends(...)]`).
6. **Add a mock** in `tests/mocks/repositories.py` for unit test use.

## Reference

- **Implementations**: `skillmeat/core/repositories/local_*.py`
- **DI wiring**: `skillmeat/api/dependencies.py` — factory providers + `*RepoDep` type aliases
- **Test doubles**: `tests/mocks/repositories.py`
