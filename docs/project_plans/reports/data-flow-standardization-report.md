---
title: "Architecture Report: Data Flow Standardization — Frontend <-> Backend <-> Storage"
description: "Comprehensive audit and standardization strategy for how the SkillMeat frontend fetches data and saves updates, establishing the canonical pattern for all data domains"
audience: [developers, architects, ai-agents, product]
tags: [architecture, data-flow, caching, frontend, backend, standardization, report]
created: 2026-02-04
updated: 2026-02-04
category: "reports"
status: approved
complexity: High
related:
  - /docs/project_plans/reports/dual-collection-system-architecture-analysis.md
  - /docs/project_plans/reports/manage-collection-page-architecture-analysis.md
  - /docs/project_plans/implementation_plans/refactors/tag-storage-consolidation-v1.md
  - /docs/project_plans/implementation_plans/refactors/tag-management-architecture-fix-v1.md
  - /docs/project_plans/implementation_plans/refactors/artifact-metadata-cache-v1.md
  - /docs/project_plans/implementation_plans/refactors/collections-api-consolidation-v1.md
  - /docs/project_plans/implementation_plans/refactors/refresh-metadata-extraction-v1.md
---

# Architecture Report: Data Flow Standardization

**Date**: 2026-02-04
**Author**: Claude Opus 4.5 (AI-generated)
**Scope**: Full-stack data flow audit across all SkillMeat data domains
**Status**: Approved -- establishes canonical patterns going forward

---

## 1. Executive Summary

SkillMeat operates a dual-stack architecture: **filesystem** (CLI-first, offline-capable) plus **database cache** (web-first, performant). After multiple refactors -- collections API consolidation, artifact metadata caching, tag storage consolidation, and tag management fixes -- the system has converged on a clear architectural pattern but still has measurable inconsistencies across data domains.

### Key Findings

| Metric | Value |
|--------|-------|
| Data domains audited | 12 |
| Unique frontend hooks audited | 47 |
| Fully compliant domains | 4 (Collections, Groups, Context Entities, Auto-Tags) |
| Partially compliant domains | 5 (Artifacts, Tags, Deployments, Projects, Snapshots) |
| Non-compliant domains | 3 (File operations, Sync, Marketplace catalog) |
| Inconsistencies identified | 14 |
| Critical severity | 1 |
| High severity | 4 |
| Medium severity | 6 |
| Low severity | 3 |

### What This Report Delivers

1. **Canonical data flow principles** -- six principles that all current and future data domains must follow
2. **Complete domain-by-domain audit** -- every hook, endpoint, data source, and cache invalidation mapped
3. **14 specific inconsistencies** with severity ratings and fix approaches
4. **Three-phase remediation plan** with effort estimates

---

## 2. Architectural Principles (The Standard)

The following six principles constitute the canonical data flow standard for SkillMeat. All domains must comply.

### Principle 1: DB Cache is the Web's Source of Truth

The frontend **always** reads from API endpoints backed by the database cache for browsable, listable data. The frontend **never** reads directly from filesystem-backed endpoints for data that should be cached.

**Exception**: Individual file content viewing (reading a single `SKILL.md` file, for example) may go directly to the filesystem, as file content is not cached in the database.

**Rationale**: The DB cache provides consistent pagination, filtering, and performance. Filesystem reads are slower, lack pagination support, and create inconsistencies when cache and filesystem diverge.

### Principle 2: Filesystem is the CLI's Source of Truth

`collection.toml` and artifact files on disk are the durable source of truth for the CLI. The CLI reads and writes the filesystem directly, never through the DB. The DB cache is a **derived view** of filesystem state.

**Rationale**: Offline-first design for CLI users. The filesystem is always available; the database server may not be running.

### Principle 3: Write-Through Pattern for Web Mutations

Web mutations on filesystem-backed data follow the write-through pattern:

1. Write to **filesystem first** (source of truth)
2. **Sync** the change to DB cache via `refresh_single_artifact_cache()`
3. **Invalidate** relevant TanStack Query caches on the frontend

**Exception**: DB-native features (user collections, groups, tags) that have no filesystem equivalent write to DB first, then write-back to filesystem where applicable (e.g., tag write-back to `collection.toml`).

### Principle 4: Cache Refresh is the Sync Mechanism

| Trigger | Scope | Mechanism |
|---------|-------|-----------|
| Server startup | Full | FS -> DB full sync in `lifespan()` |
| Single artifact mutation | Targeted | `refresh_single_artifact_cache()` |
| Manual refresh | Full | `POST /cache/refresh` endpoint |
| Frontend bulk operation | Full | `useCacheRefresh()` hook |

### Principle 5: TanStack Query Stale Times Must Be Consistent by Domain

| Domain | Stale Time | Rationale |
|--------|-----------|-----------|
| Artifacts (list via `useArtifacts`) | **5 min** | Standard browsing, cache-backed |
| Artifacts (infinite via `useInfiniteArtifacts`) | 5 min | Same as list |
| Artifacts (detail via `useArtifact`) | 5 min | Same as list |
| Collections (all hooks) | 5 min | Standard browsing |
| Collection Artifacts | 5 min | Standard browsing |
| Tags (list/detail) | 5 min | Low-frequency changes |
| Tags (search) | 30 sec | Interactive, needs freshness |
| Groups (all hooks) | 5 min | Low-frequency changes |
| Deployments | 2 min | More dynamic, filesystem-backed |
| Projects | 5 min | Low-frequency changes |
| Marketplace listings | 1 min | External, moderately dynamic |
| Marketplace detail | 5 min | Slow-changing |
| Analytics summary | 30 sec | Monitoring dashboard, needs freshness |
| Analytics trends | 5 min | Aggregate, slow-changing |
| Context Entities | 5 min | Low-frequency changes |
| Artifact Search | 30 sec | Interactive search |
| Cache status | 30 sec | Monitoring |
| Context Sync status | 30 sec | Active sync monitoring |

### Principle 6: Mutations Always Invalidate Related Caches

The following table defines the mandatory cache invalidation graph. Mutations that fail to invalidate all listed keys are non-compliant.

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

## 3. Current State Audit: Data Flow by Domain

### 3.1 Artifacts Domain

**Key files**:
- Frontend hooks: `skillmeat/web/hooks/useArtifacts.ts`
- Frontend API: `skillmeat/web/lib/api/artifacts.ts`
- Backend router: `skillmeat/api/routers/artifacts.py`

#### Read Operations

| Operation | Frontend Hook | API Endpoint | Backend Source | Stale Time | Compliant? |
|-----------|--------------|-------------|---------------|-----------|------------|
| List all (paginated) | `useArtifacts()` | `GET /artifacts` | `ArtifactManager.list_artifacts()` (filesystem via `collection_mgr`) | 30 sec | **NO** -- stale time is 30sec, standard is 5min |
| List all (infinite scroll) | `useInfiniteArtifacts()` | `GET /artifacts` | Same filesystem path | 5 min | PARTIAL -- same FS source |
| Get detail | `useArtifact()` | `GET /artifacts/{id}` | `ArtifactManager.show()` (filesystem) | none (default) | **NO** -- reads from FS, not DB cache; no stale time set |
| Search artifacts | `useArtifactSearch()` | `GET /marketplace/catalog/search` | FTS5 DB (marketplace catalog) | 30 sec | YES -- search is DB-backed |

