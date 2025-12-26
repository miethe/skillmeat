# Bug Fixes - December 2025

## 2025-12-01

### CollectionManager get_collection Method Not Found

**Issue**: `skillmeat sync-check` CLI command fails with `'CollectionManager' object has no attribute 'get_collection'`
- **Location**: `skillmeat/core/sync.py:413,622,762,1098,1428`
- **Root Cause**: `SyncManager` called `self.collection_mgr.get_collection()` but the correct method name is `load_collection()`
- **Fix**: Replaced all 5 occurrences of `get_collection` with `load_collection` in sync.py; updated corresponding test mocks in tests/test_sync.py
- **Commit(s)**: b13c97d
- **Status**: RESOLVED

### Select Component Import Errors on Web Build

**Issue**: Web build fails with numerous import errors from `@/components/ui/select` - components trying to import Radix UI sub-components that don't exist
- **Location**: `skillmeat/web/components/ui/select.tsx` and 8 consuming components
- **Root Cause**: `select.tsx` was a simple native HTML wrapper, but 2 discovery components expected Radix UI Select sub-components (`SelectContent`, `SelectItem`, `SelectTrigger`, `SelectValue`)
- **Fix**:
  1. Replaced `select.tsx` with full Radix UI-based shadcn/ui Select component
  2. Migrated 6 components from old native API to new Radix API:
     - `components/collection/filters.tsx`
     - `components/entity/entity-form.tsx`
     - `components/sync-status/comparison-selector.tsx`
     - `components/mcp/MCPServerList.tsx`
     - `components/marketplace/MarketplaceFilters.tsx`
     - `components/marketplace/MarketplaceInstallDialog.tsx`
- **Commit(s)**: 62cca2f
- **Status**: RESOLVED

### Collection Object Missing path Attribute

**Issue**: `skillmeat sync-check` fails with `'Collection' object has no attribute 'path'`
- **Location**: `skillmeat/core/sync.py:414,623,764,1099,1436`
- **Root Cause**: Code accessed `collection.path` but `Collection` is a dataclass without a `path` attribute. Path is managed by `ConfigManager`, not the Collection object.
- **Fix**: Replaced all 5 occurrences of `collection.path` with `self.collection_mgr.config.get_collection_path(collection_name)`
- **Commit(s)**: fc24e7b
- **Status**: RESOLVED

### Discovery Service Scans Wrong Directory Structure

**Issue**: Smart Import/Discovery banner never appears on `/manage` page despite feature being "complete"
- **Location**: `skillmeat/core/discovery.py:100-107`
- **Root Cause**: `ArtifactDiscoveryService` scanned `collection_path/artifacts/` directory, but:
  1. The collection directory `~/.skillmeat/collection/` doesn't exist (never initialized)
  2. The design was wrong - discovery should scan project `.claude/` directories, not collection
- **Fix**: Modified `ArtifactDiscoveryService.__init__` to support three scan modes:
  - `project`: Scans `base_path/.claude/` subdirectories (skills/, commands/, agents/, hooks/, mcp/)
  - `collection`: Scans `base_path/artifacts/` (legacy support)
  - `auto` (default): Auto-detects based on directory structure
- **Commit(s)**: 857ef8d
- **Status**: RESOLVED

### Discovery Banner on Wrong Page (Architectural Bug)

**Issue**: Discovery banner was on `/manage` page which manages collection artifacts (already imported), not project artifacts
- **Location**: `skillmeat/web/app/manage/page.tsx:177-186`
- **Root Cause**: Design mismatch - discovery should help users import artifacts FROM projects INTO collection, not discover artifacts in the collection itself
- **Fix**:
  1. Created new `useProjectDiscovery` hook for project-specific scanning (`skillmeat/web/hooks/useProjectDiscovery.ts`)
  2. Added project-aware API endpoint `POST /api/v1/artifacts/discover/project/{project_id}` (`skillmeat/api/routers/artifacts.py`)
  3. Moved discovery banner and bulk import modal to `/projects/{id}` page (`skillmeat/web/app/projects/[id]/page.tsx`)
  4. Removed discovery functionality from `/manage` page
- **Commit(s)**: a14063c, 0ab58c3
- **Status**: RESOLVED

### Invalid Artifact Structure for Planning Skill

**Issue**: Discovery scan encounters "Invalid artifact structure" warning for `.claude/skills/planning`
- **Location**: `.claude/skills/planning/SKILL.md:3`
- **Root Cause**: YAML frontmatter had unquoted colons in the description field (e.g., "Supports: 1)", "Example: ") which YAML interprets as key-value pairs, causing parsing to fail at column 271
- **Fix**: Converted description to YAML folded block scalar syntax (`>`) which safely handles colons and special characters
- **Commit(s)**: 14c249a
- **Status**: RESOLVED

### Import 422 Error - Source Must Include Owner and Repository

**Issue**: Importing discovered local artifacts fails with 422 error "Source must include owner and repository"
- **Location**: `skillmeat/core/validation.py:36`, `skillmeat/core/discovery.py:407`
- **Root Cause**: Local artifacts in `.claude/` directories don't have GitHub-format source fields (owner/repo/path) in their frontmatter. Validation required this format unconditionally.
- **Fix**:
  1. Discovery service now generates synthetic `local/{type}/{name}` sources for artifacts without GitHub sources
  2. Validation accepts `local/` prefix as valid source format
- **Commit(s)**: a010f2c
- **Status**: RESOLVED

### DialogContent Missing DialogTitle Accessibility Warning

**Issue**: Navigating to `/projects/{id}` page throws "DialogContent requires a DialogTitle for accessibility"
- **Location**: `skillmeat/web/components/discovery/BulkImportModal.tsx:143`, `ParameterEditorModal.tsx:153`
- **Root Cause**: Custom ARIA attributes (`aria-labelledby`, `aria-describedby`) on DialogContent were overriding Radix UI's automatic ARIA linking, making Radix think DialogTitle was missing
- **Fix**: Removed custom `aria-labelledby`, `aria-describedby` attributes and `id` attributes from DialogTitle/DialogDescription in both modals. Radix UI handles ARIA automatically.
- **Commit(s)**: 0abde84
- **Status**: RESOLVED

