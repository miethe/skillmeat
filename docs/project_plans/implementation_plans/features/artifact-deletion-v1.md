---
title: 'Implementation Plan: Artifact Deletion from Collections and Projects'
description: Phased implementation for artifact deletion UI with multi-step confirmation
  dialogs and cascading deletion from collections and projects
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- phases
- tasks
- web-ui
- deletion
- crud
created: 2025-12-20
updated: '2026-02-07'
category: product-planning
status: completed
related:
- /docs/project_plans/PRDs/features/artifact-deletion-v1.md
- /.claude/rules/web/api-client.md
- /.claude/rules/web/hooks.md
---

# Implementation Plan: Artifact Deletion from Collections and Projects

**Plan ID**: `IMPL-2025-12-20-ARTIFACT-DELETION`

**Date**: 2025-12-20

**Author**: Claude Code (Implementation Orchestrator)

**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/features/artifact-deletion-v1.md`
- **API Client Rules**: `/.claude/rules/web/api-client.md`
- **Hooks Patterns**: `/.claude/rules/web/hooks.md`

**Complexity**: Medium (M)

**Total Estimated Effort**: 11 story points

**Target Timeline**: 2-3 weeks

**Workflow Track**: Standard (Haiku + Sonnet agents with dependency mapping)

---

## Executive Summary

This implementation plan delivers the Artifact Deletion feature for the SkillMeat web application. The solution provides users with a sophisticated multi-step confirmation dialog enabling deletion of artifacts from collections and projects, with optional cascading deletions, RED visual warnings for dangerous operations, and selective project/deployment choice before execution. All backend APIs already exist and are production-ready; this plan focuses on frontend UI and orchestration logic.

**Key Outcomes**:
- ✅ Delete artifacts from collections via "..." menu
- ✅ Delete artifacts from projects without affecting collections
- ✅ Cascading deletion from both collection and projects in one operation
- ✅ Selective project/deployment choice before deletion
- ✅ Visual RED warnings for filesystem deletion operations
- ✅ Proper cache invalidation and error handling
- ✅ Full test coverage and accessibility compliance

---

## Architecture Overview

### Implementation Strategy

**Bottom-Up Component Assembly**:

1. **API Client Functions** → Wrap existing backend endpoints
2. **useArtifactDeletion Hook** → Orchestrate deletion operations
3. **ArtifactDeletionDialog Component** → Multi-step UI with toggles and selections
4. **Integration Points** → Wire into EntityActions and UnifiedEntityModal

**No Backend Changes Required**: All APIs (`DELETE /artifacts/{id}`, `POST /deploy/undeploy`) are already implemented and tested.

### Data Flow

```
User clicks Delete
  ↓
ArtifactDeletionDialog opens with context (collection or project)
  ↓
User configures deletion scope (toggles + selections):
  - deleteFromCollection: boolean
  - deleteFromProjects: boolean
  - deleteDeployments: boolean
  - selectedProjectPaths: string[]
  ↓
User clicks "Delete" button
  ↓
useArtifactDeletion mutation triggered
  ↓
Orchestrate parallel/sequential API calls:
  - DELETE /api/v1/artifacts/{id} (if collection deletion)
  - POST /api/v1/deploy/undeploy x N (for each project)
  ↓
Cache invalidation (TanStack Query)
  ↓
Toast notification (success/error)
  ↓
