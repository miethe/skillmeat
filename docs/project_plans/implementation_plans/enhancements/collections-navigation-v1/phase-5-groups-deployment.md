---
title: 'Phase 5: Groups & Deployment Dashboard - Collections & Navigation Enhancement'
phase: 5
status: inferred_complete
assigned_to:
- ui-engineer-enhanced
- frontend-developer
dependencies:
- Phase 4 (Collection Features)
story_points: 12
duration: 1.5 weeks
---
# Phase 5: Groups & Deployment Dashboard

**Complexity**: Drag-and-drop interactions, advanced state management, cross-project views
**Story Points**: 12 | **Duration**: 1.5 weeks | **Status**: Pending

---

## Phase Objective

Implement the Grouped View with drag-and-drop functionality, Manage Groups dialog, repurpose /manage as the Deployment Dashboard, and add Deployments tab to the unified modal.

---

## Task Breakdown

### 1. Grouped View with Drag-and-Drop (TASK-5.1)
**Description**: Display artifacts organized by groups with drag-and-drop reordering

**Acceptance Criteria**:
- [ ] Grouped View mode added to collection page view mode toggle
- [ ] Display structure:
  - [ ] Groups displayed as sections/columns
  - [ ] Groups ordered by position field
  - [ ] Artifacts within each group ordered by position
  - [ ] Expandable/collapsible groups (optional)
  - [ ] Group header with name and artifact count
  - [ ] Empty group handling (show placeholder)
- [ ] Drag-and-drop functionality:
  - [ ] Drag artifact card to different group
  - [ ] Drop updates artifact position in target group
  - [ ] Position automatically reordered for other artifacts
  - [ ] Optimistic update: UI updates before API response
  - [ ] Revert on error: restore previous state if API fails
  - [ ] Visual feedback during drag: drop zone highlighting
  - [ ] Cursor changes to indicate draggable
- [ ] Performance:
  - [ ] Smooth drag animations (60 fps)
  - [ ] Batch position updates (update multiple at once)
  - [ ] Debounced API calls while dragging
- [ ] Accessibility:
  - [ ] Keyboard alternative to drag-drop (context menu reorder)
  - [ ] ARIA attributes for drag regions
  - [ ] Screen reader announces move operation
  - [ ] Focus management during move
- [ ] Mobile support:
  - [ ] Touch-friendly drag (larger drag handles)
  - [ ] Swipe gestures (optional: swipe to change groups)
  - [ ] Long-press to initiate drag
- [ ] Error handling:
  - [ ] Network error: rollback to previous state, show error toast
  - [ ] Validation error: show specific error message
  - [ ] Retry mechanism

**Files to Create/Modify**:
- Create: `/skillmeat/web/components/collection/artifact-grouped.tsx`
- Create: `/skillmeat/web/hooks/use-drag-drop.ts` (reusable hook)
- Modify: `/skillmeat/web/app/collection/page.tsx`

**Estimated Effort**: 3 points

---

### 2. Manage Groups Dialog (TASK-5.2)
**Description**: Dialog for CRUD operations on groups within collection

**Acceptance Criteria**:
- [ ] Dialog triggered from:
  - [ ] Artifact card ellipsis menu "Manage Groups"
  - [ ] Unified modal "Collections/Groups" tab
  - [ ] Collection page toolbar (future: manage all groups)
- [ ] Dialog displays:
  - [ ] List of all groups in current collection
  - [ ] Checkboxes for each group (checked if artifact in group)
  - [ ] "Create new group" option/input at bottom
  - [ ] Current artifact name shown in header
- [ ] Create new group:
  - [ ] Text input to enter group name
  - [ ] Validates: 1-255 chars, unique in collection
  - [ ] Auto-add artifact to newly created group
  - [ ] New group added to list and auto-checked
