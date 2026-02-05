# Deploy to Project Infrastructure Analysis

## Overview
Complete exploration of the Deploy to Project feature infrastructure, including button component, dialog flow, and supporting API endpoints.

## Component Inventory

### Frontend Components

#### 1. Deploy Button (`components/shared/deploy-button.tsx`)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/shared/deploy-button.tsx`

**Type**: Split-style dropdown button with three actions

**Props**:
- `artifact: Artifact | null` - Artifact to deploy (null disables)
- `existingDeploymentPaths?: string[]` - Detection of overwrite situations
- `onDeploySuccess?: () => void` - Callback after successful deployment
- `variant?: 'default' | 'outline'` - Button styling
- `size?: 'default' | 'sm'` - Button size
- `className?: string` - Additional CSS classes
- `label?: string` - Label override (default: "Deploy")

**Actions**:
1. Primary click → Opens `DeployDialog`
2. "Quick Deploy via CLI" → Copies deploy command to clipboard
3. "CLI Deploy Options..." → Opens modal with full CLI commands

**Key Handler**:
```typescript
handlePrimaryClick() → setShowDeployDialog(true)
```

---

#### 2. Deploy Dialog (`components/collection/deploy-dialog.tsx`)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/collection/deploy-dialog.tsx`

**Type**: Multi-step modal dialog

**Features**:
- Project selector with dropdown
- Overwrite detection (checks `existingDeploymentPaths`)
- Custom path input with validation
- Custom deployment sub-path with directory traversal protection
- Progress indicator during deployment
- Confirmation dialog when overwriting existing deployments

**Key State**:
- `selectedProjectId` - Selected project or `CUSTOM_PATH_VALUE`
- `customPath` - Custom project path (when using custom path mode)
- `customPathEnabled` - Toggle for custom sub-directory
- `customSubPath` - Sub-directory within default deployment path
- `overwriteEnabled` - Overwrite existing deployment toggle
- `isDeploying` - Active deployment state

**Validation Logic**:
```typescript
validateAndSanitizeSubPath(input): Checks for:
  - Directory traversal (..)
  - Absolute paths (/)
  - Windows paths (C:)
  - Dangerous characters (\x00, \n, \r)
  - Auto-appends trailing slash
```

**Hook Usage**:
```typescript
useDeployArtifact() // Mutation for deployment
useProjects() // Query for available projects
```

**Flow**:
1. User selects project or custom path
2. If already deployed and not overwriting → Show warning + require toggle
3. If overwriting → Show confirmation dialog
4. Execute deployment via `deployMutation.mutateAsync()`
5. Progress indicator shows deployment steps
6. Close dialog + trigger success callback on completion

**Deployment Path Calculation**:
```typescript
effectivePath = useCustomPath ? customPath : selectedProject?.path
computedDestPath = defaultDeployPath + customSubPath (if enabled)
// Example: '.claude/skills/' + 'dev/' = '.claude/skills/dev/'
```

---

#### 3. Merge Workflow Dialog (`components/merge/merge-workflow-dialog.tsx`)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/merge/merge-workflow-dialog.tsx`

**Type**: Multi-step workflow orchestrator

**Steps**:
1. `analyze` - Merge safety analysis
2. `preview` - Preview merge changes
3. `resolve` - Resolve conflicts
4. `confirm` - Final confirmation
5. `execute` - Execute merge

**Props**:
```typescript
{
  open: boolean
  onOpenChange: (open: boolean) => void
  baseSnapshotId: string
  localCollection: string
  remoteSnapshotId: string
  remoteCollection?: string
  onComplete?: () => void
}
```

**Key Hooks**:
- `useAnalyzeMerge()` - POST `/merge/analyze`
- `usePreviewMerge()` - POST `/merge/preview`
- `useExecuteMerge()` - POST `/merge/execute`
- `useResolveConflict()` - POST `/merge/resolve`

**State Management**:
```typescript
workflowState: {
  step: 'analyze' | 'preview' | 'resolve' | 'confirm' | 'execute'
  unresolvedConflicts: ConflictMetadata[]
  resolvedConflicts: Map<string, string>
  strategy: 'auto' | 'manual'
  analysis?: MergeSafetyResponse
}
```

---

