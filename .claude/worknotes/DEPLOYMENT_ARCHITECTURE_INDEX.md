# Deployment Architecture - Complete Index

**Generated**: 2026-01-10
**Branch**: feat/projects-deploy-refactor-v1
**Scope**: All artifact deployment features across frontend, backend, and core

---

## Documentation Files Created

1. **deployment-architecture-map.md** - Comprehensive architecture document
   - Detailed file-by-file breakdown
   - Data flow diagrams
   - Critical issues identified
   - Type definitions and configuration

2. **deployment-files-quick-ref.md** - Quick reference table
   - All files organized by layer
   - Purpose and key exports
   - Problem areas summary
   - Dependency map

3. **DEPLOYMENT_ARCHITECTURE_INDEX.md** - This file
   - Master index for all deployment resources
   - File paths and purposes
   - Quick navigation guide

---

## All Deployment-Related Files

### Frontend Components (React/TypeScript)

#### Primary Components
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/collection/deploy-dialog.tsx` (355 lines)
  - **Exports**: `DeployDialog`, `DeployDialogProps`
  - **Purpose**: Main deployment UI dialog
  - **Key Features**: Project selection, path input, overwrite toggle (state only)
  - **State**: selectedProjectId, customPath, overwrite, isDeploying, streamUrl
  - **Key Methods**: handleDeploy(), handleComplete(), isAlreadyDeployed(), canDeploy (memo)

- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/collection/progress-indicator.tsx` (225 lines)
  - **Exports**: `ProgressIndicator`, `ProgressStep`, `ProgressIndicatorProps`
  - **Purpose**: Real-time progress display with SSE integration
  - **Key Features**: Step-by-step progress, overall progress bar, error handling
  - **Uses**: `useSSE()` hook for event streaming
  - **Events**: 'progress', 'complete', 'error_event'

- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/deployments/deployment-card.tsx`
  - **Exports**: `DeploymentCard`, `DeploymentCardSkeleton`, `Deployment`
  - **Purpose**: Single deployment display card
  - **Features**: Shows artifact name, type, project path, sync status, dates

- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/deployments/deployment-actions.tsx`
  - **Purpose**: Undeploy, sync, and other actions

- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/entity/unified-entity-modal.tsx` (100+ relevant lines)
  - **Purpose**: Entity detail modal with deployments tab
  - **Imports**: useDeploymentList, useProjects, DeployDialog, DeploymentCard
  - **Features**: Lists artifact deployments, deploy to new project button

- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/projects/components/create-project-dialog.tsx` (100+ lines)
  - **Exports**: `CreateProjectDialog`, `CreateProjectDialogProps`
  - **Purpose**: Create new projects from within deployment flow
  - **Validation**: Name (1-100 chars, alphanumeric+hyphens/underscores), Path (absolute)

#### Hooks
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/use-deployments.ts` (255 lines)
  - **Exports**: useDeployArtifact(), useUndeployArtifact(), useDeploymentList(), useDeploymentSummary(), useRefreshDeployments(), deploymentKeys
  - **Framework**: TanStack Query v5
  - **Key Features**: Automatic cache invalidation, hierarchical query keys, error logging

- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useSSE.ts` (65 lines) **⚠️ STUB**
  - **Exports**: useSSE(), SSEMessage, SSEState, UseSSEOptions
  - **Status**: NOT IMPLEMENTED - Only sets isConnecting=true, never creates EventSource
  - **Problem**: Blocks real-time progress updates
  - **Impact**: BLOCKER for SSE progress streaming

- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useProjects.ts`
  - **Exports**: useProjects(), useCreateProject()
  - **Purpose**: Project listing and creation

#### API Client
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/deployments.ts` (218 lines)
  - **Exports**: deployArtifact(), undeployArtifact(), listDeployments(), getDeploymentSummary(), getDeployments()
  - **Base URL**: `/api/v1`
  - **Error Handling**: Extracts error text, throws descriptive Error

