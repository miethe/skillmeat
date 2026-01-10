# Deployment Architecture Map - SkillMeat

Complete mapping of artifact deployment features across frontend, backend, and core logic.

**Generated**: 2026-01-10
**Branch**: feat/projects-deploy-refactor-v1

---

## Overview

The deployment system follows a multi-layer architecture:

```
Frontend UI (React)
    ↓ (HTTP REST)
Backend API (FastAPI)
    ↓ (Direct method calls)
Core Business Logic (Python)
    ↓ (Direct method calls)
Storage/Filesystem (TOML + filesystem)
```

---

## Frontend Layer

### 1. Deploy Dialog Component
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/collection/deploy-dialog.tsx`

**Exports**:
- `DeployDialog` (component)
- `DeployDialogProps` (interface)

**Key Functions**:
- `handleDeploy()` - Initiates deployment via `useDeployArtifact()` mutation
- `handleComplete()` - Handles successful deployment completion
- `isAlreadyDeployed()` - Checks if artifact already deployed to a project
- `canDeploy` (memo) - Validates deployment readiness

**Props**:
```typescript
interface DeployDialogProps {
  artifact: Artifact | null;
  existingDeploymentPaths?: string[];
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}
```

**Key State**:
- `selectedProjectId` - Selected project (or CUSTOM_PATH_VALUE)
- `customPath` - Custom deployment path
- `overwrite` - Whether to overwrite existing deployment
- `isDeploying` - Deployment in progress flag
- `streamUrl` - SSE stream URL (for progress updates)

**Project Selection Logic**:
- Users can select from existing projects loaded via `useProjects()`
- Or enter custom path via `CUSTOM_PATH_VALUE` selector
- Selected project's path used as `project_path` in deployment request
- Checks `existingDeploymentPaths` to prevent re-deployment to same project

**Deployment Request**:
```typescript
await deployMutation.mutateAsync({
  artifact_id: `${artifact.type}:${artifact.name}`,
  artifact_name: artifact.name,
  artifact_type: artifact.type,
  project_path: effectivePath || undefined,
  overwrite,
});
```

---

### 2. Progress Indicator Component
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/collection/progress-indicator.tsx`

**Exports**:
- `ProgressIndicator` (component)
- `ProgressStep` (interface)
- `ProgressIndicatorProps` (interface)

**Key Features**:
- SSE stream listener via `useSSE()` hook
- Real-time step-by-step progress updates
- Overall progress percentage calculation
- Error handling with fallback UI

**Props**:
```typescript
interface ProgressIndicatorProps {
  streamUrl: string | null;
  enabled?: boolean;
  initialSteps?: ProgressStep[];
  onComplete?: (success: boolean, message?: string) => void;
  onError?: (error: Error) => void;
}
```

**Message Handling**:
- `progress` event: Updates individual step status
- `complete` event: Marks deployment as complete
- `error_event` event: Handles operation errors

**Step States**:
```typescript
type ProgressStep = {
  step: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  message?: string;
  progress?: number;
};
```

**SSE Connection Flow**:
1. Component mounted with `streamUrl`
2. `useSSE()` establishes EventSource connection
3. Messages parsed and steps updated
4. On completion/error, `onComplete()` called
5. Connection automatically closed on unmount

---

### 3. API Client
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/deployments.ts`

**Exports**:
- `deployArtifact()` - POST to `/api/v1/deploy`
- `undeployArtifact()` - POST to `/api/v1/deploy/undeploy`
- `listDeployments()` - GET from `/api/v1/deploy`
- `getDeploymentSummary()` - Calculates summary from list response
- `getDeployments()` - Filters deployments by type/status

**Request Types**:
```typescript
interface ArtifactDeployRequest {
  artifact_id: string;
  artifact_name: string;
  artifact_type: string;
  project_path?: string;
  overwrite?: boolean;
}

interface ArtifactUndeployRequest {
  artifact_name: string;
  artifact_type: string;
  project_path?: string;
}
```

**Response Types**:
```typescript
interface ArtifactDeploymentResponse {
  success: boolean;
  message: string;
  deployment_id: string;
  stream_url: string | null;  // SSE endpoint (if available)
  artifact_name: string;
  artifact_type: string;
  project_path: string;
  deployed_path: string;
  deployed_at: string;
}

interface ArtifactDeploymentListResponse {
  project_path: string;
  deployments: ArtifactDeploymentInfo[];
  total: number;
}

