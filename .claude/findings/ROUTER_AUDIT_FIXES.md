# Enterprise Router Audit - Implementation Fixes

**Scope**: 9 BROKEN + 8 RISKY endpoints across 8 routers
**Estimated Effort**: 3-4 developer hours for Tier 1, additional 2-3 hours for Tier 2-3
**Blocking**: Yes - Enterprise deployment blocked until Tier 1 fixed

---

## Tier 1: Critical Fixes (Blocks Enterprise)

### Task 1.1: Fix artifacts.py - resolve_collection_name() [30 min]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/artifacts.py:350-410`

**Current code** (lines 370-380):
```python
def resolve_collection_name(
    collection: Optional[str],
    collection_mgr,
) -> str:
    """Resolve collection name parameter."""
    if collection:
        return collection

    # BROKEN: filesystem only
    try:
        config = collection_mgr.config
        return config.get_active_collection_name()
    except Exception:
        return "default"
```

**Fixed code**:
```python
def resolve_collection_name(
    collection: Optional[str],
    collection_repo: CollectionRepoDep,
    session: DbSessionDep,
) -> str:
    """Resolve collection name parameter."""
    if collection:
        return collection

    # Query DB for active collection
    try:
        active = collection_repo.get_active(session)  # or get DB method
        return active.name if active else "default"
    except Exception:
        return "default"
```

**Also update** function signature where called (lines matching resolve_collection_name pattern).

---

### Task 1.2: Fix artifacts.py - _find_artifact_in_collections() [45 min]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/artifacts.py:410-471`

**Current code** (lines 460-475):
```python
def _find_artifact_in_collections(
    artifact_type: ArtifactType,
    name: str,
    collection_mgr,
    db_session=None,
):
    """Find artifact across collections."""

    # BROKEN: filesystem only
    for coll_name in collection_mgr.list_collections():
        coll = collection_mgr.load_collection(coll_name)
        if artifact in coll.artifacts:
            return artifact

    return None
```

**Fixed code**:
```python
def _find_artifact_in_collections(
    artifact_type: ArtifactType,
    name: str,
    artifact_repo: ArtifactRepoDep,
    session: DbSessionDep,
) -> Optional[ArtifactDTO]:
    """Find artifact across collections."""

    # Query DB for artifact
    artifact = artifact_repo.get_by_name_and_type(
        artifact_type=artifact_type,
        name=name,
        session=session
    )
    return artifact
```

**Update all callers** of this function to pass new DI parameters.

---

### Task 1.3: Fix artifacts.py - build_version_graph() [1 hour]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/artifacts.py:600-667`

**Current code** (lines 626-642):
```python
async def build_version_graph(
    artifact_id: str,
    collection_name: Optional[str] = None,
    collection_mgr=None,
) -> VersionGraphResponse:
    """Build version history graph."""

    # BROKEN: filesystem enumeration
    collections_to_check = (
        [collection_name] if collection_name
        else collection_mgr.list_collections()
    )

    for coll_name in collections_to_check:
        coll = collection_mgr.load_collection(coll_name)
        # ... build graph from manifest
```

**Fixed code**:
```python
async def build_version_graph(
    artifact_id: str,
    artifact_repo: ArtifactRepoDep,
    history_repo: DbArtifactHistoryRepoDep,
    session: DbSessionDep,
) -> VersionGraphResponse:
    """Build version history graph from DB."""

    # Query DB for version history
    versions = history_repo.list_versions(artifact_id, session)

    # Build graph from DB versions
    graph = VersionGraphResponse(
        nodes=[
            VersionGraphNodeResponse(
                version=v.version,
                created_at=v.created_at,
                source=v.source,
            ) for v in versions
        ]
    )
    return graph
```

**Check if DbArtifactHistoryRepoDep exists**, if not create it or use appropriate DB query.

---

### Task 1.4: Fix collections.py - Return 410 for all 3 endpoints [20 min]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/collections.py`

**For all 3 endpoints** (list_collections, get_collection, list_collection_artifacts):

**Add at start of each function**:
```python
@router.get("/")
async def list_collections(
    settings: SettingsDep,
) -> Union[CollectionListResponse, ErrorResponse]:
    """List all collections (DEPRECATED)."""
    if settings.edition == "enterprise":
        raise HTTPException(
            status_code=410,
            detail="This endpoint is deprecated. Use GET /api/v1/user-collections instead.",
        )
    # ... existing filesystem logic
```

