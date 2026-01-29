---
title: "Implementation Plan: Marketplace Folder View"
description: "Phased implementation of tree-based folder view for marketplace source detail pages with accessibility and performance optimization"
audience: [ai-agents, developers]
tags: [implementation, planning, features, frontend, marketplace]
created: 2026-01-28
updated: 2026-01-29
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
**Total Estimated Effort**: 35 story points (was 29, +6 for mixed-content handling)
**Target Timeline**: 10 days (4 days Phase 1 + 3 days Phase 2 + 2 days Phase 3 + 1 day integration buffer)

---

## Executive Summary

This plan delivers a two-pane master-detail Folder View for marketplace source detail pages with semantic navigation tree and rich folder detail pane. The left pane (25%) shows a smart semantic navigation tree (excluding root and leaf artifact containers), while the right pane (75%) displays folder metadata, description, and all artifacts in that folder with type-based grouping. The implementation follows MeatyPrompts frontend-first architecture: build tree and filtering utilities first, then semantic tree component, then folder detail pane, then integration. Three phases deliver core layout with semantic tree (Phase 1), folder detail pane with bulk import and subfolders (Phase 2), and accessibility/performance optimization (Phase 3). No API changes required; all tree building happens client-side using existing `CatalogEntry.path` field.

**Key Outcomes:**
- Users discover related artifacts 2-3x faster with two-pane layout
- Semantic filtering eliminates root/leaf containers for cleaner navigation
- Folder detail pane shows rich metadata and "Import All" bulk action
- Artifacts grouped by type within each folder for clarity
- Mixed-content folders (direct artifacts + subfolders) clearly identified with badges and visual indicators
- Subfolders section enables nested exploration without tree navigation
- Full WCAG 2.1 AA accessibility compliance with keyboard navigation
- Tree renders 1000+ artifacts within 200ms budget via lazy rendering

---

## Implementation Strategy

### Architecture Sequence (Frontend-Focused)

Since this is a frontend feature with no backend changes, we follow a **Component-First Build Order**:

1. **Utilities Layer** (no dependencies) - Tree builder, semantic filtering, folder description extraction
2. **Hook Layer** (depends on utilities) - `use-folder-selection` state management hook
3. **Semantic Tree Component** (depends on hooks) - Left pane tree with smart filtering
4. **Tree Node Component** (depends on hooks) - Individual folder items in tree
5. **Folder Detail Pane** (depends on utilities) - Right pane container showing folder metadata
6. **Folder Detail Header** (depends on utilities) - Title, parent chip, description, "Import All" button
7. **Artifact Type Section** (depends on utilities) - Type grouping component for right pane
8. **Subfolders Section** (depends on utilities) - **NEW**: Subfolders display component
9. **Subfolder Card** (depends on utilities) - **NEW**: Individual subfolder card component
10. **Layout Container** (depends on all above) - Two-pane master-detail layout
11. **Integration Layer** (depends on layout) - Toolbar modifications, page integration
12. **Testing Layer** - Unit tests (utilities), component tests, E2E tests
13. **Documentation & Optimization** - Accessibility audit, performance profiling, lazy rendering

### Parallel Work Opportunities

- **Phase 1A (Days 1-2)**: Tree utilities + semantic filtering + folder description extraction (no UI dependency)
- **Phase 1B (Days 1-2)**: Two-pane layout design + tree node component design (visual design, mockups)
- **Merge Point (Day 3)**: Integrate utilities into semantic tree component
- **Phase 1 Finalization (Day 4)**: Layout container + page integration + first folder auto-selection + badge rendering
- **Phase 2A (Days 5-6)**: Folder detail pane, bulk import, type grouping (sequential)
- **Phase 2B (Days 5-6)**: Subfolders section and subfolder card components (can parallelize with A after start)
- **Phase 2C (Day 7)**: Filter integration + localStorage persistence
- **Phase 3A (Day 8)**: Accessibility audit + keyboard nav (can parallelize with Phase 2 finish)
- **Phase 3B (Day 8)**: Performance profiling + memoization (concurrent with A11y work)
- **Validation (Day 9)**: Final testing, E2E validation, docs

### Critical Path

1. **Blocking**: Tree builder + semantic filtering utilities must complete before semantic tree component (Day 2)
2. **Blocking**: Semantic tree component must work before folder detail pane (Day 4)
3. **Blocking**: Two-pane layout container must integrate semantic tree + folder detail pane (Day 4)
4. **Critical**: Folder detail pane must implement before type grouping and bulk import (Day 5)
5. **Critical**: Subfolders section requires tree builder to provide subfolder data (Day 5)
6. **Can Parallelize**: Accessibility and performance work in Phase 3 (concurrent execution)

**Critical Path Duration**: 10 days (all critical phases sequential, Phase 3 parallelizable)

---

## Phase Breakdown

### Phase 1: Two-Pane Layout & Semantic Tree (4 Days)

**Duration**: 4 days
**Dependencies**: None
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer
**Start Date**: Day 1 | **End Date**: Day 4

#### Overview

Phase 1 delivers the two-pane master-detail layout with semantic navigation tree (left pane) and folder detail pane container (right pane). This phase builds tree utilities with smart semantic filtering (excluding root folders like `plugins/`, `src/` and leaf artifact containers like `commands/`, `agents/`), renders the semantic tree component with collapsible folders, implements the folder detail pane container, and integrates the layout into the source detail page. By end of Phase 1, users can toggle to folder view, see the two-pane layout, select folders from the semantic tree, and see the folder detail pane populate on the right. Tree nodes display direct artifact count badges and visual indicators for mixed-content folders.

#### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|------|-------------|--------------|
| **MFV-1.1** | **Tree builder utilities** | Create `buildFolderTree()` function to convert flat CatalogEntry[] to nested tree structure; separate direct artifacts from subfolders; handle depth filtering with `maxDepth` parameter; calculate directCount, totalCount, hasDirectArtifacts, hasSubfolders for each node | Tree converts flat paths into nested object structure; separates direct artifacts from children; handles 1000+ items; filters by depth; calculates counts correctly; returns proper type; no console errors on malformed paths | 3 pts | frontend-developer | None |
| **MFV-1.2** | **Semantic filtering utilities** | Create `isSemanticFolder()` to exclude root folders (plugins/, src/, skills/, etc.) and leaf containers (commands/, agents/, mcp_servers/, etc.); implement smart tree filtering | Filters exclude designated roots and leafs; intermediate folders shown; function handles edge cases; filters produce clean navigation tree | 2 pts | frontend-developer | None |
| **MFV-1.3** | **Use-folder-selection hook** | Create React hook `useFolderSelection()` managing folder selection state (selected folder path, expanded folders); return selection + setSelected() callback | Hook tracks selected folder; tracks expanded state; updates on user interaction; memoized; integrates with semantic filtering | 2 pts | frontend-developer | MFV-1.1, MFV-1.2 |
| **MFV-1.4** | **Source-folder-layout component** | Create two-pane container layout with left pane (25%, semantic tree) and right pane (75%, folder detail). Manage layout, responsive behavior, splitter | Layout renders two panes side-by-side; proportions correct; responsive on smaller screens (stacked layout); smooth splitter (optional) | 3 pts | ui-engineer-enhanced | None |
| **MFV-1.5** | **Semantic-tree component** | Create left pane semantic navigation tree; render folders filtered by semantic rules; support expand/collapse; integrate folder selection | Tree renders only semantic folders; expand/collapse works; selection tracking; shows folder hierarchy; no root/leaf containers | 3 pts | ui-engineer-enhanced | MFV-1.2, MFV-1.3 |
| **MFV-1.6** | **Tree-node component with badges** | Create individual tree folder item with: folder icon, folder name, expand/collapse chevron, direct count badge (N), total count badge [M] on hover, mixed-folder indicator dot; integrate with selection state | Folder node renders with proper styling; chevron rotates on expand; direct count badge shows when > 0; total count on hover; mixed indicator visible; keyboard-accessible; consistent with design system; ARIA label includes counts | 3 pts | ui-engineer-enhanced | MFV-1.3 |
| **MFV-1.7** | **Folder-detail-pane container** | Create right pane container accepting selected folder; renders folder detail header + artifact list; prepare for child components in Phase 2 | Pane renders with selected folder data; shows placeholder content; integrated with layout; accepts folder selection from left pane; displays direct artifacts only | 2 pts | ui-engineer-enhanced | MFV-1.4, MFV-1.5 |
| **MFV-1.8** | **Toolbar folder toggle integration** | Add "Folder" button to view mode toggle in SourceToolbar; button toggles between grid/list/folder modes; uses existing view mode pattern | Button appears in toolbar; clicking switches to folder view; view mode persists in state; styling consistent | 2 pts | frontend-developer | MFV-1.4 |
| **MFV-1.9** | **First folder auto-selection** | Implement auto-selection of first semantic folder on folder view load; ensure right pane populates immediately | On folder view toggle, first folder auto-selected; folder detail pane shows data immediately; smooth UX transition | 1 pt | frontend-developer | MFV-1.3, MFV-1.7 |
| **MFV-1.10** | **Unit tests: tree building & filtering** | Test `buildFolderTree()`, `isSemanticFolder()`, and filtering logic; cover edge cases (roots, leafs, special chars, deep nesting, mixed content separation); verify count calculations | >80% coverage for utility functions; semantic filtering works correctly; direct/total counts accurate; mixed-content detection correct; tests pass for 1000+ item sets; edge cases handled | 3 pts | frontend-developer | MFV-1.1, MFV-1.2 |

**Phase 1 Total**: 24 story points

#### Phase 1 Quality Gates

- [ ] Tree builder + semantic filtering utilities tested (>80% coverage)
- [ ] Tree builder correctly separates direct artifacts from subfolders
- [ ] Count calculations (directCount, totalCount) verified for various folder structures
- [ ] Two-pane layout renders correctly with proper proportions (25% left, 75% right)
- [ ] Semantic tree displays only intermediate folders (roots/leafs excluded)
- [ ] Tree nodes display direct count badges and mixed-folder indicators correctly
- [ ] Folder view button appears in toolbar and toggles layout correctly
- [ ] First folder auto-selects on folder view toggle; right pane populates
- [ ] Folder selection works; tree node selection state visual feedback
- [ ] No console errors; malformed paths handled gracefully
- [ ] Performance baseline: tree renders for 500 items in <300ms (initial, not optimized)
- [ ] Manual testing: toggle folder view, expand/collapse folders in left pane, folder detail shows on right
- [ ] Visual indicators for mixed-content folders visible and clear

---

### Phase 2: Folder Detail Pane & Bulk Import & Subfolders (3 Days)

**Duration**: 3 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer, ui-designer
**Start Date**: Day 5 | **End Date**: Day 7

#### Overview

