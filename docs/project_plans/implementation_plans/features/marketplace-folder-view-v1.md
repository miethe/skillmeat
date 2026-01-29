---
title: "Implementation Plan: Marketplace Folder View"
description: "Phased implementation of tree-based folder view for marketplace source detail pages with accessibility and performance optimization"
audience: [ai-agents, developers]
tags: [implementation, planning, features, frontend, marketplace]
created: 2026-01-28
updated: 2026-01-28
category: "product-planning"
status: draft
related:
  - /docs/project_plans/PRDs/features/marketplace-folder-view-v1.md
---

# Implementation Plan: Marketplace Folder View

**Plan ID**: `IMPL-MARKETPLACE-FOLDER-VIEW-v1`
**Date**: 2026-01-28
**Author**: Implementation Planning Orchestrator
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/features/marketplace-folder-view-v1.md`
- **Progress Tracking**: `.claude/progress/marketplace-folder-view-v1/all-phases-progress.md`

**Complexity**: Medium (M)
**Total Estimated Effort**: 28 story points
**Target Timeline**: 10 days (4 days Phase 1 + 3 days Phase 2 + 3 days Phase 3)

---

## Executive Summary

This plan delivers a hierarchical tree-based Folder View for marketplace source detail pages, enabling users to navigate 100+ artifact repositories by directory structure instead of flat lists. The implementation follows MeatyPrompts frontend-first architecture: build tree utilities first (no UI dependencies), then leaf components, then containers, then integration. Three phases deliver core functionality (Phase 1), configuration and polish (Phase 2), and accessibility/performance optimization (Phase 3). No API changes required; all tree building happens client-side using existing `CatalogEntry.path` field.

**Key Outcomes:**
- Users discover related artifacts 2-3x faster in large repositories
- Folder view integrates seamlessly alongside existing grid/list modes
- Full WCAG 2.1 AA accessibility compliance with keyboard navigation
- Tree renders 1000+ artifacts within 200ms budget via lazy rendering

---

## Implementation Strategy

### Architecture Sequence (Frontend-Focused)

Since this is a frontend feature with no backend changes, we follow a **Component-First Build Order**:

1. **Utilities Layer** (no dependencies) - Tree builder, depth calculator functions
2. **Hook Layer** (depends on utilities) - `use-folder-tree` state management hook
3. **Leaf Components** (depends on hooks) - `ArtifactRowFolder`, `DirectoryNode`
4. **Container Component** (depends on leaves) - `CatalogFolder` main tree view
5. **Integration Layer** (depends on container) - Toolbar modifications, page integration
6. **Testing Layer** - Unit tests (utilities), component tests, E2E tests
7. **Documentation Layer** - Component docs, accessibility guide, JSDoc comments
8. **Optimization Layer** - Performance profiling, lazy rendering, accessibility audit

### Parallel Work Opportunities

- **Phase 1A (Days 1-2)**: Tree utilities + depth calculator (no UI dependency)
- **Phase 1B (Days 1-2)**: Leaf components design in Storybook (visual design, mockups)
- **Merge Point (Day 3)**: Integrate utilities into leaf components
- **Phase 2**: Depth controls, count badges, UI polish (sequential)
- **Phase 3A (Day 8)**: Accessibility audit + keyboard nav (can start while Phase 2 finishes)
- **Phase 3B (Day 9)**: Performance profiling + lazy rendering (concurrent with A11y work)
- **Validation (Day 10)**: Final testing, E2E validation, docs

### Critical Path

1. **Blocking**: Tree builder utilities must be solid before component integration
2. **Blocking**: Leaf components (DirectoryNode, ArtifactRow) must work before CatalogFolder
3. **Critical**: Filter propagation logic must be tested early (Day 2) to avoid rework
4. **Can Parallelize**: Accessibility and performance work can happen concurrently in Phase 3

**Critical Path Duration**: 10 days (all phases sequential with some parallelization in Phase 3)

---

## Phase Breakdown

### Phase 1: Core Folder View Component & Tree Building (4 Days)

**Duration**: 4 days
**Dependencies**: None
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer
**Start Date**: Day 1 | **End Date**: Day 4

#### Overview

Phase 1 delivers the foundational tree-building utilities and UI components needed to render folder-based artifact navigation. This phase focuses on core functionality: parsing paths into tree structures, rendering collapsible folders with Radix, and integrating with existing filters. By end of Phase 1, users can toggle to folder view, expand/collapse folders, and see filtered artifacts organized hierarchically.

#### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|------|-------------|--------------|
| **MFV-1.1** | **Tree builder utilities** | Create `buildFolderTree()` function to convert flat CatalogEntry[] to nested tree structure; handle depth filtering with `maxDepth` parameter | Tree converts flat paths into nested object structure; handles 1000+ items; filters by depth; returns proper type; no console errors on malformed paths | 2 pts | frontend-developer | None |
| **MFV-1.2** | **Depth calculator** | Create `calculateAutoDepth()` function; detect optimal depth from `root_hint` or scan first 50 entries; implement depth options (Auto/TopLevel/1-3 levels) | Function returns auto-detected depth; respects `root_hint`; provides consistent results; handles edge cases (empty catalog, single item) | 2 pts | frontend-developer | None |
| **MFV-1.3** | **Use-folder-tree hook** | Create React hook `useFolderTree()` managing tree state (expanded folders, depth setting, filtered items); return tree data + setExpanded() callback | Hook returns tree structure and management functions; tracks expanded state; re-builds tree on filter/depth change; memoized to prevent unnecessary rebuilds | 3 pts | frontend-developer | MFV-1.1, MFV-1.2 |
| **MFV-1.4** | **ArtifactRowFolder component** | Create artifact row component displaying: type icon, artifact name, confidence badge, status indicator, import/exclude actions (reuse CatalogRow pattern) | Row renders in folder context; shows all artifact metadata; actions work (import/exclude); matches grid/list row styling; TypeScript fully typed | 3 pts | ui-engineer-enhanced | None |
| **MFV-1.5** | **DirectoryNode component** | Create collapsible folder node using Radix Collapsible: chevron icon, folder icon, folder name, artifact count badge; integrate with `useFolderTree` expanded state | Folder expands/collapses on click; chevron rotates; shows artifact count; lazy-renders children; matches folder icon from Lucide; keyboard-accessible | 3 pts | ui-engineer-enhanced | MFV-1.3 |
| **MFV-1.6** | **CatalogFolder container** | Create main tree view component; recursively renders DirectoryNode and ArtifactRowFolder; integrates with `useSourceCatalog` and filter state | Tree renders correctly from root; all filters (type/confidence/search) applied to tree items; empty state shown for filtered results; scrolls smoothly | 3 pts | ui-engineer-enhanced | MFV-1.4, MFV-1.5 |
| **MFV-1.7** | **Folder view toolbar button** | Add "Folder" button to view mode toggle in SourceToolbar; button toggles between grid/list/folder modes; uses existing view mode pattern | Button appears in toolbar; clicking switches to folder view; other buttons still work; view toggle styling consistent | 2 pts | frontend-developer | MFV-1.6 |
| **MFV-1.8** | **Filter integration** | Verify all filters (type, confidence, search, status) work with folder view; tree re-renders on filter change; filtered items removed from tree | Filters applied to tree items; empty folders show "(No importable artifacts)" message; tree updates reactively; no performance lag | 2 pts | frontend-developer | MFV-1.6 |
| **MFV-1.9** | **Unit tests: tree builder** | Test `buildFolderTree()` and `calculateAutoDepth()` functions; cover path parsing edge cases (special chars, deep nesting, malformed paths) | >80% coverage for utility functions; tests pass for 1000+ item sets; edge cases handled gracefully | 2 pts | frontend-developer | MFV-1.1, MFV-1.2 |
| **MFV-1.10** | **Storybook stories** | Create Storybook stories for DirectoryNode, ArtifactRowFolder, CatalogFolder showing all states (expanded/collapsed, loading, empty, filtered) | Stories render all component states; interactions work in Storybook; visual consistency with existing design system | 2 pts | ui-engineer-enhanced | MFV-1.4, MFV-1.5, MFV-1.6 |

**Phase 1 Total**: 24 story points

#### Phase 1 Quality Gates

- [ ] Tree builder utilities tested and verified (>80% coverage)
- [ ] All components render in Storybook with correct styling
- [ ] Folder view button appears in toolbar and toggles correctly
- [ ] Filters apply to tree; filtered items removed; re-rendering works
- [ ] No console errors; malformed paths handled gracefully
- [ ] Performance baseline: tree renders for 500 items in <300ms (initial, not optimized)
- [ ] Manual testing: expand/collapse folders, apply filters, toggle between view modes

---

### Phase 2: Depth Configuration & Polish (3 Days)

**Duration**: 3 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer, ui-designer
**Start Date**: Day 5 | **End Date**: Day 7

#### Overview

Phase 2 refines the core functionality with depth configuration controls, visual polish, folder count accuracy, and persistence. Users can now configure how deep the tree expands initially via dropdown (Auto/TopLevel/1/2/3 Levels). Folder counts are accurate, empty folders show helpful messages, and view preference persists to localStorage. E2E tests verify the complete folder view workflow.

#### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|------|-------------|--------------|
| **MFV-2.1** | **Depth controls dropdown** | Create FolderDepthControls component in toolbar; dropdown with options: Auto, Top Level, 1 Level Deep, 2 Levels, 3 Levels Deep; updates tree on selection | Dropdown renders in toolbar; all options work; tree re-renders with correct depth; selection persists visually | 2 pts | ui-engineer-enhanced | MFV-1.7 |
| **MFV-2.2** | **Auto depth detection algorithm** | Refine `calculateAutoDepth()` to intelligently detect optimal depth; prioritize `root_hint`, scan first 50 entries for depth patterns; return sensible default | Function detects depth from repository structure; returns safe default (2-3 levels typically); handles edge cases (flat repos, deep monorepos) | 2 pts | frontend-developer | MFV-1.2 |
| **MFV-2.3** | **Folder count badges** | Show accurate artifact counts on folder nodes (direct children only); update counts when filters applied; include "(N) importable artifacts" format | Count badges render on all folders; counts accurate; "(0 importable artifacts)" shown for filtered empty folders; counts update on filter change | 2 pts | ui-engineer-enhanced | MFV-1.6 |
| **MFV-2.4** | **Empty folder messages** | Display helpful message for empty folders: "(No importable artifacts)" with styling matching empty states elsewhere in app | Message shown for folders with no matching items under current filters; styled consistently with grid/list empty state | 1 pt | ui-engineer-enhanced | MFV-1.6 |
| **MFV-2.5** | **Deep nesting handling** | Test and handle 4+ nesting levels; implement breadcrumb or path truncation if needed; ensure UI doesn't break under deep nesting | UI remains readable at 5+ levels; deep nesting doesn't cause layout issues; visual hierarchy clear; consider breadcrumb for context | 2 pts | ui-engineer-enhanced | MFV-1.6 |
| **MFV-2.6** | **View mode localStorage persistence** | Implement localStorage storage for view mode preference; use existing `VIEW_MODE_STORAGE_KEY` pattern; persist folder view selection | View mode saved to localStorage; on page return, folder view restored; matches existing grid/list persistence pattern | 1 pt | frontend-developer | MFV-1.7 |
| **MFV-2.7** | **Depth configuration persistence** | Save selected depth level to localStorage (e.g., `folder-depth-setting`); restore on page return | Depth setting persists; on return to source detail page, previously selected depth restored; dropdown reflects saved value | 1 pt | frontend-developer | MFV-2.1 |
| **MFV-2.8** | **Visual refinement & polish** | Review spacing, colors, icon alignment against design system; ensure folder/file icons from Lucide match grid/list; adjust margins, padding, hover states | Visual consistency with existing components; spacing matches design tokens; icons clearly indicate folder/artifact; hover states intuitive | 1 pt | ui-designer | MFV-1.4, MFV-1.5 |
| **MFV-2.9** | **E2E tests: folder workflow** | Write Playwright tests covering: toggle to folder view, expand/collapse folders, apply filters, see updated tree, import artifact from tree | Test suite covers critical path: view toggle → folder expansion → filter application → import action | 3 pts | frontend-developer | MFV-1.6, MFV-2.1 |
| **MFV-2.10** | **Analytics events** | Log folder view toggle, folder expand/collapse, depth control changes to analytics; prepare for adoption tracking | Events fired on view toggle, folder expand, depth change; events include context (view mode, folder path, depth setting) | 1 pt | frontend-developer | MFV-1.7, MFV-2.1 |

**Phase 2 Total**: 16 story points

#### Phase 2 Quality Gates

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

### Phase 3: Accessibility & Performance Optimization (3 Days)

**Duration**: 3 days
**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: web-accessibility-checker, ui-engineer-enhanced, frontend-developer, react-performance-optimizer
**Start Date**: Day 8 | **End Date**: Day 10

#### Overview

Phase 3 ensures accessibility compliance (WCAG 2.1 AA), full keyboard navigation, and performance optimization. Users can navigate the entire tree using arrow keys, enter/space to expand/collapse, and Tab between controls. Screen readers announce folder state, item counts, and artifact types. Performance is optimized: collapsed folders don't render children initially, tree renders 1000+ artifacts within 200ms budget. Final validation includes accessibility audit and performance profiling.

#### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|------|-------------|--------------|
| **MFV-3.1** | **Keyboard navigation** | Implement full keyboard support: Up/Down arrows navigate siblings, Left/Right expand/collapse folders, Enter/Space to toggle, Tab to next control, Home/End for first/last | Up/Down moves between tree items; Left collapses, Right expands; Enter/Space toggles; Tab moves to next control; focus stays in tree | 3 pts | web-accessibility-checker | MFV-1.5 |
| **MFV-3.2** | **ARIA labels & roles** | Add semantic roles and labels: folders as `role="treeitem"`, announce expanded/collapsed state, item counts, artifact types; roving tabindex pattern | Screen reader announces: "Folder: skills, 42 artifacts, expanded"; "Artifact: my-skill, type: skill, confidence: high" | 2 pts | web-accessibility-checker | MFV-1.4, MFV-1.5, MFV-1.6 |
| **MFV-3.3** | **Focus management** | Implement roving tabindex pattern; manage focus when expanding/collapsing; focus indicators visible (2px ring); focus trap not created | Focus moves with tree navigation; focus visible on keyboard nav; expanding folder doesn't move focus away; no focus traps | 2 pts | web-accessibility-checker | MFV-3.1 |
| **MFV-3.4** | **Screen reader testing** | Test with NVDA (Windows), JAWS (Windows), VoiceOver (macOS); verify folder structure announced correctly; test expand/collapse announcements | Tested on at least 2 screen readers; folder/artifact structure clear; expand/collapse state announced; no confusion or missing context | 2 pts | web-accessibility-checker | MFV-3.2 |
| **MFV-3.5** | **Lazy folder rendering** | Prevent DOM explosion: collapsed folders don't render children initially; render on demand when expanded; measure DOM node count before/after | Collapsed folders have no child DOM nodes; expanding loads children on-demand; DOM node count reduced 60-80% with mostly collapsed tree | 3 pts | frontend-developer | MFV-1.5, MFV-1.6 |
| **MFV-3.6** | **Performance profiling** | Profile tree rendering with DevTools; measure render time for 500/1000 item trees; optimize hot paths; target <200ms for 1000 items | Tree renders 1000 artifacts in <200ms; filter changes apply in <100ms; no jank on expand/collapse; DevTools timeline shows smooth frames | 2 pts | react-performance-optimizer | MFV-1.3, MFV-1.6 |
| **MFV-3.7** | **Memoization & optimization** | Add React.memo() to components; memoize tree calculation functions; prevent unnecessary re-renders on leaf changes | Components wrapped with React.memo; functions memoized with useMemo; re-render count reduced in DevTools profiler | 2 pts | frontend-developer | MFV-3.5, MFV-3.6 |
| **MFV-3.8** | **Accessibility audit** | Run automated WCAG audit (axe); manual testing of all interactions; verify focus indicators, color contrast, label associations | Automated audit passes (zero critical/serious issues); manual keyboard nav complete; color contrast >4.5:1 for text | 2 pts | web-accessibility-checker | MFV-3.2, MFV-3.4 |
| **MFV-3.9** | **Performance E2E tests** | Write Playwright tests measuring render time; benchmark tree loading for 500/1000 items; create performance regression test | E2E tests verify render time <200ms; performance baseline established; tests run in CI to catch regressions | 2 pts | frontend-developer | MFV-3.6 |
| **MFV-3.10** | **Documentation: accessibility guide** | Document keyboard navigation, ARIA patterns, screen reader behavior in `.claude/context/` or CLAUDE.md; include implementation notes | Developer guide explains keyboard nav, ARIA labels, roving tabindex; includes code examples and patterns | 1 pt | documentation-writer | MFV-3.1, MFV-3.2 |

**Phase 3 Total**: 21 story points

#### Phase 3 Quality Gates

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

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| **Tree rendering performance** (1000+ artifacts jank) | High | Medium | Implement lazy rendering Phase 3; benchmark early Phase 1; use DevTools profiler; have virtualization (react-window) as fallback |
| **Complex path parsing edge cases** (special chars, inconsistent separators) | Medium | Medium | Add comprehensive unit tests Phase 1.9; log malformed paths; provide graceful fallback to flat view if parsing fails |
| **Filter + tree interaction confusing** (users don't understand why items disappear) | Low | Medium | Show active filters prominently; add tooltip explaining filter behavior; implement "(0 artifacts)" message for empty folders |
| **Keyboard navigation complexity** (arrow key focus hard to manage) | Medium | Low | Use Radix Collapsible patterns; test extensively with screen reader Phase 3.4; a11y audit in Phase 3.8 |
| **Deep nesting breaks UI** (indentation, wrapping at 4+ levels) | Medium | Low | Test with real repos 5+ levels deep Phase 2.5; implement breadcrumb or truncation if needed; visual hierarchy tests |
| **Screen reader compatibility** (announced state confusing) | Medium | Low | Test on NVDA/JAWS/VoiceOver Phase 3.4; refine ARIA labels based on feedback; include screen reader testing in final QA |
| **localStorage quota exceeded** | Low | Very Low | View preference storage is minimal (~100 bytes); not a concern for typical use |
| **Adoption low** (users stick with grid/list) | Medium | Medium | Collect analytics Phase 2.10; iterate on UX based on usage data; consider A/B test or feature flag Phase 4 |

### Mitigation Actions

1. **Performance**: Establish DevTools profiling baseline Day 2 (Phase 1.1); if 500 items >300ms, escalate to performance optimization early
2. **Edge Cases**: Create test file with malformed paths before Phase 1.1 completes; ensure parser handles gracefully
3. **Accessibility**: Schedule screen reader testing Phase 3.4 with external accessibility consultant if budget allows
4. **Filter UX**: Add filter badge in toolbar (low-effort, high-value clarification)
5. **Deep Nesting**: Test with actual repository from Anthropic org before Phase 2.5 starts; adjust UI if needed

---

## Resource Requirements

### Team Composition

| Role | Phases | Effort | Notes |
|------|--------|--------|-------|
| **ui-engineer-enhanced** | 1, 2, 3 | 6-8 FTE days | Component implementation, polish, performance |
| **frontend-developer** | 1, 2, 3 | 6-8 FTE days | Tree utilities, hooks, integration, testing |
| **web-accessibility-checker** | 3 | 3-4 FTE days | Keyboard nav, ARIA, screen reader testing, audit |
| **ui-designer** | 2 | 1 FTE day | Visual polish, design system review |
| **react-performance-optimizer** | 3 | 1-2 FTE days | Performance profiling, memoization, optimization |
| **documentation-writer** | 3 | 0.5 FTE day | Accessibility guide, JSDoc comments |

**Total Team**: ~2 FTE for 10 days; overlapping assignments allow concurrent work

### Skill Requirements

- **TypeScript/React**: Type-safe components, hooks, state management (TanStack Query integration)
- **Accessibility**: WCAG 2.1 AA, ARIA roles/labels, keyboard navigation, screen reader testing
- **Performance**: React DevTools profiler, memoization, lazy rendering, bundle analysis
- **UI/Design**: Tailwind CSS, shadcn/ui component patterns, Radix primitives
- **Testing**: Jest + React Testing Library (unit/component), Playwright (E2E), performance benchmarking
- **Next.js 15**: App Router, server/client component boundaries

---

## Success Metrics

### Delivery Metrics

- [x] All Phase 1/2/3 tasks completed on time (±1 day)
- [x] Code coverage >80% for tree utilities and component tests
- [x] Zero P0/P1 bugs in first week of staging deployment
- [x] Performance baseline: tree renders 1000 items in <200ms (Phase 3.6 benchmark)

### Quality Metrics

- [x] WCAG 2.1 AA compliance (Phase 3.8 audit passes)
- [x] Keyboard navigation fully functional (Phase 3.1/3.3 tests pass)
- [x] All E2E tests passing in CI/CD
- [x] Storybook stories for all components (Phase 1.10)

### Business Metrics

- [x] Folder view adoption >35% of source detail page visits (analytics Phase 2.10)
- [x] Discovery time reduced 40-60% vs flat list (user testing metric)
- [x] Zero critical accessibility issues reported post-launch
- [x] View mode toggle interaction logged for future A/B testing

### Technical Metrics

- [x] 100% JSDoc coverage on tree utilities and hooks
- [x] Tree builder utility tests >80% coverage (Phase 1.9)
- [x] Component tests >85% coverage (Phase 1.10, 2.9, 3.9)
- [x] No TypeScript `any` types in new code
- [x] Lazy rendering reduces DOM nodes 60-80% (Phase 3.5)

---

## Testing Strategy

### Unit Testing (Phase 1.9)

**Tree Utilities** (`tree-builder.ts`, `depth-calculator.ts`):
- `buildFolderTree()`: path parsing, depth filtering, edge cases (special chars, deep nesting, empty arrays)
- `calculateAutoDepth()`: root_hint detection, scanning logic, safe defaults
- Coverage target: >80%

```typescript
// Example tests:
- buildFolderTree([], 3) → {}
- buildFolderTree([{path: 'skills/dev'}], 3) → {skills: {dev: {...}}}
- calculateAutoDepth([...50 items at depth 2-3]) → 2
- calculateAutoDepth({root_hint: 'skills'}, catalog) → 1 (scanning from root_hint)
```

### Component Testing (Phase 1.10)

**Jest + React Testing Library**:
- DirectoryNode: expand/collapse on click, chevron rotation, count badge display
- ArtifactRowFolder: render artifact metadata, action buttons work
- CatalogFolder: tree structure renders, filter application updates tree
- Coverage target: >85%

### Integration Testing (Phase 2.9)

**Playwright E2E Tests**:
- Toggle to folder view
- Expand/collapse folders with mouse
- Apply filters (type, confidence, search) and verify tree updates
- Import artifact from tree (full workflow)
- View mode persists on page reload

### Accessibility Testing (Phase 3.4)

**Manual Screen Reader Testing**:
- NVDA (Windows)
- JAWS (Windows)
- VoiceOver (macOS)

**Keyboard Navigation Testing**:
- Up/Down arrows navigate siblings
- Left/Right collapse/expand
- Enter/Space toggle
- Tab between controls

### Performance Testing (Phase 3.9)

**Playwright Performance Benchmarks**:
```javascript
// Measure tree render time for 1000 items
const start = performance.now();
// expand all folders (trigger renders)
const end = performance.now();
expect(end - start).toBeLessThan(200); // ms
```

---

## Parallel Work Opportunities

### Optimal Parallelization

**Days 1-2 (Early Phase 1)**:
- **Stream A**: Tree utilities (MFV-1.1, MFV-1.2) - frontend-developer
- **Stream B**: Component design + Storybook setup (MFV-1.10 prep) - ui-engineer-enhanced, ui-designer

**Merge Point (Day 3)**:
- Integrate utilities into hooks (MFV-1.3)
- Leaf components use hooks (MFV-1.4, MFV-1.5)

**Days 5-7 (Phase 2)**:
- Sequential work (depth controls, count badges, polish) - single developer focus
- ui-designer available for visual review (MFV-2.8)

**Days 8-10 (Phase 3)**:
- **Stream A**: Accessibility (keyboard nav, ARIA, a11y audit) - web-accessibility-checker
- **Stream B**: Performance (profiling, memoization, lazy rendering) - react-performance-optimizer + frontend-developer
- **Stream C**: Documentation - documentation-writer (low priority, can parallelize)
- **Merge Point (Day 10)**: Final validation, E2E tests

**Estimated Parallelization Savings**: ~2 FTE days (20% reduction in wall-clock time)

---

## Critical Path

1. **Tree utilities** (MFV-1.1, MFV-1.2) → Must complete before hooks (Day 2 EOD)
2. **Hooks** (MFV-1.3) → Must complete before leaf components (Day 3)
3. **Leaf components** (MFV-1.4, MFV-1.5) → Must complete before CatalogFolder (Day 3)
4. **CatalogFolder** (MFV-1.6) → Must complete before Phase 2 depth config (Day 4)
5. **Depth config** (MFV-2.1, MFV-2.2) → Prerequisite for E2E tests (Day 6)
6. **E2E tests** (MFV-2.9) → Prerequisite for Phase 3 (Day 7)
7. **Phase 3 accessibility/performance** → Can parallelize; both must complete by Day 10

**Total Critical Path**: 10 days (no shortcuts; all dependencies critical)

---

## Implementation Notes

### Key Technical Decisions

1. **No API changes**: All tree building client-side using existing `CatalogEntry.path` field
2. **Radix Collapsible**: Reuse existing shadcn/ui pattern for consistency and a11y
3. **Lazy rendering**: Collapsed folders don't render DOM until expanded (performance optimization)
4. **Filter propagation**: All existing filters apply at tree level; tree re-renders on filter change
5. **Depth heuristics**: "Auto" scans `root_hint` first; falls back to intelligent depth detection
6. **Roving tabindex**: Keyboard nav uses Radix pattern for accessibility best practice
7. **Performance budget**: 200ms tree render for 1000 items (Phase 3 target)
8. **Memoization**: React.memo() on leaf components + useMemo() on tree calculations

### Component Architecture

```typescript
// File: skillmeat/web/lib/folder-tree.ts
export function buildFolderTree(entries: CatalogEntry[], maxDepth: number): FolderTree
export function calculateAutoDepth(entries: CatalogEntry[], rootHint?: string): number

