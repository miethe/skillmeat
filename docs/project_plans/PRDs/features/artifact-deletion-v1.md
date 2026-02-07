---
title: 'PRD: Artifact Deletion from Collections and Projects'
description: Complete artifact deletion workflow with multi-level cascading deletion
  from collections and projects through the web UI with context-aware dialogs
audience:
- ai-agents
- developers
tags:
- prd
- planning
- feature
- web-ui
- artifact-lifecycle
- deletion
- crud
created: 2025-12-20
updated: '2026-02-07'
category: product-planning
status: completed
related:
- /docs/project_plans/PRDs/features/entity-lifecycle-management-v1.md
- /.claude/rules/web/api-client.md
- /.claude/rules/web/hooks.md
---

# PRD: Artifact Deletion from Collections and Projects

**Feature Name:** Artifact Deletion from Collections and Projects

**Filepath Name:** `artifact-deletion-v1`

**Date:** 2025-12-20

**Author:** Claude Code (AI Agent)

**Version:** 1.0

**Status:** Draft

**Related Documents:**
- Entity Lifecycle Management PRD
- Web Frontend API Client Conventions (`.claude/rules/web/api-client.md`)
- Web Frontend Hooks Patterns (`.claude/rules/web/hooks.md`)

---

## 1. Executive Summary

The Artifact Deletion feature enables users to delete artifacts from collections and projects through the web UI with a sophisticated multi-step confirmation dialog. Users can selectively delete from one or both levels (collection and projects), with cascading deletion options for deployments, providing clear visual distinction for destructive actions while maintaining data integrity.

**Priority:** HIGH

**Key Outcomes:**
- Users can delete artifacts from collections via "..." menu or modal
- Users can delete artifacts from specific projects with optional collection-level deletion
- Multi-step confirmation dialog with toggles for cascading deletions
- Visual RED warnings for dangerous "Delete Deployments" option
- Selective project/deployment selection before destructive operations
- Proper cache invalidation after all deletion types
- Clear error handling with partial failure support

---

## 2. Context & Background

### Current State

**What Exists Today:**

1. **Deletion Components (Partial):**
   - `EntityActions` component (`components/entity/entity-actions.tsx`) - Has Delete option with simple confirmation dialog
   - `DeleteSourceDialog` (`components/marketplace/delete-source-dialog.tsx`) - Example of CASCADE warning pattern
   - Simple delete confirmation: artifact name + "cannot be undone" message

2. **Backend Deletion APIs (Fully Implemented):**
   - `DELETE /api/v1/artifacts/{artifact_id}` - Deletes artifact from collection
   - `POST /api/v1/deploy/undeploy` - Removes deployed artifact from specific project
   - Both endpoints are production-ready with proper error handling

3. **Frontend Components Ready for Integration:**
   - `UnifiedCard` - Displays artifacts with "..." menu via EntityActions
   - `UnifiedEntityModal` - Overview tab has space for new Delete button
   - `useDeploymentList` hook - Lists deployments for artifact
   - `useArtifacts` hook - Manages artifact queries and cache

4. **API Client Integration Points:**
   - `lib/api/collections.ts` - Collection-level artifact deletion
   - `lib/api/deployments.ts` - Deployment undeploy operations
   - Consistent error handling pattern with `ApiError` class

5. **Cache Keys Available:**
   - Collection artifact lists use TanStack Query
   - Deployment lists cached separately
   - Project artifact counts available

**Key Files/Components:**
- `skillmeat/web/components/entity/entity-actions.tsx` - Current simple delete
- `skillmeat/web/components/shared/unified-card.tsx` - Card component with actions
- `skillmeat/web/hooks/useArtifacts.ts` - Artifact management hook
- `skillmeat/web/hooks/use-deployments.ts` - Deployment listing
- `skillmeat/api/routers/artifacts.py` - Backend artifact router
- `skillmeat/api/routers/deployments.py` - Backend deployment router

### Problem Space

**Pain Points:**

1. **No Collection-Level Deletion**
   - Artifacts cannot be deleted from collections through web UI
   - Users must use CLI or manually delete files
   - No visual feedback or confirmation workflow

2. **No Project-Level Deletion**
   - Users cannot remove deployed artifacts from specific projects
   - Artifacts accumulate in projects, cluttering `.claude/` directories
   - No way to clean up deployments except manual file deletion

3. **No Cascading Deletion Options**
   - Users cannot delete from both collection and projects in one operation
   - Must navigate between multiple dialogs and pages
   - Error-prone if deletions fail partway through

4. **Inadequate Confirmation UX**
   - Current simple dialog doesn't show scope of deletion
   - No indication of deployment count or affected projects
   - Users might accidentally delete from more places than intended
   - "Delete Deployments" (filesystem deletion) not visually distinguished as dangerous

5. **Dangerous Operations Not Clearly Marked**
   - Deployment deletion (removing actual files) looks same as removal from tracking
   - No RED visual warning for actual filesystem operations
   - No confirmation of which deployments will be physically deleted

