---
type: progress
prd: collections-navigation
phase: 5
title: Groups & Deployment Dashboard
status: pending
overall_progress: 0
total_tasks: 6
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
owners:
- ui-engineer-enhanced
contributors:
- frontend-developer
tasks:
- id: TASK-5.1
  name: Grouped View with Drag-and-Drop
  description: Grouped artifact view with drag-and-drop reordering using dnd-kit
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 3h
  priority: high
- id: TASK-5.2
  name: Manage Groups Dialog
  description: CRUD dialog for group management with membership controls
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 2.5h
  priority: high
- id: TASK-5.3
  name: Deployment Dashboard (formerly /manage)
  description: Convert /manage page to deployment-focused dashboard with filters and
    search
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 3h
  priority: high
- id: TASK-5.4
  name: Deployment Card Component
  description: Card component displaying deployment status, versions, and actions
  status: pending
  assigned_to:
  - frontend-developer
  dependencies: []
  estimated_effort: 1.5h
  priority: medium
- id: TASK-5.5
  name: Deployment Summary Endpoint Integration
  description: Integrate API deployment summary endpoint with dashboard
  status: pending
  assigned_to:
  - frontend-developer
  dependencies: []
  estimated_effort: 1.5h
  priority: medium
- id: TASK-5.6
  name: Unified Modal Deployments Tab
  description: Add Deployments tab to artifact modal showing all deployments
  status: pending
  assigned_to:
  - frontend-developer
  dependencies:
  - TASK-5.4
  estimated_effort: 2h
  priority: medium
parallelization:
  batch_1:
  - TASK-5.1
  - TASK-5.2
  - TASK-5.3
  - TASK-5.4
  - TASK-5.5
  batch_2:
  - TASK-5.6
  critical_path:
  - TASK-5.1
  - TASK-5.2
  - TASK-5.3
  estimated_total_time: 1.5w
blockers: []
success_criteria:
- id: SC-1
  description: Grouped view displays artifacts organized by groups
  status: pending
- id: SC-2
  description: Drag-and-drop reordering works within groups
  status: pending
- id: SC-3
  description: Manage Groups dialog supports CRUD operations
  status: pending
- id: SC-4
  description: Deployment dashboard shows aggregated stats
  status: pending
- id: SC-5
  description: Deployment cards display status and version info
  status: pending
- id: SC-6
  description: Modal Deployments tab lists all deployments for artifact
  status: pending
- id: SC-7
  description: All drag-drop operations persist to backend
  status: pending
files_modified: []
schema_version: 2
doc_type: progress
feature_slug: collections-navigation
---

# collections-navigation - Phase 5: Groups & Deployment Dashboard

**Phase**: 5 of 6
**Status**: Pending (0% complete)
**Owner**: ui-engineer-enhanced
**Contributors**: frontend-developer
**Dependencies**: Phase 4 (Collection Features)

---

## Phase Objective

Implement grouped artifact view with drag-and-drop, group management UI, and convert /manage page to deployment-focused dashboard. This phase completes the groups functionality and enhances deployment visibility.

---

## Orchestration Quick Reference

**Batch 1** (Parallel - Core Components):
- TASK-5.1 → `ui-engineer-enhanced` (3h) - Grouped view with drag-drop
- TASK-5.2 → `ui-engineer-enhanced` (2.5h) - Manage Groups dialog
- TASK-5.3 → `ui-engineer-enhanced` (3h) - Deployment dashboard
- TASK-5.4 → `frontend-developer` (1.5h) - Deployment card component
- TASK-5.5 → `frontend-developer` (1.5h) - Deployment summary integration

**Batch 2** (Sequential - Dependent, after Batch 1):
- TASK-5.6 → `frontend-developer` (2h) - Modal Deployments tab

### Task Delegation Commands

