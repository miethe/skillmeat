# Deploy & Sync UI Implementation

## Overview

This document describes the implementation of Phase 3, Task P1-002: Deploy & Sync UI for the SkillMeat web interface.

## Implementation Summary

The Deploy & Sync UI provides users with interactive dialogs for deploying artifacts to projects and syncing them with upstream sources. The implementation includes real-time progress tracking via Server-Sent Events (SSE), conflict resolution, and comprehensive error handling.

## Components Implemented

### Core UI Components

#### 1. Dialog Component (`/components/ui/dialog.tsx`)
- Full-featured dialog component built on Radix UI
- Supports overlay, content, header, footer, title, and description
- Keyboard navigation and accessibility features
- Responsive design with animations

#### 2. Progress Component (`/components/ui/progress.tsx`)
- Visual progress bar with percentage indicator
- Smooth transitions
- Accessible ARIA attributes

#### 3. Toaster Component (`/components/ui/toaster.tsx`)
- Toast notification system using Sonner
- Positioned at top-right
- Supports success, error, warning, and info toasts
- Customized styling to match application theme

### Deploy & Sync Components

#### 1. Progress Indicator (`/components/collection/progress-indicator.tsx`)

**Purpose**: Real-time progress tracking for long-running operations

**Features**:
- SSE-based live updates
- Connection status indicator (connecting, connected, disconnected)
- Step-by-step progress visualization
- Overall progress percentage
- Error state handling
- Completion detection

**Usage**:
```tsx
<ProgressIndicator
  streamUrl="/api/v1/deploy/123/stream"
  enabled={true}
  initialSteps={[
    { step: "Validating", status: "pending" },
    { step: "Copying files", status: "pending" },
  ]}
  onComplete={(success) => console.log("Done:", success)}
  onError={(error) => console.error(error)}
/>
```

**SSE Event Format**:
```json
// Progress event
{
  "event": "progress",
  "data": {
    "step": "Copying files",
    "status": "running",
    "message": "Copying 5 files...",
    "progress": 50,
    "totalSteps": 4,
    "currentStep": 2
  }
}

// Complete event
{
  "event": "complete",
  "data": {
    "message": "Deployment successful",
    "success": true
  }
}

// Error event
{
  "event": "error_event",
  "data": {
    "message": "Failed to deploy artifact",
    "code": "DEPLOY_ERROR"
  }
}
```

#### 2. Deploy Dialog (`/components/collection/deploy-dialog.tsx`)

**Purpose**: Deploy artifacts to projects

**Features**:
- Artifact information display
- Project path input (defaults to current directory)
- Overwrite warning for existing deployments
- Real-time deployment progress
- Success/error handling
- Auto-close on completion

**Flow**:
1. User opens dialog from artifact detail view
2. User enters project path (optional)
3. User clicks "Deploy"
4. Progress indicator shows live updates via SSE
5. On completion, shows success message and closes
6. Invalidates relevant React Query caches

**API Integration**:
- `POST /api/v1/deploy` - Initiates deployment
- `GET /api/v1/deploy/{id}/stream` - SSE progress stream

#### 3. Sync Dialog (`/components/collection/sync-dialog.tsx`)

**Purpose**: Sync artifacts with upstream sources

**Features**:
- Current vs upstream version comparison
- Update availability indicator
- Local modifications warning
- Conflict detection and resolution
- Real-time sync progress
- Success/error handling with change summary

**States**:
- `ready` - Initial state, shows sync options
- `syncing` - Active sync operation with progress
- `conflicts` - Conflicts detected, resolution required
- `complete` - Sync completed successfully

**Flow**:
1. User opens dialog from artifact detail view
2. Dialog shows current vs upstream status
3. User clicks "Sync Now"
4. If conflicts detected, shows ConflictResolver
5. User chooses resolution strategy (ours/theirs)
6. Progress indicator shows live updates
7. On completion, shows summary and closes