### Current Alternatives / Workarounds

**CLI-Only Operations:**
- Users must use `skillmeat` CLI to delete artifacts
- No visual feedback in web UI
- CLI commands: `skillmeat delete <artifact>` (planned/partial)

**Manual File Deletion:**
- Edit `.claude/manifest.toml` directly
- Manually delete artifact directories from `.claude/` folders
- Requires filesystem access and understanding of structure

**No Workaround Available:**
- Cannot delete from collection and projects atomically
- Cannot selectively delete from only projects
- Cannot see which projects will be affected before deletion
- Cannot get clear visual distinction for destructive operations

### Architectural Context

**Current Deletion Model (Simple):**
```
Delete button → Simple confirmation → API call → Done
```

**Proposed Deletion Model (Enhanced):**
```
Delete button
  → Confirmation dialog (primary)
    ├── Delete from [context]?
    ├── Toggle: "Also delete from [opposite level]"
    └── Toggle: "Delete Deployments" (RED, conditional)
      → If toggled, shows expanded section
        ├── List of affected projects/deployments
        └── Checkboxes for selective deletion
  → Multiple API calls (orchestrated)
    ├── Collection deletion (if selected)
    ├── Project undeploy calls (if selected)
    └── Cache invalidation for all affected scopes
```

**Backend API Contract (Already Exists):**

| Operation | Endpoint | Method | Request | Response | Status |
|-----------|----------|--------|---------|----------|--------|
| Delete artifact from collection | `/api/v1/artifacts/{artifact_id}` | DELETE | - | `{success: bool, message: str}` | ✅ Implemented |
| List deployments | `/api/v1/deploy` | GET | Optional: `project_path` | `DeploymentListResponse` | ✅ Implemented |
| Undeploy from project | `/api/v1/deploy/undeploy` | POST | `UndeployRequest` | `UndeployResponse` | ✅ Implemented |

**Request/Response Schemas:**

```typescript
// UndeployRequest (from types/deployments.ts)
interface ArtifactUndeployRequest {
  artifact_name: string;      // e.g., "pdf-skill"
  artifact_type: string;      // e.g., "skill"
  project_path?: string;      // Optional, uses CWD if not specified
}

// UndeployResponse
interface ArtifactUndeployResponse {
  success: boolean;
  message: string;
  artifact_name: string;
  artifact_type: string;
  project_path: string;
}

// DeploymentListResponse
interface ArtifactDeploymentListResponse {
  project_path: string;
  deployments: ArtifactDeploymentInfo[];
  total: number;
}

// ArtifactDeploymentInfo
interface ArtifactDeploymentInfo {
  artifact_name: string;
  artifact_type: string;
  from_collection: string;
  deployed_at: string;
  artifact_path: string;      // Relative path in .claude/
  collection_sha: string;
  local_modifications: boolean;
  sync_status?: 'synced' | 'modified' | 'outdated';
}
```

**Frontend State Management:**
- TanStack React Query for server state
- Hooks pattern for API integration
- Cache keys for artifact lists and deployment lists
- Collection invalidation strategy

---

## 3. Problem Statement

**Core Gap:** Users cannot efficiently delete artifacts from collections or projects through the web UI, and cannot perform cascading deletions across both levels, forcing them to use CLI commands or manual file editing while lacking visibility into deletion scope.

**User Story Format:**

> "As a user managing my SkillMeat collection, when I have an artifact I no longer need, I should be able to delete it from the collection with a simple '...' menu action and confirmation dialog, but currently I have no way to do this through the web UI."

> "As a developer maintaining deployed artifacts in my project, when I want to remove a deployed artifact from my project's `.claude/` directory, I should be able to do this from the Projects page without deleting the collection version, but currently there's no UI for project-level deletion."

> "As a user cleaning up after testing, when I want to delete an artifact from everywhere it was deployed (collection + 5 projects), I need to confirm what I'm deleting and where, not just see a generic 'cannot be undone' message. I want to see which projects will be affected before confirming."

> "As a cautious user, when I delete deployments (which physically removes files), this should look visually different from just removing from tracking, with a clear RED warning so I don't accidentally delete actual project files."

> "As a developer with multiple deployments, when deleting an artifact, I want to choose which projects to delete from, not all-or-nothing deletion. I might want to keep it in one active project and remove from archived projects."

**Technical Root Causes:**

1. Delete functionality only exists in simple form in EntityActions
2. No UI for project-level (deployment) deletion
3. No cascading deletion UI - delete scope not configurable
4. No distinction between "remove from tracking" vs "delete actual files"
5. No selection UI for which projects/deployments to affect
6. Simple confirmation dialog doesn't show deployment impact

---

## 4. Feature Requirements

### 4.1 Scope & Constraints

**In Scope:**
- Delete artifacts from collections via web UI
- Delete artifacts from specific projects via web UI
- Multi-step confirmation with cascading deletion toggles
- Selective deletion: choose which projects/deployments to affect
- Visual RED warning for deployment (filesystem) deletion
- Proper cache invalidation
- Error handling for partial failures