```
# Batch 1 (Parallel)
Task("ui-engineer-enhanced", "TASK-5.1: Implement grouped view mode in collection page using @dnd-kit/core. Display artifacts organized by groups (collapsible sections). Support drag-and-drop to reorder artifacts within group and between groups. Visual feedback during drag (dragging state, drop zones). Persist reorder via useReorderArtifacts hook. Ungrouped artifacts section at bottom. Files: /skillmeat/web/components/collections/GroupedView.tsx, update CollectionView.tsx")

Task("ui-engineer-enhanced", "TASK-5.2: Create ManageGroupsDialog component using Radix Dialog. Display list of groups in current collection (ordered by position). CRUD operations: Create group (name, description), Edit group (name, description, position), Delete group (confirm dialog), Reorder groups (drag-and-drop with dnd-kit). Add/remove artifacts to/from groups (multi-select). Integrates with useGroups hooks. Files: /skillmeat/web/components/collections/ManageGroupsDialog.tsx")

Task("ui-engineer-enhanced", "TASK-5.3: Convert /manage page to deployment-focused dashboard. Header with summary stats (total deployments, by status counts). Filters: Status (active/inactive/error), Artifact type, Project. Search by artifact name or project name. View toggle: By Artifact (grouped by artifact) vs By Project (grouped by project). Uses DeploymentCard components. Empty state when no deployments. Files: /skillmeat/web/app/manage/page.tsx or /skillmeat/web/app/deployments/page.tsx")

Task("frontend-developer", "TASK-5.4: Create DeploymentCard component displaying: Artifact name and icon, Project name, Deployed version vs Latest version (with badge if outdated), Status badge (active/inactive/error with colors), Deployed date (relative time), Actions menu (Update, Undeploy, View Details). Use Radix Card and Badge components. File: /skillmeat/web/components/deployments/DeploymentCard.tsx")

Task("frontend-developer", "TASK-5.5: Create useDeployments hook integrating with /api/v1/deployments/summary endpoint. Fetch deployment summary with stats (total, by_status, by_artifact, by_project). Create useDeploymentsByArtifact and useDeploymentsByProject hooks. Implement caching with TanStack Query. Update dashboard to use these hooks. Files: /skillmeat/web/hooks/useDeployments.ts, update dashboard page")

# Batch 2 (Sequential, after Batch 1)
Task("frontend-developer", "TASK-5.6: Add Deployments tab to ArtifactModal showing all deployments for this artifact across all projects. Display list of DeploymentCard components. Show empty state if no deployments. Include Deploy to New Project button. Real-time updates when deployments change. Integrates with useDeploymentsByArtifact hook. File: /skillmeat/web/components/artifacts/ArtifactModal.tsx - add new tab")
```

---

## Task Details

### TASK-5.1: Grouped View with Drag-and-Drop
- **Status**: pending
- **Assigned**: ui-engineer-enhanced
- **Estimated Effort**: 3h
- **Priority**: high

**Description**: Grouped artifact view with drag-and-drop reordering using dnd-kit

**Acceptance Criteria**:
- [ ] Grouped view mode in collection page (alongside Grid/List)
- [ ] Displays artifacts organized by groups (collapsible sections)
- [ ] Group header shows: name, description, artifact count, expand/collapse icon
- [ ] Uses @dnd-kit/core for drag-and-drop
- [ ] Drag artifact within same group to reorder (updates position)
- [ ] Drag artifact between groups (removes from old, adds to new)
- [ ] Visual feedback: dragging state, drop zones highlighted
- [ ] Persist changes via useReorderArtifacts and useAddArtifactsToGroup hooks
- [ ] "Ungrouped Artifacts" section at bottom for artifacts not in any group
- [ ] Empty state per group when no artifacts
- [ ] Smooth animations on drag/drop

**Files**: `/skillmeat/web/components/collections/GroupedView.tsx`, update `/skillmeat/web/components/collections/CollectionView.tsx`

---

### TASK-5.2: Manage Groups Dialog
- **Status**: pending
- **Assigned**: ui-engineer-enhanced
- **Estimated Effort**: 2.5h
- **Priority**: high

**Description**: CRUD dialog for group management with membership controls

**Acceptance Criteria**:
- [ ] ManageGroupsDialog component using Radix Dialog
- [ ] Left panel: List of groups (ordered by position)
  - [ ] Each group shows: name, artifact count, edit/delete icons
  - [ ] Drag handles for reordering groups
- [ ] Right panel: Group details (when group selected)
  - [ ] Form: name (required), description (optional)
  - [ ] Artifacts in group (list with remove button)
  - [ ] Add artifacts button (opens multi-select dropdown)
- [ ] Create Group button at top
- [ ] Delete group confirmation dialog
- [ ] Reorder groups via drag-and-drop (dnd-kit)
- [ ] Integrates with useGroups, useCreateGroup, useUpdateGroup, useDeleteGroup hooks
- [ ] Toast notifications on success/error
- [ ] Loading states during operations

**Files**: `/skillmeat/web/components/collections/ManageGroupsDialog.tsx`

---

### TASK-5.3: Deployment Dashboard (formerly /manage)
- **Status**: pending
- **Assigned**: ui-engineer-enhanced
- **Estimated Effort**: 3h
- **Priority**: high

**Description**: Convert /manage page to deployment-focused dashboard with filters and search

**Acceptance Criteria**:
- [ ] Route: `/manage` or `/deployments` (deployment-focused dashboard)
- [ ] Header with summary stats:
  - [ ] Total deployments count
  - [ ] Active/Inactive/Error counts (color-coded badges)
  - [ ] Last updated timestamp
- [ ] Filters:
  - [ ] Status: All, Active, Inactive, Error (radio select)
  - [ ] Artifact Type: All, Skill, Agent, Command (checkboxes)
  - [ ] Project: All projects dropdown (searchable)
- [ ] Search bar: Filter by artifact name or project name (debounced)
- [ ] View toggle: "By Artifact" (grouped by artifact) vs "By Project" (grouped by project)
- [ ] Displays DeploymentCard components in grid
- [ ] Empty state when no deployments match filters
- [ ] Loading skeleton while fetching
- [ ] Responsive design

**Files**: `/skillmeat/web/app/manage/page.tsx` or `/skillmeat/web/app/deployments/page.tsx`

---

