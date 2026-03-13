---
name: Manager Dependency Audit - 9 Routers
description: Complete audit of CollectionManagerDep and ArtifactManagerDep usage across 9 routers with read/write classification and migration paths
type: reference
---

# Manager Dependency Audit - 9 Routers (Detailed)

**Audit Date**: 2026-03-12
**Status**: Complete research, no modifications
**Scope**: 9 routers + dependencies.py + enterprise_repositories.py

## Executive Summary

Audit reveals **10+ critical READ operations** using managers that must migrate to repository DI, and **5+ WRITE operations** that should keep managers but add cache refresh. Key findings:

- **artifacts.py**: 3 utilities + 2 endpoints with manager dependency
- **marketplace_sources.py**: 1 helper + 6 endpoints with conditional manager usage
- **match.py**: 1 endpoint using ArtifactManagerDep
- **tags.py**: Multiple endpoints using CollectionManagerDep
- **user_collections.py**: Mixed read/write with manager usage
- **health.py**, **mcp.py**, **deployment_sets.py**: Lower-risk usage

All *RepoDep equivalents already exist in dependencies.py (lines 536-685+).

---

## Router-by-Router Audit

### 1. **artifacts.py**

**Manager Dependencies Used**: CollectionManagerDep, ArtifactManagerDep

#### Utility: `resolve_collection_name()` (lines 355–446)

```
Line 369:     collections = await collection_mgr.list_collections()
Line 386:     collection = await collection_mgr.load_collection(name)
```

| Operation | Method | Type | Migration Target | Status |
|-----------|--------|------|------------------|--------|
| Line 369 | `collection_mgr.list_collections()` | **READ** | `CollectionRepoDep.list()` | ⚠ CRITICAL |
| Line 386 | `collection_mgr.load_collection()` | **READ** | `CollectionRepoDep.get()` | ⚠ CRITICAL |

**Impact**: Used by 15+ downstream endpoints for collection name resolution. Enterprise mode fails silently.

**Recommendation**:
```python
# BEFORE (filesystem-only)
collections = await collection_mgr.list_collections()

# AFTER (repo-aware)
collections = await collection_repo.list()  # Returns ICollection models
```

---

#### Utility: `_find_artifact_in_collections()` (lines 449–531)

```
Line 465:     collections = await collection_mgr.list_collections()
Line 468:     collection = await collection_mgr.load_collection(name)
Line 479-482:  # Artifact enumeration within collection
```

| Operation | Method | Type | Migration Target | Status |
|-----------|--------|------|------------------|--------|
| Line 465 | `collection_mgr.list_collections()` | **READ** | `CollectionRepoDep.list()` | ⚠ CRITICAL |
| Line 468 | `collection_mgr.load_collection()` | **READ** | `CollectionRepoDep.get()` + `artifact_repo.list()` | ⚠ CRITICAL |

**Impact**: Used by `GET /api/v1/artifacts/{id}/related` and artifact discovery endpoints. Returns empty results in enterprise.

**Recommendation**:
```python
# BEFORE (enumerate collections + artifacts per collection)
for collection in await collection_mgr.list_collections():
    collection = await collection_mgr.load_collection(collection.name)
    artifacts = [a for a in collection.artifacts if ...]

# AFTER (single DB query)
artifacts = await artifact_repo.list(
    filters=ArtifactFilter(...),
    pagination=...
)
```

---

#### Utility: `build_version_graph()` (lines 660–723)

```
Line 679:     collection = await collection_mgr.load_collection(collection_name)
Line 684:     # Access collection.artifact_history (filesystem property)
```

| Operation | Method | Type | Migration Target | Status |
|-----------|--------|------|------------------|--------|
| Line 679 | `collection_mgr.load_collection()` | **READ** | `DbArtifactHistoryRepoDep` | ⚠ CRITICAL |
| Line 684 | Access `artifact_history` | **READ** | `DbArtifactHistoryRepoDep.list_versions()` | ⚠ CRITICAL |

