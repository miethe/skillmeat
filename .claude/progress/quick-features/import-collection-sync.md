# Quick Feature: Import-Collection Sync & Tag Propagation

**Status**: completed
**Created**: 2026-01-21
**Branch**: feat/tags-imported-meta

## Problem Statement

Two related issues:

### Issue 1: Imported artifacts don't show in Default collection view

**Root Cause**: SkillMeat has TWO collection systems:
1. **File-system collections** (`~/.skillmeat/collection/collection.toml`) - managed by `CollectionManager`
2. **Database collections** (`user_collections` + `collection_artifacts` tables) - used by `/collection` page

The `ImportCoordinator._update_manifest()` adds artifacts to the **file-system** collection but NOT to the **database**. The frontend's Default collection view queries the database via `GET /api/v1/user-collections/{id}/artifacts`, which returns empty because the database `collection_artifacts` table was never populated.

**Solution**: After successful import, also add artifacts to the database default collection (`collection_artifacts` table).

### Issue 2: Path tags approved on Source detail page don't sync to collection artifacts

**Root Cause**: When a user approves a path-based tag via `PATCH /marketplace/sources/{id}/catalog/{entryId}/path-tags`, the tag is stored only in the source catalog entry's metadata. If the artifact was already imported to the collection, the collection artifact doesn't receive the updated tag.

**Solution**: Add a sync mechanism that propagates approved tags from source catalog entries to their corresponding collection artifacts.

## Implementation Plan

### Phase 1: Fix Import → Default Collection Sync (Bug Fix)

**Files to modify**:
- `skillmeat/api/routers/marketplace_sources.py` - `import_artifacts()` endpoint

**Changes**:
1. After `ImportCoordinator.import_entries()` succeeds, get the artifact IDs of successfully imported artifacts
2. Add them to the database default collection using existing `CollectionArtifact` model
3. Ensure this happens within the same transaction context

**Pattern to follow** (from `user_collections.py:migrate_artifacts_to_default_collection`):
```python
from skillmeat.api.routers.user_collections import DEFAULT_COLLECTION_ID, ensure_default_collection
from skillmeat.api.models.collection import CollectionArtifact

# After successful import
ensure_default_collection(session)
for entry in import_result.entries:
    if entry.status.value == "success":
        artifact_id = f"{entry.artifact_type}:{entry.name}"
        association = CollectionArtifact(
            collection_id=DEFAULT_COLLECTION_ID,
            artifact_id=artifact_id,
            added_at=datetime.utcnow(),
        )
        session.merge(association)  # merge is idempotent
session.commit()
```

### Phase 2: Tag Sync from Source to Collection (Enhancement)

**Files to modify**:
- `skillmeat/api/routers/marketplace_sources.py` - `update_path_tag_status()` endpoint
- `skillmeat/core/collection.py` - add `update_artifact_tags()` method

**Changes**:
1. After tag approval in `update_path_tag_status()`:
   - Check if artifact is already in collection (use existing `collection_mgr.artifact_in_collection()`)
   - If yes, retrieve the collection artifact and merge the newly approved tag
   - Save updated artifact via `collection_mgr.save_collection()`

2. Add helper method `CollectionManager.update_artifact_tags()`:
   - Takes artifact_id (type:name), collection_name, tags_to_add
   - Loads collection, finds artifact, merges tags, saves
   - Returns success/failure

**API Endpoint for explicit sync** (optional):
- `POST /marketplace/sources/{id}/catalog/{entryId}/sync-to-collection`
- Syncs all approved tags from catalog entry to collection artifact

## Files Affected

1. `skillmeat/api/routers/marketplace_sources.py` - import endpoint, tag endpoint
2. `skillmeat/core/collection.py` - tag update helper
3. `skillmeat/core/marketplace/import_coordinator.py` - minor (already done)

## Testing Checklist