interface ArtifactDeploymentInfo {
  artifact_name: string;
  artifact_type: string;
  from_collection: string;
  deployed_at: string;
  artifact_path: string;
  project_path: string;
  collection_sha: string;
  local_modifications: boolean;
  sync_status: 'synced' | 'modified' | 'outdated' | 'unknown';
}
```

**Error Handling**:
```typescript
if (!response.ok) {
  const errorText = await response.text().catch(() => response.statusText);
  throw new Error(`Failed to deploy artifact: ${errorText}`);
}
```

---

### 4. Deployments Hook
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/use-deployments.ts`

**Exports**:
- `useDeploymentList()` - Query for deployments at a project
- `useDeployments()` - Query with filtering
- `useDeploymentSummary()` - Query summary statistics
- `useDeployArtifact()` - Mutation to deploy artifact
- `useUndeployArtifact()` - Mutation to undeploy artifact
- `useRefreshDeployments()` - Manual cache refresh
- `deploymentKeys` - TanStack Query key factory

**Query Key Structure**:
```typescript
deploymentKeys = {
  all: ['deployments'],
  lists: ['deployments', 'list'],
  list: ['deployments', 'list', { projectPath }],
  summaries: ['deployments', 'summary'],
  summary: ['deployments', 'summary', { projectPath }],
  filtered: ['deployments', 'list', 'filtered', params],
}
```

**Cache Invalidation on Success**:
```typescript
onSuccess: (_, variables) => {
  // Invalidate specific project deployments
  queryClient.invalidateQueries({
    queryKey: deploymentKeys.list(variables.project_path),
  });
  // Invalidate summaries
  queryClient.invalidateQueries({
    queryKey: deploymentKeys.summary(variables.project_path),
  });
  // Invalidate all filtered queries
  queryClient.invalidateQueries({
    queryKey: deploymentKeys.lists(),
  });
}
```

**Configuration**:
- `staleTime`: 2 minutes (deployments change frequently)
- `refetchOnWindowFocus`: true
- `retry`: 1 (default from query client)

---

### 5. Unified Entity Modal (Deployments Tab)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/entity/unified-entity-modal.tsx`

**Fragment**: Lines 57-62, 150+

**Key Imports**:
```typescript
import { useDeploymentList } from '@/hooks/use-deployments';
import { useProjects } from '@/hooks/useProjects';
import { DeployDialog } from '@/components/collection/deploy-dialog';
import { DeploymentCard, DeploymentCardSkeleton } from '@/components/deployments/deployment-card';
```

**Deployments Tab Features**:
- Lists deployed instances of artifact
- Shows sync status (synced/modified/outdated)
- "Deploy to new project" button opens DeployDialog
- "Undeploy" action via `useUndeployArtifact()`
- Real-time refresh via `useRefreshDeployments()`

---

### 6. SSE Hook
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useSSE.ts`

**Status**: **STUB - Incomplete Implementation**

**Exports**:
- `useSSE()` hook
- `SSEMessage` interface
- `SSEState` interface
- `UseSSEOptions` interface

**Current Implementation**:
```typescript
export function useSSE<T = any>(url: string | null, options: UseSSEOptions = {}) {
  const [state, setState] = useState<SSEState<T>>({
    isConnected: false,
    isConnecting: false,
    error: null,
    messages: [],
    lastMessage: null,
  });

  const connect = useCallback(() => {
    // TODO: Implement full SSE logic from DEPLOY_SYNC_UI_IMPLEMENTATION.md
    setState((prev) => ({ ...prev, isConnecting: true }));
  }, []);

  const disconnect = useCallback(() => {
    setState((prev) => ({ ...prev, isConnected: false }));
    options.onClose?.();
  }, [options]);

  useEffect(() => {
    if (options.enabled && url) {
      connect();
    }
    return () => disconnect();
  }, [url, options.enabled, connect, disconnect]);

  return {
    ...state,
    connect,
    disconnect,
    clearMessages,
  };
}
```

**ISSUE**: `connect()` callback only sets `isConnecting` to true - never actually establishes EventSource connection!

**Expected Usage** (from progress-indicator):
```typescript
const { isConnected, isConnecting, error } = useSSE<ProgressData>(streamUrl, {
  enabled,
  onMessage: (message) => {
    // Handle 'progress', 'complete', 'error_event' events
  },
  onError: (err) => { /* ... */ },
});
```

---

### 7. Project Management
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/projects/components/create-project-dialog.tsx`