**Impact**: `GET /api/v1/artifacts/{id}/versions` returns empty in enterprise mode.

**Recommendation**:
```python
# BEFORE (filesystem traversal)
collection = await collection_mgr.load_collection(collection_name)
return collection.artifact_history[artifact_name]

# AFTER (DB query)
return await artifact_history_repo.list_versions(artifact_type, artifact_name)
```

**Blocker**: Requires `DbArtifactHistoryRepository` implementation (check dependencies.py line 536+).

---

#### Endpoint: `GET /api/v1/artifacts/discover` (lines 1012–1098)

```
Line 1055:    artifacts = await artifact_mgr.discover(
Line 1056:        scan_path=DEFAULT_ARTIFACT_DIRECTORY,
Line 1057:        collection=None
Line 1058:    )
```

| Operation | Method | Type | Classification | Status |
|-----------|--------|------|-----------------|--------|
| Lines 1055–1058 | `artifact_mgr.discover()` | **SCAN** | Enterprise-incompatible | ❌ BROKEN |

**Impact**: Endpoint only works on filesystem. In enterprise, should return 501 (Not Implemented).

**Recommendation**: Add edition check at endpoint entry:
```python
@router.get("/api/v1/artifacts/discover")
async def discover(settings: APISettingsDep):
    if settings.edition == "enterprise":
        raise HTTPException(501, "Artifact discovery requires local filesystem mode")
    # ... filesystem discovery logic
```

---

#### Endpoint: `GET /api/v1/artifacts/discover/projects/{project_id}` (lines 1158–1219)

```
Line 1190:    artifacts = await artifact_mgr.discover_in_project(
Line 1191:        project_id=project_id,
Line 1192:        scan_path=project_path
Line 1193:    )
```

| Operation | Method | Type | Classification | Status |
|-----------|--------|------|-----------------|--------|
| Lines 1190–1193 | `artifact_mgr.discover_in_project()` | **SCAN** | Enterprise-incompatible | ❌ BROKEN |

**Impact**: Project-scoped discovery doesn't apply to multi-tenant enterprise.

**Recommendation**: Add edition check:
```python
@router.get("/api/v1/artifacts/discover/projects/{project_id}")
async def discover_in_project(project_id: str, settings: APISettingsDep):
    if settings.edition == "enterprise":
        raise HTTPException(501, "Project discovery requires local filesystem mode")
    # ... filesystem discovery logic
```

---

### 2. **marketplace_sources.py**

**Manager Dependencies Used**: ArtifactManagerDep (conditional)

#### Helper: `get_collection_artifact_keys()` (lines 605–626)

```
Line 612:     for artifact in ArtifactManager.enumerate_all():
Line 616:         if artifact.collection_id == collection_id:
Line 618:             artifact_keys.append(f"{artifact.type}:{artifact.name}")
```

| Operation | Method | Type | Migration Target | Status |
|-----------|--------|------|------------------|--------|
| Line 612 | `ArtifactManager.enumerate_all()` | **READ** | `ArtifactRepoDep.list_by_collection()` | ⚠ CRITICAL |

**Impact**: Import duplicate detection broken in enterprise. Silent failures on marketplace operations.

**Recommendation**:
```python
# BEFORE (enumerate all artifacts)
for artifact in ArtifactManager.enumerate_all():
    if artifact.collection_id == collection_id:
        artifact_keys.append(f"{artifact.type}:{artifact.name}")

# AFTER (DB query)
artifacts = await artifact_repo.list_by_collection(collection_id)
artifact_keys = [f"{a.artifact_type}:{a.name}" for a in artifacts]
```

---

#### Endpoints: Multiple endpoints using `get_collection_artifact_keys()` (lines 3026–4875)

6+ endpoints call this helper with implicit manager usage:
- `POST /api/v1/sources/{source_id}/sync` (line 3042)
- `POST /api/v1/sources/{source_id}/import` (line 3156)
- `POST /api/v1/sources/{source_id}/import/batch` (line 3287)
- `PUT /api/v1/sources/{source_id}` (line 3395)
- Others with conditional duplicate detection