Dialog closes / component cleanup
```

### Parallel Work Opportunities

- **Phase 1**: Dialog component and hook can be built in parallel
- **Phase 1**: Unit tests can start immediately as code is written
- **Phase 2**: Both EntityActions and UnifiedEntityModal integration can proceed in parallel

---

## Phase Breakdown

### Phase 1: Core Dialog & Hook Implementation

**Duration**: 3-5 days

**Dependencies**: None (all backend APIs ready)

**Assigned Subagent(s)**: ui-engineer-enhanced (primary), codebase-explorer (pattern discovery)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| FE-001 | Create deleteArtifactFromCollection API | Add DELETE function to lib/api/artifacts.ts | Function calls DELETE /api/v1/artifacts/{id}, handles errors | 0.5 pts | ui-engineer-enhanced | None |
| FE-002 | Create useArtifactDeletion Hook | Build TanStack Query mutation hook | Mutate signature matches DeletionParams, returns DeletionResult, invalidates caches | 1.5 pts | ui-engineer-enhanced | FE-001 |
| FE-003 | Create ArtifactDeletionDialog Component | Build multi-step confirmation dialog | Renders primary step, project selection, deployment warnings; all toggles work | 2 pts | ui-engineer-enhanced | FE-002 |
| FE-004 | Add context-aware messaging | Update dialog to show correct scope based on context | Dialog title and message match collection/project context | 0.5 pts | ui-engineer-enhanced | FE-003 |
| FE-005 | Add RED styling for deployments | Implement RED visual warnings for "Delete Deployments" toggle | Toggle has RED background, warning text RED, AlertTriangle icon visible | 0.5 pts | ui-engineer-enhanced | FE-003 |
| FE-006 | Add loading/error states | Implement spinner, disabled buttons, error message display | Delete button shows spinner during operation, error message shown on failure | 0.75 pts | ui-engineer-enhanced | FE-003 |
| FE-007 | Add keyboard navigation | Ensure Tab/Enter work for all controls | All form controls accessible via Tab, Enter confirms dialog | 0.5 pts | ui-engineer-enhanced | FE-003 |
| FE-008 | Unit tests for hook | Write Jest tests for useArtifactDeletion | Tests cover collection deletion, project undeployment, cache invalidation, errors | 1.5 pts | ui-engineer-enhanced | FE-002 |
| FE-009 | Unit tests for dialog | Write Jest tests for component | Tests cover toggles, selections, state changes, button disabling, error handling | 1.75 pts | ui-engineer-enhanced | FE-003 |
| FE-010 | Accessibility audit | Run axe-core, verify WCAG AA compliance | No accessibility violations, proper aria-labels, color contrast OK | 0.5 pts | ui-engineer-enhanced | FE-003 |

**Phase 1 Subtotal**: 10 story points

**Phase 1 Quality Gates**:
- [ ] API function calls correct endpoint with proper error handling
- [ ] Hook mutation signature correct and cache invalidation works
- [ ] Dialog renders all required UI elements (toggles, buttons, messages)
- [ ] All state management working (toggles update selections, etc)
- [ ] Loading state shows spinner, error state shows message
- [ ] Unit tests pass with >90% coverage
- [ ] Accessibility audit shows 0 violations
- [ ] Component compiles without TypeScript errors

---

### Phase 2: Integration with Existing Components

**Duration**: 2-3 days

**Dependencies**: Phase 1 complete (dialog and hook tested)

**Assigned Subagent(s)**: ui-engineer-enhanced

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| FE-011 | Enhance EntityActions component | Replace simple delete with ArtifactDeletionDialog | Delete menu item opens dialog, context and projectPath passed correctly | 1 pt | ui-engineer-enhanced | FE-003 |
| FE-012 | Add Delete button to UnifiedEntityModal | Add destructive Delete button to Overview tab header | Button appears next to "Edit Parameters", opens dialog | 0.75 pts | ui-engineer-enhanced | FE-003 |
| FE-013 | Wire modal context | Pass artifact and context to dialog in modal | Modal deletion uses correct context for messaging | 0.25 pts | ui-engineer-enhanced | FE-012 |
| FE-014 | Integration tests | Write E2E tests for collection-level deletion | Delete artifact from card, confirm in dialog, artifact removed from list | 0.75 pts | ui-engineer-enhanced | FE-011 |
| FE-015 | Integration tests - project level | Test project-level deletion without collection deletion | Delete from project, artifact stays in collection | 0.75 pts | ui-engineer-enhanced | FE-011 |
| FE-016 | Integration tests - cascading | Test deletion from both collection and projects | Toggle "Also delete from Projects", confirm, both updated | 0.75 pts | ui-engineer-enhanced | FE-011 |
| FE-017 | Integration tests - error handling | Test error recovery flows | Mock API failure, verify error message and retry capability | 0.75 pts | ui-engineer-enhanced | FE-011 |

**Phase 2 Subtotal**: 5 story points

**Phase 2 Quality Gates**:
- [ ] EntityActions properly passes context to dialog
- [ ] UnifiedEntityModal Delete button visible and functional
- [ ] Dialog closes after successful deletion
- [ ] Artifact lists update immediately after deletion
- [ ] Deployment list updates after project deletion
- [ ] Error handling works, user can retry
- [ ] All integration tests pass
- [ ] No TypeScript errors in modified components

---

### Phase 3: Testing & Polish

**Duration**: 2-3 days

**Dependencies**: Phase 2 complete (integration verified)

**Assigned Subagent(s)**: ui-engineer-enhanced (test review), code-reviewer (final validation)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned To | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| FE-018 | Performance optimization | Check dialog rendering performance, optimize if needed | Dialog renders in <100ms, no memory leaks | 0.5 pts | ui-engineer-enhanced | FE-003 |
| FE-019 | Mobile responsiveness | Test on mobile viewports, adjust layout if needed | Dialog responsive on 320px-1920px viewports | 0.5 pts | ui-engineer-enhanced | FE-003 |
| FE-020 | Final accessibility pass | Run full axe-core audit on all pages with dialog | Zero violations, proper keyboard shortcuts documented | 0.5 pts | ui-engineer-enhanced | FE-010 |
| FE-021 | Documentation & code comments | Add JSDoc to all functions and components | All public APIs documented with examples | 0.5 pts | ui-engineer-enhanced | All FE tasks |
| FE-022 | Code review & merge | Final review and merge to main branch | Code reviewed by team, no blocking comments, merged to main | 0.5 pts | code-reviewer | All FE tasks |

**Phase 3 Subtotal**: 2.5 story points

**Phase 3 Quality Gates**:
- [ ] Performance benchmarks acceptable (<100ms dialog render)
- [ ] Mobile views functional and usable
- [ ] Accessibility audit shows 0 violations
- [ ] Code documented with comments and JSDoc
- [ ] Code review completed without blocking issues
- [ ] All tests passing
- [ ] No warnings in console or TypeScript

---

## Implementation Detail

### File Changes Summary

**New Files Created**:

1. **`skillmeat/web/components/entity/artifact-deletion-dialog.tsx`** (~350 LOC)
   - ArtifactDeletionDialog component with 3 UI states
   - State management for toggles and selections
   - Error handling and loading states

2. **`skillmeat/web/hooks/use-artifact-deletion.ts`** (~150 LOC)
   - useArtifactDeletion TanStack Query mutation
   - Orchestrates collection deletion and project undeployments
   - Cache invalidation logic

3. **`skillmeat/web/__tests__/artifact-deletion-dialog.test.tsx`** (~300 LOC)
   - Component rendering tests
   - Toggle and selection state tests
   - Error handling tests
   - Accessibility tests

4. **`skillmeat/web/__tests__/use-artifact-deletion.test.ts`** (~200 LOC)
   - Hook mutation function tests
   - Cache invalidation tests
   - Error recovery tests

**Modified Files**:

1. **`skillmeat/web/lib/api/artifacts.ts`** (+50 LOC)
   - Add `deleteArtifactFromCollection()` function
   - Export from index.ts

2. **`skillmeat/web/components/entity/entity-actions.tsx`** (+40 LOC)
   - Replace simple delete dialog with ArtifactDeletionDialog
   - Pass context and projectPath props
   - Wire onSuccess callback

3. **`skillmeat/web/components/entity/unified-entity-modal.tsx`** (+30 LOC)
   - Add Delete button to Overview tab header
   - Import and render ArtifactDeletionDialog
   - Pass artifact and context

4. **`skillmeat/web/lib/api/index.ts`** (+5 LOC)
   - Export new deleteArtifactFromCollection function

**Total New Code**: ~1,050 LOC

**Total Modified**: ~75 LOC

### Component Specifications

#### ArtifactDeletionDialog Component

**Location**: `skillmeat/web/components/entity/artifact-deletion-dialog.tsx`

**Props Interface**:

```typescript
export interface ArtifactDeletionDialogProps {
  artifact: Artifact;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context?: 'collection' | 'project';
  projectPath?: string;
  collectionId?: string;
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}
```

**State Management**:

```typescript
const [deleteFromCollection, setDeleteFromCollection] = useState(
  context === 'collection'
);
const [deleteFromProjects, setDeleteFromProjects] = useState(false);
const [deleteDeployments, setDeleteDeployments] = useState(false);
const [selectedProjectPaths, setSelectedProjectPaths] = useState<Set<string>>(
  new Set(deployments?.map(d => d.project_path) ?? [])
);
const [selectedDeploymentPaths, setSelectedDeploymentPaths] = useState<Set<string>>(
  new Set(deployments?.map(d => d.artifact_path) ?? [])
);
const [isDeleting, setIsDeleting] = useState(false);
const [error, setError] = useState<string | null>(null);
```

**Rendering Sections**:

1. **Primary Step** (always shown):
   - Dialog title: "Delete [artifact_name]?"
   - Context message (collection or project specific)
   - Warning: "This action cannot be undone."
   - Toggle: "Also delete from [opposite level]" with count
   - Toggle: "Delete Deployments" (RED styling) with count
   - Cancel and Delete buttons

2. **Projects Section** (conditional - shown if deleteFromProjects):
   - "Select which projects:" label
   - Checkbox list of projects with paths
   - All checked by default
   - Dynamic count: "X of Y selected"
   - Scrollable if > 5 projects

3. **Deployments Section** (conditional - shown if deleteDeployments):
   - RED warning banner: "WARNING: This removes actual files..."
   - "Deployments to delete:" label (RED)
   - Checkbox list with full paths
   - All checked by default
   - Dynamic count: "X of Y selected"

**Key Methods**:

```typescript
// Handle deletion execution
const handleDelete = async () => {
  setIsDeleting(true);
  setError(null);
  try {
    await deletionMutation.mutateAsync({
      artifact,
      deleteFromCollection,
      deleteFromProjects,
      deleteDeployments,
      selectedProjectPaths: Array.from(selectedProjectPaths),
      selectedDeploymentPaths: Array.from(selectedDeploymentPaths),
    });
    onSuccess?.();
    onOpenChange(false);
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Unknown error');
  } finally {
    setIsDeleting(false);
  }
};

