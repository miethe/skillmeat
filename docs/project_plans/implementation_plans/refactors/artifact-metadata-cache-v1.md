---
title: 'Implementation Plan: Artifact Metadata Caching Enhancement'
description: Phase 6 follow-on to collection-data-consistency-v1 that populates artifact
  metadata cache from file-based artifacts, enabling true database-backed web performance
audience:
- ai-agents
- developers
- architects
tags:
- implementation
- refactor
- performance
- caching
- collections
- web
created: 2026-02-01
updated: 2026-02-02
category: refactors
status: completed
complexity: Medium
total_effort: 12-16 hours (Phases 1-4) + 6-8 hours (Phase 5 future)
related:
- /docs/project_plans/implementation_plans/refactors/collection-data-consistency-v1.md
- /docs/project_plans/reports/dual-collection-system-architecture-analysis.md
- /docs/project_plans/reports/manage-collection-page-architecture-analysis.md
schema_version: 2
doc_type: implementation_plan
feature_slug: artifact-metadata-cache
prd_ref: null
---

# Implementation Plan: Artifact Metadata Caching Enhancement (Phase 6)

**Plan ID**: `IMPL-2026-02-01-ARTIFACT-METADATA-CACHE`
**Date**: 2026-02-01
**Author**: Claude Opus 4.5 (AI-generated)
**Related Documents**:
- **Base Plan**: `/docs/project_plans/implementation_plans/refactors/collection-data-consistency-v1.md` (Completed)
- **Architecture**: `/docs/project_plans/reports/dual-collection-system-architecture-analysis.md`
- **Page Design**: `/docs/project_plans/reports/manage-collection-page-architecture-analysis.md`

**Complexity**: Medium
**Total Estimated Effort**: 10-14 hours (2-3 days)
**Target Timeline**: Single sprint following collection-data-consistency-v1

---

## Executive Summary

The collection-data-consistency-v1 plan (Phase 5 completed) established database-backed collections and fixed N+1 query performance. However, a critical gap was discovered during implementation: `migrate_artifacts_to_default_collection()` only creates `CollectionArtifact` associations—it does NOT populate the `Artifact` cache table with metadata.

**Current Limitation**: The `/collection` page falls back to reading artifact metadata from `ArtifactManager` (file-based) on every request, bypassing the database-backed system and preventing true performance gains.

**Enhancement Goal**: Populate and maintain a complete artifact metadata cache in the database, enabling the `/collection` page to operate entirely from the database with sub-100ms response times. This is a follow-on enhancement to collection-data-consistency-v1, not a replacement.

**Implementation Status (2026-02-02)**: Phases 1-4 are complete; Phase 5 remains future-only. See `.claude/progress/artifact-metadata-cache/all-phases-progress.md`.

**Success Metrics**:
- `/collection` page metadata queries use only database, zero file-system access
- API response times <100ms for metadata-heavy queries (50+ artifacts)
- Cache invalidation automatic and reliable across all sync mechanisms
- Metadata staleness bounded by TTL-based refresh intervals

---

## Problem Statement

### Current State (Post-Phase 5)

**File**: `skillmeat/api/routers/user_collections.py` (lines 218-295)

```python
def migrate_artifacts_to_default_collection(session, artifact_mgr, collection_mgr):
    # Creates CollectionArtifact associations ONLY
    for artifact_id in all_artifact_ids:
        new_association = CollectionArtifact(
            collection_id=DEFAULT_COLLECTION_ID,
            artifact_id=artifact_id,
            added_at=datetime.utcnow(),
        )
        session.add(new_association)
    # Result: Collection associations exist, but metadata cache fields are empty
```

**Consequence**: When `/user-collections/{id}/artifacts` lists artifacts, it
cannot build metadata from the database cache and falls back to the file system:

```python
# skillmeat/api/routers/user_collections.py (list_collection_artifacts)
# Primary: ArtifactManager.show (filesystem)
# Fallback: get_artifact_metadata (DB/marketplace)
```

**Current Workaround**: Backend still reads the file system per artifact to
assemble summaries, keeping response times in the 800–1500ms range.

### Impact on User Experience

- **Collection browsing**: 800-1500ms response time (includes file-system reads)
- **Slow metadata rendering**: Multiple requests to fetch descriptions, tags, authors
- **No true collection database**: File-based system still source of truth despite having database

### Why Not Just Use File-Based System?

The dual-system architecture is intentional per `/docs/project_plans/reports/dual-collection-system-architecture-analysis.md`:

- File-based system: CLI-first, offline-capable, version-pinned
- Database system: Web-first, groups/sharing, full-text search, analytics

The goal is NOT to replace file-based with database, but to **sync metadata into database cache** so web interface can use its natural system.

---

## Solution Architecture

### What to Cache

From `ArtifactManager.show()` and file-based `Artifact` class in `skillmeat/core/artifact.py`:

```python
# Core identity
id: str                    # 'skill:my-skill' format
name: str                  # Artifact name
type: str                  # 'skill', 'command', 'agent', 'mcp', 'hook'

# Source & versioning
source: str                # GitHub path or local source
origin: str                # 'github', 'local', 'marketplace'
origin_source: str         # Full URI
version_spec: str          # Version specifier from manifest
resolved_sha: str          # Pinned SHA from lock file
resolved_version: str      # Resolved version tag

# Metadata (from YAML frontmatter)
description: str           # Short description
author: str                # Author name/email
license: str               # License (MIT, Apache-2.0, etc.)
tags: List[str]            # Classification tags
tools: List[str]           # Claude tools used by artifact

# Timestamps
synced_at: datetime         # When file-based artifact was cached
updated_at: datetime        # When metadata last changed
```

### Where Metadata Lives

**File-Based Source** (`~/.skillmeat/collection/collection.toml` and `SKILL.md` frontmatter):
```toml
[[artifacts]]
name = "pdf"
type = "skill"
source = "anthropics/skills/pdf-parser@v2.1.0"
description = "Extract text and tables from PDFs"
author = "Anthropic"
license = "MIT"
tags = ["document", "extraction"]
```

**Database Target** (`skillmeat/cache/models.py` - `CollectionArtifact` table):
- This table already models membership between a database collection and an artifact ID.
- Extend it to hold cached metadata fields, scoped to a collection (avoids project cache collisions and supports per-collection versions).
- New fields: `description`, `author`, `license`, `tags_json`, `version`, `source`, `origin`, `origin_source`, `resolved_sha`, `resolved_version`, `synced_at`

### Sync Flow