### TASK-5.4: Deployment Card Component
- **Status**: pending
- **Assigned**: frontend-developer
- **Estimated Effort**: 1.5h
- **Priority**: medium

**Description**: Card component displaying deployment status, versions, and actions

**Acceptance Criteria**:
- [ ] Uses Radix Card component
- [ ] Displays:
  - [ ] Artifact name and icon (top-left)
  - [ ] Project name (below artifact name)
  - [ ] Deployed version badge
  - [ ] Latest version badge (if different, show "Update Available" indicator)
  - [ ] Status badge (active=green, inactive=gray, error=red)
  - [ ] Deployed date (relative time, e.g., "2 days ago")
- [ ] Actions menu (ellipsis icon):
  - [ ] "Update to Latest" (if outdated)
  - [ ] "Undeploy"
  - [ ] "View Details" (opens artifact modal)
- [ ] Click card to open artifact modal
- [ ] Hover state with subtle shadow
- [ ] Responsive layout (mobile-first)

**Files**: `/skillmeat/web/components/deployments/DeploymentCard.tsx`

---

### TASK-5.5: Deployment Summary Endpoint Integration
- **Status**: pending
- **Assigned**: frontend-developer
- **Estimated Effort**: 1.5h
- **Priority**: medium

**Description**: Integrate API deployment summary endpoint with dashboard

**Acceptance Criteria**:
- [ ] Create useDeployments hook using TanStack Query
- [ ] Fetch from `/api/v1/deployments/summary`
- [ ] Return: total_deployments, by_status, by_artifact, by_project
- [ ] Create useDeploymentsByArtifact(artifactId) hook
- [ ] Create useDeploymentsByProject(projectId) hook
- [ ] Implement caching (5 minute staleTime)
- [ ] Implement refetching on window focus
- [ ] Update dashboard page to use these hooks
- [ ] Loading and error states handled
- [ ] Optimistic updates for deployment mutations

**Files**: `/skillmeat/web/hooks/useDeployments.ts`, update dashboard page

---

### TASK-5.6: Unified Modal Deployments Tab
- **Status**: pending
- **Assigned**: frontend-developer
- **Estimated Effort**: 2h
- **Priority**: medium
- **Dependencies**: TASK-5.4

**Description**: Add Deployments tab to artifact modal showing all deployments

**Acceptance Criteria**:
- [ ] New "Deployments" tab in ArtifactModal (alongside Details, Collections & Groups)
- [ ] Shows all deployments for this artifact across all projects
- [ ] Uses DeploymentCard component for each deployment
- [ ] Summary at top: Total deployments, Active count, Update available count
- [ ] "Deploy to New Project" button at top
- [ ] Empty state: "Not deployed to any projects. Deploy now to get started."
- [ ] Real-time updates: Deployment changes reflect immediately
- [ ] Integrates with useDeploymentsByArtifact hook
- [ ] Loading skeleton while fetching
- [ ] Grouped by project (collapsible sections)

**Files**: `/skillmeat/web/components/artifacts/ArtifactModal.tsx`

---

## Progress Summary

**Completed**: 0/6 tasks (0%)
**In Progress**: 0/6 tasks
**Blocked**: 0/6 tasks
**Pending**: 6/6 tasks

---

## Key Implementation Patterns

### Drag-and-Drop with dnd-kit
- Use @dnd-kit/core for all drag-drop functionality
- Implement drag sensors (mouse, touch, keyboard)
- Visual feedback with CSS classes during drag
- Optimistic UI updates during drag
- Persist to backend on drop (with rollback on error)

### Deployment Dashboard
- Summary stats in header (real-time)
- Filters and search with URL query params (shareable)
- View toggle persisted in localStorage
- Grouped views with collapsible sections

### Component Reuse
- DeploymentCard used in dashboard and modal
- GroupedView can be reused in other contexts
- Consistent actions menu pattern across cards

---

## Testing Requirements

### Component Tests
**Files**: `/skillmeat/web/components/collections/__tests__/GroupedView.test.tsx`, `/skillmeat/web/components/deployments/__tests__/DeploymentCard.test.tsx`

- Drag-and-drop behavior (reorder, move between groups)
- Group management CRUD operations
- Deployment card display and actions
- Filter and search functionality

### Integration Tests
**File**: `/skillmeat/web/app/manage/__tests__/page.test.tsx`

- Dashboard summary stats accuracy
- Filters update view correctly
- View toggle switches between modes

---

## Phase Completion Criteria

Phase 5 is complete when:

1. **Grouped View**: Artifacts displayed by groups with drag-drop
2. **Group Management**: CRUD operations for groups working
3. **Deployment Dashboard**: /manage page shows deployment stats
4. **Deployment Cards**: Cards display status and versions
5. **API Integration**: Deployment summary endpoint integrated
6. **Modal Tab**: Deployments tab shows all artifact deployments
7. **Drag-Drop**: All reordering persists to backend
8. **Accessibility**: Keyboard support for drag-drop
9. **Testing**: Component tests for major features
10. **Code Review**: Approved by UI lead