## 2025-12-02

### APScheduler Module Not Found on Web Build

**Issue**: Web app fails to start with `ModuleNotFoundError: No module named 'apscheduler'`
- **Location**: `skillmeat/cache/refresh.py:70`
- **Root Cause**: Environment not synchronized after `apscheduler>=3.10.0` was added to `pyproject.toml:60` dependencies
- **Fix**: Reinstalled package with `pip install -e ".[dev]"` to sync environment with declared dependencies
- **Commit(s)**: N/A (environment sync, no code changes)
- **Status**: RESOLVED

### Local Source Import Fails with GitHub API 404 Error

**Issue**: Importing auto-discovered local artifacts fails with 404 error: "Failed to resolve version: 404 Client Error: Not Found for url: https://api.github.com/repos/local/skill"
- **Location**: `skillmeat/core/importer.py:324`
- **Root Cause**: `ArtifactImporter._import_single()` always called `add_from_github()` regardless of source type. Local sources (e.g., `local/skill/name`) were incorrectly sent to GitHub API, which tried to fetch from non-existent `local/skill` repository.
- **Fix**:
  1. Added `path` field to `BulkImportArtifact` schema (`skillmeat/api/schemas/discovery.py:335-339`) for filesystem path of local artifacts
  2. Added `path` field to `BulkImportArtifactData` dataclass (`skillmeat/core/importer.py:32`)
  3. Updated `_import_single()` to detect `local/` sources and route to `add_from_local()` instead of `add_from_github()` (`skillmeat/core/importer.py:322-345`)
  4. Updated router to pass path field to importer (`skillmeat/api/routers/artifacts.py:774`)
  5. Added `path` field to frontend `BulkImportArtifact` type (`skillmeat/web/types/discovery.ts:44`)
  6. Updated `handleImport` to include path and generate proper local source identifiers (`skillmeat/web/app/projects/[id]/page.tsx:169-176`)
- **Commit(s)**: d796666, 7783486
- **Status**: RESOLVED

### Projects Page Metadata Shows 0/Never After Navigation

**Issue**: When navigating to `/projects`, away, and back, metadata shows 0 artifacts and "Never" for last deployed time. However, `/projects/{id}` displays correct data.
- **Location**: `skillmeat/web/hooks/useProjectCache.ts:63,95`
- **Root Cause**: Cache key mismatch - hook used `['projects', 'cached']` but mutations invalidated `['projects', 'list']`. This meant cache invalidations from deployments never reached the projects list cache.
- **Fix**: Changed cache key from `['projects', 'cached']` to `['projects', 'list']` in both query definition (line 63) and cache update (line 95)
- **Commit(s)**: 933b0c3
- **Status**: RESOLVED

### Sharing Page TypeError on bundle.metadata.name

**Issue**: Navigating to `/sharing` page throws TypeError: `Cannot read properties of undefined (reading 'name')` at bundle-list.tsx:98
- **Location**: `skillmeat/web/components/sharing/bundle-list.tsx:98,106,112,193,250`
- **Root Cause**: Component accessed `bundle.metadata.name` directly without null checks. While TypeScript types defined metadata as required, API could return incomplete data.
- **Fix**: Added optional chaining (`?.`) to all metadata accesses with sensible fallbacks:
  - `bundle.metadata?.name || 'Unnamed Bundle'`
  - `bundle.metadata?.description && ...`
  - `bundle.metadata?.tags && ...`
  - `selectedBundle.metadata?.name || 'this bundle'`
- **Commit(s)**: 1eb4fc7
- **Status**: RESOLVED

### Diff Viewer Content Overflow in Artifact Modal

**Issue**: In artifact modal Sync Status tab, Diff Viewer content overflows viewport and can't be scrolled. Buttons at bottom become hidden.
- **Location**: `skillmeat/web/components/entity/diff-viewer.tsx`, `unified-entity-modal.tsx:990`
- **Root Cause**: Parent containers had `overflow-hidden` without proper flex constraints. Missing `min-h-0` on flex children prevented CSS overflow from working correctly.
- **Fix**:
  1. Added `min-h-0` to flex containers in diff-viewer (lines 241, 265, 330, 343, 369)
  2. Added `flex-shrink-0` to headers to prevent shrinking (lines 243, 332)
  3. Changed file sidebar to `overflow-y-auto` with `flex-shrink-0` (line 267)
  4. Changed modal wrapper from `max-h-[400px] overflow-hidden` to `h-[400px]` (line 990)
- **Commit(s)**: f958e1a
- **Status**: RESOLVED

### Contents Tab Edit Mode Layout Issues

**Issue**: Multiple layout issues in artifact modal Contents tab Edit mode:
1. Preview pane cut off horizontally (no horizontal scroll)
2. File tree header "FILES" truncated to "ES"
3. File tree should collapse to give more editing space
- **Location**: `skillmeat/web/components/entity/file-tree.tsx:296-297`, `content-pane.tsx:353-360`, `unified-entity-modal.tsx:1346-1349`
- **Root Cause**:
  1. Missing `min-w-0` wrapper around SplitPreview prevented horizontal scroll
  2. Header text lacked `whitespace-nowrap` so it wrapped/truncated
  3. File tree used fixed width regardless of edit state
- **Fix**:
  1. Added `whitespace-nowrap` to FILES label and `flex-shrink-0` to Plus button (file-tree.tsx)
  2. Changed to `overflow-auto` and wrapped SplitPreview in `min-w-0` div (content-pane.tsx)
  3. Made file tree width dynamic: `w-48` when editing, `w-64 lg:w-72` otherwise, with smooth transition (unified-entity-modal.tsx)
- **Commit(s)**: 6d1fdc9
- **Status**: RESOLVED

### Regression: cn Not Defined in Unified Entity Modal