#### Type Definitions
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/types/deployments.ts`
  - **Types**: ArtifactDeployRequest, ArtifactDeploymentResponse, ArtifactDeploymentInfo, ArtifactDeploymentListResponse, ArtifactUndeployRequest, ArtifactUndeployResponse

---

### Backend API (FastAPI/Python)

#### Routers
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/deployments.py` (381 lines)
  - **Prefix**: `/api/v1/deploy`
  - **Tags**: ["deployments"]
  - **Endpoints**:
    - `POST /` - deploy_artifact()
    - `POST /undeploy` - undeploy_artifact()
    - `GET /` - list_deployments()
  - **Dependencies**: verify_api_key on all endpoints
  - **Key Logic**:
    - Validates artifact type (enum)
    - Resolves project path (uses CWD if None)
    - Creates .claude/ directory
    - Checks for existing deployment via DeploymentTracker
    - Returns 409 Conflict if exists and overwrite=false
    - Calls undeploy() first if overwrite=true
    - Records deployment to TOML via DeploymentTracker
    - Returns stream_url=None (SSE not yet implemented)

#### Schemas
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/deployments.py`
  - **Models**: DeployRequest, UndeployRequest, DeploymentInfo, DeploymentResponse, UndeployResponse, DeploymentListResponse
  - **Validation**: Pydantic field validators

---

### Core Business Logic (Python)

#### Deployment Management
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/deployment.py` (150+ lines shown)
  - **Classes**:
    - `DeploymentManager` - Orchestrates deployment operations
      - `deploy_artifacts()` - Copy from collection to project
      - `undeploy()` - Remove from project
      - `list_deployments()` - Get all deployments
      - `check_deployment_status()` - Determine sync status
    - `Deployment` (dataclass) - Single deployment record
      - Fields: artifact_name, artifact_type, from_collection, deployed_at, artifact_path, content_hash, local_modifications, parent_hash, version_lineage, merge_base_snapshot
      - Methods: to_dict(), from_dict() for TOML serialization

#### Storage/Tracking
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/storage/deployment.py`
  - **Class**: DeploymentTracker (static methods only)
  - **Methods**:
    - `get_deployment_file_path()` - Returns .claude/deployments.toml path
    - `read_deployments()` - Load from TOML
    - `write_deployments()` - Save to TOML
    - `record_deployment()` - Add new deployment record
    - `get_deployment()` - Check if artifact deployed (used for conflict detection)
    - `remove_deployment()` - Delete deployment record
    - `detect_modifications()` - Compare hashes to detect drift
  - **Storage Format**: TOML file at `.claude/deployments.toml`

#### MCP Deployment (Separate)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/mcp/deployment.py`
  - **Note**: Separate from web artifact deployment
  - **Not covered**: In this architecture map

---

### Testing

#### Unit Tests
- `/Users/miethe/dev/homelab/development/skillmeat/tests/unit/test_deployment_model.py`
  - Tests: `Deployment` dataclass serialization/deserialization

- `/Users/miethe/dev/homelab/development/skillmeat/tests/unit/test_deployment_manager.py`
  - Tests: `DeploymentManager` operations

- `/Users/miethe/dev/homelab/development/skillmeat/tests/unit/test_deployment_version_integration.py`
  - Tests: Version tracking with deployments

- `/Users/miethe/dev/homelab/development/skillmeat/tests/unit/test_deployment_tracker.py`
  - Tests: `DeploymentTracker` TOML I/O

#### Integration Tests
- `/Users/miethe/dev/homelab/development/skillmeat/tests/integration/test_deployment_version_tracking.py`
  - End-to-end version tracking workflow

- `/Users/miethe/dev/homelab/development/skillmeat/tests/integration/test_deployment_workflow.py`
  - Complete deployment workflow with all layers

#### E2E Tests
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/tests/deploy-sync.spec.ts`
  - Browser-based deployment UI flow tests

---

## Architecture Layers

### Layer 1: Frontend UI (React Components)
**Responsibility**: User interaction, form validation, state management
**Key Files**:
- deploy-dialog.tsx - Input/selection
- progress-indicator.tsx - Feedback
- deployment-card.tsx - Display

### Layer 2: Frontend Logic (Hooks & API Client)
**Responsibility**: Business logic, API calls, cache management
**Key Files**:
- use-deployments.ts - TanStack Query hooks
- lib/api/deployments.ts - HTTP requests

### Layer 3: Backend HTTP (FastAPI Router)
**Responsibility**: Request validation, response formatting, HTTP semantics
**Key Files**:
- routers/deployments.py - Endpoints

### Layer 4: Backend Logic (Core Managers)
**Responsibility**: Orchestration, business rules, validation
**Key Files**:
- core/deployment.py - DeploymentManager

### Layer 5: Storage (Filesystem)
**Responsibility**: Persistence, file I/O
**Key Files**:
- storage/deployment.py - TOML I/O

---

## Critical Issues

### Issue #1: useSSE Hook Incomplete ⚠️ BLOCKER

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useSSE.ts`
**Lines**: 37-40

