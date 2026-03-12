# Enterprise Repo Parity v2 — Triage Classification

**Branch**: `refactor/enterprise-repo-parity`
**Produced**: Phase 1 triage — ENT2-1.1 through ENT2-1.5
**Architecture constraints**: SQLAlchemy 2.x `select()` style, `EnterpriseBase`, UUID PKs, `tenant_id UUID NOT NULL` on all tables, `_apply_tenant_filter()` on every query, edition routing via `APISettings.edition == "enterprise"`.

---

## Group A: DI-Routed Interfaces

All 8 interfaces route through `dependencies.py`. Currently all non-enterprise paths raise HTTP 503 with the message "Enterprise edition does not yet support \<name\>". The two already-implemented exceptions are `IArtifactRepository` and `ICollectionRepository` (covered by v1).

| Interface | Tier | Local FS Coupling | DI Status | Rationale | Schema Sketch (if Full) |
|-----------|------|-------------------|-----------|-----------|-------------------------|
| **ITagRepository** | **Full** | None — `LocalTagRepository` is 100% DB-backed (SQLite, no FS ops) | 503 stub | Tags are tenant-scoped labels; multi-tenant isolation is essential. The interface is pure DB reads/writes with no FS dependency, making the enterprise port a straight reimplementation against `EnterpriseTag`. | `enterprise_tags(id UUID PK, tenant_id UUID NOT NULL, name TEXT NOT NULL, slug TEXT NOT NULL, color TEXT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)`; `enterprise_artifact_tags(tag_id UUID FK, artifact_uuid UUID FK, tenant_id UUID NOT NULL)` |
| **IGroupRepository** | **Full** | None — `LocalGroupRepository` is 100% DB-backed (SQLite, `session.query()` throughout) | 503 stub | Groups organise artifacts within a collection per tenant; position ordering and artifact membership are inherently DB operations. Interface has no FS methods. | `enterprise_groups(id UUID PK, tenant_id UUID NOT NULL, name TEXT, collection_id UUID FK, description TEXT, position INT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)`; `enterprise_group_artifacts(group_id UUID FK, artifact_uuid UUID FK, tenant_id UUID NOT NULL, position INT)` |
| **ISettingsRepository** | **Full** | High — `LocalSettingsRepository` reads/writes `~/.skillmeat/config.toml` via `ConfigManager`. `get()` reads TOML on every call; `update()` writes TOML. `validate_github_token()` hits GitHub API. `list_entity_type_configs()` and category methods are DB-backed (SQLite). | 503 stub | Settings in enterprise mode must be per-tenant DB rows, not a per-user TOML file. The entity_type_config and category sub-tables are already DB-backed and transfer cleanly. The GitHub token field needs per-tenant storage. `validate_github_token` has no FS dependency and can be reused. | `enterprise_settings(id UUID PK, tenant_id UUID NOT NULL UNIQUE, github_token TEXT, collection_path TEXT, default_scope TEXT, edition TEXT, indexing_mode TEXT, extra JSONB, updated_at TIMESTAMPTZ)`; `enterprise_entity_type_configs(id UUID PK, tenant_id UUID NOT NULL, entity_type TEXT NOT NULL, display_name TEXT, description TEXT, icon TEXT, color TEXT, is_system BOOL)`; `enterprise_entity_categories(id UUID PK, tenant_id UUID NOT NULL, name TEXT NOT NULL, slug TEXT, entity_type TEXT, description TEXT, color TEXT, platform TEXT, sort_order INT)` |
| **IContextEntityRepository** | **Full** | Low — `LocalContextEntityRepository` stores context entities as `Artifact` rows in SQLite with type discriminators. The `deploy()` method writes to filesystem (`project_path`). All other methods (list, get, create, update, delete, get_content) are pure DB. | 503 stub | Context entities (CLAUDE.md, rules, specs, etc.) are meaningful multi-tenant objects. The `deploy()` method writes to a caller-supplied `project_path` on the local agent's filesystem — this remains valid in enterprise mode since the deploying agent has local disk access. The DB storage layer is the part that needs the enterprise port. | `enterprise_context_entities(id UUID PK, tenant_id UUID NOT NULL, name TEXT NOT NULL, entity_type TEXT NOT NULL, content TEXT, path_pattern TEXT NOT NULL, description TEXT, category TEXT, auto_load BOOL, version TEXT, target_platforms JSONB, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)`; `enterprise_entity_category_associations(entity_id UUID FK, category_id UUID FK, tenant_id UUID NOT NULL, position INT)` |
| **IProjectRepository** | **Full** (see OQ-1) | High — `LocalProjectRepository` is the most FS-coupled interface. It uses `_build_project_dto_from_path()` (directory scan, reads `.claude/` tracking files), `path_resolver`, and has `refresh()` that rescans FS. `get_artifacts()` reads deployed artifacts from disk. `get_by_path()` and `get_or_create_by_path()` accept raw filesystem paths. | 503 stub | Projects have genuine multi-tenant meaning (team shares a project, tracks deployments). DB columns for path, name, status can be stored without FS access. `get_artifacts()` and `refresh()` have unavoidable FS coupling; the enterprise impl can store project metadata in DB and treat FS operations as caller-driven side effects. See OQ-1 for path storage decision. | `enterprise_projects(id UUID PK, tenant_id UUID NOT NULL, name TEXT NOT NULL, path TEXT NOT NULL, status TEXT, description TEXT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)`; `enterprise_project_artifacts(project_id UUID FK, artifact_uuid UUID FK, tenant_id UUID NOT NULL, deployed_at TIMESTAMPTZ, content_hash TEXT, local_modifications BOOL)` |
| **IDeploymentRepository** | **Full** | High — `LocalDeploymentRepository` delegates entirely to `DeploymentManager`, which reads/writes TOML-based tracking files in project `.claude/` directories. There is no DB layer at all in the local impl. Methods like `deploy()`, `undeploy()`, `sync_deployment_cache()` all perform FS I/O. | 503 stub | Deployment tracking is a core multi-tenant concern (who deployed what artifact to which project). The enterprise impl stores deployment records in DB; actual file copy operations still happen on the agent's local FS and are triggered separately. `upsert_idp_deployment_set()` and `sync_deployment_cache()` are cache-sync helpers that map to pure DB upserts. | `enterprise_deployments(id UUID PK, tenant_id UUID NOT NULL, artifact_id TEXT NOT NULL, project_id UUID FK, status TEXT, deployed_at TIMESTAMPTZ, content_hash TEXT, deployment_profile_id UUID, local_modifications BOOL, platform TEXT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)` |
| **IMarketplaceSourceRepository** | **Full** | Low — `LocalMarketplaceSourceRepository` delegates to `MarketplaceSourceRepository` (concrete, SQLite-backed) and `MarketplaceCatalogRepository`. One `commit_source_session()` helper accesses the session directly. No direct FS I/O in this wrapper; all storage is SQLite. | 503 stub | Marketplace sources (GitHub repos registered for scanning) and their catalog entries are meaningful per-tenant data. The interface is broad (source CRUD + catalog CRUD + composite wiring) but all operations are DB-centric. The concrete `MarketplaceSourceRepository` already has tsvector search support that maps directly to PostgreSQL. | `enterprise_marketplace_sources(id UUID PK, tenant_id UUID NOT NULL, repo_url TEXT NOT NULL, owner TEXT, repo_name TEXT, ref TEXT, scan_status TEXT, artifact_count INT, last_sync_at TIMESTAMPTZ, ...)`; `enterprise_marketplace_catalog_entries(id UUID PK, tenant_id UUID NOT NULL, source_id UUID FK, artifact_type TEXT, name TEXT, path TEXT, upstream_url TEXT, status TEXT, confidence_score INT, detected_sha TEXT, search_vector TSVECTOR, ...)` |
| **IProjectTemplateRepository** | **Stub** | Low — `LocalProjectTemplateRepository` is SQLite DB-backed. The `deploy()` method writes files to a `project_path` on disk (similar to `IContextEntityRepository.deploy()`). All metadata ops are DB-only. | 503 stub | PRD proposed Stub; confirmed. Project templates are composite context entity bundles. In Phase 2, the priority is getting core data in (artifacts, collections, deployments, tags, groups). Templates depend on context entities being in enterprise DB first; deferring until context entities are done keeps scope manageable. Return empty list from `list()` and 404 from `get()` in enterprise mode for now. | N/A (deferred) |