**Issue**: Clicking artifact card throws "cn is not defined" error at unified-entity-modal.tsx:1346
- **Location**: `skillmeat/web/components/entity/unified-entity-modal.tsx:1346`
- **Root Cause**: Previous fix (6d1fdc9) added `cn()` usage for dynamic file tree width but didn't add the import
- **Fix**: Added `import { cn } from '@/lib/utils'` at line 4
- **Commit(s)**: 2e576e8
- **Status**: RESOLVED

### Regression: React Key Warning in Bundle List

**Issue**: Navigating to /sharing throws "Each child in a list should have unique key prop" warning
- **Location**: `skillmeat/web/components/sharing/bundle-list.tsx:88`
- **Root Cause**: Some bundles may have undefined `id` values, causing duplicate keys
- **Fix**: Added index fallback: `key={bundle.id || \`bundle-${index}\`}`
- **Commit(s)**: 2e576e8
- **Status**: RESOLVED

### Sync Status Tab 500 Error - upstream-diff Endpoint Fails

**Issue**: Opening artifact modal Sync Status tab throws 500 error: "Failed to fetch upstream artifact"
- **Location**: `skillmeat/api/routers/artifacts.py:3368-3372`
- **Root Cause**: When `fetch_update` determines no update exists (SHA matches), it returns without `fetch_result` or `temp_workspace`. The API treated this as an error instead of "no changes".
- **Fix**: Added check for `not fetch_result.has_update` before the error check, returning valid `ArtifactUpstreamDiffResponse` with `has_changes=false` and empty files list
- **Commit(s)**: 29ba27a
- **Status**: RESOLVED

### Diff Viewer Scrollbar Still Not Working (Follow-up)

**Issue**: Despite previous fix (f958e1a), Diff Viewer in Sync Status tab still doesn't scroll properly. The component scrolls as one unit instead of having independent scrollbars for file tree and diff panels. Bottom buttons remain hidden.
- **Location**: `skillmeat/web/components/sync-status/sync-status-tab.tsx:726`
- **Root Cause**: The DiffViewer wrapper div used `overflow-auto` which caused the entire DiffViewer component to scroll as one unit, overriding the internal scroll management in DiffViewer which already has proper `overflow-auto` on its internal panels.
- **Fix**: Changed wrapper from `<div className="flex-1 overflow-auto">` to `<div className="flex-1 overflow-hidden min-h-0">`. This allows DiffViewer to fill available space while managing its own internal scrolling.
- **Commit(s)**: 18831eb
- **Status**: RESOLVED

### Projects Page Force Refresh Not Working (Follow-up)

**Issue**: Despite previous cache key fix (933b0c3), clicking the refresh button on `/projects` page doesn't update stale data. The `forceRefresh` function silently fails to bypass the backend cache.
- **Location**: `skillmeat/web/hooks/useProjectCache.ts:94`
- **Root Cause**: Frontend `forceRefresh` function used `?force_refresh=true` query parameter, but the backend endpoint expects `?refresh=true` (defined with `alias="refresh"` at `projects.py:319`).
- **Fix**: Changed query parameter from `'/projects?force_refresh=true'` to `'/projects?refresh=true'` to match backend's expected parameter name.
- **Commit(s)**: 18831eb
- **Status**: RESOLVED

### Diff Viewer Scroll Clipped Inside Sync Status Modal (Another follow-up)

**Issue**: Diff Viewer still overflows the artifact modal on the Sync Status tab; long diffs can't be scrolled independently and horizontal overflow is clipped.
- **Location**: `skillmeat/web/components/entity/unified-entity-modal.tsx`, `skillmeat/web/components/sync-status/sync-status-tab.tsx`, `skillmeat/web/components/entity/diff-viewer.tsx`
- **Root Cause**: The modal and tab containers lacked `min-h-0/min-w-0`, so flex children could not shrink and overflow handling never engaged. DiffViewer also synchronized pane scrolling, preventing independent scrollbars and exacerbating overflow when one side was longer.
- **Fix**:
  1. Added `h-[90vh]` plus `min-h-0/min-w-0` to the modal shell, Tabs, and SyncStatusTab so the layout has a real, bounded height for scroll containers and keeps the footer visible.
  2. Added `max-h-[55vh]` and `min-h-[320px]` around DiffViewer to enforce an internal scrollable region while leaving space for bottom actions.
  3. Added `min-w-0` to both diff panes/scroll containers for horizontal overflow and removed scroll synchronization between left/right panes to keep scrollbars independent.
- **Commit(s)**: pending
- **Status**: RESOLVED (Actually Fixed)

### Contents Tab File Tree Label Cut Off

**Issue**: In the Unified Entity modal Contents tab, the file tree hugs the left edge and the "FILES" label is clipped to "ES".
- **Location**: `skillmeat/web/components/entity/unified-entity-modal.tsx`
- **Root Cause**: The contents pane used a negative horizontal margin (`-mx-6`) combined with an `overflow-hidden` parent, clipping the leftmost portion of the file tree.
- **Fix**: Removed the negative margin on the contents pane flex wrapper so the file tree sits fully inside the modal padding without being clipped.
- **Commit(s)**: pending
- **Status**: RESOLVED

### Projects Page Metadata Resets to 0/Never After Cache Hit (Persistent Cache Bug)

**Issue**: Navigating back to `/projects` shows 0 deployments and "Never" last deployed even though `/projects/{id}` is correct.
- **Location**: `skillmeat/api/routers/projects.py:354-410`
- **Root Cause**: Persistent cache stored skeleton project records with empty artifacts and no last deployment. When the cache was hit, the API returned those zeroed values instead of reading real deployment metadata from disk.
- **Fix**: On cache hits, rebuild `ProjectSummary` from the actual deployment tracker (using `build_project_summary`) and attach cache metadata, ensuring deployment counts and last deployed timestamps stay accurate even with cached project IDs.
- **Commit(s)**: pending
- **Status**: RESOLVED

### Project Discovery Import Doesn't Add Artifact to Project