```
File-Based Artifacts              Sync Mechanism              Database Cache
(CollectionManager)               ───────────────>             (CollectionArtifact metadata)

1. Server Startup
   └─ migrate_artifacts_to_default_collection()
      └─ NEW: populate_collection_artifact_metadata()
         └─ For each file-based artifact:
            1. Create/Update CollectionArtifact row with metadata
            2. Ensure default collection association exists
            3. Set synced_at timestamp

2. CLI: skillmeat add <source>
   └─ NEW: After artifact added to file collection
      └─ Trigger API endpoint to sync single artifact into DB cache
         └─ POST /api/v1/user-collections/{collection_id}/refresh-cache

3. CLI: skillmeat sync
   └─ NEW: After collection.toml updated
      └─ Trigger refresh endpoint
         └─ POST /api/v1/user-collections/{collection_id}/refresh-cache

4. Background: Staleness check
   └─ NEW: Cache invalidation service
      └─ Refresh metadata older than TTL (30 min default)

5. Web: Deploy/Sync operations (via ArtifactManager)
   └─ NEW: After ArtifactManager completes file operation
      └─ Auto-refresh affected artifact(s) in DB cache
         └─ Hook into router response to trigger cache update
```

---

## Data Flow Architecture

### Architectural Principle

**File system is source of truth for artifact content and metadata.**

All metadata changes must flow through the file system first, then sync to database cache. This ensures:
- CLI users always see authoritative data
- Offline CLI operations remain functional
- Lock file integrity maintained
- No divergence between file and database states

### Data Flow by Operation Type

| Operation | Initiator | Flow | DB Cache Action |
|-----------|-----------|------|-----------------|
| **Add artifact** | CLI | File → DB | Sync new artifact to cache |
| **Sync artifact** | CLI | File → DB | Refresh artifact in cache |
| **Deploy artifact** | Web/CLI | File (via ArtifactManager) → DB | Refresh after deploy completes |
| **Remove artifact** | CLI | File → DB | Invalidate/remove from cache |
| **Edit metadata** | Web (future) | Web → File → DB | Write to file, then refresh cache |
| **Create artifact** | Web (future) | Web → File → DB | Write to file, then sync to cache |
| **Collection membership** | Web | DB only | No file sync (web-only feature) |
| **Groups/organization** | Web | DB only | No file sync (web-only feature) |

### Web Operations That Modify Files

When the web app performs operations that affect file-based artifacts, it must:

1. **Call ArtifactManager** to perform the file operation
2. **Wait for file operation to complete**
3. **Trigger DB cache refresh** for affected artifact(s)

```
Web Request → ArtifactManager (file ops) → File System
                     ↓ (on success)
              DB Cache Refresh ← API Response
```

### Future: Web-Based Artifact Editing

When web-based metadata editing is implemented, it MUST follow this flow:

```
1. User edits metadata in web UI
2. Web app calls API endpoint (e.g., PUT /api/v1/artifacts/{id}/metadata)
3. API writes changes to file system:
   - Update collection.toml [[artifacts]] entry
   - Update artifact's SKILL.md/COMMAND.md frontmatter (if applicable)
4. API refreshes DB cache from updated file
5. Return success to web UI

NEVER: Write to DB only (causes file/DB divergence)
```

This ensures CLI users see the same metadata as web users, and lock file integrity is preserved

### Read Path Decision (Per Dual-System Architecture)

**/user-collections must be DB-first/DB-only for metadata rendering.**
The `/user-collections/{id}/artifacts` endpoint should read metadata from the
CollectionArtifact cache table, and only fall back to filesystem reads on
explicit cache-miss (not as the primary path). This aligns with the
dual-system architecture: file system remains source of truth, while the web
UI reads from the DB cache for performance.

### Endpoint Collision Avoidance

The existing `POST /api/v1/user-collections/{collection_id}/refresh` endpoint
targets **file-based** collections. To avoid collisions (especially for the
`default` collection), this plan adds **new** DB-cache endpoints:

- `POST /api/v1/user-collections/{collection_id}/refresh-cache` (scoped)
- `POST /api/v1/user-collections/refresh-cache` (all collections)

---

## Implementation Strategy

### Phased Approach

**Phase 1**: Enhance sync function to populate CollectionArtifact metadata cache
- Modify `migrate_artifacts_to_default_collection()` to populate metadata on CollectionArtifact rows
- Create database schema migration for new CollectionArtifact fields
- Test with existing artifacts

**Phase 2**: Add incremental sync for CLI/Web operations
- Create API endpoint for metadata cache refresh (scoped to DB collection)
- Create API endpoint for batch cache refresh (all collections)
- Implement cache invalidation hooks
- Make /user-collections list endpoint DB-first (filesystem only on cache miss)

**Phase 3**: Cache invalidation and TTL-based refresh
- Implement staleness tracking (synced_at timestamps)
- Create background refresh service
- Add monitoring and logging

**Phase 4** (Optional): CLI integration
- Add `--web-sync` flag to CLI commands
- Call refresh-cache endpoint after add/sync operations
- No CLI changes required; API calls handle sync

**Phase 5** (Future): Web-based artifact editing groundwork
- Write service for file system metadata updates
- API endpoints for web-based metadata editing
- Ensures correct data flow: Web → File → DB Cache

### Parallel Work Opportunities

| Track A | Track B |
|---------|---------|
| Phase 1: Schema migration + sync function | Phase 2: API endpoints |
| Phase 3: TTL service | Phase 3: Tests |

Phases 1 and 2 have minimal dependencies.

---

## Phase Breakdown

### Phase 1: Enhanced Sync Function & Schema

**Priority**: CRITICAL
**Duration**: 3-4 hours
**Dependencies**: None
**Risk**: Low (isolated change)
**Assigned Subagent(s)**: `python-backend-engineer`

#### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|---------------------|----------|--------------|
| TASK-1.1 | Add metadata fields to CollectionArtifact model | Add `description`, `author`, `license`, `tags_json`, `version`, `source`, `origin`, `origin_source`, `resolved_sha`, `resolved_version`, `synced_at` columns to cache/models.py | All columns added; model loads without error; tests pass | 1h | None |
| TASK-1.2 | Create Alembic migration | Create database schema migration for new CollectionArtifact fields | Migration auto-generates; upgrade/downgrade work correctly | 0.5h | TASK-1.1 |
| TASK-1.3 | Create populate_collection_artifact_metadata() function | New function that reads file-based artifacts and upserts CollectionArtifact metadata cache records | Function extracts metadata from ArtifactManager; creates/updates CollectionArtifact rows | 1.5h | TASK-1.1 |
| TASK-1.4 | Integrate with migrate_artifacts_to_default_collection() | Call populate_collection_artifact_metadata() from existing migration function | migrate_artifacts_to_default_collection() populates CollectionArtifact rows with metadata | 0.5h | TASK-1.3 |
| TASK-1.5 | Add startup sync logging | Add detailed logging showing what metadata was cached | Logs show artifact count, fields populated, timing, any failures | 0.5h | TASK-1.4 |

#### Implementation Details

**TASK-1.1: Add metadata fields to CollectionArtifact model**

File: `skillmeat/cache/models.py` (CollectionArtifact class)

Add new cache fields:

```python
# Cached metadata for DB-backed /collection page
description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
author: Mapped[Optional[str]] = mapped_column(String, nullable=True)
license: Mapped[Optional[str]] = mapped_column(String, nullable=True)
tags_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array string
version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
origin: Mapped[Optional[str]] = mapped_column(String, nullable=True)
origin_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
resolved_sha: Mapped[Optional[str]] = mapped_column(String, nullable=True)
resolved_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
synced_at: Mapped[Optional[datetime]] = mapped_column(
    DateTime, nullable=True, default=datetime.utcnow
)
```