**Analysis**: The `GET /artifacts` list endpoint (line 1680 in `artifacts.py`) iterates over filesystem collections via `artifact_mgr.list_artifacts()`, calling `CollectionManager` for each collection name. It does **not** read from the `CollectionArtifact` DB cache table. The `GET /artifacts/{id}` detail endpoint (line 1993) similarly uses `artifact_mgr.show()` which reads directly from filesystem.

This is the single largest data flow inconsistency. Both endpoints should read from `CollectionArtifact` DB cache with filesystem fallback.

#### Write Operations

| Operation | Frontend Hook | API Endpoint | Write Target | Cache Sync | Cache Invalidation | Compliant? |
|-----------|--------------|-------------|-------------|-----------|-------------------|------------|
| Import/Install | `useInstallListing()` | `POST /marketplace/install` | FS first | `refresh_single_artifact_cache()` | `['marketplace']` | PARTIAL -- missing `['artifacts']` invalidation |
| Update metadata | `useUpdateArtifact()` | `PUT /artifacts/{id}` | FS first | `refresh_single_artifact_cache()` (line 2444) | `['artifacts']` | YES |
| Update tags | `useUpdateArtifactTags()` | `PUT /artifacts/{id}/tags` | DB Tag system | DB -> FS write-back | `['artifacts']`, `['tags', 'artifact', id]` | YES |
| Delete | `useDeleteArtifact()` | `DELETE /artifacts/{id}` | FS + DB | `delete_artifact_cache()` | `['artifacts']` | PARTIAL -- missing `['deployments']`, `['collections']` |
| Delete (orchestrated) | `useArtifactDeletion()` | Multiple | FS + DB | Via deletion API | `['artifacts']`, `['deployments']`, `['collections']`, `['projects']` | YES |
| Deploy | `useDeploy()` | `POST /artifacts/{id}/deploy` | FS write | `refresh_single_artifact_cache()` (line 3000) | `['artifacts']`, `['deployments']` | YES |
| Undeploy | `useUndeploy()` | `POST /artifacts/{id}/undeploy` | FS write | via backend | `['artifacts']`, `['deployments']` | YES |
| Sync upstream | `useSync()` | `POST /artifacts/{id}/sync` | FS write | `refresh_single_artifact_cache()` (line 3237) | `['artifacts']` | YES |

#### File Operations

| Operation | Frontend Hook | API Endpoint | Backend Source | Cache Sync | Compliant? |
|-----------|--------------|-------------|---------------|-----------|------------|
| List files | none (inline) | `GET /artifacts/{id}/files` | Filesystem direct | none | YES (exception: file content is not cached) |
| Get file content | none (inline) | `GET /artifacts/{id}/files/{path}` | Filesystem direct | none | YES (exception) |
| Create file | none (inline) | `POST /artifacts/{id}/files/{path}` | Filesystem only | **NONE** | **NO** -- no `refresh_single_artifact_cache()` |
| Update file | none (inline) | `PUT /artifacts/{id}/files/{path}` | Filesystem only | **NONE** | **NO** -- no `refresh_single_artifact_cache()` |
| Delete file | none (inline) | `DELETE /artifacts/{id}/files/{path}` | Filesystem only | **NONE** | **NO** -- no `refresh_single_artifact_cache()` |

**Impact of non-compliance**: After editing a `SKILL.md` file, the `description` field extracted from that file in `CollectionArtifact` remains stale until the next full cache refresh. The user sees outdated metadata in list views.

---

### 3.2 Collections Domain (User Collections)

**Key files**:
- Frontend hooks: `skillmeat/web/hooks/use-collections.ts`
- Frontend API: `skillmeat/web/lib/api/collections.ts`
- Backend router: `skillmeat/api/routers/user_collections.py`

| Operation | Frontend Hook | API Endpoint | Backend Source | Stale Time | Cache Invalidation | Compliant? |
|-----------|--------------|-------------|---------------|-----------|-------------------|------------|
| List | `useCollections()` | `GET /user-collections` | DB (Collection table) | 5 min | -- | YES |
| Get details | `useCollection()` | `GET /user-collections/{id}` | DB | 5 min | -- | YES |
| Create | `useCreateCollection()` | `POST /user-collections` | DB | -- | `['collections', 'list']` | YES |
| Update | `useUpdateCollection()` | `PUT /user-collections/{id}` | DB | -- | `['collections', 'detail', id]`, `['collections', 'list']` | YES |
| Delete | `useDeleteCollection()` | `DELETE /user-collections/{id}` | DB | -- | `['collections', 'list']` | YES |
| List artifacts | `useCollectionArtifacts()` | `GET /user-collections/{id}/artifacts` | DB (CollectionArtifact join) | 5 min | -- | YES |
| List artifacts (infinite) | `useInfiniteCollectionArtifacts()` | `GET /user-collections/{id}/artifacts` | DB | 5 min | -- | YES |
| Add artifact | `useAddArtifactToCollection()` | `POST /user-collections/{id}/artifacts` | DB | -- | `['collections', 'detail', id]`, `['collections', ..., 'artifacts']`, `['artifacts']` | YES |
| Remove artifact | `useRemoveArtifactFromCollection()` | `DELETE /user-collections/{id}/artifacts/{id}` | DB | -- | Same as above | YES |

**Note**: The deprecated `/collections` endpoints (file-based `CollectionManager`) still exist in `routers/collections.py` but the frontend correctly uses `/user-collections`. The old endpoints are used only by the CLI.

**Compliance**: **Fully compliant.** All DB-native, consistent stale times, comprehensive invalidation.

---

### 3.3 Tags Domain

**Key files**:
- Frontend hooks: `skillmeat/web/hooks/use-tags.ts`
- Frontend API: `skillmeat/web/lib/api/tags.ts`
- Backend router: `skillmeat/api/routers/tags.py`

| Operation | Frontend Hook | API Endpoint | Backend Source | Stale Time | Cache Invalidation | Compliant? |
|-----------|--------------|-------------|---------------|-----------|-------------------|------------|
| List all | `useTags()` | `GET /tags` | DB (Tag table) | 5 min | -- | YES |
| Search | `useSearchTags()` | `GET /tags/search` | DB | 30 sec | -- | YES |
| Get artifact tags | `useArtifactTags()` | `GET /artifacts/{id}/tags` | DB (ArtifactTag join) | 5 min | -- | YES |
| Create | `useCreateTag()` | `POST /tags` | DB only | -- | `['tags']` | YES |
| Update | `useUpdateTag()` | `PUT /tags/{id}` | DB + FS write-back | -- | `['tags']`, `['artifacts']` | YES |
| Delete | `useDeleteTag()` | `DELETE /tags/{id}` | DB + FS write-back | -- | `['tags']`, `['artifacts']` | PARTIAL -- see Issue #11 |
| Add to artifact | `useAddTagToArtifact()` | `POST /artifacts/{id}/tags/{tagId}` | DB | -- | `['tags', 'artifact', artifactId]` | **NO** -- missing `['artifacts']` invalidation |
| Remove from artifact | `useRemoveTagFromArtifact()` | `DELETE /artifacts/{id}/tags/{tagId}` | DB | -- | `['tags', 'artifact', artifactId]` | **NO** -- missing `['artifacts']` invalidation |