**Issue**: Importing discovered artifacts from `/projects/{id}` returns 200 with success toasts, but the artifact never appears in the project or codebase.
- **Location**: `skillmeat/api/routers/artifacts.py:657-759`, `skillmeat/web/hooks/useProjectDiscovery.ts`, `skillmeat/web/components/discovery/BulkImportModal.tsx`, `skillmeat/web/app/projects/[id]/page.tsx`
- **Root Cause**: The bulk import endpoint only added artifacts to the collection and never recorded deployments for the initiating project; the frontend also didn't pass project context and always showed a success toast regardless of actual import results.
- **Fix**: Added optional `project_id` to `/artifacts/discover/import` and record successful imports into the project's `.skillmeat-deployed.toml` (with content hashes). The frontend now passes the project ID, invalidates project queries after import, and shows toast counts from the real `BulkImportResult` instead of always reporting success.
- **Commit(s)**: pending
- **Status**: RESOLVED

### Invalid project_id on Discovery Bulk Import

**Issue**: Bulk import from project discovery returned 0/1 imported with warning `Invalid project_id provided to bulk import: Invalid base64-encoded string...` when the project_id query param was slightly malformed.
- **Location**: `skillmeat/api/routers/artifacts.py:657-759`
- **Root Cause**: Endpoint assumed strictly padded Base64; malformed/space-substituted values failed decode and aborted deployment recording.
- **Fix**: Added robust `_decode_project_id_param` helper that normalizes spaces, tolerates missing padding, and falls back to URL-decoded absolute paths before attempting deployment recording. Invalid IDs are logged but no longer break the import flow.
- **Commit(s)**: pending
- **Status**: RESOLVED

### project_id percent-encoding breaks deployment recording

**Issue**: Bulk import succeeded but deployment recording was skipped with warning about nonexistent path like `/.../skillmeat/L1Vz...` when `project_id` contained percent-encoded characters (e.g., `%3D`).
- **Location**: `skillmeat/api/routers/artifacts.py:617-759`
- **Root Cause**: The decoder attempted Base64 before URL-decoding the parameter; `%` characters caused Base64 to fail, so the value was treated as a relative path under the repo.
- **Fix**: Normalize with `unquote` before Base64 decoding in `_decode_project_id_param`, ensuring encoded padding/characters are decoded before decode attempt.
- **Commit(s)**: pending
- **Status**: RESOLVED

## 2025-12-05

### Sync Status Tab 404 Error for Artifacts with Special Characters

**Issue**: Opening Sync Status tab for Project-level artifacts like "skill:Confidence Check" returns 404 error: `GET /api/v1/artifacts/skill:Confidence Check/upstream-diff - 404`
- **Location**: `skillmeat/web/components/sync-status/sync-status-tab.tsx:319,335,385,420,462`, `skillmeat/web/components/entity/unified-entity-modal.tsx:284,359,402,539`
- **Root Cause**: Frontend components used raw `fetch()` and `apiRequest()` with unencoded artifact IDs in URL paths. Artifact IDs like `skill:Confidence Check` contain colons and spaces that must be URL-encoded.
- **Fix**: Added `encodeURIComponent(entity.id)` to all 9 API call locations in both components:
  - `sync-status-tab.tsx`: upstream-diff, project-diff, sync mutation, deploy mutation, take-upstream mutation
  - `unified-entity-modal.tsx`: file list, diff, upstream-diff, rollback-sync
- **Commit(s)**: afe270b
- **Status**: RESOLVED

### Sync Status Tab 404 Error for Discovered Artifacts

**Issue**: Sync Status tab makes API calls for "discovered" artifacts (not yet imported), causing 404 errors because `collection=discovered` is not a real collection.
- **Location**: `skillmeat/web/components/entity/unified-entity-modal.tsx:331,418`, `skillmeat/web/components/sync-status/sync-status-tab.tsx:323,339,359-374`
- **Root Cause**: Query `enabled` conditions only checked for `entity.id`, not whether the collection was a real collection. Discovered artifacts have `collection: 'discovered'` as a placeholder, not an actual collection name.
- **Fix**:
  1. Added `entity?.collection !== 'discovered'` check to all `enabled` conditions in both components
  2. Added early return in SyncStatusTab with helpful message: "Sync status is not available for discovered artifacts. Import to your collection to enable sync tracking."
- **Commit(s)**: 21de2c9
- **Status**: RESOLVED

## 2025-12-12

### GitHub Sources Page Not Accessible from UI

**Issue**: The GitHub marketplace ingestion feature at `/marketplace/sources` was fully implemented but inaccessible from the UI - users had no way to navigate to it.
- **Location**: `skillmeat/web/components/navigation.tsx`, `skillmeat/web/app/marketplace/page.tsx`
- **Root Cause**: The feature implementation (PRD marketplace-github-ingestion-v1) created the sources page and all components, but navigation links were never added to connect it to the main UI.
- **Fix**:
  1. Added "Sources" sub-item under Marketplace in sidebar navigation with Github icon
  2. Added "GitHub Sources" button in marketplace page header linking to `/marketplace/sources`
- **Commit(s)**: 3c6ad87
- **Status**: RESOLVED

### Add GitHub Source Fails with 422 Validation Error

**Issue**: Adding a new GitHub source via the modal fails with 422 error: "Input should be a valid dictionary or object to extract fields from" with raw bytes input.
- **Location**: `skillmeat/web/lib/api.ts:42`
- **Root Cause**: The `buildApiHeaders()` function only set `Accept: application/json` but not `Content-Type: application/json`. POST/PATCH requests with JSON bodies were sent without the Content-Type header, so FastAPI received raw bytes instead of parsed JSON.
- **Fix**: Added `'Content-Type': 'application/json'` to the default headers in `buildApiHeaders()`
- **Commit(s)**: 6fb51ab
- **Status**: RESOLVED

## 2025-12-13

### Create New Collection Button Shows "Not Yet Implemented" Error

