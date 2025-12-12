---
type: progress
prd: "collections-navigation"
phase: 4
title: "Collection Features - Pages, Dialogs, UI Components"
status: "pending"
overall_progress: 0
total_tasks: 7
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
owners: ["ui-engineer-enhanced"]
contributors: ["frontend-developer"]

tasks:
  - id: "TASK-4.1"
    name: "Collection Page Redesign"
    description: "Redesign collection page with view modes, filtering, search, and sorting"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "3h"
    priority: "high"

  - id: "TASK-4.2"
    name: "Collection Switcher Component"
    description: "Dropdown component to select active collection"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "2h"
    priority: "high"

  - id: "TASK-4.3"
    name: "All Collections View"
    description: "Aggregated view showing artifacts across all collections"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "2h"
    priority: "high"

  - id: "TASK-4.4"
    name: "Create/Edit Collection Dialogs"
    description: "CRUD dialogs for collection management with form validation"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "2h"
    priority: "high"

  - id: "TASK-4.5"
    name: "Move/Copy to Collections Dialog"
    description: "Bulk operations dialog for moving/copying artifacts"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["TASK-4.4"]
    estimated_effort: "1.5h"
    priority: "medium"

  - id: "TASK-4.6"
    name: "Artifact Card Enhancement"
    description: "Add ellipsis menu to artifact cards with collection actions"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: []
    estimated_effort: "2h"
    priority: "high"

  - id: "TASK-4.7"
    name: "Unified Modal Collections/Groups Tab"
    description: "Add Collections & Groups tab to artifact modal showing membership"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.4"]
    estimated_effort: "2h"
    priority: "high"

parallelization:
  batch_1: ["TASK-4.1", "TASK-4.2", "TASK-4.3", "TASK-4.4", "TASK-4.6"]
  batch_2: ["TASK-4.5", "TASK-4.7"]
  critical_path: ["TASK-4.1", "TASK-4.4", "TASK-4.7"]
  estimated_total_time: "1.5w"

blockers: []

success_criteria:
  - id: "SC-1"
    description: "Collection page supports grid/list/grouped view modes"
    status: "pending"
  - id: "SC-2"
    description: "Collection switcher dropdown works with keyboard navigation"
    status: "pending"
  - id: "SC-3"
    description: "All Collections view aggregates artifacts correctly"
    status: "pending"
  - id: "SC-4"
    description: "Create/Edit dialogs validate input and handle errors"
    status: "pending"
  - id: "SC-5"
    description: "Move/Copy dialog supports multi-select and batch operations"
    status: "pending"
  - id: "SC-6"
    description: "Artifact card menu shows context-aware actions"
    status: "pending"
  - id: "SC-7"
    description: "Modal tab displays current memberships with add/remove"
    status: "pending"
  - id: "SC-8"
    description: "All components follow Radix UI + shadcn patterns"
    status: "pending"

files_modified: []
---

# collections-navigation - Phase 4: Collection Features

**Phase**: 4 of 6
**Status**: Pending (0% complete)
**Owner**: ui-engineer-enhanced
**Contributors**: frontend-developer
**Dependencies**: Phase 3 (Frontend Foundation)

---

## Phase Objective

Build collection-focused UI components including collection pages, switcher, dialogs, and artifact card enhancements. This phase delivers the core collection browsing and management experience.

---

## Orchestration Quick Reference

**Batch 1** (Parallel - Core Components):
- TASK-4.1 → `ui-engineer-enhanced` (3h) - Collection page redesign
- TASK-4.2 → `ui-engineer-enhanced` (2h) - Collection switcher
- TASK-4.3 → `ui-engineer-enhanced` (2h) - All Collections view
- TASK-4.4 → `ui-engineer-enhanced` (2h) - Create/Edit dialogs
- TASK-4.6 → `frontend-developer` (2h) - Artifact card enhancement

**Batch 2** (Parallel - Dependent Components, after Batch 1):
- TASK-4.5 → `frontend-developer` (1.5h) - Move/Copy dialog
- TASK-4.7 → `ui-engineer-enhanced` (2h) - Unified modal tab