**Critical Issues**:
- `useAddTagToArtifact()` and `useRemoveTagFromArtifact()` only invalidate per-artifact tag queries but not the main `['artifacts']` query key. Since artifact list responses embed tag data, list views show stale tags until their own stale time expires.
- Tag count accuracy depends on the FK relationship between `artifact_tags` and `collection_artifacts` -- see tag-management-architecture-fix-v1.md.

---

### 3.4 Groups Domain

**Key files**:
- Frontend hooks: `skillmeat/web/hooks/use-groups.ts`, `skillmeat/web/hooks/use-artifact-groups.ts`
- Backend router: `skillmeat/api/routers/groups.py`

| Operation | Frontend Hook | Stale Time | Cache Invalidation | Compliant? |
|-----------|--------------|-----------|-------------------|------------|
| List by collection | `useGroups()` | 5 min | -- | YES |
| Get detail | `useGroup()` | 5 min | -- | YES |
| Get artifacts | `useGroupArtifacts()` | 5 min | -- | YES |
| Create | `useCreateGroup()` | -- | `['groups', 'list', {collectionId}]` | YES |
| Update | `useUpdateGroup()` | -- | `['groups', 'detail', id]`, `['groups', 'list', {collectionId}]` | YES |
| Delete | `useDeleteGroup()` | -- | `['groups', 'list', {collectionId}]`, `['artifact-groups']` | YES |
| Reorder groups | `useReorderGroups()` | -- | `['groups', 'list', {collectionId}]` | YES |
| Add artifact | `useAddArtifactToGroup()` | -- | `['groups', 'artifacts', groupId]`, `['groups', 'detail', groupId]`, `['artifact-groups']` | YES |
| Remove artifact | `useRemoveArtifactFromGroup()` | -- | Same as above | YES |
| Reorder artifacts | `useReorderArtifactsInGroup()` | -- | `['groups', 'artifacts', groupId]` | YES |
| Move artifact | `useMoveArtifactToGroup()` | -- | Both source/target groups + `['artifact-groups']` | YES |
| Copy group | `useCopyGroup()` | -- | `['groups', 'list', {targetCollectionId}]`, `['artifact-groups']` | YES |

**Compliance**: **Fully compliant.** All DB-native, consistent stale times, exemplary cross-hook invalidation via `artifactGroupKeys`.

---

### 3.5 Deployments Domain

**Key files**:
- Frontend hooks: `skillmeat/web/hooks/use-deployments.ts`, `skillmeat/web/hooks/useDeploy.ts`
- Backend router: `skillmeat/api/routers/deployments.py`

| Operation | Frontend Hook | API Endpoint | Backend Source | Stale Time | Compliant? |
|-----------|--------------|-------------|---------------|-----------|------------|
| List | `useDeploymentList()` | `GET /deploy` | Filesystem (project `.claude/` dirs) | 2 min | PARTIAL -- no DB cache for listing |
| List filtered | `useDeployments()` | `GET /deploy` (filtered) | Filesystem | 2 min | PARTIAL |
| Summary | `useDeploymentSummary()` | `GET /deploy/summary` | Filesystem | 2 min | PARTIAL |
| Deploy | `useDeploy()` | `POST /artifacts/{id}/deploy` | FS write | -- | YES |
| Undeploy | `useUndeploy()` | `POST /artifacts/{id}/undeploy` | FS write | -- | YES |

**Analysis**: Deployments are inherently filesystem operations (deploying files to `.claude/` project directories). The read path scans the filesystem on each request, which is acceptable for the current scale but would benefit from DB caching for faster response on large project counts.

**Deploy/Undeploy cache invalidation** in `useDeploy()` (line 73-88 in `useDeploy.ts`) is well-implemented: awaits all invalidations, includes `['artifacts']`, `['deployments']`, and project-specific detail queries.

---

### 3.6 Projects Domain

**Key files**:
- Frontend hooks: `skillmeat/web/hooks/useProjects.ts`
- Backend router: `skillmeat/api/routers/projects.py`

| Operation | Frontend Hook | API Endpoint | Backend Source | Stale Time | Compliant? |
|-----------|--------------|-------------|---------------|-----------|------------|
| List | `useProjects()` | `GET /projects` | Filesystem scan (with 5min backend cache) | 5 min | PARTIAL -- backend caches but FS is source |
| Get detail | `useProject()` | `GET /projects/{id}` | Filesystem | none (default) | **NO** -- no stale time set |
| Create | `useCreateProject()` | `POST /projects` | DB + FS | -- | `['projects', 'list']` | YES |
| Update | `useUpdateProject()` | `PUT /projects/{id}` | DB + FS | -- | `['projects', 'list']`, `['projects', 'detail', id]` | YES |
| Delete | `useDeleteProject()` | `DELETE /projects/{id}` | DB + FS | -- | `['projects', 'list']` | YES |
| Force refresh | `useProjects().forceRefresh` | `GET /projects?refresh=true` | Filesystem (bypass cache) | -- | manual | YES |

**Note**: The backend implements a 5-minute in-memory cache for project discovery results (`PROJECTS_STALE_TIME` in `useProjects.ts`, line 196). The frontend matches this with its own 5-minute stale time. However, `useProject()` for individual project detail has no stale time configured (line 241-248).

---

### 3.7 Snapshots Domain

**Key files**:
- Frontend hooks: `skillmeat/web/hooks/use-snapshots.ts`

| Operation | Frontend Hook | Stale Time | Cache Invalidation | Compliant? |
|-----------|--------------|-----------|-------------------|------------|
| List | `useSnapshots()` | 5 min | -- | YES |
| Get detail | `useSnapshot()` | 5 min | -- | YES |
| Rollback analysis | `useRollbackAnalysis()` | 5 min | -- | YES |
| Create | `useCreateSnapshot()` | -- | `['snapshots', 'list']` | YES |
| Delete | `useDeleteSnapshot()` | -- | `['snapshots', 'detail', id]`, `['snapshots', 'list']` | YES |
| **Rollback** | `useRollback()` | -- | `['snapshots']`, `['collections']`, `['artifacts']` | **PARTIAL** -- missing `['deployments']` |
| Diff | `useDiffSnapshots()` | -- | none (read-only) | YES |

**Issue**: `useRollback()` (line 220-234 in `use-snapshots.ts`) invalidates `['snapshots']`, `['collections']`, and `['artifacts']` but does **not** invalidate `['deployments']` or `['projects']`. A rollback can change deployed artifact states, leaving the deployment view stale.

---

### 3.8 Context Entities Domain

**Key files**:
- Frontend hooks: `skillmeat/web/hooks/use-context-entities.ts`

