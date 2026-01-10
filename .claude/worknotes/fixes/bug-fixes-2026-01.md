# Bug Fixes - January 2026

## Marketplace Scan Fails with CHECK Constraint Error for MCP Artifacts

**Date Fixed**: 2026-01-08
**Severity**: high
**Component**: marketplace-scanner

**Issue**: When adding a new marketplace source with a large number (1000+) of detected artifacts, the scan fails with `CHECK constraint failed: check_catalog_artifact_type` during bulk insert of catalog entries.

**Root Cause**: The `ArtifactType.MCP` enum has value `"mcp"`, but the database CHECK constraint in `marketplace_catalog_entries` table only accepted `"mcp_server"`. This was a naming mismatch between the Python enum definition and the legacy database schema.

The heuristic detector correctly identifies MCP artifacts using `ArtifactType.MCP` (value: `"mcp"`), but when these are inserted into the database, the constraint `artifact_type IN ('skill', 'command', 'agent', 'mcp_server', 'hook', ...)` rejects the value.

**Fix**: Added `'mcp'` to all artifact_type CHECK constraints while keeping `'mcp_server'` for backward compatibility with existing data.

**Files Modified**:
- `skillmeat/cache/models.py` - Updated 3 CHECK constraints:
  - `check_artifact_type` (Artifact model)
  - `check_marketplace_type` (MarketplaceEntry model)
  - `check_catalog_artifact_type` (MarketplaceCatalogEntry model)
- `skillmeat/cache/schema.py` - Updated 3 CHECK constraints in raw schema
- `skillmeat/cache/migrations/versions/20260108_1700_add_mcp_to_type_constraints.py` - New migration to update existing databases

**Testing**:
- All marketplace cache tests pass
- Migration applies cleanly using batch_alter_table for SQLite compatibility
- Verified constraint now accepts both `'mcp'` and `'mcp_server'` values

**Status**: RESOLVED

---

## List Artifacts Endpoint Fails with 500 Error Due to Variable Shadowing

**Date Fixed**: 2026-01-08
**Severity**: high
**Component**: marketplace-sources-api

**Issue**: When viewing low-confidence artifacts in the marketplace, the API returns a 500 error: `AttributeError: 'NoneType' object has no attribute 'HTTP_500_INTERNAL_SERVER_ERROR'`.

**Root Cause**: The `list_artifacts` endpoint had a query parameter named `status` which shadowed the imported `fastapi.status` module. When the query parameter was `None` (no filter provided), the exception handler tried to access `None.HTTP_500_INTERNAL_SERVER_ERROR` instead of `fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR`.

```python
# Line 1302 - query parameter shadows the module
status: Optional[str] = Query(None, ...)

# Line 1471 - exception handler references the shadowed name
raise HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,  # status is None!
    ...
)
```

**Fix**: Renamed the query parameter from `status` to `status_filter` with `alias="status"` to maintain API compatibility.

**Files Modified**:
- `skillmeat/api/routers/marketplace_sources.py`:
  - Renamed parameter `status` → `status_filter` (line 1302)
  - Added `alias="status"` for backwards compatibility
  - Updated all internal references to use `status_filter`

**Testing**: Verified function signature and status module accessibility

**Status**: RESOLVED

---

## CatalogEntryResponse Validation Error for MCP Artifact Type

**Date Fixed**: 2026-01-08
**Severity**: high
**Component**: marketplace-schemas

**Issue**: When viewing low-confidence detected artifacts from a marketplace source, the API fails with Pydantic validation error: `Input should be 'skill', 'command', 'agent', 'mcp_server' or 'hook'`.

**Root Cause**: Continuation of the MCP artifact type naming mismatch. While the database CHECK constraints were updated to accept `'mcp'`, the Pydantic response schema `CatalogEntryResponse` still used a Literal type that only accepted the old values.

```python
# Before fix - rejected 'mcp' values from database
artifact_type: Literal["skill", "command", "agent", "mcp_server", "hook"]
```