- [ ] Update group membership:
  - [ ] Check/uncheck to add/remove artifact from group
  - [ ] Changes applied on checkbox toggle (no separate save)
  - [ ] Loading state during updates
  - [ ] Optimistic updates with rollback on error
  - [ ] Multiple groups at once (artifact can be in many groups)
- [ ] Manage groups (expand optional):
  - [ ] Edit group name (inline or modal)
  - [ ] Delete group (with confirmation)
  - [ ] Reorder groups (drag or arrow buttons)
- [ ] Dialog controls:
  - [ ] "Done" or "Close" button to dismiss
  - [ ] Keyboard accessible (Escape to close)
  - [ ] Focus trap in dialog
- [ ] Success state:
  - [ ] Toast notification showing changes
  - [ ] Dialog remains open for multiple edits (optional)
  - [ ] Closes on final "Done"

**Files to Create/Modify**:
- Create: `/skillmeat/web/components/collection/manage-groups-dialog.tsx`
- Modify: `/skillmeat/web/components/collection/artifact-card.tsx` (action trigger)
- Modify: `/skillmeat/web/components/entity/modal-collections-tab.tsx` (action trigger)

**Estimated Effort**: 2.5 points

---

### 3. Deployment Dashboard (formerly /manage) (TASK-5.3)
**Description**: Repurpose /manage page to show cross-project deployment status

**Acceptance Criteria**:
- [ ] Page layout:
  - [ ] Header showing deployment summary stats
    - [ ] Total deployments count
    - [ ] By status breakdown (active, inactive, error)
    - [ ] By project breakdown
  - [ ] Filtering options:
    - [ ] By deployment status
    - [ ] By project
    - [ ] By artifact type
    - [ ] By search (artifact name, project name)
  - [ ] Sorting options:
    - [ ] By artifact name
    - [ ] By project
    - [ ] By deployment date
    - [ ] By status
  - [ ] Main content: artifact/project grid or table
- [ ] Artifact card display in dashboard:
  - [ ] Name, type, source
  - [ ] Deployed to X projects indicator
  - [ ] Status indicators per project (in tooltip or sub-rows)
  - [ ] Quick action buttons:
    - [ ] "Deploy to New Project"
    - [ ] "View Deployments"
  - [ ] Version info (deployed vs latest)
  - [ ] Update available indicator if newer version exists
  - [ ] Visual status indicator (active=green, inactive=gray, error=red)
- [ ] "Deploy to New Project" action:
  - [ ] Opens dialog to select target project
  - [ ] Optionally specify version to deploy
  - [ ] Confirmation before proceeding
  - [ ] Shows deployment progress/result
- [ ] "View Deployments" action:
  - [ ] Shows modal/panel with all deployments for artifact
  - [ ] Lists project, version, status, deploy date for each
  - [ ] Allow updating individual deployments
- [ ] Search and filtering:
  - [ ] Real-time as-you-type (debounced)
  - [ ] Results update dynamically
  - [ ] "Clear filters" button
  - [ ] Save filter presets (optional, Phase 6+)
- [ ] Performance:
  - [ ] Pagination for large datasets (100+ artifacts)
  - [ ] Lazy load deployment details (on demand)
  - [ ] Summary stats cached/aggregated
- [ ] Responsive:
  - [ ] Works on mobile (adapt to narrow screens)
  - [ ] Swipe to reveal actions on mobile

**Files to Create/Modify**:
- Modify: `/skillmeat/web/app/manage/page.tsx` - Complete redesign
- Create: `/skillmeat/web/components/deployment/deployment-dashboard.tsx`
- Create: `/skillmeat/web/components/deployment/deployment-card.tsx`
- Create: `/skillmeat/web/components/deployment/deployment-summary.tsx`
- Create: `/skillmeat/web/components/deployment/deploy-to-project-dialog.tsx`
- Create: `/skillmeat/web/components/deployment/deployments-modal.tsx`

**Estimated Effort**: 3 points

---

### 4. Deployment Card Component (TASK-5.4)
**Description**: Card component for displaying deployment status