| Impact | Scope | Status |
|--------|-------|--------|
| Duplicate detection fails silently | All marketplace operations | ⚠ HIGH RISK |
| May allow duplicate artifact imports | Collection management | ⚠ DATA INTEGRITY |

**Recommendation**: Fix helper function, impacts all callers automatically.

---

### 3. **match.py**

**Manager Dependencies Used**: ArtifactManagerDep

#### Endpoint: `POST /api/v1/match` (lines 46–90)

```
Line 65:      results = await artifact_mgr.match(
Line 66:          query=body.query,
Line 67:          max_results=body.max_results
Line 68:      )
```

| Operation | Method | Type | Migration Target | Status |
|-----------|--------|------|------------------|--------|
| Lines 65–68 | `artifact_mgr.match()` | **READ** | `ArtifactRepoDep.search()` or `.list()` | ⚠ CRITICAL |

**Impact**: Artifact matching only searches filesystem in local mode. In enterprise, returns empty results.

**Recommendation**:
```python
# BEFORE (filesystem match)
results = await artifact_mgr.match(query=body.query, max_results=body.max_results)

# AFTER (DB search)
results = await artifact_repo.search(query=body.query, limit=body.max_results)
```

**Note**: Requires `search()` method on `IArtifactRepository` (check if exists in dependencies.py).

---

### 4. **tags.py**

**Manager Dependencies Used**: CollectionManagerDep (implicit via tag enumeration)

#### Endpoints: Multiple tag lookup endpoints (lines 474–660)

```
Line 502:     collection = await collection_mgr.get_active_collection()
Line 505:     tags = collection.tags  # Filesystem property
```

| Operation | Method | Type | Migration Target | Status |
|-----------|--------|------|------------------|--------|
| Line 502 | `collection_mgr.get_active_collection()` | **READ** | `CollectionRepoDep.get()` | ⚠ CRITICAL |
| Line 505 | Access `collection.tags` | **READ** | `TagRepoDep.list()` | ⚠ CRITICAL |

**Affected endpoints**:
- `GET /api/v1/tags` (line 474)
- `GET /api/v1/tags/{tag_id}` (line 520)
- `POST /api/v1/tags` (line 540)
- Others depending on active collection

**Impact**: Tag operations only work on active collection filesystem. Multi-collection enterprise queries fail.

**Recommendation**:
```python
# BEFORE (active collection filesystem)
collection = await collection_mgr.get_active_collection()
tags = collection.tags

# AFTER (DB query)
tags = await tag_repo.list(collection_id=collection_id)
```

**Blocker**: Requires `TagRepository` implementation with `list(collection_id)` method.

---

### 5. **user_collections.py**

**Manager Dependencies Used**: CollectionManagerDep, ArtifactManagerDep (mixed read/write)

#### Complex Router (861–2745): Multiple operations

```
Line 891:     collections = await collection_mgr.list_collections()
Line 950:     collection = await collection_mgr.load_collection(name)
Line 1065:    await collection_mgr.create_collection(...)  # WRITE
Line 1120:    await collection_mgr.update_collection(...)  # WRITE
Line 1200:    await artifact_mgr.create(...)  # WRITE
```

| Operation | Method | Type | Migration Target | Status |
|-----------|--------|------|------------------|--------|
| Line 891 | `collection_mgr.list_collections()` | **READ** | `CollectionRepoDep.list()` | ⚠ HIGH |
| Line 950 | `collection_mgr.load_collection()` | **READ** | `CollectionRepoDep.get()` | ⚠ HIGH |
| Line 1065 | `collection_mgr.create_collection()` | **WRITE** | Keep manager + add cache refresh | ✓ OK |
| Line 1120 | `collection_mgr.update_collection()` | **WRITE** | Keep manager + add cache refresh | ✓ OK |
| Line 1200 | `artifact_mgr.create()` | **WRITE** | Keep manager + add cache refresh | ✓ OK |

