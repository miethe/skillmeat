---
type: quick-feature-plan
feature_slug: marketplace-auto-refresh-on-exclude
request_log_id: null
status: completed
completed_at: 2026-01-03T00:00:00Z
created: 2026-01-03T00:00:00Z
estimated_scope: small
---

# Auto-refresh Marketplace Source Page After Artifact Exclusion

## Scope

Fix cache invalidation in `useExcludeCatalogEntry` and `useRestoreCatalogEntry` hooks so that when an artifact is marked as "Not an artifact", the UI auto-updates without requiring manual page refresh.

## Root Cause

The invalidation uses `sourceKeys.catalog(sourceId)` which produces:
```
['marketplace-sources', 'catalog', sourceId, undefined]
```

But the actual query uses filters, producing:
```
['marketplace-sources', 'catalog', sourceId, {...filters}]
```

TanStack Query prefix matching doesn't match `undefined` to actual filter objects.

## Fix

Change invalidation key from:
```typescript
queryClient.invalidateQueries({ queryKey: sourceKeys.catalog(sourceId) });
```

To:
```typescript
queryClient.invalidateQueries({ queryKey: [...sourceKeys.catalogs(), sourceId] });
```

This produces `['marketplace-sources', 'catalog', sourceId]` which matches ALL queries for that source.

## Affected Files

- `skillmeat/web/hooks/useMarketplaceSources.ts`: Fix invalidation in `useExcludeCatalogEntry` (line 353) and `useRestoreCatalogEntry` (line 386)

## Implementation Steps

1. Fix `useExcludeCatalogEntry` onSuccess invalidation → @ui-engineer
2. Fix `useRestoreCatalogEntry` onSuccess invalidation → @ui-engineer

## Testing

- Manual test: Mark artifact as "Not an artifact" → should disappear from grid without refresh
- Manual test: Restore artifact → should reappear without refresh

## Completion Criteria

- [x] Implementation complete
- [ ] Manual testing verified
- [x] Build succeeds