**TASK-1.3: Create populate_collection_artifact_metadata() function**

File: `skillmeat/api/routers/user_collections.py` (NEW function before migrate_artifacts_to_default_collection)

```python
def populate_collection_artifact_metadata(
    session: Session,
    artifact_mgr,
    collection_mgr,
) -> dict:
    """Populate CollectionArtifact metadata cache from file-based artifacts.

    For each file-based artifact, create or update CollectionArtifact rows with
    full metadata:
    - description, author, license, tags from YAML frontmatter
    - version from metadata.version
    - origin/source fields from core artifact
    - resolved_sha, resolved_version from lock file
    - synced_at timestamp marking cache currency

    Args:
        session: Database session
        artifact_mgr: ArtifactManager for listing and reading artifacts
        collection_mgr: CollectionManager for collection access

    Returns:
        dict with stats: created_count, updated_count, skipped_count, errors
    """
    created_count = 0
    updated_count = 0
    skipped_count = 0
    errors = []

    for coll_name in collection_mgr.list_collections():
        try:
            artifacts = artifact_mgr.list_artifacts(collection_name=coll_name)
            for file_artifact in artifacts:
                artifact_id = f"{file_artifact.type.value}:{file_artifact.name}"

                try:
                    description = (
                        file_artifact.metadata.description
                        if file_artifact.metadata
                        else None
                    )
                    author = (
                        file_artifact.metadata.author
                        if file_artifact.metadata
                        else None
                    )
                    license_val = (
                        file_artifact.metadata.license
                        if file_artifact.metadata
                        else None
                    )
                    tags = (
                        file_artifact.metadata.tags
                        if file_artifact.metadata and file_artifact.metadata.tags
                        else []
                    )
                    version = (
                        file_artifact.metadata.version
                        if file_artifact.metadata
                        else None
                    )
                    resolved_sha = getattr(file_artifact, 'resolved_sha', None)
                    resolved_version = getattr(file_artifact, 'resolved_version', None)

                    # Upsert CollectionArtifact metadata cache
                    existing = (
                        session.query(CollectionArtifact)
                        .filter_by(
                            collection_id=DEFAULT_COLLECTION_ID,
                            artifact_id=artifact_id,
                        )
                        .first()
                    )

                    if existing:
                        existing.description = description
                        existing.author = author
                        existing.license = license_val
                        existing.tags_json = json.dumps(tags) if tags else None
                        existing.version = version
                        existing.source = file_artifact.upstream or None
                        existing.origin = file_artifact.origin
                        existing.origin_source = file_artifact.origin_source
                        existing.resolved_sha = resolved_sha
                        existing.resolved_version = resolved_version
                        existing.synced_at = datetime.utcnow()
                        updated_count += 1
                    else:
                        new_assoc = CollectionArtifact(
                            collection_id=DEFAULT_COLLECTION_ID,
                            artifact_id=artifact_id,
                            added_at=datetime.utcnow(),
                            description=description,
                            author=author,
                            license=license_val,
                            tags_json=json.dumps(tags) if tags else None,
                            version=version,
                            source=file_artifact.upstream or None,
                            origin=file_artifact.origin,
                            origin_source=file_artifact.origin_source,
                            resolved_sha=resolved_sha,
                            resolved_version=resolved_version,
                            synced_at=datetime.utcnow(),
                        )
                        session.add(new_assoc)
                        created_count += 1

                except Exception as e:
                    logger.warning(f"Failed to cache metadata for '{artifact_id}': {e}")
                    errors.append({"artifact_id": artifact_id, "error": str(e)})
                    skipped_count += 1
                    continue

        except Exception as e:
            logger.warning(f"Failed to list artifacts in collection '{coll_name}': {e}")
            continue

    if created_count + updated_count > 0:
        session.commit()

    logger.info(
        f"CollectionArtifact metadata cache: created={created_count}, "
        f"updated={updated_count}, skipped={skipped_count}, errors={len(errors)}"
    )

    return {
        "created_count": created_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "errors": errors,
    }
```

**TASK-1.4: Update migrate_artifacts_to_default_collection()**

Modify existing function to call populate_collection_artifact_metadata():

```python
def migrate_artifacts_to_default_collection(
    session: Session,
    artifact_mgr,
    collection_mgr,
) -> dict:
    """Migrate all existing artifacts to the default collection.

    Now includes full metadata population for database-backed caching.
    """
    # Ensure default collection exists
    ensure_default_collection(session)

    # NEW: Populate CollectionArtifact metadata cache from file-based artifacts
    metadata_stats = populate_collection_artifact_metadata(
        session, artifact_mgr, collection_mgr
    )

    # Get all artifacts (from default collection associations)
    all_associations = (
        session.query(CollectionArtifact.artifact_id)
        .filter_by(collection_id=DEFAULT_COLLECTION_ID)
        .all()
    )
    all_artifact_ids = {row[0] for row in all_associations}

    # Get existing associations
    existing_associations = (
        session.query(CollectionArtifact.artifact_id)
        .filter_by(collection_id=DEFAULT_COLLECTION_ID)
        .all()
    )
    existing_artifact_ids = {row[0] for row in existing_associations}

    # Add missing to default collection
    missing_artifact_ids = all_artifact_ids - existing_artifact_ids
    migrated_count = 0

    for artifact_id in missing_artifact_ids:
        try:
            new_association = CollectionArtifact(
                collection_id=DEFAULT_COLLECTION_ID,
                artifact_id=artifact_id,
                added_at=datetime.utcnow(),
            )
            session.add(new_association)
            migrated_count += 1
        except Exception as e:
            logger.warning(f"Failed to add '{artifact_id}' to default collection: {e}")

    if migrated_count > 0:
        session.commit()

    return {
        "migrated_count": migrated_count,
        "already_present_count": len(existing_artifact_ids),
        "total_artifacts": len(all_artifact_ids),
        "metadata_cache": metadata_stats,
    }
```

#### Phase 1 Quality Gates

- [ ] CollectionArtifact model includes new cache fields
- [ ] Alembic migration runs without errors (upgrade and downgrade)
- [ ] `populate_collection_artifact_metadata()` creates CollectionArtifact cache records with complete metadata
- [ ] `migrate_artifacts_to_default_collection()` returns successful stats
- [ ] Server startup completes within 5 seconds (including cache population)
- [ ] Cache fields populated in CollectionArtifact rows after startup
- [ ] Startup logs show accurate created/updated/skipped counts
- [ ] Existing artifact tests pass

---

### Phase 2: Incremental Sync & API Endpoints

**Priority**: HIGH
**Duration**: 4-5 hours
**Dependencies**: Phase 1 complete
**Risk**: Medium (new endpoints)
**Assigned Subagent(s)**: `python-backend-engineer`

#### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|---------------------|----------|--------------|
| TASK-2.1 | Create DB cache refresh endpoint | POST /api/v1/user-collections/{collection_id}/refresh-cache | Endpoint accepts POST; fetches metadata from file-based; updates CollectionArtifact cache rows | 1h | TASK-1.4 |
| TASK-2.2 | Create batch refresh endpoint | POST /api/v1/user-collections/refresh-cache | Endpoint refreshes all collections; returns stats | 1h | TASK-1.4 |
| TASK-2.3 | Add endpoint parameters validation | Validate collection_id ownership and request parameters | Validation prevents invalid requests; returns 400 with clear message | 0.5h | TASK-2.1, TASK-2.2 |
| TASK-2.4 | Add error handling and logging | Comprehensive error handling with detailed logging for debugging | Errors logged before returning; no unhandled exceptions | 0.5h | TASK-2.2 |
| TASK-2.5 | Add unit tests for endpoints | Create tests for happy path and error cases | Tests cover: valid artifact, missing artifact, collection not found | 1h | TASK-2.2 |
| TASK-2.6 | Hook deploy endpoint to refresh cache | After artifacts.py deploy_artifact() completes, trigger cache refresh for deployed artifact | Deploy via web auto-refreshes DB cache; no manual refresh needed | 0.5h | TASK-2.1 |
| TASK-2.7 | Hook sync endpoint to refresh cache | After artifacts.py sync_artifact() completes, trigger cache refresh for synced artifact | Sync via web auto-refreshes DB cache; version changes reflected | 0.5h | TASK-2.1 |
| TASK-2.8 | Hook create/update/delete endpoints | After create/update/delete operations, refresh/invalidate cache | Cache stays fresh after all file mutations | 0.5h | TASK-2.1 |
| TASK-2.9 | Make /user-collections read path DB-first | Use CollectionArtifact cache as primary source; fallback to filesystem only on cache miss | /collection page avoids filesystem reads on cache hits | 1h | TASK-1.4 |

#### Implementation Details

**TASK-2.1: Create DB cache refresh endpoint (scoped)**

File: `skillmeat/api/routers/user_collections.py` (NEW endpoint)

```python
@router.post(
    "/{collection_id}/refresh-cache",
    response_model=dict,
    tags=["user-collections"],
    summary="Refresh collection metadata cache (DB-backed)",
)
async def refresh_collection_cache(
    collection_id: str,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    db_session: DbSessionDep,
) -> dict:
    """Refresh CollectionArtifact metadata cache for a DB collection.

    IMPORTANT: This is separate from /{collection_id}/refresh, which refreshes
    file-based collections. The new endpoint targets DB cache only.
    """
    # Validate collection exists in DB
    coll = db_session.query(Collection).filter_by(id=collection_id).first()
    if not coll:
        raise HTTPException(
            status_code=404,
            detail=f"Collection '{collection_id}' not found",
        )

    # Refresh all artifacts associated with this collection
    # (Implementation uses populate_collection_artifact_metadata or equivalent
    # scoped to this collection_id)
```

**TASK-2.2: Create batch refresh endpoint (all collections)**

File: `skillmeat/api/routers/user_collections.py` (NEW endpoint)

```python
@router.post(
    "/refresh-cache",
    response_model=dict,
    tags=["user-collections"],
    summary="Refresh metadata cache for all collections",
)
async def refresh_all_collections_cache(
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    db_session: DbSessionDep,
) -> dict:
    """Refresh CollectionArtifact metadata cache across all DB collections."""
    # Implementation loops DB collections and refreshes each one
```

**TASK-2.9: Make /user-collections read path DB-first**

File: `skillmeat/api/routers/user_collections.py` (list_collection_artifacts)

Guidance:
- Build `ArtifactSummary` from CollectionArtifact cache fields first.
- Only fall back to filesystem (`ArtifactManager.show`) on explicit cache miss.
- Keep marketplace fallback as a last resort (unchanged).

```python
# Primary: use CollectionArtifact cached fields (DB)
# Fallback: file-based lookup (only on cache miss)
# Last resort: get_artifact_metadata(session, artifact_id)
```

**TASK-2.6 & TASK-2.7: Hook ArtifactManager operations to refresh cache**

File: `skillmeat/api/routers/artifacts.py` (MODIFY existing endpoints)

After `deploy_artifact()` and `sync_artifact()` complete their file operations, call the cache refresh:

```python
from skillmeat.api.services.artifact_cache_service import refresh_single_artifact_cache

@router.post("/{artifact_id}/deploy")
async def deploy_artifact(
    artifact_id: str,
    # ... existing params
) -> dict:
    """Deploy artifact to project."""
    # ... existing deploy logic via ArtifactManager ...

    # NEW: After successful file operation, refresh DB cache
    try:
        refresh_single_artifact_cache(db_session, artifact_mgr, artifact_id)
        logger.debug(f"Refreshed cache for deployed artifact: {artifact_id}")
    except Exception as e:
        # Don't fail deploy if cache refresh fails - log and continue
        logger.warning(f"Cache refresh failed for {artifact_id}: {e}")

    return {"deployed": True, "artifact_id": artifact_id}


@router.post("/{artifact_id}/sync")
async def sync_artifact(
    artifact_id: str,
    # ... existing params
) -> dict:
    """Sync artifact with upstream."""
    # ... existing sync logic via ArtifactManager ...

    # NEW: After successful file sync, refresh DB cache
    try:
        refresh_single_artifact_cache(db_session, artifact_mgr, artifact_id)
        logger.debug(f"Refreshed cache for synced artifact: {artifact_id}")
    except Exception as e:
        # Don't fail sync if cache refresh fails - log and continue
        logger.warning(f"Cache refresh failed for {artifact_id}: {e}")

    return {"synced": True, "artifact_id": artifact_id, "new_version": new_version}
```

Helper function in `artifact_cache_service.py`:

```python
def refresh_single_artifact_cache(
    session: Session,
    artifact_mgr,
    collection_id: str,
    artifact_id: str,
) -> bool:
    """Refresh cache for a single artifact after file operation.

    Args:
        session: Database session
        artifact_mgr: ArtifactManager instance
        artifact_id: Artifact ID in 'type:name' format

    Returns:
        True if refresh succeeded, False otherwise
    """
    if ":" not in artifact_id:
        return False

    artifact_type, artifact_name = artifact_id.split(":", 1)

    file_artifact = artifact_mgr.show(artifact_name)
    if not file_artifact:
        return False

    # Upsert CollectionArtifact metadata cache
    existing = (
        session.query(CollectionArtifact)
        .filter_by(collection_id=collection_id, artifact_id=artifact_id)
        .first()
    )

    metadata_fields = {
        "description": (
            file_artifact.metadata.description if file_artifact.metadata else None
        ),
        "author": (
            file_artifact.metadata.author if file_artifact.metadata else None
        ),
        "license": (
            file_artifact.metadata.license if file_artifact.metadata else None
        ),
        "tags_json": (
            json.dumps(file_artifact.metadata.tags)
            if file_artifact.metadata and file_artifact.metadata.tags
            else None
        ),
        "version": (
            file_artifact.metadata.version if file_artifact.metadata else None
        ),
        "source": file_artifact.upstream or None,
        "origin": file_artifact.origin,
        "origin_source": file_artifact.origin_source,
        "resolved_version": getattr(file_artifact, 'resolved_version', None),
        "resolved_sha": getattr(file_artifact, 'resolved_sha', None),
        "synced_at": datetime.utcnow(),
    }

    if existing:
        for key, value in metadata_fields.items():
            setattr(existing, key, value)
    else:
        new_assoc = CollectionArtifact(
            collection_id=collection_id,
            artifact_id=artifact_id,
            added_at=datetime.utcnow(),
            **metadata_fields,
        )
        session.add(new_assoc)

    session.commit()
    return True
```