### Task Delegation Commands

```
# Batch 1 (Parallel)
Task("ui-engineer-enhanced", "TASK-4.1: Redesign collection page (/collections/[id]) with view mode toggle (grid/list/grouped), filters (type, status, tags), search bar, sort options (name, date, type). Use existing ArtifactCard in grid/list modes. Include header with collection name, description, artifact count. Files: /skillmeat/web/app/collections/[id]/page.tsx, components/collections/CollectionView.tsx")

Task("ui-engineer-enhanced", "TASK-4.2: Create CollectionSwitcher dropdown component using Radix Select. Show current collection name with ChevronDown icon. Dropdown lists all collections (with icons), All Collections option at top, divider, Manage Collections action at bottom. Keyboard navigation support. Updates CollectionContext on selection. File: /skillmeat/web/components/collections/CollectionSwitcher.tsx")

Task("ui-engineer-enhanced", "TASK-4.3: Create All Collections view page (/collections) showing aggregated artifacts from all collections. Display collection badges on each artifact card. Include same filters/search/sort as single collection view. Summary stats at top (total collections, total artifacts, recent activity). File: /skillmeat/web/app/collections/page.tsx")

Task("ui-engineer-enhanced", "TASK-4.4: Create CreateCollectionDialog and EditCollectionDialog components using Radix Dialog. Form fields: name (required, 1-255 chars), description (optional, textarea). Validation with react-hook-form and zod. Integrates with useCreateCollection and useUpdateCollection hooks. Toast notifications on success/error. Files: /skillmeat/web/components/collections/CreateCollectionDialog.tsx, EditCollectionDialog.tsx")

Task("frontend-developer", "TASK-4.6: Enhance ArtifactCard component with ellipsis menu (three dots) in top-right corner using Radix DropdownMenu. Menu items: Add to Collection (submenu), Remove from Collection (if in collection view), Move to Collection (submenu), Copy to Collection (submenu), divider, View Details, Deploy. Context-aware based on current view. File: /skillmeat/web/components/artifacts/ArtifactCard.tsx")

# Batch 2 (Parallel, after Batch 1)
Task("frontend-developer", "TASK-4.5: Create MoveArtifactsDialog and CopyArtifactsDialog components using Radix Dialog. Show list of collections with radio select (move) or checkboxes (copy). Support bulk operations on multiple artifacts. Validation: target collection must exist and differ from source. Integrates with useMoveArtifacts and useCopyArtifacts hooks. Loading states during operation. Files: /skillmeat/web/components/collections/MoveArtifactsDialog.tsx, CopyArtifactsDialog.tsx")

Task("ui-engineer-enhanced", "TASK-4.7: Add Collections & Groups tab to artifact modal showing: Collections this artifact belongs to (with badges and remove button), Groups within each collection (nested list), Add to Collection button opens dialog, Add to Group submenu per collection. Integrates with CollectionContext and hooks. Real-time updates on add/remove. File: /skillmeat/web/components/artifacts/ArtifactModal.tsx - add new tab")
```

---

## Task Details

### TASK-4.1: Collection Page Redesign
- **Status**: pending
- **Assigned**: ui-engineer-enhanced
- **Estimated Effort**: 3h
- **Priority**: high

**Description**: Redesign collection page with view modes, filtering, search, and sorting

**Acceptance Criteria**:
- [ ] Route: `/collections/[id]` displays single collection
- [ ] Header: Collection name, description, artifact count, Edit/Delete buttons
- [ ] View mode toggle: Grid (default), List, Grouped (by type or group)
- [ ] Filters: Type (skill/agent/command), Status, Tags (multi-select)
- [ ] Search bar with debounced input
- [ ] Sort dropdown: Name (A-Z, Z-A), Date Added, Type
- [ ] Uses ArtifactCard component for grid/list views
- [ ] Empty state when no artifacts match filters
- [ ] Responsive design (mobile-first)
- [ ] Loading skeleton while fetching

