# Quick Feature: Modal Tab Parity

**Status**: completed
**Created**: 2026-02-02
**Scope**: 2 files affected

## Problem Statement

The artifact modals on `/manage` and `/collection` pages have inconsistent tab availability:

1. **Manage Modal** (`artifact-operations-modal.tsx`) is missing:
   - `Sources` tab - shows upstream source catalog information
   - `Collections` tab - shows which collections artifact belongs to

2. **Collection Modal** (`artifact-details-modal.tsx`) - Tags display appears inconsistent with Manage modal (needs verification)

## Tasks

- [x] TASK-1: Explore current modal implementations
- [x] TASK-2: Add `collections` tab to Manage Modal
- [x] TASK-3: Add `sources` tab to Manage Modal
- [x] TASK-4: Verify tags display parity between modals (upgraded to editable TagEditor)
- [x] TASK-5: Run quality gates (pre-existing issues only, no new errors)

## Implementation Details

### Files to Modify

1. `skillmeat/web/components/manage/artifact-operations-modal.tsx`
   - Add 'collections' and 'sources' to `OperationsModalTab` type
   - Add tabs to `TABS` array
   - Import `ModalCollectionsTab` from `@/components/entity/modal-collections-tab`
   - Add Sources tab content (mirror from collection modal)
   - Add Collections tab content using shared component

### Reference Files

- Collection modal: `skillmeat/web/components/collection/artifact-details-modal.tsx`
- Collections tab component: `skillmeat/web/components/entity/modal-collections-tab.tsx`

## Quality Gates

```bash
cd skillmeat/web && pnpm test && pnpm typecheck && pnpm lint && pnpm build
```

## Commit

```
944ab0c9 feat(web): add collections/sources tabs to manage modal and fix modal close race condition
```

## Outstanding Issue: Tags Not Displaying on /collection Modal

**Root Cause**: Backend data caching issue, not frontend.

The `/user-collections/{id}/artifacts` endpoint uses a metadata cache (`CollectionArtifact.tags_json`), while `/artifacts` reads directly from the file system. If the cache wasn't properly populated, tags won't appear in the /collection modal.

**Fix**: Call the cache refresh endpoint:
```bash
curl -X POST http://localhost:8080/api/v1/user-collections/refresh-cache
```

This will repopulate `tags_json` from the file-based artifacts for all collections.