**Out of Scope:**
- Undo/trash/recovery functionality (permanent deletion)
- Bulk selection and batch deletion
- Automatic backups before deletion
- Deletion scheduling or delayed deletion
- Deletion audit logs (can be future enhancement)

**Constraints:**
- Must use existing backend APIs (no new backend endpoints)
- Must maintain consistency with EntityActions pattern
- RED warnings only for actual filesystem operations (deployments)
- All deletion operations must invalidate appropriate caches
- Must handle network errors gracefully

### 4.2 User Interactions

#### 4.2.1 Entry Points

**1. Artifact Card "..." Menu (UnifiedCard)**

All artifact cards display a "..." button with dropdown menu:
- Location: Top-right corner of artifact card
- Component: `EntityActions`
- New Menu Item: **Delete** (RED text, warning icon, Trash2 icon)
- Behavior: Click opens Artifact Deletion Dialog

**2. Artifact Modal Overview Tab**

The Overview tab in `UnifiedEntityModal` gains a new Delete button:
- Location: Top-right corner, beside "Edit Parameters" button
- Button: `<Button variant="destructive">Delete</Button>`
- Icon: `Trash2`
- Behavior: Click opens Artifact Deletion Dialog

**3. Future Entry Point (Out of scope for Phase 1)**
- Bulk action menu when multiple artifacts selected
- Keyboard shortcut (Cmd/Ctrl + Delete)

#### 4.2.2 Artifact Deletion Dialog Flow

**Step 1: Primary Confirmation**

Dialog opens with:

```
┌─────────────────────────────────────┐
│  Delete [Artifact Name]?            │ [X]
├─────────────────────────────────────┤
│                                     │
│  Are you sure you want to delete    │
│  "canvas-design" from               │
│  [Collection/Project context]?      │
│                                     │
│  This action cannot be undone.      │
│                                     │
├─────────────────────────────────────┤
│                                     │
│  ☐ Also delete from                 │
│    [Opposite Level]                 │
│    (X deployments)                  │
│                                     │
│  ☐ Delete Deployments              │
│    ⚠ Removes from filesystem        │
│    (X projects)                     │
│                                     │
├─────────────────────────────────────┤
│           Cancel    Delete           │
└─────────────────────────────────────┘
```

**Content Requirements:**

| Element | Rules |
|---------|-------|
| Dialog Title | "Delete [artifact_name]?" |
| Context Line | Context-aware: "Delete from Collection '[name]'?" or "Delete from Project '[path]'?" |
| Warning Text | "This action cannot be undone." |
| Primary Toggle | "Also delete from [opposite level]" with deployment count |
| Deployment Toggle | "Delete Deployments" with RED styling + warning icon |
| Deployment Count | Show count only if artifact has deployments; "X projects" or "1 project" |
| Cancel Button | Standard outline style, always enabled |
| Delete Button | RED/destructive style, disabled only while operation in progress |

**Context-Aware Messaging:**

| Current Page | Message | Opposite Toggle Text |
|-------------|---------|---------------------|
| Collection page | "Delete from Collection '[name]'?" | "Also delete from Projects" |
| Project page | "Delete from Project '[path]'?" | "Also delete from Collection" |
| Modal (no context) | "Delete [artifact_name]?" | "Also delete from [Collection/Project]" |

**Step 2A: Expanded Projects Selection (If Collection Context)**

When user toggles "Also delete from Projects" while in Collection context:

Dialog expands to show:

```
┌─────────────────────────────────────┐
│  Delete [Artifact Name]?            │
├─────────────────────────────────────┤
│                                     │
│  Are you sure you want to delete    │
│  "canvas-design" from               │
│  Collection '[name]'?               │
│                                     │
│  ☑ Also delete from Projects        │
│    (5 projects)                     │
│                                     │
│  Select which projects:             │
│    ☑ /home/user/project-a          │
│    ☑ /home/user/project-b          │
│    ☐ /home/user/project-archived   │
│    ☑ /work/ml-pipeline             │
│    ☑ /dev/experimental             │
│                                     │
│  ☐ Delete Deployments              │
│    ⚠ Removes from filesystem        │
│                                     │
├─────────────────────────────────────┤
│           Cancel    Delete           │
└─────────────────────────────────────┘
```

**Behavior:**
- All projects checked by default
- User can uncheck to exclude specific projects
- "Select which projects:" label shows
- Project list scrollable if > 5 projects
- Count updates dynamically: "Also delete from Projects (3 of 5 selected)"

**Step 2B: Expanded Deployments Confirmation (If Deployment Toggle)**

When user toggles "Delete Deployments":

Dialog expands to show:

```
┌──────────────────────────────────────┐
│  Delete [Artifact Name]?             │
├──────────────────────────────────────┤
│                                      │
│  Are you sure you want to delete     │
│  "canvas-design" from Collection?    │
│                                      │
│  ☑ Also delete from Projects         │
│  ☑ Delete Deployments                │
│    ⚠ WARNING: This removes actual    │
│      files from your filesystem!     │
│                                      │
│  Deployments to delete:              │
│    ☑ /home/user/project-a           │
│        artifacts/skills/             │
│        canvas-design/                │
│    ☑ /home/user/project-b           │
│        artifacts/skills/             │
│        canvas-design/                │
│                                      │
│  This action cannot be undone!       │
│                                      │
├──────────────────────────────────────┤
│            Cancel    Delete           │
└──────────────────────────────────────┘
```

**Styling (RED Theme):**
- "Delete Deployments" label: RED text
- Toggle background: RED/destructive variant
- Warning icon: AlertTriangle (RED)
- WARNING text: RED, bold, uppercase
- "Deployments to delete:" label: RED, bold
- Deployment paths: Display in monospace font

**Behavior:**
- All deployments checked by default
- User can uncheck to exclude specific deployments
- Warning message always visible when section expanded
- Deployment list shows full path for clarity
- Count reflects selections: "3 of 5 deployments selected"

**Step 3: Orchestrated Deletion**

On "Delete" button click, execute operations in order:

1. **Batch 1 (Parallel if no dependency):**
   - If "Delete from Collection" → Call `deleteArtifactFromCollection(artifact_id)`
   - If "Also delete from Projects" → Call `undeployFromProject(project_path)` for EACH selected project

2. **Cache Invalidation (Sequential after deletions):**
   - Invalidate artifact list cache
   - Invalidate deployment list cache
   - Invalidate collection artifact count
   - Invalidate project deployment counts

3. **Success/Error State:**
   - Show toast notification (success or error)
   - Close dialog on success
   - Show error message if partial/total failure
   - Keep dialog open if errors, allow retry

**Loading State:**
- Delete button shows spinner: `<Loader2 className="mr-2 h-4 w-4 animate-spin" />`
- Button text: "Deleting..."
- All buttons disabled during operation
- Dialog not closable with X while deleting

### 4.3 Detailed Specifications

#### 4.3.1 Component: ArtifactDeletionDialog

**New Component Location:** `skillmeat/web/components/entity/artifact-deletion-dialog.tsx`

**Props Interface:**

```typescript
export interface ArtifactDeletionDialogProps {
  // Display and control
  artifact: Artifact;
  open: boolean;
  onOpenChange: (open: boolean) => void;

  // Context determines initial UI state
  context?: 'collection' | 'project';  // Where dialog opened from
  projectPath?: string;  // If context='project', the project path
  collectionId?: string;  // If context='collection', collection ID

  // Callbacks
  onSuccess?: () => void;  // After successful deletion
  onError?: (error: Error) => void;  // On error
}
```

**State Management:**

```typescript
const [step, setStep] = useState<'primary' | 'projects' | 'deployments'>('primary');
const [deleteFromCollection, setDeleteFromCollection] = useState(context === 'collection');
const [deleteFromProjects, setDeleteFromProjects] = useState(false);
const [deleteDeployments, setDeleteDeployments] = useState(false);
const [selectedProjects, setSelectedProjects] = useState<Set<string>>(
  deployments?.map(d => d.project_path) ?? []
);
const [selectedDeployments, setSelectedDeployments] = useState<Set<string>>(
  deployments?.map(d => d.artifact_name) ?? []
);
const [isDeleting, setIsDeleting] = useState(false);
const [error, setError] = useState<string | null>(null);
```

**Rendering:**

- Primary step: Title, context message, warning, toggles
- When "Also delete from [opposite]" checked:
  - Show project/collection list if necessary
  - Allow selection toggles
- When "Delete Deployments" checked:
  - Show RED warning banner
  - Show deployment list with paths
  - RED styling on toggle and warning text

**Dialog Heights:**
- Primary (no expansions): ~300px
- With project list (5 projects): ~500px
- With deployment list: ~600px
- Scrollable if content exceeds viewport

#### 4.3.2 Hook: useArtifactDeletion

**New Hook Location:** `skillmeat/web/hooks/use-artifact-deletion.ts`

**Interface:**

```typescript
export function useArtifactDeletion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: DeletionParams): Promise<DeletionResult> => {
      // Orchestrate multiple API calls based on deletion scope
      // Return result with success/failure per operation
    },
    onSuccess: (result) => {
      // Invalidate all affected caches
      queryClient.invalidateQueries({ queryKey: artifactKeys.all });
      queryClient.invalidateQueries({ queryKey: deploymentKeys.all });
    },
    onError: (error) => {
      // Error handling delegated to component
    },
  });
}

interface DeletionParams {
  artifact: Artifact;
  deleteFromCollection: boolean;
  deleteFromProjects: boolean;
  deleteDeployments: boolean;
  selectedProjectPaths: string[];  // Projects to undeploy from
  selectedDeploymentIds: string[];  // Specific deployments to delete
}

interface DeletionResult {
  collectionDeleted: boolean;
  projectsUndeployed: number;
  deploymentsDeleted: number;
  errors: Array<{ operation: string; error: string }>;
}
```