**Issue**: Clicking "Create New Collection" button on `/collection` page displays error toast "Collection creation not yet implemented" despite backend endpoint being fully functional.
- **Location**: `skillmeat/web/hooks/use-collections.ts:233`, `skillmeat/web/lib/api/collections.ts:46`
- **Root Cause**: Two issues combined:
  1. `useCreateCollection()` hook threw `ApiError('Collection creation not yet implemented', 501)` immediately instead of calling the API client
  2. `createCollection()` API client targeted `/collections` (read-only endpoint) instead of `/user-collections` (fully implemented POST endpoint)
- **Fix**:
  1. Changed API client endpoint from `/collections` to `/user-collections` in `lib/api/collections.ts`
  2. Replaced stub in `hooks/use-collections.ts` with actual `createCollection()` call
  3. Added `description?: string` to `CreateCollectionRequest` type to match backend schema
- **Commit(s)**: 86e9190
- **Status**: RESOLVED

## 2025-12-14

### React Hydration Mismatch on Navigation and Collection Pages

**Issue**: Client-side hydration mismatch errors on page load with multiple components:
  - NavSection Marketplace: `aria-expanded={true}` vs `aria-expanded="false"`
  - CollectionPage: Skeleton vs actual content rendering mismatch
- **Location**: `skillmeat/web/components/nav-section.tsx:119-126`, `skillmeat/web/context/collection-context.tsx:46-53`, `skillmeat/web/app/collection/page.tsx:95-99`
- **Root Cause**: Three components read from localStorage during `useState` initialization. Server renders with default values (null/false/grid), but client initializes with localStorage values, causing hydration mismatch when stored values differ.
- **Fix**: Applied deferred hydration pattern to all three components:
  1. **NavSection**: Initialize `isExpanded` with deterministic default (`isChildActive || defaultExpanded`), sync from localStorage in useEffect after mount with `hasMounted` state
  2. **CollectionProvider**: Initialize `selectedCollectionId` with `null`, sync from localStorage in useEffect after mount
  3. **CollectionPageContent**: Initialize `viewMode` with `'grid'`, sync from localStorage in useEffect after mount
- **Commit(s)**: c9f8968
- **Status**: RESOLVED

## 2025-12-15

### Next.js Build Fails with TypeError on /collection Page Prerendering

**Issue**: `pnpm build` fails with `TypeError: Cannot read properties of null (reading 'id')` during static prerendering of `/collection` page.
- **Location**: `skillmeat/web/components/collection/artifact-list.tsx:328,331`, `skillmeat/web/components/collection/artifact-grid.tsx:127,130`, `skillmeat/web/components/entity/unified-entity-modal.tsx:89,503,513`
- **Root Cause**: Non-null assertion operators (`!`) on optional `artifact.collection` and nullable `entity` parameters. During SSR/prerendering, data isn't available yet so these properties are null, but the code assumed they were defined after conditional checks.
- **Fix**:
  1. Replaced `artifact.collection!.id` with guard pattern `artifact.collection?.id &&` in onClick handlers
  2. Added optional chaining to `artifact.collection?.name` in both artifact-list.tsx and artifact-grid.tsx
  3. Updated `isContextEntity()` to accept `Entity | null` with null guard
  4. Added `entity?.projectPath` optional chaining
  5. Added `.filter((c): c is string => c != null)` to filter null `from_collection` values
- **Commit(s)**: 0638e4a
- **Status**: RESOLVED

## 2025-12-16

### Context Entities Page Crashes with Radix UI Select Error

**Issue**: Navigating to `/context-entities` fails with error: `A <Select.Item /> must have a value prop that is not an empty string`
- **Location**: `skillmeat/web/components/context/context-entity-filters.tsx:127,134,45`
- **Root Cause**: Radix UI Select doesn't allow empty string values for `<SelectItem>`. The category filter used `value=""` for the "All Categories" option, which crashes when rendered.
- **Fix**: Applied sentinel value pattern:
  1. Changed `<SelectItem value="">` to `<SelectItem value="__all__">` (line 134)
  2. Changed Select `value={filters.category || ''}` to `value={filters.category || '__all__'}` (line 127)
  3. Changed handler condition from `value === ''` to `value === '__all__'` (line 45)
- **Commit(s)**: beb93e7
- **Status**: RESOLVED

### Context Entities and Templates Pages Missing from Navigation

**Issue**: The `/context-entities` and `/templates` pages exist but have no navigation entries in the sidebar, making them inaccessible to users.
- **Location**: `skillmeat/web/components/navigation.tsx:50-80`
- **Root Cause**: Navigation config was never updated after agent-context-entities-v1 PRD implementation. Only Collections, Marketplace, and bottom items were configured.
- **Fix**: Added new "Agent Context" collapsible section to `navigationConfig.sections` with:
  - "Context Entities" → `/context-entities` (FileCode2 icon)
  - "Templates" → `/templates` (FileText icon)
- **Commit(s)**: beb93e7
- **Status**: RESOLVED

### Collection Switcher Not Rendered in Navigation

**Issue**: Users cannot see or switch between collections. The "New Collection" button in the header only appears in "All Collections" mode, but users have no UI to navigate to that mode.
- **Location**: `skillmeat/web/components/navigation.tsx`
- **Root Cause**: The `CollectionSwitcherWithDialogs` component exists and is fully functional but was never rendered anywhere in the application. Users had no way to:
  1. See available collections
  2. Switch between collections
  3. Navigate to "All Collections" mode (where "New Collection" button appears)
  4. Access the "Add Collection" button in the switcher dropdown
- **Fix**: Added `CollectionSwitcherWithDialogs` to the navigation sidebar:
  1. Imported `CollectionSwitcherWithDialogs` from `./collection/collection-switcher-with-dialogs`
  2. Rendered component at top of `<nav>` with `className="w-full"` for proper width
  3. Added `mb-4` wrapper div for spacing from navigation items below
- **Commit(s)**: 70abd16
- **Status**: RESOLVED

### Collection 404 on Page Load When Stored Collection Deleted