**API Integration**:
- `POST /api/v1/sync` - Initiates sync
- `GET /api/v1/sync/{id}/stream` - SSE progress stream

#### 4. Conflict Resolver (`/components/collection/conflict-resolver.tsx`)

**Purpose**: Resolve conflicts between local and upstream versions

**Features**:
- Displays conflicted files with details
- Shows local vs upstream versions
- Two resolution strategies:
  - **Keep Local (Ours)**: Keep local changes, discard upstream
  - **Use Upstream (Theirs)**: Overwrite local with upstream
- File-by-file conflict details
- Conflict type badges (modified, deleted, added)

**Conflict Types**:
- `modified` - File changed in both local and upstream
- `deleted` - File deleted in one version
- `added` - File added in one version

### Custom Hooks

#### 1. useSSE Hook (`/hooks/useSSE.ts`)

**Purpose**: Generic Server-Sent Events connection management

**Features**:
- Auto-reconnection with configurable attempts
- Connection state tracking
- Message buffering
- Custom event handlers
- Error handling
- Cleanup on unmount

**Usage**:
```tsx
const { isConnected, lastMessage, disconnect } = useSSE(
  "/api/v1/deploy/123/stream",
  {
    enabled: true,
    autoReconnect: true,
    maxReconnectAttempts: 5,
    onMessage: (msg) => console.log(msg),
    onError: (err) => console.error(err),
  }
);
```

#### 2. useDeploy Hook (`/hooks/useDeploy.ts`)

**Purpose**: React Query mutation for deployment operations

**Features**:
- Deploy mutation with optimistic updates
- Undeploy mutation for removal
- Automatic cache invalidation
- Toast notifications for success/error
- Custom callbacks

**Usage**:
```tsx
const deployMutation = useDeploy({
  onSuccess: (data) => console.log("Deployed:", data),
  onError: (error) => console.error(error),
});

deployMutation.mutate({
  artifactId: "skill:canvas",
  artifactName: "canvas",
  artifactType: "skill",
  projectPath: "/path/to/project",
  overwrite: true,
});
```

#### 3. useSync Hook (`/hooks/useSync.ts`)

**Purpose**: React Query mutation for sync operations

**Features**:
- Sync mutation with conflict detection
- Check upstream mutation (non-destructive)
- Automatic cache invalidation
- Toast notifications with change summaries
- Conflict callback handler

**Usage**:
```tsx
const syncMutation = useSync({
  onSuccess: (data) => console.log("Synced:", data),
  onConflict: (conflicts) => handleConflicts(conflicts),
  onError: (error) => console.error(error),
});

syncMutation.mutate({
  artifactId: "skill:canvas",
  artifactName: "canvas",
  artifactType: "skill",
  force: false,
  mergeStrategy: "theirs",
});
```

## Updated Components

### Artifact Detail View (`/components/collection/artifact-detail.tsx`)

**Changes**:
- Added "Deploy to Project" button
- Added "Sync with Upstream" button (conditional on hasUpstream)
- Integrated DeployDialog and SyncDialog
- Button styling based on artifact state (outdated artifacts get primary variant)
- State management for dialog visibility

## Backend Requirements

### Required API Endpoints

#### 1. Deploy Endpoints

**POST /api/v1/deploy**

Request:
```json
{
  "artifactId": "skill:canvas",
  "artifactName": "canvas",
  "artifactType": "skill",
  "projectPath": "/path/to/project",
  "collectionName": "default",
  "overwrite": true
}
```

Response:
```json
{
  "success": true,
  "message": "Deployment initiated",
  "deploymentId": "deploy-123",
  "streamUrl": "/api/v1/deploy/deploy-123/stream"
}
```

**GET /api/v1/deploy/{deploymentId}/stream**

