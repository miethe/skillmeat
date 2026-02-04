---
title: API Endpoint Mapping
purpose: Complete reference of all API endpoints - load for API mismatches or adding endpoints
references:
  - skillmeat/api/routers/collections.py
  - skillmeat/api/routers/user_collections.py
  - skillmeat/api/routers/artifacts.py
  - skillmeat/api/routers/deployments.py
  - skillmeat/api/routers/projects.py
  - skillmeat/api/routers/marketplace.py
  - skillmeat/api/routers/marketplace_sources.py
  - skillmeat/api/routers/mcp.py
  - skillmeat/api/routers/bundles.py
  - skillmeat/api/routers/groups.py
  - skillmeat/api/routers/cache.py
  - skillmeat/api/routers/context_sync.py
  - skillmeat/api/routers/analytics.py
  - skillmeat/api/routers/health.py
last_verified: 2025-02-04
---

# API Endpoint Mapping

Complete reference of all SkillMeat API endpoints organized by domain.

## Collections API (Read-Only, File-Based)

**Router**: `skillmeat/api/routers/collections.py`
**Base**: `/api/v1/collections`
**Purpose**: Legacy read-only access to file-based collections

| Endpoint | Method | Response Model | Decorator Pattern | Status |
|----------|--------|----------------|-------------------|--------|
| `/api/v1/collections` | GET | CollectionListResponse | `@router.get("", response_model=CollectionListResponse` | Active |
| `/api/v1/collections/{collection_id}` | GET | CollectionResponse | `@router.get("/{collection_id}", response_model=CollectionResponse` | Active |
| `/api/v1/collections/{collection_id}/artifacts` | GET | CollectionArtifactsResponse | `@router.get("/{collection_id}/artifacts", response_model=CollectionArtifactsResponse` | Active |

**Key Characteristics**:
- Read-only (GET only)
- File-based storage (`~/.skillmeat/collection/`)
- No pagination support
- No mutation operations

## User Collections API (CRUD, Database-Backed)

**Router**: `skillmeat/api/routers/user_collections.py`
**Base**: `/api/v1/user-collections`
**Purpose**: Full CRUD for database-backed user collections

| Endpoint | Method | Response Model | Decorator Pattern | Status |
|----------|--------|----------------|-------------------|--------|
| `/api/v1/user-collections` | GET | UserCollectionListResponse | `@router.get("", response_model=UserCollectionListResponse` | Active |
| `/api/v1/user-collections` | POST | UserCollectionResponse | `@router.post("", response_model=UserCollectionResponse, status_code=status.HTTP_201_CREATED` | Active |
| `/api/v1/user-collections/{collection_id}` | GET | UserCollectionWithGroupsResponse | `@router.get("/{collection_id}", response_model=UserCollectionWithGroupsResponse` | Active |
| `/api/v1/user-collections/{collection_id}` | PUT | UserCollectionResponse | `@router.put("/{collection_id}", response_model=UserCollectionResponse` | Active |
| `/api/v1/user-collections/{collection_id}` | DELETE | None (204) | `@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT` | Active |
| `/api/v1/user-collections/{collection_id}/artifacts` | POST | None (201) | `@router.post("/{collection_id}/artifacts", status_code=status.HTTP_201_CREATED` | Active |
| `/api/v1/user-collections/{collection_id}/artifacts/{artifact_id}` | DELETE | None (204) | `@router.delete("/{collection_id}/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT` | Active |

**Key Characteristics**:
- Full CRUD operations (GET, POST, PUT, DELETE)
- Database-backed (SQLAlchemy models)
- Supports pagination via query params
- Supports artifact association (many-to-many)
- Supports groups within collections

**Pagination Pattern**:
```python
# Query parameters
limit: int = Query(50, ge=1, le=100)
offset: int = Query(0, ge=0)
```

## Artifacts API

**Router**: `skillmeat/api/routers/artifacts.py`
**Base**: `/api/v1/artifacts`
**Purpose**: Artifact management, installation, deployment