#### Phase 2 Quality Gates

- [ ] POST /api/v1/user-collections/{collection_id}/refresh-cache works for valid collection
- [ ] POST /api/v1/user-collections/refresh-cache works (all collections)
- [ ] Endpoints validate input and return 400/404 appropriately
- [ ] CollectionArtifact metadata updated in database after refresh calls
- [ ] Synced_at timestamps updated correctly
- [ ] All endpoints have error handling and logging
- [ ] Unit tests pass for happy path and error cases
- [ ] No unhandled exceptions
- [ ] Deploy endpoint auto-refreshes cache after file operation completes
- [ ] Sync endpoint auto-refreshes cache after file operation completes
- [ ] Create/update/delete endpoints refresh/invalidate cache after file operations
- [ ] Cache refresh failures don't break deploy/sync operations (graceful degradation)
- [ ] /user-collections list endpoint reads DB cache first (filesystem only on cache miss)

---

### Phase 3: Cache Invalidation & TTL-Based Refresh

**Priority**: MEDIUM
**Duration**: 2-3 hours
**Dependencies**: Phase 2 complete
**Risk**: Medium (background service)
**Assigned Subagent(s)**: `python-backend-engineer`

#### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|---------------------|----------|--------------|
| TASK-3.1 | Create staleness detection service | Service to identify collection artifacts where synced_at > TTL threshold | Service queries cache rows with staleness calculation; returns stale list | 1h | TASK-2.2 |
| TASK-3.2 | Create cache invalidation hook | Hook to invalidate cache on collection operations (add/remove artifact) | Invalidation triggered on POST/DELETE collection artifact endpoints | 0.75h | TASK-3.1 |
| TASK-3.3 | Create background refresh task | Optional async task to auto-refresh stale metadata (can be scheduled) | Task runs on interval; calls refresh-cache endpoint; logs results | 0.75h | TASK-3.1 |
| TASK-3.4 | Add monitoring metrics | Log cache hit rate and staleness distribution | Logs show: total artifacts, stale count, refresh duration | 0.5h | TASK-3.3 |

#### Implementation Details

**TASK-3.1: Create staleness detection service**

File: `skillmeat/api/services/artifact_cache_service.py` (NEW)

```python
"""Artifact metadata cache invalidation and refresh service."""

import logging
from datetime import datetime, timedelta
from typing import List, Tuple

from sqlalchemy.orm import Session

from skillmeat.cache.models import CollectionArtifact

logger = logging.getLogger(__name__)

# Default TTL for artifact metadata cache: 30 minutes
DEFAULT_METADATA_TTL_SECONDS = 30 * 60


class ArtifactCacheService:
    """Service for managing artifact metadata cache staleness and invalidation."""

    def __init__(self, ttl_seconds: int = DEFAULT_METADATA_TTL_SECONDS):
        """Initialize cache service.

        Args:
            ttl_seconds: Time-to-live for cached metadata in seconds
        """
        self.ttl = ttl_seconds

    def find_stale_artifacts(
        self, session: Session
    ) -> List[CollectionArtifact]:
        """Find artifacts where cached metadata is stale.

        An artifact is considered stale if:
        - synced_at is NULL (never synced)
        - synced_at < now - TTL

        Args:
            session: Database session

        Returns:
            List of CollectionArtifact objects with stale metadata
        """
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.ttl)

        stale_artifacts = (
            session.query(CollectionArtifact)
            .filter(
                (CollectionArtifact.synced_at.is_(None))
                | (CollectionArtifact.synced_at < cutoff_time)
            )
            .all()
        )

        return stale_artifacts

    def get_staleness_stats(
        self, session: Session
    ) -> dict:
        """Get statistics about cache staleness.

        Args:
            session: Database session

        Returns:
            dict with: total_artifacts, stale_count, fresh_count,
                       oldest_sync_age_seconds, percentage_stale
        """
        total = session.query(CollectionArtifact).count()

        if total == 0:
            return {
                "total_artifacts": 0,
                "stale_count": 0,
                "fresh_count": 0,
                "oldest_sync_age_seconds": 0,
                "percentage_stale": 0,
            }

        stale = self.find_stale_artifacts(session)

        # Find oldest sync time
        oldest_sync = session.query(CollectionArtifact.synced_at).order_by(
            CollectionArtifact.synced_at.asc()
        ).first()

        oldest_age = None
        if oldest_sync and oldest_sync[0]:
            oldest_age = (datetime.utcnow() - oldest_sync[0]).total_seconds()

        return {
            "total_artifacts": total,
            "stale_count": len(stale),
            "fresh_count": total - len(stale),
            "oldest_sync_age_seconds": oldest_age or 0,
            "percentage_stale": round((len(stale) / total * 100), 1) if total > 0 else 0,
            "ttl_seconds": self.ttl,
        }

    def invalidate_artifact(
        self, session: Session, collection_id: str, artifact_id: str
    ) -> bool:
        """Invalidate cache for a specific artifact.

        Sets synced_at to NULL to mark as needing refresh.

        Args:
            session: Database session
            artifact_id: Artifact ID to invalidate

        Returns:
            True if artifact found and invalidated, False otherwise
        """
        assoc = (
            session.query(CollectionArtifact)
            .filter_by(collection_id=collection_id, artifact_id=artifact_id)
            .first()
        )
        if assoc:
            assoc.synced_at = None
            session.commit()
            logger.debug(
                f"Invalidated artifact cache: {collection_id}:{artifact_id}"
            )
            return True
        return False

    def invalidate_collection_artifacts(
        self, session: Session, collection_id: str
    ) -> int:
        """Invalidate cache for all artifacts in a collection.

        Args:
            session: Database session
            collection_id: Collection ID

        Returns:
            Number of artifacts invalidated
        """
        from skillmeat.cache.models import CollectionArtifact

        # Find all artifact associations in collection
        artifacts_in_collection = (
            session.query(CollectionArtifact)
            .filter(CollectionArtifact.collection_id == collection_id)
            .all()
        )

        count = 0
        for assoc in artifacts_in_collection:
            assoc.synced_at = None
            count += 1

        if count > 0:
            session.commit()
            logger.debug(f"Invalidated {count} artifacts in collection: {collection_id}")

        return count
```

**TASK-3.2: Add cache invalidation to endpoints**

Modify `user_collections.py` endpoints to call invalidation:

```python
from skillmeat.api.services.artifact_cache_service import ArtifactCacheService

cache_service = ArtifactCacheService()

@router.post("/{collection_id}/artifacts")
async def add_artifact_to_collection(
    collection_id: str,
    request: AddArtifactRequest,
    db_session: DbSessionDep,
) -> dict:
    """Add artifact to collection (existing endpoint).

    Enhanced: Invalidate artifact cache on add.
    """
    # ... existing add logic ...

    # Invalidate cache for added artifact
    cache_service.invalidate_artifact(db_session, collection_id, request.artifact_id)

    return {"success": True}

@router.delete("/{collection_id}/artifacts/{artifact_id}")
async def remove_artifact_from_collection(
    collection_id: str,
    artifact_id: str,
    db_session: DbSessionDep,
) -> dict:
    """Remove artifact from collection (existing endpoint).

    Enhanced: Invalidate artifact cache on remove.
    """
    # ... existing remove logic ...

    # Invalidate cache for removed artifact
    cache_service.invalidate_artifact(db_session, collection_id, artifact_id)

    return {"success": True}
```

**TASK-3.3: Create background refresh task (Optional)**

File: `skillmeat/api/services/background_tasks.py` (NEW - optional)

```python
"""Background tasks for cache maintenance."""

import asyncio
import logging
from typing import Optional

from sqlalchemy.orm import Session

from skillmeat.api.services.artifact_cache_service import ArtifactCacheService

logger = logging.getLogger(__name__)


async def refresh_stale_metadata_task(
    db_session_factory,
    artifact_mgr,
    refresh_interval_seconds: int = 300,  # 5 minutes
):
    """Background task to refresh stale artifact metadata.

    Can be scheduled with APScheduler or similar.

    Args:
        db_session_factory: SQLAlchemy session factory
        artifact_mgr: ArtifactManager instance
        refresh_interval_seconds: How often to check for stale artifacts
    """
    cache_service = ArtifactCacheService()

    while True:
        try:
            session = db_session_factory()

            # Find stale artifacts
            stale = cache_service.find_stale_artifacts(session)

            if stale:
                logger.info(f"Background task: refreshing {len(stale)} stale artifacts")

                # Refresh each stale artifact
                refreshed = 0
                for assoc in stale:
                    try:
                        # Parse artifact_id format: "type:name"
                        if ":" not in assoc.artifact_id:
                            continue
                        _, artifact_name = assoc.artifact_id.split(":", 1)

                        file_artifact = artifact_mgr.show(artifact_name)
                        if file_artifact:
                            assoc.description = (
                                file_artifact.metadata.description
                                if file_artifact.metadata
                                else None
                            )
                            assoc.author = (
                                file_artifact.metadata.author
                                if file_artifact.metadata
                                else None
                            )
                            assoc.license = (
                                file_artifact.metadata.license
                                if file_artifact.metadata
                                else None
                            )
                            assoc.synced_at = datetime.utcnow()
                            refreshed += 1
                    except Exception as e:
                        logger.warning(f"Failed to refresh {assoc.artifact_id}: {e}")

                if refreshed > 0:
                    session.commit()
                    logger.info(f"Background task: refreshed {refreshed} artifacts")

            session.close()

            # Sleep before next check
            await asyncio.sleep(refresh_interval_seconds)

        except Exception as e:
            logger.exception(f"Background task error: {e}")
            await asyncio.sleep(60)  # Shorter sleep on error
```

#### Phase 3 Quality Gates

- [ ] `find_stale_artifacts()` correctly identifies null and expired synced_at
- [ ] `get_staleness_stats()` returns accurate counts and percentages
- [ ] CollectionArtifact cache invalidated on add/remove operations
- [ ] Manual refresh-cache endpoint successfully refreshes stale metadata
- [ ] All monitoring metrics logged appropriately
- [ ] No performance impact on normal endpoints (<50ms added latency)

---

### Phase 4: CLI Integration Hooks (Optional)

**Priority**: LOW
**Duration**: 1-2 hours (if implemented)
**Dependencies**: Phase 2 complete
**Risk**: Low (no core changes)
**Assigned Subagent(s)**: `python-backend-engineer`

#### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|---------------------|----------|--------------|
| TASK-4.1 | Add refresh-cache hook to CLI add command | After artifact added via CLI, call refresh-cache endpoint | CLI calls API after add; no errors if API unavailable | 0.5h | TASK-2.1 |
| TASK-4.2 | Add refresh-cache hook to CLI sync command | After sync operation, call refresh-cache endpoint | CLI calls API after sync; no errors if API unavailable | 0.5h | TASK-2.2 |
| TASK-4.3 | Test end-to-end CLI→API→DB flow | Verify artifact added via CLI appears in web UI without delay | Artifact visible in /collection within 1 second of CLI add | 0.5h | TASK-4.1, TASK-4.2 |

**Note**: Phase 4 is optional and deferred if Phase 3 completes on time. The API endpoints function independently; CLI integration is a convenience feature.

---

### Phase 5: Web-Based Artifact Editing Groundwork (Future)

**Priority**: LOW (Future Enhancement)
**Duration**: 6-8 hours (when implemented)
**Dependencies**: Phases 1-3 complete
**Risk**: Medium (new write path)
**Assigned Subagent(s)**: `python-backend-engineer`, `ui-engineer-enhanced`

**Status**: GROUNDWORK ONLY - This phase lays architectural foundation for future implementation.

#### Overview

When web-based artifact editing/creation is implemented, it MUST follow the correct data flow:

```
Web UI Edit → API → File System → DB Cache Refresh → Response
```

This ensures file system remains source of truth and CLI users see the same data as web users.

#### Task Table (Future Implementation)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Dependencies |
|---------|-----------|-------------|---------------------|----------|--------------|
| TASK-5.1 | Create artifact metadata write service | Service that writes metadata changes to file system (collection.toml and artifact frontmatter) | Service writes to correct file locations; preserves existing data; handles TOML/YAML correctly | 2h | Phase 3 |
| TASK-5.2 | Create PUT /api/v1/artifacts/{id}/metadata endpoint | API endpoint for updating artifact metadata via web | Endpoint validates input; calls write service; refreshes cache; returns updated artifact | 1.5h | TASK-5.1 |
| TASK-5.3 | Create POST /api/v1/artifacts endpoint (web add) | API endpoint for adding new artifacts via web | Endpoint creates file-based artifact; adds to collection.toml; syncs to cache | 2h | TASK-5.1 |
| TASK-5.4 | Add optimistic locking | Prevent concurrent edits from CLI and web causing conflicts | Version/hash check before write; 409 Conflict on mismatch | 1h | TASK-5.2 |
| TASK-5.5 | Create web UI for metadata editing | Frontend form for editing artifact description, tags, etc. | Form validates input; shows loading state; handles errors | 2h | TASK-5.2 |

#### Architectural Requirements

**TASK-5.1: Artifact Metadata Write Service**

File: `skillmeat/api/services/artifact_write_service.py` (NEW - Future)

