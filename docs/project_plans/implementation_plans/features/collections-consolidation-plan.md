# Collections API Consolidation Plan

**Date**: 2025-12-13
**Status**: Proposed
**Author**: AI Analysis

## Executive Summary

The agent's observation is **correct**: SkillMeat has two collection systems, and consolidation to the DB-backed `/user-collections` is recommended.

**Recommendation**: Consolidate fully on `/user-collections` (DB-backed) and deprecate `/collections` (file-based).

---

## Current State Analysis

### System 1: `/collections` (File-Based)

**Router**: `skillmeat/api/routers/collections.py`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/collections` | GET | List collections |
| `/collections/{id}` | GET | Get collection details |
| `/collections/{id}/artifacts` | GET | List artifacts (with type filter) |

**Backend**: `CollectionManager` class (`skillmeat/core/collection.py`)
- Reads from TOML manifest files (`~/.skillmeat/collections/{name}/collection.toml`)
- **Read-only API** - no create/update/delete endpoints exposed
- No database, pure filesystem storage
- Used by CLI for `skillmeat init`, `skillmeat add`, `skillmeat deploy`

### System 2: `/user-collections` (Database-Backed)

**Router**: `skillmeat/api/routers/user_collections.py`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/user-collections` | GET | List collections (with search) |
| `/user-collections` | POST | Create collection |
| `/user-collections/{id}` | GET | Get collection with groups |
| `/user-collections/{id}` | PUT | Update collection |
| `/user-collections/{id}` | DELETE | Delete collection (cascade) |
| `/user-collections/{id}/artifacts` | POST | Add artifacts (idempotent) |
| `/user-collections/{id}/artifacts/{aid}` | DELETE | Remove artifact (idempotent) |

**Backend**: SQLite + SQLAlchemy ORM (`skillmeat/cache/models.py`)
- Full CRUD operations
- Supports grouping of artifacts
- Search capability
- Idempotent operations
- Cascade deletes
- Auto timestamps

---

## Gap Analysis

### Feature Comparison

| Feature | `/collections` | `/user-collections` | Gap |
|---------|----------------|---------------------|-----|
| List collections | Yes | Yes | None |
| Get collection | Yes | Yes (with groups) | user-collections richer |
| List artifacts | Yes (with type filter) | No direct endpoint | **Gap in user-collections** |
| Create collection | No | Yes | Gap in collections |
| Update collection | No | Yes | Gap in collections |
| Delete collection | No | Yes | Gap in collections |
| Add artifact | No | Yes (batch) | Gap in collections |
| Remove artifact | No | Yes | Gap in collections |
| Search | No | Yes | Gap in collections |
| Grouping | No | Yes | Gap in collections |
| Type filter | Yes | No | **Gap in user-collections** |
| Copy artifact | No | No | Neither |
| Move artifact | No | No | Neither |

### Critical Finding: Frontend API Client is Broken

**File**: `skillmeat/web/lib/api/collections.ts`

The frontend calls endpoints that **don't exist** on the file-based `/collections` router:

```typescript
// BROKEN: These endpoints don't exist on /collections
updateCollection()     → PUT /collections/{id}         // 404!
deleteCollection()     → DELETE /collections/{id}      // 404!
addArtifactToCollection()    → POST /collections/{id}/artifacts/{aid}      // 404!
removeArtifactFromCollection() → DELETE /collections/{id}/artifacts/{aid} // 404!
copyArtifactToCollection()   → POST /collections/{id}/artifacts/{aid}/copy  // 404!
moveArtifactToCollection()   → POST /collections/{id}/artifacts/{aid}/move  // 404!

// WORKS but inconsistent
createCollection()     → POST /user-collections        // Uses different system!
fetchCollections()     → GET /collections              // Uses file-based
fetchCollection()      → GET /collections/{id}         // Uses file-based
```

**Impact**: Most collection mutations in the web UI are currently broken.

---

## Consolidation Recommendation

### Why Consolidate on `/user-collections`?