| Endpoint | Method | Response Model | Required Params | Lines |
|----------|--------|----------------|-----------------|-------|
| `/api/v1/artifacts/install` | POST | ArtifactInstallResponse | N/A | ~482 |
| `/api/v1/artifacts/install/batch` | POST | BatchInstallResponse | N/A | ~623 |
| `/api/v1/artifacts/uninstall` | POST | ArtifactUninstallResponse | N/A | ~722 |
| `/api/v1/artifacts/{artifact_id}/sync` | POST | ArtifactSyncResponse | `artifact_id` (path), `project_path` (optional body) | ~3038 |
| `/api/v1/artifacts/{artifact_id}/deploy` | POST | ArtifactDeployResponse | `artifact_id` (path), `project_path` (body), `overwrite` (body) | ~2875 |
| `/api/v1/artifacts/{artifact_id}/diff` | GET | ArtifactDiffResponse | `artifact_id` (path), `project_path` (query) | ~3668 |
| `/api/v1/artifacts/{artifact_id}/upstream-diff` | GET | ArtifactUpstreamDiffResponse | `artifact_id` (path), `collection` (query, optional) | ~4027 |
| `/api/v1/artifacts` | GET | ArtifactListResponse | N/A | ~1250 |
| `/api/v1/artifacts/search` | GET | ArtifactSearchResponse | N/A | ~1480 |
| `/api/v1/artifacts/{artifact_id}` | GET | ArtifactDetailResponse | `artifact_id` (path) | ~1606 |
| `/api/v1/artifacts/{artifact_id}` | PUT | ArtifactUpdateResponse | `artifact_id` (path) | ~1772 |
| `/api/v1/artifacts/{artifact_id}/metadata` | PUT | ArtifactMetadataResponse | `artifact_id` (path) | ~1945 |
| `/api/v1/artifacts/{artifact_id}` | DELETE | None (204) | `artifact_id` (path) | ~2178 |
| `/api/v1/artifacts/validate` | POST | ValidationResponse | N/A | ~2291 |
| `/api/v1/artifacts/export` | POST | ExportResponse | N/A | ~2441 |
| `/api/v1/artifacts/import` | POST | ImportResponse | N/A | ~2802 |
| `/api/v1/artifacts/{artifact_id}/versions` | GET | VersionListResponse | `artifact_id` (path) | ~2901 |
| `/api/v1/artifacts/{artifact_id}/dependencies` | GET | DependencyListResponse | `artifact_id` (path) | ~3042 |
| `/api/v1/artifacts/{artifact_id}/deploy-status` | GET | DeployStatusResponse | `artifact_id` (path) | ~3382 |
| `/api/v1/artifacts/tags` | GET | TagListResponse | N/A | ~3790 |
| `/api/v1/artifacts/sources` | GET | SourceListResponse | N/A | ~4025 |
| `/api/v1/artifacts/{artifact_id}/clone` | PUT | ArtifactCloneResponse | `artifact_id` (path) | ~4270 |
| `/api/v1/artifacts/{artifact_id}/fork` | POST | ArtifactForkResponse | `artifact_id` (path) | ~4521 |
| `/api/v1/artifacts/{artifact_id}/snapshot` | DELETE | None (204) | `artifact_id` (path) | ~4782 |
| `/api/v1/artifacts/metadata/github` | GET | MetadataFetchResponse | N/A | ~4991 |
| `/api/v1/artifacts/stats` | GET | ArtifactStatsResponse | N/A | ~5112 |
| `/api/v1/artifacts/types` | GET | ArtifactTypesResponse | N/A | ~5151 |
| `/api/v1/artifacts/batch` | POST | BatchOperationResponse | N/A | ~5213 |
| `/api/v1/artifacts/orphaned` | DELETE | CleanupResponse | N/A | ~5301 |
| `/api/v1/artifacts/cache` | DELETE | CacheClearResponse | N/A | ~5383 |
| `/api/v1/artifacts/recent` | GET | RecentArtifactsResponse | N/A | ~5463 |

**Key Operations**:
- Installation: `/install`, `/install/batch`, `/uninstall`
- Search & Browse: `/`, `/search`, `/{artifact_id}`
- Sync & Deployment: `/{artifact_id}/sync`, `/{artifact_id}/deploy`
- Diff & Comparison: `/{artifact_id}/diff`, `/{artifact_id}/upstream-diff`
- Metadata: `/{artifact_id}/metadata`, `/metadata/github`
- Version Management: `/{artifact_id}/versions`
- Maintenance: `/orphaned`, `/cache`, `/validate`

## Context Sync API

**Router**: `skillmeat/api/routers/context_sync.py`
**Base**: `/api/v1/context-sync`
**Purpose**: Bi-directional synchronization of context entities between collections and projects