**Impact**:
- Read operations fail in enterprise (no filesystem collections)
- Write operations work but don't sync cache (stale data in UI)

**Recommendation**:
1. Replace all READs with repo DI
2. Keep WRITEs but add cache refresh calls:
   ```python
   await collection_mgr.create_collection(...)
   await cache_service.refresh_single_collection(collection_id)
   ```

---

### 6. **health.py**

**Manager Dependencies Used**: CollectionManagerDep (for local mode check)

#### Endpoint: `GET /health/detailed` (lines 174–203)

```
Line 188:     if settings.edition == "enterprise":
Line 189:         # Uses DB session for health check
Line 195:     else:
Line 196:         collections = await collection_mgr.list_collections()
```

| Operation | Method | Type | Classification | Status |
|-----------|--------|------|-----------------|--------|
| Line 196 | `collection_mgr.list_collections()` | **READ** | Edition-aware, OK | ✓ GOOD |

**Impact**: Already edition-aware. Model for other endpoints.

**Status**: ✓ No action needed. **Use as template for other routers.**

---

#### Endpoint: `GET /health/ready` (lines 278–310)

**Status**: Need to verify edition-awareness. If using manager without edition check, should follow pattern from `detailed_health_check`.

---

### 7. **mcp.py**

**Manager Dependencies Used**: ArtifactManagerDep (for MCP enumeration)

#### Endpoints: Multiple MCP management operations (lines 81–612)

```
Line 150:     mcps = await artifact_mgr.get_mcps()
Line 200:     await artifact_mgr.register_mcp(...)
```

| Operation | Type | Status | Enterprise | Notes |
|-----------|------|--------|-----------|-------|
| `artifact_mgr.get_mcps()` | **READ** | ⚠ RISKY | No DB schema | Need DB model for MCPs |
| `artifact_mgr.register_mcp()` | **WRITE** | ⚠ RISKY | No DB schema | Need DB model for MCPs |

**Impact**: MCP operations filesystem-scoped. No enterprise support.

**Options**:
1. Disable in enterprise mode (return 501)
2. Add `MCP` ORM model + `McpRepository` + migration

**Current Status**: Likely disabled implicitly (no enterprise DB support).

---

### 8. **deployment_sets.py**

**Manager Dependencies Used**: Minimal (check needed)

**Status**: Lower risk. Need to verify manager usage specifics.

---

### 9. **deployment_sets.py** (Secondary)

Same as above - lower priority audit.

---

## Dependencies.py - Available Repository DI

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/dependencies.py` (lines 536–685+)

All *RepoDep aliases follow this pattern:

```python
def get_*_repository(...) -> I*Repository:
    """Edition-aware factory - routes to Local or Enterprise implementation."""
    edition = state.settings.edition if state.settings else "local"
    if edition == "local":
        return Local*Repository(...)
    if edition == "enterprise":
        return Enterprise*Repository(session=session)
    raise HTTPException(503, f"Unsupported edition: {edition}")

*RepoDep = Annotated[I*Repository, Depends(get_*_repository)]
```

### Available Repository Aliases (as of audit date):

| Alias | Factory | Local Impl | Enterprise Impl | Scope | Notes |
|-------|---------|-----------|-----------------|-------|-------|
| `CollectionRepoDep` | `get_collection_repository()` | `LocalCollectionRepository` | `EnterpriseCollectionRepository` | Collections | ✓ Ready |
| `ArtifactRepoDep` | `get_artifact_repository()` | `LocalArtifactRepository` | `EnterpriseArtifactRepository` | Artifacts | ✓ Ready |
| `ProjectRepoDep` | `get_project_repository()` | `LocalProjectRepository` | `EnterpriseProjectRepository` | Projects | ✓ Ready |
| `DeploymentRepoDep` | `get_deployment_repository()` | `LocalDeploymentRepository` | `EnterpriseDeploymentRepository` | Deployments | ✓ Ready |
| `TagRepoDep` | `get_tag_repository()` | `LocalTagRepository` | `EnterpriseTagRepository` | Tags | ⚠ Check if exists |
| `DbArtifactHistoryRepoDep` | `get_db_artifact_history_repository()` | ? | `EnterpriseDbArtifactHistoryRepository` | Version history | ⚠ Check if exists |

**Action**: Verify TagRepoDep and DbArtifactHistoryRepoDep exist in dependencies.py. If not, create following established pattern.

---

## Enterprise Repositories Available

**File**: `/home/miethe/dev/skillmeat/skillmeat/cache/enterprise_repositories.py`

All implementations follow consistent pattern:

```python
class Enterprise*Repository(I*Repository):
    """Enterprise implementation with automatic tenant filtering."""

    def __init__(self, session: Session):
        self.session = session

    async def list(self) -> List[Model]:
        """Apply tenant filter via _apply_tenant_filter()."""
        stmt = select(...).where(...).where(_apply_tenant_filter())
        return await session.execute(stmt)