| Operation | Frontend Hook | Stale Time | Cache Invalidation | Compliant? |
|-----------|--------------|-----------|-------------------|------------|
| List | `useContextEntities()` | 5 min | -- | YES |
| Get detail | `useContextEntity()` | 5 min | -- | YES |
| Get content | `useContextEntityContent()` | 5 min | -- | YES |
| Create | `useCreateContextEntity()` | -- | `['context-entities', 'list']` | YES |
| Update | `useUpdateContextEntity()` | -- | `['context-entities', 'detail', id]`, `['context-entities', 'list']`, `['context-entities', 'detail', id, 'content']` | YES |
| Delete | `useDeleteContextEntity()` | -- | `['context-entities', 'list']` | YES |
| Deploy | `useDeployContextEntity()` | -- | `['context-entities', 'list']`, `['deployments']` | YES |

**Compliance**: **Fully compliant.**

---

### 3.9 Context Sync Domain

**Key files**:
- Frontend hooks: `skillmeat/web/hooks/use-context-sync.ts`

| Operation | Frontend Hook | Stale Time | Cache Invalidation | Compliant? |
|-----------|--------------|-----------|-------------------|------------|
| Get status | `useContextSyncStatus()` | 30 sec | -- | YES |
| Pull changes | `usePullContextChanges()` | -- | `['context-sync-status']`, `['artifact-files']`, `['context-entities']` | PARTIAL -- missing `['deployments']` |
| Push changes | `usePushContextChanges()` | -- | `['context-sync-status']`, `['artifact-files']` | **NO** -- missing `['deployments']`, `['context-entities']` |
| Resolve conflict | `useResolveContextConflict()` | -- | `['context-sync-status']`, `['artifact-files']`, `['context-entities']` | PARTIAL -- missing `['deployments']` |

**Issue**: Push/pull operations modify deployed files in project `.claude/` directories, but deployment listing doesn't refresh. The deployment view can show stale sync status.

---

### 3.10 Marketplace Domain

**Key files**:
- Frontend hooks: `skillmeat/web/hooks/useMarketplace.ts`

| Operation | Frontend Hook | Stale Time | Cache Invalidation | Compliant? |
|-----------|--------------|-----------|-------------------|------------|
| List listings | `useListings()` | 1 min | -- | YES |
| Get listing detail | `useListing()` | 5 min | -- | YES |
| Get brokers | `useBrokers()` | 5 min | -- | YES |
| Install listing | `useInstallListing()` | -- | `['marketplace', 'listings']` | PARTIAL -- missing `['artifacts']` |
| Publish bundle | `usePublishBundle()` | -- | `['marketplace', 'listings']` | YES |

**Issue**: `useInstallListing()` invalidates marketplace queries but not `['artifacts']`. After installing a listing, the artifact list doesn't refresh automatically.

---

### 3.11 Analytics Domain

**Key files**:
- Frontend hooks: `skillmeat/web/hooks/useAnalytics.ts`

| Operation | Frontend Hook | Stale Time | Refetch Interval | Compliant? |
|-----------|--------------|-----------|-------------------|------------|
| Summary | `useAnalyticsSummary()` | 30 sec | 60 sec | YES |
| Top artifacts | `useTopArtifacts()` | 30 sec | 60 sec | YES |
| Usage trends | `useUsageTrends()` | 5 min | 10 min | YES |

**Compliance**: **Fully compliant.** Read-only domain with appropriate polling intervals.

---

### 3.12 Other Domains

| Domain | Hooks | Source | Stale Time | Compliant? | Notes |
|--------|-------|--------|-----------|------------|-------|
| Cache Status | `useCacheStatus()` | Backend API (`/projects/cache/stats`) | 30 sec | YES | Monitoring-only |
| Cache Refresh | `useCacheRefresh()` | `POST /projects/cache/refresh` | -- | PARTIAL | Invalidates `['projects']`, `['cache']` but not `['artifacts']` |
| Auto-Tags | `useSourceAutoTags()`, `useUpdateAutoTag()` | DB (marketplace sources) | 5 min | YES | |
| Bulk Tag Apply | `useBulkTagApply()` | Marketplace catalog API | -- | YES | Invalidates source catalog cache |
| Sync | `useSync()` | `POST /artifacts/{id}/sync` | -- | PARTIAL | Uses raw `fetch()` instead of `apiRequest()` |
| Merge | `useAnalyzeMerge()`, etc. | Merge API | -- | YES | Read-only analysis |
| Bundles | `useBundles()` etc. | DB/FS hybrid | varies | YES | |
| Discovery | `useDiscovery()` etc. | FS scan | varies | YES | |
| Version Graph | `useVersionGraph()` | FS | varies | YES | |

---

## 4. Identified Inconsistencies (Severity-Rated)

| # | Issue | Severity | Domain | Impact | Fix Approach |
|---|-------|----------|--------|--------|-------------|
| 1 | `GET /artifacts` list endpoint reads from filesystem, not DB cache | **High** | Artifacts | Every artifact list request iterates all filesystem collections. Slow for large collections; no DB-backed pagination. The `CollectionArtifact` cache table is populated but not used for this endpoint. | Add DB-first read path in `list_artifacts()` with FS fallback. Requires new query in `artifacts.py` line 1680+. |
| 2 | `GET /artifacts/{id}` detail reads from filesystem, not DB cache | **High** | Artifacts | Single artifact detail uses `artifact_mgr.show()` (FS). Inconsistent with collection artifact endpoints that read from DB. | Add cache-first read path in `get_artifact()` at line 1993 with FS fallback. |
| 3 | File operations (create/update/delete) don't trigger cache refresh | **High** | Artifacts | After editing `SKILL.md`, the `description` field in `CollectionArtifact` is stale. Lines 5229, 4952, 5513 in `artifacts.py` lack `refresh_single_artifact_cache()` calls. | Add `refresh_single_artifact_cache()` call after file mutations (3 endpoints). |
| 4 | `useArtifacts()` stale time is 30sec, standard is 5min | **Medium** | Artifacts | `useArtifacts()` at line 345 in `useArtifacts.ts` uses `staleTime: 30000` while `useInfiniteArtifacts()` at line 540 uses `5 * 60 * 1000`. Causes unnecessary refetches and inconsistent freshness. | Change to `5 * 60 * 1000` in `useArtifacts()`. |
| 5 | `useArtifact()` has no stale time configured | **Medium** | Artifacts | At line 353-360 in `useArtifacts.ts`, no `staleTime` is set. Uses TanStack Query default (0), meaning every mount triggers a refetch. | Add `staleTime: 5 * 60 * 1000`. |
| 6 | Snapshot rollback doesn't invalidate deployment/project caches | **High** | Snapshots | `useRollback()` at line 220 in `use-snapshots.ts` invalidates `['snapshots']`, `['collections']`, `['artifacts']` but omits `['deployments']` and `['projects']`. After rollback, deployment UI shows pre-rollback state. | Add `['deployments']` and `['projects']` to rollback invalidation. |
| 7 | Context sync push/pull don't invalidate deployment cache | **Medium** | Context Sync | `usePushContextChanges()` (line 69) and `usePullContextChanges()` (line 52) modify deployed files but don't invalidate `['deployments']`. | Add `['deployments']` invalidation to both hooks. |
| 8 | `useAddTagToArtifact()` / `useRemoveTagFromArtifact()` missing artifact list invalidation | **Medium** | Tags | Lines 199-239 in `use-tags.ts`: only invalidate per-artifact tag queries `['tags', 'artifact', artifactId]` but not `['artifacts']`. Artifact list views embed tags and show stale data. | Add `queryClient.invalidateQueries({ queryKey: ['artifacts'] })` to both hooks. |
| 9 | `useSync()` uses raw `fetch()` instead of `apiRequest()` | **Low** | Sync | Line 59 in `useSync.ts` uses `fetch()` directly, bypassing the unified API client's error handling, base URL construction, and auth headers. | Migrate to `apiRequest()`. |
| 10 | `useInstallListing()` doesn't invalidate artifact cache | **Medium** | Marketplace | After installing a marketplace listing, `['artifacts']` is not invalidated (line 161 in `useMarketplace.ts`). New artifacts don't appear in the artifact list until stale time expires. | Add `queryClient.invalidateQueries({ queryKey: ['artifacts'] })`. |
| 11 | Tag deletion invalidation doesn't cover per-artifact tag queries | **Medium** | Tags | `useDeleteTag()` at line 176 invalidates `['tags']` and `['artifacts']` but not `['tags', 'artifact', specificArtifactId]` for all affected artifacts. Per-artifact views may show deleted tags. | Invalidate `['tags', 'artifact']` (prefix match covers all artifact-specific tag queries). |
| 12 | `useCacheRefresh()` doesn't invalidate `['artifacts']` | **Low** | Cache | Line 66 in `useCacheRefresh.ts`: only invalidates `['projects']` and `['cache']`. After a full cache refresh, artifact data isn't refetched. | Add `['artifacts']` to the invalidation list. |
| 13 | `useProject()` detail has no stale time | **Low** | Projects | Line 241 in `useProjects.ts` has no `staleTime`. Uses default (0), causing refetch on every mount. | Add `staleTime: PROJECTS_STALE_TIME` (5 min, matching list). |
| 14 | `useDeleteArtifact()` missing cross-domain invalidation | **Medium** | Artifacts | Line 413 in `useArtifacts.ts`: only invalidates `['artifacts']`. Missing `['deployments']`, `['collections']`. The orchestrated `useArtifactDeletion()` hook is correct, but the simple delete hook is not. | Add `['deployments']`, `['collections']` invalidation, or deprecate in favor of `useArtifactDeletion()`. |

