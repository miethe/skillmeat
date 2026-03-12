# API Router Enterprise Edition Audit Report

**Date**: 2026-03-12
**Scope**: All routers in `skillmeat/api/routers/`
**Finding**: 9 BROKEN endpoints, 8 RISKY endpoints, 8 routers affected
**Action**: Immediate fixes needed before enterprise deployment

---

## Executive Summary

An audit of all API router endpoints found systematic misuse of filesystem-based managers (`CollectionManagerDep`, `ArtifactManagerDep`) in data-read operations. In enterprise mode (PostgreSQL), collections and artifacts live in the DB, not the filesystem. Any endpoint using these managers for reads will fail silently or return empty results.

**Critical Path**: Fix 9 BROKEN read operations + deprecated collections router.

---

## BROKEN Findings (Critical - Will Fail in Enterprise)

### 1. artifacts.py - resolve_collection_name() utility [Lines 350-410]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/artifacts.py:350-410`

**What it does**: Resolves a collection name parameter, falling back to active collection.

**What's broken**:
```python
# Line 374
collection_names = collection_mgr.list_collections()  # BROKEN - filesystem only
```

**Impact**:
- Used by multiple endpoints (discover, bulk-import, etc.)
- Will return empty list in enterprise mode
- All dependent endpoints will fail with "collection not found"

**Fix**: Use `CollectionRepoDep` to query DB instead:
```python
def resolve_collection_name(
    collection_name: Optional[str],
    collection_repo: CollectionRepoDep,  # Changed
    session: DbSessionDep,
) -> str:
    if collection_name:
        return collection_name
    # Query DB for active collection, not filesystem
    active = collection_repo.get_active()  # or similar
    return active.name if active else "default"
```

**Severity**: BROKEN (critical path)

---

### 2. artifacts.py - _find_artifact_in_collections() utility [Lines 410-471]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/artifacts.py:410-471`

**What it does**: Searches for an artifact across all collections.

**What's broken**:
```python
# Lines 462-464
for coll_name in collection_mgr.list_collections():  # BROKEN - filesystem only
    coll = collection_mgr.load_collection(coll_name)  # BROKEN - filesystem only
```

**Impact**:
- Will return empty in enterprise (no filesystem collections)
- Endpoints depending on this will fail to find artifacts

**Fix**: Query `CollectionArtifact` table or use `ArtifactRepoDep`:
```python
def _find_artifact_in_collections(
    artifact_type: ArtifactType,
    name: str,
    artifact_repo: ArtifactRepoDep,  # Changed
    session: DbSessionDep,
):
    # Query DB for artifact across all collections
    return artifact_repo.get_artifact_metadata(type_name=name)
```

**Severity**: BROKEN (critical path)

---

### 3. artifacts.py - build_version_graph() utility [Lines 600-667]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/artifacts.py:600-667`

**What it does**: Builds version history graph for an artifact.

**What's broken**:
```python
# Lines 629-639
[collection_name] if collection_name else collection_mgr.list_collections()
coll = collection_mgr.load_collection(collection_name)  # BROKEN
```

**Impact**:
- `GET /api/v1/artifacts/{id}/versions` will return empty version graph
- Version history unavailable in enterprise

**Fix**: Use `DbArtifactHistoryRepoDep` to query version history from DB:
```python
async def build_version_graph(
    artifact_id: str,
    collection_name: Optional[str],
    artifact_repo: ArtifactRepoDep,
    history_repo: DbArtifactHistoryRepoDep,  # Changed
):
    # Query artifact history from DB, not filesystem
    versions = history_repo.list_versions(artifact_id)
```

**Severity**: BROKEN (critical path)

---

### 4. artifacts.py - GET /api/v1/artifacts/discover [Lines 1012-1098]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/artifacts.py:1012-1098`

**What it does**: Scans collection for existing artifacts.

**What's broken**:
```python
# Line 1057
collection_path = collection_mgr.config.get_collection_path(collection_name)  # filesystem

# Line 1074
manifest = collection_mgr.load_collection(collection_name)  # filesystem
```