---

## Group B: Non-DI Repositories

All Group B repos extend `BaseRepository` and **self-manage their SQLite session** via `db_path` constructor argument (defaults to `~/.skillmeat/cache/cache.db`). None accept an injected `Session`. They are instantiated directly in `dependencies.py` provider functions with no edition check.

| Class | Tier | Session Acquisition | Rationale | Schema Sketch (if Full) |
|-------|------|---------------------|-----------|-------------------------|
| **DeploymentSetRepository** | **Full** | Self-managed: `__init__(db_path=None)` → `BaseRepository.__init__` → `create_db_engine(self.db_path)`. New session per operation via `self._get_session()`. | DeploymentSets represent named groups of artifacts deployed together (IDP provisioning pattern). Multi-tenant environments need per-tenant set isolation. The `owner_id` scoping in the local impl maps directly to `tenant_id` in enterprise. Operations include complex tag filtering and owner-scoped queries — worth porting. | `enterprise_deployment_sets(id UUID PK, tenant_id UUID NOT NULL, name TEXT NOT NULL, remote_url TEXT, provisioned_by TEXT, description TEXT, tags_json TEXT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)`; `enterprise_deployment_set_members(set_id UUID FK, artifact_id TEXT, tenant_id UUID NOT NULL, position INT)` |
| **DeploymentProfileRepository** | **Full** | Self-managed: same `BaseRepository` pattern as above. | Deployment profiles (scope, destination path, overwrite rules) are per-tenant configuration that governs how artifacts are deployed. In multi-tenant mode each tenant needs isolated profile management. Interface is simple CRUD with no FS coupling. | `enterprise_deployment_profiles(id UUID PK, tenant_id UUID NOT NULL, name TEXT NOT NULL, scope TEXT, dest_path TEXT, overwrite BOOL, platform TEXT, metadata JSONB, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)` |
| **MarketplaceCatalogRepository** | **Passthrough** | Self-managed: same `BaseRepository` pattern. Session per operation. | The catalog repository contains discovered artifact listings from scanned GitHub repos — it's essentially read-heavy reference data. The concrete `MarketplaceSourceRepository` (Group A Full) already provides the enterprise path for catalog management via `IMarketplaceSourceRepository`. `MarketplaceCatalogRepository` is used in background scan jobs that run outside the request cycle; those jobs can continue using the local SQLite path or be migrated to use the enterprise source repo. No DI routing exists for this class; it's only used directly in scanner code. Reuse local impl or wrap. | N/A |
| **MarketplaceTransactionHandler** | **Full** | Self-managed: `__init__(db_path=None)` → `create_db_engine`. Creates sessions in `scan_update_transaction()` and `import_transaction()` context managers. | The handler provides ACID atomicity for two high-stakes operations: (1) scan completion (update source + replace catalog entries atomically) and (2) artifact import (mark entries as imported + create collection artifacts). In multi-tenant enterprise mode these atomic operations must be scoped to a tenant and use the enterprise DB connection. Downgrading to Passthrough would silently corrupt catalog state. The context-manager pattern (`ScanUpdateContext`, `ImportContext`) is portable; implementations just need to use `select()` style and accept an injected session. | Operates on `enterprise_marketplace_sources` and `enterprise_marketplace_catalog_entries` (see `IMarketplaceSourceRepository` schema above). No new tables needed; needs an enterprise-aware variant of the transaction handler that accepts an injected `Session` and applies tenant filters. |
| **DbCollectionArtifactRepository** | **Full** (was v1 — see OQ-2) | Self-managed in local path: `__init__` calls `BaseRepository` with default `db_path`. However `dependencies.py` `get_db_collection_artifact_repository()` always returns the local impl with no edition check — no enterprise path exists yet. | `DbCollectionArtifactRepository` implements `IDbCollectionArtifactRepository`, which is already used heavily by the user-collections router. The v1 work created `EnterpriseUserCollectionAdapter` for `IDbUserCollectionRepository` but left `IDbCollectionArtifactRepository` on the local SQLite path. Completing the enterprise port here is needed for full collection artifact management in enterprise mode. | Operates on `enterprise_collection_artifacts` (already defined in `models_enterprise.py` as `EnterpriseCollectionArtifact`). The enterprise impl needs to be wired into `get_db_collection_artifact_repository()` with edition routing. |
| **DbArtifactHistoryRepository** | **Stub** | Self-managed: reads from `artifacts` and `artifact_versions` SQLite tables. `get_db_artifact_history_repository()` in `dependencies.py` always returns local impl. | Artifact history (changelog timeline) is a read-only analytics feature. The enterprise `EnterpriseArtifactVersion` model exists in `models_enterprise.py` but the read-path for the timeline endpoint is low priority. Return empty list in enterprise mode for Phase 2; promote to Full in a later phase when the version history write path is also enterprise-enabled. | N/A (deferred) |
| **DuplicatePairRepository** | **Stub** | Self-managed: same `BaseRepository` pattern. `get_duplicate_pair_repository()` in `dependencies.py` always returns local impl. | Duplicate/similar artifact detection is a background analysis feature. Pairs are generated by a scanner job that runs against the collection. In enterprise mode the feature can safely return empty results (no pairs detected) without breaking any critical user workflow. Promote to Full when the duplicate scanner is adapted for multi-tenant operation. | N/A (deferred) |
| **MarketplaceSourceRepository** (concrete) | **Full** | Self-managed: same `BaseRepository` pattern. Used via both `get_marketplace_source_repository_concrete()` (direct) and wrapped by `LocalMarketplaceSourceRepository` for the DI interface path. | This is the concrete implementation that `LocalMarketplaceSourceRepository` delegates to. It must be ported along with `IMarketplaceSourceRepository` as they share the same data — the enterprise port of the interface inherently covers this class. Separating them is unnecessary; track as part of the `IMarketplaceSourceRepository` Full-tier work. | Same tables as `IMarketplaceSourceRepository` above. |