**Acceptance Criteria**:
- [ ] Card displays:
  - [ ] Artifact name and type
  - [ ] Project deployment info:
    - [ ] Project name
    - [ ] Deployed version
    - [ ] Latest available version
    - [ ] Status badge (active/inactive/error/pending)
  - [ ] Optional: Linting status indicator (future)
- [ ] Visual design:
  - [ ] Status color-coded (green=active, gray=inactive, red=error)
  - [ ] Version comparison (highlight if update available)
  - [ ] Deployment date/time (relative: "2 hours ago")
  - [ ] Hover shows more details
- [ ] Quick actions:
  - [ ] Update deployment (change version)
  - [ ] Change status
  - [ ] View history
  - [ ] Remove deployment
- [ ] States:
  - [ ] Normal: full information displayed
  - [ ] Loading: skeleton or spinner while updating
  - [ ] Error: error icon with tooltip
  - [ ] Success: green checkmark briefly shown
- [ ] Compact version for dashboard view
- [ ] Expanded version for list view with more details

**Files to Create/Modify**:
- Create: `/skillmeat/web/components/deployment/deployment-card.tsx`

**Estimated Effort**: 1.5 points

---

### 5. Deployment Summary Endpoint Integration (TASK-5.5)
**Description**: Integrate deployment summary data into dashboard

**Acceptance Criteria**:
- [ ] Dashboard fetches deployment summary from API (Phase 2)
- [ ] Summary data displayed in header:
  - [ ] Total count
  - [ ] Breakdown by status (pie chart or bars)
  - [ ] Recent deployments (last 5)
- [ ] Artifact list data enriched with deployment info:
  - [ ] Count of projects each artifact deployed to
  - [ ] Aggregated status (active if any project active)
  - [ ] Latest deployment date
  - [ ] Update available flag
- [ ] Caching strategy:
  - [ ] Summary cached for 5 minutes
  - [ ] Manual refresh available
  - [ ] Real-time updates on deployment changes
- [ ] Performance:
  - [ ] Summary query < 100ms
  - [ ] Pagination prevents large data transfer
- [ ] Error handling:
  - [ ] Graceful degradation if summary unavailable
  - [ ] Retry mechanism
  - [ ] Clear error messages

**Files to Create/Modify**:
- Create: `/skillmeat/web/hooks/use-deployments.ts` (hook for deployment data)
- Modify: `/skillmeat/web/lib/api/deployments.ts` - Add summary fetching

**Estimated Effort**: 1.5 points

---

### 6. Unified Modal Deployments Tab (TASK-5.6)
**Description**: Add "Deployments" tab to unified artifact modal

**Acceptance Criteria**:
- [ ] New tab "Deployments" added to modal
- [ ] Tab only visible if artifact has deployments
- [ ] Displays:
  - [ ] Table/list of all deployments for artifact
  - [ ] Columns: Project, Status, Deployed Version, Latest Version, Deploy Date
  - [ ] Status indicated with badge/color
  - [ ] Version comparison (highlight if outdated)
  - [ ] Action buttons per deployment:
    - [ ] "Update" - change deployed version
    - [ ] "Remove" - undeployed from project
    - [ ] "View" - show in deployment dashboard
- [ ] Summary section:
  - [ ] Total projects deployed to
  - [ ] Active deployments count
  - [ ] Outdated deployments count
- [ ] Actions:
  - [ ] "Deploy to New Project" button
  - [ ] Bulk actions (optional: update all, remove all)
- [ ] Empty state:
  - [ ] Message if no deployments
  - [ ] "Deploy now" button
- [ ] Loading/error states
- [ ] Responsive design for modal width constraints

**Files to Create/Modify**:
- Create: `/skillmeat/web/components/entity/modal-deployments-tab.tsx`
- Modify: `/skillmeat/web/components/entity/unified-entity-modal.tsx` - Add tab

