---
title: Enterprise Provider Routing Matrix
task: ENT2-001
audited: 2026-03-07
branch: feat/aaa-rbac-foundation
---

# Enterprise Provider Routing Matrix

Audit of all 10 hexagonal-architecture dependency providers in
`skillmeat/api/dependencies.py`. Each entry records what the provider returns
today (`local` edition), what enterprise implementation exists (if any) in
`skillmeat/cache/enterprise_repositories.py`, and whether it is wirable right
now or requires additional adapter work first.

---

## Legend

| Status | Meaning |
|--------|---------|
| `ready` | An enterprise repository class exists with full CRUD. A thin adapter satisfying the interface ABC is still required, but the underlying storage logic is implemented. |
| `stub` | Enterprise class exists but only partially implements the required interface (some abstract methods missing or signature mismatches with the ABC). |
| `unsupported` | No enterprise implementation exists. Provider must keep raising 503 for this edition. |

---

## Summary Table

| # | Provider function | Local class | Enterprise class | Status |
|---|-------------------|-------------|-----------------|--------|
| 1 | `get_artifact_repository` | `LocalArtifactRepository` | `EnterpriseArtifactRepository` | `stub` |
| 2 | `get_collection_repository` | `LocalCollectionRepository` | `EnterpriseCollectionRepository` | `stub` |
| 3 | `get_project_repository` | `LocalProjectRepository` | None | `unsupported` |
| 4 | `get_deployment_repository` | `LocalDeploymentRepository` | None | `unsupported` |
| 5 | `get_tag_repository` | `LocalTagRepository` | None | `unsupported` |
| 6 | `get_settings_repository` | `LocalSettingsRepository` | None | `unsupported` |
| 7 | `get_group_repository` | `LocalGroupRepository` | None | `unsupported` |
| 8 | `get_context_entity_repository` | `LocalContextEntityRepository` | None | `unsupported` |
| 9 | `get_marketplace_source_repository` | `LocalMarketplaceSourceRepository` | None | `unsupported` |
| 10 | `get_project_template_repository` | `LocalProjectTemplateRepository` | None | `unsupported` |

---

## Detailed Entries

### 1. `get_artifact_repository` → `IArtifactRepository`

**Local implementation**: `skillmeat/core/repositories/local_artifact.py::LocalArtifactRepository`

Constructor:
```python
LocalArtifactRepository(
    artifact_manager: ArtifactManager,
    path_resolver: ProjectPathResolver,
)
```

**Enterprise implementation**: `skillmeat/cache/enterprise_repositories.py::EnterpriseArtifactRepository`

Constructor:
```python
EnterpriseArtifactRepository(session: Session)
```

**Status: `stub`**

`EnterpriseArtifactRepository` has substantial storage logic implemented:
- `get(artifact_id: uuid.UUID)` — PK lookup with tenant assertion
- `get_by_uuid(artifact_uuid: str)` — UUID string lookup with tenant filter
- `get_by_name(name: str)` — name lookup within tenant
- `list(offset, limit, artifact_type, name_contains)` — paginated, with RBAC visibility filter
- `count(artifact_type)` — count with optional type filter
- `search_by_tags(tags, match_all)` — PostgreSQL JSONB GIN index tag search
- `get_content(artifact_id, version)` — version content retrieval
- `list_versions(artifact_id)` — version history
- `create(name, artifact_type, source, content, metadata, tags)` — creates row + optional v1.0.0 version
- `update(artifact_id, name, content, metadata, tags)` — field patch + auto-version on content change
- `soft_delete(artifact_id)` — sets `is_active=False`
- `hard_delete(artifact_id)` — removes artifact + version rows + collection membership rows

**Gap**: `EnterpriseArtifactRepository` does NOT subclass `IArtifactRepository`. Its method
signatures use `uuid.UUID` artifact IDs and return ORM objects (`EnterpriseArtifact`), while
`IArtifactRepository` expects string IDs (`"type:name"` format) and returns `ArtifactDTO`
frozen dataclasses. A DTO-mapping adapter class must be written before the provider can wire it.

**Required constructor arguments when wired**:
- `session: Session` — per-request SQLAlchemy session via `DbSessionDep`
- Tenant context is sourced from `TenantContext` ContextVar set by middleware (not a constructor argument)

---

### 2. `get_collection_repository` → `ICollectionRepository`

**Local implementation**: `skillmeat/core/repositories/local_collection.py::LocalCollectionRepository`

Constructor:
```python
LocalCollectionRepository(
    collection_manager: CollectionManager,
    path_resolver: ProjectPathResolver,
)
```

**Enterprise implementation**: `skillmeat/cache/enterprise_repositories.py::EnterpriseCollectionRepository`

Constructor:
```python
EnterpriseCollectionRepository(session: Session)
```