**Exports**:
- `CreateProjectDialog` (component)
- `CreateProjectDialogProps` (interface)

**Key Functions**:
- `validateForm()` - Validates name (1-100 chars, alphanumeric+hyphens/underscores) and path (absolute)
- `handleCreate()` - Creates project via `useCreateProject()` mutation

**Props**:
```typescript
interface CreateProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (project?: ProjectDetail) => void;
}

interface ProjectDetail {
  id: string;
  path: string;
  name: string;
  deployment_count: number;
  last_deployment?: string;
}
```

**Request Body**:
```typescript
interface ProjectCreateRequest {
  name: string;
  path: string;
  description?: string | null;
}
```

**Integration with Deploy Dialog**:
- Deploy dialog has "Create Project" button (Plus icon)
- Opens CreateProjectDialog on click
- On success, newly created project auto-selected in deploy dialog
- Callback: `handleProjectCreated(newProject)` updates `selectedProjectId`

---

### 8. Deployment Card Component
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/deployments/deployment-card.tsx`

**Exports**:
- `DeploymentCard` (component)
- `DeploymentCardSkeleton` (skeleton)
- `Deployment` (interface)

**Displays**:
- Artifact name and type
- Project path
- Deployed date
- Sync status badge
- Action buttons (sync, undeploy, open project)

---

## Backend API Layer

### 1. Deployments Router
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/deployments.py`

**Prefix**: `/api/v1/deploy`

**Endpoints**:

#### POST `/deploy`
**Handler**: `deploy_artifact()`

**Request Schema**: `DeployRequest`
```python
{
  "artifact_id": "skill:my-skill",
  "artifact_name": "my-skill",
  "artifact_type": "skill",
  "project_path": "/path/to/project",  # Optional, uses CWD if omitted
  "overwrite": false,  # Optional, defaults to false
}
```

**Logic Flow**:
1. Parse artifact type (validates enum)
2. Resolve project path (uses CWD if not provided)
3. Create `.claude` directory if missing
4. Check for existing deployment via `DeploymentTracker.get_deployment()`
5. If exists and `overwrite=false`: return 409 Conflict
6. If exists and `overwrite=true`: call `undeploy()` first to remove old version
7. Call `deployment_mgr.deploy_artifacts()` with artifact name
8. On success: return `DeploymentResponse` with `stream_url=None` (SSE not yet implemented)

**Response**: `DeploymentResponse`
```python
{
  "success": true,
  "message": "Artifact deployed successfully",
  "deployment_id": "skill:my-skill",
  "stream_url": null,
  "artifact_name": "my-skill",
  "artifact_type": "skill",
  "project_path": "/path/to/project",
  "deployed_path": "/path/to/project/.claude/skills/my-skill",
  "deployed_at": "2025-12-13T10:00:00Z"
}
```

**Status Codes**:
- 200: Success
- 400: Invalid artifact type or request
- 404: Artifact not found
- 409: Artifact already deployed (and `overwrite=false`)
- 500: Deployment failed

---

#### POST `/deploy/undeploy`
**Handler**: `undeploy_artifact()`

**Request Schema**: `UndeployRequest`
```python
{
  "artifact_name": "my-skill",
  "artifact_type": "skill",
  "project_path": "/path/to/project",  # Optional
}
```

**Logic**:
1. Parse artifact type
2. Resolve project path
3. Call `deployment_mgr.undeploy()`
4. Return success response

**Response**: `UndeployResponse`
```python
{
  "success": true,
  "message": "Artifact removed successfully",
  "artifact_name": "my-skill",
  "artifact_type": "skill",
  "project_path": "/path/to/project"
}
```

---

#### GET `/deploy`
**Handler**: `list_deployments()`

**Query Parameters**:
- `project_path` (optional): Project directory (uses CWD if omitted)

**Logic**:
1. Resolve project path
2. Call `deployment_mgr.list_deployments(project_path)`
3. Call `deployment_mgr.check_deployment_status(project_path)` to get sync status
4. Map deployments to response format

**Response**: `DeploymentListResponse`
```python
{
  "project_path": "/path/to/project",
  "deployments": [
    {
      "artifact_name": "my-skill",
      "artifact_type": "skill",
      "from_collection": "~/.skillmeat/collection",
      "deployed_at": "2025-12-13T10:00:00Z",
      "artifact_path": ".claude/skills/my-skill",
      "project_path": "/path/to/project",
      "collection_sha": "abc123...",
      "local_modifications": false,
      "sync_status": "synced"
    }
  ],
  "total": 1
}
```