// Handle toggle for "Also delete from [opposite]"
const toggleDeleteFromOpposite = (checked: boolean) => {
  setDeleteFromProjects(checked);
  if (!checked) {
    setDeleteDeployments(false);
  }
};

// Handle toggle for "Delete Deployments"
const toggleDeleteDeployments = (checked: boolean) => {
  setDeleteDeployments(checked);
};

// Handle project selection
const toggleProject = (projectPath: string) => {
  const newSelected = new Set(selectedProjectPaths);
  if (newSelected.has(projectPath)) {
    newSelected.delete(projectPath);
  } else {
    newSelected.add(projectPath);
  }
  setSelectedProjectPaths(newSelected);
};
```

#### useArtifactDeletion Hook

**Location**: `skillmeat/web/hooks/use-artifact-deletion.ts`

**Hook Function**:

```typescript
export function useArtifactDeletion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: DeletionParams): Promise<DeletionResult> => {
      const errors: Array<{ operation: string; error: string }> = [];
      let collectionDeleted = false;
      let projectsUndeployed = 0;

      try {
        // Step 1: Delete from collection if selected
        if (params.deleteFromCollection) {
          await deleteArtifactFromCollection(params.artifact.id);
          collectionDeleted = true;
        }

        // Step 2: Undeploy from projects (parallel with error handling)
        const undeployResults = await Promise.allSettled(
          params.selectedProjectPaths.map(projectPath =>
            undeployArtifact({
              artifact_name: params.artifact.name,
              artifact_type: params.artifact.type,
              project_path: projectPath,
            })
          )
        );

        // Count successes and collect failures
        undeployResults.forEach((result, index) => {
          if (result.status === 'fulfilled') {
            projectsUndeployed++;
          } else if (result.status === 'rejected') {
            errors.push({
              operation: `Project: ${params.selectedProjectPaths[index]}`,
              error: result.reason.message,
            });
          }
        });

        // If we have errors and nothing succeeded, throw
        if (errors.length > 0 && projectsUndeployed === 0 && !collectionDeleted) {
          throw new Error(
            `Deletion failed: ${errors.map(e => e.error).join(', ')}`
          );
        }

        return {
          collectionDeleted,
          projectsUndeployed,
          deploymentsDeleted: projectsUndeployed, // Each undeploy is one deployment
          errors,
        };
      } catch (error) {
        throw error instanceof Error ? error : new Error('Unknown error during deletion');
      }
    },
    onSuccess: () => {
      // Invalidate all affected caches
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

export interface DeletionParams {
  artifact: Artifact;
  deleteFromCollection: boolean;
  deleteFromProjects: boolean;
  deleteDeployments: boolean;
  selectedProjectPaths: string[];
  selectedDeploymentPaths: string[];
}

export interface DeletionResult {
  collectionDeleted: boolean;
  projectsUndeployed: number;
  deploymentsDeleted: number;
  errors: Array<{ operation: string; error: string }>;
}
```

### API Client Functions

**Location**: `skillmeat/web/lib/api/artifacts.ts`

New function to add:

```typescript
/**
 * Delete artifact from collection
 *
 * @param artifactId - ID of artifact to delete
 * @returns Success response with message
 * @throws Error if deletion fails
 */
export async function deleteArtifactFromCollection(
  artifactId: string
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(buildUrl(`/artifacts/${artifactId}`), {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to delete artifact: ${response.statusText}`
    );
  }

  return response.json();
}
```

Reuse existing function from deployments.ts:

```typescript
// Already exists - just import and use
export async function undeployArtifact(
  data: ArtifactUndeployRequest
): Promise<ArtifactUndeployResponse> {
  // Implementation in skillmeat/web/lib/api/deployments.ts
}
```

### Integration Points

#### EntityActions Component

**File**: `skillmeat/web/components/entity/entity-actions.tsx`

**Change**:

```typescript
// Add to component props
interface EntityActionsProps {
  entity: Entity;
  context?: 'collection' | 'project';
  projectPath?: string;
  onDelete?: () => void;
  // ... other existing props
}

// In component body
const [showDeletionDialog, setShowDeletionDialog] = useState(false);

// In dropdown menu - replace simple delete
<DropdownMenuItem onClick={() => setShowDeletionDialog(true)}>
  <Trash2 className="mr-2 h-4 w-4" />
  <span className="text-red-600">Delete</span>
</DropdownMenuItem>

// Add dialog after dropdown menu
<ArtifactDeletionDialog
  artifact={entity}
  open={showDeletionDialog}
  onOpenChange={setShowDeletionDialog}
  context={context}
  projectPath={projectPath}
  onSuccess={() => {
    onDelete?.();
    setShowDeletionDialog(false);
  }}
/>
```

#### UnifiedEntityModal Component

**File**: `skillmeat/web/components/entity/unified-entity-modal.tsx`

**Change**:

Add Delete button to Overview tab header (around line ~1326):

```typescript
// In modal header section
<div className="flex gap-2">
  <Button
    variant="outline"
    size="sm"
    onClick={openEditParametersDialog}
  >
    <Pencil className="mr-2 h-4 w-4" />
    Edit Parameters
  </Button>

  <Button
    variant="destructive"
    size="sm"
    onClick={() => setShowDeletionDialog(true)}
  >
    <Trash2 className="mr-2 h-4 w-4" />
    Delete
  </Button>
</div>

// Add state
const [showDeletionDialog, setShowDeletionDialog] = useState(false);

// Add dialog component after other dialogs
<ArtifactDeletionDialog
  artifact={artifact}
  open={showDeletionDialog}
  onOpenChange={setShowDeletionDialog}
  onSuccess={() => {
    closeModal();
  }}
/>
```

### Cache Invalidation Strategy

All cache invalidations handled in `useArtifactDeletion` hook's `onSuccess` callback:

```typescript
onSuccess: () => {
  // Broad invalidation to ensure UI consistency
  queryClient.invalidateQueries({ queryKey: ['artifacts'] });
  queryClient.invalidateQueries({ queryKey: ['deployments'] });
  queryClient.invalidateQueries({ queryKey: ['collections'] });
  queryClient.invalidateQueries({ queryKey: ['projects'] });
};
```

This approach ensures:
- Artifact lists refresh immediately
- Deployment counts update
- Collection metadata updates
- Project details refresh

---

## Orchestration & Task Sequencing

### Execution Strategy

**Track Selected**: Standard Track (Haiku + Sonnet agents)

**Parallelization Strategy**:

```
Phase 1: Sequential dependency chain
  ├─ FE-001: deleteArtifactFromCollection API (0.5h)
  │
  ├─ FE-002: useArtifactDeletion Hook (1.5h)
  │   └─ Depends on FE-001
  │
  └─ PARALLEL BATCH (FE-003, FE-008-010):
      ├─ FE-003: ArtifactDeletionDialog (2h)
      ├─ FE-004: Context-aware messaging (0.5h)
      ├─ FE-005: RED styling (0.5h)
      ├─ FE-006: Loading/error states (0.75h)
      ├─ FE-007: Keyboard navigation (0.5h)
      ├─ FE-008: Hook unit tests (1.5h)
      ├─ FE-009: Dialog unit tests (1.75h)
      └─ FE-010: Accessibility audit (0.5h)

      All depend on FE-002 and FE-003 respectively

Phase 2: Parallel integration tasks
  ├─ FE-011: EntityActions enhancement (1h)
  ├─ FE-012: UnifiedEntityModal integration (0.75h)
  ├─ FE-013: Modal context wiring (0.25h)
  ├─ FE-014: Collection deletion E2E (0.75h)
  ├─ FE-015: Project deletion E2E (0.75h)
  ├─ FE-016: Cascading deletion E2E (0.75h)
  └─ FE-017: Error handling E2E (0.75h)

  All depend on FE-003 + FE-002

Phase 3: Polish and finalization
  ├─ FE-018: Performance optimization (0.5h)
  ├─ FE-019: Mobile responsiveness (0.5h)
  ├─ FE-020: Final accessibility pass (0.5h)
  ├─ FE-021: Documentation (0.5h)
  └─ FE-022: Code review (0.5h)

  All depend on Phase 1 and 2 complete
```

### Orchestration Quick Reference

**Phase 1 - Initial Setup** (Day 1-2):

```bash
# Task FE-001: Create API client function
Task("ui-engineer-enhanced", "FE-001: Create deleteArtifactFromCollection
  Location: skillmeat/web/lib/api/artifacts.ts
  Function signature: deleteArtifactFromCollection(artifactId: string)
  Calls: DELETE /api/v1/artifacts/{artifactId}
  Error handling: Extract error detail, throw ApiError
  Return: { success: boolean; message: string }")

# Task FE-002: Create hook (parallel with dialog)
Task("ui-engineer-enhanced", "FE-002: Create useArtifactDeletion hook
  Location: skillmeat/web/hooks/use-artifact-deletion.ts
  Uses TanStack Query useMutation
  Mutation function takes DeletionParams, returns DeletionResult
  Orchestrates: DELETE artifact + parallel undeploy calls
  Cache invalidation: Invalidate artifacts, deployments, collections, projects
  Error handling: Use Promise.allSettled for project undeployments")
```

**Phase 1 - Dialog & Tests** (Day 2-3):

```bash
# Task FE-003: Create dialog component
Task("ui-engineer-enhanced", "FE-003: Create ArtifactDeletionDialog component
  Location: skillmeat/web/components/entity/artifact-deletion-dialog.tsx
  Props: ArtifactDeletionDialogProps interface with artifact, open, context, etc
  State: deleteFromCollection, deleteFromProjects, deleteDeployments, selectedProjects, isDeleting, error
  Rendering: Primary step, conditional projects section, conditional deployments section
  Styling: RED for deployments section, AlertTriangle icon, proper contrast
  Loading state: Spinner on Delete button, all buttons disabled
  Error state: Show error message, allow retry")

# Tasks FE-004-007 (Enhancement): Wire context, styling, states, navigation
Task("ui-engineer-enhanced", "FE-004-007: Dialog enhancements
  FE-004: Add context-aware messaging
  FE-005: Add RED styling for Delete Deployments section
  FE-006: Add loading/error state handling
  FE-007: Add keyboard navigation (Tab/Enter)")

# Tasks FE-008-010 (Tests & Accessibility): Testing
Task("ui-engineer-enhanced", "FE-008-010: Testing
  FE-008: Unit tests for useArtifactDeletion hook in __tests__/use-artifact-deletion.test.ts
  FE-009: Unit tests for ArtifactDeletionDialog in __tests__/artifact-deletion-dialog.test.tsx
  FE-010: Accessibility audit with axe-core, fix violations")
```

**Phase 2 - Integration** (Day 4-5):

```bash
# Task FE-011: Integrate with EntityActions
Task("ui-engineer-enhanced", "FE-011: Enhance EntityActions component
  File: skillmeat/web/components/entity/entity-actions.tsx
  Changes: Replace simple delete dialog with ArtifactDeletionDialog
  Props: Add context and projectPath parameters
  Delete menu item: Opens ArtifactDeletionDialog with context
  Callback: onSuccess closes dialog and calls parent onDelete")

# Task FE-012-013: Integrate with UnifiedEntityModal
Task("ui-engineer-enhanced", "FE-012-013: Add Delete button to UnifiedEntityModal
  File: skillmeat/web/components/entity/unified-entity-modal.tsx
  Location: Overview tab header, next to Edit Parameters button
  Button: variant=destructive, shows Trash2 icon
  State: Track showDeletionDialog state
  Dialog: Pass artifact, use default context (not collection or project specific)
  Callback: onSuccess closes modal")

# Tasks FE-014-017: Integration tests
Task("ui-engineer-enhanced", "FE-014-017: Integration and E2E tests
  FE-014: Collection-level deletion (card -> confirm -> artifact removed)
  FE-015: Project-level deletion (project page -> confirm -> artifact removed from project only)
  FE-016: Cascading deletion (toggle 'Also delete' -> select projects -> both updated)
  FE-017: Error handling (mock 500 error -> show message -> retry works)")
```

**Phase 3 - Polish** (Day 5-6):

```bash
# Task FE-018-022: Final polish
Task("ui-engineer-enhanced", "FE-018-021: Performance, responsive, docs
  FE-018: Performance check (<100ms render time)
  FE-019: Mobile responsive design (test 320px-1920px)
  FE-020: Final accessibility pass (zero violations)
  FE-021: Add JSDoc comments to all functions")

Task("code-reviewer", "FE-022: Final code review and merge
  Review all Phase 1-2 code
  Check for TypeScript errors, console warnings
  Verify all tests passing
  Merge to main branch")
```

---

## Testing Strategy

### Unit Tests

**Hook Tests** (`__tests__/use-artifact-deletion.test.ts`):

```typescript
describe('useArtifactDeletion', () => {
  // Mock setup
  beforeEach(() => {
    mockDeleteArtifactFromCollection = jest.fn();
    mockUndeployArtifact = jest.fn();
    mockQueryClient = {
      invalidateQueries: jest.fn(),
    };
  });

  // Test collection deletion only
  it('deletes artifact from collection only', async () => {
    const { result } = renderHook(() => useArtifactDeletion(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({
        artifact: mockArtifact,
        deleteFromCollection: true,
        deleteFromProjects: false,
        deleteDeployments: false,
        selectedProjectPaths: [],
        selectedDeploymentPaths: [],
      });
    });
    expect(mockDeleteArtifactFromCollection).toHaveBeenCalledWith(mockArtifact.id);
    expect(mockQueryClient.invalidateQueries).toHaveBeenCalledWith({
      queryKey: ['artifacts'],
    });
  });

  // Test project undeploy
  it('undeployments from selected projects', async () => {
    // Test logic
  });

  // Test partial failure
  it('handles partial failures gracefully', async () => {
    // Test Promise.allSettled behavior
  });

  // Test cache invalidation
  it('invalidates all relevant caches on success', async () => {
    // Verify all cache keys invalidated
  });

  // Test error handling
  it('throws error if all operations fail', async () => {
    // Test error case
  });
});
```

**Component Tests** (`__tests__/artifact-deletion-dialog.test.tsx`):

```typescript
describe('ArtifactDeletionDialog', () => {
  it('renders primary confirmation step', () => {
    const { getByText } = render(<ArtifactDeletionDialog {...props} open />);
    expect(getByText(`Delete ${artifact.name}?`)).toBeInTheDocument();
    expect(getByText('This action cannot be undone.')).toBeInTheDocument();
  });

  it('toggles "Also delete from Projects" option', async () => {
    const { getByRole } = render(<ArtifactDeletionDialog {...props} open />);
    const toggle = getByRole('checkbox', {
      name: /Also delete from Projects/i,
    });
    fireEvent.click(toggle);
    await waitFor(() => {
      expect(getByText(/Select which projects:/i)).toBeInTheDocument();
    });
  });

  it('shows project list when "Also delete" toggled', () => {
    // Test project rendering
  });

  it('toggles "Delete Deployments" with RED styling', () => {
    // Test RED styling applied
    // Test warning message shown
  });

  it('allows selective project deselection', () => {
    // Test checkboxes work independently
  });

  it('disables Delete button while deleting', async () => {
    const { getByRole } = render(<ArtifactDeletionDialog {...props} open />);
    const deleteBtn = getByRole('button', { name: /Delete/i });
    fireEvent.click(deleteBtn);
    expect(deleteBtn).toBeDisabled();
  });

  it('shows error message on failure', async () => {
    mockMutation.mutateAsync.mockRejectedValueOnce(
      new Error('Failed to delete')
    );
    // Render, click delete, verify error message shown
  });

  it('closes dialog on success', async () => {
    // Verify onOpenChange called with false
  });

  it('maintains proper focus management', () => {
    // Test keyboard navigation
  });
});
```

### Integration Tests

**Collection Deletion E2E** (`__tests__/e2e/artifact-deletion.e2e.ts`):

```typescript
test('can delete artifact from collection', async ({ page }) => {
  // 1. Navigate to collections page
  await page.goto('/collections/my-collection');

  // 2. Find artifact card
  const artifactCard = page.locator('[data-testid="artifact-card-canvas"]');

  // 3. Click delete menu item
  await artifactCard.locator('button:has-text("...")').click();
  await page.locator('text=Delete').click();

  // 4. Verify dialog opens
  await expect(
    page.locator('text=Delete canvas-design?')
  ).toBeVisible();

  // 5. Click Delete button
  await page.locator('button:has-text("Delete")').click();

  // 6. Verify deletion and dialog closes
  await expect(
    page.locator('[data-testid="artifact-card-canvas"]')
  ).not.toBeVisible();
  await expect(page.locator('text=Delete canvas-design?')).not.toBeVisible();
});
```

### Accessibility Tests

**axe-core Audit**:

```typescript
test('ArtifactDeletionDialog has zero accessibility violations', async () => {
  const { container } = render(<ArtifactDeletionDialog {...props} open />);
  const results = await axe(container);
  expect(results.violations).toHaveLength(0);
});
```

---

## Risk Assessment & Mitigation

### High-Risk Areas

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Partial failure (some projects deleted, some not) | User confusion about deletion state | Medium | Clear error message per project, show partial success, allow retry |
| User accidentally confirms full deletion | Permanent data loss | Low | Multi-step confirmation, RED warnings, toast confirmation |
| Cache stale after deletion | Old data shown in UI | Medium | Invalidate broadly in onSuccess, use query factories |
| Network error mid-operation | Incomplete deletion, inconsistent state | Low | Promise.allSettled handles per-project failures, allow retry |

### Medium-Risk Areas

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Long list of projects (100+) | Dialog performance degrades | Low | Implement virtual scrolling if needed, pagination |
| Dialog size on mobile | Layout breaks on small screens | Medium | Test responsive design, scroll content area |
| Accessibility violations | Users can't navigate dialog | Low | axe-core audit, proper labels and ARIA, keyboard nav |

### Mitigation Strategy

1. **Partial Failures**: Use `Promise.allSettled()` to ensure all operations attempted, collect errors, show detailed message
2. **Data Loss**: Multi-step confirmation dialog, visual RED warnings, test error handling thoroughly
3. **Cache Issues**: Invalidate broadly in `onSuccess`, use TanStack Query cache factories, test cache behavior
4. **Network Issues**: Error boundaries, retry capability, test network error scenarios
5. **Mobile Issues**: Test on real devices, responsive design from start, virtual scrolling if needed

---

## Success Metrics

### Quantitative

- **Deletion Success Rate**: 95%+ of operations complete without error
- **Performance**: Dialog renders in <100ms, delete operation completes in <5 seconds
- **Test Coverage**: >90% code coverage for hook and component
- **Accessibility**: 0 axe-core violations

### Qualitative

- **User Satisfaction**: Clear, intuitive deletion flow with no confusion
- **Error Recovery**: Users can easily retry failed operations
- **Visual Clarity**: RED warnings prevent accidental filesystem deletion

### Metrics to Track

- Number of deletion operations per user per week
- Success/failure rate
- Average number of projects deleted per operation
- Error rates by type (collection vs project vs deployment)

---

## Timeline & Resource Allocation

### Estimated Duration

- **Phase 1** (Core): 3-5 days (8-12 hours effort)
- **Phase 2** (Integration): 2-3 days (4-6 hours effort)
- **Phase 3** (Polish): 1-2 days (2-3 hours effort)

**Total**: 1.5-2 weeks (14-21 hours actual effort)

### Resource Requirements

**Primary Assignee**: ui-engineer-enhanced (Sonnet model)

**Support**:
- codebase-explorer: Pattern discovery if needed
- code-reviewer: Final review and merge

**No Backend Changes Required**: All APIs production-ready

---

## Dependencies & Assumptions

### Hard Dependencies

- Backend APIs: `DELETE /api/v1/artifacts/{id}`, `POST /api/v1/deploy/undeploy` (✅ implemented)
- TanStack React Query v5+ (✅ available)
- shadcn Dialog/AlertDialog components (✅ available)
- lucide-react icons (AlertTriangle, Loader2, Trash2) (✅ available)

### Soft Dependencies

- EntityActions component pattern
- Artifact and Deployment TypeScript types
- API client patterns from `lib/api/`

### Key Assumptions

1. ✅ Backend DELETE endpoint works reliably
2. ✅ Undeploy API is idempotent (safe to call multiple times)
3. ✅ Project paths are unique and stable
4. ✅ TanStack Query cache invalidation works as expected
5. ✅ Users understand collection vs project distinction

### Known Limitations

1. No undo/recovery (permanent deletion)
2. Single artifact only (no bulk deletion)
3. No deletion audit logs
4. No scheduled deletion
5. No soft-delete with recovery window

---

## Appendix: Code Examples

### Example: Minimal Dialog Usage

```typescript
import { useState } from 'react';
import { ArtifactDeletionDialog } from '@/components/entity/artifact-deletion-dialog';
import type { Artifact } from '@/types/artifact';

export function MyComponent({ artifact }: { artifact: Artifact }) {
  const [showDelete, setShowDelete] = useState(false);

  return (
    <>
      <button onClick={() => setShowDelete(true)}>Delete</button>

      <ArtifactDeletionDialog
        artifact={artifact}
        open={showDelete}
        onOpenChange={setShowDelete}
        context="collection"
        onSuccess={() => {
          console.log('Artifact deleted');
          setShowDelete(false);
        }}
      />
    </>
  );
}
```

### Example: Hook Usage in Dialog

```typescript
const { mutate: deleteArtifact, isPending } = useArtifactDeletion();

const handleConfirmDelete = async () => {
  try {
    await deleteArtifact({
      artifact,
      deleteFromCollection: true,
      deleteFromProjects: false,
      deleteDeployments: false,
      selectedProjectPaths: [],
      selectedDeploymentPaths: [],
    });

    toast.success(`Deleted ${artifact.name}`);
    onOpenChange(false);
  } catch (error) {
    toast.error(`Failed to delete: ${error.message}`);
  }
};
```

---

## References

- **PRD**: `/docs/project_plans/PRDs/features/artifact-deletion-v1.md`
- **API Client Rules**: `/.claude/rules/web/api-client.md`
- **Hooks Patterns**: `/.claude/rules/web/hooks.md`
- **Entity Actions Component**: `skillmeat/web/components/entity/entity-actions.tsx`
- **Delete Source Dialog Reference**: `skillmeat/web/components/marketplace/delete-source-dialog.tsx`
- **Backend Routers**: `skillmeat/api/routers/artifacts.py`, `skillmeat/api/routers/deployments.py`

---

**Document Version**: 1.0

**Created**: 2025-12-20

**Status**: Ready for Implementation

**Next Steps**: Execute Phase 1 task delegation with ui-engineer-enhanced agent