1. **Feature completeness**: Full CRUD vs read-only
2. **Extensibility**: DB supports groups, search, relationships
3. **Frontend already using it**: `createCollection` posts to `/user-collections`
4. **Idempotent operations**: Safer for web clients
5. **Cascade deletes**: Proper referential integrity
6. **Performance**: Indexed queries vs filesystem scans
7. **Simpler architecture**: One source of truth

### What About CLI?

The CLI uses `CollectionManager` for:
- `skillmeat init` - Creates collection directory structure
- `skillmeat add` - Adds artifact from GitHub/local
- `skillmeat deploy` - Deploys to project
- `skillmeat list` - Lists artifacts
- `skillmeat sync` - Syncs with upstream

**Strategy**: Keep `CollectionManager` for CLI file operations but sync to DB.

---

## Implementation Plan

### Phase 1: Fill Gaps in `/user-collections` (Required)

| Task | Description | Effort |
|------|-------------|--------|
| 1.1 | Add `GET /user-collections/{id}/artifacts` endpoint with type filter | Small |
| 1.2 | Add copy artifact endpoint | Small |
| 1.3 | Add move artifact endpoint | Small |

### Phase 2: Update Frontend (Required)

| Task | Description | Effort |
|------|-------------|--------|
| 2.1 | Update `lib/api/collections.ts` to use `/user-collections` for all ops | Small |
| 2.2 | Update type definitions if needed | Small |
| 2.3 | Test all collection mutations | Medium |

### Phase 3: Data Migration (If Collections Exist)

| Task | Description | Effort |
|------|-------------|--------|
| 3.1 | Create migration script: file-based → DB | Medium |
| 3.2 | Run migration for existing collections | Small |
| 3.3 | Verify data integrity | Small |

### Phase 4: Deprecate `/collections` API

| Task | Description | Effort |
|------|-------------|--------|
| 4.1 | Add deprecation warnings to `/collections` endpoints | Small |
| 4.2 | Update API docs | Small |
| 4.3 | Remove `/collections` router after transition period | Small |

### Phase 5: CLI-DB Sync (Optional Enhancement)

| Task | Description | Effort |
|------|-------------|--------|
| 5.1 | Add DB sync to `CollectionManager.save_collection()` | Medium |
| 5.2 | Add file sync from DB on load | Medium |
| 5.3 | Test bidirectional sync | Medium |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data loss during migration | High | Backup file collections first |
| CLI breaks after removal | Medium | Keep CollectionManager, add DB sync |
| Frontend regression | Medium | Comprehensive testing |
| Performance regression | Low | DB is indexed, should be faster |

---

## Decision Matrix

| Factor | Keep Both | Consolidate to DB | Consolidate to Files |
|--------|-----------|-------------------|---------------------|
| Development complexity | Bad | Good | OK |
| Feature completeness | OK | Best | Worst |
| Data consistency | Worst | Best | Good |
| Performance | OK | Best | OK |
| Migration effort | None | Medium | High |
| **Recommendation** | | **Yes** | |

---

## Appendix: Database Schema

```sql
-- Collections table
CREATE TABLE collections (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Groups table (for organizing artifacts within collections)
CREATE TABLE groups (
    id VARCHAR(32) PRIMARY KEY,
    collection_id VARCHAR(32) REFERENCES collections(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE (collection_id, name)
);

-- Collection artifacts (M:N relationship)
CREATE TABLE collection_artifacts (
    collection_id VARCHAR(32) REFERENCES collections(id) ON DELETE CASCADE,
    artifact_id VARCHAR(255) NOT NULL,  -- No FK, supports external artifacts
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (collection_id, artifact_id)
);

-- Group artifacts (for ordered artifacts within groups)
CREATE TABLE group_artifacts (
    group_id VARCHAR(32) REFERENCES groups(id) ON DELETE CASCADE,
    artifact_id VARCHAR(255) NOT NULL,
    position INTEGER DEFAULT 0,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (group_id, artifact_id)
);
```

---

## Next Steps

1. **Approve plan** - Review and approve consolidation approach
2. **Create Linear tasks** - Break down into trackable work items
3. **Phase 1** - Fill gaps in `/user-collections` API
4. **Phase 2** - Update frontend to use unified API
5. **Testing** - Comprehensive E2E testing
6. **Deprecation** - Mark `/collections` as deprecated