**Sync Status Values**:
- `synced`: Content matches collection version
- `modified`: Local modifications detected
- `outdated`: Collection version is newer
- `unknown`: Status cannot be determined

---

### 2. Deployment Schemas
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/deployments.py`

**Models**:
```python
class DeployRequest(BaseModel):
    artifact_id: str  # "type:name" format
    artifact_name: str
    artifact_type: str
    project_path: Optional[str] = None
    collection_name: Optional[str] = None
    overwrite: bool = False

class UndeployRequest(BaseModel):
    artifact_name: str
    artifact_type: str
    project_path: Optional[str] = None

class DeploymentInfo(BaseModel):
    artifact_name: str
    artifact_type: str
    from_collection: str
    deployed_at: str
    artifact_path: str
    project_path: str
    collection_sha: str
    local_modifications: bool
    sync_status: Optional[str] = None

class DeploymentListResponse(BaseModel):
    project_path: str
    deployments: List[DeploymentInfo]
    total: int

class DeploymentResponse(BaseModel):
    success: bool
    message: str
    deployment_id: str
    stream_url: Optional[str] = None
    artifact_name: str
    artifact_type: str
    project_path: str
    deployed_path: str
    deployed_at: str

class UndeployResponse(BaseModel):
    success: bool
    message: str
    artifact_name: str
    artifact_type: str
    project_path: str
```

---

## Core Business Logic Layer

### 1. Deployment Manager
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/deployment.py`

**Class**: `DeploymentManager`

**Constructor**:
```python
def __init__(self, collection_mgr=None, version_mgr=None):
    self.collection_mgr = collection_mgr
    self.filesystem_mgr = FilesystemManager()
    self._version_mgr = version_mgr
```

**Key Methods**:

#### `deploy_artifacts()`
**Signature**:
```python
def deploy_artifacts(
    self,
    artifact_names: List[str],
    collection_name: Optional[str] = None,
    project_path: Optional[Path] = None,
    artifact_type: Optional[ArtifactType] = None,
) -> List[Deployment]:
```

**Steps**:
1. Resolve project path (uses CWD if not provided)
2. Create `.claude` directory structure if needed
3. For each artifact name:
   - Fetch artifact from collection
   - Compute content hash
   - Copy to project `.claude/{type}/{name}`
   - Record deployment via `DeploymentTracker.record_deployment()`
4. Return list of created Deployment objects

**Return Type**: `List[Deployment]`

---

#### `undeploy()`
**Signature**:
```python
def undeploy(
    self,
    artifact_name: str,
    artifact_type: ArtifactType,
    project_path: Optional[Path] = None,
) -> None:
```

**Steps**:
1. Remove artifact files from `.claude/{type}/{name}`
2. Remove deployment record via `DeploymentTracker.remove_deployment()`
3. Clean up empty directories

---

#### `list_deployments()`
**Returns**: `List[Deployment]` for a project

---

#### `check_deployment_status()`
**Returns**: `Dict[str, str]` mapping deployment keys to sync status

---

### 2. Deployment Data Class
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/deployment.py` (lines 17-128)

**Class**: `Deployment`

**Fields**:
```python
@dataclass
class Deployment:
    # Core identification
    artifact_name: str
    artifact_type: str
    from_collection: str

    # Deployment metadata
    deployed_at: datetime
    artifact_path: Path  # Relative path in .claude/

    # Version tracking
    content_hash: str  # SHA-256 of artifact content at deployment
    local_modifications: bool = False

    # Optional fields
    parent_hash: Optional[str] = None
    version_lineage: List[str] = []
    last_modified_check: Optional[datetime] = None
    modification_detected_at: Optional[datetime] = None
    merge_base_snapshot: Optional[str] = None

    # Backward compatibility
    collection_sha: Optional[str] = None
```

**Serialization**:
- `to_dict()` - Converts to dict for TOML storage
- `from_dict()` - Creates instance from dict (with backward compatibility)

---

### 3. Deployment Tracker (Storage)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/storage/deployment.py`

**Class**: `DeploymentTracker` (static methods)

**Key Methods**:

#### `get_deployment_file_path(project_path)`
Returns path to `.claude/deployments.toml`

---

#### `read_deployments(project_path)`
**Returns**: `List[Deployment]` from TOML file