SSE Stream:
```
event: progress
data: {"step": "Validating", "status": "running", "message": "Checking artifact...", "progress": 25}

event: progress
data: {"step": "Copying files", "status": "running", "message": "Copying 5 files...", "progress": 50}

event: complete
data: {"message": "Deployment successful", "success": true}
```

#### 2. Sync Endpoints

**POST /api/v1/sync**

Request:
```json
{
  "artifactId": "skill:canvas",
  "artifactName": "canvas",
  "artifactType": "skill",
  "collectionName": "default",
  "force": false,
  "mergeStrategy": "ours"
}
```

Response (Success):
```json
{
  "success": true,
  "message": "Sync completed",
  "syncId": "sync-123",
  "streamUrl": "/api/v1/sync/sync-123/stream",
  "hasConflicts": false,
  "updatedVersion": "v1.1.0",
  "changesSummary": {
    "filesAdded": 0,
    "filesModified": 2,
    "filesDeleted": 0
  }
}
```

Response (Conflicts):
```json
{
  "success": false,
  "message": "Conflicts detected",
  "hasConflicts": true,
  "conflicts": [
    {
      "filePath": "SKILL.md",
      "conflictType": "modified",
      "currentVersion": "v1.0.0",
      "upstreamVersion": "v1.1.0",
      "description": "Local modifications conflict with upstream changes"
    }
  ]
}
```

**GET /api/v1/sync/{syncId}/stream**

SSE Stream:
```
event: progress
data: {"step": "Checking upstream", "status": "running", "message": "Fetching latest...", "progress": 25}

event: progress
data: {"step": "Detecting conflicts", "status": "running", "message": "Analyzing changes...", "progress": 50}

event: complete
data: {"message": "Sync successful", "success": true}
```

#### 3. Upstream Check Endpoint

**GET /api/v1/artifacts/{artifactId}/upstream**

Response:
```json
{
  "artifactId": "skill:canvas",
  "trackingEnabled": true,
  "currentVersion": "v1.0.0",
  "currentSha": "abc123",
  "upstreamVersion": "v1.1.0",
  "upstreamSha": "def456",
  "updateAvailable": true,
  "hasLocalModifications": false,
  "lastChecked": "2025-11-16T12:00:00Z"
}
```

## Implementation Notes

### Mock Data

Currently, the hooks use mock implementations for development. The actual API calls are commented out and need to be uncommented when backend endpoints are ready:

```typescript
// TODO: Replace with actual API call
// const response = await fetch("/api/v1/deploy", {
//   method: "POST",
//   headers: { "Content-Type": "application/json" },
//   body: JSON.stringify(request),
// });
```

### SSE Implementation

The SSE hook supports:
- Multiple event types (progress, complete, error_event)
- Automatic reconnection (up to 5 attempts)
- Connection state tracking
- Message buffering
- Clean disconnect

