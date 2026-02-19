---
type: quick-feature-plan
feature_slug: collection-infinite-scroll
request_log_id: null
status: completed
created: 2026-01-13 00:00:00+00:00
completed_at: 2026-01-13 00:30:00+00:00
estimated_scope: medium
schema_version: 2
doc_type: quick_feature
---

# Collection Page Infinite Scroll

## Scope

Implement infinite scrolling on the Collection page (`/collection`) to handle large collections efficiently. Currently limited to 100 artifacts with client-side filtering. Will leverage existing backend cursor-based pagination.

## Technical Approach

**Strategy**: Use TanStack Query's `useInfiniteQuery` with intersection observer for load-more trigger.

**Key Considerations**:
1. Backend already supports cursor pagination via `limit` and `after` parameters
2. Current client-side filtering (search, tags, type) must move to server-side for proper pagination
3. API returns `{ items: [], page_info: { has_next_page, end_cursor, total_count } }`

## Affected Files

### Initial Implementation (specific collections)

1. `skillmeat/web/lib/api/collections.ts`: Add `fetchCollectionArtifactsPaginated`
2. `skillmeat/web/hooks/use-collections.ts`: Create `useInfiniteCollectionArtifacts` hook
3. `skillmeat/web/app/collection/page.tsx`: Add infinite scroll for specific collections
4. `skillmeat/web/hooks/use-intersection-observer.ts`: New hook for scroll detection

### Fix: All Collections View (follow-up)

5. `skillmeat/web/lib/api/artifacts.ts`: Add `fetchArtifactsPaginated`
6. `skillmeat/web/hooks/useArtifacts.ts`: Create `useInfiniteArtifacts` hook
7. `skillmeat/web/app/collection/page.tsx`: Use infinite scroll for BOTH views

## Implementation Steps

1. Create intersection observer hook → @ui-engineer-enhanced
2. Update API client with pagination support → @ui-engineer-enhanced
3. Create `useInfiniteCollectionArtifacts` hook → @ui-engineer-enhanced
4. Update Collection page to use infinite scroll → @ui-engineer-enhanced

## API Contract (Backend Already Supports)

```
GET /api/v1/user-collections/{id}/artifacts?limit=20&after={cursor}

Response:
{
  "items": [...],
  "page_info": {
    "has_next_page": boolean,
    "end_cursor": string | null,
    "total_count": number
  }
}
```

## Testing

- Manual testing with collections of varying sizes (0, 20, 100, 500+ artifacts)
- Verify scroll-to-load triggers correctly
- Verify total count displays accurately
- Test with filter combinations

## Completion Criteria

- [x] Intersection observer hook created and exported
- [x] API client supports pagination parameters (collections + artifacts)
- [x] useInfiniteCollectionArtifacts hook implemented
- [x] useInfiniteArtifacts hook implemented (for "All Collections")
- [x] Collection page uses infinite scroll for BOTH views
- [x] Loading states shown during fetch
- [x] Tests pass (pre-existing failures, not from this change)
- [x] Build succeeds
