# `skillmeat.core.interfaces` — Storage Backend Contracts

This package defines the hexagonal-architecture contracts between the application core and its infrastructure adapters.  Nothing here may import from other SkillMeat modules except `skillmeat.core.enums` and `skillmeat.core.exceptions`.

## What This Module Provides

### Abstract Repository Interfaces (ABCs)

Six interfaces define the data-access contracts every storage backend must implement.  The core never depends on any concrete storage technology.

| Interface | Router | Description |
|-----------|--------|-------------|
| `IArtifactRepository` | `/api/v1/artifacts` | Full artifact lifecycle: CRUD, search, file content, tag associations |
| `IProjectRepository` | `/api/v1/projects` | Projects (directories with deployed artifacts): CRUD, artifact listing, cache refresh |
| `ICollectionRepository` | `/api/v1/user-collections` | The user's personal artifact library: metadata, artifact listing, stats, refresh |
| `IDeploymentRepository` | `/api/v1/deploy` | Deploy/undeploy artifacts, query deployment status and history |
| `ITagRepository` | `/api/v1/tags` | Tag CRUD, slug lookup, artifact tag assignment/removal |
| `ISettingsRepository` | `/api/v1/settings` | Single-record user configuration: get, partial update, token validation |

### Domain DTOs (Frozen Dataclasses)

Lightweight, immutable data transfer objects that cross layer boundaries without leaking ORM models or Pydantic types into the core.  All DTOs expose a `from_dict()` classmethod for construction from plain dicts.

| DTO | Key fields |
|-----|------------|
| `ArtifactDTO` | `id` (type:name), `uuid`, `name`, `artifact_type`, `source`, `version`, `scope`, `tags` |
| `ProjectDTO` | `id` (base64-encoded path), `name`, `path`, `status`, `artifact_count` |
| `CollectionDTO` | `id`, `name`, `path`, `version`, `artifact_count` |
| `DeploymentDTO` | `id`, `artifact_id`, `artifact_type`, `project_id`, `scope`, `status`, `target_path` |
| `TagDTO` | `id`, `name`, `slug`, `color`, `artifact_count` |
| `SettingsDTO` | `github_token`, `collection_path`, `default_scope`, `edition`, `indexing_mode`, `extra` |

### RequestContext

Carries per-request metadata (auth, tracing, edition) through the call stack without threading globals.

```python
from skillmeat.core.interfaces import RequestContext

ctx = RequestContext.create()           # auto-generates a UUID request_id
ctx = RequestContext(user_id="alice")   # explicit construction
```

Every repository method accepts an optional `ctx: RequestContext | None = None` as its last argument.

## How to Implement a New Storage Backend

Implement all six ABCs, then register them in `dependencies.py`.

### Step 1 — Create the Implementation Module

```python
# skillmeat/core/repositories/my_backend_artifact.py
import abc
from skillmeat.core.interfaces.context import RequestContext
from skillmeat.core.interfaces.dtos import ArtifactDTO, TagDTO
from skillmeat.core.interfaces.repositories import IArtifactRepository

class MyBackendArtifactRepository(IArtifactRepository):
    """Example: artifact repository backed by a remote API."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def get(self, id: str, ctx: RequestContext | None = None) -> ArtifactDTO | None:
        # fetch from remote, convert to ArtifactDTO, return None if 404
        ...

    def get_by_uuid(self, uuid: str, ctx: RequestContext | None = None) -> ArtifactDTO | None:
        ...

    def list(self, filters=None, offset=0, limit=50, ctx=None) -> list[ArtifactDTO]:
        ...

    def count(self, filters=None, ctx=None) -> int:
        ...

    def search(self, query: str, filters=None, ctx=None) -> list[ArtifactDTO]:
        ...

    def create(self, dto: ArtifactDTO, ctx=None) -> ArtifactDTO:
        ...

    def update(self, id: str, updates: dict, ctx=None) -> ArtifactDTO:
        ...

    def delete(self, id: str, ctx=None) -> bool:
        ...

    def get_content(self, id: str, ctx=None) -> str:
        ...

    def update_content(self, id: str, content: str, ctx=None) -> bool:
        ...

    def get_tags(self, id: str, ctx=None) -> list[TagDTO]:
        ...

    def set_tags(self, id: str, tag_ids: list[str], ctx=None) -> bool:
        ...
```

Repeat for the other five interfaces (`IProjectRepository`, `ICollectionRepository`, `IDeploymentRepository`, `ITagRepository`, `ISettingsRepository`).

### Step 2 — Register in `dependencies.py`

Factory providers live in `skillmeat/api/dependencies.py`.  Each returns the concrete type for the configured edition:

```python
# skillmeat/api/dependencies.py (excerpt)
from skillmeat.core.interfaces.repositories import IArtifactRepository

def get_artifact_repository(
    app_state: AppStateDep,
) -> IArtifactRepository:
    edition = app_state.edition
    if edition == "my-backend":
        from skillmeat.core.repositories.my_backend_artifact import (
            MyBackendArtifactRepository,
        )
        return MyBackendArtifactRepository(base_url=app_state.my_backend_url)
    # default: filesystem/SQLite
    from skillmeat.core.repositories import LocalArtifactRepository
    return LocalArtifactRepository(
        artifact_manager=app_state.artifact_manager,
        path_resolver=app_state.path_resolver,
    )
```

FastAPI routers consume repositories via the typed DI aliases defined at the bottom of `dependencies.py`:

```python
ArtifactRepoDep = Annotated[IArtifactRepository, Depends(get_artifact_repository)]
```

Routers declare the alias as a parameter type and FastAPI wires it automatically at request time.

## Interface Method Summary

### `IArtifactRepository`

| Method | Signature summary | Returns |
|--------|-------------------|---------|
| `get` | `(id)` | `ArtifactDTO | None` |
| `get_by_uuid` | `(uuid)` | `ArtifactDTO | None` |
| `list` | `(filters, offset, limit)` | `list[ArtifactDTO]` |
| `count` | `(filters)` | `int` |
| `search` | `(query, filters)` | `list[ArtifactDTO]` |
| `create` | `(dto)` | `ArtifactDTO` |
| `update` | `(id, updates)` | `ArtifactDTO` |
| `delete` | `(id)` | `bool` |
| `get_content` | `(id)` | `str` |
| `update_content` | `(id, content)` | `bool` |
| `get_tags` | `(id)` | `list[TagDTO]` |
| `set_tags` | `(id, tag_ids)` | `bool` |

### `IProjectRepository`

| Method | Signature summary | Returns |
|--------|-------------------|---------|
| `get` | `(id)` | `ProjectDTO | None` |
| `list` | `(filters)` | `list[ProjectDTO]` |
| `create` | `(dto)` | `ProjectDTO` |
| `update` | `(id, updates)` | `ProjectDTO` |
| `delete` | `(id)` | `bool` |
| `get_artifacts` | `(project_id)` | `list[ArtifactDTO]` |
| `refresh` | `(id)` | `ProjectDTO` |

### `ICollectionRepository`

| Method | Signature summary | Returns |
|--------|-------------------|---------|
| `get` | `()` | `CollectionDTO | None` |
| `get_by_id` | `(id)` | `CollectionDTO | None` |
| `list` | `()` | `list[CollectionDTO]` |
| `get_stats` | `()` | `dict[str, Any]` |
| `refresh` | `()` | `CollectionDTO` |
| `get_artifacts` | `(collection_id, filters, offset, limit)` | `list[ArtifactDTO]` |

### `IDeploymentRepository`

| Method | Signature summary | Returns |
|--------|-------------------|---------|
| `get` | `(id)` | `DeploymentDTO | None` |
| `list` | `(filters)` | `list[DeploymentDTO]` |
| `deploy` | `(artifact_id, project_id, options)` | `DeploymentDTO` |
| `undeploy` | `(id)` | `bool` |
| `get_status` | `(id)` | `str` |
| `get_by_artifact` | `(artifact_id)` | `list[DeploymentDTO]` |

### `ITagRepository`

| Method | Signature summary | Returns |
|--------|-------------------|---------|
| `get` | `(id)` | `TagDTO | None` |
| `get_by_slug` | `(slug)` | `TagDTO | None` |
| `list` | `(filters)` | `list[TagDTO]` |
| `create` | `(name, color)` | `TagDTO` |
| `update` | `(id, updates)` | `TagDTO` |
| `delete` | `(id)` | `bool` |
| `assign` | `(tag_id, artifact_id)` | `bool` |
| `unassign` | `(tag_id, artifact_id)` | `bool` |

### `ISettingsRepository`

| Method | Signature summary | Returns |
|--------|-------------------|---------|
| `get` | `()` | `SettingsDTO` |
| `update` | `(updates)` | `SettingsDTO` |
| `validate_github_token` | `(token)` | `bool` |

## Reference Implementation

The local (filesystem + SQLite) implementation lives in `skillmeat/core/repositories/`:

| Module | Interface |
|--------|-----------|
| `local_artifact.py` | `IArtifactRepository` |
| `local_project.py` | `IProjectRepository` |
| `local_collection.py` | `ICollectionRepository` |
| `local_deployment.py` | `IDeploymentRepository` |
| `local_tag.py` | `ITagRepository` |
| `local_settings_repo.py` | `ISettingsRepository` |

Each module delegates to the appropriate domain manager (`ArtifactManager`, `CollectionManager`, `DeploymentManager`, etc.) and uses `ProjectPathResolver` for collection and deploy-target path construction.

In-memory mock implementations (for unit tests) live in `tests/mocks/`:
- `tests/mocks/repositories.py` — drop-in stubs with configurable return values
- `tests/mocks/__init__.py` — convenience factory that assembles a mock `AppState` for tests