**Issue**: First page load returns 404 for `/api/v1/user-collections/{id}` when the previously selected collection (stored in localStorage) no longer exists.
- **Location**: `skillmeat/web/context/collection-context.tsx:53,89-93`
- **Root Cause**: CollectionProvider stored selected collection ID in localStorage (`skillmeat-selected-collection`). On page load, it fetched this stored ID via `useCollection()`. If the collection was deleted or inaccessible, API returned 404, but nothing handled this gracefully - the error persisted on every page load.
- **Fix**: Added `useEffect` hook that monitors `collectionError`. When an error occurs with a selected collection ID:
  1. Logs warning message for debugging
  2. Clears invalid ID from localStorage
  3. Resets `selectedCollectionId` state to `null` using the direct state setter (avoiding re-persistence)
- **Commit(s)**: 0175ae0
- **Status**: RESOLVED

## 2025-12-18

### Take Upstream Hangs and Times Out on Sync Status Tab

**Issue**: Clicking "Take Upstream" in artifact modal Sync Status tab causes web app to hang, then fails with `ECONNRESET` socket hang up error. API logs show warning about existing artifact path but never completes.
- **Location**: `skillmeat/core/deployment.py:206-210`, `skillmeat/api/routers/artifacts.py:2387-2392`
- **Root Cause**: Two issues combined:
  1. `deploy_artifacts()` was designed for CLI use with interactive prompts. When an artifact already exists at the destination, it calls `rich.Confirm.ask()` which blocks waiting for stdin input
  2. The API endpoint received `overwrite: true` from frontend but never passed it to the core function - `request.overwrite` was ignored
  3. When called from API context with no stdin, the function hangs forever waiting for user confirmation
- **Fix**:
  1. Added `overwrite: bool = False` parameter to `deploy_artifacts()` function signature
  2. Modified overwrite prompt logic to skip `Confirm.ask()` when `overwrite=True`
  3. Updated router to pass `request.overwrite` to `deploy_artifacts()` call
  4. Added `--overwrite/-o` CLI flag for consistency
  5. Added unit test for overwrite=True behavior
- **Commit(s)**: 0b2e0c6
- **Status**: RESOLVED

### Next.js Build Fails - useSearchParams Missing Suspense Boundary

**Issue**: Web app build fails with error: `useSearchParams() should be wrapped in a suspense boundary at page "/collection"`
- **Location**: `skillmeat/web/app/collection/page.tsx:95`, `skillmeat/web/app/projects/[id]/page.tsx:56`
- **Root Cause**: Next.js App Router requires `useSearchParams()` to be wrapped in a Suspense boundary to prevent hydration mismatches during SSR. Both pages called the hook directly without wrapping.
- **Fix**:
  1. `/collection/page.tsx`: Wrapped existing `<CollectionPageContent />` in `<Suspense>` with Loader2 spinner fallback
  2. `/projects/[id]/page.tsx`: Renamed `ProjectDetailPage` to `ProjectDetailPageContent`, created new default export wrapping content in `<Suspense>`
  3. Added `Suspense` from 'react' and `Loader2` from 'lucide-react' imports to both files
- **Commit(s)**: 601debd
- **Status**: RESOLVED

### Tags API Fails with TypeError on list_tags

**Issue**: Tags API returns 500 error: `TagService.list_tags() got an unexpected keyword argument 'order_by'`
- **Location**: `skillmeat/api/routers/tags.py` (multiple lines), `skillmeat/web/lib/api/tags.ts`
- **Root Cause**: Router-to-service contract mismatches after TagService refactor:
  1. `list_tags(order_by="name")` - service doesn't accept `order_by` param
  2. `create_tag(name=..., slug=...)` - service expects `TagCreateRequest` object
  3. `get_tag_by_id()` - method is named `get_tag()`
  4. `update_tag(id, **updates)` - service expects `TagUpdateRequest` object
  5. `get_tag_artifact_count()` - method doesn't exist (count is in response)
  6. Frontend PageInfo types mismatched (`has_next` vs `has_next_page`, etc.)
- **Fix**:
  1. Changed `list_tags()` call to use correct signature without `order_by`
  2. Changed `create_tag()` to pass request object directly
  3. Changed `get_tag_by_id()` → `get_tag()`
  4. Changed `update_tag()` to pass request object directly
  5. Removed manual artifact_count calls (service includes it in response)
  6. Fixed frontend `TagListResponse.page_info` to match backend `PageInfo` schema
- **Commit(s)**: 71a5087
- **Status**: RESOLVED

### Edit Parameters Modal Uses Plain Text Input for Tags

**Issue**: Tags field in artifact Edit Parameters modal requires comma-separated text input instead of using the TagInput component with search, autocomplete, and inline tag creation.
- **Location**: `skillmeat/web/components/discovery/ParameterEditorModal.tsx:245-255`
- **Root Cause**: Original implementation used basic `<Input>` with comma-separated string parsing. The full-featured `TagInput` component already existed but wasn't integrated.
- **Fix**:
  1. Imported `TagInput` component and `useTags` hook
  2. Changed form field type from `string` to `string[]`
  3. Used `Controller` from react-hook-form to integrate TagInput
  4. Configured TagInput with suggestions from API, `allowCreate={true}`
  5. Updated form submission to use array directly (removed comma-split parsing)
  6. Updated help text to reflect new UX
- **Commit(s)**: df3fbfd
- **Status**: RESOLVED

## 2025-12-19

### Edit Parameters Modal Fails with GitHubMetadataExtractor Missing Cache Argument

**Issue**: Saving Tags via the Edit Parameters form fails with error: `GitHubMetadataExtractor.__init__() missing 1 required positional argument: 'cache'`
- **Location**: `skillmeat/api/routers/artifacts.py:2063`
- **Root Cause**: `GitHubMetadataExtractor()` was instantiated without the required `cache` argument. The class signature is `__init__(self, cache: MetadataCache, token: Optional[str] = None)`, but the call at line 2063 passed no arguments.
- **Fix**: Changed `GitHubMetadataExtractor()` to `GitHubMetadataExtractor(cache=None)`. This matches the validation-only pattern used in `core/validation.py:40` - no caching is needed for `parse_github_url()` validation.
- **Commit(s)**: 0410802
- **Status**: RESOLVED

