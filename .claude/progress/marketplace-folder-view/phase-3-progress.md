---
type: progress
prd: "marketplace-folder-view"
phase: 3
title: "Accessibility & Performance Optimization"
status: not_started
started: null
completed: null

progress: 0
completion_estimate: "on-track"

total_tasks: 10
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0

owners: ["web-accessibility-checker", "react-performance-optimizer"]
contributors: ["frontend-developer", "documentation-writer"]

blockers: []

success_criteria:
  - id: "SC-3.1"
    description: "Full keyboard navigation working (all keys tested)"
    status: pending
  - id: "SC-3.2"
    description: "Screen reader announces folder/artifact correctly (tested on 2+ readers)"
    status: pending
  - id: "SC-3.3"
    description: "Focus indicators visible and focus management correct"
    status: pending
  - id: "SC-3.4"
    description: "Accessibility audit passes WCAG 2.1 AA (automated + manual)"
    status: pending
  - id: "SC-3.5"
    description: "Tree renders 1000 items in <200ms"
    status: pending
  - id: "SC-3.6"
    description: "Lazy rendering reduces initial DOM nodes 60-80%"
    status: pending
  - id: "SC-3.7"
    description: "No performance regression on filter changes"
    status: pending
  - id: "SC-3.8"
    description: "Performance E2E tests pass"
    status: pending
  - id: "SC-3.9"
    description: "Accessibility documentation complete"
    status: pending

tasks:
  - id: "MFV-3.1"
    title: "Keyboard navigation"
    status: pending
    assigned_to: ["web-accessibility-checker"]
    model: opus
    effort: 3
    priority: critical
    dependencies: []
    description: "Implement full keyboard support: Up/Down navigate siblings, Left/Right expand/collapse, Enter/Space toggle"

  - id: "MFV-3.2"
    title: "ARIA labels & roles"
    status: pending
    assigned_to: ["web-accessibility-checker"]
    model: opus
    effort: 2
    priority: critical
    dependencies: []
    description: "Add semantic roles and labels: folders as role=treeitem, announce expanded/collapsed state"

  - id: "MFV-3.3"
    title: "Focus management"
    status: pending
    assigned_to: ["web-accessibility-checker"]
    model: opus
    effort: 2
    priority: critical
    dependencies: ["MFV-3.1"]
    description: "Implement roving tabindex pattern; focus indicators visible (2px ring); no focus traps"

  - id: "MFV-3.4"
    title: "Screen reader testing"
    status: pending
    assigned_to: ["web-accessibility-checker"]
    model: opus
    effort: 2
    priority: high
    dependencies: ["MFV-3.2"]
    description: "Test with NVDA, JAWS, VoiceOver; verify folder structure announced correctly"

  - id: "MFV-3.5"
    title: "Lazy rendering implementation"
    status: pending
    assigned_to: ["react-performance-optimizer"]
    model: opus
    effort: 3
    priority: critical
    dependencies: []
    description: "Collapsed folders don't render children; render on demand when expanded"

  - id: "MFV-3.6"
    title: "Performance profiling"
    status: pending
    assigned_to: ["react-performance-optimizer"]
    model: opus
    effort: 2
    priority: high
    dependencies: []
    description: "Profile tree rendering with DevTools; measure render time for 500/1000 item trees"

  - id: "MFV-3.7"
    title: "Memoization optimization"
    status: pending
    assigned_to: ["react-performance-optimizer"]
    model: sonnet
    effort: 2
    priority: high
    dependencies: ["MFV-3.5", "MFV-3.6"]
    description: "Add React.memo() to components; memoize tree calculation functions"

  - id: "MFV-3.8"
    title: "Accessibility audit fixes"
    status: pending
    assigned_to: ["web-accessibility-checker"]
    model: opus
    effort: 2
    priority: high
    dependencies: ["MFV-3.2", "MFV-3.4"]
    description: "Run automated WCAG audit (axe); fix any critical/serious issues; verify color contrast"

  - id: "MFV-3.9"
    title: "Performance E2E tests"
    status: pending
    assigned_to: ["frontend-developer"]
    model: sonnet
    effort: 2
    priority: medium
    dependencies: ["MFV-3.6"]
    description: "Write Playwright tests measuring render time; benchmark tree loading for 500/1000 items"

  - id: "MFV-3.10"
    title: "Documentation update"
    status: pending
    assigned_to: ["documentation-writer"]
    model: haiku
    effort: 1
    priority: low
    dependencies: ["MFV-3.1", "MFV-3.2"]
    description: "Document keyboard navigation, ARIA patterns, screen reader behavior"

