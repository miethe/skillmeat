---
type: progress
prd: "artifact-deletion-v1"
phase: 1
title: "Core Dialog & Hook"
status: completed
progress: 100
total_tasks: 8
completed_tasks: 8
blocked_tasks: 0
created: "2025-12-20"
updated: "2025-12-20"
completed_at: "2025-12-20"
commit: "87764fa"

tasks:
  - id: "FE-001"
    title: "Create API client function for artifact deletion"
    status: "completed"
    priority: "high"
    estimate: "0.5pt"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    file_targets:
      - "skillmeat/web/lib/api/artifacts.ts"
    notes: "Added deleteArtifactFromCollection function with proper error handling"

  - id: "FE-002"
    title: "Create useArtifactDeletion hook with TanStack Query"
    status: "completed"
    priority: "high"
    estimate: "1pt"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-001"]
    file_targets:
      - "skillmeat/web/hooks/use-artifact-deletion.ts"
    notes: "Mutation hook with Promise.allSettled for parallel undeployments, cache invalidation"

  - id: "FE-003"
    title: "Create ArtifactDeletionDialog component (Step 1 - Primary)"
    status: "completed"
    priority: "high"
    estimate: "1.5pt"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-002"]
    file_targets:
      - "skillmeat/web/components/entity/artifact-deletion-dialog.tsx"
    notes: "Primary confirmation step with context-aware messaging and toggle options"

  - id: "FE-004"
    title: "Implement Project Selection expandable section"
    status: "completed"
    priority: "medium"
    estimate: "1.5pt"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-003"]
    file_targets:
      - "skillmeat/web/components/entity/artifact-deletion-dialog.tsx"
    notes: "Expandable section with checkboxes, Select All/Deselect All, scrollable list"

  - id: "FE-005"
    title: "Implement Deployment Warning expandable section (RED styling)"
    status: "completed"
    priority: "medium"
    estimate: "1.5pt"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-003"]
    file_targets:
      - "skillmeat/web/components/entity/artifact-deletion-dialog.tsx"
    notes: "RED warning banner, AlertTriangle icons, destructive styling for filesystem deletion"

  - id: "FE-006"
    title: "Unit tests for useArtifactDeletion hook"
    status: "completed"
    priority: "medium"
    estimate: "1pt"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-002"]
    file_targets:
      - "skillmeat/web/__tests__/hooks/use-artifact-deletion.test.tsx"
    notes: "16 tests covering all mutation scenarios, partial failures, cache invalidation"

  - id: "FE-007"
    title: "Component tests for ArtifactDeletionDialog"
    status: "completed"
    priority: "medium"
    estimate: "1pt"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["FE-005"]
    file_targets:
      - "skillmeat/web/__tests__/components/entity/artifact-deletion-dialog.test.tsx"
    notes: "33 tests covering dialog flow, toggles, project/deployment selection, accessibility"

  - id: "FE-008"
    title: "Accessibility audit for Phase 1 components"
    status: "completed"
    priority: "low"
    estimate: "1pt"
    assigned_to: ["a11y-sheriff"]
    dependencies: ["FE-007"]
    file_targets:
      - "skillmeat/web/__tests__/a11y/artifact-deletion-dialog.a11y.test.tsx"
    notes: "23 axe-core tests, WCAG AA compliance, keyboard navigation, screen reader support"

parallelization:
  batch_1: ["FE-001"]
  batch_2: ["FE-002"]
  batch_3: ["FE-003", "FE-006"]
  batch_4: ["FE-004", "FE-005"]
  batch_5: ["FE-007"]
  batch_6: ["FE-008"]

blockers: []

references:
  prd: "docs/project_plans/PRDs/features/artifact-deletion-v1.md"
  implementation_plan: "docs/project_plans/implementation_plans/features/artifact-deletion-v1.md"
---

# Phase 1: Core Dialog & Hook

## Summary

Phase 1 establishes the core deletion infrastructure: API client functions, TanStack Query mutation hook, and the multi-step ArtifactDeletionDialog component with project selection and deployment warning sections.

