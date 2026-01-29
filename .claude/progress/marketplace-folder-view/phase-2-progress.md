---
type: progress
prd: "marketplace-folder-view"
phase: 2
title: "Depth Configuration & Polish"
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
    description: "Depth dropdown works and updates tree correctly"
    status: pending
  - id: "SC-2.2"
    description: "Auto depth detection produces reasonable results for test repositories"
    status: pending
  - id: "SC-2.3"
    description: "Folder counts accurate and update on filter change"
    status: pending
  - id: "SC-2.4"
    description: "Empty folder messages styled consistently"
    status: pending
  - id: "SC-2.5"
    description: "Deep nesting (4+ levels) doesn't break UI"
    status: pending
  - id: "SC-2.6"
    description: "View mode and depth setting persist to localStorage"
    status: pending
  - id: "SC-2.7"
    description: "Visual polish complete; icons and spacing match design system"
    status: pending
  - id: "SC-2.8"
    description: "E2E tests pass (toggle, expand/collapse, filter, import)"
    status: pending
  - id: "SC-2.9"
    description: "Analytics events firing correctly"
    status: pending

tasks:
  - id: "MFV-2.1"
    title: "Depth dropdown component"
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    model: sonnet
    effort: 2
    priority: high
    dependencies: []
    description: "Create FolderDepthControls component with dropdown: Auto, Top Level, 1-3 Levels Deep"

  - id: "MFV-2.2"
    title: "Auto-detection algorithm enhancement"
    status: pending
    assigned_to: ["frontend-developer"]
    model: sonnet
    effort: 2
    priority: high
    dependencies: []
    description: "Refine calculateAutoDepth() to intelligently detect optimal depth from repository structure"

  - id: "MFV-2.3"
    title: "Folder count bubbling"
    status: pending
    assigned_to: ["frontend-developer"]
    model: sonnet
    effort: 2
    priority: high
    dependencies: []
    description: "Show accurate artifact counts on folder nodes; update counts when filters applied"

  - id: "MFV-2.4"
    title: "Empty folder states"
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    model: sonnet
    effort: 1
    priority: medium
    dependencies: []
    description: "Display '(No importable artifacts)' message for empty folders after filtering"

  - id: "MFV-2.5"
    title: "Deep nesting handling"
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    model: sonnet
    effort: 2
    priority: medium
    dependencies: []
    description: "Test and handle 4+ nesting levels; implement breadcrumb or path truncation if needed"

  - id: "MFV-2.6"
    title: "localStorage persistence"
    status: pending
    assigned_to: ["frontend-developer"]
    model: haiku
    effort: 1
    priority: medium
    dependencies: []
    description: "Implement localStorage storage for view mode preference using existing pattern"

  - id: "MFV-2.7"
    title: "URL state sync"
    status: pending
    assigned_to: ["frontend-developer"]
    model: sonnet
    effort: 1
    priority: medium
    dependencies: []
    description: "Save selected depth level to localStorage; restore on page return"

  - id: "MFV-2.8"
    title: "Visual polish pass"
    status: pending
    assigned_to: ["ui-designer"]
    model: sonnet
    effort: 1
    priority: medium
    dependencies: ["MFV-2.4", "MFV-2.5"]
    description: "Review spacing, colors, icon alignment against design system"

  - id: "MFV-2.9"
    title: "E2E tests"
    status: pending
    assigned_to: ["frontend-developer"]
    model: sonnet
    effort: 3
    priority: high
    dependencies: ["MFV-2.1"]
    description: "Write Playwright tests covering folder view toggle, expand/collapse, filters, import"

  - id: "MFV-2.10"
    title: "Analytics integration"
    status: pending
    assigned_to: ["frontend-developer"]
    model: haiku
    effort: 1
    priority: low
    dependencies: []
    description: "Log folder view toggle, folder expand/collapse, depth control changes to analytics"

parallelization:
  batch_1: ["MFV-2.1", "MFV-2.2", "MFV-2.3"]
  batch_2: ["MFV-2.4", "MFV-2.5"]
  batch_3: ["MFV-2.6", "MFV-2.7"]
  batch_4: ["MFV-2.8"]
  batch_5: ["MFV-2.9", "MFV-2.10"]
---

# Phase 2: Depth Configuration & Polish

## Overview

Phase 2 refines the core functionality with depth configuration controls, visual polish, folder count accuracy, and persistence. Users can configure how deep the tree expands initially via dropdown (Auto/TopLevel/1/2/3 Levels). Folder counts are accurate, empty folders show helpful messages, and view preference persists to localStorage. E2E tests verify the complete folder view workflow.

**Duration**: 3 days
**Total Effort**: 16 story points
**Dependencies**: Phase 1 complete

## Tasks

### MFV-2.1: Depth dropdown component

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: sonnet
**Effort**: 2 pts
**Priority**: high

**Description**: Create FolderDepthControls component in toolbar; dropdown with options: Auto, Top Level, 1 Level Deep, 2 Levels, 3 Levels Deep; updates tree on selection.

**Acceptance Criteria**:
- Dropdown renders in toolbar when folder view active
- All options work and update tree immediately
- Tree re-renders with correct depth on selection change
- Selection persists visually (controlled component)

**Files to Create**:
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-depth-controls.tsx`

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/source-toolbar.tsx`

---

### MFV-2.2: Auto-detection algorithm enhancement

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: high

