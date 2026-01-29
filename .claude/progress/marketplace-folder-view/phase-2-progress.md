---
type: progress
prd: "marketplace-folder-view"
phase: 2
title: "Folder Detail Pane & Bulk Import"
status: not_started
started: null
completed: null

progress: 0
completion_estimate: "on-track"

total_tasks: 10
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0

owners: ["ui-engineer-enhanced", "frontend-developer"]
contributors: ["ui-designer"]

blockers: []

success_criteria:
  - id: "SC-2.1"
    description: "Folder detail header displays title, parent chip, description, 'Import All' button"
    status: pending
  - id: "SC-2.2"
    description: "README extraction works; falls back to AI summary if no README"
    status: pending
  - id: "SC-2.3"
    description: "Artifacts grouped by type in right pane with section headers"
    status: pending
  - id: "SC-2.4"
    description: "Type grouping includes all artifact types; counts accurate"
    status: pending
  - id: "SC-2.5"
    description: "'Import All' bulk action works; progress shown; success/error states handled"
    status: pending
  - id: "SC-2.6"
    description: "Empty folder state shown when no artifacts match filters"
    status: pending
  - id: "SC-2.7"
    description: "Filters apply to right pane; counts update reactively"
    status: pending
  - id: "SC-2.8"
    description: "Visual polish complete; panes balanced, consistent spacing"
    status: pending
  - id: "SC-2.9"
    description: "E2E tests pass (folder selection -> right pane display -> bulk import)"
    status: pending
  - id: "SC-2.10"
    description: "View mode and filter state persist to localStorage"
    status: pending

tasks:
  - id: "MFV-2.1"
    title: "Folder detail pane container"
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    model: sonnet
    effort: 2
    priority: high
    dependencies: []
    description: "Create right pane container accepting selected folder; renders folder detail header + artifact list"

  - id: "MFV-2.2"
    title: "Folder detail header"
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    model: opus
    effort: 3
    priority: high
    dependencies: ["MFV-2.1"]
    description: "Create header showing: folder title, parent breadcrumb chip, folder description, 'Import All' button"

  - id: "MFV-2.3"
    title: "README extraction utilities"
    status: pending
    assigned_to: ["frontend-developer"]
    model: sonnet
    effort: 2
    priority: high
    dependencies: []
    description: "Create utility to extract README from folder artifacts; parse markdown content; extract summary section or first paragraph"

  - id: "MFV-2.4"
    title: "'Import All' bulk action"
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    model: opus
    effort: 3
    priority: high
    dependencies: ["MFV-2.2"]
    description: "Implement bulk import button; import all artifacts in selected folder; show progress indicator; handle success/error states"

  - id: "MFV-2.5"
    title: "Artifact type section component"
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    model: sonnet
    effort: 2
    priority: high
    dependencies: []
    description: "Create component showing artifacts grouped by type with section header (e.g., 'Skills (5)', 'Commands (2)')"

  - id: "MFV-2.6"
    title: "Type grouping logic"
    status: pending
    assigned_to: ["frontend-developer"]
    model: sonnet
    effort: 2
    priority: high
    dependencies: ["MFV-2.5"]
    description: "Implement grouping of artifacts by type within folder; handle all artifact types; maintain sort order"

  - id: "MFV-2.7"
    title: "Empty state for folder detail"
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    model: haiku
    effort: 1
    priority: medium
    dependencies: ["MFV-2.1"]
    description: "Show helpful empty state when folder has no importable artifacts under current filters"

  - id: "MFV-2.8"
    title: "Filter integration"
    status: pending
    assigned_to: ["frontend-developer"]
    model: sonnet
    effort: 2
    priority: medium
    dependencies: ["MFV-2.1", "MFV-2.6"]
    description: "Ensure all filters (type, confidence, search, status) apply to artifacts shown in folder detail pane"

  - id: "MFV-2.9"
    title: "Visual polish"
    status: pending
    assigned_to: ["ui-designer"]
    model: sonnet
    effort: 2
    priority: medium
    dependencies: ["MFV-2.1", "MFV-2.2", "MFV-2.3", "MFV-2.4", "MFV-2.5", "MFV-2.6", "MFV-2.7", "MFV-2.8"]
    description: "Review spacing, colors, icon alignment between left/right panes; ensure type section headers consistent"

  - id: "MFV-2.10"
    title: "E2E tests"
    status: pending
    assigned_to: ["frontend-developer"]
    model: sonnet
    effort: 2
    priority: high
    dependencies: ["MFV-2.9"]
    description: "Write Playwright tests: toggle to folder view, select folder, see right pane populate, apply filters, use 'Import All' button"