**Estimated Effort**: 10 story points (3-5 days)
**Dependencies**: None (foundational phase)
**Assigned Agents**: ui-engineer-enhanced, a11y-sheriff

## Orchestration Quick Reference

### Batch 1 (Sequential - Foundation)

**FE-001** → `ui-engineer-enhanced` (0.5pt)

```
Task("ui-engineer-enhanced", "FE-001: Create API client functions for artifact deletion.

File: skillmeat/web/lib/api/artifacts.ts

Add two functions:
1. deleteArtifactFromCollection(artifactId: string, collection?: string): Promise<void>
   - DELETE /api/v1/artifacts/{artifact_id}?collection={collection}
   - Returns void (204 No Content)

2. undeployArtifact(request: UndeployRequest): Promise<UndeployResponse>
   - POST /api/v1/deploy/undeploy
   - Request: { artifact_name, artifact_type, project_path }

Follow existing patterns in collections.ts for error handling.
Use buildUrl() helper for URL construction.")
```

### Batch 2 (Sequential - Depends on FE-001)

**FE-002** → `ui-engineer-enhanced` (1pt)

```
Task("ui-engineer-enhanced", "FE-002: Create useArtifactDeletion hook.

File: skillmeat/web/hooks/use-artifact-deletion.ts

Create TanStack Query mutation hook that:
1. Accepts deletion options: { artifactId, collection?, deleteFromProjects?: string[], deleteDeployments?: string[] }
2. Orchestrates deletion sequence:
   - First: undeploy from selected projects (parallel calls)
   - Then: delete from collection (if requested)
3. Cache invalidation:
   - Invalidate ['artifacts'] after collection deletion
   - Invalidate ['deployments'] after any undeploy
   - Invalidate entity lists
4. Handle partial failures gracefully - report which succeeded/failed
5. Return { mutate, mutateAsync, isPending, isError, error, data }

Import API functions from FE-001.
Follow patterns in use-collections.ts for mutation structure.")
```

### Batch 3 (Parallel - FE-003 and FE-006)

**FE-003** → `ui-engineer-enhanced` (1.5pt)

```
Task("ui-engineer-enhanced", "FE-003: Create ArtifactDeletionDialog component - Step 1 Primary.

File: skillmeat/web/components/entity/artifact-deletion-dialog.tsx

Create multi-step AlertDialog following DeleteSourceDialog pattern:

Props:
- entity: Entity | null
- open: boolean
- onOpenChange: (open: boolean) => void
- context: 'collection' | 'project'
- projectPath?: string (for project context)
- onSuccess?: () => void

Primary Step:
1. Header with AlertTriangle icon (destructive)
2. Context-aware message: 'Delete [name] from [Collection X / Project Y]?'
3. Toggle: 'Also delete from [Projects/Collection]' (opposite of context)
4. Toggle: 'Delete Deployments' (only if deployments > 0, conditionally rendered)
5. Cancel and Delete buttons

State management:
- deleteFromOpposite: boolean
- deleteDeployments: boolean
- selectedProjects: string[]
- selectedDeployments: string[]

Use useArtifactDeletion hook from FE-002.
Use existing Radix AlertDialog, Switch, and Button components.")
```

**FE-006** → `ui-engineer-enhanced` (1pt)

```
Task("ui-engineer-enhanced", "FE-006: Unit tests for useArtifactDeletion hook.

File: skillmeat/web/__tests__/hooks/use-artifact-deletion.test.ts

Test cases:
1. Collection deletion only - success
2. Collection deletion only - failure (404)
3. Undeploy single project - success
4. Undeploy multiple projects in parallel - all succeed
5. Undeploy multiple projects - partial failure (one fails)
6. Combined: undeploy then delete collection
7. Cache invalidation after success
8. Error state after failure

Mock fetch globally. Use QueryClient wrapper.
Follow patterns in existing hook tests.")
```

### Batch 4 (Parallel - FE-004 and FE-005)

**FE-004** → `ui-engineer-enhanced` (1.5pt)

