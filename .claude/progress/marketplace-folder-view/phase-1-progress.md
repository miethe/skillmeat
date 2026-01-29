---
type: progress
prd: "marketplace-folder-view"
phase: 1
title: "Two-Pane Layout & Semantic Tree"
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
contributors: []

blockers: []

success_criteria:
  - id: "SC-1.1"
    description: "Tree builder + semantic filtering utilities tested (>80% coverage)"
    status: pending
  - id: "SC-1.2"
    description: "Two-pane layout renders correctly with proper proportions (25% left, 75% right)"
    status: pending
  - id: "SC-1.3"
    description: "Semantic tree displays only intermediate folders (roots/leafs excluded)"
    status: pending
  - id: "SC-1.4"
    description: "Folder view button appears in toolbar and toggles layout correctly"
    status: pending
  - id: "SC-1.5"
    description: "First folder auto-selects on folder view toggle; right pane populates"
    status: pending
  - id: "SC-1.6"
    description: "Folder selection works; tree node selection state visual feedback"
    status: pending
  - id: "SC-1.7"
    description: "No console errors; malformed paths handled gracefully"
    status: pending
  - id: "SC-1.8"
    description: "Performance baseline: tree renders for 500 items in <300ms"
    status: pending

tasks:
  - id: "MFV-1.1"
    title: "Tree builder utilities"
    status: pending
    assigned_to: ["frontend-developer"]
    model: sonnet
    effort: 2
    priority: critical
    dependencies: []
    description: "Create buildFolderTree() function to convert flat CatalogEntry[] to nested tree structure with maxDepth parameter"

  - id: "MFV-1.2"
    title: "Semantic filtering utilities"
    status: pending
    assigned_to: ["frontend-developer"]
    model: sonnet
    effort: 2
    priority: critical
    dependencies: []
    description: "Create isSemanticFolder() to exclude root folders (plugins/, src/, skills/) and leaf containers (commands/, agents/, mcp_servers/); implement smart tree filtering"

  - id: "MFV-1.3"
    title: "useFolderSelection hook"
    status: pending
    assigned_to: ["frontend-developer"]
    model: sonnet
    effort: 2
    priority: high
    dependencies: ["MFV-1.1"]
    description: "Create React hook managing folder selection state (selected folder path, expanded folders); return selection + setSelected() callback"

  - id: "MFV-1.4"
    title: "Two-pane layout component"
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    model: opus
    effort: 3
    priority: high
    dependencies: []
    description: "Create two-pane container layout with left pane (25%, semantic tree) and right pane (75%, folder detail). Manage layout, responsive behavior"

  - id: "MFV-1.5"
    title: "Semantic tree component"
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    model: opus
    effort: 3
    priority: high
    dependencies: ["MFV-1.2", "MFV-1.3"]
    description: "Create left pane semantic navigation tree; render folders filtered by semantic rules; support expand/collapse; integrate folder selection"

  - id: "MFV-1.6"
    title: "Tree node component"
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    model: sonnet
    effort: 2
    priority: high
    dependencies: []
    description: "Create individual tree folder item with: folder icon, folder name, expand/collapse chevron, count badge; integrate with selection state"

  - id: "MFV-1.7"
    title: "Toolbar folder toggle"
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    model: sonnet
    effort: 1
    priority: medium
    dependencies: []
    description: "Add 'Folder' button to view mode toggle in SourceToolbar; button toggles between grid/list/folder modes"

  - id: "MFV-1.8"
    title: "Page integration"
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    model: sonnet
    effort: 2
    priority: medium
    dependencies: ["MFV-1.4", "MFV-1.5"]
    description: "Integrate two-pane layout into source detail page with view mode switching"

  - id: "MFV-1.9"
    title: "First folder auto-selection"
    status: pending
    assigned_to: ["frontend-developer"]
    model: sonnet
    effort: 2
    priority: medium
    dependencies: ["MFV-1.3", "MFV-1.5"]
    description: "Implement auto-selection of first semantic folder on folder view load; ensure right pane populates immediately"

  - id: "MFV-1.10"
    title: "Unit tests"
    status: pending
    assigned_to: ["frontend-developer"]
    model: sonnet
    effort: 2
    priority: medium
    dependencies: ["MFV-1.1", "MFV-1.2"]
    description: "Test buildFolderTree(), isSemanticFolder(), and filtering logic; cover edge cases (roots, leafs, special chars, deep nesting)"