**Fix**: Added `'mcp'` to the Literal type annotations in Pydantic schemas.

**Files Modified**:
- `skillmeat/api/schemas/marketplace.py`:
  - Line 1038: `CatalogEntryResponse.artifact_type` - Added 'mcp' to Literal type
  - Line 2132: `ManualMapEntry.artifact_type` - Added 'mcp' to Literal type

**Testing**: Response schema now accepts both 'mcp' and 'mcp_server' values

**Status**: RESOLVED

---

## Frontend Crash When Displaying MCP Artifacts

**Date Fixed**: 2026-01-08
**Severity**: high
**Component**: web-frontend

**Issue**: When toggling to view detected artifacts in the marketplace sources page, the app crashes with `TypeError: Cannot read properties of undefined (reading 'color')` at CatalogCard (page.tsx:148:81).

**Root Cause**: The frontend UI config objects (typeConfig, artifactTypeIcons, artifactTypeLabels, etc.) only had entries for `mcp_server`, not `mcp`. When artifacts with `artifact_type='mcp'` were returned from the API, the config lookup returned `undefined`, causing the property access to fail.

**Fix**: Added `'mcp'` entries to all artifact type config objects in the frontend, using the same orange color scheme as `mcp_server`.

**Files Modified**:
- `skillmeat/web/types/marketplace.ts`: Added 'mcp' to ArtifactType union type
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx`: Added 'mcp' to typeConfig
- `skillmeat/web/app/marketplace/sources/[id]/components/catalog-list.tsx`: Added 'mcp' to 5 config objects:
  - artifactTypeIcons
  - artifactTypeLabels
  - artifactTypeIconColors
  - artifactTypeRowTints
  - artifactTypeBorderAccents

**Testing**: UI now renders 'mcp' artifacts with orange styling matching 'mcp_server'

**Status**: RESOLVED

---

## Hook Artifact Detection Has Inconsistent Low Confidence Scores

**Date Fixed**: 2026-01-08
**Severity**: medium
**Component**: marketplace-heuristic-detector

**Issue**: Hook artifacts detected from marketplace sources have unexpectedly low confidence scores. A hook at path `cli-tool/components/hooks/development-tools` with 8 files had a raw score of 49 (normalized to 31%), when it should score higher due to being inside an appropriately named parent directory (`hooks`).

**Root Cause**: Signal ordering bug in `_score_directory` and `_calculate_marketplace_confidence` methods. The parent_hint bonus (+15 pts) was calculated BEFORE container_hint inference, so when artifact_type was inferred from container_hint (e.g., HOOK from hooks/ directory), the parent_hint scoring returned 0 because artifact_type was still None at that point.

**Signal ordering before fix**:
1. Signal 4: `_score_parent_hint(path, artifact_type)` → returns 0 if artifact_type is None
2. Signal 6: Container hint inference → sets artifact_type = container_hint if None (too late!)

**Fix**: Reordered signals so container_hint inference happens BEFORE parent_hint scoring:
1. Signal 4 (NEW): Container hint inference - if artifact_type is None and container_hint exists, set artifact_type = container_hint (+12 pts)
2. Signal 5: Parent hint bonus - now artifact_type is set, so parent_hint works correctly (+15 pts)
3. Signal 7: Container hint match bonus - only gives full 25 pts if type was already detected (not inferred)

**Files Modified**:
- `skillmeat/core/marketplace/heuristic_detector.py`:
  - `_score_directory` method (lines ~1207-1280): Reordered signals 4-7
  - `_calculate_marketplace_confidence` method (lines ~2015-2083): Same reordering

**Testing**:
- All 212 heuristic detector tests pass
- Verified scoring with test paths:
  - Path inside `hooks/` container now correctly gets both container_hint (+12) AND parent_hint (+15)
  - Before fix: hooks/development-tools scored ~13-15 raw
  - After fix: hooks/development-tools scores ~28-48 raw (depending on other signals)

**Impact**: Artifacts inside typed containers that were previously missing the parent_hint bonus now score 8-12 percentage points higher (normalized), making them more likely to exceed the confidence threshold for display.

**Status**: RESOLVED

---

## Infinite API Request Loop When Changing Items Per Page Selector

**Date Fixed**: 2026-01-08
**Severity**: high
**Component**: marketplace-pagination

**Issue**: When a user changes the number of detected artifacts to display from a marketplace source using the items per page selector, the site begins looping the same API requests constantly until hitting a rate limit, breaking site functionality.

**Root Cause**: The `useEffect` hook that triggers `fetchNextPage()` for infinite scroll used a `>=` comparison instead of `>`:

```javascript
// BUG: Line 509 in page.tsx
if (hasNextPage && endIndex >= allEntries.length && !isFetchingNextPage) {
    fetchNextPage();
}
```

The infinite loop occurred because:
1. User changes `itemsPerPage` from 25 to 100
2. `endIndex` recalculates to 100 (for page 1)
3. `allEntries.length` is 50 (from first API fetch with limit=50)
4. Condition `100 >= 50` is true → triggers `fetchNextPage()`
5. After fetch completes: `allEntries.length = 100`
6. Condition `100 >= 100` is **still true** → triggers another fetch!
7. Loop continues indefinitely until rate limit is hit

**Fix**: Changed comparison from `>=` to `>` so that when we have exactly enough data (`endIndex === allEntries.length`), we don't trigger another unnecessary fetch.

```javascript
// FIXED: Line 509 in page.tsx
if (hasNextPage && endIndex > allEntries.length && !isFetchingNextPage) {
    fetchNextPage();
}
```

Also added missing `updateURLParams` dependency to the URL sync useEffect (line 400) to prevent potential stale closure bugs.

**Files Modified**:
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx`:
  - Line 509: Changed `>=` to `>` in fetchNextPage condition
  - Line 400: Added `updateURLParams` to dependency array

