---
title: 'Phase 4: Collection Features - Collections & Navigation Enhancement'
phase: 4
status: inferred_complete
assigned_to:
- ui-engineer-enhanced
- frontend-developer
dependencies:
- Phase 3 (Frontend Foundation)
story_points: 15
duration: 1.5 weeks
---
# Phase 4: Collection Features

**Complexity**: Feature-rich UI components with complex state management
**Story Points**: 15 | **Duration**: 1.5 weeks | **Status**: Pending

---

## Phase Objective

Implement the primary Collection page interface with view modes, filtering, collection management dialogs, and enhanced artifact cards. This phase brings the core collection browsing experience to life.

---

## Task Breakdown

### 1. Collection Page Redesign (TASK-4.1)
**Description**: Rebuild /collection page with view modes and filtering capabilities

**Acceptance Criteria**:
- [ ] Page layout created with:
  - [ ] Header section (title, collection info)
  - [ ] Toolbar (view mode toggle, filters, search, refresh button)
  - [ ] Main content area (grid/list/grouped views)
  - [ ] Optional: Sidebar for advanced filters
- [ ] View mode toggle implemented (Grid/List/Grouped)
  - [ ] State persisted to localStorage
  - [ ] Smooth transitions between views
  - [ ] All views display same data, different layout
- [ ] Filtering system created:
  - [ ] By artifact type (skill, command, agent, etc.)
  - [ ] By deployment status (deployed, not deployed, update available)
  - [ ] By scope (user, local)
  - [ ] Combined filters work together (AND logic)
- [ ] Search functionality:
  - [ ] Case-insensitive search by name
  - [ ] Real-time as-you-type (debounced)
  - [ ] Search highlights matching terms
- [ ] Sorting options:
  - [ ] By name (A-Z, Z-A)
  - [ ] By created date (newest/oldest)
  - [ ] By last modified
  - [ ] By type
- [ ] Pagination or infinite scroll for large collections
- [ ] Loading state with skeleton screens
- [ ] Empty state with helpful message
- [ ] Error state with retry option
- [ ] Responsive design (mobile, tablet, desktop)

**Files to Create/Modify**:
- Modify: `/skillmeat/web/app/collection/page.tsx`
- Create: `/skillmeat/web/components/collection/collection-header.tsx`
- Create: `/skillmeat/web/components/collection/collection-toolbar.tsx`
- Create: `/skillmeat/web/components/collection/artifact-grid.tsx`
- Create: `/skillmeat/web/components/collection/artifact-list.tsx`

**Estimated Effort**: 3 points

---

### 2. Collection Switcher Component (TASK-4.2)
**Description**: Dropdown component to switch between collections

**Acceptance Criteria**:
- [ ] Dropdown positioned prominently in page header
- [ ] Shows currently selected collection name
- [ ] Dropdown options include:
  - [ ] All available collections
  - [ ] "All Collections" special option (aggregated view)
  - [ ] "Add Collection" option to create new
- [ ] Clicking collection changes view immediately
- [ ] Visual indicator for current selection
- [ ] "Add Collection" triggers dialog (TASK-4.3)
- [ ] Loading state while fetching collections
- [ ] Search within dropdown if many collections (10+)
- [ ] Keyboard accessible (arrow keys, Enter)
- [ ] Mobile-friendly (touch targets >= 44px)

**Files to Create/Modify**:
- Create: `/skillmeat/web/components/collection/collection-switcher.tsx`
- Modify: `/skillmeat/web/components/collection/collection-header.tsx`

**Estimated Effort**: 2 points

---

### 3. All Collections View (TASK-4.3)
**Description**: Aggregated view showing artifacts from all collections

**Acceptance Criteria**:
- [ ] Selectable from collection switcher as "All Collections"
- [ ] Displays artifacts from all collections combined
- [ ] Shows collection name/tag with each artifact
- [ ] Same filtering/search/sorting available as single collection view
- [ ] Preserves view mode selection (grid/list/grouped)
- [ ] All artifact actions available (move, edit, delete)
- [ ] Performance: pagination required (load only visible artifacts)
- [ ] Clear visual distinction from single collection view
- [ ] Breadcrumb or label shows "All Collections" mode