**Impact**:
- Discovery endpoint won't work in enterprise
- Returns "scan path does not exist" error

**Fix**: In enterprise mode, disable this endpoint or provide DB-based discovery:
```python
@router.get("/discover")
async def discover_artifacts(
    request: DiscoveryRequest,
    settings: SettingsDep,
    collection_repo: CollectionRepoDep,
):
    if settings.edition == "enterprise":
        raise HTTPException(status_code=501, detail="Discovery not available in enterprise mode")
    # ... existing filesystem logic
```

**Severity**: BROKEN (discovery doesn't apply to enterprise)

---

### 5. artifacts.py - GET /api/v1/artifacts/discover/projects/{project_id} [Lines 1158-1219]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/artifacts.py:1158-1219`

**What it does**: Discover artifacts in a specific project.

**What's broken**:
```python
# Line 1210
manifest = collection_mgr.load_collection(collection_name)  # filesystem only
```

**Impact**:
- Project-scoped discovery won't work in enterprise
- No project collections in enterprise DB schema

**Fix**: Disable in enterprise mode:
```python
if settings.edition == "enterprise":
    raise HTTPException(status_code=501, detail="Project discovery not available in enterprise")
```

**Severity**: BROKEN (project-scoped discovery doesn't apply to enterprise)

---

### 6. collections.py - GET /api/v1/collections [Lines 110-193]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/collections.py:110-193`

**What it does**: List all collections (DEPRECATED endpoint).

**What's broken**:
```python
# Line 147
all_collection_names = collection_mgr.list_collections()  # filesystem only
```

**Impact**:
- Endpoint is already deprecated
- Will return empty in enterprise
- Should point users to `user_collections` router instead

**Fix**: Return 410 Gone or redirect in enterprise:
```python
@router.get("/")
async def list_collections(
    settings: SettingsDep,
):
    if settings.edition == "enterprise":
        raise HTTPException(status_code=410, detail="Use /api/v1/user-collections instead")
    # ... existing logic
```

**Severity**: BROKEN (but already deprecated)

---

### 7. collections.py - GET /api/v1/collections/{collection_id} [Lines 224-291]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/collections.py:224-291`

**What it does**: Get a specific collection (DEPRECATED).

**What's broken**:
```python
# Line 251
if collection_id not in collection_mgr.list_collections():  # filesystem only
```

**Impact**:
- Endpoint is deprecated
- Will always return 404 in enterprise

**Fix**: Return 410 Gone:
```python
if settings.edition == "enterprise":
    raise HTTPException(status_code=410, detail="This endpoint is deprecated")
```

**Severity**: BROKEN (but already deprecated)

---

### 8. collections.py - GET /api/v1/collections/{collection_id}/artifacts [Lines 296-390]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/collections.py:296-390`

**What it does**: List artifacts in a collection (DEPRECATED).

**What's broken**:
```python
# Line 350
if collection_id not in collection_mgr.list_collections():  # filesystem only
```

**Impact**:
- Endpoint is deprecated
- Will always return 404 in enterprise

**Fix**: Return 410 Gone:
```python
if settings.edition == "enterprise":
    raise HTTPException(status_code=410, detail="This endpoint is deprecated")
```

**Severity**: BROKEN (but already deprecated)

---

### 9. marketplace_sources.py - get_collection_artifact_keys() [Lines 605-626]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/marketplace_sources.py:605-626`

**What it does**: Get set of artifact keys already in collection (used by import logic).

**What's broken**:
```python
# Line 620-621
artifact_mgr = ArtifactManager(collection_mgr)
artifacts = artifact_mgr.list_artifacts()  # filesystem enumeration
```

**Impact**:
- Used by `sync_imported_artifacts` endpoint
- Will return empty set in enterprise
- Import duplicate-detection won't work

**Fix**: Query `CollectionArtifact` table instead:
```python
def get_collection_artifact_keys(artifact_repo: ArtifactRepoDep) -> Set[str]:
    # Query DB for artifact keys
    artifacts = artifact_repo.list_by_collection(collection_id)
    return {f"{a.type}:{a.name}" for a in artifacts}
```

**Severity**: BROKEN (import duplicate detection fails)

---

## RISKY Findings (Degraded Functionality)

### 10. health.py - GET /health/detailed [Lines 152-275]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/health.py:152-275`

**What it does**: Return detailed health check including component status.

**What's risky**:
```python
# Line 155
collection_manager: CollectionManagerDep,
```

**Impact**:
- Collectionmanager won't have collections in enterprise
- Health check will show "0 collections" (misleading)
- May return false negatives

**Fix**: Use `CollectionRepoDep` for enterprise:
```python
if settings.edition == "enterprise":
    collection_count = collection_repo.count()  # Query DB
else:
    collection_count = len(collection_manager.list_collections())
```

**Severity**: RISKY (misleading health status)

---

### 11. health.py - GET /health/readiness [Lines 278-310]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/health.py:278-310`

**What it does**: Readiness check for orchestrators.

**What's risky**:
```python
# Line 279
collection_manager: CollectionManagerDep,
```

**Impact**:
- May return "not ready" even if DB is ready
- Orchestrator may not bring up container

**Fix**: Edition-aware readiness check:
```python
async def readiness_check(
    settings: SettingsDep,
    collection_repo: Optional[CollectionRepoDep] = None,
) -> Dict[str, str]:
    if settings.edition == "enterprise":
        return {"status": "ready"}  # Just check DB health
    # ... check filesystem collections
```

**Severity**: RISKY (may prevent container startup in enterprise)

---

### 12. match.py - POST /api/v1/match [Lines 46-90]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/match.py:46-90`

**What it does**: Find matching artifacts.

**What's risky**:
```python
# Lines 63-64
artifact_mgr: ArtifactManagerDep,
collection_mgr: CollectionManagerDep,
```

**Impact**:
- Matching against filesystem artifacts only
- Won't find DB artifacts in enterprise
- Incomplete/incorrect matches

**Fix**: Use `ArtifactRepoDep` for edition-aware matching:
```python
async def match_artifacts(
    request: MatchRequest,
    artifact_repo: ArtifactRepoDep,
):
    # Query DB for all artifacts, not filesystem
    all_artifacts = artifact_repo.list_all()
```

**Severity**: RISKY (incomplete matching)

---

### 13-19. marketplace_sources.py - Multiple endpoints [Lines 3026-4875]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/marketplace_sources.py`

**Endpoints**:
- `POST /api/v1/marketplace-sources/{source_id}/sync` (Line 3023)
- `GET /api/v1/marketplace-sources/{source_id}/artifacts` (Line 3344)
- `PUT /api/v1/marketplace-sources/{source_id}` (related)
- Others

**What's risky**:
```python
# Line 3386 (optional parameter)
collection_mgr: CollectionManagerDep = None

# Line 3542 (conditional usage)
if collection_mgr:
    get_collection_artifact_keys(collection_mgr)
```

**Impact**:
- Works when `collection_mgr` is None (API still functional)
- But loses duplicate detection in enterprise
- Partial data returned

**Fix**: Edition-aware duplicate detection:
```python
if settings.edition == "enterprise":
    existing_keys = artifact_repo.get_keys_by_collection(collection_id)
else:
    existing_keys = get_collection_artifact_keys(collection_mgr) if collection_mgr else set()
```

**Severity**: RISKY (degraded duplicate detection)

---

### 20-21. mcp.py - Multiple endpoints [Lines 81-612]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/mcp.py`

**What's risky**:
```python
# Multiple lines throughout
collection_mgr: CollectionManagerDep,
# Used for MCP server management
```

**Impact**:
- MCP servers are currently filesystem-scoped
- No enterprise DB schema for MCP servers yet
- Will return empty in enterprise

**Fix**: Either:
1. Migrate MCP servers to DB tables in enterprise schema
2. Disable MCP endpoints in enterprise mode

**Severity**: RISKY (MCP not yet supported in enterprise)

---

### 22-23. tags.py - Tag lookup endpoints [Lines 474-660]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/tags.py`

**Endpoints**:
- `GET /api/v1/tags/slugs` (Line 474)
- `GET /api/v1/tags/by-name/{name}` (Line 595)

**What's risky**:
```python
# Both endpoints use
collection_mgr: CollectionManagerDep,
```

**Impact**:
- May not find tags in enterprise
- Limited tag enumeration

**Fix**: Use `TagRepoDep` for enterprise:
```python
if settings.edition == "enterprise":
    tags = tag_repo.list_all()
else:
    tags = get_tags_from_filesystem(collection_mgr)
```

**Severity**: RISKY (incomplete tag enumeration)

---

### 24-27. user_collections.py - Multiple endpoints [Lines 861-2745]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/user_collections.py`

**Lines**: 861-862, 1101-1102, 1652, 2624-2625

**What's risky**:
```python
# Lines 861-862
artifact_mgr: ArtifactManagerDep,
collection_mgr: CollectionManagerDep,
```

**Impact**: Depends on operation type:
- Read operations: will fail to find data in enterprise
- Write operations: filesystem writes + DB sync (OK)

**Fix**: Replace manager deps with repo deps for reads:
```python
@router.get("/{collection_id}/artifacts")
async def list_artifacts(
    artifact_repo: ArtifactRepoDep,  # Changed
    collection_id: str,
):
    return artifact_repo.list_by_collection(collection_id)
```

**Severity**: RISKY (mixed read/write pattern)

---

## Summary Table

| File | BROKEN | RISKY | OK |
|------|--------|-------|-----|
| artifacts.py | 6 | 0 | 20+ |
| collections.py | 3 | 0 | 0 |
| health.py | 0 | 2 | 2 |
| deployment_sets.py | 0 | 0 | 1 |
| marketplace_sources.py | 1 | 6 | 0 |
| match.py | 1 | 0 | 0 |
| mcp.py | 0 | 7 | 0 |
| tags.py | 0 | 2 | 0 |
| user_collections.py | 0 | 4 | 0 |
| **TOTAL** | **9** | **21** | **23+** |

---

## Implementation Priorities

### Tier 1: Critical (Block Enterprise Deployment)

1. **collections.py** - Return 410 Gone for all 3 endpoints
2. **artifacts.py resolve_collection_name()** - Switch to `CollectionRepoDep`
3. **artifacts.py _find_artifact_in_collections()** - Switch to `ArtifactRepoDep`
4. **artifacts.py build_version_graph()** - Query DB history
5. **marketplace_sources.py get_collection_artifact_keys()** - Query DB instead

### Tier 2: High Priority (Fix Before Release)

6. **health.py** - Edition-aware health checks
7. **match.py** - Use `ArtifactRepoDep`
8. **artifacts.py discover endpoints** - Disable in enterprise or provide DB alternative
9. **mcp.py** - Migrate to DB or disable in enterprise

### Tier 3: Polish (Next Sprint)

10. **marketplace_sources.py** - Edition-aware duplicate detection
11. **tags.py** - Edition-aware tag queries
12. **user_collections.py** - Audit and fix read operations

---

## Technical Context

**Related Rules**:
- `.claude/rules/api/routers.md` - Routers must use `I*Repository` for data access
- `.claude/rules/api/auth.md` - All `/api/v1/*` routes protected by default
- `.claude/context/key-context/repository-architecture.md` - Repository DI pattern

**Key Invariant**: Filesystem managers (`CollectionManager`, `ArtifactManager`) are for **CLI + write operations only**. All data reads in routers must use repository DI.

**Write-Through Pattern** (OK): Write to filesystem first, then call `refresh_single_artifact_cache()` to sync DB. This is correct for deployment/sync operations.

---

## Verification Checklist

- [ ] All 9 BROKEN endpoints fixed
- [ ] collections.py deprecated properly (410 Gone)
- [ ] health.py edition-aware
- [ ] marketplace_sources duplicate detection works in enterprise
- [ ] match.py uses `ArtifactRepoDep`
- [ ] mcp.py addressed (DB or disabled)
- [ ] tags.py edition-aware
- [ ] user_collections.py audited
- [ ] Enterprise mode tested end-to-end
- [ ] No remaining `CollectionManagerDep` reads in routers