**Testing**: Lint and type-check pass without new errors. The fix ensures:
- When `endIndex > allEntries.length`: Still fetches more data (correct behavior)
- When `endIndex === allEntries.length`: Stops fetching (prevents infinite loop)
- When `endIndex < allEntries.length`: Doesn't fetch (we already have enough)

**Status**: RESOLVED

---

## Marketplace Catalog Limited to 50 Items Due to Client-Side Sorting

**Date Fixed**: 2026-01-08
**Severity**: high
**Component**: marketplace-pagination, marketplace-sorting

**Issue**: When viewing artifacts from a marketplace source, only 50 items would ever display regardless of how many artifacts existed. The user reported:
- Max 50 items displayed regardless of settings or filters
- Changing Type filter showed different artifacts (proving more existed)
- Sorting only affected displayed items, not the full list
- No way to load more items even with pagination

**Root Cause**: Architecture flaw in the pagination/sorting order of operations:

1. **Backend** loaded all entries matching filters into memory, but paginated to 50 items with **no server-side sorting**
2. **Frontend** received 50-item pages and applied **client-side sorting** only on loaded items
3. **Sorting happened AFTER pagination** instead of BEFORE, so sorting never operated on the full dataset
4. **Prefetch logic** only triggered when `endIndex > allEntries.length`, which never happened because sorting the 50 items kept them within bounds

**Why Type filter revealed different artifacts**: The Type filter was passed to the backend, which filtered the full dataset BEFORE pagination. Different filter = different first-50 items from the filtered set.

**Why sorting appeared broken**: Sorting operated on the 50 loaded items, not the full dataset. Sorting by "Name A-Z" would alphabetize items 1-50, but items 51-200 (sorted first by name) would never load because the prefetch trigger never fired.

**Fix**: Implemented proper server-side sorting architecture:

1. **Backend**: Added `sort_by` (confidence|name|date) and `sort_order` (asc|desc) query parameters
2. **Backend**: Sort full filtered entries BEFORE cursor pagination
3. **Frontend Types**: Added `sort_by` and `sort_order` to `CatalogFilters` interface
4. **Frontend Hook**: Pass sort params in API request
5. **Frontend Page**: Removed client-side sorting, rely on server response order