**Estimated Effort**: 2 points

---

## Task Breakdown Table

| Task ID | Task Name | Description | Story Points | Assigned To |
|---------|-----------|-------------|--------------|-------------|
| TASK-5.1 | Grouped View with Drag-Drop | Grouped view with reordering | 3 | ui-engineer-enhanced |
| TASK-5.2 | Manage Groups Dialog | CRUD for group membership | 2.5 | ui-engineer-enhanced |
| TASK-5.3 | Deployment Dashboard | /manage page redesign | 3 | ui-engineer-enhanced |
| TASK-5.4 | Deployment Card | Component for deployment display | 1.5 | frontend-developer |
| TASK-5.5 | Deployment Summary Integration | API integration for summary | 1.5 | frontend-developer |
| TASK-5.6 | Unified Modal Deployments Tab | New modal tab | 2 | frontend-developer |

**Total**: 12 story points

---

## Drag-and-Drop Implementation Details

### Using `@dnd-kit` Library

```typescript
// Installation
npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities

// Basic structure
import { DndContext, closestCenter, KeyboardSensor } from '@dnd-kit/core';
import { SortableContext } from '@dnd-kit/sortable';

// Artifact card made draggable with useSortable hook
const ArtifactCardDraggable = ({ id, artifact }) => {
  const { attributes, listeners, setNodeRef, transform } = useSortable({ id });

  return (
    <div ref={setNodeRef} {...attributes} {...listeners}>
      {/* Card content */}
    </div>
  );
};

// Group container with drop zone
const GroupDropZone = ({ group, artifacts }) => {
  const { active, over } = useDroppable({ id: group.id });

  return (
    <div className={over ? 'drop-active' : ''}>
      {/* Artifacts */}
    </div>
  );
};
```

### Position Update Logic

```typescript
// When artifact is dropped in new group
const handleDragEnd = async (event) => {
  const { active, over } = event;

  if (!over || active.id === over.id) return;

  // Optimistic update
  updateArtifactPosition(active.id, over.id, newPosition);

  // API call
  try {
    await api.updateGroupArtifact(groupId, artifactId, { position });
  } catch (error) {
    // Rollback on error
    revertArtifactPosition(active.id);
  }
};
```

---

## Testing Strategy

### Component Tests

**File**: `/skillmeat/web/__tests__/components/grouped-view.test.tsx`

```typescript
describe('Grouped View', () => {
  it('renders groups with artifacts', () => {
    // Verify groups displayed with correct artifacts
  });

  it('handles drag and drop', async () => {
    // Simulate drag, verify API called, UI updated
  });

  it('reverts on drag error', async () => {
    // Simulate failed API call, verify position reverted
  });

  it('keyboard alternative to drag', () => {
    // Use context menu to move artifact
  });
});

describe('ManageGroupsDialog', () => {
  it('renders groups with checkboxes', () => {
    // Verify all groups listed and correctly checked
  });

  it('toggles group membership', async () => {
    // Check/uncheck group, verify API called
  });

  it('creates new group', async () => {
    // Enter group name, verify created and added to list
  });
});
```

### E2E Tests

**File**: `/skillmeat/web/tests/deployment-workflow.spec.ts`

```typescript
test('deployment dashboard workflow', async ({ page }) => {
  await page.goto('/manage');

  // Verify summary stats visible
  await expect(page.getByText(/\d+ Deployments/)).toBeVisible();

  // Filter by status
  await page.selectOption('[data-testid="status-filter"]', 'active');
  await expect(page.locator('[data-deployment-status="active"]')).toHaveCount(5);

  // Deploy to new project
  await page.click('[data-testid="deploy-button"]');
  await page.selectOption('[name="project"]', 'proj-123');
  await page.click('button:has-text("Deploy")');

  // Verify success
  await expect(page.getByText('Deployed successfully')).toBeVisible();
});
```

---

## Quality Gates

