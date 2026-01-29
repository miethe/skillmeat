---
type: progress
prd: "marketplace-folder-view"
phase: 1
title: "Core Folder View Component & Tree Building"
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
    description: "Tree builder utilities tested and verified (>80% coverage)"
    status: pending
  - id: "SC-1.2"
    description: "All components render in Storybook with correct styling"
    status: pending
  - id: "SC-1.3"
    description: "Folder view button appears in toolbar and toggles correctly"
    status: pending
  - id: "SC-1.4"
    description: "Filters apply to tree; filtered items removed; re-rendering works"
    status: pending
  - id: "SC-1.5"
    description: "No console errors; malformed paths handled gracefully"
    status: pending
  - id: "SC-1.6"
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
    title: "Depth calculator"
    status: pending
    assigned_to: ["frontend-developer"]
    model: sonnet
    effort: 2
    priority: critical
    dependencies: []
    description: "Create calculateAutoDepth() function; detect optimal depth from root_hint or scan first 50 entries"

  - id: "MFV-1.3"
    title: "useFolderTree hook"
    status: pending
    assigned_to: ["frontend-developer"]
    model: sonnet
    effort: 3
    priority: high
    dependencies: ["MFV-1.1", "MFV-1.2"]
    description: "Create React hook managing tree state (expanded folders, depth setting, filtered items)"

  - id: "MFV-1.4"
    title: "ArtifactRowFolder component"
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    model: opus
    effort: 3
    priority: high
    dependencies: []
    description: "Create artifact row component with type icon, name, confidence badge, status indicator, actions"

  - id: "MFV-1.5"
    title: "DirectoryNode component"
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    model: opus
    effort: 3
    priority: high
    dependencies: ["MFV-1.3"]
    description: "Create collapsible folder node using Radix Collapsible with chevron, folder icon, name, count badge"

  - id: "MFV-1.6"
    title: "CatalogFolder container"
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    model: opus
    effort: 3
    priority: high
    dependencies: ["MFV-1.4", "MFV-1.5"]
    description: "Create main tree view component; recursively renders DirectoryNode and ArtifactRowFolder"

  - id: "MFV-1.7"
    title: "Folder view toolbar button"
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    model: sonnet
    effort: 2
    priority: medium
    dependencies: ["MFV-1.6"]
    description: "Add 'Folder' button to view mode toggle in SourceToolbar"

  - id: "MFV-1.8"
    title: "Page integration"
    status: pending
    assigned_to: ["ui-engineer-enhanced"]
    model: sonnet
    effort: 2
    priority: medium
    dependencies: ["MFV-1.6"]
    description: "Integrate CatalogFolder into source detail page with view mode switching"

  - id: "MFV-1.9"
    title: "Filter integration"
    status: pending
    assigned_to: ["frontend-developer"]
    model: sonnet
    effort: 2
    priority: medium
    dependencies: ["MFV-1.6"]
    description: "Verify all filters (type, confidence, search, status) work with folder view"

  - id: "MFV-1.10"
    title: "Unit tests + Storybook"
    status: pending
    assigned_to: ["frontend-developer"]
    model: sonnet
    effort: 2
    priority: medium
    dependencies: ["MFV-1.1", "MFV-1.2", "MFV-1.4", "MFV-1.5", "MFV-1.6"]
    description: "Test buildFolderTree() and calculateAutoDepth(); create Storybook stories for all components"

parallelization:
  batch_1: ["MFV-1.1", "MFV-1.2"]
  batch_2: ["MFV-1.3"]
  batch_3: ["MFV-1.4"]
  batch_4: ["MFV-1.5", "MFV-1.6"]
  batch_5: ["MFV-1.7", "MFV-1.8", "MFV-1.9"]
  batch_6: ["MFV-1.10"]
---

# Phase 1: Core Folder View Component & Tree Building

## Overview

Phase 1 delivers the foundational tree-building utilities and UI components for folder-based artifact navigation. This phase focuses on core functionality: parsing paths into tree structures, rendering collapsible folders with Radix, and integrating with existing filters. By end of Phase 1, users can toggle to folder view, expand/collapse folders, and see filtered artifacts organized hierarchically.

**Duration**: 4 days
**Total Effort**: 24 story points
**Dependencies**: None (frontend-only, no API changes)

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
- `skillmeat/web/lib/folder-tree.ts`

---

### MFV-1.2: Depth calculator

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: critical

**Description**: Create `calculateAutoDepth()` function; detect optimal depth from `root_hint` or scan first 50 entries; implement depth options (Auto/TopLevel/1-3 levels).

**Acceptance Criteria**:
- Function returns auto-detected depth
- Respects `root_hint` when provided
- Provides consistent results across similar catalogs
- Handles edge cases (empty catalog, single item)

**Files to Create**:
- `skillmeat/web/lib/folder-tree.ts` (extend)

---

### MFV-1.3: useFolderTree hook

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 3 pts
**Priority**: high

**Description**: Create React hook `useFolderTree()` managing tree state (expanded folders, depth setting, filtered items); return tree data + setExpanded() callback.

**Acceptance Criteria**:
- Hook returns tree structure and management functions
- Tracks expanded state per folder path
- Re-builds tree on filter/depth change
- Memoized to prevent unnecessary rebuilds

**Files to Create**:
- `skillmeat/web/lib/hooks/use-folder-tree.ts`

**Dependencies**:
- MFV-1.1: Tree builder functions
- MFV-1.2: Depth calculator functions

