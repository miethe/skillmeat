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

## 2025-11-28

### Web Build Clean Script Fails on pnpm Symlinks

**Issue**: `pnpm build:fresh` fails when cleaning `.next` directory due to nested pnpm symlinks in `.next/standalone/node_modules/.pnpm/` causing "Directory not empty" errors on macOS.

- **Location**: `skillmeat/web/package.json:11-13`
- **Root Cause**: pnpm creates complex symlink structures inside the Next.js standalone build output. On macOS, `rm -rf` can fail on these nested symlink directories when file permissions or locks prevent immediate deletion.
- **Fix**: Enhanced clean scripts to retry with permission fix if initial `rm -rf` fails:
  - `clean`: Attempts `rm -rf`, falls back to `chmod -R u+w` then retry, always succeeds
  - `clean:cache`: Same pattern for cache-only cleanup
  - `clean:all`: Same pattern for full cleanup including node_modules
- **Commit(s)**: `cb8e14c`
- **Status**: RESOLVED

---

### Custom API Port Not Applied to Frontend

**Issue**: Running `skillmeat web dev --api-port 8080 --web-port 3001` starts the API on port 8080, but the frontend continues making requests to port 8000.

- **Location**: `skillmeat/web/manager.py:151-155`
- **Root Cause**: The WebManager's `_get_web_config()` method only set the `PORT` environment variable for Next.js but never set `NEXT_PUBLIC_API_URL`. Without this variable, the frontend fell back to hardcoded defaults (inconsistently 8000 or 8080 across different modules).
- **Fix**:
  1. Added `NEXT_PUBLIC_API_URL` environment variable in `manager.py` using the configured `api_host` and `api_port`
  2. Unified the environment variable name from `NEXT_PUBLIC_API_BASE_URL` to `NEXT_PUBLIC_API_URL` in `sdk/core/OpenAPI.ts`
  3. Standardized fallback port to 8080 in `app/settings/page.tsx` for consistency with `lib/api.ts`
- **Commit(s)**: `b10af74`
- **Status**: RESOLVED

---

### Missing EntityLifecycleProvider in Project Detail Page

**Issue**: Clicking into a project from the projects list causes React error: "useEntityLifecycle must be used within EntityLifecycleProvider"

- **Location**: `skillmeat/web/app/projects/[id]/page.tsx:366-370`
- **Root Cause**: The ProjectDetailPage component renders UnifiedEntityModal which internally calls useEntityLifecycle hook, but the page did not wrap its content in EntityLifecycleProvider. When users clicked on a deployed artifact to view details, the modal attempted to access the context and threw an error.
- **Fix**:
  1. Added import for EntityLifecycleProvider from '@/components/entity/EntityLifecycleProvider' (line 22)
  2. Wrapped entire page return JSX with `<EntityLifecycleProvider mode="project" projectPath={project?.path}>` (lines 179-374)
  3. Pattern matches other project pages like `/projects/[id]/manage/page.tsx`
- **Commit(s)**: `3164567`
- **Status**: RESOLVED

---

### React Warning: asChild Prop on DOM Element

**Issue**: React console warning when using Button component with asChild prop: "React does not recognize the `asChild` prop on a DOM element"

- **Location**: `skillmeat/web/components/ui/button.tsx:44-48`
- **Root Cause**: The Button component declared `asChild?: boolean` in its TypeScript interface but didn't implement the prop handling logic. The prop was being spread directly to the native `<button>` DOM element via `{...props}`, causing React to warn about an unrecognized prop.
- **Fix**:
  1. Imported `Slot` from `@radix-ui/react-slot` (line 2)
  2. Destructured `asChild = false` from props to prevent it from spreading to DOM (line 43)
  3. Created polymorphic component selector: `const Comp = asChild ? Slot : "button"` (line 44)
  4. Replaced hardcoded `<button>` with dynamic `<Comp>` element (lines 46-50)
  5. Installed `@radix-ui/react-slot` dependency
- **Commit(s)**: `ee7c59d`
- **Status**: RESOLVED

---

### Sync with Upstream Fails with 400 Bad Request

**Issue**: Attempting "Sync with Upstream" on a skill within a project fails with HTTP 400 error: `POST /api/v1/artifacts/notebooklm-skill/sync - 400`

- **Location**: `skillmeat/web/app/projects/[id]/page.tsx:106`
- **Root Cause**: The Entity object created when clicking on a deployed artifact used only the artifact name for the `id` field (`id: matchingArtifact.name`). However, the backend API expects entity IDs in `type:name` format (e.g., `skill:notebooklm-skill`) for proper routing. The sync endpoint validates this format and returns 400 when receiving just the name.
- **Fix**:
  1. Changed Entity `id` from `matchingArtifact.name` to `${matchingArtifact.type}:${matchingArtifact.name}` (line 106)
  2. Ensures consistency with Entity interface spec: `id` should be "Unique identifier in format 'type:name'"
  3. Enables proper API routing for sync, deploy, and other entity operations
- **Commit(s)**: `ee7c59d`
- **Status**: RESOLVED

---

## 2025-11-29

### Upstream Diff Endpoint AttributeError on artifact.upstream.spec

**Issue**: Navigating to Sync Status tab on an artifact fails with: `AttributeError: 'str' object has no attribute 'spec'`

- **Location**: `skillmeat/api/routers/artifacts.py:2922`
- **Root Cause**: The `get_artifact_upstream_diff` endpoint incorrectly accessed `artifact.upstream.spec`, but `artifact.upstream` is already a string containing the source spec (e.g., "anthropics/skills/pdf"), not an object with a `.spec` attribute.
- **Fix**: Changed `artifact.upstream.spec` to `artifact.upstream` to correctly use the string value directly.
- **Commit(s)**: `46a6fd6`
- **Status**: RESOLVED