| Endpoint | Method | Request Body | Response Model | Required Params | Lines |
|----------|--------|--------------|----------------|-----------------|-------|
| `/api/v1/context-sync/pull` | POST | SyncPullRequest | List[SyncResultResponse] | `project_path`, `entity_ids` (optional) | ~76 |
| `/api/v1/context-sync/push` | POST | SyncPushRequest | List[SyncResultResponse] | `project_path`, `entity_ids` (optional), `overwrite` | ~180 |
| `/api/v1/context-sync/status` | GET | N/A | SyncStatusResponse | `project_path` (query) | ~281 |
| `/api/v1/context-sync/resolve` | POST | SyncResolveRequest | SyncResultResponse | `project_path`, `entity_id`, `resolution`, `merged_content` (if merge) | ~396 |

**Request Body Examples**:

**Pull Request** (SyncPullRequest):
```json
{
  "project_path": "/absolute/path/to/project",
  "entity_ids": ["spec_file:api-patterns", "rule_file:debugging"]
}
```

**Push Request** (SyncPushRequest):
```json
{
  "project_path": "/absolute/path/to/project",
  "entity_ids": ["spec_file:api-patterns"],
  "overwrite": false
}
```

**Resolve Request** (SyncResolveRequest):
```json
{
  "project_path": "/absolute/path/to/project",
  "entity_id": "spec_file:api-patterns",
  "resolution": "keep_local",
  "merged_content": null
}
```

**Cache Invalidation Keys** (TanStack Query):
- `['context-sync-status']` - Invalidate on any pull/push/resolve mutation
- `['artifact-files']` - Invalidate when entity file content changes
- `['context-entities']` - Invalidate when entities modified
- `['deployments']` - Invalidate for deployment-related changes
- `['artifacts']` - Invalidate for artifact list changes

## Deployments API

**Router**: `skillmeat/api/routers/deployments.py`
**Base**: `/api/v1/deployments`

| Endpoint | Method | Response Model | Decorator Pattern | Lines |
|----------|--------|----------------|-------------------|-------|
| `/api/v1/deployments/deploy` | POST | DeployResponse | `@router.post("/deploy", response_model=DeployResponse` | ~52 |
| `/api/v1/deployments/rollback` | POST | RollbackResponse | `@router.post("/rollback", response_model=RollbackResponse` | ~192 |
| `/api/v1/deployments/{project_id}` | GET | DeploymentListResponse | `@router.get("/{project_id}", response_model=DeploymentListResponse` | ~287 |

## Projects API

**Router**: `skillmeat/api/routers/projects.py`
**Base**: `/api/v1/projects`

| Endpoint | Method | Response Model | Decorator Pattern | Lines |
|----------|--------|----------------|-------------------|-------|
| `/api/v1/projects` | GET | ProjectListResponse | `@router.get("", response_model=ProjectListResponse` | ~292 |
| `/api/v1/projects` | POST | ProjectCreateResponse | `@router.post("", response_model=ProjectCreateResponse` | ~515 |
| `/api/v1/projects/{project_id}` | GET | ProjectDetailResponse | `@router.get("/{project_id}", response_model=ProjectDetailResponse` | ~635 |
| `/api/v1/projects/{project_id}` | PUT | ProjectUpdateResponse | `@router.put("/{project_id}", response_model=ProjectUpdateResponse` | ~739 |
| `/api/v1/projects/{project_id}` | DELETE | None (204) | `@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT` | ~843 |
| `/api/v1/projects/{project_id}/init` | POST | ProjectInitResponse | `@router.post("/{project_id}/init", response_model=ProjectInitResponse` | ~955 |
| `/api/v1/projects/{project_id}/artifacts` | GET | ProjectArtifactsResponse | `@router.get("/{project_id}/artifacts", response_model=ProjectArtifactsResponse` | ~1120 |
| `/api/v1/projects/register` | POST | ProjectRegisterResponse | `@router.post("/register", response_model=ProjectRegisterResponse` | ~1261 |
| `/api/v1/projects/discover` | GET | ProjectDiscoverResponse | `@router.get("/discover", response_model=ProjectDiscoverResponse` | ~1303 |

## Marketplace API

**Router**: `skillmeat/api/routers/marketplace.py`
**Base**: `/api/v1/marketplace`