**Status: `stub`**

`EnterpriseCollectionRepository` implements:
- `create(name, description, metadata)` — creates row with tenant + owner_id
- `get(collection_id: uuid.UUID)` — PK lookup with tenant assertion
- `get_by_name(name: str)` — name lookup within tenant
- `list(offset, limit)` — paginated, alphabetically ordered
- `update(collection_id, name, description)` — field patch with owner check
- `delete(collection_id)` — removes collection + membership rows
- `add_artifact(collection_id, artifact_id, position)` — creates `EnterpriseCollectionArtifact` membership
- (remainder of membership methods continue beyond line 1750 of the file)

**Gap**: Same structural gap as artifact repository — `EnterpriseCollectionRepository` does NOT
subclass `ICollectionRepository`. IDs use `uuid.UUID`, returns are ORM objects not DTOs.
A DTO-mapping adapter must be written.

**Required constructor arguments when wired**:
- `session: Session` — per-request SQLAlchemy session via `DbSessionDep`

---

### 3. `get_project_repository` → `IProjectRepository`

**Local implementation**: `skillmeat/core/repositories/local_project.py::LocalProjectRepository`

Constructor:
```python
LocalProjectRepository(
    path_resolver: ProjectPathResolver,
    cache_manager: Optional[CacheManager],
)
```

**Enterprise implementation**: None — no class in `enterprise_repositories.py`

**Status: `unsupported`**

Projects map to local filesystem `.claude/` directories. In enterprise mode, project discovery
and path resolution would need to be database-backed, but no enterprise data model or repository
for projects has been designed. The `IProjectRepository` interface defines `list`, `get`,
`create`, `update`, `delete`, `list_artifacts`, and `get_stats` — none are implemented for
the enterprise tier.

---

### 4. `get_deployment_repository` → `IDeploymentRepository`

**Local implementation**: `skillmeat/core/repositories/local_deployment.py::LocalDeploymentRepository`

Constructor:
```python
LocalDeploymentRepository(
    deployment_manager: DeploymentManager,
    path_resolver: ProjectPathResolver,
)
```
Note: `DeploymentManager` is constructed inside the provider from `CollectionManager`.

**Enterprise implementation**: None

**Status: `unsupported`**

Deployments are intrinsically tied to local project filesystem paths. There is no enterprise
model for deployment tracking. The `IDeploymentRepository` interface exposes `list`, `get`,
`create`, `update`, `delete`, and `list_for_artifact` — none are implemented for enterprise.

---

### 5. `get_tag_repository` → `ITagRepository`

**Local implementation**: `skillmeat/core/repositories/local_tag.py::LocalTagRepository`

Constructor:
```python
LocalTagRepository()  # no arguments; manages its own SQLite session
```

**Enterprise implementation**: None

**Status: `unsupported`**

Tags in the enterprise schema are stored as JSONB arrays on `EnterpriseArtifact.tags` and
queried via `EnterpriseArtifactRepository.search_by_tags()`. There is no standalone
`ITagRepository`-compatible enterprise class. The `ITagRepository` interface defines
`list_all`, `get`, `create`, `update`, `delete`, `list_for_artifact`,
`add_to_artifact`, and `remove_from_artifact`.

---

### 6. `get_settings_repository` → `ISettingsRepository`

**Local implementation**: `skillmeat/core/repositories/local_settings_repo.py::LocalSettingsRepository`

Constructor:
```python
LocalSettingsRepository(
    path_resolver: ProjectPathResolver,
    config_manager: ConfigManager,
)
```

**Enterprise implementation**: None

**Status: `unsupported`**

Settings are stored in local config files managed by `ConfigManager`. No enterprise model
or tenant-scoped settings table exists. The `ISettingsRepository` interface defines
`get_user_settings`, `update_user_settings`, `get_entity_type_configs`,
`create_entity_type_config`, `update_entity_type_config`, `delete_entity_type_config`,
`get_entity_categories`, and `create_entity_category`.

---

### 7. `get_group_repository` → `IGroupRepository`

**Local implementation**: `skillmeat/core/repositories/local_group.py::LocalGroupRepository`

Constructor:
```python
LocalGroupRepository()  # no arguments; manages its own SQLite session
```

**Enterprise implementation**: None

**Status: `unsupported`**

Groups are a SQLite-backed tagging/classification layer. No enterprise group model exists.
The `IGroupRepository` interface defines `list`, `get`, `create`, `update`, `delete`,
`list_artifacts`, and membership mutation methods.

---

### 8. `get_context_entity_repository` → `IContextEntityRepository`

**Local implementation**: `skillmeat/core/repositories/local_context_entity.py::LocalContextEntityRepository`

Constructor:
```python
LocalContextEntityRepository()  # no arguments; manages its own SQLite session
```

**Enterprise implementation**: None