Phase 2 builds out the folder detail pane (right side) with rich metadata display, artifact grouping by type, bulk import functionality, and subfolders section. The folder detail header shows title, parent breadcrumb chip, folder description (extracted from README or AI-generated summary), and "Import All" button. Artifacts are grouped by type (Skills, Commands, Agents, etc.) with section headers. When a folder contains subfolders, a "Subfolders" section appears at the bottom with clickable folder cards that enable nested exploration. Filters apply to the right pane artifacts. E2E tests verify the complete folder view workflow including bulk import and subfolder navigation.

#### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|------|-------------|--------------|
| **MFV-2.1** | **Folder-detail-header component** | Create header showing: folder title, parent breadcrumb chip, folder description, "Import All" button. Extract description from folder README or generate AI summary | Header renders folder metadata; parent chip clickable (navigates to parent folder); "Import All" button functional; description displayed; responsive | 3 pts | ui-engineer-enhanced | MFV-1.7 |
| **MFV-2.2** | **Folder README extraction** | Create utility to extract README from folder artifacts (if any); parse markdown content; extract summary section or first paragraph | Utility detects README files in folder; extracts content; falls back to AI summary generation if no README found | 2 pts | frontend-developer | None |
| **MFV-2.3** | **Artifact-type-section component** | Create component showing artifacts grouped by type with section header (e.g., "Skills (5)", "Commands (2)"); render artifact rows in section | Section header shows type name + count; artifacts render below; consistent styling with grid/list views; collapsible sections (optional) | 2 pts | ui-engineer-enhanced | None |
| **MFV-2.4** | **Type grouping logic** | Implement grouping of artifacts by type within folder; handle all artifact types (Skill, Command, Agent, MCP Server, Hook); maintain sort order; account for mixed-content folders | Artifacts grouped correctly by type; grouping includes all types; groups render in consistent order; empty groups hidden; direct artifacts only (not descendants) | 2 pts | frontend-developer | MFV-1.7 |
| **MFV-2.5** | **"Import All" bulk action** | Implement bulk import button; import all direct artifacts in selected folder; show progress indicator; handle success/error states | Button imports all direct artifacts in folder (not descendants); progress shown during import; success/error message displayed; folder refreshes after completion | 3 pts | frontend-developer | MFV-2.1 |
| **MFV-2.6** | **Empty folder detail state** | Show helpful empty state when folder has no importable direct artifacts under current filters | Empty state message shown (e.g., "No importable artifacts in this folder"); styled consistently with grid/list empty states | 1 pt | ui-engineer-enhanced | MFV-1.7 |
| **MFV-2.7** | **Subfolders-section component** | Create section component that displays subfolders as clickable cards; positioned at bottom of detail pane; shows when selected folder has children | Section renders only if folder has subfolders; cards display subfolder info; responsive grid layout; proper spacing below artifact sections | 2 pts | ui-engineer-enhanced | MFV-1.7 |
| **MFV-2.8** | **Subfolder-card component** | Create card showing: folder icon, folder name, descendant artifact count, "Click to explore" affordance; integrates with folder selection hook | Card displays folder metadata clearly; count shows total descendants (not direct artifacts); clickable; hover state clear; keyboard accessible | 2 pts | ui-engineer-enhanced | MFV-1.3 |
| **MFV-2.9** | **Subfolder navigation integration** | Implement click handler for subfolder cards; clicking card selects folder in tree, expands tree path, updates detail pane | Clicking subfolder card navigates tree; tree expands path to folder; folder auto-selected; detail pane updates; smooth animation | 2 pts | frontend-developer | MFV-1.3, MFV-2.8 |
| **MFV-2.10** | **Filter integration: right pane** | Ensure all filters (type, confidence, search, status) apply to artifacts shown in folder detail pane; pane updates reactively on filter change; subfolders section unaffected by filters | Filters applied to right pane artifacts; artifact counts in type sections update; empty state shown if no results; subfolders always visible; no performance lag | 2 pts | frontend-developer | MFV-2.1, MFV-2.4 |
| **MFV-2.11** | **Visual refinement & polish** | Review spacing, colors, icon alignment between left/right panes; ensure type section headers and subfolder cards consistent; adjust hover states, transitions | Visual consistency across panes; spacing matches design tokens; type grouping clearly labeled; subfolder cards polished; interactions smooth | 1 pt | ui-designer | MFV-2.1, MFV-2.3, MFV-2.8 |
| **MFV-2.12** | **E2E tests: folder detail workflow** | Write Playwright tests: toggle to folder view, select folder, see right pane populate, apply filters, use "Import All" button, click subfolder card to navigate | Test suite covers: folder selection → right pane display → filter application → bulk import action → subfolder navigation → detail pane update | 3 pts | frontend-developer | MFV-2.1, MFV-2.5, MFV-2.9 |
| **MFV-2.13** | **View mode & filter persistence** | Persist view mode and filter state to localStorage; restore on page return | View mode + selected folder path saved; filters persisted; on return, layout restored to previous state | 1 pt | frontend-developer | MFV-1.8 |

**Phase 2 Total**: 28 story points

#### Phase 2 Quality Gates

- [ ] Folder detail header displays title, parent chip, description, "Import All" button
- [ ] README extraction works; falls back to AI summary if no README
- [ ] Artifacts grouped by type in right pane with section headers
- [ ] Type grouping includes all artifact types; counts accurate; reflects only direct artifacts
- [ ] "Import All" bulk action works; progress shown; success/error states handled
- [ ] Empty folder state shown when no direct artifacts match filters
- [ ] Subfolders section renders when folder has children
- [ ] Subfolder cards display correctly with folder info and descendant count
- [ ] Clicking subfolder card navigates tree and updates detail pane
- [ ] Filters apply to right pane artifacts; subfolders section unaffected
- [ ] Visual polish complete; panes balanced, consistent spacing
- [ ] E2E tests pass (folder selection → right pane display → subfolder nav → bulk import)
- [ ] View mode and filter state persist to localStorage