- [x] Import artifact → appears in Default collection view immediately
- [x] Import artifact → appears in All Collections view
- [x] Approve path tag on imported artifact → tag appears on collection artifact
- [x] Multiple tag approvals accumulate correctly
- [x] Re-importing same artifact doesn't duplicate in collection
- [x] Tag sync is idempotent

## Implementation Summary

### Changes Made

**File: `skillmeat/api/routers/marketplace_sources.py`**

1. **Added database session dependency** (lines 108-147):
   - `get_db_session()` generator function
   - `DbSessionDep` type alias
   - `ensure_default_collection()` helper function

2. **Modified `import_artifacts()` endpoint** (lines 2402-2515):
   - Added `session: DbSessionDep` parameter
   - After file-system import succeeds, now also adds artifacts to database `collection_artifacts` table
   - Uses `session.merge()` for idempotent operation (no duplicates)
   - Errors during DB sync are logged but don't fail the import

3. **Modified `update_path_tag_status()` endpoint** (lines 3082-3247):
   - Added `collection_mgr: CollectionManagerDep` parameter
   - After tag is approved, checks if artifact is in collection
   - If yes, syncs the approved tag to the collection artifact
   - Uses existing `artifact_in_collection()` and `save_collection()` methods
   - Errors during sync are logged but don't fail the tag update

## Success Criteria

1. Newly imported artifacts immediately visible in `/collection` Default view
2. Path tag approval automatically propagates to collection artifact
3. No manual migration or refresh required

---

## Follow-up Fix (2026-01-21 Session 2)

### Issue 1: Source Field Display Format

**Problem**: Source field showed full GitHub URLs (`https://github.com/owner/repo/tree/sha/path`) instead of expected short format (`owner/repo/path`).

**Fix**: Added `_url_to_short_source()` helper in `import_coordinator.py` to convert URLs to short format.

**File**: `skillmeat/core/marketplace/import_coordinator.py`
- Added `_url_to_short_source()` method (lines 550-575)
- Updated `_update_manifest()` to use short format (line 401, 411)

### Issue 2: Collection Page Refresh

**Problem**: After import, `/collection` page didn't show new artifacts until manual refresh.

**Root Cause**: Frontend cache invalidation targeted `['artifacts']` but collection page uses `['collections', 'default', 'infinite-artifacts']`.

**Fix**: Added collection query invalidation in `useImportArtifacts` hook.

**File**: `skillmeat/web/hooks/useMarketplaceSources.ts`
- Added `queryClient.invalidateQueries({ queryKey: ['collections'] });` (line 289)

---

## Follow-up Fix 2 (2026-01-21 Session 3)

### Issue 1: Source Field Showing Wrong Format

**Problem**: Source field was showing `TYPE:NAME` format instead of full GitHub URL.

**Root Cause**: Previous fix incorrectly converted full URLs to short format. Also, the frontend `Artifact` TypeScript type was missing `origin` and `origin_source` fields, and the `artifactToEntity()` mapping wasn't passing these fields.

**Fixes Applied**:

1. **Reverted short URL change** in `skillmeat/core/marketplace/import_coordinator.py`
   - Changed `upstream=short_source` back to `upstream=entry.upstream_url`
   - Full GitHub URLs are now preserved (e.g., `https://github.com/owner/repo/tree/sha/path`)

2. **Added origin fields to TypeScript** in `skillmeat/web/types/artifact.ts`
   - Added `origin?: string` field
   - Added `origin_source?: string` field

3. **Updated artifactToEntity() mapping** in `skillmeat/web/app/collection/page.tsx`
   - Added `origin: artifact.origin` mapping
   - Added `origin_source: artifact.origin_source` mapping

### Result
- **Source field**: Now displays full GitHub URL from `artifact.upstream`
- **Origin badge**: Shows "local", "github", or "marketplace"
- **Origin Source badge**: Shows "github", "gitlab", etc. (when origin is "marketplace")
