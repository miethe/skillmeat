# Deployment Files - Quick Reference

Quick lookup table of all deployment-related files and their purposes.

---

## Frontend Components

| File | Type | Key Exports | Line Count | Purpose |
|------|------|-------------|-----------|---------|
| `skillmeat/web/components/collection/deploy-dialog.tsx` | React Component | `DeployDialog`, `DeployDialogProps` | 355 | Main deployment UI dialog with project selection |
| `skillmeat/web/components/collection/progress-indicator.tsx` | React Component | `ProgressIndicator`, `ProgressStep` | 225 | Real-time progress display with SSE listener |
| `skillmeat/web/components/deployments/deployment-card.tsx` | React Component | `DeploymentCard`, `DeploymentCardSkeleton` | N/A | Card view for single deployment |
| `skillmeat/web/components/deployments/deployment-actions.tsx` | React Component | `DeploymentActions` | N/A | Undeploy and sync action buttons |
| `skillmeat/web/components/entity/unified-entity-modal.tsx` | React Component | `UnifiedEntityModal` | 100+ | Contains deployments tab of entity details |
| `skillmeat/web/app/projects/components/create-project-dialog.tsx` | React Component | `CreateProjectDialog` | 100+ | New project creation dialog (integrated into deploy flow) |

---

## Frontend Hooks

| File | Type | Key Exports | Purpose |
|------|------|-------------|---------|
| `skillmeat/web/hooks/use-deployments.ts` | Custom Hook | `useDeployArtifact()`, `useUndeployArtifact()`, `useDeploymentList()`, `useDeploymentSummary()`, `useRefreshDeployments()`, `deploymentKeys` | TanStack Query hooks for deployment operations + cache key factory |
| `skillmeat/web/hooks/useSSE.ts` | Custom Hook | `useSSE()` | **STUB** - Server-Sent Events hook (NOT IMPLEMENTED) |
| `skillmeat/web/hooks/useProjects.ts` | Custom Hook | `useProjects()`, `useCreateProject()` | Project listing and creation |

---

## Frontend API Client

| File | Type | Key Exports | Purpose |
|------|------|-------------|---------|
| `skillmeat/web/lib/api/deployments.ts` | API Client | `deployArtifact()`, `undeployArtifact()`, `listDeployments()`, `getDeploymentSummary()`, `getDeployments()` | REST API client for deployment endpoints |

---

## Frontend Type Definitions

| File | Type | Purpose |
|------|------|---------|
| `skillmeat/web/types/deployments.ts` | TypeScript Types | `ArtifactDeployRequest`, `ArtifactDeploymentResponse`, `ArtifactDeploymentInfo`, etc. |

---

## Backend Router

| File | Type | Prefix | Endpoints | Purpose |
|------|------|--------|-----------|---------|
| `skillmeat/api/routers/deployments.py` | FastAPI Router | `/api/v1/deploy` | POST `/` (deploy), POST `/undeploy`, GET `/` (list) | Deployment REST API endpoints |

---

## Backend Schemas

| File | Type | Key Models | Purpose |
|------|------|-----------|---------|
| `skillmeat/api/schemas/deployments.py` | Pydantic Models | `DeployRequest`, `DeploymentResponse`, `DeploymentInfo`, `DeploymentListResponse`, `UndeployRequest`, `UndeployResponse` | Request/response validation and serialization |

---

## Backend Core Logic

| File | Type | Key Classes/Functions | Purpose |
|------|------|-----------|---------|
| `skillmeat/core/deployment.py` | Python Module | `DeploymentManager` (class), `Deployment` (dataclass) | Deployment orchestration and version tracking |
| `skillmeat/storage/deployment.py` | Python Module | `DeploymentTracker` (static methods) | TOML file I/O for deployment records |
| `skillmeat/core/mcp/deployment.py` | Python Module | MCP deployment handlers | **Separate from web deployment** |

---

## Test Files

| File | Type | Framework | Scope |
|------|------|-----------|-------|
| `tests/unit/test_deployment_model.py` | Unit Test | pytest | `Deployment` dataclass behavior |
| `tests/unit/test_deployment_manager.py` | Unit Test | pytest | `DeploymentManager` operations |
| `tests/unit/test_deployment_version_integration.py` | Unit Test | pytest | Version tracking integration |
| `tests/unit/test_deployment_tracker.py` | Unit Test | pytest | `DeploymentTracker` TOML I/O |
| `tests/integration/test_deployment_version_tracking.py` | Integration Test | pytest | End-to-end version tracking |
| `tests/integration/test_deployment_workflow.py` | Integration Test | pytest | Complete deployment workflow |
| `skillmeat/web/tests/deploy-sync.spec.ts` | E2E Test | Playwright | Deployment UI flow |

