---
type: progress
prd: "global-fields-management"
phase: 4
status: pending
progress: 0

tasks:
  - id: "GFM-IMPL-4.1"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    model: "sonnet"

  - id: "GFM-IMPL-4.2"
    status: "pending"
    assigned_to: ["python-backend-engineer", "ui-engineer-enhanced"]
    dependencies: []
    model: "opus"

  - id: "GFM-IMPL-4.3"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["GFM-IMPL-4.1"]
    model: "sonnet"

  - id: "GFM-IMPL-4.4"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["GFM-IMPL-4.1"]
    model: "sonnet"

  - id: "GFM-IMPL-4.5"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["GFM-IMPL-4.1"]
    model: "sonnet"

  - id: "GFM-IMPL-4.6"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["GFM-IMPL-4.3", "GFM-IMPL-4.4", "GFM-IMPL-4.5"]
    model: "sonnet"

  - id: "GFM-IMPL-4.7"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["GFM-IMPL-4.2"]
    model: "sonnet"

parallelization:
  batch_1: ["GFM-IMPL-4.1", "GFM-IMPL-4.2"]
  batch_2: ["GFM-IMPL-4.3", "GFM-IMPL-4.4", "GFM-IMPL-4.5", "GFM-IMPL-4.7"]
  batch_3: ["GFM-IMPL-4.6"]
---

# Phase 4: Marketplace Source Fields

**Duration:** 4 days | **Effort:** 17 points

## Phase Goals

1. Add Marketplace Sources tab to settings page
2. Implement list display for marketplace source fields (Tags, Trust Level, Visibility, Auto Tags)
3. Read-only display for system-managed fields (Auto Tags, Scan Status)
4. Field descriptions and help text

## Tasks

### GFM-IMPL-4.1: Create MarketplaceSourcesTab
**Status:** Pending | **Assigned:** ui-engineer-enhanced | **Estimate:** 3 pts

Add Marketplace Sources tab to FieldsClient; display field list: Tags, Trust Level, Visibility, Auto Tags.

**Acceptance Criteria:**
- Tab appears in ObjectTypeTabs
- Clicking switches to marketplace fields
- Field list displays all 4 fields

---

### GFM-IMPL-4.2: Implement Marketplace Tags CRUD
**Status:** Pending | **Assigned:** python-backend-engineer, ui-engineer-enhanced | **Estimate:** 4 pts

Implement add/edit/remove for Marketplace Source tags (separate from artifact tags).

**Acceptance Criteria:**
- Add/edit/remove dialogs work for marketplace tags
- Stored in MarketplaceSource JSON field
- UI consistent with artifact tags

---

### GFM-IMPL-4.3: Display Trust Level (View-Only)
**Status:** Pending | **Assigned:** ui-engineer-enhanced | **Estimate:** 2 pts

Display Trust Level field in Marketplace Sources tab; mark as view-only; disable edit/remove buttons; show current values.

**Acceptance Criteria:**
- Trust Level field displays with values (High, Medium, Low)
- Edit/remove buttons disabled
- Clear "view-only" indicator

**Dependencies:** GFM-IMPL-4.1

---

### GFM-IMPL-4.4: Display Visibility (View-Only)
**Status:** Pending | **Assigned:** ui-engineer-enhanced | **Estimate:** 2 pts

Display Visibility field in Marketplace Sources tab; mark as view-only; disable edit/remove buttons.

**Acceptance Criteria:**
- Visibility field displays with values (Public, Private)
- Edit/remove buttons disabled
- Clear indicator

**Dependencies:** GFM-IMPL-4.1

---

### GFM-IMPL-4.5: Display Auto Tags (View-Only)
**Status:** Pending | **Assigned:** ui-engineer-enhanced | **Estimate:** 2 pts

Display Auto Tags field in Marketplace Sources tab; mark as view-only; explain system-generated.

**Acceptance Criteria:**
- Auto Tags field displays as read-only
- Shows system-generated tags from GitHub topics
- No edit/remove buttons

**Dependencies:** GFM-IMPL-4.1

---

### GFM-IMPL-4.6: Add Field Descriptions & Help Text
**Status:** Pending | **Assigned:** ui-engineer-enhanced | **Estimate:** 2 pts

Add tooltips/help text for each field explaining purpose, constraints, read-only rationale.

**Acceptance Criteria:**
- Hovering over field shows description
- Auto Tags tooltip explains system-generated
- Visible on desktop, accessible on mobile

**Dependencies:** GFM-IMPL-4.3, GFM-IMPL-4.4, GFM-IMPL-4.5

---

### GFM-IMPL-4.7: Integration Test: Marketplace Fields
**Status:** Pending | **Assigned:** python-backend-engineer | **Estimate:** 2 pts

Test marketplace source field listing and read-only enforcement via API.

**Acceptance Criteria:**
- Tests verify: marketplace fields endpoint returns correct structure
- Edit/remove attempts fail for read-only fields

**Dependencies:** GFM-IMPL-4.2

---

## Quality Gates

- [ ] Marketplace Sources tab displays correctly
- [ ] All 4 fields visible and properly categorized (editable vs. read-only)
- [ ] Tag CRUD works for marketplace tags
- [ ] Read-only fields clearly marked
- [ ] Help text visible and accessible

## Dependencies

- Phase 2 FieldsClient layout
- Phase 3 tag CRUD implementation
- MarketplaceSource model schema

## Notes

Batch 1 (tab + marketplace tags) can run in parallel. Batch 2 (all view-only fields + integration tests) can run in parallel after tab is ready.