parallelization:
  batch_1: ["MFV-1.1", "MFV-1.2", "MFV-1.4", "MFV-1.6", "MFV-1.7"]
  batch_2: ["MFV-1.3", "MFV-1.10"]
  batch_3: ["MFV-1.5"]
  batch_4: ["MFV-1.8", "MFV-1.9"]
---

# Phase 1: Two-Pane Layout & Semantic Tree

## Overview

Phase 1 delivers the two-pane master-detail layout with semantic navigation tree (left pane) and folder detail pane container (right pane). This phase builds tree utilities with smart semantic filtering (excluding root folders like `plugins/`, `src/` and leaf artifact containers like `commands/`, `agents/`), renders the semantic tree component with collapsible folders, implements the folder detail pane container, and integrates the layout into the source detail page. By end of Phase 1, users can toggle to folder view, see the two-pane layout, select folders from the semantic tree, and see the folder detail pane populate on the right.

**Duration**: 4 days
**Total Effort**: 21 story points
**Dependencies**: None (frontend-only, no API changes)
**Design Reference**: Aligns with Gemini design spec for two-pane layout

## Tasks

### MFV-1.1: Tree builder utilities

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: critical

**Description**: Create `buildFolderTree()` function to convert flat CatalogEntry[] to nested tree structure; handle depth filtering with `maxDepth` parameter.

**Acceptance Criteria**:
- Tree converts flat paths into nested object structure
- Handles 1000+ items without performance issues
- Filters by depth with maxDepth parameter
- Returns proper FolderTree type
- No console errors on malformed paths

**Files to Create**:
- `skillmeat/web/lib/tree-builder.ts`

---

### MFV-1.2: Semantic filtering utilities

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: critical

**Description**: Create `isSemanticFolder()` to exclude root folders (plugins/, src/, skills/, etc.) and leaf containers (commands/, agents/, mcp_servers/, etc.); implement smart tree filtering.

**Acceptance Criteria**:
- Filters exclude designated roots and leafs
- Intermediate folders shown
- Function handles edge cases
- Filters produce clean navigation tree

**Files to Create**:
- `skillmeat/web/lib/tree-filter-utils.ts`

---

### MFV-1.3: useFolderSelection hook

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: high

**Description**: Create React hook `useFolderSelection()` managing folder selection state (selected folder path, expanded folders); return selection + setSelected() callback.

**Acceptance Criteria**:
- Hook tracks selected folder
- Tracks expanded state
- Updates on user interaction
- Memoized
- Integrates with semantic filtering

**Files to Create**:
- `skillmeat/web/lib/hooks/use-folder-selection.ts`

**Dependencies**:
- MFV-1.1: Tree builder functions

---

### MFV-1.4: Two-pane layout component

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: opus
**Effort**: 3 pts
**Priority**: high

**Description**: Create two-pane container layout with left pane (25%, semantic tree) and right pane (75%, folder detail). Manage layout, responsive behavior, splitter.

**Acceptance Criteria**:
- Layout renders two panes side-by-side
- Proportions correct (25% left, 75% right)
- Responsive on smaller screens (stacked layout)
- Smooth splitter (optional)

**Files to Create**:
- `skillmeat/web/app/marketplace/sources/[id]/components/source-folder-layout.tsx`

---

### MFV-1.5: Semantic tree component

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: opus
**Effort**: 3 pts
**Priority**: high

**Description**: Create left pane semantic navigation tree; render folders filtered by semantic rules; support expand/collapse; integrate folder selection.

**Acceptance Criteria**:
- Tree renders only semantic folders
- Expand/collapse works
- Selection tracking
- Shows folder hierarchy
- No root/leaf containers

**Files to Create**:
- `skillmeat/web/app/marketplace/sources/[id]/components/semantic-tree.tsx`

**Dependencies**:
- MFV-1.2: Semantic filtering utilities
- MFV-1.3: useFolderSelection hook

---