---

## Data Flow Summary

```
User opens DeployDialog
    ↓
useProjects() loads available projects
    ↓
User selects project + clicks Deploy
    ↓
useDeployArtifact().mutateAsync({
  artifact_name, artifact_type, project_path, overwrite
})
    ↓
fetch POST /api/v1/deploy
    ↓
[Backend] deploy_artifact() in routers/deployments.py
    ├─ DeploymentManager.deploy_artifacts()
    │   └─ DeploymentTracker.record_deployment()
    └─ Return DeploymentResponse (stream_url=null)
    ↓
[Frontend] onSuccess callback
    ├─ Invalidate deployment queries
    ├─ Show toast
    ├─ Close dialog (after 1.5s)
```

---

## Problem Areas

### Critical Issues

| Issue | File | Line(s) | Impact | Status |
|-------|------|---------|--------|--------|
| useSSE hook stub (not implemented) | `useSSE.ts` | 37-40 | No progress updates from SSE stream | **BLOCKER** |
| SSE endpoint not implemented | `routers/deployments.py` | 167 | No backend SSE endpoint for progress | **BLOCKER** |
| Overwrite checkbox missing from UI | `deploy-dialog.tsx` | 44, 300-316 | Users can't force overwrite | Minor |
| Project path validation | `deploy-dialog.tsx` | 116 | May send undefined if path empty | Minor |

---

## Dependency Map

### Deploy Dialog Dependencies
```
deploy-dialog.tsx
├─ useDeployArtifact() [use-deployments.ts]
├─ useProjects() [useProjects.ts]
├─ deployArtifact() [lib/api/deployments.ts]
├─ CreateProjectDialog [create-project-dialog.tsx]
└─ ProgressIndicator [progress-indicator.tsx]
    ├─ useSSE() [useSSE.ts] ❌ INCOMPLETE
    └─ onComplete callback → handleComplete()
```

### Backend Dependencies
```
deploy_artifact() [routers/deployments.py]
├─ DeploymentManager [core/deployment.py]
│   ├─ CollectionManager
│   └─ FilesystemManager
├─ DeploymentTracker [storage/deployment.py]
└─ ArtifactType enum
```

---

## Key Concepts

### Project Selection Logic
- **Modes**: Registered project OR custom path
- **Validation**: Project path must exist or be absolute
- **Deployment Check**: `isAlreadyDeployed()` prevents duplicate deployments to same project
- **Path Used**: `selectedProject.path` or `customPath` → sent as `project_path` parameter

### Overwrite Handling
- **Default**: `overwrite = false`
- **Check**: Backend queries `DeploymentTracker.get_deployment()` to see if already deployed
- **Conflict**: Returns 409 if exists and `overwrite = false`
- **Override**: If `overwrite = true`, calls `undeploy()` first, then deploys

### Progress Tracking (NOT YET IMPLEMENTED)
- **Design**: SSE stream from backend to frontend
- **Events**: `progress`, `complete`, `error_event`
- **Status**: `useSSE()` hook incomplete - never connects EventSource
- **Fallback**: Dialog closes after 1.5s timeout (blocks user if something goes wrong)

### Sync Status Values
- `synced`: Content matches collection version
- `modified`: Local modifications detected
- `outdated`: Collection version is newer
- `unknown`: Cannot determine status

---

## Configuration Constants

### Frontend
- API base URL: `process.env.NEXT_PUBLIC_API_URL` or `http://localhost:8080`
- API version: `process.env.NEXT_PUBLIC_API_VERSION` or `v1`
- Custom path mode selector value: `'__custom__'`
- Dialog close delay: 1.5 seconds after successful deployment
- Deployment cache stale time: 2 minutes

### Backend
- Deployment manifest file: `.claude/deployments.toml`
- Default project path: Current working directory (if not specified)
- Artifact type subdirectories: `skills/`, `commands/`, `agents/`, `mcp/`, `hooks/`

---

## Important Notes

1. **SSE is not implemented** - Real-time progress doesn't work
2. **Overwrite UI missing** - Users can't control this parameter visually
3. **Project selection validates path existence** - Can't deploy to non-existent projects
4. **Deployment is idempotent with overwrite flag** - Safe to re-run
5. **Cache invalidation is comprehensive** - All deployment queries refresh on success
6. **Project creation integrated** - Users can create projects within deployment flow