parallelization:
  batch_1: ["MFV-3.1", "MFV-3.2", "MFV-3.3"]
  batch_2: ["MFV-3.4"]
  batch_3: ["MFV-3.5", "MFV-3.6"]
  batch_4: ["MFV-3.7"]
  batch_5: ["MFV-3.8", "MFV-3.9"]
  batch_6: ["MFV-3.10"]
---

# Phase 3: Accessibility & Performance Optimization

## Overview

Phase 3 ensures accessibility compliance (WCAG 2.1 AA), full keyboard navigation, and performance optimization. Users can navigate the entire tree using arrow keys, Enter/Space to expand/collapse, and Tab between controls. Screen readers announce folder state, item counts, and artifact types. Performance is optimized: collapsed folders don't render children initially, tree renders 1000+ artifacts within 200ms budget. Final validation includes accessibility audit and performance profiling.

**Duration**: 3 days
**Total Effort**: 21 story points
**Dependencies**: Phase 2 complete

## Tasks

### MFV-3.1: Keyboard navigation

**Status**: `pending`
**Assigned**: web-accessibility-checker
**Model**: opus
**Effort**: 3 pts
**Priority**: critical

**Description**: Implement full keyboard support: Up/Down arrows navigate siblings, Left/Right expand/collapse folders, Enter/Space to toggle, Tab to next control, Home/End for first/last.

**Acceptance Criteria**:
- Up/Down moves between tree items (folders and artifacts)
- Left collapses current folder or moves to parent
- Right expands current folder or moves to first child
- Enter/Space toggles folder expand/collapse
- Tab moves to next control outside tree
- Home/End jump to first/last tree item
- Focus stays within tree during arrow navigation

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/catalog-folder.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx`

---

### MFV-3.2: ARIA labels & roles

**Status**: `pending`
**Assigned**: web-accessibility-checker
**Model**: opus
**Effort**: 2 pts
**Priority**: critical

**Description**: Add semantic roles and labels: folders as `role="treeitem"`, announce expanded/collapsed state, item counts, artifact types; roving tabindex pattern.

**Acceptance Criteria**:
- Tree container has `role="tree"`
- Folders have `role="treeitem"` with `aria-expanded`
- Artifacts have `role="treeitem"` (leaf nodes)
- Screen reader announces: "Folder: skills, 42 artifacts, expanded"
- Screen reader announces: "Artifact: my-skill, type: skill, confidence: high"
- Groups have `role="group"` for proper nesting

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/catalog-folder.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/artifact-row-folder.tsx`

---

### MFV-3.3: Focus management

**Status**: `pending`
**Assigned**: web-accessibility-checker
**Model**: opus
**Effort**: 2 pts
**Priority**: critical

**Description**: Implement roving tabindex pattern; manage focus when expanding/collapsing; focus indicators visible (2px ring); focus trap not created.

**Acceptance Criteria**:
- Only one tree item is in tab order at a time (roving tabindex)
- Focus moves with keyboard navigation
- Focus indicator visible on keyboard nav (2px ring, high contrast)
- Expanding folder doesn't move focus away from current item
- No focus traps created; Tab moves outside tree

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/catalog-folder.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx`

**Dependencies**:
- MFV-3.1: Keyboard navigation complete

---

### MFV-3.4: Screen reader testing

**Status**: `pending`
**Assigned**: web-accessibility-checker
**Model**: opus
**Effort**: 2 pts
**Priority**: high

**Description**: Test with NVDA (Windows), JAWS (Windows), VoiceOver (macOS); verify folder structure announced correctly; test expand/collapse announcements.

**Acceptance Criteria**:
- Tested on at least 2 screen readers
- Folder/artifact structure announced clearly
- Expand/collapse state announced
- No confusion or missing context
- Navigation works correctly with screen reader

**Dependencies**:
- MFV-3.2: ARIA labels complete

---

### MFV-3.5: Lazy rendering implementation

**Status**: `pending`
**Assigned**: react-performance-optimizer
**Model**: opus
**Effort**: 3 pts
**Priority**: critical

**Description**: Prevent DOM explosion: collapsed folders don't render children initially; render on demand when expanded; measure DOM node count before/after.

**Acceptance Criteria**:
- Collapsed folders have no child DOM nodes
- Expanding folder renders children on-demand
- DOM node count reduced 60-80% with mostly collapsed tree
- Smooth expansion animation (no jank on render)

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/catalog-folder.tsx`

---

### MFV-3.6: Performance profiling

**Status**: `pending`
**Assigned**: react-performance-optimizer
**Model**: opus
**Effort**: 2 pts
**Priority**: high

**Description**: Profile tree rendering with DevTools; measure render time for 500/1000 item trees; optimize hot paths; target <200ms for 1000 items.