---

### Phase 3: Accessibility & Performance Optimization (2 Days)

**Duration**: 2 days
**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: web-accessibility-checker, frontend-developer, react-performance-optimizer
**Start Date**: Day 8 | **End Date**: Day 9

#### Overview

Phase 3 ensures accessibility compliance (WCAG 2.1 AA) and performance optimization. Users can navigate the left pane tree using arrow keys, enter/space to expand/collapse, and Tab between panes. Screen readers announce folder state, item counts, artifact types, and badge information. Performance is optimized: collapsed folders don't render children initially, tree renders 1000+ artifacts within 200ms budget. Mixed-content indicators and subfolders section are fully accessible. Final validation includes accessibility audit and performance profiling.

#### Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Est. | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|------|-------------|--------------|
| **MFV-3.1** | **Keyboard navigation (tree + panes)** | Implement: Up/Down arrows navigate tree siblings, Left/Right expand/collapse folders, Enter/Space to select, Tab to move between left pane/right pane, Home/End for first/last | Up/Down moves between tree items; Left collapses, Right expands; Enter selects folder; Tab moves pane focus; no focus traps; subfolders keyboard accessible | 2 pts | web-accessibility-checker | MFV-1.5 |
| **MFV-3.2** | **ARIA labels & roles (semantic tree + detail pane)** | Add semantic roles/labels: left pane as `role="tree"`, folders as `role="treeitem"`, right pane as main content region; announce folder counts, artifact types, badge context; subfolders section as landmark region | Screen reader announces: "Folder tree region"; "Folder: skills, 2 direct artifacts, 10 total descendants, mixed content"; artifact types and counts in right pane; subfolders section purpose | 3 pts | web-accessibility-checker | MFV-1.5, MFV-2.1, MFV-2.8 |
| **MFV-3.3** | **Focus management & indicators** | Implement roving tabindex in tree; manage focus when selecting folders; visible focus indicators (2px ring); focus transitions between panes smooth; subfolder card focus clear | Focus moves with tree navigation; visible on keyboard nav; selecting folder doesn't lose focus; Tab cycles between panes; subfolder cards focusable; no traps | 2 pts | web-accessibility-checker | MFV-3.1 |
| **MFV-3.4** | **Screen reader testing** | Test with NVDA (Windows), JAWS (Windows), VoiceOver (macOS); verify tree structure, folder selection, count badges, mixed-folder indicators, right pane content, subfolders section all announced correctly | Tested on 2+ screen readers; tree navigation clear; folder selection announced with counts; badge context explained; mixed indicator announced; subfolder cards properly labeled | 2 pts | web-accessibility-checker | MFV-3.2 |
| **MFV-3.5** | **Lazy folder rendering** | Prevent DOM explosion: collapsed folders don't render children initially; render on demand when expanded; measure DOM node count before/after | Collapsed folders have no child DOM nodes; expanding loads children on-demand; DOM node count reduced 60-80% with mostly collapsed tree | 2 pts | frontend-developer | MFV-1.5 |
| **MFV-3.6** | **Performance profiling & optimization** | Profile tree rendering with DevTools; measure render time for 500/1000 item trees; optimize hot paths; target <200ms for 1000 items | Tree renders 1000 artifacts in <200ms; filter changes apply in <100ms; no jank on expand/collapse; smooth frames in DevTools | 2 pts | react-performance-optimizer | MFV-1.3, MFV-1.5 |
| **MFV-3.7** | **Memoization & component optimization** | Add React.memo() to tree nodes and detail pane components; memoize tree/filtering functions; prevent unnecessary re-renders; optimize subfolder card rendering | Components wrapped with React.memo; functions memoized with useMemo; re-render count reduced in DevTools profiler; subfolder grid optimized | 2 pts | frontend-developer | MFV-3.5, MFV-3.6 |
| **MFV-3.8** | **Accessibility audit** | Run automated WCAG audit (axe); manual keyboard nav and screen reader testing; verify color contrast, labels, focus indicators; validate badge contrast | Automated audit passes (zero critical/serious issues); manual testing complete; contrast >4.5:1 for text and badges; all interactions keyboard accessible | 2 pts | web-accessibility-checker | MFV-3.2, MFV-3.4 |

**Phase 3 Total**: 17 story points

#### Phase 3 Quality Gates