---

## Open Question Resolutions

### OQ-1: IProjectRepository filesystem paths

**Resolution**: Store filesystem path in the enterprise DB as a plain `TEXT` column (`path TEXT NOT NULL`). The enterprise `EnterpriseProject.path` column is informational — it records where the project *was* when registered. Methods like `get_by_path()` and `get_or_create_by_path()` perform DB lookups on the stored path string; they do not scan the filesystem themselves. The `refresh()` and `get_artifacts()` methods that require live FS access are explicitly marked as caller-invoked side effects: in enterprise mode `refresh()` re-reads the project's deployed artifact list from DB (populated by `sync_deployment_cache()` calls) rather than rescanning disk. The enterprise implementation does not scan the filesystem during normal API requests; FS operations remain in the CLI layer and are synced into DB via the existing write-through pattern.

**Path as ID**: The existing local impl uses a base64-encoded path as the project primary key. The enterprise impl uses a proper UUID PK with `path` as a unique indexed column per tenant. Callers that pass base64 path IDs are handled by a lookup helper that first tries UUID parse, then falls back to base64-decode + path lookup.

### OQ-2: DbCollectionArtifactRepository v1 status

**Resolution**: Not covered by v1. The v1 enterprise-db-storage work created `EnterpriseUserCollectionAdapter` for `IDbUserCollectionRepository` (user collection metadata: names, descriptions, membership counts) but left `IDbCollectionArtifactRepository` (the join table that links artifacts to collections, with search and pagination) on the local SQLite path. The `get_db_collection_artifact_repository()` provider in `dependencies.py` has no edition check and always returns `DbCollectionArtifactRepository()`. This must be addressed in Phase 2 as it is a critical path for the user-collections router. The `EnterpriseCollectionArtifact` model already exists in `models_enterprise.py` — the work is implementing the repository class and wiring the DI provider.