**Files to Create/Modify**:
- Modify: `/skillmeat/web/app/collection/page.tsx`
- Modify: `/skillmeat/web/components/collection/artifact-grid.tsx`
- Modify: `/skillmeat/web/components/collection/artifact-list.tsx`

**Estimated Effort**: 2 points

---

### 4. Create/Edit Collection Dialogs (TASK-4.4)
**Description**: Dialogs for creating and editing collections

**Acceptance Criteria**:
- [ ] "Create Collection" dialog:
  - [ ] Triggered from collection switcher "Add Collection" option
  - [ ] Form fields: name (required), description (optional)
  - [ ] Validation: name 1-255 chars, no duplicates
  - [ ] Loading state during submission
  - [ ] Error message if creation fails
  - [ ] Success: dialog closes, new collection selected
  - [ ] Cancel: closes without changes
- [ ] "Edit Collection" dialog (accessed from dropdown or context menu):
  - [ ] Pre-populated with current collection data
  - [ ] Same fields as create
  - [ ] Partial update support (can update just one field)
  - [ ] Delete button (with confirmation) in dialog footer
  - [ ] Success: updates view, no reload needed
- [ ] "Delete Collection" confirmation:
  - [ ] Triggered from edit dialog or context menu
  - [ ] Warning message about cascading deletes
  - [ ] Confirms action before proceeding
  - [ ] Success: closes dialog, navigates to another collection
- [ ] Both dialogs:
  - [ ] Keyboard accessible (Escape to close, Tab navigation)
  - [ ] Focus management (trap focus in dialog)
  - [ ] Accessible error messages
  - [ ] Loading indicator during async operations

**Files to Create/Modify**:
- Create: `/skillmeat/web/components/collection/create-collection-dialog.tsx`
- Create: `/skillmeat/web/components/collection/edit-collection-dialog.tsx`
- Modify: `/skillmeat/web/components/collection/collection-switcher.tsx`

**Estimated Effort**: 2 points

---

### 5. Move/Copy to Collections Dialog (TASK-4.5)
**Description**: Dialog for bulk moving/copying artifacts between collections

**Acceptance Criteria**:
- [ ] Dialog triggered from artifact card action menu
- [ ] Form elements:
  - [ ] Checkboxes to select target collection(s)
  - [ ] 2 buttons: "Move" and "Copy" (move removes from original)
  - [ ] Info text showing # artifacts being moved/copied
- [ ] Behavior:
  - [ ] "Move": artifact removed from current, added to target
  - [ ] "Copy": artifact added to target, stays in current
  - [ ] Transactional: all succeed or all fail
  - [ ] Error handling: clear error message on failure
- [ ] UX considerations:
  - [ ] Cannot select current collection
  - [ ] Shows which artifacts will be affected
  - [ ] Loading state during operation
  - [ ] Success toast/notification
  - [ ] Dialog closes on success
- [ ] Keyboard accessible
- [ ] Works with single artifact or bulk selection

**Files to Create/Modify**:
- Create: `/skillmeat/web/components/collection/move-copy-dialog.tsx`

**Estimated Effort**: 1.5 points

---

### 6. Artifact Card Enhancement (TASK-4.6)
**Description**: Enhanced artifact card with ellipsis action menu

**Acceptance Criteria**:
- [ ] Artifact card displays:
  - [ ] Name, type badge, description excerpt
  - [ ] Source/version info
  - [ ] Collection tag (in "All Collections" view)
  - [ ] Deployment status indicator (optional, Phase 5)