| Endpoint | Method | Response Model | Decorator Pattern | Lines |
|----------|--------|----------------|-------------------|-------|
| `/api/v1/marketplace/search` | GET | MarketplaceSearchResponse | `@router.get("/search", response_model=MarketplaceSearchResponse` | ~85 |
| `/api/v1/marketplace/skills/{skill_id}` | GET | SkillDetailResponse | `@router.get("/skills/{skill_id}", response_model=SkillDetailResponse` | ~319 |
| `/api/v1/marketplace/install` | POST | InstallResponse | `@router.post("/install", response_model=InstallResponse` | ~439 |
| `/api/v1/marketplace/sync` | POST | SyncMarketplaceResponse | `@router.post("/sync", response_model=SyncMarketplaceResponse` | ~574 |
| `/api/v1/marketplace/categories` | GET | CategoryListResponse | `@router.get("/categories", response_model=CategoryListResponse` | ~691 |
| `/api/v1/marketplace/featured` | POST | FeaturedListResponse | `@router.post("/featured", response_model=FeaturedListResponse` | ~762 |
| `/api/v1/marketplace/trending` | POST | TrendingListResponse | `@router.post("/trending", response_model=TrendingListResponse` | ~832 |
| `/api/v1/marketplace/recommended` | POST | RecommendedListResponse | `@router.post("/recommended", response_model=RecommendedListResponse` | ~882 |
| `/api/v1/marketplace/stats` | GET | MarketplaceStatsResponse | `@router.get("/stats", response_model=MarketplaceStatsResponse` | ~938 |

## Marketplace Sources API

**Router**: `skillmeat/api/routers/marketplace_sources.py`
**Base**: `/api/v1/marketplace-sources`

| Endpoint | Method | Response Model | Decorator Pattern | Lines |
|----------|--------|----------------|-------------------|-------|
| `/api/v1/marketplace-sources` | POST | MarketplaceSourceResponse | `@router.post("", response_model=MarketplaceSourceResponse` | ~151 |
| `/api/v1/marketplace-sources` | GET | MarketplaceSourceListResponse | `@router.get("", response_model=MarketplaceSourceListResponse` | ~234 |
| `/api/v1/marketplace-sources/{source_id}` | GET | MarketplaceSourceDetailResponse | `@router.get("/{source_id}", response_model=MarketplaceSourceDetailResponse` | ~292 |
| `/api/v1/marketplace-sources/{source_id}` | PATCH | MarketplaceSourceResponse | `@router.patch("/{source_id}", response_model=MarketplaceSourceResponse` | ~337 |
| `/api/v1/marketplace-sources/{source_id}` | DELETE | None (204) | `@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT` | ~418 |
| `/api/v1/marketplace-sources/{source_id}/sync` | POST | SourceSyncResponse | `@router.post("/{source_id}/sync", response_model=SourceSyncResponse` | ~468 |
| `/api/v1/marketplace-sources/{source_id}/artifacts` | GET | SourceArtifactListResponse | `@router.get("/{source_id}/artifacts", response_model=SourceArtifactListResponse` | ~600 |
| `/api/v1/marketplace-sources/batch-sync` | POST | BatchSyncResponse | `@router.post("/batch-sync", response_model=BatchSyncResponse` | ~734 |

## MCP Servers API

**Router**: `skillmeat/api/routers/mcp.py`
**Base**: `/api/v1/mcp`

| Endpoint | Method | Response Model | Decorator Pattern | Lines |
|----------|--------|----------------|-------------------|-------|
| `/api/v1/mcp/servers` | GET | MCPServerListResponse | `@router.get("/servers", response_model=MCPServerListResponse` | ~67 |
| `/api/v1/mcp/servers/{server_id}` | GET | MCPServerDetailResponse | `@router.get("/servers/{server_id}", response_model=MCPServerDetailResponse` | ~133 |
| `/api/v1/mcp/servers` | POST | MCPServerCreateResponse | `@router.post("/servers", response_model=MCPServerCreateResponse` | ~203 |
| `/api/v1/mcp/servers/{server_id}` | PUT | MCPServerUpdateResponse | `@router.put("/servers/{server_id}", response_model=MCPServerUpdateResponse` | ~305 |
| `/api/v1/mcp/servers/{server_id}` | DELETE | None (204) | `@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT` | ~403 |
| `/api/v1/mcp/servers/{server_id}/start` | POST | MCPServerStatusResponse | `@router.post("/servers/{server_id}/start", response_model=MCPServerStatusResponse` | ~474 |
| `/api/v1/mcp/servers/{server_id}/stop` | POST | MCPServerStatusResponse | `@router.post("/servers/{server_id}/stop", response_model=MCPServerStatusResponse` | ~590 |
| `/api/v1/mcp/servers/{server_id}/status` | GET | MCPServerStatusResponse | `@router.get("/servers/{server_id}/status", response_model=MCPServerStatusResponse` | ~687 |
| `/api/v1/mcp/servers/{server_id}/logs` | GET | MCPServerLogsResponse | `@router.get("/servers/{server_id}/logs", response_model=MCPServerLogsResponse` | ~769 |
| `/api/v1/mcp/config` | GET | MCPConfigResponse | `@router.get("/config", response_model=MCPConfigResponse` | ~842 |

