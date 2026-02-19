---
type: progress
prd: global-fields-management
phase: 2
status: pending
progress: 0
tasks:
- id: GFM-IMPL-2.1
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  model: sonnet
- id: GFM-IMPL-2.2
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - GFM-IMPL-2.1
  model: opus
- id: GFM-IMPL-2.3
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - GFM-IMPL-2.2
  model: opus
- id: GFM-IMPL-2.4
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - GFM-IMPL-2.2
  model: opus
- id: GFM-IMPL-2.5
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - GFM-IMPL-2.2
  model: sonnet
- id: GFM-IMPL-2.6
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - GFM-IMPL-2.2
  model: sonnet
- id: GFM-IMPL-2.7
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  model: opus
- id: GFM-IMPL-2.8
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - GFM-IMPL-2.7
  model: sonnet
parallelization:
  batch_1:
  - GFM-IMPL-2.1
  - GFM-IMPL-2.7
  batch_2:
  - GFM-IMPL-2.2
  batch_3:
  - GFM-IMPL-2.3
  - GFM-IMPL-2.4
  - GFM-IMPL-2.5
  - GFM-IMPL-2.6
  - GFM-IMPL-2.8
schema_version: 2
doc_type: progress
feature_slug: global-fields-management
---

# Phase 2: Frontend Core & Settings Page

**Duration:** 5 days | **Effort:** 31 points

## Phase Goals

1. Create `/settings/fields` page structure with object type tabs
2. Implement core UI components (Tabs, Sidebar, Options List)
3. Integrate with TanStack Query for data fetching
4. Build form components for Add/Edit dialogs
5. Error handling and loading states

## Tasks

### GFM-IMPL-2.1: Create Settings Fields Page
**Status:** Pending | **Assigned:** ui-engineer-enhanced | **Estimate:** 3 pts

Create `/settings/fields` page (server component) that loads initial data; render FieldsClient (client component).

**Acceptance Criteria:**
- Page loads at `/settings/fields`
- Header displays "Global Fields Management"
- Passes props to FieldsClient

---

### GFM-IMPL-2.2: Create FieldsClient Layout
**Status:** Pending | **Assigned:** ui-engineer-enhanced | **Estimate:** 5 pts

Implement FieldsClient component with: ObjectTypeTabs (Artifacts, Marketplace Sources), FieldSidebar (field list), FieldOptionsContent (options + actions).

**Acceptance Criteria:**
- Tabs switch smoothly
- Sidebar updates when tab changes
- Content area displays field options
- Responsive layout

**Dependencies:** GFM-IMPL-2.1

---

### GFM-IMPL-2.3: Create FieldOptionsList
**Status:** Pending | **Assigned:** ui-engineer-enhanced | **Estimate:** 4 pts

Build options list component displaying: name, color (if applicable), usage count, Edit/Remove buttons; pagination support.

**Acceptance Criteria:**
- List renders with row layout
- Edit/remove buttons functional
- Usage count displayed
- Pagination cursor visible

**Dependencies:** GFM-IMPL-2.2

---

### GFM-IMPL-2.4: Create AddOptionDialog
**Status:** Pending | **Assigned:** ui-engineer-enhanced | **Estimate:** 4 pts

Build dialog for adding field options: name input, optional color picker (for tags), form validation, submit button.

**Acceptance Criteria:**
- Dialog opens/closes
- Validates name (not empty), color (hex or empty)
- Shows validation errors inline
- Disables submit on invalid

**Dependencies:** GFM-IMPL-2.2

---

### GFM-IMPL-2.5: Create EditOptionDialog
**Status:** Pending | **Assigned:** ui-engineer-enhanced | **Estimate:** 3 pts

Build dialog for editing field options: pre-fill current values, form validation, submit button.

**Acceptance Criteria:**
- Dialog pre-fills name and color
- Allows editing
- Validates same as add dialog
- Submit updates option

**Dependencies:** GFM-IMPL-2.2

---

### GFM-IMPL-2.6: Create RemoveConfirmDialog
**Status:** Pending | **Assigned:** ui-engineer-enhanced | **Estimate:** 3 pts

Build confirmation dialog showing: usage count, cascade warning (for tags), confirm/cancel buttons.

**Acceptance Criteria:**
- Shows usage count
- Warns if cascade will affect records
- Confirm button calls delete API

**Dependencies:** GFM-IMPL-2.2

---

### GFM-IMPL-2.7: Setup TanStack Query Hooks
**Status:** Pending | **Assigned:** ui-engineer-enhanced | **Estimate:** 5 pts

Create custom hooks: useFieldOptions(), useAddFieldOption(), useUpdateFieldOption(), useDeleteFieldOption() with error handling.

**Acceptance Criteria:**
- Hooks fetch from /api/v1/fields
- Mutations handle create/update/delete
- Refetch on success
- Error states captured

---

### GFM-IMPL-2.8: Error Handling & UX
**Status:** Pending | **Assigned:** ui-engineer-enhanced | **Estimate:** 3 pts

Implement error display: inline form validation, toast notifications for API failures, loading skeletons.

**Acceptance Criteria:**
- Form validation shows immediately
- API errors show toast with friendly message
- Loading states visible during operations

**Dependencies:** GFM-IMPL-2.7

---

## Quality Gates

- [ ] Page loads without errors; all components render correctly
- [ ] Form validation prevents invalid submissions
- [ ] Error messages are user-friendly and actionable
- [ ] TanStack Query caching works (verified in DevTools)
- [ ] Responsive layout tested on desktop and tablet

## Dependencies

- Phase 1 API endpoints complete
- shadcn/ui components (Tabs, Card, Button, Dialog, Input)
- Existing tag-editor styling patterns
- TanStack Query v5

## Notes

Batch 1 (page + hooks) can run in parallel. Batch 3 (all dialogs + error handling) can run in parallel after layout is complete.