**Status: `unsupported`**

Context entities (CLAUDE.md entries, hooks, rules stored in the DB) have no enterprise
counterpart. The `IContextEntityRepository` interface is one of the larger ABCs, covering
full CRUD plus search, category management, and optional modular content assembly.

---

### 9. `get_marketplace_source_repository` → `IMarketplaceSourceRepository`

**Local implementation**: `skillmeat/core/repositories/local_marketplace_source.py::LocalMarketplaceSourceRepository`

Constructor:
```python
LocalMarketplaceSourceRepository()  # no arguments; manages its own SQLite session
```

**Enterprise implementation**: None

**Status: `unsupported`**

Marketplace sources are tracked in the local SQLite cache only. There is no enterprise
tenant-scoped marketplace source model. Note that `dependencies.py` also exposes a concrete
`MarketplaceSourceRepository` (from `cache/repositories.py`) via the separate
`get_marketplace_source_repository_concrete` provider; that path is not affected by the
hexagonal interface layer.

---

### 10. `get_project_template_repository` → `IProjectTemplateRepository`

**Local implementation**: `skillmeat/core/repositories/local_project_template.py::LocalProjectTemplateRepository`

Constructor:
```python
LocalProjectTemplateRepository()  # no arguments; manages its own SQLite session
```

**Enterprise implementation**: None

**Status: `unsupported`**

Project templates are stored locally. No enterprise model or repository implementation
exists. The `IProjectTemplateRepository` interface defines `list`, `get`, `create`,
`update`, and `delete`.

---

## Key Findings

### What exists for enterprise

Only two enterprise storage classes are implemented in `skillmeat/cache/enterprise_repositories.py`:

1. **`EnterpriseArtifactRepository`** — full CRUD, version history, JSONB tag search, tenant
   scoping, audit logging, RBAC visibility filtering. Comprehensive implementation but NOT
   wired to `IArtifactRepository` ABC.

2. **`EnterpriseCollectionRepository`** — full CRUD plus collection membership management.
   Also NOT wired to `ICollectionRepository` ABC.

Both classes inherit from `EnterpriseRepositoryBase[T]`, which provides:
- `TenantContext` ContextVar for request-scoped tenant isolation
- `_apply_tenant_filter(stmt)` — automatic `WHERE tenant_id = ?` injection
- `_assert_tenant_owns(obj)` — post-fetch ownership assertion
- `_log_operation(...)` — structured audit logging
- `_apply_auth_context(auth_context)` — sets `TenantContext` from `AuthContext.tenant_id`

### What `repository_factory.py` shows

`RepositoryFactory` only covers `IArtifactRepository` and `ICollectionRepository`.
Its `_build_enterprise_artifact_repository` and `_build_enterprise_collection_repository`
methods both raise `NotImplementedError` with a `# TODO (ENT-2.x)` comment, confirming
the adapter gap described above.

### The adapter gap

`EnterpriseArtifactRepository.get()` signature:
```python
def get(self, artifact_id: uuid.UUID, auth_context=None) -> Optional[EnterpriseArtifact]
```

`IArtifactRepository.get()` signature:
```python
def get(self, id: str, ctx=None, auth_context=None) -> ArtifactDTO | None
```

To wire providers 1 and 2, an adapter class (e.g. `EnterpriseArtifactRepositoryAdapter`)
must:
- Subclass `IArtifactRepository`
- Hold an `EnterpriseArtifactRepository` instance
- Translate `"type:name"` string IDs to UUID lookups
- Map `EnterpriseArtifact` ORM objects to `ArtifactDTO` frozen dataclasses

Providers 3–10 require both enterprise ORM models AND repository implementations to be
built from scratch before they can leave `unsupported` status.

---

## Files Referenced

| File | Role |
|------|------|
| `skillmeat/api/dependencies.py` | 10 provider functions audited (lines 494–758) |
| `skillmeat/api/config.py` | `APISettings.edition` field (default `"local"`, accepts `"enterprise"`) |
| `skillmeat/cache/enterprise_repositories.py` | `EnterpriseRepositoryBase`, `EnterpriseArtifactRepository`, `EnterpriseCollectionRepository` |
| `skillmeat/cache/repository_factory.py` | `RepositoryFactory` — routes by `SKILLMEAT_EDITION`; enterprise builders raise `NotImplementedError` |
| `skillmeat/core/interfaces/repositories.py` | 10 ABCs: `IArtifactRepository`, `ICollectionRepository`, `IProjectRepository`, `IDeploymentRepository`, `ITagRepository`, `ISettingsRepository`, `IGroupRepository`, `IContextEntityRepository`, `IMarketplaceSourceRepository`, `IProjectTemplateRepository` |
| `skillmeat/core/repositories/local_*.py` | 10 local filesystem implementations |