---

## 5. Canonical Data Flow Diagrams

### 5.1 Standard Read Flow (Cache-First) -- Target State

```
Frontend                   API Server               DB Cache              Filesystem
   |                          |                        |                      |
   |-- useHook() ----------->|                        |                      |
   |                          |-- Query DB cache ----->|                      |
   |                          |<-- Cached data --------|                      |
   |<-- Response -------------|                        |                      |
   |                          |                        |                      |
   |  [If cache miss or empty]                         |                      |
   |                          |-- Read filesystem ---------------------------->|
   |                          |<-- Raw data ----------------------------------|
   |                          |-- Upsert cache ------->|                      |
   |<-- Response -------------|                        |                      |
```

**Current deviation**: The `GET /artifacts` and `GET /artifacts/{id}` endpoints skip the DB cache entirely and always read from the filesystem. The cache-first path exists only for collection artifact endpoints (`GET /user-collections/{id}/artifacts`).

### 5.2 Standard Write Flow (Write-Through for FS-Backed Data)

```
Frontend                   API Server               Filesystem            DB Cache
   |                          |                        |                      |
   |-- useMutation() -------->|                        |                      |
   |                          |-- Write to FS -------->|                      |
   |                          |<-- Success ------------|                      |
   |                          |-- refresh_single_ -------------------------------->|
   |                          |   artifact_cache()     |                      |
   |                          |<-- Cache updated ------|----------------------|
   |<-- Response -------------|                        |                      |
   |                          |                        |                      |
   |-- invalidateQueries() ---|                        |                      |
   |   (TanStack auto-refetch)|                        |                      |
```

**Key call sites for `refresh_single_artifact_cache()`** in `artifacts.py`:
- Line 1639: After artifact metadata update (`PUT /artifacts/{id}`)
- Line 2444: After artifact update (alternative path)
- Line 3000: After deploy
- Line 3237: After sync
- Line 3390: After import
- **MISSING**: After file create/update/delete (lines 5229, 4952, 5513)

### 5.3 DB-Native Feature Write Flow (Collections, Groups, Tags)

```
Frontend                   API Server               Database              Filesystem
   |                          |                        |                      |
   |-- useMutation() -------->|                        |                      |
   |                          |-- Write to DB -------->|                      |
   |                          |<-- Success ------------|                      |
   |                          |                        |                      |
   |                          |  [If write-back needed, e.g. tags]            |
   |                          |-- Write-back to FS ---------------------------->|
   |                          |<-- FS updated --------------------------------|
   |                          |                        |                      |
   |<-- Response -------------|                        |                      |
   |-- invalidateQueries() ---|                        |                      |
```

**Write-back currently implemented for**: Tag update, tag delete (via `tag-management-architecture-fix-v1.md`).
**Write-back NOT implemented for**: Collection membership changes, group changes (DB-only, no FS representation).

### 5.4 Cache Refresh Flow (Full Sync)

```
Trigger                    API Server               Filesystem            DB Cache
   |                          |                        |                      |
   |-- refresh -------------->|                        |                      |
   |   (startup / manual /    |                        |                      |
   |    useCacheRefresh())    |                        |                      |
   |                          |-- Scan all FS -------->|                      |
   |                          |   collections          |                      |
   |                          |<-- All artifacts ------|                      |
   |                          |                        |                      |
   |                          |-- Upsert all -------------------------------->|
   |                          |   CollectionArtifact   |                      |
   |                          |-- Sync tags -----------|--------------------->|
   |                          |   (FS tags -> DB)      |                      |
   |                          |<-- Cache populated ---|----------------------|
   |<-- Complete --------------|                        |                      |
```

---

## 6. Remediation Plan (Prioritized)

### Phase 0: Execute Existing In-Flight Plans

These plans address known issues that are already documented.

| Item | Implementation Plan | Current Status | Priority | Resolves Issues |
|------|-------------------|---------------|----------|-----------------|
| Tag FK mismatch | `tag-management-architecture-fix-v1.md` Phase 1 | Draft | CRITICAL | Unblocks correct tag-artifact associations |
| Tag write-back durability | `tag-management-architecture-fix-v1.md` Phases 2-4 | Draft | HIGH | Tag rename/delete survive cache refresh |
| Tag storage consolidation | `tag-storage-consolidation-v1.md` | Draft | HIGH | Single source of truth for tags |
| Refresh metadata extraction | `refresh-metadata-extraction-v1.md` | In Progress | MEDIUM | Better metadata in cache |

### Phase 1: Frontend Standardization (4-6h estimated)

Quick wins that only require frontend hook changes. No backend changes needed.