**Repeat for other 2 endpoints** with appropriate deprecation messages.

---

### Task 1.5: Fix marketplace_sources.py - get_collection_artifact_keys() [45 min]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/marketplace_sources.py:605-626`

**Current code**:
```python
def get_collection_artifact_keys(collection_mgr) -> Set[str]:
    """Get artifact keys from collection."""
    if not collection_mgr:
        return set()

    # BROKEN: filesystem enumeration
    artifact_mgr = ArtifactManager(collection_mgr)
    artifacts = artifact_mgr.list_artifacts()
    return {f"{a.type}:{a.name}" for a in artifacts}
```

**Fixed code**:
```python
def get_collection_artifact_keys(
    artifact_repo: ArtifactRepoDep,
    collection_id: uuid.UUID,
    session: DbSessionDep,
) -> Set[str]:
    """Get artifact keys from collection (DB-backed)."""
    if not collection_id:
        return set()

    # Query DB for artifacts
    artifacts = artifact_repo.list_by_collection(collection_id, session)
    return {f"{a.type}:{a.name}" for a in artifacts}
```

**Update all callers** of this function (e.g., sync_imported_artifacts at line 3023).

---

## Tier 2: High-Priority Fixes (Before Release)

### Task 2.1: Fix health.py - Edition-aware health checks [30 min]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/health.py:152-310`

**For both endpoints** (detailed_health_check, readiness_check):

**Current**:
```python
async def detailed_health_check(
    settings: SettingsDep,
    config_manager: ConfigManagerDep,
    collection_manager: CollectionManagerDep,  # WRONG
) -> DetailedHealthStatus:
    ...
    collection_count = len(collection_manager.list_collections())
```

**Fixed**:
```python
async def detailed_health_check(
    settings: SettingsDep,
    config_manager: ConfigManagerDep,
    collection_repo: Optional[CollectionRepoDep] = None,
    session: Optional[DbSessionDep] = None,
) -> DetailedHealthStatus:
    ...
    if settings.edition == "enterprise":
        collection_count = collection_repo.count(session) if session else 0
    else:
        # Use manager for local mode
        app_state = get_app_state()
        collection_count = len(app_state.collection_manager.list_collections())
```

---

### Task 2.2: Fix artifacts.py discovery endpoints [1 hour]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/artifacts.py:1012-1219`

**For both endpoints** (discover_artifacts, discover_project_artifacts):

**Add edition check at start**:
```python
@router.get("/discover")
async def discover_artifacts(
    request: DiscoveryRequest,
    settings: SettingsDep,
    ...
) -> DiscoveryResult:
    if settings.edition == "enterprise":
        raise HTTPException(
            status_code=501,
            detail="Artifact discovery is only available in local mode. "
                   "In enterprise, use the marketplace to import artifacts.",
        )

    # ... existing filesystem logic
```

---

### Task 2.3: Fix match.py - Use ArtifactRepoDep [45 min]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/match.py:46-90`

**Current**:
```python
@router.post("/")
async def match_artifacts(
    request: MatchRequest,
    artifact_mgr: ArtifactManagerDep,  # WRONG
    collection_mgr: CollectionManagerDep,  # WRONG
) -> SimilarArtifactsResponse:
    all_artifacts = artifact_mgr.list_artifacts()
```

**Fixed**:
```python
@router.post("/")
async def match_artifacts(
    request: MatchRequest,
    artifact_repo: ArtifactRepoDep,
    session: DbSessionDep,
    settings: SettingsDep,
) -> SimilarArtifactsResponse:
    # Query DB for all artifacts
    all_artifacts = artifact_repo.list_all(session)

    # ... rest of matching logic
```

---

## Tier 3: Polish (Next Sprint)

### Task 3.1: Fix mcp.py - Migrate or disable [2+ hours]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/mcp.py`

**Option A** (Simpler - Disable in enterprise):
- Add edition check at start of each endpoint
- Return 501 Not Implemented for enterprise

**Option B** (Full - Migrate to DB):
- Create MCP server models in `skillmeat/cache/models.py`
- Create `Mcp*Repository` interfaces in `core/interfaces/repositories.py`
- Implement repositories in `core/repositories/` and `cache/enterprise_repositories.py`
- Update endpoints to use repo DI