## Bundles API

**Router**: `skillmeat/api/routers/bundles.py`
**Base**: `/api/v1/bundles`

| Endpoint | Method | Response Model | Decorator Pattern | Lines |
|----------|--------|----------------|-------------------|-------|
| `/api/v1/bundles/create` | POST | BundleCreateResponse | `@router.post("/create", response_model=BundleCreateResponse` | ~63 |
| `/api/v1/bundles/install` | POST | BundleInstallResponse | `@router.post("/install", response_model=BundleInstallResponse` | ~235 |
| `/api/v1/bundles/export` | POST | BundleExportResponse | `@router.post("/export", response_model=BundleExportResponse` | ~343 |
| `/api/v1/bundles/import` | POST | BundleImportResponse | `@router.post("/import", response_model=BundleImportResponse` | ~592 |
| `/api/v1/bundles` | GET | BundleListResponse | `@router.get("", response_model=BundleListResponse` | ~785 |
| `/api/v1/bundles/{bundle_id}` | GET | BundleDetailResponse | `@router.get("/{bundle_id}", response_model=BundleDetailResponse` | ~866 |
| `/api/v1/bundles/{bundle_id}` | DELETE | None (204) | `@router.delete("/{bundle_id}", status_code=status.HTTP_204_NO_CONTENT` | ~928 |
| `/api/v1/bundles/{bundle_id}/artifacts` | GET | BundleArtifactsResponse | `@router.get("/{bundle_id}/artifacts", response_model=BundleArtifactsResponse` | ~1007 |
| `/api/v1/bundles/{bundle_id}` | PUT | BundleUpdateResponse | `@router.put("/{bundle_id}", response_model=BundleUpdateResponse` | ~1286 |
| `/api/v1/bundles/{bundle_id}/share` | DELETE | BundleShareResponse | `@router.delete("/{bundle_id}/share", response_model=BundleShareResponse` | ~1407 |

## Groups API

**Router**: `skillmeat/api/routers/groups.py`
**Base**: `/api/v1/groups`

| Endpoint | Method | Response Model | Decorator Pattern | Lines |
|----------|--------|----------------|-------------------|-------|
| `/api/v1/groups` | POST | GroupCreateResponse | `@router.post("", response_model=GroupCreateResponse` | ~55 |
| `/api/v1/groups` | GET | GroupListResponse | `@router.get("", response_model=GroupListResponse` | ~153 |
| `/api/v1/groups/{group_id}` | GET | GroupDetailResponse | `@router.get("/{group_id}", response_model=GroupDetailResponse` | ~241 |
| `/api/v1/groups/{group_id}` | PUT | GroupUpdateResponse | `@router.put("/{group_id}", response_model=GroupUpdateResponse` | ~316 |
| `/api/v1/groups/{group_id}` | DELETE | None (204) | `@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT` | ~411 |
| `/api/v1/groups/{group_id}/reorder` | PUT | GroupReorderResponse | `@router.put("/{group_id}/reorder", response_model=GroupReorderResponse` | ~466 |
| `/api/v1/groups/{group_id}/artifacts` | POST | GroupAddArtifactResponse | `@router.post("/{group_id}/artifacts", response_model=GroupAddArtifactResponse` | ~560 |
| `/api/v1/groups/{group_id}/artifacts/{artifact_id}` | DELETE | None (204) | `@router.delete("/{group_id}/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT` | ~683 |
| `/api/v1/groups/{group_id}/artifacts/reorder` | PUT | ArtifactReorderResponse | `@router.put("/{group_id}/artifacts/reorder", response_model=ArtifactReorderResponse` | ~752 |
| `/api/v1/groups/{group_id}/move` | POST | GroupMoveResponse | `@router.post("/{group_id}/move", response_model=GroupMoveResponse` | ~849 |