| Task | Description | File | Line(s) | Issue # |
|------|-------------|------|---------|---------|
| 1.1 | Change `useArtifacts()` stale time from 30sec to 5min | `hooks/useArtifacts.ts` | 345 | #4 |
| 1.2 | Add stale time to `useArtifact()` (5min) | `hooks/useArtifacts.ts` | 353-360 | #5 |
| 1.3 | Add stale time to `useProject()` (5min) | `hooks/useProjects.ts` | 241-248 | #13 |
| 1.4 | Add `['deployments']`, `['projects']` to `useRollback()` invalidation | `hooks/use-snapshots.ts` | 229-232 | #6 |
| 1.5 | Add `['deployments']` to context sync push/pull/resolve invalidation | `hooks/use-context-sync.ts` | 59, 82, 109 | #7 |
| 1.6 | Add `['artifacts']` to `useAddTagToArtifact()` and `useRemoveTagFromArtifact()` invalidation | `hooks/use-tags.ts` | 206-210, 232-237 | #8 |
| 1.7 | Add `['tags', 'artifact']` prefix invalidation to `useDeleteTag()` | `hooks/use-tags.ts` | 176-182 | #11 |
| 1.8 | Add `['artifacts']` to `useInstallListing()` invalidation | `hooks/useMarketplace.ts` | 160-162 | #10 |
| 1.9 | Add `['artifacts']` to `useCacheRefresh()` invalidation | `hooks/useCacheRefresh.ts` | 66-77 | #12 |
| 1.10 | Add `['deployments']`, `['collections']` to `useDeleteArtifact()` invalidation or deprecate | `hooks/useArtifacts.ts` | 413-416 | #14 |
| 1.11 | Document stale time strategy in `web/CLAUDE.md` | `web/CLAUDE.md` | new section | -- |

### Phase 2: Backend Cache-First Reads (6-8h estimated)

Changes to backend routers to read from DB cache instead of filesystem for list and detail endpoints.

| Task | Description | File | Line(s) | Issue # |
|------|-------------|------|---------|---------|
| 2.1 | Add cache-first read path for `GET /artifacts` list endpoint | `api/routers/artifacts.py` | 1680-1800 | #1 |
| 2.2 | Add cache-first read path for `GET /artifacts/{id}` detail endpoint | `api/routers/artifacts.py` | 1993-2112 | #2 |
| 2.3 | Add `refresh_single_artifact_cache()` after file create | `api/routers/artifacts.py` | ~5350 (after write in `create_artifact_file`) | #3 |
| 2.4 | Add `refresh_single_artifact_cache()` after file update | `api/routers/artifacts.py` | ~5100 (after write in `update_artifact_file_content`) | #3 |
| 2.5 | Add `refresh_single_artifact_cache()` after file delete | `api/routers/artifacts.py` | ~5610 (after delete in `delete_artifact_file`) | #3 |
| 2.6 | Migrate `useSync()` from raw `fetch()` to `apiRequest()` | `hooks/useSync.ts` | 59 | #9 |

### Phase 3: Future Enhancements (Separate PRD)

Larger improvements that require dedicated planning.

| Task | Description | Effort | Priority |
|------|-------------|--------|----------|
| 3.1 | Add deployment state to DB cache for faster listing | 4-6h | Medium |
| 3.2 | Add project state to DB cache for faster listing | 4-6h | Medium |
| 3.3 | Add `X-Cache-Age` header to cache-backed API responses | 2-3h | Low |
| 3.4 | Add cache freshness indicator to frontend UI | 2-3h | Low |
| 3.5 | Implement WebSocket push for real-time cache invalidation | 8-12h | Low |

---

## 7. Decision Record

### ADR-2026-02-04: Data Flow Standardization

**Status**: Accepted

**Context**: SkillMeat has undergone multiple refactors since the introduction of the `CollectionArtifact` DB cache (artifact-metadata-cache-v1), collections API consolidation, and tag management fixes. Each refactor incrementally improved data flow patterns, but the overall system accumulated inconsistencies:

- Some endpoints read from DB cache while others read from filesystem for the same data domain
- Cache invalidation coverage varies between hooks: some invalidate cross-domain, others only invalidate their own domain
- Stale times range from 0 (no caching) to 10 minutes with no documented rationale
- Write-through patterns are applied inconsistently across file mutation endpoints

**Decision**: Establish "DB Cache is the Web's Source of Truth" as the canonical pattern with six architectural principles:

1. DB Cache is the Web's Source of Truth (reads)
2. Filesystem is the CLI's Source of Truth (reads)
3. Write-Through Pattern for Web Mutations (writes)
4. Cache Refresh is the Sync Mechanism (consistency)
5. Standardized Stale Times by Domain (freshness)
6. Mutations Always Invalidate Related Caches (reactivity)

**Consequences**:

- All future feature work **must** follow the standard patterns documented in this report
- Existing inconsistencies will be remediated in three phases (Phase 0-2)
- The 14 identified issues provide a concrete, prioritized backlog
- Phase 1 (frontend-only changes) can be executed immediately with low risk
- Phase 2 (backend cache-first reads) requires careful testing to ensure cache consistency

**Alternatives Considered**:

1. **Do nothing**: Inconsistencies would compound as new features are added. Rejected.
2. **Full DB migration**: Make DB the single source of truth for everything, including CLI. Rejected -- violates the offline-first design principle for CLI users.
3. **Event-sourced sync**: Use an event bus to automatically propagate all changes. Rejected -- over-architecture for current scale (YAGNI principle).

---

## 8. Appendix A: Complete Hook-to-Endpoint Mapping

### All Query Hooks

