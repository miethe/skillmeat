# Bug Fixes - November 2025

## 2025-11-21

### Collection Artifacts API AttributeError

**Issue**: Sync Ops page failing to populate artifacts from collection
- **Location**: `skillmeat/api/routers/collections.py:341-342,352,355`
- **Error**: Multiple AttributeErrors - `'Artifact' object has no attribute 'version'`, `'source'`, `'tuple' object has no attribute 'encode'`
- **Root Cause**:
  - Direct access to non-existent `artifact.version` (should use `resolved_version` or `version_spec`)
  - Direct access to non-existent `artifact.source` (should use `upstream` for GitHub, "local" otherwise)
  - `composite_key()` returns tuple but `encode_cursor()` expects string
- **Fix**:
  - Version: Use `artifact.resolved_version or artifact.version_spec`
  - Source: Use `artifact.upstream if artifact.origin == "github" else "local"`
  - Cursor: Convert tuple to string with `":".join(composite_key())`
- **Validation**: API endpoint tested, returns artifacts successfully

### CollectionManager Method Name Error

**Issue**: Version refresh in Sync Ops failing with AttributeError
- **Location**: `skillmeat/api/routers/artifacts.py:106`, `skillmeat/api/routers/sync.py:732`, `skillmeat/core/sync.py:803,1012,1152,1488,1820`
- **Error**: `'CollectionManager' object has no attribute 'get_collection'. Did you mean: 'delete_collection'?`
- **Root Cause**: Code calling non-existent `get_collection()` method instead of `load_collection()`
- **Fix**: Replace all 7 occurrences of `collection_mgr.get_collection()` with `collection_mgr.load_collection()`
- **Validation**: API endpoint tested successfully

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

### Sharing Page TypeError on Name Access

**Issue**: `/sharing` page crashing with TypeError on render
- **Location**: Multiple components - `bundle-list.tsx:109`, `bundle-preview.tsx:36,165`, `export-dialog.tsx:252,478`
- **Error**: `Cannot read properties of undefined (reading 'name')`
- **Root Cause**:
  - Components accessing `bundle.metadata.name` and `artifact.name` without null checks
  - `useExportBundle` mock generating artifacts with empty metadata objects
  - No defensive coding for optional properties in TypeScript types
- **Fix**:
  - Added optional chaining (`?.`) and fallback values for all `.name` accesses
  - Updated mock data generator to fetch real artifacts from React Query cache
  - Fallback values: "Unnamed Bundle", "Unknown Artifact"
- **Files Modified**:
  - `skillmeat/web/components/sharing/bundle-list.tsx` (3 locations)
  - `skillmeat/web/components/sharing/bundle-preview.tsx` (2 locations)
  - `skillmeat/web/components/sharing/export-dialog.tsx` (2 locations)
  - `skillmeat/web/hooks/useExportBundle.ts` (enhanced mock data)
- **Validation**: Page now renders without crashes; verified with chrome-devtools MCP
