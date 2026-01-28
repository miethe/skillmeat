# Artifact Modal Architecture Analysis

**Date**: 2026-01-28
**Context**: Analysis of three related bugs in artifact modals across /collection and /manage pages
**Status**: Quick fixes applied, architectural recommendations documented

## Executive Summary

Three bugs were identified and fixed related to artifact modal functionality:
1. Collections tab empty on /manage page
2. Source tab not appearing until visiting /marketplace/sources
3. Source link navigation non-functional on /collection page

While quick fixes resolved the immediate issues, the root causes reveal architectural inconsistencies that could benefit from future refactoring.

## Bug Analysis

### Bug 1: Collections Tab Empty on /manage Page

**Root Cause**: Two different mapping functions convert API responses to Entity objects:
- `mapApiArtifactToEntity()` in `useEntityLifecycle.tsx` (used by /manage)
- `artifactToEntity()` in `collection/page.tsx` (used by /collection)

The useEntityLifecycle version was missing the `collections` field mapping.

**Fix Applied**: Added collections mapping to `mapApiArtifactToEntity()`.

**Architectural Issue**: **Duplicate mapping logic** - Two separate functions that should produce identical Entity objects from API data.

### Bug 2: Source Tab Missing Until Visiting /marketplace/sources

**Root Cause**: The `useSources()` hook uses TanStack Query's `useInfiniteQuery` with lazy loading. Data isn't fetched until explicitly requested. When a user opens an artifact modal, the sources data hasn't been loaded unless they've previously visited /marketplace/sources (which populates the cache).

**Fix Applied**: Modified unified-entity-modal to trigger `fetchNextPage()` when sources data is empty.

**Architectural Issue**: **Implicit cache dependency** - Feature functionality depends on React Query cache being pre-populated by unrelated user navigation.

### Bug 3: Source Link Navigation Broken on /collection Page

**Root Cause**: The /collection page didn't pass `onNavigateToSource` and `onNavigateToDeployment` handlers to `UnifiedEntityModal`, while /manage page did.

**Fix Applied**: Added the navigation handlers to collection/page.tsx.

**Architectural Issue**: **Inconsistent component usage** - Same modal component used differently across pages without clear contract enforcement.

## Architectural Recommendations

### Recommendation 1: Centralize Entity Mapping (Priority: High)

**Current State**: Multiple mapping functions (`mapApiArtifactToEntity`, `artifactToEntity`) scattered across files.

**Recommended State**: Single source of truth for API → Entity mapping.

**Implementation**:
```typescript
// lib/api/mappers.ts
export function mapArtifactResponseToEntity(
  response: ArtifactResponse,
  mode: 'collection' | 'project' = 'collection'
): Entity {
  // Single comprehensive mapping
}
```

**Benefits**:
- Eliminates field omission bugs
- Single place to update when API changes
- Type safety enforcement

**Effort**: Low (1-2 hours)

### Recommendation 2: Preload Critical Data at App Level (Priority: Medium)

**Current State**: Sources data only loads when user visits /marketplace/sources or when modal explicitly triggers fetch.

**Recommended State**: Critical shared data preloaded at app initialization.

**Implementation Options**:

A. **Provider-level prefetch** (Recommended):
```typescript
// app/providers.tsx
function DataPrefetcher({ children }) {
  // Prefetch sources list at app startup
  useSources(50); // Loads into cache
  return children;
}
```

B. **Query prefetching in layout**:
```typescript
// app/layout.tsx
queryClient.prefetchInfiniteQuery({
  queryKey: sourceKeys.lists(),
  queryFn: ...
});
```

**Benefits**:
- Features work immediately without navigation dependencies
- Better perceived performance
- Eliminates race conditions

**Effort**: Low (1 hour)

### Recommendation 3: Component Props Contract Enforcement (Priority: Medium)

**Current State**: Optional props in `UnifiedEntityModal` lead to silent feature degradation when handlers aren't provided.

**Recommended State**: Either enforce required handlers or handle missing handlers gracefully with user feedback.

**Implementation Options**:

A. **Make navigation handlers required when entity has source**:
```typescript
interface UnifiedEntityModalProps {
  entity: Entity | null;
  open: boolean;
  onClose: () => void;
  // Required when entity has source
  onNavigateToSource: (sourceId: string, path: string) => void;
  onNavigateToDeployment: (projectPath: string, artifactId: string) => void;
}
```

B. **Add runtime warning when handlers missing**:
```typescript
if (entity?.source && !onNavigateToSource) {
  console.warn('UnifiedEntityModal: onNavigateToSource not provided for entity with source');
}
```

C. **Create page-specific modal wrappers** that ensure proper handlers:
```typescript
// components/collection/CollectionArtifactModal.tsx
export function CollectionArtifactModal({ entity, open, onClose }) {
  const router = useRouter();
  return (
    <UnifiedEntityModal
      entity={entity}
      open={open}
      onClose={onClose}
      onNavigateToSource={(sid, path) => router.push(...)}
      onNavigateToDeployment={(pp, aid) => router.push(...)}
    />
  );
}
```

**Effort**: Medium (2-4 hours)

### Recommendation 4: Consider Database-Backed Collections (Priority: Low, Long-term)

**Current State**: Collection membership appears to be computed/joined at API response time. The `collections` array on artifacts may not always be populated depending on the API endpoint called.

**Observation**: The /collection page uses `useInfiniteCollectionArtifacts` which returns lightweight summaries that need enrichment. The /manage page uses `useEntityLifecycle` which calls `/artifacts` endpoint.

**Potential Issue**: If different API endpoints return different collection membership data, the UI will show inconsistent information.

**Recommendation**: Ensure all artifact-returning endpoints include consistent `collections` array data, or create a dedicated endpoint for fetching artifact collection membership.

**Effort**: Medium-High (requires backend investigation)

## Fixes Applied (2026-01-28)

| File | Change |
|------|--------|
| `hooks/useEntityLifecycle.tsx` | Added `collections` mapping to `mapApiArtifactToEntity()` |
| `components/entity/unified-entity-modal.tsx` | Added eager fetch for sources data when modal opens |
| `app/collection/page.tsx` | Added `onNavigateToSource` and `onNavigateToDeployment` handlers |

## Testing Verification

After fixes, verify:
1. Open artifact from /manage page → Collections tab shows collections
2. Fresh app start → Open artifact from /collection → Source tab appears (with loading state)
3. Click source link from /collection modal → Navigates to source detail page

## Related Files

- `skillmeat/web/hooks/useEntityLifecycle.tsx` - Entity mapping and lifecycle
- `skillmeat/web/components/entity/unified-entity-modal.tsx` - Unified modal component
- `skillmeat/web/app/collection/page.tsx` - Collection page
- `skillmeat/web/app/manage/page.tsx` - Management page
- `skillmeat/web/components/entity/modal-collections-tab.tsx` - Collections tab component
- `skillmeat/web/hooks/useMarketplaceSources.ts` - Sources data hook
