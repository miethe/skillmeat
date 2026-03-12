# Enterprise Mode: Unsupported Repository 503 Errors

## Problem

When running SkillMeat in enterprise mode (`SKILLMEAT_EDITION=enterprise`), most API endpoints return HTTP 503 because the DI layer in `dependencies.py` only routes two repository types to enterprise implementations. The remaining eight raise `HTTPException(503)` with "Enterprise edition does not yet support X".

## Affected Repositories

| Repository Interface | Enterprise Status | DI Provider Function | Impact |
|---------------------|-------------------|---------------------|--------|
| `IArtifactRepository` | Supported | `get_artifact_repository` | Working |
| `ICollectionRepository` | Supported | `get_collection_repository` | Working |
| `IDbUserCollectionRepository` | Supported (adapter) | `get_db_user_collection_repository` | Working |
| `IProjectRepository` | **Not implemented** | `get_project_repository` | 503 |
| `IDeploymentRepository` | **Not implemented** | `get_deployment_repository` | 503 |
| `ITagRepository` | **Not implemented** | `get_tag_repository` | 503 |
| `ISettingsRepository` | **Not implemented** | `get_settings_repository` | 503 |
| `IGroupRepository` | **Not implemented** | `get_group_repository` | 503 |
| `IContextEntityRepository` | **Not implemented** | `get_context_entity_repository` | 503 |
| `IMarketplaceSourceRepository` | **Not implemented** | `get_marketplace_source_repository` | 503 |
| `IProjectTemplateRepository` | **Not implemented** | `get_project_template_repository` | 503 |

## Non-DI Repositories Also Affected

Several repositories in `dependencies.py` are instantiated directly without edition routing. They use SQLite-backed implementations unconditionally:

- `DeploymentSetRepository` — `get_deployment_set_repository()`
- `DeploymentProfileRepository` — `get_deployment_profile_repository()`
- `MarketplaceSourceRepository` (concrete) — `get_marketplace_source_repository_concrete()`
- `MarketplaceCatalogRepository` — `get_marketplace_catalog_repository()`
- `MarketplaceTransactionHandler` — `get_marketplace_transaction_handler()`
- `DuplicatePairRepository` — `get_duplicate_pair_repository()`
- `DbCollectionArtifactRepository` — `get_db_collection_artifact_repository()`
- `DbArtifactHistoryRepository` — `get_db_artifact_history_repository()`

These will silently use SQLite even in enterprise mode (PostgreSQL), causing data split or connection errors if no SQLite database exists in the container.

## Endpoint Impact Assessment

### Fully Working in Enterprise Mode
- `GET/POST /api/v1/artifacts` (artifact CRUD)
- `GET/POST /api/v1/user-collections` (collection CRUD)
- `GET /health` (health check)

### Broken (503) — Uses Unsupported DI Repositories
- `/api/v1/projects` — uses `ProjectRepoDep`
- `/api/v1/deployments` — uses `DeploymentRepoDep`
- `/api/v1/tags` — uses `TagRepoDep`
- `/api/v1/settings` — uses `SettingsRepoDep`
- `/api/v1/groups` — uses `GroupRepoDep`
- `/api/v1/context-entities` — uses `ContextEntityRepoDep`
- `/api/v1/marketplace-sources` — uses `MarketplaceSourceRepoDep`
- `/api/v1/project-templates` — uses `ProjectTemplateRepoDep`

### Silently Wrong — Hardcoded SQLite Repositories
- `/api/v1/deployment-sets` — `DeploymentSetRepository()` (SQLite)
- `/api/v1/deployment-profiles` — `DeploymentProfileRepository()` (SQLite)
- `/api/v1/marketplace-catalog` — `MarketplaceCatalogRepository()` (SQLite)
- `/api/v1/bundles` — may use hardcoded repos
- `/api/v1/artifact-history` — `DbArtifactHistoryRepository()` (SQLite)

## Recommendations

### Option A: Implement Missing Enterprise Repositories (Full Parity)

Create enterprise implementations for all 8 missing repository interfaces. Each would follow the same pattern as `EnterpriseArtifactRepository` and `EnterpriseCollectionRepository`:
- Accept injected `Session` from FastAPI DI
- Use SQLAlchemy 2.x `select()` style
- Automatic tenant filtering via `_apply_tenant_filter()`
- UUID primary keys

**Effort**: High (8 repositories, models, tests)
**Benefit**: Full feature parity in enterprise mode

### Option B: Stub Enterprise Repositories with No-Op/Empty Returns (MVP)

Create lightweight enterprise stubs that return empty results instead of 503. This unblocks the UI from crashing while the full implementations are built.

```python
# Example stub
class EnterpriseProjectRepository(EnterpriseRepositoryBase):
    def list(self, **kwargs): return []
    def get(self, id): return None
    # ... minimal interface satisfaction
```

**Effort**: Low-Medium (stubs + DI wiring)
**Benefit**: UI renders without 503 crashes; features gracefully degrade

### Option C: Enterprise-Aware Router Exclusion

Exclude unsupported routers entirely in enterprise mode during `server.py` startup. Only include routers that have enterprise-compatible dependencies.

```python
if edition != "enterprise":
    app.include_router(projects.router, ...)
    app.include_router(deployments.router, ...)
    # ... only include when supported
```

**Effort**: Low
**Benefit**: Clean 404 instead of misleading 503; OpenAPI spec reflects actual capabilities
**Drawback**: Frontend must handle missing endpoints

### Recommended Approach

**Phase 1 (immediate)**: Option C — exclude unsupported routers to stop 503 noise
**Phase 2 (next sprint)**: Option B — stub repositories for graceful degradation
**Phase 3 (planned)**: Option A — full enterprise implementations as needed

## Files Requiring Changes

| File | Change |
|------|--------|
| `skillmeat/api/server.py` | Edition-conditional router registration |
| `skillmeat/api/dependencies.py` | New enterprise DI providers (Phase 2/3) |
| `skillmeat/cache/enterprise_repositories.py` | New repository classes (Phase 3) |
| `skillmeat/cache/models_enterprise.py` | New enterprise models if needed (Phase 3) |

## Related Context

- Branch: `fix/enterprise-repo-fixes`
- Recent commits addressing enterprise repo issues:
  - `8ac40fc0` fix(api): expand tilde in sentinel project paths
  - `b2b50870` fix(enterprise): implement missing IDbUserCollectionRepository methods
  - `dd64cac3` fix(enterprise): add IDbUserCollectionRepository inheritance
  - `80b76eb1` fix(enterprise): add edition-aware DI for user collection repository
- Existing diagnosis: `.claude/findings/ALL_COLLECTIONS_404_DIAGNOSIS.md`