```
Task("ui-engineer-enhanced", "FE-004: Implement Project Selection expandable section.

File: skillmeat/web/components/entity/artifact-deletion-dialog.tsx

When 'Also delete from Projects' toggle is ON:
1. Show expandable section below toggle
2. Fetch deployments for this artifact using useDeploymentList
3. Group by project_path
4. Render checkbox list of projects with artifact deployed
5. Each item shows: project name, deployment path
6. 'Select All' / 'Deselect All' buttons
7. Update selectedProjects state on change

Use Collapsible component for expand/collapse.
Use Checkbox for selection.
Handle loading state while fetching deployments.")
```

**FE-005** → `ui-engineer-enhanced` (1.5pt)

```
Task("ui-engineer-enhanced", "FE-005: Implement Deployment Warning expandable section with RED styling.

File: skillmeat/web/components/entity/artifact-deletion-dialog.tsx

When 'Delete Deployments' toggle is ON:
1. Show expandable section with DESTRUCTIVE styling:
   - Red border: border-destructive
   - Red background tint: bg-destructive/10
   - Red text for warnings: text-destructive
2. Warning message: 'This will permanently delete files from your filesystem'
3. List of deployments with checkboxes
4. Each shows: deployment path (full filesystem path)
5. 'Select All' / 'Deselect All' buttons
6. Update selectedDeployments state

CRITICAL: Very clear visual distinction that this deletes actual files.
Use AlertTriangle icon prominently.
Red styling throughout this section.")
```

### Batch 5 (Sequential - Depends on FE-005)

**FE-007** → `ui-engineer-enhanced` (1pt)

```
Task("ui-engineer-enhanced", "FE-007: Component tests for ArtifactDeletionDialog.

File: skillmeat/web/__tests__/components/artifact-deletion-dialog.test.tsx

Test cases:
1. Renders with collection context - correct messaging
2. Renders with project context - correct messaging
3. Toggle 'Also delete from Projects' - shows expandable section
4. Toggle 'Delete Deployments' - shows RED warning section
5. Project selection checkboxes work
6. Deployment selection checkboxes work
7. Cancel button closes dialog
8. Delete button triggers mutation
9. Loading state during deletion
10. Error state after failure

Mock useDeploymentList and useArtifactDeletion hooks.
Use @testing-library/react for rendering and assertions.")
```

### Batch 6 (Sequential - Depends on FE-007)

**FE-008** → `a11y-sheriff` (1pt)

```
Task("a11y-sheriff", "FE-008: Accessibility audit for Phase 1 components.

Components to audit:
- skillmeat/web/components/entity/artifact-deletion-dialog.tsx

Check:
1. Focus management - focus trapped in dialog
2. Escape key closes dialog
3. Tab order is logical
4. Toggle switches have proper labels
5. Checkboxes have accessible names
6. Color contrast meets WCAG AA (especially RED warning section)
7. Screen reader announces dialog title and description
8. Error messages announced to screen reader
9. Loading state announced

Use jest-axe for automated checks.
Manual testing with VoiceOver or NVDA.")
```

## Key Files

| File | Purpose | LOC Est. |
|------|---------|----------|
| `lib/api/artifacts.ts` | API client functions | ~50 |
| `hooks/use-artifact-deletion.ts` | Mutation hook | ~150 |
| `components/entity/artifact-deletion-dialog.tsx` | Dialog component | ~350 |
| `__tests__/hooks/use-artifact-deletion.test.ts` | Hook tests | ~150 |
| `__tests__/components/artifact-deletion-dialog.test.tsx` | Component tests | ~200 |

## Acceptance Criteria

- [ ] API client functions call correct endpoints
- [ ] Hook handles parallel undeploy operations
- [ ] Hook provides cache invalidation
- [ ] Dialog shows context-aware messaging
- [ ] Toggle sections expand/collapse correctly
- [ ] Deployment warning uses RED styling
- [ ] Selective project/deployment deletion works
- [ ] Unit tests pass with >80% coverage
- [ ] Accessibility audit passes

## Notes

- Backend APIs already exist - no backend work needed
- Pattern reference: DeleteSourceDialog for cascade warning styling
- Pattern reference: entity-actions.tsx for existing simple delete dialog
- Pattern reference: use-collections.ts for mutation structure