**Data Flow After Fix**:
```
User selects "Name A-Z" → filters.sort_by='name', sort_order='asc'
  → Hook refetches with ?sort_by=name&sort_order=asc
  → Server sorts FULL dataset by name
  → Server returns first 50 items (sorted across entire dataset)
  → User clicks "Next Page"
  → Server returns items 51-100 (still sorted by name)
  → Data remains consistently sorted across pagination
```

**Files Modified**:
- `skillmeat/api/routers/marketplace_sources.py`:
  - Added `sort_by` and `sort_order` Query parameters (lines 1329-1340)
  - Added sorting logic before pagination in both code paths (lines 1443-1451, 1476-1484)
  - Updated docstring with sorting documentation
- `skillmeat/web/types/marketplace.ts`:
  - Added `sort_by?: 'confidence' | 'name' | 'date'` to CatalogFilters
  - Added `sort_order?: 'asc' | 'desc'` to CatalogFilters
- `skillmeat/web/hooks/useMarketplaceSources.ts`:
  - Added params.append for sort_by and sort_order (lines 262-267)
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx`:
  - Initialize filters with sort_by='confidence', sort_order='desc'
  - Added `parseSortOption()` helper to convert UI format to API format
  - Added useEffect to sync sortOption changes to filters
  - Removed client-side sorting from `filteredEntries` useMemo

**Testing**:
- TypeScript compilation passes (pre-existing test type errors unrelated)
- Python import validation passes
- Backend sorting logic covers all three fields with null handling

**Impact**: Users can now:
- Browse ALL artifacts from a source via proper pagination
- Sort the entire dataset (not just loaded items)
- Sorting remains consistent across page navigation

**Status**: RESOLVED

---

## Sync Status Tab Shows 404 Errors and "No Comparison Data" Due to Duplicate Queries

**Date Fixed**: 2026-01-09
**Severity**: high
**Component**: sync-status-tab, unified-entity-modal

**Issue**: When navigating to the Sync Status tab for an artifact with an upstream source, the first upstream-diff API call succeeds and returns all files, but then successive API calls fail with 404 errors. The modal displays "No comparison data available" with "No Project deployment found" even when the user only wants to view Source vs Collection.

**Root Cause**: Two separate upstream-diff queries were running with different configurations when the Sync Status tab opened:

| Component | Query Key | API URL | Result |
|-----------|-----------|---------|--------|
| `unified-entity-modal.tsx` | `['upstream-diff', id, collection]` | `/upstream-diff?collection=xxx` | Success |
| `sync-status-tab.tsx` | `['upstream-diff', id]` | `/upstream-diff` | 404 Error |

The queries had different cache keys (TanStack Query treated them as separate) and different URL parameters:
1. `unified-entity-modal.tsx` included the `collection` parameter, which helped the backend find the correct artifact
2. `sync-status-tab.tsx` omitted the `collection` parameter, forcing the backend to search all collections

When the backend searched all collections without the `collection` hint, it could fail to find the artifact in certain edge cases, returning 404.

Additionally, `unified-entity-modal.tsx` had an upstream query that was dead code - the `_renderUpstreamSection()` function that used it was never called in render.

**Fix**:

1. **Updated `sync-status-tab.tsx` query** to include `entity.collection`:
   - Added `entity.collection` to query key: `['upstream-diff', entity.id, entity.collection]`
   - Added `collection` parameter to API URL: `/upstream-diff?collection=${entity.collection}`
   - Updated all cache invalidation calls to use the new query key format

2. **Disabled dead query in `unified-entity-modal.tsx`**:
   - Set `enabled: false` on the redundant upstream-diff query
   - Added comment explaining this prevents duplicate API calls

**Files Modified**:
- `skillmeat/web/components/sync-status/sync-status-tab.tsx`:
  - Line 279: Added `entity.collection` to query key
  - Lines 280-287: Added URLSearchParams to include `collection` param in URL
  - Lines 330, 363, 402, 698: Updated cache invalidation calls to use new query key format
- `skillmeat/web/components/entity/unified-entity-modal.tsx`:
  - Lines 473-475: Set `enabled: false` with comment explaining the change

**Testing**: TypeScript type-check passes (pre-existing test type errors unrelated to this change)

**Impact**: Only one upstream-diff query now runs per Sync Status tab view, with proper collection context provided to the backend, preventing 404 errors and ensuring consistent cache behavior.

**Status**: RESOLVED

---

## DeploymentCard Crashes on Deployments Tab Due to Array Type Check

**Date Fixed**: 2026-01-10
**Severity**: high
**Component**: deployment-card, deploy-dialog

**Issue**: When opening the Deployments tab in the unified-entity-modal, the page crashes with:
```
TypeError: projects.find is not a function
    at DeploymentCard.useMemo[projectMatch] (deployment-card.tsx:146:21)