---

#### `write_deployments(project_path, deployments)`
Writes deployments list to TOML file

---

#### `record_deployment(project_path, artifact_name, artifact_type, content_hash, ...)`
**Steps**:
1. Read existing deployments
2. Create new Deployment record
3. Add to list
4. Write back to TOML

---

#### `get_deployment(project_path, artifact_name, artifact_type)`
**Returns**: Single Deployment or None

**Used by router** to check if artifact already deployed (for conflict detection)

---

#### `remove_deployment(project_path, artifact_name, artifact_type)`
**Steps**:
1. Read existing deployments
2. Remove matching deployment
3. Write back to TOML

---

#### `detect_modifications(project_path, deployment)`
Compares current artifact files with deployment's `content_hash` to detect local modifications

---

## Data Flow Diagrams

### Deployment Flow
```
User clicks "Deploy" in UI
    ↓
DeployDialog validates selection
    ↓
useDeployArtifact() calls deployArtifact()
    ↓
fetch POST /api/v1/deploy with {artifact_id, project_path, overwrite}
    ↓
[Backend] deploy_artifact() handler
    ├─ Parse artifact type
    ├─ Resolve project path
    ├─ Create .claude/ directory
    ├─ Check DeploymentTracker.get_deployment() for existing
    │  ├─ If exists and overwrite=false → 409 Conflict
    │  └─ If exists and overwrite=true → undeploy() first
    ├─ Call DeploymentManager.deploy_artifacts()
    │  ├─ Fetch artifact from collection
    │  ├─ Compute content hash
    │  ├─ Copy to .claude/{type}/{name}/
    │  └─ Call DeploymentTracker.record_deployment()
    └─ Return DeploymentResponse (with stream_url=null)
    ↓
Frontend: mutationFn returns successfully
    ↓
onSuccess callback:
    ├─ Invalidate deployment queries for project
    ├─ Show success toast
    └─ Close dialog after 1.5s delay
    ↓
User sees confirmation and dialog closes
```

### Project Selection Flow
```
User opens deploy dialog
    ↓
useProjects() loads list of registered projects
    ↓
User selects project from dropdown
    ├─ Project name shown with check mark if already deployed
    ├─ isAlreadyDeployed() checks existingDeploymentPaths
    └─ selectedProjectId stored in state
    ↓
OR user selects "Custom path..." option
    ├─ CUSTOM_PATH_VALUE selected
    ├─ Custom path input appears
    └─ customPath stored in state
    ↓
canDeploy computed based on selection:
    ├─ Custom path: valid if not empty
    └─ Project: valid if not already deployed (isAlreadyDeployed check)
    ↓
effectivePath determined:
    ├─ If custom: customPath
    └─ If project: selectedProject.path
    ↓
User clicks Deploy button
    ↓
project_path: effectivePath sent to backend
```

### SSE/Progress Flow (NOT YET IMPLEMENTED)
```
User clicks Deploy → isDeploying = true
    ↓
deployment response includes stream_url
    ↓
setStreamUrl(stream_url)
    ↓
ProgressIndicator mounted with streamUrl
    ↓
useSSE(streamUrl) attempts to connect
    ├─ ❌ ISSUE: connect() only sets isConnecting=true
    ├─ Never creates EventSource
    ├─ Never actually connects to SSE endpoint
    └─ Messages never received
    ↓
Progress indicator shows "Waiting..."
    ↓
Deployment completes backend (without SSE notifications)
    ↓
handleComplete(true) called after timeout
    ↓
Dialog closes
```

---

## Critical Issues Identified

### 1. SSE Hook Incomplete (BLOCKER)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useSSE.ts`

**Problem**: `connect()` callback only sets state but never establishes EventSource connection

**Current Code**:
```typescript
const connect = useCallback(() => {
  // TODO: Implement full SSE logic from DEPLOY_SYNC_UI_IMPLEMENTATION.md
  setState((prev) => ({ ...prev, isConnecting: true }));
}, []);
```

**Impact**:
- Progress updates never received from backend
- ProgressIndicator shows "Waiting..." forever
- Deployment completes but UI doesn't update

**Expected Implementation** (from usage in progress-indicator):
```typescript
// Should create EventSource, listen to events
// Call options.onMessage() for each message
// Call options.onError() on connection failure
// Call options.onClose() on disconnect
```

---

### 2. SSE Endpoint Not Implemented (BACKEND)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/deployments.py:167`