#### 4. Sync Status Tab (`components/sync-status/sync-status-tab.tsx`)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/sync-status/sync-status-tab.tsx`

**Type**: Tab content component within artifact modal

**Props**:
```typescript
{
  entity: Artifact
  mode: 'collection' | 'project'
  projectPath?: string
  onClose: () => void
}
```

**Features**:
- 3-tier flow visualization (Source → Collection → Project)
- Comparison scope selector
- Side-by-side diff viewer
- Drift status alerts
- Sync actions footer

**Queries**:
1. **Upstream Diff** (if `hasValidUpstreamSource(entity)` && not 'discovered'):
   ```typescript
   queryKey: ['upstream-diff', entity.id, entity.collection]
   url: `/artifacts/{id}/upstream-diff?collection={name}`
   enabled: entity has valid GitHub source
   ```

2. **Project Diff** (if `projectPath` exists && not 'discovered'):
   ```typescript
   queryKey: ['project-diff', entity.id, projectPath]
   url: `/artifacts/{id}/diff?project_path={path}`
   enabled: !!projectPath
   ```

**Mutations**:
- `syncMutation` - POST `/artifacts/{id}/sync` (pulls from source)
- Invalidates: artifacts, deployments, upstream-diff, project-diff, collections

**Drift Status Computation**:
```typescript
computeDriftStatus(diffData):
  - 'none' if no changes
  - 'conflict' if unified_diff contains '<<<<<<< '
  - 'modified' otherwise
```

---

### Supporting Types

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/types/merge.ts`
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/types/sync.ts`

Key interfaces:
- `MergeAnalyzeRequest` / `MergeSafetyResponse`
- `MergePreviewRequest` / `MergePreviewResponse`
- `MergeExecuteRequest` / `MergeExecuteResponse`
- `ConflictMetadata` - Conflict information
- `SyncConflict` - Sync-specific conflict structure

---

## API Infrastructure

### Frontend API Clients

#### 1. Merge API (`lib/api/merge.ts`)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/merge.ts`

**Endpoints**:
- `POST /api/v1/merge/analyze` → `analyzeMergeSafety(request)`
- `POST /api/v1/merge/preview` → `previewMerge(request)`
- `POST /api/v1/merge/execute` → `executeMerge(request)`
- `POST /api/v1/merge/resolve` → `resolveConflict(request)`

**Case Conversion**: camelCase ↔ snake_case (for API compatibility)

#### 2. Context Sync API (`lib/api/context-sync.ts`)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/lib/api/context-sync.ts`

**Endpoints**:
- `POST /api/v1/context-sync/pull` → `pullChanges(projectPath, entityIds?)`
- `POST /api/v1/context-sync/push` → `pushChanges(projectPath, entityIds?, overwrite?)`
- `GET /api/v1/context-sync/status` → `getSyncStatus(projectPath)`
- `POST /api/v1/context-sync/resolve` → `resolveConflict(projectPath, entityId, resolution, mergedContent?)`

**Types**:
```typescript
SyncResolution = 'keep_local' | 'keep_remote' | 'merge'
SyncResult: { entity_id, entity_name, action, message }
SyncConflict: { entity_id, entity_name, collection_hash, deployed_hash, content, paths }
SyncStatus: { modified_in_project, modified_in_collection, conflicts }
```

#### 3. Deployments API (`lib/api/deployments.ts`)
**Functions**:
- `listDeployments()`
- `getDeploymentSummary()`
- `getDeployments()`
- `removeProjectDeployment()`

### Backend API Routers

#### 1. Deployments Router (`routers/deployments.py`)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/deployments.py`

**Endpoints**:
- `POST /api/v1/deploy` - Deploy artifact to project
  - Body: `DeployRequest`
  - Response: `DeploymentResponse`
  - Status codes: 200 (success), 400 (invalid), 401 (unauthorized), 404 (not found), 500 (error)

**Request Schema**:
```python
class DeployRequest:
  artifact_id: str  # "type:name"
  project_path: Optional[str]
  overwrite: bool = False
  dest_path: Optional[str]  # Custom destination path
  collection_name: Optional[str] = 'default'
```