- [ ] Ellipsis menu (⋯) in bottom right corner on hover
  - [ ] Appears on hover (desktop) or always visible (mobile)
  - [ ] Click opens dropdown menu with actions:
    - [ ] "Move/Copy to Collections" → Opens TASK-4.5 dialog
    - [ ] "Manage Groups" → Opens manage groups dialog (TASK-5.2)
    - [ ] "Edit" → Opens unified modal to Edit Parameters tab
    - [ ] "Delete" → Opens delete confirmation
  - [ ] Submenu items keyboard accessible
- [ ] Click on card body:
  - [ ] Opens unified artifact modal (existing feature)
  - [ ] Not affected by ellipsis menu
- [ ] Visual feedback:
  - [ ] Hover state on card
  - [ ] Active state for actions
  - [ ] Disabled state if user lacks permissions
- [ ] Touch/mobile optimization:
  - [ ] Ellipsis menu always visible on touch devices
  - [ ] Touch targets >= 44px
  - [ ] Menu doesn't obscure important card info

**Files to Create/Modify**:
- Modify: `/skillmeat/web/components/collection/artifact-card.tsx`
- Modify: `/skillmeat/web/components/collection/artifact-actions-menu.tsx` (create if needed)

**Estimated Effort**: 2 points

---

### 7. Unified Modal Collections/Groups Tab (TASK-4.7)
**Description**: New tab in unified artifact modal showing collection/group memberships

**Acceptance Criteria**:
- [ ] New tab "Collections/Groups" added to unified modal
- [ ] Displays:
  - [ ] List of collections artifact belongs to
  - [ ] Under each collection, list of groups artifact is in
  - [ ] Hierarchical display (collection → groups)
  - [ ] No collections/groups indicator if none
- [ ] Action buttons:
  - [ ] "Manage Groups" → Opens manage groups dialog
  - [ ] "Move/Copy to Collections" → Opens move/copy dialog
  - [ ] "Leave Collection" → Remove from collection (confirm first)
- [ ] Tab only visible when artifact in at least one collection
- [ ] Loading state while fetching memberships
- [ ] Error handling with retry option
- [ ] Integrates with existing modal tabs:
  - [ ] Overview
  - [ ] Sync/Deploy
  - [ ] History
  - [ ] Files
  - [ ] Collections/Groups (NEW)
  - [ ] Deployments (Phase 5)

**Files to Create/Modify**:
- Modify: `/skillmeat/web/components/entity/unified-entity-modal.tsx`
- Create: `/skillmeat/web/components/entity/modal-collections-tab.tsx`

**Estimated Effort**: 2 points

---

## Task Breakdown Table

| Task ID | Task Name | Description | Story Points | Assigned To |
|---------|-----------|-------------|--------------|-------------|
| TASK-4.1 | Collection Page Redesign | View modes, filtering, search, sort | 3 | ui-engineer-enhanced |
| TASK-4.2 | Collection Switcher | Dropdown to select collection | 2 | ui-engineer-enhanced |
| TASK-4.3 | All Collections View | Aggregated artifact view | 2 | ui-engineer-enhanced |
| TASK-4.4 | Create/Edit Dialogs | CRUD dialogs for collections | 2 | ui-engineer-enhanced |
| TASK-4.5 | Move/Copy Dialog | Bulk artifact operations | 1.5 | frontend-developer |
| TASK-4.6 | Artifact Card Enhancement | Ellipsis menu with actions | 2 | frontend-developer |
| TASK-4.7 | Unified Modal Tab | Collections/Groups membership tab | 2 | ui-engineer-enhanced |

**Total**: 15 story points

---

## Component Hierarchy

