# Phase 1 Context: Marketplace Catalog UX Enhancements

## Implementation Decisions

- **Pagination State**: URL-based (page, limit query params) for deep-linking support
- **Visual Separation**: Combination of subtle border-top and semi-transparent bg (avoid aggressive glassmorphism)
- **Artifact Count**: Display format "Showing X of Y artifacts" above pagination controls
- **Directory Extraction**: Recursive descent to parse marketplace source structure for tag suggestions
- **Component Reuse**: Leverage existing Radix UI Button, Dialog, Select components from shadcn
- **No Backend Changes**: All 4 features are frontend-only; leverage existing API endpoints

## Technical Patterns Used

- **TanStack Query Hooks**: useMarketplaceSourceArtifacts with page/limit params, automatic refetch on state change
- **Next.js Dynamic Routes**: [id] param from marketplace sources catalog endpoint
- **React State Management**: URLSearchParams for pagination (via Next.js useSearchParams)
- **Dialog Pattern**: Radix Dialog wrapper for bulk tag dialog (following SkillMeat conventions)
- **Recursive Directory Parsing**: Extract artifact directories and group by type for tag suggestions

## Gotchas and Learnings

- **Pagination Sync**: useSearchParams() reads client-side; must use useRouter().push() to update URL without page reload
- **Query Key Invalidation**: TanStack Query keys must include page/limit to trigger refetch on param change
- **Directory Structure Variance**: Different marketplace sources may have different artifact layouts; extraction logic must be robust to missing directories
- **Tag Suggestion Scope**: Only suggest tags for artifacts in current view (not entire source) to avoid overwhelming UI
- **API Pagination**: Backend returns total_count; use for "X of Y" display and pagination calculations

## Key Files Modified

- `skillmeat/web/app/marketplace/sources/[id]/page.tsx`: Add pagination controls and artifact count
- `skillmeat/web/app/marketplace/sources/[id]/components/catalog-list.tsx`: Integrate URL-based pagination state
- `skillmeat/web/components/marketplace/pagination-controls.tsx`: New pagination UI component (numbered pages, items/page)
- `skillmeat/web/components/marketplace/bulk-tag-dialog.tsx`: New dialog for directory-level tag suggestions
- `skillmeat/web/lib/marketplace/directory-extraction.ts`: Utility to parse marketplace source structure

## Integration Points

- **Catalog List Hook**: useMarketplaceSourceArtifacts() receives page/limit params, triggers refetch on change
- **URL State**: URLSearchParams in [id]/page.tsx manages page and limit
- **Dialog Trigger**: Bulk tag button in pagination bar opens dialog, receives directory structure from extraction util
- **Cache Invalidation**: Pagination changes trigger query refetch via TanStack Query key matching

## Implementation Scope

Phase 1 deliverables:
1. ✓ Pagination controls (numbered pages + items/page selector)
2. ✓ Visual separation for pagination bar
3. ✓ Artifact count display
4. ✓ Bulk tag dialog scaffold (dialog opens, closes; tag suggestions structure)

Not in Phase 1:
- Tag application logic (deferred to Phase 2)
- Backend tag persistence (Phase 2+)
- Advanced filtering by tags (Phase 2+)

## Context for AI Agents

**When implementing features**:
- Check useMarketplaceSourceArtifacts hook for current page/limit handling
- Verify URL param sync with component state (no client-side desyncs)
- Ensure pagination calculations account for backend total_count
- Test with sources having 50+ artifacts (to verify pagination behavior)
- Directory extraction must handle edge cases (missing /artifacts dir, flat structures)

**When debugging**:
- Query keys: collectionKeys structure in hooks/use-marketplace-sources.ts
- Pagination params: page (1-indexed), limit (items per page)
- Dialog trigger: bulk-tag-dialog visibility state and initial data
- API endpoint: GET /marketplace-sources/{id}/artifacts with ?page=X&limit=Y