## Cache API

**Router**: `skillmeat/api/routers/cache.py`
**Base**: `/api/v1/cache`

| Endpoint | Method | Response Model | Decorator Pattern | Lines |
|----------|--------|----------------|-------------------|-------|
| `/api/v1/cache/invalidate` | POST | CacheInvalidateResponse | `@router.post("/invalidate", response_model=CacheInvalidateResponse` | ~107 |
| `/api/v1/cache/stats` | GET | CacheStatsResponse | `@router.get("/stats", response_model=CacheStatsResponse` | ~178 |
| `/api/v1/cache/entries` | GET | CacheEntriesResponse | `@router.get("/entries", response_model=CacheEntriesResponse` | ~240 |
| `/api/v1/cache/entries/{key}` | GET | CacheEntryDetailResponse | `@router.get("/entries/{key}", response_model=CacheEntryDetailResponse` | ~341 |
| `/api/v1/cache/metadata` | GET | CacheMetadataResponse | `@router.get("/metadata", response_model=CacheMetadataResponse` | ~458 |
| `/api/v1/cache/github` | GET | GitHubCacheResponse | `@router.get("/github", response_model=GitHubCacheResponse` | ~635 |
| `/api/v1/cache/clear` | POST | CacheClearResponse | `@router.post("/clear", response_model=CacheClearResponse` | ~770 |
| `/api/v1/cache/size` | GET | CacheSizeResponse | `@router.get("/size", response_model=CacheSizeResponse` | ~840 |

## Analytics API

**Router**: `skillmeat/api/routers/analytics.py`
**Base**: `/api/v1/analytics`

| Endpoint | Method | Response Model | Decorator Pattern | Lines |
|----------|--------|----------------|-------------------|-------|
| `/api/v1/analytics/usage` | GET | UsageAnalyticsResponse | `@router.get("/usage", response_model=UsageAnalyticsResponse` | ~97 |
| `/api/v1/analytics/deployments` | GET | DeploymentAnalyticsResponse | `@router.get("/deployments", response_model=DeploymentAnalyticsResponse` | ~209 |
| `/api/v1/analytics/artifacts` | GET | ArtifactAnalyticsResponse | `@router.get("/artifacts", response_model=ArtifactAnalyticsResponse` | ~380 |

## Health API

**Router**: `skillmeat/api/routers/health.py`
**Base**: `/health`

| Endpoint | Method | Response Model | Decorator Pattern | Lines |
|----------|--------|----------------|-------------------|-------|
| `/health` | GET | HealthResponse | `@router.get("", response_model=HealthResponse` | ~103 |
| `/health/ready` | GET | ReadinessResponse | `@router.get("/ready", response_model=ReadinessResponse` | ~133 |
| `/health/live` | GET | LivenessResponse | `@router.get("/live", response_model=LivenessResponse` | ~242 |
| `/health/version` | GET | VersionResponse | `@router.get("/version", response_model=VersionResponse` | ~276 |

## Key Distinctions

### Collections vs User Collections

| Feature | Collections API | User Collections API |
|---------|----------------|---------------------|
| Storage | File-based (~/.skillmeat/collection/) | Database (SQLAlchemy) |
| Operations | Read-only (GET) | Full CRUD (GET/POST/PUT/DELETE) |
| Pagination | No | Yes (limit/offset) |
| Artifact Association | No mutations | Yes (add/remove artifacts) |
| Groups | No | Yes (nested groups) |
| Status | Legacy/deprecated | Active/preferred |

### Pagination Patterns

**User Collections** (and other database-backed endpoints):
```python
# Query parameters
limit: int = Query(50, ge=1, le=100)  # Page size
offset: int = Query(0, ge=0)          # Skip count
```

**Artifacts** (cursor-based for some endpoints):
```python
# Query parameters
limit: int = Query(50, ge=1, le=100)
after: Optional[str] = Query(None)    # Cursor for next page
```

## Sync & Deployment Patterns

### Artifact Sync Endpoint (`POST /api/v1/artifacts/{artifact_id}/sync`)

**Purpose**: Pull changes from GitHub upstream or deployed project back to collection

**Request Body** (ArtifactSyncRequest):
```typescript
{
  project_path?: string;        // Optional: path to project for project sync
  force?: boolean;              // Optional: force sync despite conflicts
  strategy?: 'theirs' | 'ours' | 'manual';  // Conflict resolution strategy
}
```