**Files**: `/skillmeat/web/app/collections/[id]/page.tsx`, `/skillmeat/web/components/collections/CollectionView.tsx`

---

### TASK-4.2: Collection Switcher Component
- **Status**: pending
- **Assigned**: ui-engineer-enhanced
- **Estimated Effort**: 2h
- **Priority**: high

**Description**: Dropdown component to select active collection

**Acceptance Criteria**:
- [ ] Uses Radix Select component
- [ ] Trigger shows current collection name with ChevronDown icon
- [ ] Dropdown content:
  - [ ] "All Collections" option at top
  - [ ] Divider
  - [ ] List of collections (alphabetical, with icons)
  - [ ] Divider
  - [ ] "Manage Collections..." action (opens dialog)
- [ ] Keyboard navigation (arrow keys, Enter, Escape)
- [ ] Updates CollectionContext.currentCollection on selection
- [ ] Highlight current selection
- [ ] Maximum height with scroll if many collections

**Files**: `/skillmeat/web/components/collections/CollectionSwitcher.tsx`

---

### TASK-4.3: All Collections View
- **Status**: pending
- **Assigned**: ui-engineer-enhanced
- **Estimated Effort**: 2h
- **Priority**: high

**Description**: Aggregated view showing artifacts across all collections

**Acceptance Criteria**:
- [ ] Route: `/collections` displays all artifacts
- [ ] Header: "All Collections" title, summary stats
- [ ] Stats: Total collections count, total artifacts count, recent activity
- [ ] Each artifact card shows collection badges (which collections it belongs to)
- [ ] Same filters/search/sort as single collection view
- [ ] View mode toggle (grid/list)
- [ ] Click collection badge navigates to that collection
- [ ] Empty state when no collections exist
- [ ] Loading skeleton while fetching

**Files**: `/skillmeat/web/app/collections/page.tsx`

---

### TASK-4.4: Create/Edit Collection Dialogs
- **Status**: pending
- **Assigned**: ui-engineer-enhanced
- **Estimated Effort**: 2h
- **Priority**: high

**Description**: CRUD dialogs for collection management with form validation

**Acceptance Criteria**:
- [ ] CreateCollectionDialog with form fields: name (required), description (optional)
- [ ] EditCollectionDialog with same fields pre-populated
- [ ] Form validation: name (1-255 chars), description (optional)
- [ ] Uses react-hook-form with zod schema
- [ ] Integrates with useCreateCollection and useUpdateCollection hooks
- [ ] Loading state during submission (disabled form, spinner)
- [ ] Error handling: display validation errors inline
- [ ] Success: Toast notification, close dialog, invalidate cache
- [ ] Cancel button clears form
- [ ] Keyboard shortcuts: Enter (submit), Escape (cancel)

**Files**: `/skillmeat/web/components/collections/CreateCollectionDialog.tsx`, `/skillmeat/web/components/collections/EditCollectionDialog.tsx`

---

### TASK-4.5: Move/Copy to Collections Dialog
- **Status**: pending
- **Assigned**: frontend-developer
- **Estimated Effort**: 1.5h
- **Priority**: medium
- **Dependencies**: TASK-4.4

**Description**: Bulk operations dialog for moving/copying artifacts

**Acceptance Criteria**:
- [ ] MoveArtifactsDialog shows list of collections (radio select)
- [ ] CopyArtifactsDialog shows list of collections (checkboxes for multi-select)
- [ ] Supports bulk operations on multiple artifacts (array of IDs)
- [ ] Validation: Target collection must exist and differ from source (move only)
- [ ] Integrates with useMoveArtifacts and useCopyArtifacts hooks
- [ ] Loading state during operation (progress indicator)
- [ ] Success: Toast notification with count, close dialog, cache invalidation
- [ ] Error handling: Display error message, keep dialog open
- [ ] Shows artifact count in dialog title

**Files**: `/skillmeat/web/components/collections/MoveArtifactsDialog.tsx`, `/skillmeat/web/components/collections/CopyArtifactsDialog.tsx`

---

