# Bug Fixes - November 2025

## 2025-11-18

### API Import Errors

**Issue 1: BundleImporter Import Error**
- **Location**: `skillmeat/api/routers/marketplace.py:29`
- **Error**: Cannot import `BundleImporter` from `skillmeat.core.sharing.bundle`
- **Root Cause**: `BundleImporter` is defined in `skillmeat/core/sharing/importer.py`, not `bundle.py`
- **Fix**: Updated import from `from skillmeat.core.sharing.bundle import Bundle, BundleImporter` to separate imports

**Issue 2: RateLimitMiddleware Missing Import**
- **Location**: `skillmeat/api/server.py:103`
- **Error**: `RateLimitMiddleware` not defined
- **Root Cause**: Missing import in server.py, though class is properly exported from middleware module
- **Fix**: Added `RateLimitMiddleware, get_rate_limiter` to line 22 imports

**Validation**: Both imports now work successfully; server app creation succeeds

### Collection Page 422 Validation Error

**Issue**: `/collection` page failing to load with 422 validation error
- **Location**: `skillmeat/web/hooks/useArtifacts.ts:233`
- **Error**: `limit` parameter validation failed - frontend requested 200 but API max is 100
- **Root Cause**: `DEFAULT_ARTIFACT_LIMIT = 200` exceeded backend API constraint `le=100`
- **Fix**: Reduced `DEFAULT_ARTIFACT_LIMIT` from 200 to 100
- **Validation**: Code change confirmed; API accepts limit=100

### Marketplace Endpoints 404 Errors

**Issue**: All marketplace endpoints returning 404 errors
- **Location**: `skillmeat/web/hooks/useMarketplace.ts:22`
- **Error**: GET `/api/marketplace/*` routes not found
- **Root Cause**: Frontend calling `/api/marketplace/*` but backend serving at `/api/v1/marketplace/*` - missing version segment
- **Fix**: Updated `API_BASE_URL` from `"http://localhost:8000/api"` to `"http://localhost:8000/api/v1"`
- **Validation**: Brokers and listings endpoints now accessible; returns 2 brokers (skillmeat, claudehub)

### Deploy Function Non-Functional (Feature Completion)

**Issue**: Web UI deploy/undeploy functionality not operational
- **Locations**:
  - Backend: `skillmeat/api/routers/artifacts.py` (missing endpoints)
  - Frontend: `skillmeat/web/hooks/useDeploy.ts` (stubbed with mock)
- **Status**: Incomplete feature - core logic existed but API/UI integration missing
- **Root Cause**:
  - No POST `/artifacts/{id}/deploy` or `/artifacts/{id}/undeploy` endpoints
  - Frontend hooks using setTimeout mock instead of real API calls
- **Implementation**:
  - Added `ArtifactDeployRequest/Response` schemas following MCP pattern
  - Implemented deploy/undeploy endpoints with full error handling
  - Wired frontend hooks to real API using centralized `apiRequest` utility
  - Integrated with existing `DeploymentManager` from core layer
  - Added deployment tracking via `.skillmeat-deployed.toml`
- **Files Modified**:
  - `skillmeat/api/schemas/artifacts.py` (schemas)
  - `skillmeat/api/routers/artifacts.py` (endpoints)
  - `skillmeat/web/hooks/useDeploy.ts` (API integration)
  - `skillmeat/web/components/collection/deploy-dialog.tsx` (response handling)
  - `skillmeat/web/hooks/useMcpServers.ts` (refactored to use apiRequest)
- **Note**: API server restart required to activate new endpoints

## 2025-11-25

### React Error #310 on /manage Tab

**Issue**: Navigating to `/manage` tab crashes with React error #310 (fewer hooks than expected)
- **Location**: `skillmeat/web/components/entity/entity-list.tsx:70-208`
- **Error**: `Uncaught Error: Minified React error #310` in `useCallback`
- **Root Cause**: React hooks called after early returns, violating Rules of Hooks:
  - `renderEntityCard` useCallback defined at line 117 (after empty state return at line 102)
  - `renderEntityRow` useCallback defined at line 158 (after grid view return at line 148)
- **Fix**: Moved all `useCallback` hooks before any conditional returns
- **Validation**: Chrome DevTools confirmed no React errors on /manage and /manage?type=command

### atob InvalidCharacterError on /projects/{id}/manage

**Issue**: Navigating to project manage page crashes with InvalidCharacterError
- **Location**: `skillmeat/web/app/projects/[id]/manage/page.tsx:261`
- **Error**: `Uncaught InvalidCharacterError: Failed to execute 'atob' on 'Window'`
- **Root Cause**: Base64 project IDs contain `+`, `/`, `=` chars that get URL-encoded, corrupting the string for `atob()`
- **Fix**: Get `projectPath` from API response (`project.path`) instead of client-side decoding
- **Validation**: Chrome DevTools confirmed no atob errors on /projects/{id}/manage

### Deployment TypeError missing content_hash

**Issue**: Deploying artifact from project manage page throws TypeError
- **Location**: `skillmeat/storage/deployment.py:110`
- **Error**: `TypeError: Deployment.__init__() missing 1 required positional argument: 'content_hash'`
- **Root Cause**: `Deployment` dataclass requires `content_hash` but `record_deployment()` passed deprecated `collection_sha` parameter
- **Fix**: Changed `collection_sha=collection_sha` to `content_hash=collection_sha` in line 116
- **Validation**: API server reloaded successfully; dataclass constructor now receives correct parameter