**Implementation Strategy:**

```typescript
// 1. Delete from collection (if selected)
if (params.deleteFromCollection) {
  await deleteArtifactFromCollection(artifact_id);
}

// 2. Undeploy from projects (if selected) - PARALLEL
const undeployPromises = params.selectedProjectPaths.map(projectPath =>
  undeployArtifact({
    artifact_name: artifact.name,
    artifact_type: artifact.type,
    project_path: projectPath,
  })
);
await Promise.allSettled(undeployPromises);

// 3. Cache invalidation
queryClient.invalidateQueries({ queryKey: ['artifacts'] });
queryClient.invalidateQueries({ queryKey: ['deployments'] });
```

**Error Handling:**
- Use `Promise.allSettled` for project undeployments (don't fail on first error)
- Collect all errors and report
- Return partial success info
- Allow user to retry with different selections

#### 4.3.3 API Integration

**API Client Updates:** `skillmeat/web/lib/api/artifacts.ts`

```typescript
/**
 * Delete artifact from collection
 */
export async function deleteArtifactFromCollection(
  artifactId: string
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(buildUrl(`/artifacts/${artifactId}`), {
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to delete artifact: ${response.statusText}`);
  }
  return response.json();
}
```

**Existing API to Reuse:** `lib/api/deployments.ts`

```typescript
// Already exists, just reuse
export async function undeployArtifact(
  data: ArtifactUndeployRequest
): Promise<ArtifactUndeployResponse> { ... }
```

#### 4.3.4 Cache Invalidation Strategy

**Query Keys to Invalidate:**

```typescript
// Artifact lists (broad scope for collection deletion)
queryClient.invalidateQueries({
  queryKey: ['artifacts', { scope: 'collection' }]
});

// Deployment lists (for project deletions)
queryClient.invalidateQueries({
  queryKey: ['deployments']
});

// Collection artifact counts (for UI badges)
queryClient.invalidateQueries({
  queryKey: ['collections']
});

// Project details (deployment counts)
queryClient.invalidateQueries({
  queryKey: ['projects']
});
```

**Timing:**
- Cache invalidation AFTER all deletion API calls complete
- Use `onSuccess` callback in mutation hook
- Invalidate broadly to ensure UI consistency

### 4.4 UI/UX Requirements

#### 4.4.1 Visual Hierarchy

| Element | Style | Purpose |
|---------|-------|---------|
| Dialog Title | Bold, 16pt | Primary action confirmation |
| Context Message | Regular, 14pt | Shows scope clearly |
| Warning Text | Orange/yellow, 12pt | Non-destructive operation warning |
| RED Elements | RED (#dc2626), bold | Dangerous (filesystem) operations |
| Toggles | Checkbox UI | Enable/disable cascading deletions |
| Buttons | Standard dialog buttons | Standard interaction pattern |

#### 4.4.2 Accessibility

- Dialog modal with proper focus management
- Labels for all toggles and checkboxes
- Warning text has proper color contrast (RED should meet WCAG AA)
- Keyboard navigation: Tab through toggles/checkboxes, Enter to confirm
- `aria-label` on warning icon
- Screen reader: "Warning: Deletes actual filesystem files"
- Focus trap within dialog

#### 4.4.3 Responsive Design

- Dialog max-width: 500px (desktop), 90vw (mobile)
- Scrollable content area if list > 400px
- Touch-friendly toggle sizes: 44px min
- Mobile-optimized expanded sections (stacked, not side-by-side)

#### 4.4.4 Loading & Error States

**Loading State:**
- Delete button shows spinner
- All form controls disabled
- Dialog cannot be closed with X
- Tooltip on spinner: "Deleting artifact..."

**Error State:**
- Error message displayed in dialog
- Details of which operations failed (collection vs projects)
- Suggestion to retry or cancel
- Delete button re-enabled to retry

**Success State:**
- Toast notification: "Successfully deleted [artifact_name]"
- Dialog closes automatically
- Caller redirected if necessary (e.g., back to collection list)

### 4.5 Integration Points

#### 4.5.1 EntityActions Component Enhancement

Current `EntityActions` delete option needs update:

```typescript
// Current simple delete
<DropdownMenuItem onClick={() => setShowDeleteDialog(true)}>
  <Trash2 className="mr-2 h-4 w-4" />
  Delete
</DropdownMenuItem>

// New: Replace with ArtifactDeletionDialog
export function EntityActions({ entity, onDelete, context, ... }) {
  const [showDeletionDialog, setShowDeletionDialog] = useState(false);

  return (
    <>
      <DropdownMenuItem onClick={() => setShowDeletionDialog(true)}>
        <Trash2 className="mr-2 h-4 w-4" />
        Delete
      </DropdownMenuItem>

      <ArtifactDeletionDialog
        artifact={entity}
        open={showDeletionDialog}
        onOpenChange={setShowDeletionDialog}
        context={context}  // 'collection' or 'project'
        projectPath={projectPath}
        onSuccess={() => onDelete?.()}  // Callback to parent for navigation
      />
    </>
  );
}
```

#### 4.5.2 UnifiedEntityModal Enhancement

Add Delete button to Overview tab header:

```typescript
// In modal header
<div className="flex gap-2">
  <Button variant="outline" onClick={openEditParametersDialog}>
    <Pencil className="mr-2 h-4 w-4" />
    Edit Parameters
  </Button>

  <Button variant="destructive" onClick={() => setShowDeletionDialog(true)}>
    <Trash2 className="mr-2 h-4 w-4" />
    Delete
  </Button>
