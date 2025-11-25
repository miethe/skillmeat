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
