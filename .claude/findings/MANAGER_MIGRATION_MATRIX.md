# Manager Migration Matrix - Quick Reference

**Audit Date**: 2026-03-12
**File**: For quick lookup of specific migrations needed

---

## artifacts.py Migration Summary

| Line | Function/Endpoint | Current Code | Migration Path | Priority |
|------|------------------|--------------|-----------------|----------|
| 369 | `resolve_collection_name()` | `collection_mgr.list_collections()` | `CollectionRepoDep.list()` | P0 |
| 386 | `resolve_collection_name()` | `collection_mgr.load_collection(name)` | `CollectionRepoDep.get(name)` | P0 |
| 465 | `_find_artifact_in_collections()` | `collection_mgr.list_collections()` | `CollectionRepoDep.list()` | P0 |
| 468 | `_find_artifact_in_collections()` | `collection_mgr.load_collection(name)` | `ArtifactRepoDep.list(filters)` | P0 |
| 679 | `build_version_graph()` | `collection_mgr.load_collection()` | `DbArtifactHistoryRepoDep.list_versions()` | P0 |
| 684 | `build_version_graph()` | Access `artifact_history` | `DbArtifactHistoryRepoDep.list_versions()` | P0 |
| 1055 | `GET /discover` | `artifact_mgr.discover()` | Add: `if edition=="enterprise": 501` | P0 |
| 1190 | `GET /discover/projects/{id}` | `artifact_mgr.discover_in_project()` | Add: `if edition=="enterprise": 501` | P0 |

---

## marketplace_sources.py Migration Summary

| Line | Function/Endpoint | Current Code | Migration Path | Priority |
|------|------------------|--------------|-----------------|----------|
| 612 | `get_collection_artifact_keys()` | `ArtifactManager.enumerate_all()` | `ArtifactRepoDep.list_by_collection()` | P1 |
| 3042–4875 | 6+ endpoints using helper | Via helper | Fix helper (cascades) | P1 |

---

## match.py Migration Summary

| Line | Function/Endpoint | Current Code | Migration Path | Priority |
|------|------------------|--------------|-----------------|----------|
| 65 | `POST /api/v1/match` | `artifact_mgr.match()` | `ArtifactRepoDep.search()` | P1 |

---

## tags.py Migration Summary

| Line | Function/Endpoint | Current Code | Migration Path | Priority |
|------|------------------|--------------|-----------------|----------|
| 502 | Tag endpoints | `collection_mgr.get_active_collection()` | `CollectionRepoDep.get()` | P1 |
| 505 | Tag endpoints | Access `collection.tags` | `TagRepoDep.list(collection_id)` | P1 |

---

## user_collections.py Migration Summary

| Line | Operation | Current Code | Migration Path | Priority |
|------|-----------|--------------|-----------------|----------|
| 891 | READ | `collection_mgr.list_collections()` | `CollectionRepoDep.list()` | P2 |
| 950 | READ | `collection_mgr.load_collection()` | `CollectionRepoDep.get()` | P2 |
| 1065 | WRITE | `collection_mgr.create_collection()` | Keep + add cache refresh | P2 |
| 1120 | WRITE | `collection_mgr.update_collection()` | Keep + add cache refresh | P2 |
| 1200 | WRITE | `artifact_mgr.create()` | Keep + add cache refresh | P2 |

---

## Repository DI Availability Matrix

| Repository | Alias | Status | Notes |
|-----------|-------|--------|-------|
| CollectionRepository | `CollectionRepoDep` | ✓ Ready | Has `.list()`, `.get()` |
| ArtifactRepository | `ArtifactRepoDep` | ✓ Ready | Has `.list()`, `.get()`, need verify: `.list_by_collection()`, `.search()` |
| ProjectRepository | `ProjectRepoDep` | ✓ Ready | As needed |
| DeploymentRepository | `DeploymentRepoDep` | ✓ Ready | As needed |
| TagRepository | `TagRepoDep` | ⚠ Verify | Need `.list(collection_id)` method |
| DbArtifactHistoryRepository | `DbArtifactHistoryRepoDep` | ⚠ Verify | Need `.list_versions(type, name)` method |

---

## Verification Checklist

Before starting implementation:

```bash
# 1. Verify DbArtifactHistoryRepository exists
grep -n "DbArtifactHistoryRepoDep\|get_db_artifact_history" \
  /home/miethe/dev/skillmeat/skillmeat/api/dependencies.py

# 2. Verify TagRepository exists
grep -n "TagRepoDep\|get_tag_repository" \
  /home/miethe/dev/skillmeat/skillmeat/api/dependencies.py

# 3. Check ArtifactRepository methods
grep -n "def list_by_collection\|def search" \
  /home/miethe/dev/skillmeat/skillmeat/core/interfaces/repositories.py

# 4. Verify all enterprise implementations
grep -n "class Enterprise.*Repository" \
  /home/miethe/dev/skillmeat/skillmeat/cache/enterprise_repositories.py
```

