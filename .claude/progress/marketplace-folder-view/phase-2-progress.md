---
type: progress
prd: marketplace-folder-view
phase: 2
title: Folder Detail Pane & Bulk Import
status: completed
started: '2026-01-29T13:30:00Z'
completed: '2026-01-29T14:15:00Z'
progress: 100
completion_estimate: on-track
total_tasks: 13
completed_tasks: 13
in_progress_tasks: 0
blocked_tasks: 0
owners:
- ui-engineer-enhanced
- frontend-developer
contributors:
- ui-designer
blockers: []
success_criteria:
- id: SC-2.1
  description: Folder detail header displays title, parent chip, description, 'Import
    All' button
  status: completed
- id: SC-2.2
  description: README extraction works; falls back to AI summary if no README
  status: completed
- id: SC-2.3
  description: Artifacts grouped by type in right pane with section headers
  status: completed
- id: SC-2.4
  description: Type grouping includes all artifact types; counts accurate
  status: completed
- id: SC-2.5
  description: '''Import All'' bulk action works; progress shown; success/error states
    handled'
  status: completed
- id: SC-2.6
  description: Subfolders section renders at bottom when folder has subfolders
  status: completed
- id: SC-2.7
  description: Subfolder cards show name, count, and navigate on click
  status: completed
- id: SC-2.8
  description: Empty folder state shown when no artifacts match filters
  status: completed
- id: SC-2.9
  description: Filters apply to right pane; counts update reactively
  status: completed
- id: SC-2.10
  description: Visual polish complete; panes balanced, consistent spacing
  status: completed
- id: SC-2.11
  description: E2E tests pass (folder selection -> right pane display -> bulk import)
  status: completed
- id: SC-2.12
  description: View mode and filter state persist to localStorage
  status: completed
tasks:
- id: MFV-2.1
  title: Folder detail pane container
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  model: sonnet
  effort: 2
  priority: high
  dependencies: []
  description: Create right pane container accepting selected folder; renders folder
    detail header + artifact list
- id: MFV-2.2
  title: Folder detail header
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  model: opus
  effort: 3
  priority: high
  dependencies:
  - MFV-2.1
  description: 'Create header showing: folder title, parent breadcrumb chip, folder
    description, ''Import All'' button'
- id: MFV-2.3
  title: README extraction utilities
  status: completed
  assigned_to:
  - frontend-developer
  model: sonnet
  effort: 2
  priority: high
  dependencies: []
  description: Create utility to extract README from folder artifacts; parse markdown
    content; extract summary section or first paragraph
- id: MFV-2.4
  title: '''Import All'' bulk action'
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  model: opus
  effort: 3
  priority: high
  dependencies:
  - MFV-2.2
  description: Implement bulk import button; import all artifacts in selected folder;
    show progress indicator; handle success/error states
- id: MFV-2.5
  title: Artifact type section component
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  model: sonnet
  effort: 2
  priority: high
  dependencies: []
  description: Create component showing artifacts grouped by type with section header
    (e.g., 'Skills (5)', 'Commands (2)')
- id: MFV-2.6
  title: Type grouping logic
  status: completed
  assigned_to:
  - frontend-developer
  model: sonnet
  effort: 2
  priority: high
  dependencies:
  - MFV-2.5
  description: Implement grouping of artifacts by type within folder; handle all artifact
    types; maintain sort order
- id: MFV-2.7
  title: Subfolders section component
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  model: sonnet
  effort: 2
  priority: high
  dependencies:
  - MFV-2.1
  description: Create section rendered at bottom of folder detail pane when folder
    has subfolders; grid layout of subfolder cards; section header 'Subfolders (N)'
- id: MFV-2.8
  title: Subfolder card component
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  model: sonnet
  effort: 2
  priority: high
  dependencies: []
  description: Create card showing folder icon, name, and descendant artifact count;
    click handler to select folder in tree; hover state with folder description preview
- id: MFV-2.9
  title: Subfolder navigation integration
  status: completed
  assigned_to:
  - frontend-developer
  model: sonnet
  effort: 2
  priority: high
  dependencies:
  - MFV-2.7
  - MFV-2.8
  description: Wire subfolder card clicks to tree selection; update detail pane when
    subfolder selected; handle keyboard navigation between panes