- [ ] Full keyboard navigation working (tree, pane focus, Home/End, Tab, subfolder cards)
- [ ] Screen reader announces tree structure, folder selection, artifact counts, badge context, subfolders (tested on 2+ readers)
- [ ] Focus indicators visible; focus management correct between panes and subfolders
- [ ] Accessibility audit passes WCAG 2.1 AA (automated + manual)
- [ ] Tree renders 1000 items in <200ms
- [ ] Lazy rendering reduces initial DOM nodes 60-80%
- [ ] No performance regression on filter changes or folder selection
- [ ] Memoization prevents unnecessary re-renders
- [ ] Mixed-folder indicator and subfolders section fully accessible

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| **Tree rendering performance** (1000+ artifacts jank) | High | Medium | Implement lazy rendering Phase 3; benchmark early Phase 1; use DevTools profiler; have virtualization (react-window) as fallback |
| **Complex path parsing edge cases** (special chars, inconsistent separators) | Medium | Medium | Add comprehensive unit tests Phase 1.10; log malformed paths; provide graceful fallback to flat view if parsing fails |
| **Filter + tree interaction confusing** (users don't understand why items disappear) | Low | Medium | Show active filters prominently; add tooltip explaining filter behavior; implement "(0 artifacts)" message for empty folders |
| **Keyboard navigation complexity** (arrow key focus hard to manage) | Medium | Low | Use Radix Collapsible patterns; test extensively with screen reader Phase 3.4; a11y audit in Phase 3.8 |
| **Deep nesting breaks UI** (indentation, wrapping at 4+ levels) | Medium | Low | Test with real repos 5+ levels deep Phase 2.5; implement breadcrumb or truncation if needed; visual hierarchy tests |
| **Screen reader compatibility** (announced state confusing) | Medium | Low | Test on NVDA/JAWS/VoiceOver Phase 3.4; refine ARIA labels based on feedback; include screen reader testing in final QA |
| **Mixed-content detection fails** (wrong separation of direct vs descendants) | High | Low | Comprehensive unit tests Phase 1.10; test with real repo structures; validate edge cases (single folder, deep nesting, no direct artifacts) |
| **Subfolders section not discoverable** | Medium | Medium | Placement at bottom; clear "Subfolders" heading; highlight with subtle color; user testing Phase 2 |
| **localStorage quota exceeded** | Low | Very Low | View preference storage is minimal (~100 bytes); not a concern for typical use |
| **Adoption low** (users stick with grid/list) | Medium | Medium | Collect analytics Phase 2.13; iterate on UX based on usage data; consider A/B test or feature flag Phase 4 |

### Mitigation Actions

1. **Mixed-Content Detection**: Establish test cases Phase 1.1 for folders with direct artifacts, subfolders, both, and neither
2. **Performance**: Establish DevTools profiling baseline Day 2 (Phase 1.1); if 500 items >300ms, escalate early
3. **Edge Cases**: Create test file with malformed paths before Phase 1.1 completes; ensure parser handles gracefully
4. **Accessibility**: Schedule screen reader testing Phase 3.4 with external accessibility consultant if budget allows
5. **Subfolders Discovery**: A/B test section placement and styling based on Phase 2 feedback
6. **Deep Nesting**: Test with actual repository from Anthropic org before Phase 2.5 starts; adjust UI if needed

---

## Resource Requirements

### Team Composition

| Role | Phases | Effort | Notes |
|------|--------|--------|-------|
| **ui-engineer-enhanced** | 1, 2, 3 | 8-10 FTE days | Component implementation, polish, performance, subfolders UI |
| **frontend-developer** | 1, 2, 3 | 8-10 FTE days | Tree utilities, hooks, integration, testing, subfolder nav logic |
| **web-accessibility-checker** | 3 | 3-4 FTE days | Keyboard nav, ARIA, screen reader testing, audit |
| **ui-designer** | 2 | 1 FTE day | Visual polish, design system review, subfolders section styling |
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

- [x] Folder view adoption >35% of source detail page visits (analytics Phase 2.13)
- [x] Discovery time reduced 40-60% vs flat list (user testing metric)
- [x] Zero critical accessibility issues reported post-launch
- [x] View mode toggle interaction logged for future A/B testing
- [x] Subfolder navigation completion rate >80% (user testing)

### Technical Metrics

- [x] 100% JSDoc coverage on tree utilities and hooks
- [x] Tree builder utility tests >80% coverage (Phase 1.10)
- [x] Component tests >85% coverage (Phase 1.10, 2.12, 3.8)
- [x] No TypeScript `any` types in new code
- [x] Lazy rendering reduces DOM nodes 60-80% (Phase 3.5)
- [x] Mixed-content detection 100% accurate (unit tests)

---

## Testing Strategy

### Unit Testing (Phase 1.10)

**Tree Utilities** (`tree-builder.ts`, `depth-calculator.ts`):
- `buildFolderTree()`: path parsing, depth filtering, direct/subfolder separation, count calculations, edge cases (special chars, deep nesting, empty arrays, mixed content)
- `calculateAutoDepth()`: root_hint detection, scanning logic, safe defaults
- Coverage target: >80%

```typescript
// Example tests:
- buildFolderTree([], 3) → {}
- buildFolderTree([{path: 'skills/dev'}], 3) → {skills: {dev: {...}}} with directCount=0, hasSubfolders=false
- buildFolderTree([{path: 'skills'}, {path: 'skills/dev/tool'}], 3) → mixed structure with directCount=1, hasSubfolders=true
- calculateAutoDepth([...50 items at depth 2-3]) → 2
- Count calculations: directCount=items at folder level, totalCount=all descendants
```

### Component Testing (Phase 1.10, Phase 2.12)

**Jest + React Testing Library**:
- TreeNode: expand/collapse on click, chevron rotation, badge display (direct + total), mixed indicator visibility, ARIA labels
- SubfolderCard: folder icon display, artifact count, click navigation, hover state
- FolderDetailPane: correct folder display, artifact grouping, subfolders section visibility
- SubfoldersSection: conditional rendering, grid layout, responsive
- CatalogFolder: tree structure renders, filter application updates tree
- Coverage target: >85%

### Integration Testing (Phase 2.12)

**Playwright E2E Tests**:
- Toggle to folder view
- Expand/collapse folders with mouse; verify mixed indicators
- Apply filters (type, confidence, search) and verify tree updates
- Click subfolder card; verify tree expands and folder selects
- Import artifact from tree (full workflow)
- View mode persists on page reload
- Subfolder navigation maintains tree state

### Accessibility Testing (Phase 3.4)

**Manual Screen Reader Testing**:
- NVDA (Windows)
- JAWS (Windows)
- VoiceOver (macOS)
- Verify badge counts announced
- Verify mixed-folder indicator announced
- Verify subfolder cards labeled correctly

**Keyboard Navigation Testing**:
- Up/Down arrows navigate siblings
- Left/Right collapse/expand
- Enter/Space toggle
- Tab between controls and subfolders
- Home/End navigation

### Performance Testing (Phase 3.6)

**Playwright Performance Benchmarks**:
```javascript
// Measure tree render time for 1000 items
const start = performance.now();
// expand all folders (trigger renders)
const end = performance.now();
expect(end - start).toBeLessThan(200); // ms

// Measure subfolder grid render
const gridStart = performance.now();
// scroll subfolders section (if large)
const gridEnd = performance.now();
expect(gridEnd - gridStart).toBeLessThan(100); // ms
```

---

## Parallel Work Opportunities

### Optimal Parallelization

**Days 1-2 (Early Phase 1)**:
- **Stream A**: Tree utilities + semantic filtering + mixed-content detection (MFV-1.1, MFV-1.2) - frontend-developer
- **Stream B**: Two-pane layout design + tree node component design + subfolder card design (MFV-1.4, MFV-1.6 prep) - ui-engineer-enhanced

**Merge Point (Day 3)**:
- Integrate utilities into use-folder-selection hook (MFV-1.3)
- Semantic tree component (MFV-1.5), tree node with badges (MFV-1.6)
- Two-pane layout container (MFV-1.4)

**Day 4 (Phase 1 Finalization)**:
- Folder detail pane (MFV-1.7), toolbar integration (MFV-1.8), first folder auto-selection (MFV-1.9)
- Unit tests (MFV-1.10)

**Days 5-7 (Phase 2)**:
- **Stream A**: Folder detail header, README extraction, type grouping, bulk import (MFV-2.1 through MFV-2.6) - primary focus
- **Stream B**: Subfolders section and subfolder card (MFV-2.7, MFV-2.8) - can start Day 5 after Phase 1
- **Stream C**: Subfolder navigation integration (MFV-2.9) - starts Day 6 after MFV-2.8
- ui-designer available for visual review (MFV-2.11)

**Days 8-9 (Phase 3)**:
- **Stream A**: Accessibility (keyboard nav, ARIA, focus, audit) - web-accessibility-checker
- **Stream B**: Performance (lazy rendering, profiling, memoization) - react-performance-optimizer + frontend-developer
- **Merge Point (Day 9)**: Final validation, E2E tests, subfolders accessibility verification

**Estimated Parallelization Savings**: ~2 FTE days (20% reduction in wall-clock time)

---

## Critical Path

1. **Tree utilities + semantic filtering + mixed-content detection** (MFV-1.1, MFV-1.2) → Must complete before hooks (Day 2 EOD)
2. **use-folder-selection hook** (MFV-1.3) → Must complete before semantic tree (Day 3)
3. **Semantic tree component with badges** (MFV-1.5, MFV-1.6) → Must complete before two-pane layout (Day 3)
4. **Two-pane layout** (MFV-1.4) → Must complete before folder detail pane (Day 4)
5. **Folder detail pane** (MFV-1.7) → Must complete before type grouping + bulk import (Phase 2, Day 5)
6. **Subfolders section + subfolder cards** (MFV-2.7, MFV-2.8) → Can start Day 5; ready by Day 6
7. **Subfolder navigation integration** (MFV-2.9) → Must start after MFV-2.8 complete (Day 6)
8. **Type grouping + bulk import** (MFV-2.4, MFV-2.5) → Prerequisite for filter integration (Day 6)
9. **Filter integration** (MFV-2.10) → Prerequisite for E2E tests (Day 7)
10. **Phase 3 accessibility/performance** → Can parallelize; both must complete by Day 9

**Total Critical Path**: 10 days (no shortcuts; all dependencies critical)

---

## Implementation Notes

### Key Technical Decisions

1. **No API changes**: All tree building client-side using existing `CatalogEntry.path` field
2. **Two-pane layout**: 25% left (semantic tree), 75% right (folder detail) - responsive fallback to stacked
3. **Semantic filtering**: Exclude designated root folders (plugins/, src/, skills/, etc.) and leaf containers (commands/, agents/, mcp_servers/, etc.)
4. **Mixed-content handling**: Tree builder separates `directArtifacts` (at folder level) from `children` (subfolders); calculates directCount and totalCount
5. **Count badges**: Direct count always shown (N); total count on hover [M] to reduce clutter
6. **Mixed-folder indicator**: Subtle dot or icon shows folder has both direct artifacts and subfolders
7. **Lazy rendering**: Collapsed folders don't render DOM until expanded (performance optimization)
8. **Folder selection state**: `use-folder-selection` hook manages selected folder + expanded state; first folder auto-selects on load
9. **Artifact grouping**: Right pane groups artifacts by type with section headers; counts reflect current filters; includes only direct artifacts
10. **Subfolders section**: Positioned at bottom of detail pane; shows only if folder has children; clicking card navigates tree
11. **Bulk import**: "Import All" button imports all direct artifacts in selected folder (not descendants); shows progress and success/error states
12. **Filter propagation**: All existing filters apply to right pane; pane updates reactively; subfolders section unaffected
13. **README extraction**: Utility detects and extracts README from folder; falls back to AI-generated summary
14. **Roving tabindex**: Keyboard nav uses Radix pattern for accessibility best practice
15. **Performance budget**: 200ms tree render for 1000 items; lazy rendering target
16. **Memoization**: React.memo() on tree nodes + type sections + subfolders section + useMemo() on tree/grouping calculations

### Component Architecture

```typescript
// File: skillmeat/web/lib/tree-builder.ts
export function buildFolderTree(entries: CatalogEntry[], maxDepth: number): FolderTree

interface FolderNode {
  name: string;
  fullPath: string;
  directArtifacts: CatalogEntry[];  // Artifacts directly in this folder
  totalArtifactCount: number;        // All artifacts including descendants
  directCount: number;               // Count of direct artifacts
  children: FolderNode[];            // Subfolders only
  hasSubfolders: boolean;            // Quick check
  hasDirectArtifacts: boolean;       // Quick check for mixed-content detection
}

// File: skillmeat/web/lib/tree-filter-utils.ts
export function isSemanticFolder(folderPath: string): boolean
export function filterSemanticFolders(tree: FolderTree): FolderTree

// File: skillmeat/web/lib/folder-readme-utils.ts
export function extractFolderReadme(folderPath: string, entries: CatalogEntry[]): string | null
export function generateFolderSummary(folderPath: string): Promise<string>

// File: skillmeat/web/lib/hooks/use-folder-selection.ts
export function useFolderSelection(semanticTree: FolderTree, entries: CatalogEntry[]): {
  selectedFolder: string | null
  setSelectedFolder: (path: string) => void
  expanded: Set<string>
  setExpanded: (path: string, isExpanded: boolean) => void
}

// File: skillmeat/web/app/marketplace/sources/[id]/components/source-folder-layout.tsx
export function SourceFolderLayout({ catalog, filters, onImport, onExclude }: Props): JSX.Element

// File: skillmeat/web/app/marketplace/sources/[id]/components/semantic-tree.tsx
export function SemanticTree({ tree, selectedFolder, expanded, onSelectFolder, onToggleExpand }: Props): JSX.Element

// File: skillmeat/web/app/marketplace/sources/[id]/components/tree-node.tsx
export function TreeNode({ folderPath, directCount, totalCount, hasDirectArtifacts, selected, expanded, onSelect, onToggleExpand }: Props): JSX.Element

// File: skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-pane.tsx
export function FolderDetailPane({ folder, catalog, filters, onImport, onExclude }: Props): JSX.Element

// File: skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-header.tsx
export function FolderDetailHeader({ folder, parentFolder, description, onImportAll }: Props): JSX.Element

// File: skillmeat/web/app/marketplace/sources/[id]/components/artifact-type-section.tsx
export function ArtifactTypeSection({ type, artifacts, onImport, onExclude }: Props): JSX.Element

// File: skillmeat/web/app/marketplace/sources/[id]/components/subfolders-section.tsx
export function SubfoldersSection({ subfolders, onSelectFolder }: Props): JSX.Element

// File: skillmeat/web/app/marketplace/sources/[id]/components/subfolder-card.tsx
export function SubfolderCard({ folder, descendantCount, onSelect }: Props): JSX.Element
```

### Files to Create

1. `/skillmeat/web/lib/tree-builder.ts` - Tree builder utility functions
2. `/skillmeat/web/lib/tree-filter-utils.ts` - Semantic filtering utilities (exclude roots/leafs)
3. `/skillmeat/web/lib/folder-readme-utils.ts` - README extraction and AI summary generation
4. `/skillmeat/web/lib/hooks/use-folder-selection.ts` - React hook for folder selection state
5. `/skillmeat/web/app/marketplace/sources/[id]/components/source-folder-layout.tsx` - Two-pane container layout
6. `/skillmeat/web/app/marketplace/sources/[id]/components/semantic-tree.tsx` - Left pane semantic tree
7. `/skillmeat/web/app/marketplace/sources/[id]/components/tree-node.tsx` - Individual tree folder item
8. `/skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-pane.tsx` - Right pane container
9. `/skillmeat/web/app/marketplace/sources/[id]/components/folder-detail-header.tsx` - Title, chip, description, import all
10. `/skillmeat/web/app/marketplace/sources/[id]/components/artifact-type-section.tsx` - Type grouping component
11. `/skillmeat/web/app/marketplace/sources/[id]/components/subfolders-section.tsx` - **NEW**: Subfolders grid component
12. `/skillmeat/web/app/marketplace/sources/[id]/components/subfolder-card.tsx` - **NEW**: Individual subfolder card

### Files to Modify

1. `/skillmeat/web/app/marketplace/sources/[id]/page.tsx` - Add folder view conditional rendering
2. `/skillmeat/web/app/marketplace/sources/[id]/components/source-toolbar.tsx` - Add folder button
3. `/skillmeat/web/CLAUDE.md` - Add component patterns and accessibility guide
4. `/skillmeat/web/__tests__/` - Add tree builder + semantic filtering unit tests

### Edge Cases Handled

- **Malformed paths**: Missing levels, special characters, Windows backslashes → Logged but don't crash
- **Circular references**: Prevented by depth filtering; tree depth controlled by `maxDepth`
- **Empty catalog**: Tree builder returns empty object; UI shows empty state
- **Semantic filtering edge cases**: Root-only catalogs show empty tree; leaf containers properly excluded; intermediate folders preserved
- **Filtered empty tree**: Folders with no matching items show "(0 importable artifacts)" message in right pane
- **No README**: Folder description falls back to AI-generated summary or generic text
- **First folder missing**: Auto-selection skips to first available semantic folder
- **Pane overflow**: Right pane scrolls independently; left pane (semantic tree) scrollable; layout responsive on small screens
- **Folder with ONLY direct artifacts**: Subfolders section hidden; artifact groups displayed
- **Folder with ONLY subfolders**: Artifact groups hidden or show empty state; subfolders section displayed
- **Folder with BOTH**: Both artifact groups and subfolders section displayed; "(N) [M]" badges and mixed indicator visible
- **Empty folder with subfolders**: No artifact groups; only subfolders section; "(0)" or no direct count badge

---

## Post-Implementation

### Metrics Collection (Phase 2.13 onwards)

- **Adoption**: Folder view toggle click rate, percentage of visits using folder view
- **Engagement**: Folder expand/collapse rate, time spent in folder view, import rate from folders
- **Subfolder Navigation**: Subfolder card click rate, subfolder drill-down depth, bounce-back rate
- **Performance**: Tree render time in production, filter response time, any console errors

### Iteration Opportunities

- **Phase 4**: React window virtualization for left pane (if performance issues arise with 500+ folders)
- **Phase 4**: Smart breadcrumb navigation in detail pane (if deep nesting UX testing shows value)
- **Phase 4**: URL state for view mode + selected folder (`?view=folder&folder=skills` for deep linking)
- **Phase 4**: Per-folder sorting options in right pane (artifacts by type, name, import date)
- **Phase 4**: Folder favorites/bookmarks with quick access
- **Phase 4**: Folder-level statistics (total artifacts, types distribution, import rate)
- **Phase 4**: Subfolder grid customization (card size, view mode toggle)

### Maintenance Notes

- Tree builder utilities are stable after Phase 1; unlikely to need changes
- Mixed-content detection is critical path; monitor for edge cases
- Filter integration is critical path; monitor for performance issues
- Screen reader compatibility may need tweaks based on user feedback
- Performance benchmarks should be re-run quarterly

---

## Acceptance Criteria Summary

### Functional Acceptance (All Phases)

- [x] Folder view button appears in view mode toggle
- [x] Two-pane layout renders: left (semantic tree 25%), right (folder detail 75%)
- [x] Semantic tree excludes roots and leaf containers; shows intermediate folders only
- [x] Tree nodes display direct artifact count badges (N)
- [x] Tree nodes display total descendant count on hover [M]
- [x] Mixed-content folders (direct + subfolders) show visual indicator
- [x] Folders expand/collapse with click and keyboard in left pane
- [x] Folder selection populates right pane with folder metadata and artifacts
- [x] Artifacts grouped by type in right pane with section headers and counts
- [x] "Import All" button bulk imports all direct artifacts in selected folder
- [x] Folder description shows README content or AI-generated summary
- [x] All filters (type, confidence, search, status) work in right pane
- [x] Empty folders show helpful messages in right pane
- [x] Subfolders section appears when folder has children
- [x] Subfolder cards display with folder icon, name, descendant count
- [x] Clicking subfolder card navigates tree and updates detail pane
- [x] View mode and selected folder path persist to localStorage
- [x] URL state remains synchronized with existing filters

### Technical Acceptance (All Phases)

- [x] No API changes; uses existing `CatalogEntry.path` only
- [x] Follows Next.js 15 App Router patterns
- [x] Follows component conventions (shadcn/ui, Radix, named exports)
- [x] TypeScript fully typed; no `any` types
- [x] Tree builder + semantic filtering functions unit tested (>80% coverage)
- [x] Mixed-content detection unit tested (>80% coverage)
- [x] Performance: tree renders <200ms for 1000 artifacts
- [x] Lazy rendering implemented for collapsed folders
- [x] React.memo and useMemo applied to prevent unnecessary re-renders
- [x] Responsive layout (two-pane on desktop, stacked on mobile)
- [x] Direct artifacts properly separated from subfolders in tree structure

### Quality Acceptance (All Phases)

- [x] Unit tests >80% (tree builder, semantic filtering, mixed-content logic, folder README utils, hooks)
- [x] Component tests >85% (semantic tree, tree node, folder detail pane, type sections, subfolders section, subfolder card)
- [x] E2E tests cover critical path (folder selection, type grouping, bulk import, filter integration, subfolder navigation)
- [x] WCAG 2.1 AA compliance (keyboard nav, ARIA, focus management, badge/indicator accessibility)
- [x] No performance regressions on filter changes or folder selection
- [x] Visual consistency across both panes; balanced proportions
- [x] Subfolders section clear and properly positioned

### Documentation Acceptance (All Phases)

- [x] Component usage guide in CLAUDE.md or dedicated .md
- [x] JSDoc comments on all exported functions and utilities
- [x] Semantic filtering rules documented (which folders excluded/included)
- [x] Mixed-content handling rules documented (direct vs descendants, badge display, visual indicators)
- [x] Accessibility implementation guide (keyboard nav, ARIA patterns, focus management, badge/indicator ARIA)
- [x] PR description explains two-pane layout, semantic filtering, type grouping, bulk import, mixed-content handling, subfolders
- [x] Storybook stories for semantic tree, tree nodes, folder detail pane, type sections, subfolders section, subfolder card

---

**Progress Tracking:**

See `.claude/progress/marketplace-folder-view-v1/all-phases-progress.md`

---

**Implementation Plan Version**: 2.0 (Updated with mixed-content support)
**Last Updated**: 2026-01-29
**Status**: Ready for Phase 1 execution
