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

---

## Architecture Review

**Sign-off status**: Approved with Changes

**Reviewer**: backend-architect (ENT2-1.6)

**Review date**: 2026-03-12

---

### Invariant Compliance Assessment

All tier assignments were evaluated against the six architecture invariants defined in the triage header.

#### SQLAlchemy 2.x `select()` style

Confirmed correct for all Full-tier items. The existing `EnterpriseRepositoryBase` in `enterprise_repositories.py` enforces 2.x style through its `_apply_tenant_filter()` / `_tenant_select()` / `_apply_tenant_filter()` base methods, which all receive and return SQLAlchemy 2.x `Select` objects. Every new enterprise repository class must extend `EnterpriseRepositoryBase[T]` and use only `select(Model)` — never `session.query()`.

One specific risk identified: `IGroupRepository`'s rationale notes that `LocalGroupRepository` uses `session.query()` throughout. The enterprise port must not carry this pattern forward. Implementors must rewrite all queries in the 2.x `select()` style when porting — this is already noted in the `cache/CLAUDE.md` invariant but worth flagging explicitly here since `IGroupRepository` is the interface most likely to be ported by copying from the local implementation.

#### `EnterpriseBase` declarative base

All schema sketches are validated as requiring `EnterpriseBase` (from `models_enterprise.py`). The existing seven enterprise models (`EnterpriseArtifact`, `EnterpriseArtifactVersion`, `EnterpriseCollection`, `EnterpriseCollectionArtifact`, `EnterpriseUser`, `EnterpriseTeam`, `EnterpriseTeamMember`) all extend `EnterpriseBase`. The `EnterpriseCollectionArtifact` model referenced under `DbCollectionArtifactRepository` (Group B, Full) already exists and already extends `EnterpriseBase` — this is correct and no model change is needed for that item.

No schema sketch in the triage proposes using `Base` from `models.py`. Assessment: clean.

#### UUID primary keys on all enterprise models

All Full-tier schema sketches specify `id UUID PK DEFAULT gen_random_uuid()`. The existing models confirm UUID PKs as the pattern (`EnterpriseArtifact.id`, `EnterpriseCollection.id`, etc., all using `UUID(as_uuid=True)` with `default=uuid.uuid4`).

One precision concern: the schema sketches use PostgreSQL DDL notation `DEFAULT gen_random_uuid()`. In the SQLAlchemy ORM the correct Python-side equivalent is `server_default=text("gen_random_uuid()")` or `default=uuid.uuid4` (client-side). The existing models use `default=uuid.uuid4` (client-side generation). Implementation must be consistent with the existing pattern — use `default=uuid.uuid4` on the Python column definition. Do not mix `server_default=text("gen_random_uuid()")` with `default=uuid.uuid4` on the same column.

#### `tenant_id UUID NOT NULL` on every new table

All Full-tier schema sketches include `tenant_id UUID NOT NULL`. The join tables (`enterprise_artifact_tags`, `enterprise_group_artifacts`, `enterprise_entity_category_associations`, `enterprise_project_artifacts`, `enterprise_deployment_set_members`) all carry `tenant_id` — this is correct and consistent with `EnterpriseCollectionArtifact` which already has `tenant_id` on the join table. Do not omit `tenant_id` from join tables under the assumption that the parent row provides coverage — tenant filtering on joins must be applied independently per table.

One index gap: the sketches do not explicitly call out indexes. Every new table must have at minimum:
- `Index("ix_<table>_tenant_id", "<table>.tenant_id")`
- Unique constraints where noted (e.g., `enterprise_settings` is one-row-per-tenant, needs `UNIQUE(tenant_id)`)
- Join tables need a composite `UNIQUE(parent_id, child_id, tenant_id)` or at minimum a `UNIQUE(parent_id, child_id)` with tenant enforced through filter (existing `EnterpriseCollectionArtifact` uses `UniqueConstraint("collection_id", "artifact_uuid", "tenant_id")` — match this pattern for all new join tables)

#### `_apply_tenant_filter()` on every query

