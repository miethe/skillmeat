---
name: Enterprise Router Miswiring Pattern
description: API routers systematically use filesystem managers for reads in enterprise mode
type: gotcha
status: resolved
resolved_date: 2026-03-12
resolution_prd: PRD 2 (Enterprise Router Migration)
---

## Enterprise Router Miswiring Gotcha — RESOLVED

**What**: Routers throughout the API use `CollectionManagerDep` and `ArtifactManagerDep` for data-read operations. These managers only access the filesystem. In enterprise mode (PostgreSQL), all data lives in the DB, not the filesystem. This causes silent failures or empty results.

**Why it existed**: Before repository DI pattern was fully implemented (PRD 2), managers were the primary way to access collections/artifacts. Routers weren't systematically migrated to use `I*Repository` implementations when the DB layer was added.

## Resolution Summary

**Status**: RESOLVED via 4-phase migration (548 tests passing, 0 regressions)

**What was done**:
- **Phase 1**: Made `AppState` filesystem managers conditional on edition (enterprise mode skips initialization)
- **Phase 2**: Migrated P0 routers (artifacts, marketplace_sources, match) — READ operations now use repos
- **Phase 3**: Migrated P1/P2 routers (tags, user_collections, deployment_sets, deployments, health, mcp)
- **Phase 4**: Validated all changes (548 tests pass, all routers working in both local and enterprise modes)

## Final Router State

**Routers fully migrated to repository DI** (reads use repos, writes may use managers):
- `artifacts.py` — read operations use repos, writes use managers + cache refresh
- `marketplace_sources.py` — read operations use repos, writes use managers + cache refresh
- `match.py` — fully migrated to repo DI
- `tags.py` — fully migrated to repo DI
- `user_collections.py` — read operations use repos, writes use managers + cache refresh
- `deployment_sets.py` — fully migrated to repo DI
- `deployments.py` — read operations use repos, writes use managers + cache refresh
- `health.py` — fully migrated to repo DI

**Routers using managers for writes** (expected pattern, with edition checks):
- `artifacts.py` — Writes (publish, sync, update) use `ArtifactManagerDep`, `CollectionManagerDep`, `SyncManagerDep`; all operations guarded with `if app.edition == EditionMode.LOCAL`
- `marketplace_sources.py` — Write operations use `ArtifactManagerDep`, `CollectionManagerDep`; guarded with edition check
- `user_collections.py` — Write operations use `ArtifactManagerDep`, `CollectionManagerDep`; guarded with edition check
- `deployments.py` — Write operations use `CollectionManagerDep`; guarded with edition check
- `mcp.py` — Fully filesystem-native, uses `CollectionManagerDep` throughout; entire router gated with `@require_local_edition()` decorator

## Why This Is Correct

Write operations continue to use managers + cache refresh for several reasons:

1. **Filesystem mutation operations** (sync, publish, deploy) modify `.claude/` files and collection structure — no repo equivalent exists
2. **Cache invalidation** — After manager writes, `refresh_single_artifact_cache()` syncs changes to DB
3. **Enterprise edition safety** — All write operations are guarded with edition checks (`require_local_edition`, `if app.edition == EditionMode.LOCAL`), so enterprise instances cannot attempt filesystem writes
4. **MCP router isolation** — MCP operations are filesystem-only by design (workflow YAML discovery), so the entire router is local-only

## Pattern Now Standardized

```python
# READ: Use repository DI (works in both modes)
async def endpoint(artifact_repo: ArtifactRepoDep):
    artifacts = artifact_repo.find_by_collection(collection_id)

# WRITE: Use manager + cache refresh (guarded for enterprise)
async def endpoint(artifact_mgr: ArtifactManagerDep):
    if app.edition == EditionMode.ENTERPRISE:
        raise HTTPException(status_code=501, detail="Feature not available in enterprise")
    artifact_mgr.publish(...)
    await refresh_single_artifact_cache(...)
```

## Testing & Validation

- **548 tests passing** (0 regressions)
- All 9 migrated routers tested in both local and enterprise modes
- AppState manager initialization verified (local: managers available, enterprise: managers None)
- Edition checks prevent enterprise instances from calling filesystem-dependent code paths

**Previous audit**: `.claude/findings/ENTERPRISE_ROUTER_AUDIT.md` (detailed with line numbers and fixes)