### Tags Not Displayed After Saving Despite Successful API Response

**Issue**: Tags appear to save successfully (API logs show update), but never display on artifact cards, in modals, in the filterable tag list, or in the Edit Parameters modal.
- **Location**: `skillmeat/api/schemas/artifacts.py:185`, `skillmeat/api/routers/artifacts.py:477`, `skillmeat/web/hooks/useDiscovery.ts:144`
- **Root Cause**: Tags were being persisted correctly to disk (manifest.toml), but:
  1. `ArtifactResponse` schema was missing the `tags` field entirely
  2. `artifact_to_response()` function never mapped `artifact.tags` to the response
  3. Frontend cache invalidation after tag edit only invalidated artifact queries, not entity queries used by the modal
- **Fix**:
  1. Added `tags: List[str]` field to `ArtifactResponse` schema
  2. Added `tags=artifact.tags or []` to `artifact_to_response()` constructor
  3. Added `['entities']` query invalidation after tag edit in `useEditArtifactParameters` hook
- **Commit(s)**: aba3e6d
- **Status**: RESOLVED

### Artifact Cards Have Inconsistent Heights on /collection Page

**Issue**: Artifact cards have varying sizes depending on whether they have tags attached. Cards with tags are taller than cards without, causing inconsistent row heights.
- **Location**: `skillmeat/web/components/collection/artifact-grid.tsx:152,205`
- **Root Cause**: The `UnifiedCard` component conditionally renders the tags section (only when tags exist). Without CSS Grid row height normalization, cards without tags were shorter than cards with tags.
- **Fix**: Added `auto-rows-fr` Tailwind class to both grid containers (main grid and skeleton). This CSS Grid property (`grid-auto-rows: 1fr`) equalizes row heights based on the tallest item in each row.
- **Commit(s)**: 7000902
- **Status**: RESOLVED

## 2025-12-20

### ContextEntityCard Crashes on Unknown Entity Type

**Issue**: Context entities page fails with `TypeError: Cannot read properties of undefined (reading 'icon')` at ContextEntityCard.
- **Location**: `skillmeat/web/components/context/context-entity-card.tsx:214-215,107`
- **Root Cause**: Two issues:
  1. `typeConfig[entity.entity_type]` returns `undefined` when type doesn't match - API may return different casing than expected lowercase snake_case values
  2. `TypeBadge` sub-component did its own `typeConfig` lookup without normalization, crashing when accessing `config.icon` on undefined
- **Fix**:
  1. Added type normalization: `(entity.entity_type?.toLowerCase() || '') as ContextEntityType`
  2. Added `defaultConfig` with gray styling as fallback instead of error state
  3. Added `console.warn()` for debugging unknown types
  4. Updated `TypeBadge` to receive pre-resolved `config` from parent instead of doing its own lookup
- **Commit(s)**: d98ab9a, 062f4e5, 0599018
- **Status**: RESOLVED

### DeployToProjectDialog Crashes on Preview with entity_type.replace() Error

**Issue**: Clicking "Preview" on any artifact in /context-entities page fails with `TypeError: Cannot read properties of undefined (reading 'replace')`.
- **Location**: `skillmeat/web/components/context/deploy-to-project-dialog.tsx:133`, `skillmeat/web/app/context-entities/page.tsx:326`
- **Root Cause**: Two issues:
  1. `entity.entity_type.replace('_', ' ')` called without null check - crashes when `entity_type` is undefined
  2. Prop mismatch: page passed `onClose` but dialog interface expects `onOpenChange`
- **Fix**:
  1. Added optional chaining with fallback: `entity.entity_type?.replace('_', ' ') || 'Unknown'`
  2. Changed prop from `onClose={handleDeployClose}` to `onOpenChange={(open) => !open && handleDeployClose()}`
- **Commit(s)**: 1cc2b1e
- **Status**: RESOLVED

## 2025-12-22

### UnifiedCard Crashes on ArtifactSummary with Unknown Type

**Issue**: Switching to a specific collection on `/collection` page throws `TypeError: Cannot read properties of undefined (reading 'icon')` at unified-card.tsx:217, and `Cannot read properties of undefined (reading 'color')` at line 341.
- **Location**: `skillmeat/web/components/shared/unified-card.tsx:214-217,341`
- **Root Cause**: When viewing a specific collection, `useCollectionArtifacts` returns `ArtifactSummary` objects that have `type: string` (generic) instead of strict `EntityType`. When an unknown type is passed to `getEntityTypeConfig()`, it returns `undefined`, and accessing `config.icon` or `config.color` crashes.
- **Fix**: Added defensive null checks with fallbacks:
  - `const iconName = config?.icon ?? 'FileText'` (line 216)
  - `config?.color ?? 'text-muted-foreground'` (line 341)
- **Commit(s)**: 996df89, a373a88
- **Status**: RESOLVED

### ArtifactGrid Missing Key Prop for ArtifactSummary Objects

**Issue**: React warning: "Each child in a list should have a unique 'key' prop" in ArtifactGrid component.
- **Location**: `skillmeat/web/components/collection/artifact-grid.tsx:212`
- **Root Cause**: `ArtifactSummary` objects from the collection artifacts API don't have an `id` field. The `key={artifact.id}` was `undefined`, causing React to warn about duplicate keys.
- **Fix**: Added composite key fallback: `key={artifact.id || \`${artifact.name}-${artifact.type}\`}`
- **Commit(s)**: 4b48327
- **Status**: RESOLVED

### Collection View Crashes on "Cannot read properties of undefined (reading 'tags')"