The `EnterpriseRepositoryBase._apply_tenant_filter()` method is already provided and documented. All new repository implementations must call it via `self._apply_tenant_filter(stmt)` or the `self._tenant_select()` shorthand on every `select()`. This is the highest-risk area for implementation errors. The `MarketplaceTransactionHandler` enterprise variant (OQ-3) is a particular watch point because it uses context managers (`ScanUpdateContext`, `ImportContext`) that build their own queries — each internal query inside those contexts must also apply tenant filtering.

#### Edition routing via `APISettings.edition == "enterprise"`

The DI pattern in `dependencies.py` is confirmed correct. The two already-wired providers (`get_artifact_repository`, `get_collection_repository`) check `edition == "enterprise"` before returning the enterprise implementation. The `get_db_user_collection_repository` provider uses the same pattern and also correctly checks `edition == "enterprise"`. The `get_membership_repository` provider uses the alternative pattern (checking `auth_context.tenant_id` rather than `edition` string) — this is intentional for that provider and is not a defect.

All twelve providers listed in the Phase 2 scope must add the `edition == "enterprise"` branch. The three Stub items (`IProjectTemplateRepository`, `DbArtifactHistoryRepository`, `DuplicatePairRepository`) must return an appropriate empty-result stub class (not raise 503) so that callers in enterprise mode get empty lists rather than errors. The current 503 pattern for Group A unimplemented repos is correct for the period before Phase 2 but must be replaced on delivery.

---

### Classification Changes

#### No reclassifications required.

All 16 tier assignments are validated as correct. No Full items can be safely downgraded to Stub based on current information.

One note on `MarketplaceCatalogRepository` (Passthrough): the Passthrough tier is correct for now, but Phase 2 implementors should be aware that the enterprise `IMarketplaceSourceRepository` Full implementation will write to `enterprise_marketplace_catalog_entries`. If the `MarketplaceCatalogRepository` Passthrough path continues reading from the local SQLite `marketplace_catalog_entries` table in enterprise mode, catalog reads (e.g., search) will silently miss any records written through the enterprise path. This does not change the tier assignment for Phase 2, but it must be tracked as a known inconsistency and addressed in Phase 3 when the marketplace scanner is adapted for multi-tenant operation.

---

### IProjectRepository Filesystem Decision (OQ-1) — Confirmation

The OQ-1 resolution is architecturally sound. Storing `path TEXT NOT NULL` as an informational column is the correct approach. The critical design constraint is:

**The enterprise `IProjectRepository` implementation must never initiate filesystem scans from within repository methods.** The path column is a record of registration, not a trigger for FS I/O.

The proposed UUID-primary-key design with `path` as a unique indexed column per tenant is correct and avoids the fragility of the local base64-encoded path PK. The fallback lookup helper (UUID parse → base64-decode + path lookup) is required for backward compatibility with existing callers that pass base64 path IDs via the API. This lookup helper must be implemented as a helper on the enterprise repository class, not in the router layer.

The `refresh()` method behavior in enterprise mode (re-reads from DB rather than rescanning disk) must be clearly documented in the enterprise implementation class — the interface contract says "refresh project data" which is ambiguous between FS rescan and DB reread. Add an explicit docstring override noting the enterprise semantics.

One gap in the schema sketch: the `enterprise_projects` table is missing a `UNIQUE(tenant_id, path)` constraint. The path must be unique per tenant (two tenants can register the same filesystem path; a single tenant cannot register the same path twice). The migration must include `UniqueConstraint("tenant_id", "path", name="uq_enterprise_projects_tenant_path")`.

---

### Schema Design Concerns

#### `enterprise_settings` — UNIQUE constraint required

The table is documented as "one row per tenant" but the schema sketch only states `tenant_id UUID NOT NULL UNIQUE`. Confirm that the Alembic migration includes `UniqueConstraint("tenant_id", name="uq_enterprise_settings_tenant")`. This constraint prevents accidental double-insert on tenant provisioning.

The `extra JSONB` column is appropriate for forward-compatible extension but should have a `server_default=text("'{}'::jsonb")` to avoid null-check burden in application code. Existing models (`EnterpriseArtifact.extra_data`) set a `server_default` on JSONB columns — follow the same pattern.

#### `enterprise_deployments` — `artifact_id` type concern