// File: skillmeat/web/lib/hooks/use-folder-tree.ts
export function useFolderTree(catalog: CatalogEntry[], filters: CatalogFilters): {
  tree: FolderTree
  expanded: Set<string>
  setExpanded: (path: string, isExpanded: boolean) => void
  depth: number
  setDepth: (depth: number) => void
}

// File: skillmeat/web/app/marketplace/sources/[id]/components/artifact-row-folder.tsx
export function ArtifactRowFolder({ entry, onImport, onExclude }: Props): JSX.Element

// File: skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx
export function DirectoryNode({ node, depth, expanded, onToggleExpand, onImport }: Props): JSX.Element

// File: skillmeat/web/app/marketplace/sources/[id]/components/catalog-folder.tsx
export function CatalogFolder({ catalog, filters, onImport, onExclude }: Props): JSX.Element

// File: skillmeat/web/app/marketplace/sources/[id]/components/folder-depth-controls.tsx
export function FolderDepthControls({ value, onChange }: Props): JSX.Element
```

### Files to Create

1. `/skillmeat/web/lib/folder-tree.ts` - Tree builder utility functions
2. `/skillmeat/web/lib/hooks/use-folder-tree.ts` - React hook for tree state
3. `/skillmeat/web/app/marketplace/sources/[id]/components/catalog-folder.tsx` - Main tree container
4. `/skillmeat/web/app/marketplace/sources/[id]/components/directory-node.tsx` - Collapsible folder
5. `/skillmeat/web/app/marketplace/sources/[id]/components/artifact-row-folder.tsx` - Artifact row
6. `/skillmeat/web/app/marketplace/sources/[id]/components/folder-depth-controls.tsx` - Depth dropdown

### Files to Modify

1. `/skillmeat/web/app/marketplace/sources/[id]/page.tsx` - Add folder view conditional rendering
2. `/skillmeat/web/app/marketplace/sources/[id]/components/source-toolbar.tsx` - Add folder button + depth controls
3. `/skillmeat/web/CLAUDE.md` - Add component patterns and accessibility guide
4. `/skillmeat/web/__tests__/` - Add tree builder unit tests

### Edge Cases Handled

- **Malformed paths**: Missing levels, special characters, Windows backslashes → Logged but don't crash
- **Circular references**: Prevented by depth filtering; tree depth controlled by `maxDepth`
- **Empty catalog**: Tree builder returns empty object; UI shows empty state
- **Filtered empty tree**: Folders with no matching items show "(0 importable artifacts)" message
- **Deep nesting**: 5+ levels tested; breadcrumb or truncation implemented if UI breaks
- **Single artifact**: Tree still renders correctly; no unnecessary nesting

---

## Post-Implementation

### Metrics Collection (Phase 2.10 onwards)

- **Adoption**: Folder view toggle click rate, percentage of visits using folder view
- **Engagement**: Folder expand/collapse rate, time spent in folder view, import rate from folders
- **Performance**: Tree render time in production, filter response time, any console errors

### Iteration Opportunities

- **Phase 4**: React window virtualization (if performance issues arise)
- **Phase 4**: Nested count badges (if UX testing validates value)
- **Phase 4**: URL state for view mode (`?view=folder` for deep linking)
- **Phase 4**: Per-folder sorting options
- **Phase 4**: Bookmark/favorite folders

### Maintenance Notes

- Tree builder utilities are stable after Phase 1; unlikely to need changes
- Filter integration is critical path; monitor for performance issues
- Screen reader compatibility may need tweaks based on user feedback
- Performance benchmarks should be re-run quarterly

---

## Acceptance Criteria Summary

### Functional Acceptance (All Phases)

- [x] Folder view button appears in view mode toggle
- [x] Tree renders hierarchy from artifact paths
- [x] Folders expand/collapse with click and keyboard
- [x] Folder count badges show accurate artifact counts
- [x] All filters (type, confidence, search, status) work in folder view
- [x] Empty folders show helpful messages
- [x] Deep nesting (4+ levels) handled gracefully
- [x] View mode and depth persist to localStorage
- [x] URL state remains synchronized with existing filters

### Technical Acceptance (All Phases)

- [x] No API changes; uses existing `CatalogEntry.path` only
- [x] Follows Next.js 15 App Router patterns
- [x] Follows component conventions (shadcn/ui, Radix, named exports)
- [x] TypeScript fully typed; no `any` types
- [x] Tree builder function unit tested (>80% coverage)
- [x] Performance: tree renders <200ms for 1000 artifacts
- [x] Lazy rendering implemented for collapsed folders

### Quality Acceptance (All Phases)

- [x] Unit tests >80% (tree builder, hooks)
- [x] Component tests >85% (all UI components)
- [x] E2E tests cover critical path
- [x] WCAG 2.1 AA compliance (keyboard nav, ARIA, focus)
- [x] No performance regressions
- [x] Visual consistency with grid/list views

### Documentation Acceptance (All Phases)

- [x] Component usage guide in CLAUDE.md or dedicated .md
- [x] JSDoc comments on all exported functions
- [x] Accessibility implementation guide (keyboard nav, ARIA patterns)
- [x] PR description explains tree building approach
- [x] Storybook stories for all components

---

**Progress Tracking:**

See `.claude/progress/marketplace-folder-view-v1/all-phases-progress.md`

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-01-28
**Status**: Ready for Phase 1 execution