### MFV-1.6: Tree node component

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: sonnet
**Effort**: 2 pts
**Priority**: high

**Description**: Create individual tree folder item with: folder icon, folder name, expand/collapse chevron, count badge; integrate with selection state.

**Acceptance Criteria**:
- Folder node renders with proper styling
- Chevron rotates on expand
- Count shows
- Keyboard-accessible
- Consistent with design system

**Files to Create**:
- `skillmeat/web/app/marketplace/sources/[id]/components/tree-node.tsx`

---

### MFV-1.7: Toolbar folder toggle

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: sonnet
**Effort**: 1 pt
**Priority**: medium

**Description**: Add "Folder" button to view mode toggle in SourceToolbar; button toggles between grid/list/folder modes; uses existing view mode pattern.

**Acceptance Criteria**:
- Button appears in toolbar
- Clicking switches to folder view
- View mode persists in state
- Styling consistent

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/source-toolbar.tsx`

---

### MFV-1.8: Page integration

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: sonnet
**Effort**: 2 pts
**Priority**: medium

**Description**: Integrate two-pane layout into source detail page with conditional rendering based on view mode.

**Acceptance Criteria**:
- Folder view renders when view mode is "folder"
- Transitions between view modes work smoothly
- Page layout consistent across all view modes

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx`

**Dependencies**:
- MFV-1.4: Two-pane layout component
- MFV-1.5: Semantic tree component

---

### MFV-1.9: First folder auto-selection

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: medium

**Description**: Implement auto-selection of first semantic folder on folder view load; ensure right pane populates immediately.

**Acceptance Criteria**:
- On folder view toggle, first folder auto-selected
- Folder detail pane shows data immediately
- Smooth UX transition

**Files to Modify**:
- `skillmeat/web/lib/hooks/use-folder-selection.ts`
- `skillmeat/web/app/marketplace/sources/[id]/components/semantic-tree.tsx`

**Dependencies**:
- MFV-1.3: useFolderSelection hook
- MFV-1.5: Semantic tree component

---

### MFV-1.10: Unit tests

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: medium

**Description**: Test `buildFolderTree()`, `isSemanticFolder()`, and filtering logic; cover edge cases (roots, leafs, special chars, deep nesting).

**Acceptance Criteria**:
- >80% coverage for utility functions
- Semantic filtering works correctly
- Tests pass for 1000+ item sets

**Files to Create**:
- `skillmeat/web/__tests__/lib/tree-builder.test.ts`
- `skillmeat/web/__tests__/lib/tree-filter-utils.test.ts`

**Dependencies**:
- MFV-1.1: Tree builder utilities
- MFV-1.2: Semantic filtering utilities

---

## Quality Gates

- [ ] Tree builder + semantic filtering utilities tested (>80% coverage)
- [ ] Two-pane layout renders correctly with proper proportions (25% left, 75% right)
- [ ] Semantic tree displays only intermediate folders (roots/leafs excluded)
- [ ] Folder view button appears in toolbar and toggles layout correctly
- [ ] First folder auto-selects on folder view toggle; right pane populates
- [ ] Folder selection works; tree node selection state visual feedback
- [ ] No console errors; malformed paths handled gracefully
- [ ] Performance baseline: tree renders for 500 items in <300ms (initial, not optimized)
- [ ] Manual testing: toggle folder view, expand/collapse folders in left pane, folder detail shows on right

---

## Key Files

### New Files
- `skillmeat/web/lib/tree-builder.ts`
- `skillmeat/web/lib/tree-filter-utils.ts`
- `skillmeat/web/lib/hooks/use-folder-selection.ts`
- `skillmeat/web/app/marketplace/sources/[id]/components/source-folder-layout.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/semantic-tree.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/tree-node.tsx`
- `skillmeat/web/__tests__/lib/tree-builder.test.ts`
- `skillmeat/web/__tests__/lib/tree-filter-utils.test.ts`

### Modified Files
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/source-toolbar.tsx`

---

## Notes

Phase 1 is frontend-only with no API changes. All tree building happens client-side using existing `CatalogEntry.path` field. This phase implements a two-pane master-detail layout aligning with Gemini design spec. Focus on getting core layout and semantic tree working before Phase 2 folder detail pane features.