**Description**: Refine `calculateAutoDepth()` to intelligently detect optimal depth; prioritize `root_hint`, scan first 50 entries for depth patterns; return sensible default.

**Acceptance Criteria**:
- Function detects depth from repository structure patterns
- Returns safe default (2-3 levels typically)
- Handles edge cases (flat repos, deep monorepos)
- Consistent results across similar catalogs

**Files to Modify**:
- `skillmeat/web/lib/folder-tree.ts`

---

### MFV-2.3: Folder count bubbling

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: high

**Description**: Show accurate artifact counts on folder nodes (direct children only); update counts when filters applied; include "(N) importable artifacts" format.

**Acceptance Criteria**:
- Count badges render on all folders
- Counts show direct importable artifacts only
- "(0 importable artifacts)" shown for filtered empty folders
- Counts update immediately on filter change

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx`
- `skillmeat/web/lib/folder-tree.ts`

---

### MFV-2.4: Empty folder states

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: sonnet
**Effort**: 1 pt
**Priority**: medium

**Description**: Display helpful message for empty folders: "(No importable artifacts)" with styling matching empty states elsewhere in app.

**Acceptance Criteria**:
- Message shown for folders with no matching items under current filters
- Styled consistently with grid/list empty state
- Message is unobtrusive but informative

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx`

---

### MFV-2.5: Deep nesting handling

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: sonnet
**Effort**: 2 pts
**Priority**: medium

**Description**: Test and handle 4+ nesting levels; implement breadcrumb or path truncation if needed; ensure UI doesn't break under deep nesting.

**Acceptance Criteria**:
- UI remains readable at 5+ levels
- Deep nesting doesn't cause layout issues (overflow, wrapping)
- Visual hierarchy remains clear at all depths
- Consider breadcrumb or path context for deeply nested items

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/catalog-folder.tsx`

---

### MFV-2.6: localStorage persistence

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: haiku
**Effort**: 1 pt
**Priority**: medium

**Description**: Implement localStorage storage for view mode preference; use existing `VIEW_MODE_STORAGE_KEY` pattern; persist folder view selection.

**Acceptance Criteria**:
- View mode saved to localStorage on change
- On page return, folder view restored if previously selected
- Matches existing grid/list persistence pattern

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx`
- `skillmeat/web/lib/hooks/use-folder-tree.ts`

---

### MFV-2.7: URL state sync

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 1 pt
**Priority**: medium

**Description**: Save selected depth level to localStorage (e.g., `folder-depth-setting`); restore on page return.

**Acceptance Criteria**:
- Depth setting persists across page navigation
- On return to source detail page, previously selected depth restored
- Dropdown reflects saved value on load

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-depth-controls.tsx`
- `skillmeat/web/lib/hooks/use-folder-tree.ts`

---

### MFV-2.8: Visual polish pass

**Status**: `pending`
**Assigned**: ui-designer
**Model**: sonnet
**Effort**: 1 pt
**Priority**: medium

**Description**: Review spacing, colors, icon alignment against design system; ensure folder/file icons from Lucide match grid/list; adjust margins, padding, hover states.

**Acceptance Criteria**:
- Visual consistency with existing grid/list components
- Spacing matches design tokens
- Icons clearly indicate folder vs artifact
- Hover states intuitive and consistent

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/artifact-row-folder.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx`

**Dependencies**:
- MFV-2.4: Empty folder states complete
- MFV-2.5: Deep nesting handling complete

---

### MFV-2.9: E2E tests

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 3 pts
**Priority**: high

**Description**: Write Playwright tests covering: toggle to folder view, expand/collapse folders, apply filters, see updated tree, import artifact from tree.

**Acceptance Criteria**:
- Test suite covers critical path: view toggle, folder expansion, filter application, import action
- Tests pass reliably in CI
- Performance within acceptable bounds

**Files to Create**:
- `skillmeat/web/tests/marketplace/folder-view.spec.ts`

**Dependencies**:
- MFV-2.1: Depth controls complete

---

### MFV-2.10: Analytics integration

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: haiku
**Effort**: 1 pt
**Priority**: low

**Description**: Log folder view toggle, folder expand/collapse, depth control changes to analytics; prepare for adoption tracking.

**Acceptance Criteria**:
- Events fired on view toggle (grid/list/folder)
- Events fired on folder expand/collapse
- Events fired on depth change
- Events include context (view mode, folder path, depth setting)

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/source-toolbar.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-depth-controls.tsx`

---

## Quality Gates

- [ ] Depth dropdown works and updates tree correctly
- [ ] Auto depth detection produces reasonable results for test repositories
- [ ] Folder counts accurate and update on filter change
- [ ] Empty folder messages styled consistently
- [ ] Deep nesting (4+ levels) doesn't break UI
- [ ] View mode and depth setting persist to localStorage
- [ ] Visual polish complete; icons and spacing match design system
- [ ] E2E tests pass (toggle, expand/collapse, filter, import)
- [ ] Analytics events firing correctly

---

## Key Files

### New Files
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-depth-controls.tsx`
- `skillmeat/web/tests/marketplace/folder-view.spec.ts`

### Modified Files
- `skillmeat/web/lib/folder-tree.ts`
- `skillmeat/web/lib/hooks/use-folder-tree.ts`
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/source-toolbar.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/artifact-row-folder.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/catalog-folder.tsx`

---

## Notes

Phase 2 focuses on configuration, polish, and testing. No new major components, but significant refinement of Phase 1 work. E2E tests are critical path for Phase 3 validation.
