# Quick Feature: Editable Tags & Filter Link

**Status**: completed
**Created**: 2026-01-22

## Feature Request

When viewing the modal for an artifact on the 'Overview' tab:
1. Tags section should always be editable
2. Each Tag should have an 'x' on hover to remove
3. '+' at the end of the list opens component to add tags
4. Shows existing global artifact tags as autocomplete options
5. Accepts new tags typed inline
6. Changes save immediately
7. All artifact tags normalized (lowercase, spaces to underscores)
8. Tags filter on /collection page linked to actual artifact tags with counts

## Implementation Plan

### Task 1: Tag Normalization Utility
- Create `normalizeTag()` function: lowercase, spaces→underscores, trim
- Update existing tag-suggestions.ts or create new utility
- Apply normalization on save (frontend + backend)

### Task 2: TagEditor Component
- New component: `TagEditor.tsx` in `web/components/shared/`
- Features:
  - Display existing tags as badges with 'x' on hover
  - '+' button at end to add new tag
  - Popover/combobox for tag selection
  - Autocomplete from existing tags (useTags hook)
  - Allow typing new tags
  - Immediate save via mutation

### Task 3: Update Artifact Modal
- Modify `unified-entity-modal.tsx` Overview tab
- Replace static tag display with TagEditor
- Wire up artifact tag update mutation

### Task 4: Backend API for Artifact Tags
- Add/update endpoint: `PUT /api/v1/artifacts/{id}/tags`
- Accept tag names (normalized), create if new
- Return updated artifact with tags

### Task 5: Fix Tags Filter Connection
- Update TagFilterPopover to query tags that are actually used by artifacts
- Add artifact count to each tag option
- Ensure filter actually filters by artifact tags field

## Files to Modify

**Frontend:**
- `web/lib/utils/tag-suggestions.ts` - Add normalizeTag()
- `web/components/shared/tag-editor.tsx` - NEW
- `web/components/entity/unified-entity-modal.tsx` - Use TagEditor
- `web/components/ui/tag-filter-popover.tsx` - Fix tag source
- `web/hooks/use-artifacts.ts` - Add tag update mutation

**Backend:**
- `api/routers/artifacts.py` - Add tags endpoint
- `api/schemas/artifacts.py` - Tag update schema

## Quality Gates
- [x] pnpm type-check (pre-existing test file errors only)
- [x] pnpm lint (pre-existing errors only, no errors in modified files)
- [x] pnpm build (success)

## Files Modified

**Frontend:**
- `web/lib/utils/tag-suggestions.ts` - Added `normalizeTagForStorage()` function
- `web/components/shared/tag-editor.tsx` - NEW - Editable tag component
- `web/components/entity/unified-entity-modal.tsx` - Integrated TagEditor
- `web/components/ui/tag-filter-popover.tsx` - Fixed to use tag names, filter zero-count tags
- `web/hooks/useArtifacts.ts` - Added `useUpdateArtifactTags` mutation
- `web/hooks/index.ts` - Exported new hook

**Backend:**
- `api/routers/artifacts.py` - Added `PUT /api/v1/artifacts/{id}/tags` endpoint
- `api/schemas/artifacts.py` - Added `ArtifactTagsUpdate` schema with normalization
