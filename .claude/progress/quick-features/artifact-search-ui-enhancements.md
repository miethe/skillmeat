# Quick Feature: Artifact Search UI Enhancements

**Status**: completed
**Created**: 2025-01-27
**Scope**: UI-only changes, 1 file

## Description

Enhance the artifact search results UI on `/marketplace/sources` page:
1. Add color-coded left border per artifact type (using existing `typeConfig` colors)
2. Replace text type badge with icon-only badge + tooltip
3. Add "Imported" indicator badge for artifacts with `status === 'imported'`

## Files to Modify

| File | Change |
|------|--------|
| `skillmeat/web/components/marketplace/artifact-search-results.tsx` | Add type icons, colors, imported badge |

## Implementation Details

### 1. Type Icon Mapping (reuse from CatalogEntryModal)

| Type | Icon | Border Color |
|------|------|--------------|
| skill | Package | blue-500 |
| command | Terminal | purple-500 |
| agent | Bot | green-500 |
| mcp | Server | orange-500 |
| mcp_server | Server | orange-500 |
| hook | Webhook | pink-500 |

### 2. Changes to `ResultCard` component

- Replace `FileCode` icon with type-specific icon
- Add colored left border based on type
- Replace text badge with icon badge + Tooltip
- Add "Imported" badge when `result.status === 'imported'`

### 3. Pattern References

- `typeConfig` from CatalogEntryModal.tsx:108-127
- `artifactTypeIcons` from collection/artifact-detail.tsx:50-55
- `statusConfig` from CatalogEntryModal.tsx:129-151

## Quality Gates

- [x] TypeScript compiles (pre-existing errors in test files only)
- [x] Linting passes
- [x] Build succeeds
- [ ] Visual check on `/marketplace/sources` page
