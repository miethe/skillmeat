---
type: progress
prd: global-fields-management
phase: 3
status: pending
progress: 0
tasks:
- id: GFM-IMPL-3.1
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  model: sonnet
- id: GFM-IMPL-3.2
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  model: sonnet
- id: GFM-IMPL-3.3
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  model: sonnet
- id: GFM-IMPL-3.4
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: opus
- id: GFM-IMPL-3.5
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - GFM-IMPL-3.4
  model: sonnet
- id: GFM-IMPL-3.6
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - GFM-IMPL-3.4
  - GFM-IMPL-3.5
  model: sonnet
- id: GFM-IMPL-3.7
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - GFM-IMPL-3.1
  - GFM-IMPL-3.2
  - GFM-IMPL-3.3
  model: opus
parallelization:
  batch_1:
  - GFM-IMPL-3.1
  - GFM-IMPL-3.2
  - GFM-IMPL-3.3
  - GFM-IMPL-3.4
  batch_2:
  - GFM-IMPL-3.5
  batch_3:
  - GFM-IMPL-3.6
  - GFM-IMPL-3.7
schema_version: 2
doc_type: progress
feature_slug: global-fields-management
---

# Phase 3: Tags CRUD Implementation

**Duration:** 5 days | **Effort:** 21 points

## Phase Goals

1. Integrate Phase 2 UI with Phase 1 API for tags
2. Implement full CRUD workflow for tags (Create, Read, Update, Delete)
3. Cascade delete with artifact cleanup
4. Tag normalization and validation
5. E2E test for tag management

## Tasks

### GFM-IMPL-3.1: Wire AddOptionDialog for Tags
**Status:** Pending | **Assigned:** ui-engineer-enhanced | **Estimate:** 3 pts

Connect AddOptionDialog to useAddFieldOption() hook; normalize tag name via API; handle API errors (409 duplicates, 422 validation).

**Acceptance Criteria:**
- Add tag dialog opens
- User enters name, optional color
- Submit normalizes and creates
- Duplicates rejected with error
- Success refreshes list

---

### GFM-IMPL-3.2: Wire EditOptionDialog for Tags
**Status:** Pending | **Assigned:** ui-engineer-enhanced | **Estimate:** 2 pts

Connect EditOptionDialog to useUpdateFieldOption() hook; pre-fill current values; submit updates tag.

**Acceptance Criteria:**
- Edit dialog pre-fills name and color
- User modifies
- Submit updates
- Success refreshes list

---

### GFM-IMPL-3.3: Wire RemoveConfirmDialog for Tags
**Status:** Pending | **Assigned:** ui-engineer-enhanced | **Estimate:** 3 pts

Connect RemoveConfirmDialog to useDeleteFieldOption() hook; validate in-use before deleting; cascade removes from artifacts.

**Acceptance Criteria:**
- Remove dialog shows usage count
- Confirm triggers delete
- Cascade deletes tag from all artifacts
- Success refreshes list

---

### GFM-IMPL-3.4: Implement Cascade Delete Service
**Status:** Pending | **Assigned:** python-backend-engineer | **Estimate:** 3 pts

Extend FieldsService.delete_field_option() to cascade-delete tags from artifacts; log cascade operations.

**Acceptance Criteria:**
- delete_field_option() for tags calls TagService.delete_tag()
- Logs cascade with trace_id
- Returns cascade_count

---

### GFM-IMPL-3.5: Tag Normalization & Validation
**Status:** Pending | **Assigned:** python-backend-engineer | **Estimate:** 2 pts

Verify tag normalization (trim → lowercase → underscores) applied via FieldsService/TagService; reject duplicates; validate color format.

**Acceptance Criteria:**
- Tags normalize correctly (e.g., "Python 3" → "python-3")
- Duplicates rejected (409)
- Colors validate hex format

**Dependencies:** GFM-IMPL-3.4

---

### GFM-IMPL-3.6: Integration Test: Tag CRUD
**Status:** Pending | **Assigned:** python-backend-engineer | **Estimate:** 4 pts

Write tests covering tag add/edit/remove workflow via API; cascade validation; error cases.

**Acceptance Criteria:**
- Tests verify: create tag, duplicate rejection, update tag, delete tag, cascade artifact cleanup
- All status codes correct

**Dependencies:** GFM-IMPL-3.4, GFM-IMPL-3.5

---

### GFM-IMPL-3.7: E2E Test: Tag Management
**Status:** Pending | **Assigned:** ui-engineer-enhanced | **Estimate:** 4 pts

Write Playwright test for full tag management flow: add tag, verify in list, edit tag, remove tag, verify cascade.

**Acceptance Criteria:**
- E2E covers: navigate to fields page, add tag, check list updates, edit tag, verify edit, remove tag, verify removal

**Dependencies:** GFM-IMPL-3.1, GFM-IMPL-3.2, GFM-IMPL-3.3

---

## Quality Gates

- [ ] All tag CRUD operations work end-to-end
- [ ] Cascade delete removes tags from all linked artifacts
- [ ] Duplicate tag names rejected
- [ ] Tag normalization consistent with existing service
- [ ] E2E test passes in CI/CD pipeline

## Dependencies

- Phase 1 FieldsService complete
- Phase 2 UI components complete
- TagService.delete_tag() cascade logic

## Notes

Batch 1 (all UI wiring + cascade service) can run in parallel. This is where frontend meets backend.