- id: MFV-2.10
  title: Empty state for folder detail
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  model: haiku
  effort: 1
  priority: medium
  dependencies:
  - MFV-2.1
  description: Show helpful empty state when folder has no importable artifacts under
    current filters
- id: MFV-2.11
  title: Filter integration
  status: completed
  assigned_to:
  - frontend-developer
  model: sonnet
  effort: 2
  priority: medium
  dependencies:
  - MFV-2.1
  - MFV-2.6
  description: Ensure all filters (type, confidence, search, status) apply to artifacts
    shown in folder detail pane
- id: MFV-2.12
  title: Visual polish
  status: completed
  assigned_to:
  - ui-designer
  model: sonnet
  effort: 2
  priority: medium
  dependencies:
  - MFV-2.1
  - MFV-2.2
  - MFV-2.3
  - MFV-2.4
  - MFV-2.5
  - MFV-2.6
  - MFV-2.7
  - MFV-2.8
  - MFV-2.9
  - MFV-2.10
  - MFV-2.11
  description: Review spacing, colors, icon alignment between left/right panes; ensure
    type section headers consistent
- id: MFV-2.13
  title: E2E tests
  status: completed
  assigned_to:
  - frontend-developer
  model: sonnet
  effort: 2
  priority: high
  dependencies:
  - MFV-2.12
  description: 'Write Playwright tests: toggle to folder view, select folder, see
    right pane populate, apply filters, use ''Import All'' button, navigate via subfolder
    cards'
parallelization:
  batch_1:
  - MFV-2.1
  - MFV-2.3
  - MFV-2.5
  - MFV-2.8
  batch_2:
  - MFV-2.2
  - MFV-2.6
  - MFV-2.7
  - MFV-2.10
  batch_3:
  - MFV-2.4
  - MFV-2.9
  - MFV-2.11
  batch_4:
  - MFV-2.12
  batch_5:
  - MFV-2.13
schema_version: 2
doc_type: progress
feature_slug: marketplace-folder-view
---

# Phase 2: Folder Detail Pane & Bulk Import

## Overview

Phase 2 builds out the folder detail pane (right side) with rich metadata display, artifact grouping by type, subfolder navigation, and bulk import functionality. The folder detail header shows title, parent breadcrumb chip, folder description (extracted from README or AI-generated summary), and "Import All" button. Artifacts are grouped by type (Skills, Commands, Agents, etc.) with section headers. A new Subfolders section at the bottom allows navigation to child folders. Filters apply to the right pane artifacts. E2E tests verify the complete folder view workflow including bulk import and subfolder navigation.

**Duration**: 4 days
**Total Effort**: 28 story points
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

### MFV-2.7: Subfolders section component

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: sonnet
**Effort**: 2 pts
**Priority**: high

**Description**: Create section rendered at bottom of folder detail pane when folder has subfolders; grid layout of subfolder cards; section header "Subfolders (N)".

**Acceptance Criteria**:
- Section only renders when folder has subfolders (hasSubfolders flag)
- Grid layout (2-3 columns responsive)
- Section header shows "Subfolders (N)" with count
- Positioned below artifact type sections
- Not rendered for folders with ONLY direct artifacts

**Files to Create**:
- `skillmeat/web/app/marketplace/sources/[id]/components/subfolders-section.tsx`

**Dependencies**:
- MFV-2.1: Folder detail pane container

---

### MFV-2.8: Subfolder card component

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: sonnet
**Effort**: 2 pts
**Priority**: high

**Description**: Create card showing folder icon, name, and descendant artifact count; click handler to select folder in tree; hover state with folder description preview.

**Acceptance Criteria**:
- Card shows folder icon and name
- Descendant artifact count displayed (totalArtifactCount)
- Click navigates to folder (selects in tree, updates detail pane)
- Hover state shows folder description preview if available
- Keyboard accessible (Enter/Space to select)

**Files to Create**:
- `skillmeat/web/app/marketplace/sources/[id]/components/subfolder-card.tsx`

---

### MFV-2.9: Subfolder navigation integration

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: high

**Description**: Wire subfolder card clicks to tree selection; update detail pane when subfolder selected; handle keyboard navigation between panes.

