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

---

## All Collection Artifacts Showing as 'discovered'

**Date Fixed**: 2025-01-07
**Severity**: high
**Component**: web/collection

**Issue**: After the previous fix, ALL artifacts on the `/collection` page were incorrectly showing as 'discovered', causing sync status and other features to treat them as marketplace artifacts not yet imported.

**Root Cause**: The previous fix changed `artifactToEntity` to use `'discovered'` as the fallback when `artifact.collection` was undefined. However, `artifact.collection` was undefined for ALL artifacts because:
1. `enrichArtifactSummary` fallback didn't set a `collection` property
2. Full artifacts from API also sometimes lacked collection info

The `/collection` page is for viewing collection artifacts (not marketplace), so the fallback should be `'default'`, not `'discovered'`.

**Fix**: Two-part fix:

1. Updated `enrichArtifactSummary` to accept optional `collectionInfo` parameter and set it on:
   - Fallback objects (line 82)
   - Full artifacts that lack collection (line 49-51)

2. Updated the call site (line 319-325) to pass `currentCollection` context when enriching summaries

3. Reverted `artifactToEntity` fallback from `'discovered'` back to `'default'` (line 98)

**Files Modified**:
- `skillmeat/web/app/collection/page.tsx` - Updated `enrichArtifactSummary`, call site, and `artifactToEntity`

**Testing**: Build passes (`pnpm build`)

**Commit**: bb3b203

**Status**: RESOLVED

---

## Sync Status Tab Blocking and 404 Errors (Comprehensive Fix)

**Date Fixed**: 2025-01-07
**Severity**: high
**Component**: web/sync-status-tab
**Related Issues**: REQ-20260107-skillmeat-01, REQ-20260107-skillmeat-02

**Issue**: Two related bugs prevented Sync Status tab from working for most/all artifacts:
1. 404 errors from upstream-diff API for artifacts without backend collection entries
2. "local-only artifact" message blocking the entire tab instead of disabling options

**Root Cause**:

1. **404 errors**: Query enabled condition passed but artifact didn't exist in backend:
   - `enabled: !!entity.source && entity.collection !== 'discovered'`
   - Artifacts with `source` set from enrichment but no actual backend collection entry

2. **Blocking behavior**: Early return at lines 312-324 completely blocked the tab:
   - `if (isLocalOnly && comparisonScope === 'source-vs-collection') { return <Alert>... }`
   - `isLocalOnly` check too broad (`!entity.source || entity.source === 'local'`)
   - Should have disabled options in ComparisonSelector instead of blocking

**Fix**: 5-part remediation (commit 4899b5b):

1. **FIX-001**: Removed early return for local-only artifacts - let ComparisonSelector handle disabled state
2. **FIX-002**: Improved hasSource detection: `!!entity.source && entity.source !== 'local' && entity.source !== 'unknown'`
3. **FIX-003**: Smart default scope based on available options (collection-vs-project if no source)
4. **FIX-004**: Strengthened query guard with source URL pattern validation
5. **FIX-005**: Added graceful empty diff state with helpful message
6. **Bonus**: Fixed pre-existing React hooks rule violation by moving early returns after hooks

**Files Modified**:
- `skillmeat/web/components/sync-status/sync-status-tab.tsx` - All fixes applied

**Testing**: Build passes (`pnpm build`), no sync-status lint errors

**Commit**: 4899b5b

**Status**: RESOLVED