Backend should implement:
```python
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

async def deployment_stream(deployment_id: str) -> AsyncGenerator[str, None]:
    """Stream deployment progress via SSE"""
    yield f"event: progress\ndata: {json.dumps({'step': 'Starting', 'status': 'running'})}\n\n"

    # ... perform deployment ...

    yield f"event: complete\ndata: {json.dumps({'message': 'Complete'})}\n\n"

@router.get("/deploy/{deployment_id}/stream")
async def stream_deployment(deployment_id: str):
    return StreamingResponse(
        deployment_stream(deployment_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

### Error Handling

All operations include comprehensive error handling:
- Toast notifications for user feedback
- Error boundaries around async operations
- Graceful degradation if SSE not available
- Retry logic for transient failures

### Cache Invalidation

Operations invalidate relevant React Query caches:
- Deploy: `["artifacts"]`, `["deployments"]`, `["projects"]`
- Sync: `["artifacts"]`, `["artifact", id]`

### Accessibility

All components include:
- Keyboard navigation
- ARIA labels and roles
- Focus management
- Screen reader support

## Testing Considerations

### Manual Testing

1. **Deploy Flow**:
   - Open artifact detail
   - Click "Deploy to Project"
   - Enter project path
   - Verify progress updates
   - Verify success message

2. **Sync Flow**:
   - Open outdated artifact
   - Click "Update to Latest Version"
   - Verify progress updates
   - Verify version update

3. **Conflict Resolution**:
   - Trigger sync with conflicts (mock 20% chance)
   - Verify conflict display
   - Select resolution strategy
   - Verify re-sync with strategy

4. **Error Handling**:
   - Test with invalid project path
   - Test with network errors
   - Test SSE disconnection
   - Verify error messages

### Integration Testing

Once backend endpoints are ready:
1. Test actual deployment to project
2. Test actual sync from GitHub
3. Test real conflict scenarios
4. Test SSE stream performance
5. Test concurrent operations

## Dependencies Added

```json
{
  "dependencies": {
    "@radix-ui/react-dialog": "^1.1.15",
    "@radix-ui/react-progress": "^1.1.8",
    "sonner": "^2.0.7"
  }
}
```

## File Structure

```
skillmeat/web/
├── components/
│   ├── collection/
│   │   ├── artifact-detail.tsx (updated)
│   │   ├── conflict-resolver.tsx (new)
│   │   ├── deploy-dialog.tsx (new)
│   │   ├── progress-indicator.tsx (new)
│   │   └── sync-dialog.tsx (new)
│   ├── ui/
│   │   ├── dialog.tsx (new)
│   │   ├── progress.tsx (new)
│   │   └── toaster.tsx (new)
│   └── providers.tsx (updated)
├── hooks/
│   ├── useDeploy.ts (new)
│   ├── useSSE.ts (new)
│   └── useSync.ts (new)
└── DEPLOY_SYNC_UI_IMPLEMENTATION.md (new)
```

## Acceptance Criteria Status

- [x] Deploy button/action in artifact detail view
- [x] Sync button/action for checking upstream updates
- [x] SSE progress indicators during operations
  - [x] Connection status
  - [x] Progress percentage
  - [x] Step-by-step updates
  - [x] Completion status
- [x] Conflict resolution modals for deploy/sync conflicts
- [x] Deployment target selection (project selection)
- [x] Sync options (force, merge strategies)
- [x] Success/error notifications
- [ ] Operation history/log viewer (deferred to future phase)
- [x] Cancel operation capability (via dialog close)

## Next Steps

1. **Backend Implementation**:
   - Implement POST /api/v1/deploy endpoint
   - Implement GET /api/v1/deploy/{id}/stream SSE endpoint
   - Implement POST /api/v1/sync endpoint
   - Implement GET /api/v1/sync/{id}/stream SSE endpoint

2. **Testing**:
   - End-to-end testing with real backend
   - Performance testing for SSE streams
   - Error scenario testing

3. **Enhancements**:
   - Operation history viewer
   - Batch deploy/sync operations
   - Advanced conflict resolution (3-way merge)
   - Deployment presets/templates

## Architecture Decisions

1. **SSE over WebSockets**: Chosen for simplicity and one-way communication pattern
2. **Separate dialogs**: Deploy and Sync in separate components for clarity
3. **Mock data**: Allows frontend development without backend dependency
4. **Toast notifications**: Using Sonner for better UX and accessibility
5. **React Query**: For state management and cache invalidation
6. **Optimistic updates**: UI updates immediately, syncs in background

## Known Limitations

1. SSE streams require HTTP/2 or connection pooling
2. No progress persistence across page refreshes
3. No multi-artifact batch operations (yet)
4. No manual conflict resolution editor (yet)
5. Backend endpoints not yet implemented (using mocks)

## Performance Considerations

1. SSE connections automatically close after completion
2. Automatic reconnection limited to 5 attempts
3. Message buffering limited to prevent memory issues
4. React Query cache prevents redundant fetches
5. Optimistic updates for instant feedback