**Acceptance Criteria**:
- Tree renders 1000 artifacts in <200ms
- Filter changes apply in <100ms
- No jank on expand/collapse
- DevTools timeline shows smooth frames (no long tasks)
- Hot paths identified and documented

**Files to Analyze**:
- `skillmeat/web/lib/folder-tree.ts`
- `skillmeat/web/lib/hooks/use-folder-tree.ts`
- `skillmeat/web/app/marketplace/sources/[id]/components/catalog-folder.tsx`

---

### MFV-3.7: Memoization optimization

**Status**: `pending`
**Assigned**: react-performance-optimizer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: high

**Description**: Add React.memo() to components; memoize tree calculation functions; prevent unnecessary re-renders on leaf changes.

**Acceptance Criteria**:
- Leaf components wrapped with React.memo
- Tree calculation functions memoized with useMemo
- Re-render count reduced in DevTools profiler
- No unnecessary re-renders on unrelated state changes

**Files to Modify**:
- `skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/artifact-row-folder.tsx`
- `skillmeat/web/lib/hooks/use-folder-tree.ts`

**Dependencies**:
- MFV-3.5: Lazy rendering complete
- MFV-3.6: Performance profiling complete (know what to optimize)

---

### MFV-3.8: Accessibility audit fixes

**Status**: `pending`
**Assigned**: web-accessibility-checker
**Model**: opus
**Effort**: 2 pts
**Priority**: high

**Description**: Run automated WCAG audit (axe); manual testing of all interactions; verify focus indicators, color contrast, label associations.

**Acceptance Criteria**:
- Automated audit passes (zero critical/serious issues)
- Manual keyboard navigation complete
- Color contrast >4.5:1 for text
- All interactive elements have accessible names
- No WCAG 2.1 AA violations

**Dependencies**:
- MFV-3.2: ARIA labels complete
- MFV-3.4: Screen reader testing complete

---

### MFV-3.9: Performance E2E tests

**Status**: `pending`
**Assigned**: frontend-developer
**Model**: sonnet
**Effort**: 2 pts
**Priority**: medium

**Description**: Write Playwright tests measuring render time; benchmark tree loading for 500/1000 items; create performance regression test.

**Acceptance Criteria**:
- E2E tests verify render time <200ms for 1000 items
- Performance baseline established
- Tests run in CI to catch regressions
- Clear failure message if performance degrades

**Files to Create**:
- `skillmeat/web/tests/marketplace/folder-view-performance.spec.ts`

**Dependencies**:
- MFV-3.6: Performance profiling complete

---

### MFV-3.10: Documentation update

**Status**: `pending`
**Assigned**: documentation-writer
**Model**: haiku
**Effort**: 1 pt
**Priority**: low

**Description**: Document keyboard navigation, ARIA patterns, screen reader behavior in `.claude/context/` or CLAUDE.md; include implementation notes.

**Acceptance Criteria**:
- Developer guide explains keyboard nav (all key bindings)
- ARIA labels pattern documented
- Roving tabindex implementation explained
- Includes code examples and patterns
- Screen reader behavior documented

**Files to Create/Modify**:
- `skillmeat/web/CLAUDE.md` (add section)
- `skillmeat/web/app/marketplace/sources/[id]/components/README.md` (optional)

**Dependencies**:
- MFV-3.1: Keyboard navigation complete
- MFV-3.2: ARIA labels complete

---

## Quality Gates

- [ ] Full keyboard navigation working (all keys tested)
- [ ] Screen reader announces folder/artifact correctly (tested on 2+ readers)
- [ ] Focus indicators visible and focus management correct
- [ ] Accessibility audit passes WCAG 2.1 AA (automated + manual)
- [ ] Tree renders 1000 items in <200ms
- [ ] Lazy rendering reduces initial DOM nodes 60-80%
- [ ] No performance regression on filter changes
- [ ] Performance E2E tests pass
- [ ] Accessibility documentation complete

---

## Key Files

### New Files
- `skillmeat/web/tests/marketplace/folder-view-performance.spec.ts`

### Modified Files
- `skillmeat/web/app/marketplace/sources/[id]/components/catalog-folder.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx`
- `skillmeat/web/app/marketplace/sources/[id]/components/artifact-row-folder.tsx`
- `skillmeat/web/lib/hooks/use-folder-tree.ts`
- `skillmeat/web/CLAUDE.md`

---

## Notes

Phase 3 can be parallelized: accessibility work (MFV-3.1-3.4, 3.8) and performance work (MFV-3.5-3.7, 3.9) are largely independent. Documentation (MFV-3.10) can happen concurrently with audit fixes. Target WCAG 2.1 AA compliance and <200ms render for 1000 items.