The schema sketch uses `artifact_id TEXT NOT NULL` for the deployment record. This matches the existing `sync_deployment_cache()` interface which takes `artifact_id: str` in `"type:name"` format. However, `enterprise_artifacts.id` is a UUID PK in the enterprise model. In enterprise mode the deployment record should reference `enterprise_artifacts.id` (UUID FK) rather than a text-format artifact identifier. The text `artifact_id` would be appropriate only as a transitional field or a denormalized cache. Recommend adding `artifact_uuid UUID` as the primary FK alongside the `artifact_id TEXT` field (or replacing it) during implementation. This is a **Phase 2 implementation decision** that must be resolved before the migration is written — it is not a blocker for tier classification but is a blocker for the migration DDL.

#### `enterprise_context_entities` — join table naming inconsistency

The Phase 2 scope lists both `enterprise_entity_category_associations` (from `ISettingsRepository`) and `enterprise_context_entity_category_associations` (from `IContextEntityRepository`). These are two distinct join tables with different semantics:
- `enterprise_entity_category_associations`: links `entity_type_configs` to `entity_categories` (settings domain)
- `enterprise_context_entity_category_associations`: links `context_entities` to `entity_categories` (context entity domain)

This is correct — they should remain separate tables. The naming is sufficiently distinct. No change required, but the migration author must create both and not conflate them.

#### `enterprise_deployment_set_tags` — missing from schema sketches

The Phase 2 scope table lists `enterprise_deployment_set_tags` as a new table, but no schema sketch is provided in the Group B `DeploymentSetRepository` entry. The local `DeploymentSetTag` model maps string tags to deployment sets. The enterprise table should follow the join-table pattern: `enterprise_deployment_set_tags(set_id UUID FK, tag TEXT NOT NULL, tenant_id UUID NOT NULL)` with `UNIQUE(set_id, tag)`. This table must be added to the migration.

#### `MarketplaceTransactionHandler` — no new tables needed

OQ-3 confirms Full tier with a note that no new tables are needed (operates on `enterprise_marketplace_sources` and `enterprise_marketplace_catalog_entries`). This is correct. The enterprise transaction handler is purely an orchestration class that accepts an injected `Session` — it is not an `EnterpriseRepositoryBase` subclass since it manages multi-table operations. It must still apply `tenant_id` filters on every query it issues, even though it does not inherit the base's `_apply_tenant_filter()` helper. The implementation should accept `tenant_id: uuid.UUID` as a constructor parameter and apply it explicitly.

---

### Phase 2 Scope — Confirmed with Amendments

The scope as listed is confirmed correct with the following amendments:

1. **Add** `enterprise_deployment_set_tags` to the "new tables" list (was in the scope table but missing a schema sketch).

2. **Add** `UNIQUE(tenant_id, path)` constraint requirement to `enterprise_projects`.

3. **Resolve** `enterprise_deployments.artifact_id` type (TEXT vs UUID FK) before writing the migration. Recommend adding `artifact_uuid UUID REFERENCES enterprise_artifacts(id)` with a separate `artifact_id TEXT` kept for backward compatibility during transition.

4. **Note** that `get_project_repository()` in `dependencies.py` does not yet accept a `Session` parameter (unlike the artifact and collection providers). Adding an enterprise branch requires adding `session: Annotated[Session, Depends(get_db_session)]` to its signature — a one-line provider signature change required before the enterprise implementation can be wired.

5. **Note** that all three Stub providers (`get_project_template_repository`, `get_db_artifact_history_repository`, `get_duplicate_pair_repository`) currently either raise 503 or return the local SQLite-backed class with no edition check. Phase 2 must replace these with proper Stub implementations that return empty results in enterprise mode rather than routing to SQLite.

6. **Confirmed**: `DbCollectionArtifactRepository` is a v1 gap — the `get_db_collection_artifact_repository()` provider has no edition check and no `session` parameter. Wiring this is critical-path for the user-collections router in enterprise mode and must be treated as a P0 item within Phase 2.

No items should be removed from scope. The 15 new tables, 4 tables-already-exist items, and 12 DI provider changes are all confirmed necessary.