---

### Task 3.2: Fix marketplace_sources.py - Edition-aware filtering [1 hour]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/marketplace_sources.py:3344-3566`

**Update** `list_artifacts` and related endpoints to handle both modes:

```python
async def list_artifacts(
    source_id: str,
    settings: SettingsDep,
    artifact_repo: Optional[ArtifactRepoDep] = None,
    collection_mgr: Optional[CollectionManagerDep] = None,
):
    # ... list source artifacts

    if settings.edition == "enterprise":
        existing_keys = artifact_repo.get_keys_by_collection(...)
    else:
        existing_keys = (
            get_collection_artifact_keys(collection_mgr)
            if collection_mgr else set()
        )

    # Filter and return
```

---

### Task 3.3: Fix tags.py - DB queries [45 min]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/tags.py:474-660`

**For both endpoints**:

```python
@router.get("/slugs")
async def list_tag_slugs(
    settings: SettingsDep,
    tag_repo: Optional[TagRepoDep] = None,
    collection_mgr: Optional[CollectionManagerDep] = None,
):
    if settings.edition == "enterprise":
        tags = tag_repo.list_all(session) if tag_repo else []
    else:
        # Existing filesystem logic
        ...

    return {"slugs": [t.slug for t in tags]}
```

---

### Task 3.4: Audit user_collections.py [1+ hours]

**File**: `/home/miethe/dev/skillmeat/skillmeat/api/routers/user_collections.py`

**Process**:
1. Identify all function signatures with `ArtifactManagerDep` or `CollectionManagerDep`
2. For each, determine if operation is read or write
3. If read: Replace with appropriate `*RepoDep`
4. If write: Keep manager but add `refresh_single_artifact_cache()` call
5. Test both local and enterprise modes

---

## Testing Checklist

After implementing fixes:

```bash
# Test local mode (existing behavior)
export SKILLMEAT_EDITION=local
pytest skillmeat/api/tests/ -v -k "not enterprise"

# Test enterprise mode
export SKILLMEAT_EDITION=enterprise
export SKILLMEAT_DB_URL=postgresql://...
pytest skillmeat/api/tests/ -v -k "enterprise"

# Test deprecated endpoints
curl -X GET http://localhost:8080/api/v1/collections
# Should return 410 Gone

# Test fixed endpoints
curl -X GET http://localhost:8080/api/v1/artifacts/discover
# Should return 501 Not Implemented or DB-backed results
```

---

## Code Review Checklist

For each fix:

- [ ] No `collection_mgr.list_collections()` calls in routers
- [ ] No `artifact_mgr.list_artifacts()` calls in routers (except write operations)
- [ ] All reads use appropriate `*RepoDep` from DI
- [ ] All writes include `refresh_single_artifact_cache()` call
- [ ] Edition checks use `settings.edition` (not direct edition check)
- [ ] Deprecated endpoints return 410 Gone
- [ ] Error messages reference newer endpoints
- [ ] Tests cover both local and enterprise modes

---

## Verification Script

```bash
#!/bin/bash
# Quick verification of audit fixes

echo "Checking for remaining filesystem-only reads..."
grep -r "collection_mgr.list_collections\|artifact_mgr.list_artifacts" \
  skillmeat/api/routers/ \
  --include="*.py" \
  | grep -v "# WRITE-THROUGH" \
  | grep -v "# OK" \
  && echo "FAIL: Found remaining filesystem reads" || echo "PASS: All reads fixed"

echo "Checking collections.py deprecation..."
grep -n "status_code=410" skillmeat/api/routers/collections.py \
  && echo "PASS: Deprecation returns 410" || echo "FAIL: Missing 410 deprecation"

echo "Checking health.py edition awareness..."
grep -n "settings.edition == \"enterprise\"" skillmeat/api/routers/health.py \
  && echo "PASS: Health checks are edition-aware" || echo "FAIL: Missing edition check"
```

---

## Rollback Plan

If issues discovered in production:

1. Revert all router changes: `git revert <commit-hash>`
2. Disable enterprise edition: `export SKILLMEAT_EDITION=local`
3. Investigate specific endpoint failures using `.claude/findings/ENTERPRISE_ROUTER_AUDIT.md`
4. Re-implement fixes with more testing

**Estimated rollback time**: <5 minutes (git revert + env var)
