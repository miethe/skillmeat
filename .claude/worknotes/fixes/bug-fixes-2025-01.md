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

---

## Upstream Diff Fetch Error in UnifiedEntityModal

**Date Fixed**: 2026-01-08
**Severity**: medium
**Component**: web/entity/unified-entity-modal

**Issue**: The Sync Status tab in the UnifiedEntityModal was throwing API errors when opened for non-GitHub artifacts:
```
Upstream diff fetch error: ApiError: Request failed
    at apiRequest (api.ts:87:11)
    at async UnifiedEntityModal.useQuery (unified-entity-modal.tsx:445:26)
```

**Root Cause**: The `unified-entity-modal.tsx` component has its own upstream diff query (separate from `SyncStatusTab`) that was missing the source validation guards added to `sync-status-tab.tsx` in commit `738d46f`.

The insufficient guard at line 461:
```typescript
enabled: activeTab === 'sync' && !!entity?.id && entity?.collection !== 'discovered',
```

Allowed the query to fire for:
- Marketplace artifacts without GitHub upstream tracking
- Local artifacts with `source === 'local'`
- Artifacts with unknown/missing source info

The backend returned 400/404 errors for these cases since they don't have GitHub upstream sources.

**Fix**: Updated the `enabled` condition to match the guards in `sync-status-tab.tsx`:
```typescript
enabled: activeTab === 'sync'
  && !!entity?.id
  && !!entity?.source
  && entity.source !== 'local'
  && entity.source !== 'unknown'
  && entity?.collection !== 'discovered'
  && (entity.source.includes('/') || entity.source.includes('github')),
```

**Files Modified**:
- `skillmeat/web/components/entity/unified-entity-modal.tsx` - Lines 461-467: Added source validation guards

**Testing**: TypeScript compilation passes, no lint errors in modified file

**Commit**: dcfec9b

**Status**: RESOLVED

---

## Marketplace Duplicate Detection Not Persisting to Catalog

**Date Fixed**: 2026-01-08
**Severity**: high
**Component**: api/marketplace

**Issue**: When scanning a marketplace source:
1. Scan completion message showed correct duplicate counts (e.g., "4 Within-Source Duplicates, 1 New")
2. But catalog displayed ALL artifacts marked as "New"
3. `showOnlyDuplicates` toggle had no effect on displayed artifacts

**Root Cause**: Two related bugs:

1. **Catalog entry creation ignored exclusion metadata**:
   - `MarketplaceCatalogEntry` creation (lines 479-493 in `marketplace_sources.py`) always set `status="new"`
   - Ignored `excluded_at`, `excluded_reason`, and `status` from `DetectedArtifact` after deduplication
   - Deduplication engine correctly marked duplicates with `status="excluded"`, `excluded_reason="duplicate_within_source"`, but these weren't persisted

2. **Missing `is_duplicate` field in API response**:
   - `CatalogEntryResponse` schema lacked `is_duplicate` boolean field
   - Frontend filtering at `page.tsx:445` used `entry.is_duplicate === true`
   - Since field was always undefined, filter never matched

**PRD Reference**: `docs/project_plans/PRDs/features/marketplace-source-detection-improvements-v1.md` sections 3.2.1-3.2.4

**Fix**:

1. **Catalog entry creation** now copies exclusion metadata:
```python
entry = MarketplaceCatalogEntry(
    ...
    status=artifact.status if artifact.status else "new",
    excluded_at=datetime.fromisoformat(artifact.excluded_at) if artifact.excluded_at else None,
    excluded_reason=artifact.excluded_reason,
)
```

2. **Added `is_duplicate` field** to `CatalogEntryResponse`:
```python
is_duplicate: bool = Field(
    default=False,
    description="Whether this artifact was excluded as a duplicate (within-source or cross-source)",
)
```

3. **`entry_to_response()` computes `is_duplicate`**:
```python
is_duplicate = entry.excluded_reason in ("duplicate_within_source", "duplicate_cross_source") if entry.excluded_reason else False
```

**Files Modified**:
- `skillmeat/api/routers/marketplace_sources.py` - Lines 491-508: Copy exclusion metadata; Lines 330-339, 359: Compute is_duplicate
- `skillmeat/api/schemas/marketplace.py` - Lines 1128-1131: Added is_duplicate field

**Testing**:
- Deduplication tests: 79 passed
- Rescan integration tests: 7 passed
- TypeScript build: Passes

**Commit**: 3aba5fa

**Status**: RESOLVED

---

## Sync Status Tab 404 Errors for Local-Only Artifacts

**Date Fixed**: 2026-01-08
**Severity**: medium
**Component**: web/sync-status, web/unified-entity-modal

**Issue**: The Sync Status tab was failing with 404 errors for a subset of artifacts. The `/upstream-diff` API request returned 404 for local-only artifacts, causing the entire tab to fail to load.

**Root Cause**: Two issues:

1. **Incomplete source validation guards**: Both `unified-entity-modal.tsx` and `sync-status-tab.tsx` checked `entity.source !== 'local'` but missed:
   - Sources starting with `'local:'` prefix (e.g., `'local:/path/to/artifact'`)
   - The `entity.source.includes('/')` check falsely matched local paths

2. **Blocking error handling**: In `sync-status-tab.tsx`, when upstream-diff returned 404 (expected for local artifacts), the entire tab showed an error, even if project-diff was available:
   ```typescript
   const error = upstreamError || projectError;
   if (error) { return <Alert variant="destructive">... }
   ```

**Fix**:

1. **Added helper function** to consistently validate upstream sources:
   ```typescript
   function hasValidUpstreamSource(source: string | undefined | null): boolean {
     if (!source) return false;
     if (source === 'local' || source === 'unknown') return false;
     if (source.startsWith('local:')) return false;
     return source.includes('/') && !source.startsWith('local');
   }
   ```

2. **Simplified query enabled conditions** in both files to use the helper

3. **Improved error handling** in `sync-status-tab.tsx`:
   - Only block tab when BOTH queries fail, or when project query fails for local artifacts
   - Show partial data when available (e.g., project diff without upstream)

**Files Modified**:
- `skillmeat/web/components/entity/unified-entity-modal.tsx` - Added `hasValidUpstreamSource` helper, simplified enabled condition
- `skillmeat/web/components/sync-status/sync-status-tab.tsx` - Added helper, improved error handling logic

**Testing**: ESLint passes for modified files, pre-existing type errors in test files unrelated to changes

**Commit**: ee6f9ba

**Status**: RESOLVED