**Problem**:
```typescript
const connect = useCallback(() => {
  // TODO: Implement full SSE logic from DEPLOY_SYNC_UI_IMPLEMENTATION.md
  setState((prev) => ({ ...prev, isConnecting: true }));
}, []);
```

Only sets `isConnecting=true`, never establishes EventSource connection.

**Impact**:
- ProgressIndicator shows "Waiting..." forever
- Deployment completes but UI doesn't update
- Real-time progress updates completely broken

**Expected Implementation**:
```typescript
// Should:
// 1. Create EventSource(url)
// 2. Listen to message events
// 3. Call options.onMessage() for each event
// 4. Call options.onError() on failure
// 5. Call options.onClose() on disconnect
```

---

### Issue #2: SSE Endpoint Not Implemented ⚠️ BLOCKER

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/deployments.py`
**Line**: 167

**Problem**:
```python
stream_url=None,  # SSE streaming not yet implemented
```

Backend never returns a stream URL, so no endpoint to connect to.

**Impact**:
- Even if useSSE hook fixed, no backend SSE endpoint exists
- Would need separate endpoint to stream progress events

**Expected Implementation**:
- Separate SSE endpoint at `/api/v1/deploy/stream/{deployment_id}`
- Stream progress events in real-time

---

### Issue #3: Overwrite Checkbox Missing ⚠️ MINOR

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/collection/deploy-dialog.tsx`
**Lines**: 44, 300-316

**Problem**:
State exists (`overwrite`, `setOverwrite`) but no UI control.

**Current Code**:
```typescript
const [overwrite, setOverwrite] = useState(false);  // Line 44
// No <input>, <checkbox>, or <toggle> to set this value
```

**Impact**:
- `overwrite` always false
- Users can't force overwrite of existing deployments
- Must delete deployment manually and redeploy

**Expected Fix**:
- Add checkbox to dialog
- Allow user to opt-in to overwrite

---

## Project Selection Logic

### Modes
1. **Registered Project Mode**
   - User selects from dropdown of existing projects
   - `selectedProjectId` is project.id
   - Path resolved from selected project: `selectedProject.path`

2. **Custom Path Mode**
   - User selects `CUSTOM_PATH_VALUE` ('__custom__')
   - Input field appears for custom path
   - Path taken directly from input: `customPath`

### Validation
```typescript
canDeploy = useMemo(() => {
  if (!selectedProjectId) return false;

  if (useCustomPath) {
    return customPath.trim().length > 0;
  }

  if (selectedProject) {
    return !isAlreadyDeployed(selectedProject.path);
  }

  return false;
}, [selectedProjectId, useCustomPath, customPath, selectedProject, existingDeploymentPaths])
```

### Conflict Prevention
- `isAlreadyDeployed(projectPath)` checks if artifact deployed to any subdirectory
- Returns true if any `existingDeploymentPaths` starts with `projectPath + '/.claude/'`
- Disables deploy button if already deployed

### Backend Validation
```python
# In router - resolve and validate path
project_path = Path(request.project_path) if request.project_path else Path.cwd()
project_path = project_path.resolve()

# Create .claude directory if missing
claude_dir = project_path / ".claude"
if not claude_dir.exists():
    claude_dir.mkdir(parents=True, exist_ok=True)

# Check for existing deployment
existing_deployment = DeploymentTracker.get_deployment(
    project_path, request.artifact_name, request.artifact_type
)

if existing_deployment:
    if not request.overwrite:
        raise HTTPException(409, "Already deployed. Set overwrite=true to replace.")
    else:
        deployment_mgr.undeploy(...)  # Remove old version first
```