parallelization:
  batch_1: ["MFV-2.1", "MFV-2.3", "MFV-2.5"]
  batch_2: ["MFV-2.2", "MFV-2.6", "MFV-2.7"]
  batch_3: ["MFV-2.4", "MFV-2.8"]
  batch_4: ["MFV-2.9"]
  batch_5: ["MFV-2.10"]
---

# Phase 2: Folder Detail Pane & Bulk Import

## Overview

Phase 2 builds out the folder detail pane (right side) with rich metadata display, artifact grouping by type, and bulk import functionality. The folder detail header shows title, parent breadcrumb chip, folder description (extracted from README or AI-generated summary), and "Import All" button. Artifacts are grouped by type (Skills, Commands, Agents, etc.) with section headers. Filters apply to the right pane artifacts. E2E tests verify the complete folder view workflow including bulk import.

**Duration**: 3 days
**Total Effort**: 19 story points
**Dependencies**: Phase 1 complete

## Tasks

### MFV-2.1: Folder detail pane container

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: sonnet
**Effort**: 2 pts
**Priority**: high

**Description**: Create right pane container accepting selected folder; renders folder detail header + artifact list; prepare for child components.

**Acceptance Criteria**:
- Pane renders with selected folder data
- Shows placeholder content initially
- Integrated with layout
- Accepts folder selection from left pane

**Files to Create**:
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-pane.tsx`

---

### MFV-2.2: Folder detail header

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: opus
**Effort**: 3 pts
**Priority**: high

**Description**: Create header showing: folder title, parent breadcrumb chip, folder description, "Import All" button. Extract description from folder README or generate AI summary.

**Acceptance Criteria**:
- Header renders folder metadata
- Parent chip clickable (navigates to parent folder)
- "Import All" button functional
- Description displayed

**Files to Create**:
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-header.tsx`

**Dependencies**:
- MFV-2.1: Folder detail pane container

---

### MFV-2.3: README extraction utilities

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: high

**Description**: Create utility to extract README from folder artifacts (if any); parse markdown content; extract summary section or first paragraph.

**Acceptance Criteria**:
- Utility detects README files in folder
- Extracts content
- Falls back to AI summary generation if no README found

**Files to Create**:
- `skillmeat/web/lib/folder-readme-utils.ts`

---

### MFV-2.4: "Import All" bulk action

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: opus
**Effort**: 3 pts
**Priority**: high

**Description**: Implement bulk import button; import all artifacts in selected folder; show progress indicator; handle success/error states.