**Code**:
```python
stream_url=None,  # SSE streaming not yet implemented
```

**Status**: Response always returns `stream_url: null`

**Impact**: Even if SSE hook were fixed, no backend endpoint to stream progress

---

### 3. Missing Overwrite Parameter in Dialog
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/collection/deploy-dialog.tsx:44`

**Issue**: `overwrite` state exists but checkbox not shown to user in UI

**Current Code**:
```typescript
const [overwrite, setOverwrite] = useState(false);
// ... but no UI control to set this value
```

**Result**: `overwrite` always false, even if user wants to replace existing deployment

---

### 4. Project Path Not Returned Consistently
**Multiple issues**:

**In deploy dialog** (line 116):
```typescript
project_path: effectivePath || undefined,
```

Sends undefined if effectivePath is empty string (should validate first)

**In backend response** (line 170):
```typescript
project_path=str(project_path),
```

Returns resolved absolute path, not original input

---

## Type Definitions

### Frontend Types
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/types/deployments.ts`

```typescript
export interface ArtifactDeployRequest {
  artifact_id: string;
  artifact_name: string;
  artifact_type: string;
  project_path?: string;
  overwrite?: boolean;
  collection_name?: string;
}

export interface ArtifactDeploymentResponse {
  success: boolean;
  message: string;
  deployment_id: string;
  stream_url?: string | null;
  artifact_name: string;
  artifact_type: string;
  project_path: string;
  deployed_path: string;
  deployed_at: string;
}

export interface ArtifactDeploymentInfo {
  artifact_name: string;
  artifact_type: string;
  from_collection: string;
  deployed_at: string;
  artifact_path: string;
  project_path: string;
  collection_sha: string;
  local_modifications: boolean;
  sync_status?: string;
}

export interface ArtifactDeploymentListResponse {
  project_path: string;
  deployments: ArtifactDeploymentInfo[];
  total: number;
}

export interface ArtifactUndeployRequest {
  artifact_name: string;
  artifact_type: string;
  project_path?: string;
}

export interface ArtifactUndeployResponse {
  success: boolean;
  message: string;
  artifact_name: string;
  artifact_type: string;
  project_path: string;
}
```

---

## Configuration & Constants

### Frontend
- `API_BASE`: `process.env.NEXT_PUBLIC_API_URL` or `'http://localhost:8080'`
- `API_VERSION`: `process.env.NEXT_PUBLIC_API_VERSION` or `'v1'`
- `CUSTOM_PATH_VALUE`: `'__custom__'` (selector value for custom path mode)
- Deployment cache stale time: 2 minutes
- Dialog auto-close delay: 1.5 seconds after success

### Backend
- Deployment tracker file: `.claude/deployments.toml`
- Default project path: Current working directory
- Artifact types: `skill`, `command`, `agent`, `mcp`, `hook`

---

## Testing Files

**Unit Tests**:
- `/Users/miethe/dev/homelab/development/skillmeat/tests/unit/test_deployment_model.py`
- `/Users/miethe/dev/homelab/development/skillmeat/tests/unit/test_deployment_manager.py`
- `/Users/miethe/dev/homelab/development/skillmeat/tests/unit/test_deployment_version_integration.py`
- `/Users/miethe/dev/homelab/development/skillmeat/tests/unit/test_deployment_tracker.py`

**Integration Tests**:
- `/Users/miethe/dev/homelab/development/skillmeat/tests/integration/test_deployment_version_tracking.py`
- `/Users/miethe/dev/homelab/development/skillmeat/tests/integration/test_deployment_workflow.py`

**E2E Tests**:
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/tests/deploy-sync.spec.ts`

---

## Reference Documentation

**Project CLAUDE.md Files**:
- `/Users/miethe/dev/homelab/development/skillmeat/CLAUDE.md` - Project root
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/CLAUDE.md` - Backend API patterns
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/CLAUDE.md` - Frontend patterns

**Router Patterns**:
- `/Users/miethe/dev/homelab/development/skillmeat/.claude/rules/api/routers.md` - FastAPI layer contracts

**Hook Patterns**:
- `/Users/miethe/dev/homelab/development/skillmeat/.claude/rules/web/hooks.md` - TanStack Query patterns

**API Client Patterns**:
- `/Users/miethe/dev/homelab/development/skillmeat/.claude/rules/web/api-client.md` - Endpoint mappings, error handling