### OQ-3: MarketplaceTransactionHandler tier

**Resolution**: **Full**. The handler coordinates ACID cross-table writes between marketplace sources and catalog entries. Downgrading to Passthrough or Stub means scan jobs and import operations in enterprise mode would write to the local SQLite file instead of the tenant's PostgreSQL database, silently corrupting catalog state. The transaction pattern (context managers with commit/rollback) is clean and portable; the enterprise variant accepts an injected `Session` from the DI layer rather than self-managing a `db_path`-based engine. The `ScanUpdateContext` and `ImportContext` helper classes need enterprise-aware variants that use `select()` style and apply `_apply_tenant_filter()`.

### OQ-4: Group B repos already guarded

**Resolution**: None of the Group B repos have any edition checks in either their class bodies or their `dependencies.py` provider functions. All eight providers in `dependencies.py` instantiate the local SQLite-backed class unconditionally:

```python
def get_deployment_set_repository() -> DeploymentSetRepository:
    return DeploymentSetRepository()  # no edition check

def get_marketplace_transaction_handler() -> MarketplaceTransactionHandler:
    return MarketplaceTransactionHandler()  # no edition check
# ... same pattern for all others
```

This means enterprise-mode requests currently silently fall through to SQLite for all Group B repos. All Full-tier items need edition routing added to their provider functions in Phase 2.

