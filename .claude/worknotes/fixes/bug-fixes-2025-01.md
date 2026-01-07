# Bug Fixes - January 2025

## Sync Status Tab 404 for Marketplace Artifacts

**Date Fixed**: 2025-01-07
**Severity**: medium
**Component**: web/collection

**Issue**: The Sync Status tab in unified entity modals on the `/collection` page was failing with 404 errors for marketplace artifacts. Log showed:
```
GET /api/v1/artifacts/skill%3ADesign%20Principles/upstream-diff HTTP/1.1" 404
```

**Root Cause**: In `app/collection/page.tsx`, the `artifactToEntity` function set `collection: artifact.collection?.name || 'default'`. When marketplace artifacts (scanned from GitHub but not yet imported to a user collection) had no `artifact.collection`, they defaulted to `'default'` - a real collection name - instead of `'discovered'` - the marker for unimported artifacts.

This caused `sync-status-tab.tsx` to pass its guard condition `entity.collection !== 'discovered'` (line 269), triggering an upstream-diff API call that failed because the artifact doesn't exist in any collection yet.

**Fix**: Changed the fallback from `'default'` to `'discovered'`:
```typescript
// Before
collection: artifact.collection?.name || 'default',

// After
const collectionName = artifact.collection?.name ?? 'discovered';
// ...
collection: collectionName,
```

**Files Modified**:
- `skillmeat/web/app/collection/page.tsx` - Updated `artifactToEntity` function (lines 89-99)

**Testing**: Build passes (`pnpm build`)

**Commit**: d6d8a0b

**Status**: RESOLVED