**Acceptance Criteria**:
- Clicking subfolder card selects folder in left pane tree
- Tree expands to show selected folder
- Detail pane updates to show selected folder content
- Keyboard navigation: Tab between panes, Enter to select subfolder
- Scroll tree to show selected folder if out of view

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-pane.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/subfolders-section.tsx`
- `skillmeat/web/lib/hooks/use-folder-selection.ts`

**Dependencies**:
- MFV-2.7: Subfolders section component
- MFV-2.8: Subfolder card component

---

### MFV-2.10: Empty state for folder detail

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: haiku
**Effort**: 1 pt
**Priority**: medium

**Description**: Show helpful empty state when folder has no importable artifacts under current filters.

**Acceptance Criteria**:
- Empty state message shown (e.g., "No importable artifacts in this folder")
- Styled consistently with grid/list empty states
- For folder with only subfolders: Show subfolders section, no "Import All" button

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-pane.tsx`

**Dependencies**:
- MFV-2.1: Folder detail pane container

---

### MFV-2.11: Filter integration

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

### MFV-2.12: Visual polish

**Status**: `pending`
**Assigned**: ui-designer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: medium

**Description**: Review spacing, colors, icon alignment between left/right panes; ensure type section headers consistent; adjust hover states, transitions for subfolders.

**Acceptance Criteria**:
- Visual consistency across panes
- Spacing matches design tokens
- Type grouping clearly labeled
- Subfolder cards consistent with design system
- Interactions smooth

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-pane.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-header.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/artifact-type-section.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/subfolders-section.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/subfolder-card.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/semantic-tree.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/tree-node.tsx`

**Dependencies**:
- MFV-2.1 through MFV-2.11

---

### MFV-2.13: E2E tests

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: high

**Description**: Write Playwright tests: toggle to folder view, select folder, see right pane populate, apply filters, use "Import All" button, navigate via subfolder cards, verify import success.

**Acceptance Criteria**:
- Test suite covers: folder selection -> right pane display -> filter application -> bulk import action
- Tests cover subfolder navigation: click subfolder card -> tree updates -> detail pane updates
- Tests verify mixed-content folders show both artifact sections and subfolders section
- Tests pass reliably in CI

**Files to Create**:
- `skillmeat/web/tests/marketplace/folder-view.spec.ts`

**Dependencies**:
- MFV-2.12: Visual polish

---

## Quality Gates

- [ ] Folder detail header displays title, parent chip, description, "Import All" button
- [ ] README extraction works; falls back to AI summary if no README
- [ ] Artifacts grouped by type in right pane with section headers
- [ ] Type grouping includes all artifact types; counts accurate
- [ ] "Import All" bulk action works; progress shown; success/error states handled
- [ ] Subfolders section renders at bottom when folder has subfolders
- [ ] Subfolder cards show name, count, and navigate on click
- [ ] Empty folder state shown when no artifacts match filters
- [ ] Filters apply to right pane; counts update reactively
- [ ] Visual polish complete; panes balanced, consistent spacing
- [ ] E2E tests pass (folder selection -> right pane display -> bulk import -> subfolder navigation)
- [ ] View mode and filter state persist to localStorage

---

## Key Files

### New Files
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-pane.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-header.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/artifact-type-section.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/subfolders-section.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/subfolder-card.tsx`
- `skillmeat/web/lib/folder-readme-utils.ts`
- `skillmeat/web/lib/artifact-grouping-utils.ts`
- `skillmeat/web/tests/marketplace/folder-view.spec.ts`

### Modified Files
- `skillmeat/web/app/marketplace/sources/[id]/components/semantic-tree.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/tree-node.tsx`
- `skillmeat/web/lib/hooks/use-folder-selection.ts`

---

## Notes

Phase 2 focuses on the right pane of the two-pane layout. Key features: folder detail header with metadata, artifact grouping by type, subfolder navigation section, and bulk import functionality. The new subfolder navigation allows users to drill down into nested folders from the detail pane. E2E tests are critical path for Phase 3 validation.

### Mixed-Content Folder Handling

- **Folder with ONLY direct artifacts**: Show type sections, no Subfolders section
- **Folder with ONLY subfolders**: Show Subfolders section only, no "Import All" if no direct artifacts
- **Empty folder with subfolders**: Show Subfolders section, "(0)" direct count in tree
- **Mixed folder (direct + subfolders)**: Type sections ABOVE Subfolders section