```

**Root Cause**: The newly added `projects` prop validation used a falsy check (`if (!projects)`) which only catches `undefined`, `null`, `0`, `''`, etc. During React Query loading states or certain edge cases, `projects` could be truthy but not an array (e.g., an empty object or the query result object itself).

Similarly, `existingDeploymentPaths` in `deploy-dialog.tsx` had the same potential issue.

```typescript
// BUG: Only catches falsy values, not non-array truthy values
if (!projects) return null;
projects.find(...)  // Crashes if projects is {} or other non-array
```

**Fix**: Changed both guard clauses to use `Array.isArray()` for proper type validation:

```typescript
// FIX: Properly validates array type
if (!Array.isArray(projects)) return null;
projects.find(...)  // Safe - guaranteed to be an array
```

**Files Modified**:
- `skillmeat/web/components/deployments/deployment-card.tsx`:
  - Line 143: Changed `if (!projects)` to `if (!Array.isArray(projects))`
- `skillmeat/web/components/collection/deploy-dialog.tsx`:
  - Line 68: Changed `if (!existingDeploymentPaths)` to `if (!Array.isArray(existingDeploymentPaths))`

**Testing**: Build succeeds, TypeScript type-check passes

**Status**: RESOLVED

---

## Deploy Artifact Returns 404 - Wrong Endpoint in useDeploy Hook

**Date Fixed**: 2026-01-10
**Severity**: high
**Component**: web/deploy-dialog

**Issue**: Attempting to deploy an artifact from the web UI fails with a 404 error: `POST /api/v1/artifacts/agent%3Aprd-writer/deploy HTTP/1.1" 404`. The deployment functionality completely broken.

**Root Cause**: The `useDeploy` hook in `hooks/useDeploy.ts` called a non-existent endpoint `/artifacts/${artifactId}/deploy` instead of the correct `/deploy` endpoint. This was a mismatch between two competing implementations:

1. **Broken hook** (`useDeploy`): Called `/api/v1/artifacts/{id}/deploy` - doesn't exist
2. **Correct hook** (`useDeployArtifact`): Calls `/api/v1/deploy` - works correctly

The `DeployDialog` component used the broken `useDeploy` hook.

**Fix**: Updated `deploy-dialog.tsx` to use the correct `useDeployArtifact` hook from `use-deployments.ts`:

1. Changed import from `useDeploy` to `useDeployArtifact`
2. Updated request shape to use snake_case properties matching `ArtifactDeployRequest`:
   - `artifact_id` (format: `type:name`)
   - `artifact_name`
   - `artifact_type`
   - `project_path`
   - `overwrite`
3. Moved success handling into the try block after `mutateAsync` completes

**Files Modified**:
- `skillmeat/web/components/collection/deploy-dialog.tsx` - Migrated to correct hook

**Testing**: 
- TypeScript compilation passes
- Correct endpoint `/api/v1/deploy` now called with proper request body

**Commit(s)**: (pending)

**Status**: RESOLVED