**Validation**:
```python
validate_dest_path(dest_path):
  - Rejects directory traversal (..)
  - Rejects absolute paths (/)
  - Rejects Windows absolute paths (C:)
  - Rejects dangerous characters (\x00, \n, \r)
  - Auto-normalizes trailing slash
```

**Manager**: `DeploymentManager(collection_mgr)`

---

#### 2. Artifacts Router - Diff Endpoint (`routers/artifacts.py`)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/artifacts.py:3681`

**Endpoint**: `GET /api/v1/artifacts/{artifact_id}/diff`

**Query Parameters**:
- `project_path` (required) - Path to deployed project
- `collection` (optional) - Collection filter

**Response**: `ArtifactDiffResponse`
```python
{
  "artifact_id": "skill:name",
  "artifact_name": "name",
  "artifact_type": "skill",
  "collection_name": "default",
  "project_path": "/path/to/project",
  "has_changes": True,
  "files": [
    {
      "file_path": "SKILL.md",
      "status": "modified|added|deleted|unchanged",
      "collection_hash": "abc123",
      "project_hash": "def456",
      "unified_diff": "--- a/SKILL.md\n+++ b/SKILL.md\n..."
    }
  ],
  "summary": {
    "added": 0,
    "modified": 1,
    "deleted": 0,
    "unchanged": 3
  }
}
```

**Implementation**:
- Compares artifact in collection with deployed version in project
- Generates file-level diffs with unified diff format
- Returns file hashes for change detection
- Summary counts added/modified/deleted/unchanged files

---

#### 3. Artifacts Router - Upstream Diff Endpoint (`routers/artifacts.py:4040`)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/artifacts.py:4040`

**Endpoint**: `GET /api/v1/artifacts/{artifact_id}/upstream-diff`

**Query Parameters**:
- `collection` (optional) - Collection filter

**Response**: `ArtifactUpstreamDiffResponse`
- Same structure as `ArtifactDiffResponse`
- Compares collection version with upstream source (GitHub)

---

#### 4. Sync Artifact Endpoint (`routers/artifacts.py:3050`)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/artifacts.py:3050`

**Endpoint**: `POST /api/v1/artifacts/{artifact_id}/sync`

**Request Body**:
```python
{
  "project_path": Optional[str],  # If provided, sync from project
  "resolution": Optional[SyncResolution]  # Resolution strategy
}
```

**Response**: `ArtifactSyncResponse`
```python
{
  "artifact_id": "skill:name",
  "synced": True,
  "message": "Sync completed successfully",
  "conflicts": Optional[List[SyncConflict]]
}
```

**Logic**:
- If no `project_path`: Sync from upstream source (pull)
- If `project_path`: Sync from project (pull deployed version)
- Returns conflicts if detected during sync

---

#### 5. Merge Router (`routers/merge.py`)
**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/merge.py`

**Endpoints**:
1. `POST /api/v1/merge/analyze` (Line 52)
   - Request: `MergeAnalyzeRequest`
   - Response: `MergeSafetyResponse`
   - Purpose: Dry-run three-way diff without modifying files

2. `POST /api/v1/merge/preview` (similar pattern)
   - Response: `MergePreviewResponse`
   - Purpose: Preview changes that would result from merge

3. `POST /api/v1/merge/execute` (similar pattern)
   - Request: `MergeExecuteRequest`
   - Response: `MergeExecuteResponse`
   - Purpose: Execute merge with full conflict detection

4. `POST /api/v1/merge/resolve` (similar pattern)
   - Request: `ConflictResolveRequest`
   - Response: `ConflictResolveResponse`
   - Purpose: Resolve individual conflicts

**Conflict Detection**:
- Service: `VersionMergeService().analyze_merge_safety()`
- Detects conflicts during dry-run analysis
- Three-way merge (base, local, remote)
- Returns `ConflictMetadata[]` with conflict details

---

## Current Flow

### 1. Deploy Button Click Flow
```
User clicks "Deploy to Project"
  ↓
DeployButton.handlePrimaryClick()
  ↓
setShowDeployDialog(true)
  ↓
DeployDialog renders
  ↓
User selects project or custom path
  ↓
User clicks "Deploy"
  ↓
