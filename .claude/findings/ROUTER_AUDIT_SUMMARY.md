# Enterprise Router Audit - Quick Reference

**Finding Date**: 2026-03-12
**Status**: Ready for implementation
**Impact**: 9 BROKEN endpoints, 8 RISKY endpoints

---

## BROKEN Endpoints (Fix Immediately)

| # | File | Endpoint/Function | Line(s) | Issue | Fix |
|---|------|------------------|---------|-------|-----|
| 1 | artifacts.py | resolve_collection_name() | 350-410 | Uses `list_collections()` | Switch to `CollectionRepoDep` |
| 2 | artifacts.py | _find_artifact_in_collections() | 410-471 | Filesystem enumeration | Switch to `ArtifactRepoDep` |
| 3 | artifacts.py | build_version_graph() | 600-667 | Loads filesystem manifest | Use `DbArtifactHistoryRepoDep` |
| 4 | artifacts.py | GET /discover | 1012-1098 | Filesystem scan only | Disable in enterprise |
| 5 | artifacts.py | GET /discover/projects | 1158-1219 | Filesystem scan only | Disable in enterprise |
| 6 | collections.py | GET /collections | 110-193 | DEPRECATED + broken | Return 410 Gone |
| 7 | collections.py | GET /collections/{id} | 224-291 | DEPRECATED + broken | Return 410 Gone |
| 8 | collections.py | GET /collections/{id}/artifacts | 296-390 | DEPRECATED + broken | Return 410 Gone |
| 9 | marketplace_sources.py | get_collection_artifact_keys() | 605-626 | Filesystem enumeration | Query `CollectionArtifact` table |

---

## RISKY Endpoints (Fix Before Release)

| # | File | Endpoint/Function | Line(s) | Issue | Mitigation |
|---|------|------------------|---------|-------|-----------|
| 10 | health.py | GET /health/detailed | 152-275 | CollectionManagerDep | Use `CollectionRepoDep` + DB count |
| 11 | health.py | GET /health/readiness | 278-310 | CollectionManagerDep | Edition-aware check |
| 12 | match.py | POST /match | 46-90 | Uses ArtifactManagerDep | Switch to `ArtifactRepoDep` |
| 13 | marketplace_sources.py | Multiple endpoints | 3023-4875 | Optional CollectionManagerDep | Edition-aware duplicate detection |
| 14 | mcp.py | Multiple endpoints | 81-612 | Filesystem-scoped | Migrate to DB or disable |
| 15 | tags.py | GET /tags/slugs | 474-555 | CollectionManagerDep | Use `TagRepoDep` + DB query |
| 16 | tags.py | GET /tags/by-name | 595-660 | CollectionManagerDep | Use `TagRepoDep` + DB query |
| 17 | user_collections.py | Multiple endpoints | Various | Mixed read/write | Fix read operations |

---

## DI Replacement Reference

**Remove**:
```python
collection_mgr: CollectionManagerDep
artifact_mgr: ArtifactManagerDep
```

**Replace with** (based on operation):

| Operation | Use | Import |
|-----------|-----|--------|
| Read collections | `CollectionRepoDep` | Already in dependencies.py |
| Read artifacts | `ArtifactRepoDep` | Already in dependencies.py |
| Read artifact history | `DbArtifactHistoryRepoDep` | Already in dependencies.py |
| Read tags | `TagRepoDep` | Already in dependencies.py |
| Read deployments | `DeploymentRepoDep` | Already in dependencies.py |
| Write artifacts | `ArtifactManagerDep` (keep) + `refresh_single_artifact_cache()` | Already in dependencies.py |
| Write deployments | `ArtifactManagerDep` (keep) + `refresh_single_artifact_cache()` | Already in dependencies.py |

---

## Edition-Aware Pattern

**For optional/conditional logic**:

```python
from skillmeat.api.config import get_settings

@router.get("/endpoint")
async def my_endpoint(
    settings: SettingsDep,
    collection_repo: CollectionRepoDep,
    collection_mgr: Optional[CollectionManagerDep] = None,
):
    if settings.edition == "enterprise":
        # Use DB repos
        data = collection_repo.list()
    else:
        # Use managers
        data = collection_mgr.list_collections()
    return data
```

**For fully incompatible features**:

```python
if settings.edition == "enterprise":
    raise HTTPException(status_code=501, detail="Feature not available in enterprise")
```

---

## Testing Enterprise Mode

**Enable enterprise in test**:

```bash
export SKILLMEAT_EDITION=enterprise
# Set up PostgreSQL connection
uvicorn skillmeat.api.server:app --reload
```

**Test checklist**:
1. All 9 BROKEN endpoints return proper errors
2. All 8 RISKY endpoints work with DB data
3. collections.py endpoints return 410 Gone
4. discovery endpoints disabled or fail gracefully
5. health checks report correct status
6. No AttributeError on filesystem access

---

## Code References

**Available repos in DI** (from dependencies.py):
- `ArtifactRepoDep` - IArtifactRepository
- `CollectionRepoDep` - ICollectionRepository
- `DeploymentRepoDep` - IDeploymentRepository
- `TagRepoDep` - ITagRepository
- `ProjectRepoDep` - IProjectRepository
- `SettingsRepoDep` - ISettingsRepository
- `GroupRepoDep` - IGroupRepository
- `ContextEntityRepoDep` - IContextEntityRepository
- `DbArtifactHistoryRepoDep` - IDbArtifactHistoryRepository
- `DbCollectionArtifactRepoDep` - IDbCollectionArtifactRepository
- `DbUserCollectionRepoDep` - IDbUserCollectionRepository

**DB session** (per-request):
- `DbSessionDep` - SQLAlchemy Session

**Write-through pattern** (for mutations):
```python
from skillmeat.api.services import refresh_single_artifact_cache

# After filesystem write:
await refresh_single_artifact_cache(artifact_id, session)
```

---

## Related Documentation

- **Full Audit**: `.claude/findings/ENTERPRISE_ROUTER_AUDIT.md`
- **Router Patterns**: `.claude/context/key-context/router-patterns.md`
- **Repository Architecture**: `.claude/context/key-context/repository-architecture.md`
- **Auth Architecture**: `.claude/context/key-context/auth-architecture.md`

---

## Implementation Order

### Phase 1: Critical Blockers (Block deployment)
1. collections.py (3 endpoints) - Return 410
2. artifacts.py utility functions (3 functions) - Fix resolve/find/version
3. marketplace_sources get_collection_artifact_keys() - Fix duplicate detection

### Phase 2: Health/Safety (Before release)
4. health.py (2 endpoints) - Edition-aware
5. artifacts.py discovery endpoints (2 endpoints) - Disable or provide alternative

### Phase 3: Feature Parity (Next sprint)
6. match.py - Use ArtifactRepoDep
7. mcp.py - Migrate or disable
8. marketplace_sources - Edition-aware filtering
9. tags.py - DB queries
10. user_collections.py - Fix read operations

---

## Questions to Answer Before Fixing

1. **Collections Router**: Should collections.py be completely removed, or just return 410?
2. **Discovery**: Is artifact discovery even a valid operation in enterprise? Or should it be disabled?
3. **MCP**: Should MCP servers be migrated to DB tables in enterprise schema?
4. **Project Artifacts**: Are project-scoped artifacts needed in enterprise, or only user collections?

These will determine exact implementation approach.