| Hook | File | Endpoint | Query Key Root | Stale Time | Refetch Interval | Compliant Stale? |
|------|------|----------|---------------|-----------|------------------|-----------------|
| `useArtifacts()` | `useArtifacts.ts:336` | `GET /artifacts` | `['artifacts', 'list', ...]` | **30 sec** | -- | NO (should be 5 min) |
| `useArtifact()` | `useArtifacts.ts:352` | `GET /artifacts/{id}` | `['artifacts', 'detail', id]` | **none** | -- | NO (should be 5 min) |
| `useInfiniteArtifacts()` | `useArtifacts.ts:520` | `GET /artifacts` | `['artifacts', 'infinite', ...]` | 5 min | -- | YES |
| `useCollections()` | `use-collections.ts:114` | `GET /user-collections` | `['collections', 'list', ...]` | 5 min | -- | YES |
| `useCollection()` | `use-collections.ts:170` | `GET /user-collections/{id}` | `['collections', 'detail', id]` | 5 min | -- | YES |
| `useCollectionArtifacts()` | `use-collections.ts:197` | `GET /user-collections/{id}/artifacts` | `['collections', 'detail', id, 'artifacts', ...]` | 5 min | -- | YES |
| `useInfiniteCollectionArtifacts()` | `use-collections.ts:277` | `GET /user-collections/{id}/artifacts` | `['collections', 'detail', id, 'infinite-artifacts', ...]` | 5 min | -- | YES |
| `useTags()` | `use-tags.ts:50` | `GET /tags` | `['tags', 'list', ...]` | 5 min | -- | YES |
| `useSearchTags()` | `use-tags.ts:70` | `GET /tags/search` | `['tags', 'search', query]` | 30 sec | -- | YES |
| `useArtifactTags()` | `use-tags.ts:90` | `GET /artifacts/{id}/tags` | `['tags', 'artifact', id]` | 5 min | -- | YES |
| `useGroups()` | `use-groups.ts:189` | `GET /groups` | `['groups', 'list', ...]` | 5 min | -- | YES |
| `useGroup()` | `use-groups.ts:240` | `GET /groups/{id}` | `['groups', 'detail', id]` | 5 min | -- | YES |
| `useGroupArtifacts()` | `use-groups.ts:287` | `GET /groups/{id}` | `['groups', 'detail', id, 'artifacts']` | 5 min | -- | YES |
| `useDeploymentList()` | `use-deployments.ts:71` | `GET /deploy` | `['deployments', 'list', ...]` | 2 min | -- | YES |
| `useDeployments()` | `use-deployments.ts:99` | `GET /deploy` | `['deployments', 'list', 'filtered', ...]` | 2 min | -- | YES |
| `useDeploymentSummary()` | `use-deployments.ts:126` | `GET /deploy/summary` | `['deployments', 'summary', ...]` | 2 min | -- | YES |
| `useProjects()` | `useProjects.ts:207` | `GET /projects` | `['projects', 'list']` | 5 min | -- | YES |
| `useProject()` | `useProjects.ts:240` | `GET /projects/{id}` | `['projects', 'detail', id]` | **none** | -- | NO (should be 5 min) |
| `useSnapshots()` | `use-snapshots.ts:70` | `GET /snapshots` | `['snapshots', 'list', ...]` | 5 min | -- | YES |
| `useSnapshot()` | `use-snapshots.ts:95` | `GET /snapshots/{id}` | `['snapshots', 'detail', ...]` | 5 min | -- | YES |
| `useRollbackAnalysis()` | `use-snapshots.ts:123` | `GET /snapshots/{id}/rollback-analysis` | `['snapshots', 'detail', ..., 'rollback-analysis']` | 5 min | -- | YES |
| `useContextEntities()` | `use-context-entities.ts:63` | `GET /context-entities` | `['context-entities', 'list', ...]` | 5 min | -- | YES |
| `useContextEntity()` | `use-context-entities.ts:88` | `GET /context-entities/{id}` | `['context-entities', 'detail', id]` | 5 min | -- | YES |
| `useContextEntityContent()` | `use-context-entities.ts:115` | `GET /context-entities/{id}/content` | `['context-entities', 'detail', id, 'content']` | 5 min | -- | YES |
| `useContextSyncStatus()` | `use-context-sync.ts:18` | `GET /context-sync/status` | `['context-sync-status', projectPath]` | 30 sec | 60 sec | YES |
| `useListings()` | `useMarketplace.ts:114` | `GET /marketplace/listings` | `['marketplace', 'listings', ...]` | 1 min | -- | YES |
| `useListing()` | `useMarketplace.ts:130` | `GET /marketplace/listings/{id}` | `['marketplace', 'detail', id]` | 5 min | -- | YES |
| `useBrokers()` | `useMarketplace.ts:142` | `GET /marketplace/brokers` | `['marketplace', 'brokers']` | 5 min | -- | YES |
| `useAnalyticsSummary()` | `useAnalytics.ts:177` | `GET /analytics/summary` | `['analytics', 'summary']` | 30 sec | 60 sec | YES |
| `useTopArtifacts()` | `useAnalytics.ts:189` | `GET /analytics/top-artifacts` | `['analytics', 'top-artifacts', ...]` | 30 sec | 60 sec | YES |
| `useUsageTrends()` | `useAnalytics.ts:201` | `GET /analytics/trends` | `['analytics', 'trends', ...]` | 5 min | 10 min | YES |
| `useCacheStatus()` | `useCacheStatus.ts:62` | `GET /projects/cache/stats` | `['cache', 'status']` | 30 sec | 60 sec | YES |
| `useArtifactSearch()` | `use-artifact-search.ts:147` | `GET /marketplace/catalog/search` | `['artifact-search', 'search', ...]` | 30 sec | -- | YES |
| `useSourceAutoTags()` | `use-auto-tags.ts:41` | `GET /marketplace/sources/{id}/auto-tags` | `['auto-tags', sourceId]` | 5 min | -- | YES |

### All Mutation Hooks