---

## Common Migration Pattern

### READ Operations (Manager → Repository)

```python
# BEFORE
async def some_endpoint(collection_mgr: CollectionManagerDep) -> List[Collection]:
    collections = await collection_mgr.list_collections()
    return collections

# AFTER
async def some_endpoint(collection_repo: CollectionRepoDep) -> List[Collection]:
    collections = await collection_repo.list()
    return collections
```

### WRITE Operations (Manager → Manager + Cache Refresh)

```python
# BEFORE
async def create_artifact(artifact_mgr: ArtifactManagerDep) -> Artifact:
    artifact = await artifact_mgr.create(...)
    return artifact

# AFTER
async def create_artifact(
    artifact_mgr: ArtifactManagerDep,
    cache_service: CacheServiceDep  # Add this
) -> Artifact:
    artifact = await artifact_mgr.create(...)
    await cache_service.refresh_single_artifact(artifact.id)  # Add this
    return artifact
```

### Edition-Aware Checks (Discovery Endpoints)

```python
# BEFORE
async def discover(artifact_mgr: ArtifactManagerDep) -> List[Artifact]:
    return await artifact_mgr.discover(...)

# AFTER
async def discover(
    artifact_mgr: ArtifactManagerDep,
    settings: APISettingsDep  # Add this
) -> List[Artifact]:
    if settings.edition == "enterprise":
        raise HTTPException(501, "Artifact discovery requires local filesystem mode")
    return await artifact_mgr.discover(...)
```

---

## Dependencies to Check

Before creating migrations, verify these exist and have required methods:

### In dependencies.py:

- `DbArtifactHistoryRepoDep` - for version history queries
- `TagRepoDep` - for tag lookups
- Methods on `ArtifactRepoDep`:
  - `list_by_collection(collection_id)` - used by marketplace_sources
  - `search(query)` - used by match endpoint

### In enterprise_repositories.py:

- `EnterpriseDbArtifactHistoryRepository` - with `list_versions()`
- `EnterpriseTagRepository` - with `list(collection_id)`

### Cache Service:

- `refresh_single_collection(collection_id)`
- `refresh_single_artifact(artifact_id)`

---

## Error Messages to Watch For

When migrating, expect these errors if dependencies missing:

```
ImportError: cannot import name 'DbArtifactHistoryRepoDep' from 'skillmeat.api.dependencies'
# → Need to create DbArtifactHistoryRepoDep factory in dependencies.py

AttributeError: 'EnterpriseArtifactRepository' has no attribute 'list_by_collection'
# → Need to add method to repository

TypeError: ... takes positional argument but ... positional arguments were given
# → Check method signature matches between Local and Enterprise implementations
```

---

## Files to Modify (Implementation Order)

### Phase 1 (Critical - 3 files)

1. `/home/miethe/dev/skillmeat/skillmeat/api/routers/artifacts.py`
   - Lines 369, 386, 465, 468, 679, 684, 1055, 1190

2. `/home/miethe/dev/skillmeat/skillmeat/api/routers/marketplace_sources.py`
   - Line 612

3. `/home/miethe/dev/skillmeat/skillmeat/api/routers/match.py`
   - Line 65

### Phase 2 (High-Priority - 2 files)

4. `/home/miethe/dev/skillmeat/skillmeat/api/routers/tags.py`
   - Lines 502, 505

5. `/home/miethe/dev/skillmeat/skillmeat/api/routers/user_collections.py`
   - Lines 891, 950, 1065, 1120, 1200

### Possibly Phase 3 (Depends on findings)

6. `/home/miethe/dev/skillmeat/skillmeat/api/routers/health.py`
   - Verify edition-awareness

7. `/home/miethe/dev/skillmeat/skillmeat/api/routers/mcp.py`
   - Decide: disable vs add DB support

---

## Related Architecture Files

For implementation context:

- **Router patterns**: `.claude/context/key-context/router-patterns.md`
- **Repository architecture**: `.claude/context/key-context/repository-architecture.md`
- **Data flow patterns**: `.claude/context/key-context/data-flow-patterns.md`
- **Auth architecture**: `.claude/context/key-context/auth-architecture.md`
- **Dependency rules**: `.claude/rules/api/routers.md`, `.claude/rules/api/auth.md`

---

## Testing Strategy

After migrations, verify:

1. Local mode: All endpoints work with filesystem collections
2. Enterprise mode: All endpoints work with DB collections
3. Cache freshness: After WRITE operations, UI sees updated data
4. Error handling: Edition-aware endpoints return 501 in incompatible mode

Example test:
```bash
# Local mode test
SKILLMEAT_EDITION=local pytest tests/test_artifacts.py::test_resolve_collection_name

# Enterprise mode test
SKILLMEAT_EDITION=enterprise pytest tests/test_artifacts.py::test_resolve_collection_name
```

---

**Last Updated**: 2026-03-12
**Status**: Ready for implementation delegation