</div>

<ArtifactDeletionDialog
  artifact={artifact}
  open={showDeletionDialog}
  onOpenChange={setShowDeletionDialog}
  onSuccess={() => closeModal()}  // Close modal after deletion
/>
```

#### 4.5.3 Query Client Configuration

Ensure proper cache behavior in `components/providers.tsx`:

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,  // 5 minutes
      retry: 1,
    },
  },
});
```

No changes needed - exists already.

#### 4.5.4 Project Context Integration

For project-level deletion, need to provide project path:

```typescript
// In project detail page
<EntityActions
  entity={artifact}
  context="project"
  projectPath={currentProject.path}
  onDelete={handleDelete}
/>
```

---

## 5. Technical Architecture

### 5.1 Component Hierarchy

```
UnifiedCard / UnifiedEntityModal
  └── EntityActions (enhanced)
      └── ArtifactDeletionDialog (new)
          ├── PrimaryConfirmation
          ├── ProjectsSelection (conditional)
          └── DeploymentsWarning (conditional)
```

### 5.2 Data Flow

```
User clicks Delete
  ↓
ArtifactDeletionDialog opens
  ↓
User configures deletion scope
  ├── deleteFromCollection: boolean
  ├── deleteFromProjects: boolean
  ├── deleteDeployments: boolean
  ├── selectedProjects: string[]
  └── selectedDeployments: string[]
  ↓
User clicks "Delete"
  ↓
useArtifactDeletion mutation triggered
  ↓
Orchestrate API calls (parallel where possible)
  ├── DELETE /api/v1/artifacts/{id} (if collection)
  └── POST /api/v1/deploy/undeploy (parallel for each project)
  ↓
Invalidate caches
  ├── Artifact lists
  ├── Deployment lists
  └── Project counts
  ↓
Show success toast
  ↓
Dialog closes
  ↓
Optional: Navigate away (collection list, etc)
```

### 5.3 State Management

**Component State (Local):**
- Dialog open/closed
- Which deletions are toggled
- Which projects/deployments selected
- Loading state
- Error message

**Server State (TanStack Query):**
- Artifact list
- Deployment list
- Project details
- Collection metadata

**No Redux/Zustand needed** - all state is local to dialog or server-managed.

### 5.4 Error Handling Strategy

**Error Types & Handling:**

| Error Type | Scenario | Handling |
|-----------|----------|----------|
| Collection delete fails | 404/403/500 | Show error, keep dialog open, offer retry |
| Single project undeploy fails | One of many fails | Show partial success, offer retry individual |
| All projects fail | All undeploy calls fail | Show "all projects failed", keep dialog, offer retry |
| Network timeout | Lost connection | Show timeout error, offer retry |
| Validation error | Invalid artifact | Show validation message, close dialog |

**Error Message Format:**
```
Failed to delete artifact:
- Collection deletion: [specific error]
- Project /path/a: [specific error]
- Project /path/b: [specific error]

Retry failed operations or close dialog.
```

**Toast Notifications:**
- Success: "Successfully deleted [artifact] from [scope]"
- Error: "Failed to delete [artifact]: [detail]"
- Partial: "Partially deleted [artifact]: [X of Y succeeded]"

### 5.5 Testing Strategy

**Unit Tests (Jest):**

1. **Dialog Component:**
   - Dialog opens with correct context message
   - Toggles update state correctly
   - Project list appears when "Also delete" toggled
   - Deployment list appears when "Delete Deployments" toggled
   - All checkboxes work independently
   - Delete button disabled during loading

2. **Hook (useArtifactDeletion):**
   - Calls deleteArtifactFromCollection when collection selected
   - Calls undeployArtifact for each selected project
   - Invalidates caches on success
   - Handles partial failures gracefully
   - Returns correct DeletionResult structure

3. **API Client:**
   - DELETE request to correct endpoint
   - Proper error handling and message extraction
   - JSON parsing and return type correct

**Integration Tests (Playwright):**

1. **Collection-level deletion:**
   - Click delete on artifact card
   - Confirm in dialog
   - Artifact removed from list
   - Deployment list updated

2. **Project-level deletion:**
   - Navigate to project
   - Click delete on deployed artifact
   - Confirm without collection deletion
   - Artifact removed from project only

3. **Cascading deletion:**
   - Toggle "Also delete from projects"
   - Select/deselect specific projects
   - Confirm
   - Both collection and projects updated

4. **Error handling:**
   - Delete fails with 500 error
   - Error message shown in dialog
   - Can retry