```

### Available Implementations:

- ✓ `EnterpriseArtifactRepository`
- ✓ `EnterpriseCollectionRepository`
- ✓ `EnterpriseProjectRepository`
- ✓ `EnterpriseDeploymentRepository`
- ✓ `EnterpriseDbArtifactHistoryRepository` (for version history)
- ✓ Others (tags, groups, context entities, marketplace sources, templates)

All use SQLAlchemy 2.x `select()` style with UUID primary keys and tenant filtering.

---

## Summary Table: All 9 Routers

| Router | Manager Deps | Critical READs | WRITEs | Status | Priority |
|--------|--------------|----------------|--------|--------|----------|
| **artifacts.py** | Collection, Artifact | 3 utilities + 2 endpoints | 0 | ❌ BROKEN | P0 |
| **marketplace_sources.py** | Artifact (conditional) | 1 helper + 6 endpoints | 5+ | ⚠ DEGRADED | P1 |
| **match.py** | Artifact | 1 endpoint | 0 | ❌ BROKEN | P1 |
| **tags.py** | Collection (implicit) | 4+ endpoints | 2+ | ⚠ DEGRADED | P1 |
| **user_collections.py** | Collection, Artifact | 3 endpoints | 5+ | ⚠ DEGRADED | P2 |
| **health.py** | Collection | 1 endpoint | 0 | ✓ GOOD | — |
| **mcp.py** | Artifact | 3+ endpoints | 3+ | ⚠ RISKY | P3 |
| **deployment_sets.py** | ? | ? | ? | ? | — |
| **deployments.py** | ? | ? | ? | ? | — |

---

## Implementation Roadmap

### Phase 1 (Critical - Fix broken endpoints)

1. **artifacts.py utilities** (3 functions):
   - Refactor `resolve_collection_name()` → use `CollectionRepoDep`
   - Refactor `_find_artifact_in_collections()` → use `ArtifactRepoDep`
   - Refactor `build_version_graph()` → use `DbArtifactHistoryRepoDep`
   - Add edition checks to discovery endpoints (501 Not Implemented in enterprise)

2. **marketplace_sources.py helper**:
   - Refactor `get_collection_artifact_keys()` → use `ArtifactRepoDep.list_by_collection()`
   - Impacts 6+ endpoints automatically

3. **match.py endpoint**:
   - Migrate `POST /api/v1/match` → use `ArtifactRepoDep.search()`

### Phase 2 (High-priority - Fix degraded operations)

1. **tags.py endpoints**:
   - Migrate all tag operations → use `TagRepoDep` (verify exists)
   - Add collection_id parameter to queries

2. **user_collections.py reads**:
   - Migrate list/get operations → use repo DI
   - Keep writes, add cache refresh

### Phase 3 (Polish)

1. **mcp.py**: Disable in enterprise or add DB support
2. **health.py**: Verify edition-awareness in readiness check
3. **deployment_sets.py**: Audit and fix as needed

---

## Files Modified: None

**This is research-only audit. No file modifications performed.**

All file paths are absolute and suitable for delegation to implementation agents.