---

## Phase 2 Scope Confirmation

Tables to be created in Phase 2 (all in PostgreSQL with `EnterpriseBase`, UUID PKs, `tenant_id UUID NOT NULL`):

**From Group A (Full-tier interfaces):**

- `enterprise_tags`
- `enterprise_artifact_tags` (join table)
- `enterprise_groups`
- `enterprise_group_artifacts` (join table)
- `enterprise_settings` (one row per tenant)
- `enterprise_entity_type_configs`
- `enterprise_entity_categories`
- `enterprise_entity_category_associations` (join table)
- `enterprise_context_entities`
- `enterprise_context_entity_category_associations` (join table)
- `enterprise_projects`
- `enterprise_project_artifacts` (join table)
- `enterprise_deployments`
- `enterprise_marketplace_sources`
- `enterprise_marketplace_catalog_entries`

**From Group B (Full-tier, new tables needed):**

- `enterprise_deployment_sets`
- `enterprise_deployment_set_members` (join table)
- `enterprise_deployment_set_tags` (join table, mirrors local `DeploymentSetTag`)
- `enterprise_deployment_profiles`

**From Group B (Full-tier, tables already exist):**

- `enterprise_collection_artifacts` — already defined as `EnterpriseCollectionArtifact` in `models_enterprise.py`; only DI wiring needed, no new migration

**DI provider changes needed in `dependencies.py`:**

- `get_tag_repository()` — add enterprise branch
- `get_group_repository()` — add enterprise branch
- `get_settings_repository()` — add enterprise branch
- `get_context_entity_repository()` — add enterprise branch
- `get_project_repository()` — add enterprise branch
- `get_deployment_repository()` — add enterprise branch
- `get_marketplace_source_repository()` — add enterprise branch
- `get_project_template_repository()` — enterprise returns Stub (empty list / 404)
- `get_deployment_set_repository()` — add edition routing
- `get_deployment_profile_repository()` — add edition routing
- `get_marketplace_transaction_handler()` — add edition routing
- `get_db_collection_artifact_repository()` — add enterprise branch (critical, v1 gap)

---

## Summary Statistics

| Tier | Group A count | Group B count | Total |
|------|--------------|--------------|-------|
| Full | 7 | 5 | 12 |
| Passthrough | 0 | 1 | 1 |
| Stub | 1 | 2 | 3 |
| Excluded | 0 | 0 | 0 |

**PRD tier proposals validated:** 14 of 16 match. Two adjustments:
1. `MarketplaceCatalogRepository` — PRD proposed Passthrough, confirmed **Passthrough** (matches).
2. `DbCollectionArtifactRepository` — PRD proposed Full, confirmed **Full** but noted it is a v1 gap (DI provider has no edition check), not a new item.