| Hook | File | Endpoint | Method | Invalidates |
|------|------|----------|--------|-------------|
| `useUpdateArtifact()` | `useArtifacts.ts:365` | `PUT /artifacts/{id}` | PUT | `['artifacts']` |
| `useDeleteArtifact()` | `useArtifacts.ts:395` | `DELETE /artifacts/{id}` | DELETE | `['artifacts']` **INCOMPLETE** |
| `useUpdateArtifactTags()` | `useArtifacts.ts:437` | `PUT /artifacts/{id}/tags` | PUT | `['artifacts']`, `['tags', 'artifact', id]` |
| `useArtifactDeletion()` | `use-artifact-deletion.ts:65` | Multiple | Mixed | `['artifacts']`, `['deployments']`, `['collections']`, `['projects']` |
| `useCreateCollection()` | `use-collections.ts:311` | `POST /user-collections` | POST | `['collections', 'list']` |
| `useUpdateCollection()` | `use-collections.ts:339` | `PUT /user-collections/{id}` | PUT | `['collections', 'detail', id]`, `['collections', 'list']` |
| `useDeleteCollection()` | `use-collections.ts:371` | `DELETE /user-collections/{id}` | DELETE | `['collections', 'list']` |
| `useAddArtifactToCollection()` | `use-collections.ts:399` | `POST /user-collections/{id}/artifacts` | POST | `['collections', 'detail', id]`, `['collections', ..., 'artifacts']`, `['artifacts']` |
| `useRemoveArtifactFromCollection()` | `use-collections.ts:441` | `DELETE /user-collections/{id}/artifacts/{id}` | DELETE | Same as above |
| `useCreateTag()` | `use-tags.ts:114` | `POST /tags` | POST | `['tags']` |
| `useUpdateTag()` | `use-tags.ts:142` | `PUT /tags/{id}` | PUT | `['tags']`, `['artifacts']` |
| `useDeleteTag()` | `use-tags.ts:169` | `DELETE /tags/{id}` | DELETE | `['tags']`, `['artifacts']` **INCOMPLETE** |
| `useAddTagToArtifact()` | `use-tags.ts:199` | `POST /artifacts/{id}/tags/{tagId}` | POST | `['tags', 'artifact', id]` **INCOMPLETE** |
| `useRemoveTagFromArtifact()` | `use-tags.ts:227` | `DELETE /artifacts/{id}/tags/{tagId}` | DELETE | `['tags', 'artifact', id]` **INCOMPLETE** |
| `useCreateGroup()` | `use-groups.ts:334` | `POST /groups` | POST | `['groups', 'list', {collectionId}]` |
| `useUpdateGroup()` | `use-groups.ts:389` | `PUT /groups/{id}` | PUT | `['groups', 'detail', id]`, `['groups', 'list', {collectionId}]` |
| `useDeleteGroup()` | `use-groups.ts:439` | `DELETE /groups/{id}` | DELETE | `['groups', 'list', {collectionId}]`, `['artifact-groups']` |
| `useReorderGroups()` | `use-groups.ts:488` | `PUT /collections/{id}/groups/reorder` | PUT | `['groups', 'list', {collectionId}]` |
| `useAddArtifactToGroup()` | `use-groups.ts:547` | `POST /groups/{id}/artifacts` | POST | `['groups', 'artifacts', id]`, `['groups', 'detail', id]`, `['artifact-groups']` |
| `useRemoveArtifactFromGroup()` | `use-groups.ts:609` | `DELETE /groups/{id}/artifacts/{id}` | DELETE | Same as above |
| `useReorderArtifactsInGroup()` | `use-groups.ts:664` | `POST /groups/{id}/artifacts/reorder` | POST | `['groups', 'artifacts', id]` |
| `useMoveArtifactToGroup()` | `use-groups.ts:727` | `POST /groups/{id}/artifacts/{id}/move` | POST | Both groups + `['artifact-groups']` |
| `useCopyGroup()` | `use-groups.ts:804` | `POST /groups/{id}/copy` | POST | `['groups', 'list', {targetId}]`, `['artifact-groups']` |
| `useDeployArtifact()` | `use-deployments.ts:156` | `POST /deploy` | POST | `['deployments', 'list', ...]`, `['deployments', 'summary', ...]`, `['deployments', 'list']` |
| `useUndeployArtifact()` | `use-deployments.ts:202` | `POST /deploy/undeploy` | POST | Same as above |
| `useDeploy()` | `useDeploy.ts:45` | `POST /artifacts/{id}/deploy` | POST | `['artifacts']`, `['deployments']`, project detail |
| `useUndeploy()` | `useDeploy.ts:120` | `POST /artifacts/{id}/undeploy` | POST | `['artifacts']`, `['deployments']`, project detail |
| `useCreateSnapshot()` | `use-snapshots.ts:150` | `POST /snapshots` | POST | `['snapshots', 'list']` |
| `useDeleteSnapshot()` | `use-snapshots.ts:180` | `DELETE /snapshots/{id}` | DELETE | `['snapshots', 'detail', ...]`, `['snapshots', 'list']` |
| `useRollback()` | `use-snapshots.ts:220` | `POST /snapshots/{id}/rollback` | POST | `['snapshots']`, `['collections']`, `['artifacts']` **INCOMPLETE** |
| `useCreateContextEntity()` | `use-context-entities.ts:145` | `POST /context-entities` | POST | `['context-entities', 'list']` |
| `useUpdateContextEntity()` | `use-context-entities.ts:178` | `PUT /context-entities/{id}` | PUT | `['context-entities', 'detail', id]`, `['context-entities', 'list']`, `['context-entities', 'detail', id, 'content']` |
| `useDeleteContextEntity()` | `use-context-entities.ts:213` | `DELETE /context-entities/{id}` | DELETE | `['context-entities', 'list']` |
| `useDeployContextEntity()` | `use-context-entities.ts:239` | `POST /context-entities/{id}/deploy` | POST | `['context-entities', 'list']`, `['deployments']` |
| `usePullContextChanges()` | `use-context-sync.ts:52` | `POST /context-sync/pull` | POST | `['context-sync-status']`, `['artifact-files']`, `['context-entities']` **INCOMPLETE** |
| `usePushContextChanges()` | `use-context-sync.ts:69` | `POST /context-sync/push` | POST | `['context-sync-status']`, `['artifact-files']` **INCOMPLETE** |
| `useResolveContextConflict()` | `use-context-sync.ts:95` | `POST /context-sync/resolve` | POST | `['context-sync-status']`, `['artifact-files']`, `['context-entities']` **INCOMPLETE** |
| `useCacheRefresh()` | `useCacheRefresh.ts:54` | `POST /projects/cache/refresh` | POST | `['projects']`, `['cache']` **INCOMPLETE** |
| `useInstallListing()` | `useMarketplace.ts:153` | `POST /marketplace/install` | POST | `['marketplace', 'listings']` **INCOMPLETE** |
| `usePublishBundle()` | `useMarketplace.ts:183` | `POST /marketplace/publish` | POST | `['marketplace', 'listings']` |
| `useSync()` | `useSync.ts:54` | `POST /artifacts/{id}/sync` | POST | `['artifacts']` |
| `useCreateProject()` | `useProjects.ts:253` | `POST /projects` | POST | `['projects', 'list']` |
| `useUpdateProject()` | `useProjects.ts:268` | `PUT /projects/{id}` | PUT | `['projects', 'list']`, `['projects', 'detail', id]` |
| `useDeleteProject()` | `useProjects.ts:285` | `DELETE /projects/{id}` | DELETE | `['projects', 'list']` |
| `useUpdateAutoTag()` | `use-auto-tags.ts:75` | `PUT /marketplace/sources/{id}/auto-tags` | PUT | `['auto-tags', sourceId]`, `['sources', sourceId]` |
| `useBulkTagApply()` | `use-bulk-tag-apply.ts:80` | Multiple catalog endpoints | Mixed | Source catalog cache |

---

## 9. Appendix B: Related Documents

| Document | Path | Status | Relationship |
|----------|------|--------|-------------|
| Dual Collection System Architecture Analysis | `/docs/project_plans/reports/dual-collection-system-architecture-analysis.md` | Complete | Explains why FS + DB dual-stack exists |
| Manage Collection Page Architecture Analysis | `/docs/project_plans/reports/manage-collection-page-architecture-analysis.md` | Complete | UI-side collection management patterns |
| Collections API Consolidation | `/docs/project_plans/implementation_plans/refactors/collections-api-consolidation-v1.md` | Complete | Migrated frontend from `/collections` to `/user-collections` |
| Artifact Metadata Cache | `/docs/project_plans/implementation_plans/refactors/artifact-metadata-cache-v1.md` | Complete | Introduced `CollectionArtifact` DB cache table |
| Tag Storage Consolidation | `/docs/project_plans/implementation_plans/refactors/tag-storage-consolidation-v1.md` | Draft | Plan to unify tag storage between FS and DB |
| Tag Management Architecture Fix | `/docs/project_plans/implementation_plans/refactors/tag-management-architecture-fix-v1.md` | Draft | Fixes FK mismatch, tag write-back, tag count bugs |
| Refresh Metadata Extraction | `/docs/project_plans/implementation_plans/refactors/refresh-metadata-extraction-v1.md` | In Progress | Improves metadata extraction during cache refresh |
| Collection Data Consistency | `/docs/project_plans/implementation_plans/refactors/collection-data-consistency-v1.md` | Complete | Fixed FS<->DB data consistency issues |
| Entity-Artifact Consolidation | `/docs/project_plans/implementation_plans/refactors/entity-artifact-consolidation-v1.md` | Complete | Renamed Entity -> Artifact across codebase |

---

*This report establishes the canonical data flow standard for SkillMeat. All future feature development and refactoring must comply with the six principles defined in Section 2. Deviations require an explicit ADR justifying the exception.*