**Response** (ArtifactSyncResponse):
```typescript
{
  success: boolean;
  message: string;
  artifact_name: string;
  artifact_type: string;
  conflicts?: ConflictInfo[] | null;
  updated_version?: string | null;
  synced_files_count?: number | null;
}
```

**Behavior**:
- If `project_path` omitted → syncs from GitHub upstream (requires GitHub origin)
- If `project_path` provided → syncs from deployed project files
- Empty body (`{}`) → defaults to upstream sync

**Cache Invalidation** (on success):
- `['upstream-diff', artifact_id, collection_name]`
- `['project-diff', artifact_id]`
- `['artifacts']`

### Artifact Deploy Endpoint (`POST /api/v1/artifacts/{artifact_id}/deploy`)

**Purpose**: Deploy artifact from collection to project's `.claude/` directory

**Request Body** (ArtifactDeployRequest):
```typescript
{
  project_path: string;    // Required: absolute path to project
  overwrite: boolean;      // Optional: force overwrite if exists (default: false)
}
```

**Response** (ArtifactDeployResponse):
```typescript
{
  success: boolean;
  message: string;
  artifact_name: string;
  artifact_type: string;
  deployed_path?: string;
  error_message?: string;
}
```

**Cache Invalidation** (on success):
- `['project-diff', artifact_id]`
- `['upstream-diff', artifact_id, collection_name]`
- `['artifacts']`
- `['deployments']`

### Diff Endpoints

**GET `/api/v1/artifacts/{artifact_id}/diff`**:
- **Params**: `artifact_id` (path), `project_path` (query, required)
- **Response**: ArtifactDiffResponse (collection vs deployed files)
- **Purpose**: Compare artifact in collection with deployed version in project

**GET `/api/v1/artifacts/{artifact_id}/upstream-diff`**:
- **Params**: `artifact_id` (path), `collection` (query, optional)
- **Response**: ArtifactUpstreamDiffResponse (collection vs GitHub upstream)
- **Purpose**: Compare artifact in collection with latest GitHub upstream version

### Web Client Usage (React/TanStack Query)

**Pull Changes** (from project to collection):
```typescript
const result = await pullChanges(projectPath, entityIds);
queryClient.invalidateQueries({ queryKey: ['context-sync-status'] });
queryClient.invalidateQueries({ queryKey: ['artifact-files'] });
queryClient.invalidateQueries({ queryKey: ['context-entities'] });
queryClient.invalidateQueries({ queryKey: ['deployments'] });
queryClient.invalidateQueries({ queryKey: ['upstream-diff', artifactId, collection] });
queryClient.invalidateQueries({ queryKey: ['project-diff', artifactId] });
```

**Push Changes** (from collection to project):
```typescript
const result = await pushChanges(projectPath, entityIds, overwrite);
// Same invalidation pattern as pull
```

**Artifact Sync** (upstream):
```typescript
const result = await apiRequest(`/artifacts/${artifactId}/sync`, {
  method: 'POST',
  body: JSON.stringify({})  // Empty body for upstream sync
});
queryClient.invalidateQueries({ queryKey: ['upstream-diff', artifactId, collection] });
queryClient.invalidateQueries({ queryKey: ['project-diff', artifactId] });
queryClient.invalidateQueries({ queryKey: ['artifacts'] });
```

**Artifact Deploy**:
```typescript
const result = await apiRequest(`/artifacts/${artifactId}/deploy`, {
  method: 'POST',
  body: JSON.stringify({
    project_path: projectPath,
    overwrite: false
  })
});
queryClient.invalidateQueries({ queryKey: ['project-diff', artifactId] });
queryClient.invalidateQueries({ queryKey: ['upstream-diff', artifactId, collection] });
queryClient.invalidateQueries({ queryKey: ['artifacts'] });
queryClient.invalidateQueries({ queryKey: ['deployments'] });
```

## Maintenance

### Verify Endpoint Patterns

```bash
# List all router decorators
grep -r "@router\." skillmeat/api/routers/*.py

# Check specific router
grep -A 3 "@router\." skillmeat/api/routers/context_sync.py

# Verify response models
grep "response_model=" skillmeat/api/routers/artifacts.py
```

### Update This File

When adding new endpoints:
1. Grep for new `@router.*` patterns in target file
2. Add to appropriate section with required parameters
3. Document cache invalidation keys from web client mutations
4. Update last_verified date
5. Run verification commands to confirm accuracy
