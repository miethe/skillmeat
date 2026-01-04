---
type: quick-feature-plan
feature_slug: marketplace-import-auto-refresh
request_log_id: null
status: completed
created: 2026-01-04T00:00:00Z
completed_at: 2026-01-04T00:00:00Z
estimated_scope: small
---

# Marketplace Import Auto-Refresh

## Scope

Fix cache invalidation bug where importing artifacts from marketplace sources doesn't trigger UI refresh. The `useImportArtifacts` hook invalidates with wrong query key pattern.

## Root Cause

`useImportArtifacts` line 274:
```typescript
queryClient.invalidateQueries({ queryKey: sourceKeys.catalog(sourceId) });
// Produces: ['marketplace-sources', 'catalog', sourceId, undefined]
```

But `useSourceCatalog` queries use:
```typescript
queryKey: sourceKeys.catalog(id, filters)
// Produces: ['marketplace-sources', 'catalog', sourceId, {type: 'skill', status: 'new', ...}]
```

The `undefined` doesn't match filters object → no invalidation.

## Fix

Use partial key pattern (already used by exclude/restore hooks):
```typescript
queryClient.invalidateQueries({ queryKey: [...sourceKeys.catalogs(), sourceId] });
// Produces: ['marketplace-sources', 'catalog', sourceId]
// This prefix-matches ALL catalog queries for this source
```

## Affected Files

- `skillmeat/web/hooks/useMarketplaceSources.ts`: Line 274 - change invalidation pattern

## Implementation Steps

1. Change line 274 from `sourceKeys.catalog(sourceId)` to `[...sourceKeys.catalogs(), sourceId]` → @ui-engineer

## Testing

- Import artifact from marketplace source page
- Verify UI updates without manual refresh
- Verify import status badge changes from "New" to "Imported"

## Completion Criteria

- [x] Implementation complete
- [ ] Manual test passes (requires user verification)
- [x] Build succeeds (pre-existing test type errors unrelated to this fix)