### Drag-and-Drop Checklist
- [ ] Smooth animations (60 fps measured with Profiler)
- [ ] Keyboard alternative available
- [ ] Mobile touch targets >= 44px
- [ ] ARIA attributes for accessibility
- [ ] Rollback on network error
- [ ] Optimistic updates work correctly
- [ ] No memory leaks (cleanup listeners)
- [ ] Touch support (iOS, Android)

### Dashboard Checklist
- [ ] Summary stats accurate
- [ ] Filtering works correctly (AND logic)
- [ ] Search is responsive (< 300ms)
- [ ] Pagination handles 1000+ artifacts
- [ ] Status colors clear and accessible
- [ ] Version comparisons obvious
- [ ] Quick actions intuitive

### Deployments Tab Checklist
- [ ] Tab only shows when deployments exist
- [ ] Data displayed clearly in table format
- [ ] Status badges color-coded
- [ ] Version comparison highlighted
- [ ] Action buttons working correctly
- [ ] Modal width constraints handled
- [ ] Loading states shown

---

## Files to Create

### Grouped View Files
1. `/skillmeat/web/components/collection/artifact-grouped.tsx` (~150 lines)
2. `/skillmeat/web/hooks/use-drag-drop.ts` (~100 lines)

### Manage Groups Dialog
1. `/skillmeat/web/components/collection/manage-groups-dialog.tsx` (~150 lines)

### Deployment Dashboard Files
1. `/skillmeat/web/components/deployment/deployment-dashboard.tsx` (~200 lines)
2. `/skillmeat/web/components/deployment/deployment-card.tsx` (~120 lines)
3. `/skillmeat/web/components/deployment/deployment-summary.tsx` (~80 lines)
4. `/skillmeat/web/components/deployment/deploy-to-project-dialog.tsx` (~120 lines)
5. `/skillmeat/web/components/deployment/deployments-modal.tsx` (~100 lines)
6. `/skillmeat/web/hooks/use-deployments.ts` (~80 lines)
7. `/skillmeat/web/components/entity/modal-deployments-tab.tsx` (~100 lines)

---

## Dependencies

### Runtime
- `@dnd-kit/core` - Drag and drop
- `@dnd-kit/sortable` - Sorting
- `@dnd-kit/utilities` - Helper functions
- Existing React Query, Radix UI

### Development
- `@testing-library/user-event` - User interactions in tests

---

## Effort Breakdown

| Task | Hours | Notes |
|------|-------|-------|
| Grouped View & Drag-Drop | 12 | Complex interactions, accessibility |
| Manage Groups Dialog | 8 | Group membership management |
| Deployment Dashboard | 12 | Page redesign, filtering, sorting |
| Deployment Cards | 6 | Component with states |
| Deployment Summary Integration | 4 | API integration |
| Modal Deployments Tab | 6 | Tab integration |
| Testing | 10 | Component, E2E, accessibility |
| **Total** | **58 hours** | ~7 days actual work, ~10 business days calendar |

---

## Success Criteria

Phase 5 is complete when:

1. **Grouped View**: Display and drag-drop working smoothly
2. **Manage Groups**: Dialog for membership management functional
3. **Deployment Dashboard**: /manage redesigned with all features
4. **Deployment Cards**: Status, versions, quick actions working
5. **Summary Integration**: API data properly displayed and cached
6. **Modal Tab**: Deployments tab integrated into unified modal
7. **Testing**: 85%+ coverage of new components
8. **Accessibility**: WCAG 2.1 AA compliance verified
9. **Performance**: Drag-drop smooth (60 fps), dashboard loads < 2 seconds
10. **Code Review**: Approved by ui-engineer-enhanced

---

## Next Phase

Phase 6 (Caching & Polish) is the final phase. It will:
- Implement local artifact cache
- Add background refresh mechanism
- Ensure cache persists across restarts
- Add comprehensive testing
- Complete documentation
