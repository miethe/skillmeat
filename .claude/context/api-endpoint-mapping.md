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
  - skillmeat/api/routers/analytics.py
  - skillmeat/api/routers/health.py
last_verified: 2025-12-13
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

| Endpoint | Method | Response Model | Decorator Pattern | Lines |
|----------|--------|----------------|-------------------|-------|
| `/api/v1/artifacts/install` | POST | ArtifactInstallResponse | `@router.post("/install", response_model=ArtifactInstallResponse` | ~482 |
| `/api/v1/artifacts/install/batch` | POST | BatchInstallResponse | `@router.post("/install/batch", response_model=BatchInstallResponse` | ~623 |
| `/api/v1/artifacts/uninstall` | POST | ArtifactUninstallResponse | `@router.post("/uninstall", response_model=ArtifactUninstallResponse` | ~722 |
| `/api/v1/artifacts/sync` | POST | SyncResponse | `@router.post("/sync", response_model=SyncResponse` | ~998 |
| `/api/v1/artifacts` | GET | ArtifactListResponse | `@router.get("", response_model=ArtifactListResponse` | ~1250 |
| `/api/v1/artifacts/search` | GET | ArtifactSearchResponse | `@router.get("/search", response_model=ArtifactSearchResponse` | ~1480 |
| `/api/v1/artifacts/{artifact_id}` | GET | ArtifactDetailResponse | `@router.get("/{artifact_id}", response_model=ArtifactDetailResponse` | ~1606 |
| `/api/v1/artifacts/{artifact_id}` | PUT | ArtifactUpdateResponse | `@router.put("/{artifact_id}", response_model=ArtifactUpdateResponse` | ~1772 |
| `/api/v1/artifacts/{artifact_id}/metadata` | PUT | ArtifactMetadataResponse | `@router.put("/{artifact_id}/metadata", response_model=ArtifactMetadataResponse` | ~1945 |
| `/api/v1/artifacts/{artifact_id}` | DELETE | None (204) | `@router.delete("/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT` | ~2178 |
| `/api/v1/artifacts/validate` | POST | ValidationResponse | `@router.post("/validate", response_model=ValidationResponse` | ~2291 |
| `/api/v1/artifacts/export` | POST | ExportResponse | `@router.post("/export", response_model=ExportResponse` | ~2441 |
| `/api/v1/artifacts/import` | POST | ImportResponse | `@router.post("/import", response_model=ImportResponse` | ~2802 |
| `/api/v1/artifacts/{artifact_id}/versions` | GET | VersionListResponse | `@router.get("/{artifact_id}/versions", response_model=VersionListResponse` | ~2901 |
| `/api/v1/artifacts/{artifact_id}/dependencies` | GET | DependencyListResponse | `@router.get("/{artifact_id}/dependencies", response_model=DependencyListResponse` | ~3042 |
| `/api/v1/artifacts/{artifact_id}/deploy-status` | GET | DeployStatusResponse | `@router.get("/{artifact_id}/deploy-status", response_model=DeployStatusResponse` | ~3382 |
| `/api/v1/artifacts/tags` | GET | TagListResponse | `@router.get("/tags", response_model=TagListResponse` | ~3790 |
| `/api/v1/artifacts/sources` | GET | SourceListResponse | `@router.get("/sources", response_model=SourceListResponse` | ~4025 |
| `/api/v1/artifacts/{artifact_id}/clone` | PUT | ArtifactCloneResponse | `@router.put("/{artifact_id}/clone", response_model=ArtifactCloneResponse` | ~4270 |
| `/api/v1/artifacts/{artifact_id}/fork` | POST | ArtifactForkResponse | `@router.post("/{artifact_id}/fork", response_model=ArtifactForkResponse` | ~4521 |
| `/api/v1/artifacts/{artifact_id}/snapshot` | DELETE | None (204) | `@router.delete("/{artifact_id}/snapshot", status_code=status.HTTP_204_NO_CONTENT` | ~4782 |
| `/api/v1/artifacts/metadata/github` | GET | MetadataFetchResponse | `@router.get("/metadata/github", response_model=MetadataFetchResponse)` | ~4991 |
| `/api/v1/artifacts/stats` | GET | ArtifactStatsResponse | `@router.get("/stats", response_model=ArtifactStatsResponse` | ~5112 |
| `/api/v1/artifacts/types` | GET | ArtifactTypesResponse | `@router.get("/types", response_model=ArtifactTypesResponse` | ~5151 |
| `/api/v1/artifacts/batch` | POST | BatchOperationResponse | `@router.post("/batch", response_model=BatchOperationResponse` | ~5213 |
| `/api/v1/artifacts/orphaned` | DELETE | CleanupResponse | `@router.delete("/orphaned", response_model=CleanupResponse` | ~5301 |
| `/api/v1/artifacts/cache` | DELETE | CacheClearResponse | `@router.delete("/cache", response_model=CacheClearResponse` | ~5383 |
| `/api/v1/artifacts/recent` | GET | RecentArtifactsResponse | `@router.get("/recent", response_model=RecentArtifactsResponse` | ~5463 |

**Key Operations**:
- Installation: `/install`, `/install/batch`, `/uninstall`
- Search & Browse: `/`, `/search`, `/{artifact_id}`
- Metadata: `/{artifact_id}/metadata`, `/metadata/github`
- Version Management: `/{artifact_id}/versions`, `/sync`
- Deployment: `/{artifact_id}/deploy-status`
- Maintenance: `/orphaned`, `/cache`, `/validate`

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

## Maintenance

### Verify Endpoint Patterns

```bash
# List all router decorators
grep -r "@router\." skillmeat/api/routers/*.py

# Check specific router
grep -A 3 "@router\." skillmeat/api/routers/user_collections.py

# Verify response models
grep "response_model=" skillmeat/api/routers/*.py
```

### Update This File

When adding new endpoints:
1. Grep for new `@router.*` patterns in target file
2. Add to appropriate section with decorator pattern
3. Update last_verified date
4. Run verification commands to confirm accuracy