**Acceptance Criteria**:
- Button imports all artifacts in folder
- Progress shown during import
- Success/error message displayed
- Folder refreshes after completion

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-header.tsx`

**Dependencies**:
- MFV-2.2: Folder detail header

---

### MFV-2.5: Artifact type section component

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: sonnet
**Effort**: 2 pts
**Priority**: high

**Description**: Create component showing artifacts grouped by type with section header (e.g., "Skills (5)", "Commands (2)"); render artifact rows in section.

**Acceptance Criteria**:
- Section header shows type name + count
- Artifacts render below
- Consistent styling with grid/list views
- Collapsible sections (optional)

**Files to Create**:
- `skillmeat/web/app/marketplace/sources/[id]/components/artifact-type-section.tsx`

---

### MFV-2.6: Type grouping logic

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: high

**Description**: Implement grouping of artifacts by type within folder; handle all artifact types (Skill, Command, Agent, MCP Server, Hook); maintain sort order.

**Acceptance Criteria**:
- Artifacts grouped correctly by type
- Grouping includes all types
- Groups render in consistent order
- Empty groups hidden

**Files to Create**:
- `skillmeat/web/lib/artifact-grouping-utils.ts`

**Dependencies**:
- MFV-2.5: Artifact type section component

---

### MFV-2.7: Empty state for folder detail

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: haiku
**Effort**: 1 pt
**Priority**: medium

**Description**: Show helpful empty state when folder has no importable artifacts under current filters.

**Acceptance Criteria**:
- Empty state message shown (e.g., "No importable artifacts in this folder")
- Styled consistently with grid/list empty states

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-pane.tsx`

**Dependencies**:
- MFV-2.1: Folder detail pane container

---

### MFV-2.8: Filter integration

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: medium

**Description**: Ensure all filters (type, confidence, search, status) apply to artifacts shown in folder detail pane; pane updates reactively on filter change.

**Acceptance Criteria**:
- Filters applied to right pane artifacts
- Artifact counts in type sections update
- Empty state shown if no results
- No performance lag

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-pane.tsx`

**Dependencies**:
- MFV-2.1: Folder detail pane container
- MFV-2.6: Type grouping logic

---

### MFV-2.9: Visual polish

**Status**: `pending`
**Assigned**: ui-designer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: medium

**Description**: Review spacing, colors, icon alignment between left/right panes; ensure type section headers consistent; adjust hover states, transitions.

**Acceptance Criteria**:
- Visual consistency across panes
- Spacing matches design tokens
- Type grouping clearly labeled
- Interactions smooth

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-pane.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-header.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/artifact-type-section.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/semantic-tree.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/tree-node.tsx`

**Dependencies**:
- MFV-2.1 through MFV-2.8

---

### MFV-2.10: E2E tests

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: high

**Description**: Write Playwright tests: toggle to folder view, select folder, see right pane populate, apply filters, use "Import All" button, verify import success.

**Acceptance Criteria**:
- Test suite covers: folder selection -> right pane display -> filter application -> bulk import action
- Tests pass reliably in CI

**Files to Create**:
- `skillmeat/web/tests/marketplace/folder-view.spec.ts`

**Dependencies**:
- MFV-2.9: Visual polish

---

## Quality Gates

- [ ] Folder detail header displays title, parent chip, description, "Import All" button
- [ ] README extraction works; falls back to AI summary if no README
- [ ] Artifacts grouped by type in right pane with section headers
- [ ] Type grouping includes all artifact types; counts accurate
- [ ] "Import All" bulk action works; progress shown; success/error states handled
- [ ] Empty folder state shown when no artifacts match filters
- [ ] Filters apply to right pane; counts update reactively
- [ ] Visual polish complete; panes balanced, consistent spacing
- [ ] E2E tests pass (folder selection -> right pane display -> bulk import)
- [ ] View mode and filter state persist to localStorage

---

## Key Files

### New Files
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-pane.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-header.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/artifact-type-section.tsx`
- `skillmeat/web/lib/folder-readme-utils.ts`
- `skillmeat/web/lib/artifact-grouping-utils.ts`
- `skillmeat/web/tests/marketplace/folder-view.spec.ts`

### Modified Files
- `skillmeat/web/app/marketplace/sources/[id]/components/semantic-tree.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/tree-node.tsx`

---

## Notes

Phase 2 focuses on the right pane of the two-pane layout. Key features: folder detail header with metadata, artifact grouping by type, and bulk import functionality. E2E tests are critical path for Phase 3 validation.
