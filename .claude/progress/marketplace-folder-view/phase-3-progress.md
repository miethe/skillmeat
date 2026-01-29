---
type: progress
prd: marketplace-folder-view
phase: 3
title: Accessibility & Performance Optimization
status: pending
started: null
completed: null
progress: 37
completion_estimate: on-track
total_tasks: 8
completed_tasks: 3
in_progress_tasks: 0
blocked_tasks: 0
owners:
- web-accessibility-checker
- react-performance-optimizer
contributors:
- frontend-developer
- documentation-writer
blockers: []
success_criteria:
- id: SC-3.1
  description: Full keyboard navigation working (tree + panes, all keys tested)
  status: pending
- id: SC-3.2
  description: Screen reader announces folder structure, selection, artifact counts
    (tested on 2+ readers)
  status: pending
- id: SC-3.3
  description: Focus indicators visible; focus management correct between panes
  status: pending
- id: SC-3.4
  description: Accessibility audit passes WCAG 2.1 AA (automated + manual)
  status: pending
- id: SC-3.5
  description: Tree renders 1000 items in <200ms
  status: pending
- id: SC-3.6
  description: Lazy rendering reduces initial DOM nodes 60-80%
  status: pending
- id: SC-3.7
  description: No performance regression on filter changes or folder selection
  status: pending
- id: SC-3.8
  description: Memoization prevents unnecessary re-renders
  status: pending
tasks:
- id: MFV-3.1
  title: Keyboard navigation
  status: completed
  assigned_to:
  - web-accessibility-checker
  model: opus
  effort: 3
  priority: critical
  dependencies: []
  description: 'Implement: Up/Down arrows navigate tree siblings, Left/Right expand/collapse
    folders, Enter/Space to select, Tab to move between left pane/right pane, Home/End
    for first/last'
- id: MFV-3.2
  title: ARIA labels and roles
  status: completed
  assigned_to:
  - web-accessibility-checker
  model: opus
  effort: 2
  priority: critical
  dependencies: []
  description: 'Add semantic roles/labels: left pane as role=''tree'', folders as
    role=''treeitem'', right pane as main content region; announce folder counts,
    artifact types'
- id: MFV-3.3
  title: Focus management between panes
  status: pending
  assigned_to:
  - web-accessibility-checker
  model: opus
  effort: 2
  priority: critical
  dependencies:
  - MFV-3.1
  description: Implement roving tabindex in tree; manage focus when selecting folders;
    visible focus indicators (2px ring); focus transitions between panes smooth
- id: MFV-3.4
  title: Screen reader testing
  status: pending
  assigned_to:
  - web-accessibility-checker
  model: opus
  effort: 2
  priority: high
  dependencies:
  - MFV-3.2
  description: Test with NVDA (Windows), JAWS (Windows), VoiceOver (macOS); verify
    tree structure, folder selection, right pane content all announced correctly
- id: MFV-3.5
  title: Lazy rendering
  status: completed
  assigned_to:
  - react-performance-optimizer
  model: opus
  effort: 2
  priority: critical
  dependencies: []
  description: 'Prevent DOM explosion: collapsed folders don''t render children initially;
    render on demand when expanded; measure DOM node count before/after'
- id: MFV-3.6
  title: Performance profiling
  status: pending
  assigned_to:
  - react-performance-optimizer
  model: sonnet
  effort: 2
  priority: high
  dependencies:
  - MFV-3.5
  description: Profile tree rendering with DevTools; measure render time for 500/1000
    item trees; optimize hot paths; target <200ms for 1000 items
- id: MFV-3.7
  title: Memoization optimization
  status: pending
  assigned_to:
  - react-performance-optimizer
  model: sonnet
  effort: 1
  priority: high
  dependencies:
  - MFV-3.6
  description: Add React.memo() to tree nodes and detail pane components; memoize
    tree/filtering functions; prevent unnecessary re-renders
- id: MFV-3.8
  title: Documentation update
  status: pending
  assigned_to:
  - documentation-writer
  model: haiku
  effort: 2
  priority: low
  dependencies:
  - MFV-3.1
  - MFV-3.2
  - MFV-3.3
  - MFV-3.4
  - MFV-3.5
  - MFV-3.6
  - MFV-3.7
  description: Document keyboard navigation, ARIA patterns, focus management, performance
    optimizations
parallelization:
  batch_1:
  - MFV-3.1
  - MFV-3.2
  - MFV-3.5
  batch_2:
  - MFV-3.3
  - MFV-3.4
  - MFV-3.6
  batch_3:
  - MFV-3.7
  batch_4:
  - MFV-3.8
updated: '2026-01-29'
---

# Phase 3: Accessibility & Performance Optimization

## Overview

Phase 3 ensures accessibility compliance (WCAG 2.1 AA) and performance optimization. Users can navigate the left pane tree using arrow keys, enter/space to expand/collapse, and Tab between panes. Screen readers announce folder state, item counts, and artifact types. Performance is optimized: collapsed folders don't render children initially, tree renders 1000+ artifacts within 200ms budget. Final validation includes accessibility audit and performance profiling.

**Duration**: 2 days
**Total Effort**: 16 story points
**Dependencies**: Phase 2 complete

## Tasks

### MFV-3.1: Keyboard navigation

**Status**: `pending`
**Assigned**: web-accessibility-checker
**Model**: opus
**Effort**: 3 pts
**Priority**: critical

**Description**: Implement: Up/Down arrows navigate tree siblings, Left/Right expand/collapse folders, Enter/Space to select, Tab to move between left pane/right pane, Home/End for first/last.