deployMutation.mutateAsync({
  artifact_id: "type:name",
  artifact_name: name,
  artifact_type: type,
  project_path: selectedProject.path,
  overwrite: overwriteEnabled,
  dest_path: computedDestPath,
  collection_name: artifact.collection
})
  ↓
POST /api/v1/deploy
  ↓
Backend: DeploymentManager.deploy()
  ↓
Copy artifact files to project
Update deployment registry
  ↓
Return DeploymentResponse
  ↓
onDeploySuccess callback
  ↓
Dialog closes
  ↓
UI refetches data via onSuccess callbacks
```

### 2. Sync Status Tab Flow
```
User opens artifact modal with Sync tab
  ↓
SyncStatusTab mounts
  ↓
Query: GET /api/v1/artifacts/{id}/upstream-diff
        (if GitHub source + tracking enabled)
  ↓
Query: GET /api/v1/artifacts/{id}/diff?project_path={path}
        (if projectPath provided)
  ↓
Queries return ArtifactDiffResponse objects
  ↓
computeDriftStatus() analyzes for conflicts
  ↓
DriftAlertBanner displays status
  ↓
DiffViewer shows side-by-side comparison
  ↓
User clicks "Pull Changes" / "Push Changes"
  ↓
Sync mutation fires
  ↓
Cache invalidation refreshes all queries
```

### 3. Merge Workflow Flow
```
User initiates merge
  ↓
MergeWorkflowDialog opens
  ↓
Step 1: ANALYZE
  POST /api/v1/merge/analyze
  VersionMergeService.analyze_merge_safety()
    → Three-way diff (base, local, remote)
    → Detect conflicts
    → Return MergeSafetyResponse
  ↓
If conflicts found:
  unresolvedConflicts = analysis.conflicts

Step 2: PREVIEW
  POST /api/v1/merge/preview
  Returns potential changes

Step 3: RESOLVE
  User resolves conflicts or chooses merge strategy
  POST /api/v1/merge/resolve (for each conflict)

Step 4: CONFIRM
  User reviews merge results

Step 5: EXECUTE
  POST /api/v1/merge/execute
  Apply merged changes to both snapshots
  ↓
onComplete callback
```

---

## Conflict Detection Infrastructure

### Frontend Conflict Detection
**Location**: `components/sync-status/sync-status-tab.tsx:61-72`

```typescript
computeDriftStatus(diffData):
  if !diffData.has_changes → 'none'
  if diffData.files.some(f => f.unified_diff includes '<<<<<<< ') → 'conflict'
  else → 'modified'
```

**Display**: `DriftAlertBanner` shows conflict status and offers actions

### Backend Conflict Detection
**Location**: `api/routers/merge.py` (merge service)

```python
VersionMergeService.analyze_merge_safety():
  1. Load base, local (collection), remote (upstream/other)
  2. Three-way merge algorithm
  3. Detect line-level conflicts
  4. Return ConflictMetadata[] in response
```

**Conflict Metadata**:
```python
class ConflictMetadata:
  entity_id: str
  entity_name: str
  conflict_type: str  # 'text', 'structural', etc.
  base_content: str
  local_content: str
  remote_content: str
  suggested_resolution: Optional[str]
```

---

## What's Missing

### 1. Wiring Deploy → Sync Status
**Issue**: Deploy button doesn't automatically open Sync tab or show conflict resolution UI

**Current State**:
- Deploy dialog is independent modal
- Sync status tab is separate component in artifact modal
- No connection between deployment and upstream/project diff display

**Gap**: After deployment, user must manually navigate to artifact modal > Sync tab to see project conflicts

**Solution Needed**:
```typescript
// Option 1: Auto-open artifact modal with Sync tab active after deploy
onDeploySuccess={() => {
  openArtifactModal(artifact, activeTab='sync', projectPath=deployedPath)
}}