**Mock Data:**
- Sample artifacts with 0, 1, 5+ deployments
- Sample projects with various paths
- Mock API responses for success/errors

---

## 6. Implementation Plan

### 6.1 Phases

**Phase 1: Core Dialog & Hook** (Primary deliverable)

| Task | Effort | Assigned | Status |
|------|--------|----------|--------|
| Create ArtifactDeletionDialog component | 2h | ui-engineer-enhanced | - |
| Create useArtifactDeletion hook | 1.5h | ui-engineer-enhanced | - |
| Create deleteArtifactFromCollection API | 0.5h | ui-engineer-enhanced | - |
| Update EntityActions with new dialog | 1h | ui-engineer-enhanced | - |
| Write unit tests | 2h | ui-engineer-enhanced | - |
| Integration test & E2E | 1.5h | ui-engineer-enhanced | - |

**Subtotal Phase 1: ~8.5 hours**

**Phase 2: Modal Integration** (Secondary)

| Task | Effort | Assigned | Status |
|------|--------|----------|--------|
| Add Delete button to UnifiedEntityModal | 1h | ui-engineer-enhanced | - |
| Wire up modal context | 0.5h | ui-engineer-enhanced | - |
| Test modal deletion flow | 1h | ui-engineer-enhanced | - |

**Subtotal Phase 2: ~2.5 hours**

**Phase 3: Polish & Edge Cases** (Future)

- Error recovery flows
- Keyboard shortcut support (Cmd/Ctrl+Delete)
- Bulk selection preparation
- Analytics/telemetry

### 6.2 Dependencies

**External Dependencies:**
- None (all APIs exist)
- lucide-react icons (AlertTriangle, Loader2, Trash2) - already available
- shadcn Dialog/AlertDialog components - already available

**Internal Dependencies:**
- Artifact type definitions (`types/artifact.ts`)
- Deployment type definitions (`types/deployments.ts`)
- TanStack React Query (already configured)
- API client functions (exists in `lib/api/deployments.ts`)

**No Blockers:** All backend APIs are production-ready.

### 6.3 File Changes Summary

**New Files:**
- `skillmeat/web/components/entity/artifact-deletion-dialog.tsx` (350 LOC)
- `skillmeat/web/hooks/use-artifact-deletion.ts` (150 LOC)
- `skillmeat/web/lib/api/artifacts.ts` (50 LOC - new delete function)
- `skillmeat/web/__tests__/artifact-deletion-dialog.test.tsx` (300 LOC)
- `skillmeat/web/__tests__/use-artifact-deletion.test.tsx` (200 LOC)

**Modified Files:**
- `skillmeat/web/components/entity/entity-actions.tsx` (+40 LOC)
- `skillmeat/web/components/entity/unified-entity-modal.tsx` (+30 LOC)
- `skillmeat/web/lib/api/index.ts` (re-export new delete function)

**Total New Code:** ~1,100 LOC
**Total Modified:** ~70 LOC

---

## 7. Acceptance Criteria

### User-Facing Acceptance Criteria

| Criterion | How to Test | Status |
|-----------|------------|--------|
| User can delete artifact from collection via "..." menu | Click delete on card, confirm dialog, artifact removed | - |
| User can delete artifact from project without affecting collection | Navigate to project, delete deployed artifact, collection still has artifact | - |
| User can delete from both collection and projects in one operation | Click delete, toggle "Also delete from Projects", select all, confirm | - |
| User can selectively choose which projects to delete from | Toggle "Also delete", uncheck some projects, confirm, those projects unaffected | - |
| "Delete Deployments" option is visually distinct (RED) | Look at dialog, deployments section has RED styling | - |
| User can see which deployments will be deleted | Toggle "Delete Deployments", list of deployments shown with paths | - |
| Artifact list updates after deletion | After deletion, artifact not in list | - |
| Deployment list updates after project deletion | After undeploy, artifact not in project's deployment list | - |
| Error message shown if deletion fails | Mock API failure, error displayed in dialog | - |
| Dialog has proper keyboard navigation | Use Tab/Enter to navigate and confirm | - |

### Technical Acceptance Criteria

| Criterion | How to Test | Status |
|-----------|------------|--------|
| API calls use correct endpoints | Network tab shows DELETE /api/v1/artifacts/... and POST /api/v1/deploy/undeploy | - |
| Cache invalidation works | After deletion, new data fetched (not stale) | - |
| Partial failures handled gracefully | Mock failure on project 2 of 3, dialog shows partial success | - |
| Dialog is accessible (WCAG AA) | Run axe-core audit, no violations | - |
| TypeScript types correct | No `any` types, strict mode enabled | - |
| Unit tests pass | `jest` runs all tests, 100% pass | - |
| Integration tests pass | Playwright E2E tests pass | - |
| Error boundary catches errors | Component errors don't crash app | - |

---

## 8. Risk Assessment