```python
"""Service for writing artifact metadata to file system.

CRITICAL: All metadata writes MUST go through this service to ensure
file system remains source of truth. Never write metadata directly to DB.
"""

import logging
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


class ArtifactWriteService:
    """Service for writing artifact changes to file system."""

    def __init__(self, collection_mgr, artifact_mgr):
        self.collection_mgr = collection_mgr
        self.artifact_mgr = artifact_mgr

    def update_artifact_metadata(
        self,
        artifact_id: str,
        description: Optional[str] = None,
        author: Optional[str] = None,
        tags: Optional[List[str]] = None,
        license: Optional[str] = None,
    ) -> dict:
        """Update artifact metadata in file system.

        Flow:
        1. Load current artifact from file system
        2. Update specified fields
        3. Write back to file system (collection.toml + SKILL.md frontmatter)
        4. Return updated metadata for cache refresh

        Args:
            artifact_id: Artifact ID in 'type:name' format
            description: New description (None = no change)
            author: New author (None = no change)
            tags: New tags list (None = no change)
            license: New license (None = no change)

        Returns:
            dict with updated metadata fields

        Raises:
            FileNotFoundError: Artifact not found in collection
            PermissionError: Cannot write to collection files
            ValueError: Invalid artifact_id format
        """
        if ":" not in artifact_id:
            raise ValueError(f"Invalid artifact_id format: {artifact_id}")

        artifact_type, artifact_name = artifact_id.split(":", 1)

        # 1. Get current artifact from file system
        artifact = self.artifact_mgr.show(artifact_name)
        if not artifact:
            raise FileNotFoundError(f"Artifact not found: {artifact_id}")

        # 2. Build update dict (only non-None values)
        updates = {}
        if description is not None:
            updates["description"] = description
        if author is not None:
            updates["author"] = author
        if tags is not None:
            updates["tags"] = tags
        if license is not None:
            updates["license"] = license

        if not updates:
            return {"artifact_id": artifact_id, "changed": False}

        # 3. Write to collection.toml
        self._update_collection_toml(artifact_name, artifact_type, updates)

        # 4. Write to artifact frontmatter (if artifact has SKILL.md/etc)
        self._update_artifact_frontmatter(artifact, updates)

        logger.info(f"Updated artifact metadata in file system: {artifact_id}")

        return {
            "artifact_id": artifact_id,
            "changed": True,
            "updated_fields": list(updates.keys()),
        }

    def _update_collection_toml(
        self, artifact_name: str, artifact_type: str, updates: dict
    ) -> None:
        """Update artifact entry in collection.toml."""
        # Implementation: Load TOML, find artifact entry, update fields, write back
        # Use atomic write pattern (write to temp, then rename)
        pass  # Future implementation

    def _update_artifact_frontmatter(self, artifact, updates: dict) -> None:
        """Update YAML frontmatter in artifact's main file (SKILL.md, etc)."""
        # Implementation: Load file, parse frontmatter, update, write back
        # Preserve non-metadata content
        pass  # Future implementation
```

**TASK-5.2: Metadata Update Endpoint**

File: `skillmeat/api/routers/artifacts.py` (ADD new endpoint - Future)

```python
from skillmeat.api.services.artifact_write_service import ArtifactWriteService
from skillmeat.api.services.artifact_cache_service import refresh_single_artifact_cache

@router.put(
    "/{artifact_id}/metadata",
    response_model=ArtifactResponse,
    tags=["artifacts"],
    summary="Update artifact metadata (web editing)",
)
async def update_artifact_metadata(
    artifact_id: str,
    request: UpdateMetadataRequest,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    db_session: DbSessionDep,
) -> ArtifactResponse:
    """Update artifact metadata via web interface.

    IMPORTANT: This endpoint writes to file system first, then refreshes DB cache.
    File system is source of truth - never write directly to database.

    Flow:
    1. Validate request
    2. Write changes to file system (collection.toml + artifact frontmatter)
    3. Refresh DB cache from updated files
    4. Return updated artifact

    Args:
        artifact_id: Artifact ID in 'type:name' format
        request: Metadata update request (description, author, tags, license)

    Returns:
        Updated ArtifactResponse with new metadata

    Raises:
        HTTPException(404): Artifact not found
        HTTPException(409): Conflict - artifact modified by another process
        HTTPException(422): Invalid input
    """
    write_service = ArtifactWriteService(collection_mgr, artifact_mgr)

    try:
        # 1. Write to file system
        result = write_service.update_artifact_metadata(
            artifact_id=artifact_id,
            description=request.description,
            author=request.author,
            tags=request.tags,
            license=request.license,
        )

        # 2. Refresh DB cache from updated files
        refresh_single_artifact_cache(db_session, artifact_mgr, artifact_id)

        # 3. Return updated artifact from cache
        artifact = db_session.query(Artifact).filter_by(id=artifact_id).first()
        return ArtifactResponse.from_orm(artifact)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to update artifact metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to update metadata")
```

#### Quality Gates (Future)

- [ ] All metadata writes go through `ArtifactWriteService` (never direct DB writes)
- [ ] File system updated before DB cache refresh
- [ ] CLI can read metadata written via web (file is source of truth)
- [ ] Web can read metadata written via CLI (cache refresh works)
- [ ] Optimistic locking prevents lost updates
- [ ] Atomic file writes prevent corruption
- [ ] Error handling preserves file integrity on failure

#### Why This Architecture

| Approach | Problem |
|----------|---------|
| Write to DB only | CLI users don't see changes; lock file breaks; offline CLI fails |
| Write to DB, sync to file | Complex sync logic; race conditions; source of truth unclear |
| **Write to file, refresh cache** | ✅ Simple; file remains source of truth; CLI/web always consistent |

---

## Risk Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Metadata extraction fails for some artifacts | Medium | Medium | Graceful error handling with logging; skip count returned; no exception propagation |
| Stale metadata visible briefly | Low | Low | Invalidation synchronous; no async staleness window |
| Database migration breaks existing data | Low | High | Test migration both upgrade and downgrade; backup before applying |
| Refresh-cache endpoint DOS abuse | Low | Medium | Add rate limiting to refresh-cache endpoints; consider auth requirements |
| Performance regression on startup | Low | Medium | Batch populate operation optimized; measure and log timing |

### Data Consistency Risks

| Risk | Mitigation |
|------|-----------|
| File-based and DB metadata diverge | One-way sync only; file is source of truth. Manual refresh available. |
| Stale cache during long CLI operations | TTL-based invalidation. User can manually refresh. |
| Duplicate CollectionArtifact rows | Upsert logic prevents duplicates; composite PK enforced |
| Orphaned CollectionArtifact cache entries when artifact removed from file | Remove association on delete; orphans are safe and can be cleaned during refresh |

### Schedule Risks

| Risk | Mitigation |
|------|-----------|
| Alembic migration complex | Keep migration minimal (add columns); no data transformation |
| API endpoint testing time-consuming | Use existing test patterns; 2-3 focused test cases per endpoint |
| Background task debugging difficult | Make task optional; focus on manual endpoints first |