---

### MFV-1.4: ArtifactRowFolder component

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: opus
**Effort**: 3 pts
**Priority**: high

**Description**: Create artifact row component displaying: type icon, artifact name, confidence badge, status indicator, import/exclude actions (reuse CatalogRow pattern).

**Acceptance Criteria**:
- Row renders in folder context with proper indentation
- Shows all artifact metadata (type, name, confidence, status)
- Actions work (import/exclude buttons)
- Matches grid/list row styling
- TypeScript fully typed

**Files to Create**:
- `skillmeat/web/app/marketplace/sources/[id]/components/artifact-row-folder.tsx`

---

### MFV-1.5: DirectoryNode component

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: opus
**Effort**: 3 pts
**Priority**: high

**Description**: Create collapsible folder node using Radix Collapsible: chevron icon, folder icon, folder name, artifact count badge; integrate with `useFolderTree` expanded state.

**Acceptance Criteria**:
- Folder expands/collapses on click
- Chevron rotates on expand/collapse
- Shows artifact count badge
- Lazy-renders children (collapsed folders have no child DOM)
- Matches folder icon from Lucide
- Keyboard-accessible (Enter/Space to toggle)

**Files to Create**:
- `skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx`

**Dependencies**:
- MFV-1.3: useFolderTree hook for expanded state

---

### MFV-1.6: CatalogFolder container

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: opus
**Effort**: 3 pts
**Priority**: high

**Description**: Create main tree view component; recursively renders DirectoryNode and ArtifactRowFolder; integrates with `useSourceCatalog` and filter state.

**Acceptance Criteria**:
- Tree renders correctly from root
- All filters (type/confidence/search) applied to tree items
- Empty state shown for filtered results
- Scrolls smoothly with large trees

**Files to Create**:
- `skillmeat/web/app/marketplace/sources/[id]/components/catalog-folder.tsx`

**Dependencies**:
- MFV-1.4: ArtifactRowFolder component
- MFV-1.5: DirectoryNode component

---

### MFV-1.7: Folder view toolbar button

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: sonnet
**Effort**: 2 pts
**Priority**: medium

**Description**: Add "Folder" button to view mode toggle in SourceToolbar; button toggles between grid/list/folder modes; uses existing view mode pattern.

**Acceptance Criteria**:
- Button appears in toolbar alongside grid/list
- Clicking switches to folder view
- Other buttons still work
- View toggle styling consistent

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/source-toolbar.tsx`

**Dependencies**:
- MFV-1.6: CatalogFolder component exists

---

### MFV-1.8: Page integration

**Status**: `pending`
**Assigned**: ui-engineer-enhanced
**Model**: sonnet
**Effort**: 2 pts
**Priority**: medium

**Description**: Integrate CatalogFolder into source detail page with conditional rendering based on view mode.

**Acceptance Criteria**:
- Folder view renders when view mode is "folder"
- Transitions between view modes work smoothly
- Page layout consistent across all view modes

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx`

**Dependencies**:
- MFV-1.6: CatalogFolder component exists

---

### MFV-1.9: Filter integration

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: medium

**Description**: Verify all filters (type, confidence, search, status) work with folder view; tree re-renders on filter change; filtered items removed from tree.

**Acceptance Criteria**:
- Filters applied to tree items
- Empty folders show "(No importable artifacts)" message
- Tree updates reactively on filter change
- No performance lag on filter change

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/catalog-folder.tsx`

**Dependencies**:
- MFV-1.6: CatalogFolder component exists

---

### MFV-1.10: Unit tests + Storybook

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: medium

**Description**: Test `buildFolderTree()` and `calculateAutoDepth()` functions; cover path parsing edge cases; create Storybook stories for all components.

**Acceptance Criteria**:
- >80% coverage for utility functions
- Tests pass for 1000+ item sets
- Edge cases handled gracefully (special chars, deep nesting)
- Stories render all component states (expanded/collapsed, loading, empty, filtered)
- Interactions work in Storybook

**Files to Create**:
- `skillmeat/web/__tests__/lib/folder-tree.test.ts`
- `skillmeat/web/stories/marketplace/folder-view.stories.tsx`

**Dependencies**:
- MFV-1.1, MFV-1.2: Utilities to test
- MFV-1.4, MFV-1.5, MFV-1.6: Components to story

---

## Quality Gates

- [ ] Tree builder utilities tested and verified (>80% coverage)
- [ ] All components render in Storybook with correct styling
- [ ] Folder view button appears in toolbar and toggles correctly
- [ ] Filters apply to tree; filtered items removed; re-rendering works
- [ ] No console errors; malformed paths handled gracefully
- [ ] Performance baseline: tree renders for 500 items in <300ms (initial, not optimized)
- [ ] Manual testing: expand/collapse folders, apply filters, toggle between view modes

---

## Key Files

### New Files
- `skillmeat/web/lib/folder-tree.ts`
- `skillmeat/web/lib/hooks/use-folder-tree.ts`
- `skillmeat/web/app/marketplace/sources/[id]/components/catalog-folder.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/artifact-row-folder.tsx`
- `skillmeat/web/__tests__/lib/folder-tree.test.ts`

### Modified Files
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/source-toolbar.tsx`

---

## Notes

Phase 1 is frontend-only with no API changes. All tree building happens client-side using existing `CatalogEntry.path` field. Focus on getting core functionality working before polish.
