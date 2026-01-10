# Sync + Collections Regression Analysis (2026-01-09)

## Scope

- Reviewed Sync Status tab behavior, diff viewer integrations, and artifact sync flows.
- Traced project deployment linking, multi-collection flows, and groups APIs.
- Checked data layer and deployment metadata formats for drift and sync logic.

## Findings

### 1. Deployment metadata schema mismatch breaks drift detection and sync status

- `skillmeat/core/sync.py` reads `.skillmeat-deployed.toml` using a `[deployment]` + `[[artifacts]]` schema in `_load_deployment_metadata`.
- `skillmeat/storage/deployment.py` writes `.skillmeat-deployed.toml` using a `deployed = [...]` list with a different shape in `DeploymentTracker.write_deployments`.
- `SyncManager.check_drift()` (used by `/artifacts?check_drift=true`) silently yields no drift info when the file format does not match, which collapses `drift_status` + local modification detection and can make Sync Status appear “synced” even when changes exist.

### 2. Cache migrations are not executed at runtime, leaving collections/groups tables missing on existing DBs

- `skillmeat/cache/manager.py` only calls `create_tables()` and never runs Alembic migrations.
- New tables (`collections`, `groups`, `group_artifacts`) and constraints are created via migrations in `skillmeat/cache/migrations/versions/20251212_1600_create_collections_schema.py` but are not applied to existing databases.
- Group endpoints in `skillmeat/api/routers/groups.py` assume those tables exist and will fail on older cache DBs, which matches “groups are completely non-functional.”

### 3. Collection identity is inconsistent across API layers and UI, breaking multi-collection behavior

- UI collection context uses database-backed `user-collections` (UUID `collection_id`). Artifact APIs still use file-based collection *names* from `CollectionManager`.
- The core entity mapping hard-codes `collection: 'default'` for collection-mode entities (`skillmeat/web/hooks/useEntityLifecycle.tsx`), which causes upstream-diff and sync queries to target the default collection regardless of the selected user collection.
- `DeployFromCollectionDialog` also hard-codes `collection: 'default'` and fetches from `/artifacts` without the selected collection context (`skillmeat/web/app/projects/[id]/manage/components/deploy-from-collection-dialog.tsx`).
- Result: Sync Status tab, upstream diff, and deployment actions can point at the wrong collection, so multi-collection is only partially functional.

### 4. Artifact linking to project deployments is name-only and ignores type/collection

- Project detail view matches deployed artifacts to collection artifacts using name-only lookup: `artifactsData?.artifacts.find(artifact => artifact.name === deployedArtifact.artifact_name)` in `skillmeat/web/app/projects/[id]/page.tsx`.
- This fails when multiple types share a name or when artifacts exist in multiple collections, leading to incorrect linking and partial deployment sync behavior.
- Collection page enrichment also matches by name only (`enrichArtifactSummary` in `skillmeat/web/app/collection/page.tsx`), causing incorrect metadata when names collide across types.

### 5. Deployment tracking does not support MCP/Hook artifact types

- `DeploymentTracker.record_deployment` and `DeploymentManager.deploy_artifacts` only handle `skill`, `command`, `agent` (`skillmeat/storage/deployment.py`, `skillmeat/core/deployment.py`).
- `ArtifactType` now includes `mcp` and `hook` (`skillmeat/core/artifact_detection.py`), but these types are not deployed or tracked, so diff/sync/linking for MCP/Hook artifacts is effectively broken.

### 6. Context sync service is largely stubbed, so context entity sync is misleading

- `ContextSyncService` uses deployment hashes as both collection and baseline hashes and has TODOs for actual collection updates and conflict resolution (`skillmeat/core/services/context_sync.py`).
- `ContextSyncStatus` in the UI relies on `/context-sync/status` and will report “no changes” unless deployment hashes differ, but collection-side changes are never detected or applied.

### 7. User-collection artifact summaries depend on cache entries that may not exist

- `get_artifact_metadata()` in `skillmeat/api/services/artifact_metadata_service.py` only looks in the cache DB or marketplace catalog. It does not consult the file-based collection store.
- If the cache DB is not populated for local artifacts, collection/group listings degrade to `type="unknown"` with `name=artifact_id`, which breaks grouping and collection views.

## Recommendations

### A. Unify deployment metadata format

- Pick one `.skillmeat-deployed.toml` schema and update both `SyncManager` and `DeploymentTracker` to read/write the same structure.
- Add a migration/compat shim that detects old schema and converts to the new one on read.

### B. Run cache migrations at startup

- Replace `create_tables()` in `CacheManager.initialize_cache()` with `run_migrations()` for existing DBs, keeping `create_tables()` only for fresh databases.
- Add a health check that verifies the presence of `collections` and `groups` tables on startup and logs a clear warning if missing.

### C. Wire collection IDs to artifact APIs

- Introduce a mapping between `user-collections` (DB id) and file-based collection names, or standardize on one source of truth.
- Update `mapApiArtifactToEntity`, Sync Status tab queries, and project dialogs to use the selected collection context instead of `default`.
- Add optional `collection_id` support to `/artifacts` endpoints (or a bridging endpoint) so UI can filter correctly.

### D. Fix artifact-to-deployment linking

- Match on `(artifact_type, artifact_name)` instead of name-only.
- When multiple collections contain the same artifact, include `from_collection` in the matching logic to avoid incorrect associations.

### E. Add MCP/Hook deployment support

- Extend deployment paths in `DeploymentManager` and `DeploymentTracker` for MCP/Hook so sync/diff can work for those types.
- Confirm `ArtifactType` normalization (mcp vs mcp_server) is consistent at API boundaries.

### F. Complete context sync implementation or clearly flag as preview

- Either implement collection reads/writes in `ContextSyncService` or hide/flag the Sync Status UI for context entities until it is functional.

### G. Populate cache artifact metadata for user-collections

- Add a background job or explicit API to sync file-based collection artifacts into the cache DB so `get_artifact_metadata()` can return real data.
- Alternatively, add a fallback lookup via `CollectionManager` for local artifacts.
