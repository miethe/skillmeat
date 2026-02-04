# Implementation Plan: Wire Tag ORM Sync to File-Based Tags

**Status**: Complete
**Branch**: `feat/refresh-metadata-extraction-v1`
**Commits**: `7ca9f1a3`, `1b840374`

---

## Problem

The Tag/ArtifactTag ORM tables were out of sync with the consolidated file-based `Artifact.tags`. `TagService.sync_artifact_tags()` existed and worked correctly, but was only called from the artifact parameter-update endpoint (`routers/artifacts.py`). It was never called during startup cache population, batch cache refresh, single collection refresh, or single artifact cache refresh.

This caused `/settings/tags` to show incomplete tags with 0 artifact counts. A frontend workaround in `tag-manager.tsx` fetched all artifacts and merged inline tags client-side.

## Architecture Context

| System | Storage | Source of Truth? |
|--------|---------|-----------------|
| #1 File-based `Artifact.tags` | YAML/TOML files on disk | YES |
| #2 `CollectionArtifact.tags_json` | SQLite cache column | Cache of #1 |
| #3 `Tag` + `ArtifactTag` ORM tables | SQLite tables | Should mirror #1 |

**Key insight**: `TagService` creates its own `TagRepository` with its own DB session (via `_get_session()`). It does NOT share sessions with the cache population code. Sync can be called independently after cache refresh.

## Changes Made

### Backend (commit `7ca9f1a3`)

| File | Change |
|------|--------|
| `skillmeat/api/routers/user_collections.py` | Added `_sync_all_tags_to_orm()` helper; called after `populate_collection_artifact_metadata()` in `migrate_artifacts_to_default_collection()`; added per-artifact tag sync in `_refresh_single_collection_cache()` |
| `skillmeat/api/services/artifact_cache_service.py` | Added tag sync call in `refresh_single_artifact_cache()` after session commit |

Design decisions:
- All tag sync calls use **lazy imports** to prevent circular import issues
- All calls wrapped in **try/except** -- tag sync failure logged at warning level but never blocks primary operation
- `TagService()` instantiated with **zero-arg constructor** (creates own internal DB session)
- In batch path, `TagService` instantiated **once** at function start, reused across loop

### Frontend (commit `1b840374`)

| File | Change |
|------|--------|
| `skillmeat/web/components/settings/tag-manager.tsx` | Removed `useArtifacts` hook, `useMemo` merge logic, `isInlineOnly` property, and conditional rendering. Reverted to simple `useTags(100)` data source. |

Removed ~100 lines of workaround code. All CRUD functionality preserved.

## Quality Gates

- Backend: No new test failures (pre-existing collection errors unrelated)
- Frontend type-check: No errors in `tag-manager.tsx` (pre-existing errors in test files unrelated)
- Frontend lint: No errors in `tag-manager.tsx`

## Verification Steps

1. Start dev server: `skillmeat web dev`
2. Navigate to `/settings/tags` -- all tags from artifacts should appear
3. Artifact counts should be non-zero and match `/collection` page counts
4. Create/rename/delete tags -- CRUD should work normally
5. Trigger cache refresh via API (`POST /api/v1/user-collections/refresh-cache`) -- tags should update