```
CollectionPage
├── CollectionHeader
│   ├── CollectionSwitcher (TASK-4.2)
│   │   ├── CreateCollectionDialog (TASK-4.4)
│   │   └── EditCollectionDialog (TASK-4.4)
│   └── PageTitle
├── CollectionToolbar (TASK-4.1)
│   ├── ViewModeToggle
│   ├── FilterPanel
│   ├── SearchInput
│   └── RefreshButton
├── ArtifactView (TASK-4.1, 4.3)
│   ├── ArtifactGrid
│   │   └── ArtifactCard (TASK-4.6)
│   │       └── ArtifactActionsMenu
│   │           ├── MoveCopyDialog (TASK-4.5)
│   │           └── ManageGroupsDialog (TASK-5.2)
│   ├── ArtifactList
│   │   └── ArtifactCard (TASK-4.6)
│   └── ArtifactGrouped (TASK-5.1)
└── Pagination (if needed)

UnifiedArtifactModal (existing)
├── OverviewTab
├── SyncDeployTab
├── HistoryTab
├── FilesTab
├── CollectionsGroupsTab (TASK-4.7)
│   ├── ManageGroupsDialog (TASK-5.2)
│   └── MoveCopyDialog (TASK-4.5)
└── DeploymentsTab (TASK-5.3)
```

---

## Testing Strategy

### Component Tests

**File**: `/skillmeat/web/__tests__/components/collection-page.test.tsx`

```typescript
describe('CollectionPage', () => {
  it('renders collection header with switcher', () => {
    // Verify header and switcher visible
  });

  it('changes view mode (Grid/List)', () => {
    // Toggle view, verify layout changes
  });

  it('filters artifacts by type', () => {
    // Select type filter, verify only matching artifacts shown
  });

  it('searches artifacts', () => {
    // Type in search, verify results updated
  });

  it('displays loading state', () => {
    // Verify skeleton screens during load
  });

  it('handles empty state', () => {
    // Verify helpful message when no artifacts
  });
});

describe('ArtifactCard', () => {
  it('renders card with artifact data', () => {
    // Verify name, type, description visible
  });

  it('opens actions menu on ellipsis click', () => {
    // Click ellipsis, verify menu appears
  });

  it('opens artifact modal on card click', () => {
    // Click card body, verify modal opens
  });

  it('handles mobile view (no hover)', () => {
    // Verify menu always visible on mobile
  });
});
```

### E2E Tests

**File**: `/skillmeat/web/tests/collection-workflow.spec.ts`

```typescript
test('complete collection workflow', async ({ page }) => {
  await page.goto('/collection');

  // Create new collection
  await page.click('[data-testid="collection-switcher"]');
  await page.click('button:has-text("Add Collection")');
  await page.fill('input[name="name"]', 'Test Collection');
  await page.click('button:has-text("Create")');

  // Verify new collection selected
  await expect(page.getByText('Test Collection')).toBeVisible();

  // Filter artifacts
  await page.selectOption('[data-testid="type-filter"]', 'skill');
  await expect(page.locator('[data-artifact-type]')).toHaveCount(3);

  // Move artifact
  await page.click('[data-testid="artifact-actions-0"]');
  await page.click('text=Move/Copy to Collections');
  // ... continue workflow
});
```

---

## Quality Gates

### UI/UX Checklist
- [ ] All components visually consistent with design
- [ ] Responsive design works on mobile/tablet/desktop
- [ ] View modes switch smoothly without jank
- [ ] Filters work correctly (AND logic)
- [ ] Search is responsive (debounced, < 300ms)
- [ ] Dialogs properly handle focus and escape key
- [ ] Touch targets >= 44px on mobile
- [ ] Hover states provide clear feedback

### Functionality Checklist
- [ ] Collection switcher shows all collections
- [ ] All Collections view aggregates correctly
- [ ] Filters persist during view mode changes
- [ ] Move/Copy operations are transactional
- [ ] Delete operations require confirmation
- [ ] All error states handled gracefully
- [ ] Loading states show while data fetches
- [ ] Keyboard navigation works everywhere

### Accessibility Checklist
- [ ] All interactive elements keyboard accessible
- [ ] ARIA labels on all buttons/dialogs
- [ ] Color not sole means of information
- [ ] Focus indicators visible
- [ ] Screen reader announcements for state changes
- [ ] Semantic HTML used
- [ ] Contrast ratios >= 4.5:1