### High-Risk Areas

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Partial failure (some projects deleted, some not) | User confused about deletion state | Clear error message listing what succeeded/failed, allow retry |
| User accidentally confirms full deletion | Data loss | Multi-step confirmation, RED visual warnings, toast confirmation |
| Cache invalidation too broad | Performance degradation | Targeted cache keys, use query key factories |
| Network error mid-operation | Inconsistent state | Use Promise.allSettled, allow retry, show partial results |
| Race conditions with concurrent operations | Artifact deleted by another user/tab | Implement optimistic update, show stale warning if detected |

### Medium-Risk Areas

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Long list of projects (100+) | Dialog performance degrades | Virtualize project list, paginate if needed |
| Sensitive deployments in project list | User deletes wrong project | Show full path, highlight "production" projects differently |
| Undeploy API returns success but files remain | Inconsistent state | Log warning, suggest manual cleanup, link to support docs |

### Low-Risk Areas

- Dialog UI complexity - uses standard shadcn components
- TypeScript type safety - strong typing throughout
- API contract stability - APIs are already production

---

## 9. Success Metrics

### Quantitative Metrics

- **Deletion Success Rate:** 95%+ of deletion operations complete without error
- **Average Time to Delete:** < 3 seconds (from click to completion)
- **Error Recovery Rate:** 80%+ of errors resolved on first retry
- **Cache Hit Rate After Deletion:** 100% (no stale data shown)

### Qualitative Metrics

- **User Satisfaction:** Users report clear understanding of what will be deleted
- **Reduced Support Burden:** No questions about "how do I delete an artifact"
- **Intuitive UX:** Toggles and selections feel natural (no user confusion about state)

### Metrics to Track

- Number of deletion operations per user per month
- Deletion success/failure rate
- Average number of projects deleted per operation
- Time from artifact selection to confirmation
- Error rates by error type

---

## 10. Dependencies & Assumptions

### Assumptions

| Assumption | Validation | Risk if False |
|-----------|-----------|--------------|
| Backend DELETE endpoint for artifacts works reliably | Run API tests | Must implement error recovery |
| Undeploy API is idempotent (can call multiple times safely) | Test with same artifact twice | Might need API changes |
| Project paths are stable and unique | Verify in existing code | Deletion might affect wrong project |
| TanStack Query cache invalidation works as expected | Unit test cache patterns | Stale data might be shown |
| Users understand difference between collection and project | User research | Might need better terminology |

### Dependencies

**Hard Dependencies:**
- Backend APIs: `DELETE /artifacts/{id}`, `POST /deploy/undeploy`
- TanStack React Query v5+
- shadcn Dialog/AlertDialog components
- lucide-react icons

**Soft Dependencies:**
- EntityActions component pattern
- Artifact and Deployment type definitions
- API client patterns from `lib/api/`

### Known Limitations

1. **No Undo/Recovery:** Deletion is permanent (as designed)
2. **No Bulk Deletion:** Single artifact at a time (can be future enhancement)
3. **No Deletion History:** No audit log of deletions (can be future enhancement)
4. **Deletion is Synchronous:** UI blocks during delete (acceptable for < 5 seconds)

---

## 11. Future Enhancements

**Phase 2+:**
- Bulk artifact selection and batch deletion
- Soft delete with recovery window (7 days)
- Deletion audit log with timestamps
- Keyboard shortcut (Cmd/Ctrl+Delete)
- Confirmation email for bulk deletions
- Deletion scheduled for specific time
- CLI `skillmeat delete` command enhanced
- Analytics: most-deleted artifacts, deletion patterns

---

## 12. Glossary & Terminology

| Term | Definition |
|------|-----------|
| **Collection** | User's global artifact library (instance-level) |
| **Project** | Individual codebase with `.claude/` directory |
| **Deployment** | Artifact copied from collection to project's `.claude/` |
| **Undeploy** | Remove deployment (remove from project tracking, optionally delete files) |
| **Cascading Deletion** | Delete from multiple levels (collection + projects) in one operation |
| **Scope** | Which level artifact is being deleted from (collection vs project) |
| **Artifact Name** | Human-readable identifier (e.g., "canvas-design") |
| **Artifact Type** | Category (skill, command, agent, mcp, hook) |

---

## 13. Appendix: Design References

### Dialog Pattern Reference

Based on `DeleteSourceDialog` (`components/marketplace/delete-source-dialog.tsx`):
- Use AlertDialog for destructive actions
- Show warning icon + message
- Clear consequences text
- RED styling for dangerous operations
- Loading state with spinner

### Component Pattern Reference

Based on `EntityActions` (`components/entity/entity-actions.tsx`):
- Dropdown menu with context-aware options
- Separate state for confirmation dialogs
- Loading state management
- Error handling with try/catch

### Hook Pattern Reference

Based on existing `useDeploy` hook:
- Use TanStack Query `useMutation`
- Invalidate specific cache keys on success
- Return result object with status
- Error handling delegated to component

---

**Document Version:** 1.0
**Last Updated:** 2025-12-20
**Prepared By:** Claude Code (AI Agent)
