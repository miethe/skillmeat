# Data Flow Patterns Reference

Detailed reference for SkillMeat's canonical data flow standard.
**Source**: `docs/project_plans/reports/data-flow-standardization-report.md`

---

## Write-Through Pattern (FS-Backed Data)

Web mutations on filesystem-backed data:

1. Write to **filesystem first** (source of truth)
2. Sync to DB cache via `refresh_single_artifact_cache()`
3. Invalidate TanStack Query caches on frontend

**Exception**: DB-native features (collections, groups, tags) write DB first, then write-back to FS where applicable (e.g., tag write-back to `collection.toml`).

**Key call sites** for `refresh_single_artifact_cache()` in `artifacts.py`:
- After artifact metadata update (`PUT /artifacts/{id}`)
- After deploy / undeploy
- After sync
- After import
- After file create/update/delete

---

## Cache Refresh Triggers

| Trigger | Scope | Mechanism |
|---------|-------|-----------|
| Server startup | Full | FS -> DB full sync in `lifespan()` |
| Single artifact mutation | Targeted | `refresh_single_artifact_cache()` |
| Manual refresh | Full | `POST /cache/refresh` endpoint |
| Frontend bulk operation | Full | `useCacheRefresh()` hook |

---

## Stale Times by Domain (Principle 5)

| Domain | Stale Time | Rationale |
|--------|-----------|-----------|
| Artifacts (list, infinite, detail) | 5 min | Standard browsing, cache-backed |
| Collections (all hooks) | 5 min | Standard browsing |
| Collection Artifacts | 5 min | Standard browsing |
| Tags (list/detail) | 5 min | Low-frequency changes |
| Tags (search) | 30 sec | Interactive, needs freshness |
| Groups (all hooks) | 5 min | Low-frequency changes |
| Deployments | 2 min | More dynamic, filesystem-backed |
| Projects | 5 min | Low-frequency changes |
| Marketplace listings | 1 min | External, moderately dynamic |
| Marketplace detail | 5 min | Slow-changing |
| Analytics summary | 30 sec | Monitoring dashboard |
| Analytics trends | 5 min | Aggregate, slow-changing |
| Context Entities | 5 min | Low-frequency changes |
| Artifact Search | 30 sec | Interactive search |
| Cache status | 30 sec | Monitoring |
| Context Sync status | 30 sec | Active sync monitoring |

**Rule**: Interactive/monitoring queries use 30sec. Standard browsing uses 5min. Deployments use 2min (FS-backed, more dynamic).

---

## Cache Invalidation Graph (Principle 6)

Mutations **must** invalidate all listed keys. Missing invalidations are non-compliant.

| Mutation | Must Invalidate |
|----------|----------------|
| Artifact CRUD | `['artifacts']`, `['collections']`, `['deployments']` |
| Artifact file create/update/delete | `['artifacts']` (metadata may change) |
| Tag CRUD | `['tags']`, `['artifacts']` (tags embed in artifact responses) |
| Tag add/remove from artifact | `['tags', 'artifact', artifactId]`, `['artifacts']` |
| Collection CRUD | `['collections']`, `['artifacts']` (collection membership) |
| Group CRUD | `['groups']`, `['artifact-groups']` |
| Group artifact add/remove/move | `['groups']`, `['artifact-groups']` |
| Deploy/Undeploy | `['deployments']`, `['artifacts']`, `['projects']` |
| Snapshot rollback | `['snapshots']`, `['artifacts']`, `['deployments']`, `['collections']` |
| Context entity deploy | `['context-entities']`, `['deployments']` |
| Context sync push/pull | `['context-sync-status']`, `['artifact-files']`, `['context-entities']`, `['deployments']` |
| Cache refresh | `['projects']`, `['cache']`, `['artifacts']` |

---

## Data Flow Diagrams

### Cache-First Read (Target State)

```
Frontend → API → DB Cache → Response
                    ↓ (miss)
              Filesystem → Upsert Cache → Response
```

### Write-Through (FS-Backed)

```
Frontend → API → Filesystem → refresh_single_artifact_cache() → DB Cache
Frontend ← invalidateQueries() ← Response
```

### DB-Native Write (Collections, Groups, Tags)

```
Frontend → API → Database → [optional FS write-back] → Response
Frontend ← invalidateQueries() ← Response
```