---

## Deployment Request/Response

### Request
```typescript
interface ArtifactDeployRequest {
  artifact_id: string;           // "type:name"
  artifact_name: string;
  artifact_type: string;
  project_path?: string;         // Optional, uses CWD if omitted
  overwrite?: boolean;           // Default: false
  collection_name?: string;      // Optional
}
```

### Response
```typescript
interface ArtifactDeploymentResponse {
  success: boolean;
  message: string;
  deployment_id: string;
  stream_url: string | null;     // Always null (SSE not implemented)
  artifact_name: string;
  artifact_type: string;
  project_path: string;          // Resolved absolute path
  deployed_path: string;         // Path to deployed artifact
  deployed_at: string;           // ISO 8601 timestamp
}
```

---

## Cache Invalidation Strategy

### TanStack Query Keys
```typescript
deploymentKeys = {
  all: ['deployments'],
  lists: () => [...deploymentKeys.all, 'list'],
  list: (projectPath?: string) => [...deploymentKeys.lists(), { projectPath }],
  summaries: () => [...deploymentKeys.all, 'summary'],
  summary: (projectPath?: string) => [...deploymentKeys.summaries(), { projectPath }],
  filtered: (params?: DeploymentQueryParams) => [...deploymentKeys.lists(), 'filtered', params],
}
```

### On Success Invalidation
```typescript
onSuccess: (_, variables) => {
  // Specific project deployments
  queryClient.invalidateQueries({
    queryKey: deploymentKeys.list(variables.project_path),
  });
  // Summary for this project
  queryClient.invalidateQueries({
    queryKey: deploymentKeys.summary(variables.project_path),
  });
  // All filtered queries
  queryClient.invalidateQueries({
    queryKey: deploymentKeys.lists(),
  });
}
```

---

## Configuration

### Frontend Defaults
- API Base: `process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'`
- API Version: `process.env.NEXT_PUBLIC_API_VERSION || 'v1'`
- Custom path selector value: `'__custom__'`
- Dialog close delay: 1.5 seconds after success
- Deployment cache stale time: 2 minutes

### Backend Defaults
- Deployment manifest: `.claude/deployments.toml`
- Default project path: Current working directory
- Artifact type subdirs: `skills/`, `commands/`, `agents/`, `mcp/`, `hooks/`

### Environment Variables
```bash
# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8080
NEXT_PUBLIC_API_VERSION=v1

# Backend
SKILLMEAT_API_HOST=0.0.0.0
SKILLMEAT_API_PORT=8000
SKILLMEAT_COLLECTION_PATH=~/.skillmeat/collection
```

---

## Next Steps / Fixes Needed

1. **Fix useSSE hook** (BLOCKER)
   - Implement EventSource connection logic
   - Add proper cleanup on unmount
   - Call callbacks on messages, errors, disconnect

2. **Add SSE endpoint** (BLOCKER)
   - Implement `/api/v1/deploy/stream/{deployment_id}`
   - Stream progress events in real-time
   - Return stream URL in deploy response

3. **Add overwrite UI** (NICE-TO-HAVE)
   - Add checkbox to deploy dialog
   - Wire to setOverwrite state
   - Show warning when overwrite enabled

4. **Improve error handling**
   - Better error messages
   - Recovery options for failed deployments
   - Retry logic

---

## Related Documentation

- **Root CLAUDE.md**: `/Users/miethe/dev/homelab/development/skillmeat/CLAUDE.md`
- **Backend CLAUDE.md**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/CLAUDE.md`
- **Frontend CLAUDE.md**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/CLAUDE.md`
- **Router Patterns**: `/Users/miethe/dev/homelab/development/skillmeat/.claude/rules/api/routers.md`
- **Hook Patterns**: `/Users/miethe/dev/homelab/development/skillmeat/.claude/rules/web/hooks.md`
- **API Client Patterns**: `/Users/miethe/dev/homelab/development/skillmeat/.claude/rules/web/api-client.md`

---

**Last Updated**: 2026-01-10
**Status**: Complete mapping of all deployment architecture
**Needs**: Implementation of SSE hook and backend endpoint