### Performance Checklist
- [ ] Page load < 2 seconds (cached)
- [ ] Filter/search debounced (< 300ms user-facing delay)
- [ ] No unnecessary re-renders (React Profiler verified)
- [ ] Images lazy-loaded
- [ ] Code splitting used for heavy components
- [ ] Bundle size monitored

---

## Files to Create

### New Component Files
1. `/skillmeat/web/components/collection/collection-header.tsx` (~80 lines)
2. `/skillmeat/web/components/collection/collection-toolbar.tsx` (~100 lines)
3. `/skillmeat/web/components/collection/collection-switcher.tsx` (~120 lines)
4. `/skillmeat/web/components/collection/artifact-grid.tsx` (~80 lines)
5. `/skillmeat/web/components/collection/artifact-list.tsx` (~80 lines)
6. `/skillmeat/web/components/collection/create-collection-dialog.tsx` (~100 lines)
7. `/skillmeat/web/components/collection/edit-collection-dialog.tsx` (~120 lines)
8. `/skillmeat/web/components/collection/move-copy-dialog.tsx` (~120 lines)
9. `/skillmeat/web/components/entity/modal-collections-tab.tsx` (~100 lines)

### Modified Files
1. `/skillmeat/web/app/collection/page.tsx` - Page layout
2. `/skillmeat/web/components/collection/artifact-card.tsx` - Add ellipsis menu
3. `/skillmeat/web/components/entity/unified-entity-modal.tsx` - Add tab

---

## Effort Breakdown

| Task | Hours | Notes |
|------|-------|-------|
| Collection Page Redesign | 12 | View modes, filtering, search, sort |
| Collection Switcher | 6 | Dropdown with create integration |
| All Collections View | 4 | Aggregation logic |
| Create/Edit Dialogs | 8 | CRUD operations, validation |
| Move/Copy Dialog | 6 | Transactional operations |
| Artifact Card Enhancement | 6 | Ellipsis menu, actions |
| Unified Modal Tab | 6 | New tab, integration |
| Testing | 8 | Component, E2E, accessibility |
| **Total** | **56 hours** | ~7 days actual work, ~10 business days calendar |

---

## Success Criteria

Phase 4 is complete when:

1. **Collection Page**: Full redesign with view modes, filtering, search
2. **Collection Switcher**: Works with all collections, "All Collections" option
3. **Dialogs**: Create/edit/delete collections working smoothly
4. **Move/Copy**: Bulk operations with transactional guarantees
5. **Artifact Cards**: Ellipsis menu with all actions
6. **Unified Modal**: New Collections/Groups tab integrated
7. **Testing**: 85%+ component test coverage
8. **Accessibility**: WCAG 2.1 AA compliance verified
9. **Performance**: Page loads < 2 seconds (cached), filters < 300ms
10. **Code Review**: Approved by ui-engineer-enhanced

---

## Orchestration Quick Reference

### Task Delegation Commands

Batch 1 (Parallel):
- **TASK-4.1** → `ui-engineer-enhanced` (3h) - Collection page redesign
- **TASK-4.2** → `ui-engineer-enhanced` (2h) - Collection switcher

Batch 2 (Sequential, after Batch 1):
- **TASK-4.3** → `ui-engineer-enhanced` (2h) - All Collections view
- **TASK-4.4** → `ui-engineer-enhanced` (2h) - Create/Edit dialogs

Batch 3 (Parallel, after Batch 2):
- **TASK-4.5** → `frontend-developer` (1.5h) - Move/Copy dialog
- **TASK-4.6** → `frontend-developer` (2h) - Artifact card enhancement

Batch 4 (Sequential, after Batch 3):
- **TASK-4.7** → `ui-engineer-enhanced` (2h) - Unified modal Collections/Groups tab

---

## Next Phase

Phase 5 (Groups & Deployment Dashboard) depends on Phase 4 being complete. It will:
- Create Grouped View with drag-and-drop
- Implement Manage Groups dialog
- Repurpose /manage as Deployment Dashboard
- Add Deployments tab to unified modal