---

## Quality Gates

### Phase 1 Completion

- [ ] CollectionArtifact cache fields added
- [ ] Alembic migration created and tested (upgrade + downgrade)
- [ ] `populate_collection_artifact_metadata()` creates records with all fields populated
- [ ] Server startup includes metadata population (logs show stats)
- [ ] No regression in existing artifact list/detail endpoints
- [ ] Startup time <5 seconds including cache population
- [ ] Database integrity verified (constraints, indexes)

### Phase 2 Completion

- [ ] POST /api/v1/user-collections/{collection_id}/refresh-cache works for valid collection
- [ ] POST /api/v1/user-collections/refresh-cache works (all collections)
- [ ] Endpoints return appropriate error codes (404, 422, 500)
- [ ] CollectionArtifact metadata updates verified in database
- [ ] synced_at timestamps accurate
- [ ] No unhandled exceptions in endpoint code
- [ ] Unit tests for both endpoints pass
- [ ] Error logging comprehensive and actionable
- [ ] /user-collections list endpoint DB-first (filesystem only on cache miss)

### Phase 3 Completion

- [ ] Cache staleness correctly detected
- [ ] Cache invalidation triggered on collection operations
- [ ] Invalidation works (verified by querying database)
- [ ] Monitoring metrics logged at appropriate levels
- [ ] No performance regression (<5ms added per request)
- [ ] Optional background task tested (if implemented)

### Phase 4 Completion (if implemented)

- [ ] CLI add command calls refresh-cache endpoint successfully
- [ ] CLI sync command calls refresh-cache endpoint successfully
- [ ] E2E test: artifact added via CLI visible in web UI within 1 second
- [ ] No errors if API unavailable (graceful degradation)

---

## Data Schema Changes

### CollectionArtifact Metadata Cache Additions

**File**: `skillmeat/cache/models.py`

```sql
-- New columns in collection_artifacts table
ALTER TABLE collection_artifacts ADD COLUMN description TEXT NULL;
ALTER TABLE collection_artifacts ADD COLUMN author VARCHAR(255) NULL;
ALTER TABLE collection_artifacts ADD COLUMN license VARCHAR(50) NULL;
ALTER TABLE collection_artifacts ADD COLUMN tags_json TEXT NULL;  -- JSON array string
ALTER TABLE collection_artifacts ADD COLUMN version VARCHAR(50) NULL;
ALTER TABLE collection_artifacts ADD COLUMN source VARCHAR(255) NULL;
ALTER TABLE collection_artifacts ADD COLUMN origin VARCHAR(50) NULL;
ALTER TABLE collection_artifacts ADD COLUMN origin_source VARCHAR(50) NULL;
ALTER TABLE collection_artifacts ADD COLUMN resolved_sha VARCHAR(64) NULL;
ALTER TABLE collection_artifacts ADD COLUMN resolved_version VARCHAR(50) NULL;
ALTER TABLE collection_artifacts ADD COLUMN synced_at DATETIME NULL;

-- Add index for staleness queries
CREATE INDEX idx_collection_artifacts_synced_at ON collection_artifacts(synced_at);
```

### Database Constraints

- No new unique constraints (composite PK already exists)
- Existing foreign keys and cascades preserved
- All new columns nullable (backward compatible)

---

## Success Metrics

| Metric | Baseline | Target | Verification |
|--------|----------|--------|--------------|
| /collection page response time | 800-1500ms | <100ms | APM/Chrome DevTools |
| Database queries for /collection | Mixed (file + DB) | 100% database | Query logging |
| Metadata freshness | Variable | ≤30 minutes stale | Timestamps in DB |
| Cache hit rate | N/A | >95% | Log metrics |
| Startup time | 2-3s | <5s with cache | Server logs |
| Artifact visibility latency (CLI→Web) | N/A | <1 second | E2E test timing |

---

## Post-Implementation

### Monitoring

Add to observability dashboard:

```python
# Log on startup
logger.info(f"CollectionArtifact metadata cache: {metadata_stats}")

# Log on refresh
logger.info(f"Metadata refresh: {refresh_stats}")

# Log staleness
logger.info(f"Cache staleness: {cache_stats}")
```

### Validation Checklist

- [ ] All acceptance criteria met per task
- [ ] All quality gates passed per phase
- [ ] No P0/P1 bugs in first week post-merge
- [ ] Success metrics achieved
- [ ] End-to-end test: CLI add → web visibility working

### Future Enhancements

**Phase 5 (Groundwork Included)**: Web-based artifact editing
- Architecture and service design documented in this plan
- Implementation deferred until web editing feature prioritized
- Ensures correct data flow: Web → File → DB Cache

**Deferred to subsequent PRD**:

1. **Web artifact creation**: Add new artifacts via web UI (builds on Phase 5)
2. **Unified ID scheme**: Same artifact IDs across CLI and web (medium priority)
3. **Optimistic locking**: Prevent CLI/web edit conflicts (builds on Phase 5)
4. **Analytics tracking**: Usage stats from database queries (low priority)

### Documentation

Create/update:

1. **ADR: Artifact Metadata Caching Strategy** - Decision to implement TTL-based caching
2. **Architecture update**: Dual-system architecture now includes cache layer
3. **API documentation**: New refresh-cache endpoints
4. **Operational guide**: Cache monitoring and invalidation procedures

---

## Resource Requirements

### Subagent Assignments

| Agent | Primary Phases | Estimated Hours |
|-------|---------------|-----------------|
| `python-backend-engineer` | Phase 1, 2, 3 | 8-12 hours |
| `python-backend-engineer` (tests) | All phases | 2-3 hours |

### Key Files Reference

**Backend**:
- `skillmeat/cache/models.py` - CollectionArtifact model (Phase 1)
- `skillmeat/api/routers/user_collections.py` - Endpoints (Phase 2, 3)
- `skillmeat/api/services/artifact_metadata_service.py` - Fallback metadata service (Phase 2+)
- `skillmeat/api/services/artifact_cache_service.py` (NEW - Phase 3)
- `skillmeat/api/services/background_tasks.py` (NEW - Phase 4, optional)
- `alembic/versions/` - Database migration (Phase 1)

**Frontend** (No changes):
- `/collection` page uses existing `useInfiniteCollectionArtifacts` hook
- Already benefits from faster API responses after Phase 1-3

**Core**:
- `skillmeat/core/artifact.py` - Reference for metadata field names
- `skillmeat/core/collection.py` - CollectionManager reference

---

## Related Work

This enhancement builds on:

1. **collection-data-consistency-v1** (completed): Established database-backed collections and fixed N+1 queries
2. **dual-collection-system-architecture** (analysis): Confirms file-based + database dual design is intentional
3. **manage-collection-page-architecture** (design): Specifies how pages use endpoints

Complements:

- **Phase 4 (completed)**: CollectionCountCache - Similar TTL-based caching pattern for counts
- **Phase 5 (completed)**: DataPrefetcher - Frontend prefetching benefits from faster API responses

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-01
**Status**: Ready for Phase 1 execution