### Contents Tab Width Overflow in Entity Modal

**Issue**: Content tab in UnifiedEntityModal extends beyond modal width
- **Location**: `skillmeat/web/components/entity/unified-entity-modal.tsx:794`
- **Error**: Content pane overflows modal container on large content
- **Root Cause**: Modal width fixed at `max-w-2xl`, Contents tab using percentage-based file tree width (`w-1/3`), missing `min-w-0` on flex children
- **Fix**:
  - Modal: `max-w-2xl` → `max-w-2xl lg:max-w-5xl xl:max-w-6xl` (responsive width)
  - Contents tab: Added `min-h-0 overflow-hidden` to flex container
  - File tree: Changed `w-1/3` to `w-64 lg:w-72 flex-shrink-0` (fixed width)
  - Content pane: Added `min-w-0 overflow-hidden` for flex constraint
  - Split-preview: Added `overflow-hidden` and proper word-break properties
- **Files Modified**:
  - `unified-entity-modal.tsx` (modal width, Contents tab layout)
  - `content-pane.tsx` (overflow handling)
  - `split-preview.tsx` (markdown preview overflow)

## 2025-11-26

### Next.js Build Cache Corruption (MODULE_NOT_FOUND)

**Issue**: App fails to start with MODULE_NOT_FOUND for vendor chunks
- **Errors**:
  - `Cannot find module './vendor-chunks/@tanstack+query-core@5.90.10.js'`
  - `Cannot find module './vendor-chunks/next@15.5.6_@babel+core@7.28.5_...js'`
- **Root Cause**: Corrupted `.next` build cache with missing webpack vendor chunks
- **Fix**: Clean `.next` directory (`rm -rf .next`) and restart dev server
- **Validation**: Chrome DevTools confirmed collection page loads successfully

### Horizontal Overflow in Entity Modal Content Panes

**Issue**: Content in entity modal extends beyond modal width
- **Locations**:
  - `unified-entity-modal.tsx:967` - Contents tab container
  - `content-pane.tsx:358` - Markdown content wrapper
  - `split-preview.tsx:51` - Split view container
- **Root Cause**: Missing `min-w-0` flex constraints and improper overflow handling
- **Fix**:
  - Added `min-w-0` to Contents tab container for proper flex constraints
  - Changed `overflow-hidden` to `overflow-x-auto overflow-y-hidden` on markdown wrapper
  - Added `min-w-0 overflow-hidden` to split-preview container
  - Added `w-full prose-headings:break-words prose-p:break-words` to preview prose
- **Files Modified**:
  - `unified-entity-modal.tsx`
  - `content-pane.tsx`
  - `split-preview.tsx`

### Edit Mode Navigation Without Warning

**Issue**: Clicking another file while in Edit mode navigates without warning about unsaved changes
- **Location**: `unified-entity-modal.tsx` and `content-pane.tsx`
- **Root Cause**: Edit state was local to ContentPane, parent had no awareness to guard navigation
- **Fix**:
  - Created `UnsavedChangesDialog` component for confirmation prompts
  - Lifted edit state (`isEditing`, `editedContent`) to unified-entity-modal
  - Added navigation guards for file selection (`handleFileSelect`)
  - Added navigation guards for tab switching (`handleTabChange`)
  - Guards check `hasUnsavedChanges` before allowing navigation
  - Dialog offers: Save & Continue, Discard, or Cancel options
- **Files Created**:
  - `unsaved-changes-dialog.tsx`
- **Files Modified**:
  - `unified-entity-modal.tsx` (lift state, add guards, render dialog)
  - `content-pane.tsx` (accept lifted state as props)

### File Save 404 Error (PUT /artifacts/{id}/files/{path})

**Issue**: Saving file changes returns 404 "File not found"
- **Location**: `skillmeat/api/routers/artifacts.py:3037`
- **Error**: `PUT /api/v1/artifacts/skill:notebooklm-skill/files/SKILL.md` returns 404
- **Root Cause**: PUT endpoint manually constructed path using `artifact_type.value` ("skill" singular) instead of `artifact.path` ("skills" plural)
- **Fix**: Changed `artifact_root = Path(collection_path) / artifact_type.value / artifact_name` to `artifact_root = collection_path / artifact.path`

### New Project Not Appearing in /projects

**Issue**: Adding a new project via web UI doesn't show in project list
- **Location**: `skillmeat/api/routers/projects.py:434-438`
- **Root Cause**: `discover_projects()` searches for `.skillmeat-deployed.toml` but new projects only create `.skillmeat-metadata.toml`
- **Fix**: Initialize empty deployment file after creating metadata: `DeploymentTracker.write_deployments(project_path, [])`

### Markdown Preview Code Block Overflow

**Issue**: Code blocks in markdown preview extend beyond modal width
- **Location**: `skillmeat/web/components/editor/split-preview.tsx:67`
- **Fix**: Added `prose-pre:overflow-x-auto prose-code:break-all` to prose container classes

### Deployment content_hash Missing (CLI and Web)

**Issue**: Adding artifact via CLI/web causes `Deployment.__init__() missing 1 required positional argument: 'content_hash'`
- **Location**: `skillmeat/core/deployment.py:220`
- **Root Cause**: `DeploymentManager.deploy_artifacts()` used deprecated `collection_sha` parameter instead of required `content_hash`
- **Fix**: Changed `collection_sha=content_hash` to `content_hash=content_hash`