// Option 2: Show inline sync status in deploy dialog after deployment
// Option 3: Add post-deploy merge suggestion UI
```

### 2. Pre-Deployment Conflict Detection
**Issue**: No conflict check before deploying artifact

**Current Gaps**:
- Deploy dialog only checks if artifact already deployed (overwrite)
- Doesn't check for conflicts with project version before deployment
- No preview of what files would change

**What Exists**:
- `/diff` endpoint can compare collection vs project
- Merge analysis endpoints exist
- Conflict detection infrastructure is there

**Solution Needed**:
```typescript
// Add pre-deployment conflict check
useEffect(() => {
  if (selectedProject) {
    // Query /artifacts/{id}/diff?project_path={selectedProject.path}
    // Show conflicts/changes warning
    // Offer merge workflow option
  }
}, [selectedProject])
```

### 3. Post-Deployment Merge Suggestion
**Issue**: After deployment, if changes exist in project, user must manually trigger merge

**Current State**:
- Merge dialog exists and works
- Sync status tab can show conflicts
- But no integration point after deployment success

**Gap**: Deploy completes → artifact deployed → no suggestion to resolve conflicts

**Solution Needed**:
```typescript
// After successful deployment
onDeploySuccess={() => {
  // Check if project version has conflicts with just-deployed version
  // If yes, suggest: "Merge workspace changes?"
  // Link to MergeWorkflowDialog
}
```

### 4. SyncDialog Not Wired
**Location**: `components/collection/sync-dialog.tsx` exists but unclear where it's used

**Purpose**: Appears to be legacy sync UI

**Current State**:
- `SyncStatusTab` has reference to it
- Never actually opened in current codebase

**Gap**: May be duplicate/redundant with `SyncStatusTab` functionality

---

## Integration Points

### Data Flow Path
```
Deploy Button
  → DeployDialog (project selection + overwrite handling)
    → useDeploy hook
      → POST /api/v1/deploy
        → Backend DeploymentManager
          → Copy files + update registry

After Deploy:
  onSuccess → Cache invalidation
            → Could trigger: SyncStatusTab auto-open
            → Could trigger: Merge conflict check
            → Could trigger: Merge workflow suggestion
```

### Cache Invalidation
**Current Implementation** (`useDeploy.ts`):
```typescript
onSuccess: async (data, variables) => {
  await queryClient.invalidateQueries({ queryKey: ['artifacts'] });
  await queryClient.invalidateQueries({ queryKey: ['deployments'] });
  // Project-specific data NOT invalidated
}
```

**Missing**:
- Invalidate `['project-diff', entity.id]` after deployment
- Invalidate `['upstream-diff']` if deployment changes source status

---

## File Paths Summary

### Frontend
| Component | Path |
|-----------|------|
| Deploy Button | `/skillmeat/web/components/shared/deploy-button.tsx` |
| Deploy Dialog | `/skillmeat/web/components/collection/deploy-dialog.tsx` |
| Merge Workflow Dialog | `/skillmeat/web/components/merge/merge-workflow-dialog.tsx` |
| Sync Status Tab | `/skillmeat/web/components/sync-status/sync-status-tab.tsx` |
| Merge API Client | `/skillmeat/web/lib/api/merge.ts` |
| Sync API Client | `/skillmeat/web/lib/api/context-sync.ts` |
| useDeploy Hook | `/skillmeat/web/hooks/useDeploy.ts` |

### Backend
| Router | Path |
|--------|------|
| Deployments | `/skillmeat/api/routers/deployments.py` |
| Artifacts (diff) | `/skillmeat/api/routers/artifacts.py:3681` |
| Artifacts (upstream-diff) | `/skillmeat/api/routers/artifacts.py:4040` |
| Artifacts (sync) | `/skillmeat/api/routers/artifacts.py:3050` |
| Merge | `/skillmeat/api/routers/merge.py` |
| Context Sync | `/skillmeat/api/routers/context_sync.py` |

---

## Recommendations

### Next Steps for Feature Completion
1. **Post-Deploy Conflict Detection**
   - Query `/diff` endpoint after deployment
   - Display conflicts in success state or new modal

2. **Auto-Open Sync Tab**
   - After deployment, open artifact modal with Sync tab active
   - Show project-vs-collection diff
   - Offer merge workflow

3. **Merge Suggestion**
   - After deployment, if conflicts exist
   - Suggest running merge workflow
   - Link directly to `MergeWorkflowDialog`

4. **Cache Invalidation Fix**
   - Add project-diff and upstream-diff to post-deploy invalidation
   - Ensure UI shows fresh data immediately

5. **Pre-Deploy Preview**
   - Show what files would change before committing
   - Warn about conflicts before deployment
   - Offer merge as alternative to deployment
