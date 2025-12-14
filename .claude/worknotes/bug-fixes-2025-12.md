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