### TASK-4.6: Artifact Card Enhancement
- **Status**: pending
- **Assigned**: frontend-developer
- **Estimated Effort**: 2h
- **Priority**: high

**Description**: Add ellipsis menu to artifact cards with collection actions

**Acceptance Criteria**:
- [ ] Ellipsis menu (three dots) in top-right corner of ArtifactCard
- [ ] Uses Radix DropdownMenu component
- [ ] Menu items (context-aware):
  - [ ] "Add to Collection" → Opens submenu with collections list
  - [ ] "Remove from Collection" (only in collection view)
  - [ ] "Move to Collection" → Opens submenu with collections list
  - [ ] "Copy to Collection" → Opens submenu with collections list
  - [ ] Divider
  - [ ] "View Details" → Opens artifact modal
  - [ ] "Deploy" → Opens deployment dialog
- [ ] Submenus show all collections (alphabetical)
- [ ] Clicking submenu item performs action immediately
- [ ] Toast notification on success
- [ ] Keyboard navigation support

**Files**: `/skillmeat/web/components/artifacts/ArtifactCard.tsx`

---

### TASK-4.7: Unified Modal Collections/Groups Tab
- **Status**: pending
- **Assigned**: ui-engineer-enhanced
- **Estimated Effort**: 2h
- **Priority**: high
- **Dependencies**: TASK-4.4

**Description**: Add Collections & Groups tab to artifact modal showing membership

**Acceptance Criteria**:
- [ ] New "Collections & Groups" tab in ArtifactModal (alongside Details, Deployments)
- [ ] Display section: "This artifact is in:"
  - [ ] List of collections (badges with X to remove)
  - [ ] Nested list of groups within each collection (with X to remove)
- [ ] "Add to Collection" button opens dialog with collection select
- [ ] "Add to Group" button shows submenu per collection
- [ ] Real-time updates: Membership changes reflect immediately
- [ ] Integrates with useCollectionContext, useRemoveArtifactFromCollection, useRemoveArtifactFromGroup
- [ ] Empty state: "Not in any collections. Add to collection to organize."
- [ ] Loading state while fetching memberships

**Files**: `/skillmeat/web/components/artifacts/ArtifactModal.tsx`

---

## Progress Summary

**Completed**: 0/7 tasks (0%)
**In Progress**: 0/7 tasks
**Blocked**: 0/7 tasks
**Pending**: 7/7 tasks

---

## Key UI Patterns

### Component Library
- All dialogs use Radix Dialog primitive
- All dropdowns use Radix DropdownMenu or Select
- Follow shadcn component patterns
- Consistent spacing with Tailwind utility classes

### Form Handling
- react-hook-form for all forms
- zod for validation schemas
- Inline error messages
- Disabled state during submission

### Loading States
- Skeleton components during data fetching
- Spinners during mutations
- Disabled buttons during operations
- Progress indicators for bulk operations

---

## Testing Requirements

### Component Tests
**Files**: `/skillmeat/web/components/collections/__tests__/*.test.tsx`

- CollectionSwitcher dropdown behavior
- Create/Edit dialog form validation
- Move/Copy dialog bulk operations
- Artifact card menu actions
- Modal tab membership display

### Integration Tests
**File**: `/skillmeat/web/app/collections/__tests__/page.test.tsx`

- Collection page filters and search
- View mode switching
- All Collections aggregation

---

## Phase Completion Criteria

Phase 4 is complete when:

1. **Collection Page**: View modes, filters, search, sort working
2. **Switcher**: Collection switcher dropdown functional
3. **All Collections**: Aggregated view displays correctly
4. **Dialogs**: Create/Edit dialogs with validation
5. **Bulk Ops**: Move/Copy dialogs support multi-select
6. **Card Menu**: Artifact cards have context-aware actions
7. **Modal Tab**: Collections & Groups tab shows membership
8. **Design Consistency**: All components follow Radix + shadcn patterns
9. **Accessibility**: Keyboard navigation and ARIA labels
10. **Testing**: Component tests for all major features
11. **Code Review**: Approved by UI lead