**Acceptance Criteria**:
- Up/Down moves between tree items
- Left collapses, Right expands
- Enter selects folder
- Tab moves pane focus
- No focus traps

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/semantic-tree.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/tree-node.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/source-folder-layout.tsx`

---

### MFV-3.2: ARIA labels and roles

**Status**: `pending`
**Assigned**: web-accessibility-checker
**Model**: opus
**Effort**: 2 pts
**Priority**: critical

**Description**: Add semantic roles/labels: left pane as `role="tree"`, folders as `role="treeitem"`, right pane as main content region; announce folder counts, artifact types.

**Acceptance Criteria**:
- Screen reader announces: "Folder tree region"
- Screen reader announces: "Folder: skills, 42 artifacts, expanded"
- Artifact types and counts in right pane announced

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/semantic-tree.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/tree-node.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-pane.tsx`

---

### MFV-3.3: Focus management between panes

**Status**: `pending`
**Assigned**: web-accessibility-checker
**Model**: opus
**Effort**: 2 pts
**Priority**: critical

**Description**: Implement roving tabindex in tree; manage focus when selecting folders; visible focus indicators (2px ring); focus transitions between panes smooth.

**Acceptance Criteria**:
- Focus moves with tree navigation
- Visible on keyboard nav
- Selecting folder doesn't lose focus
- Tab cycles between panes
- No traps

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/semantic-tree.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/tree-node.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/source-folder-layout.tsx`

**Dependencies**:
- MFV-3.1: Keyboard navigation

---

### MFV-3.4: Screen reader testing

**Status**: `pending`
**Assigned**: web-accessibility-checker
**Model**: opus
**Effort**: 2 pts
**Priority**: high

**Description**: Test with NVDA (Windows), JAWS (Windows), VoiceOver (macOS); verify tree structure, folder selection, right pane content all announced correctly.

**Acceptance Criteria**:
- Tested on 2+ screen readers
- Tree navigation clear
- Folder selection announced
- Right pane content accessible

**Dependencies**:
- MFV-3.2: ARIA labels and roles

---

### MFV-3.5: Lazy rendering

**Status**: `pending`
**Assigned**: react-performance-optimizer
**Model**: opus
**Effort**: 2 pts
**Priority**: critical

**Description**: Prevent DOM explosion: collapsed folders don't render children initially; render on demand when expanded; measure DOM node count before/after.

**Acceptance Criteria**:
- Collapsed folders have no child DOM nodes
- Expanding loads children on-demand
- DOM node count reduced 60-80% with mostly collapsed tree

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/semantic-tree.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/tree-node.tsx`

---

### MFV-3.6: Performance profiling

**Status**: `pending`
**Assigned**: react-performance-optimizer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: high

**Description**: Profile tree rendering with DevTools; measure render time for 500/1000 item trees; optimize hot paths; target <200ms for 1000 items.

**Acceptance Criteria**:
- Tree renders 1000 artifacts in <200ms
- Filter changes apply in <100ms
- No jank on expand/collapse
- Smooth frames in DevTools

**Files to Analyze**:
- `skillmeat/web/lib/tree-builder.ts`
- `skillmeat/web/lib/tree-filter-utils.ts`
- `skillmeat/web/lib/hooks/use-folder-selection.ts`
- `skillmeat/web/app/marketplace/sources/[id]/components/semantic-tree.tsx`

**Dependencies**:
- MFV-3.5: Lazy rendering

---

### MFV-3.7: Memoization optimization

**Status**: `pending`
**Assigned**: react-performance-optimizer
**Model**: sonnet
**Effort**: 1 pt
**Priority**: high

**Description**: Add React.memo() to tree nodes and detail pane components; memoize tree/filtering functions; prevent unnecessary re-renders.

**Acceptance Criteria**:
- Components wrapped with React.memo
- Functions memoized with useMemo
- Re-render count reduced in DevTools profiler

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/tree-node.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/artifact-type-section.tsx`
- `skillmeat/web/lib/hooks/use-folder-selection.ts`

**Dependencies**:
- MFV-3.6: Performance profiling

---

### MFV-3.8: Documentation update

**Status**: `pending`
**Assigned**: documentation-writer
**Model**: haiku
**Effort**: 2 pts
**Priority**: low

**Description**: Document keyboard navigation, ARIA patterns, focus management, performance optimizations in CLAUDE.md or dedicated doc.

**Acceptance Criteria**:
- Developer guide explains keyboard nav (all key bindings)
- ARIA labels pattern documented
- Roving tabindex implementation explained
- Performance optimizations documented

**Files to Create/Modify**:
- `skillmeat/web/CLAUDE.md` (add section)

**Dependencies**:
- MFV-3.1 through MFV-3.7

---

## Quality Gates

- [ ] Full keyboard navigation working (tree + panes, all keys tested)
- [ ] Screen reader announces folder structure, selection, artifact counts (tested on 2+ readers)
- [ ] Focus indicators visible; focus management correct between panes
- [ ] Accessibility audit passes WCAG 2.1 AA (automated + manual)
- [ ] Tree renders 1000 items in <200ms
- [ ] Lazy rendering reduces initial DOM nodes 60-80%
- [ ] No performance regression on filter changes or folder selection
- [ ] Memoization prevents unnecessary re-renders

---

## Key Files

### Modified Files
- `skillmeat/web/app/marketplace/sources/[id]/components/semantic-tree.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/tree-node.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/source-folder-layout.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-pane.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/artifact-type-section.tsx`
- `skillmeat/web/lib/hooks/use-folder-selection.ts`
- `skillmeat/web/CLAUDE.md`

---

## Notes

Phase 3 can be parallelized: accessibility work (MFV-3.1-3.4) and performance work (MFV-3.5-3.7) are largely independent. Documentation (MFV-3.8) depends on all other tasks completing. Target WCAG 2.1 AA compliance and <200ms render for 1000 items.