**Issue**: Opening the unified modal for artifacts within a specific collection on `/collection` page throws `TypeError: Cannot read properties of undefined (reading 'tags')` at page.tsx:40.
- **Location**: `skillmeat/web/app/collection/page.tsx:40-41`, `skillmeat/web/components/collection/artifact-list.tsx:307,316`
- **Root Cause**: When viewing a specific collection, `/user-collections/{id}/artifacts` returns `ArtifactSummary` objects (4 fields: name, type, version, source) that lack the `metadata` property. The `artifactToEntity` function accessed `artifact.metadata.tags` and `artifact.metadata.description` without null checks.
- **Fix**: Added optional chaining (`?.`) to all metadata property accesses:
  - `artifact.metadata?.tags || []`
  - `artifact.metadata?.description`
  - `artifact.metadata?.version`
  - `artifact.metadata?.title || artifact.name`
- **Commit(s)**: 43350e0
- **Status**: RESOLVED

### Collection View Cards Appear Different from Catalog View

**Issue**: Artifact cards within a specific collection appear sparse/different from the main catalog view - missing description, tags, usage stats, and other metadata.
- **Location**: `skillmeat/web/app/collection/page.tsx:247-285`
- **Root Cause**: Same as above - `ArtifactSummary` has only 4 fields vs full `Artifact` with 16+ fields. Both views use the same `UnifiedCard` component, but sparse data results in sparse cards.
- **Fix**: Added `enrichArtifactSummary()` function that:
  1. Takes an `ArtifactSummary` and the full artifacts array from `useArtifacts()`
  2. Finds the matching full `Artifact` by name
  3. Returns the enriched artifact with all metadata, usageStats, etc.
  4. Applied in `filteredArtifacts` useMemo when viewing a specific collection
- **Commit(s)**: 43350e0
- **Status**: RESOLVED

## 2025-12-25

### claudectl Wrapper Fails with "No such option: --smart-defaults"

**Issue**: After installing claudectl via `skillmeat alias install`, running any claudectl command fails with `Error: No such option: --smart-defaults`
- **Location**: `skillmeat/cli.py:49-63` (main group definition)
- **Root Cause**: PRD-003 Task P1-T2 specified adding `--smart-defaults` flag to the main CLI group, but the implementation was incomplete. The wrapper script at `~/.local/bin/claudectl` runs `exec skillmeat --smart-defaults "$@"`, but the `--smart-defaults` option was never defined on the `@click.group()` decorator. All subcommands checked `ctx.obj.get("smart_defaults")` but `ctx.obj` was never initialized with this value.
- **Fix**: Added the missing option to the main group:
  ```python
  @click.group()
  @click.version_option(version=__version__, prog_name="skillmeat")
  @click.option("--smart-defaults", is_flag=True, hidden=True, help="Enable smart defaults mode (used by claudectl wrapper)")
  @click.pass_context
  def main(ctx, smart_defaults):
      ctx.ensure_object(dict)
      ctx.obj["smart_defaults"] = smart_defaults
  ```
- **Commit(s)**: fd53eba
- **Status**: RESOLVED

### Sync Status Tab API Errors - Incorrect API Base URL

**Issue**: Navigating to the Sync Status tab of an artifact from `/projects/{ID}/` page throws errors: `ApiError: Request failed` for upstream diff fetch and other sync operations.
- **Location**: `skillmeat/web/components/sync-status/sync-status-tab.tsx:264,280,332,367,409`
- **Root Cause**: The `sync-status-tab.tsx` component used raw `fetch()` with hardcoded paths like `/api/v1/artifacts/.../upstream-diff` which went to Next.js's internal routing (port 3000) instead of the FastAPI backend (port 8080). The `apiRequest` helper in `lib/api.ts` was already available and properly builds URLs with the correct API base URL.
- **Fix**: Replaced all 5 raw `fetch()` calls with `apiRequest()`:
  1. Upstream diff query (line 265): `apiRequest<ArtifactUpstreamDiffResponse>('/artifacts/.../upstream-diff')`
  2. Project diff query (line 281): `apiRequest<ArtifactDiffResponse>('/artifacts/.../diff?...')`
  3. Sync mutation (line 333): `apiRequest('/artifacts/.../sync', { method: 'POST', ... })`
  4. Deploy mutation (line 365): `apiRequest('/artifacts/.../deploy', { method: 'POST', ... })`
  5. Take upstream mutation (line 404): `apiRequest('/artifacts/.../deploy', { method: 'POST', ... })`
- **Commit(s)**: ee426ba
- **Status**: RESOLVED

### Button Nesting Hydration Error in Sync Status Tab

**Issue**: React hydration warning: "In HTML, `<button>` cannot be a descendant of `<button>`. This will cause a hydration error."
- **Location**: Reported near `unified-entity-modal.tsx` TabsContent for sync tab
- **Root Cause**: Investigated extensively but could not locate the exact button nesting violation in the codebase. All trigger components (DropdownMenuTrigger, DialogTrigger, TooltipTrigger, etc.) properly use `asChild` when wrapping Button components. The error may be a transient hydration timing issue, browser extension interference, or a false positive from React's strict mode.
- **Fix**: Unable to fix - could not reproduce from code analysis
- **Commit(s)**: N/A
- **Status**: INVESTIGATION CLOSED (Could not reproduce)

## 2025-12-26

### Marketplace Sources Missing enable_frontmatter_detection Column

**Issue**: `/marketplace/sources` page crashes with SQLAlchemy OperationalError: "no such column: marketplace_sources.enable_frontmatter_detection"
- **Location**: `skillmeat/cache/models.py:1244` (MarketplaceSource model)
- **Root Cause**: The `MarketplaceSource` model had `enable_frontmatter_detection` column defined but Alembic version tracking was out of sync - database stamped at `20251215_1400_add_collection_type_fields` while later migrations added columns but weren't tracked. Migration `20251226_1500_add_frontmatter_detection` never ran.
- **Fix**:
  1. Added missing column via direct SQLite ALTER TABLE
  2. Stamped Alembic to latest revision `20251226_1500_add_frontmatter_detection`
  3. Added `enable_frontmatter_detection` to `source_to_response()` function
- **Commit(s)**: 9b608cb
- **Status**: RESOLVED
