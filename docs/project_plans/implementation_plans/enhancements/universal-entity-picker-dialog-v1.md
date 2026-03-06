---
title: "Implementation Plan: Universal Entity Picker Dialog"
schema_version: "1.0"
doc_type: implementation_plan
status: draft
created: "2026-03-06"
updated: "2026-03-06"
feature_slug: universal-entity-picker-dialog
feature_version: "v1"
prd_ref: docs/project_plans/PRDs/enhancements/universal-entity-picker-dialog-v1.md
plan_ref: null
scope: "Frontend-only enhancement extracting rich dialog picker patterns for workflow UI"
effort_estimate: "14 points"
architecture_summary: "Extract generic EntityPickerDialog from AddMemberDialog patterns; integrate into Stage Editor and Builder Sidebar replacing compact pickers with rich browsable dialogs"
related_documents:
  - docs/project_plans/PRDs/enhancements/universal-entity-picker-dialog-v1.md
  - .claude/context/key-context/component-patterns.md
  - .claude/context/key-context/testing-patterns.md
owner: null
contributors: []
priority: medium
risk_level: low
category: product-planning
tags: [implementation, planning, frontend, components, picker, dialog]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - skillmeat/web/components/shared/entity-picker-dialog.tsx
  - skillmeat/web/components/context/mini-context-entity-card.tsx
  - skillmeat/web/components/workflow/stage-editor.tsx
  - skillmeat/web/components/workflow/builder-sidebar.tsx
---

# Implementation Plan: Universal Entity Picker Dialog

**Plan ID**: `IMPL-2026-03-06-UNIVERSAL-ENTITY-PICKER`
**Date**: 2026-03-06
**Author**: Implementation Planner (Orchestrator)
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/enhancements/universal-entity-picker-dialog-v1.md`
- **Source Component**: `skillmeat/web/components/deployment-sets/add-member-dialog.tsx`
- **Replacement Components**: `skillmeat/web/components/shared/artifact-picker.tsx`, `skillmeat/web/components/shared/context-module-picker.tsx`

**Complexity**: Small
**Total Estimated Effort**: 14 story points
**Target Timeline**: 5-6 days (1 week sprint)

## Executive Summary

This implementation plan extracts the rich dialog-based entity browsing UX from the existing `AddMemberDialog` component into a reusable, generic `EntityPickerDialog` component with configurable tabs, infinite scroll, type filtering, and rich mini-cards. The new component is then integrated into three workflow UI locations to replace the current compact popover pickers (`ArtifactPicker` and `ContextModulePicker`), enabling users to browse and select all available entities without pagination limits.

**Key milestones**:
1. Extract and validate `EntityPickerDialog` with full test coverage
2. Create `MiniContextEntityCard` component for context entity display
3. Integrate into Stage Editor (Primary Agent and Supporting Tools pickers)
4. Integrate into Builder Sidebar (Global Modules picker)
5. Full test suite pass, accessibility validation, and zero regressions

**Success criteria**: All three workflow picker fields open rich browsable dialogs; users can scroll to see all entities; form state roundtrip works correctly; no visual or functional regressions.

## Implementation Strategy

### Architecture Sequence

This is a **frontend-only** component refactoring following these principles:

1. **Component Extraction** - Extract generic dialog from `AddMemberDialog` patterns (tabs, search, filtering, infinite scroll, selection state)
2. **Mini Card Creation** - Create `MiniContextEntityCard` as compact variant of `context-entity-card.tsx`
3. **Integration Layer** - Replace picker invocations in workflow components with `EntityPickerDialog`
4. **Testing & Validation** - Unit tests, integration tests, accessibility audit, form state verification
5. **Polish & Documentation** - Visual alignment, JSDoc, type safety, accessibility checks

### Parallel Work Opportunities

- **Phase 1 + Phase 2 can run in parallel**: Both are independent component creation tasks
- **Phase 3 + Phase 4 can run in parallel**: Both are integration tasks that depend only on Phase 1 + Phase 2
- **Phase 5 (validation) depends on all phases**: Cannot start until Phases 1-4 are complete

### Critical Path

1. Phase 1: EntityPickerDialog extraction (5 points) — gates Phases 3 & 4
2. Phase 2: MiniContextEntityCard (2 points) — gates Phase 4
3. Phases 3 & 4: Integrations (5 points total) — run in parallel after Phase 1 complete
4. Phase 5: Testing & polish (2 points) — final validation

**Timeline**: 5-6 days assuming single dedicated developer; 3-4 days with parallel execution (batch 1: Phases 1+2, batch 2: Phases 3+4, batch 3: Phase 5).

## Phase Breakdown

### Phase 1: Extract EntityPickerDialog Component

**Duration**: 2 days
**Dependencies**: None
**Assigned Subagent(s)**: ui-engineer-enhanced

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| UEPD-1.1 | EntityPickerDialog component | Create generic dialog with tabs, search, infinite scroll, type filters, selection state | Component renders multiple tabs; search filters results; infinite scroll loads next page; single/multi-select modes work | 3 pts | ui-engineer-enhanced | None |
| UEPD-1.2 | EntityPickerTrigger component | Create trigger element showing selection summary and opening dialog | Trigger shows single-select name or multi-select count; opens dialog on click; shows removable badges in multi mode | 1.5 pts | ui-engineer-enhanced | UEPD-1.1 |
| UEPD-1.3 | useEntityPickerArtifacts adapter hook | Wrap useInfiniteArtifacts to match EntityPickerTab.useData interface | Hook returns { items, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage } matching tab contract | 0.5 pts | ui-engineer-enhanced | None |

**Phase 1 Quality Gates:**
- [ ] `pnpm type-check` passes with zero errors
- [ ] `EntityPickerDialog` accepts props: `open`, `onOpenChange`, `tabs`, `mode`, `value`, `onChange`, `title?`, `description?`
- [ ] Component renders all tabs correctly; switching tabs works
- [ ] Search input filters results with 300ms debounce
- [ ] Type filter pills appear when configured; clicking toggles filter
- [ ] Infinite scroll sentinel triggers `fetchNextPage` when in view
- [ ] Single-select closes dialog on card click
- [ ] Multi-select toggles selection state; "Done" button emits array
- [ ] Empty state message shown when no results
- [ ] Loading skeletons shown during fetch
- [ ] Unit tests cover: render, tab switch, search, filter toggle, single-select, multi-select, keyboard Escape
- [ ] JSDoc blocks on component and all interfaces

**Key Integration Points**:
- Reuse `useIntersectionObserver` hook from `AddMemberDialog` for infinite scroll sentinel
- Reuse search + debounce pattern from `AddMemberDialog`
- Reuse type filter pills UI pattern from `AddMemberDialog`
- Extract tab structure from `AddMemberDialog` deployment-set mutation logic (mutation cleanup)
- Reuse Radix Dialog + Command for UI primitives (already in use)

**Files Created/Modified**:
- Create: `skillmeat/web/components/shared/entity-picker-dialog.tsx` (~450 lines including JSDoc)
- Create: `skillmeat/web/components/shared/entity-picker-adapter-hooks.ts` (~50 lines for useEntityPickerArtifacts, useEntityPickerContextModules)
- No modifications to existing files in Phase 1

---

### Phase 2: Context Entity Mini Card

**Duration**: 1 day
**Dependencies**: None (can run parallel to Phase 1)
**Assigned Subagent(s)**: ui-engineer-enhanced

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| UEPD-2.1 | MiniContextEntityCard component | Create compact context entity card showing name, type badge, description | Renders name + description (2-line truncate) + type chip; type color from context-entity-config; matches mini-artifact-card visual scale | 1.5 pts | ui-engineer-enhanced | None |
| UEPD-2.2 | useEntityPickerContextModules adapter hook | Wrap useContextModules to match EntityPickerTab.useData interface | Hook returns { items, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage }; works with search + limit params | 0.5 pts | ui-engineer-enhanced | None |

**Phase 2 Quality Gates:**
- [ ] `pnpm type-check` passes
- [ ] MiniContextEntityCard renders name, type badge (with color from context-entity-config), and truncated description
- [ ] Card accepts `onClick`, `disabled`, `selected` props
- [ ] Selected state shows checkmark overlay (visual consistency with MiniArtifactCard)
- [ ] Responsive: matches layout/scale of MiniArtifactCard
- [ ] Unit test verifies render with all props
- [ ] JSDoc on component

**Key Integration Points**:
- Derive visual pattern from `MiniArtifactCard` at `skillmeat/web/components/collection/mini-artifact-card.tsx`
- Use color mapping from `skillmeat/web/lib/context-entity-config.ts` for type badges
- Support same selection/disabled states as MiniArtifactCard

**Files Created**:
- Create: `skillmeat/web/components/context/mini-context-entity-card.tsx` (~150 lines)
- Reuse: `skillmeat/web/lib/context-entity-config.ts` (existing; no changes needed)

---

### Phase 3: Integrate into Workflow Stage Editor

**Duration**: 1.5 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: ui-engineer-enhanced

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| UEPD-3.1 | Replace Primary Agent picker | Replace ArtifactPicker (lines ~413-421) with EntityPickerDialog single-select Artifacts tab filtered to agent type | Dialog opens on trigger click; selecting agent closes dialog and updates primaryAgentUuid; form state preserved | 1.5 pts | ui-engineer-enhanced | UEPD-1.1, UEPD-1.2, UEPD-1.3 |
| UEPD-3.2 | Replace Supporting Tools picker | Replace ArtifactPicker (lines ~424-432) with EntityPickerDialog multi-select Artifacts tab filtered to skill/command/mcp types | Dialog opens on trigger click; selecting/deselecting tools updates toolUuids array; form state preserved | 1.5 pts | ui-engineer-enhanced | UEPD-1.1, UEPD-1.2, UEPD-1.3 |

**Phase 3 Quality Gates:**
- [ ] `pnpm type-check` passes on stage-editor.tsx
- [ ] Primary Agent picker opens EntityPickerDialog when trigger clicked
- [ ] Only agent-type artifacts shown in Artifacts tab
- [ ] Single-select: clicking agent closes dialog and updates form field
- [ ] Supporting Tools picker opens EntityPickerDialog when trigger clicked
- [ ] Only skill/command/mcp artifacts shown in Artifacts tab
- [ ] Multi-select: clicking/deselecting tools toggles selection; "Done" updates form field
- [ ] Both pickers: form value shape unchanged (primaryAgentUuid: string, toolUuids: string[])
- [ ] Both pickers: existing form save/load behavior works (form state roundtrip verified)
- [ ] Unit tests updated: old ArtifactPicker mocks replaced with EntityPickerDialog mocks
- [ ] Manual QA: stage editor form opens and closes correctly; selections persist

**Key Integration Points**:
- `stage-editor.tsx` lines ~413-421: Primary Agent field
- `stage-editor.tsx` lines ~424-432: Supporting Tools field
- Preserve `value` and `onChange` prop contracts with parent form
- Reuse `useEntityPickerArtifacts` hook from Phase 1
- Type filter: `typeFilter=['agent']` for Primary Agent, `typeFilter=['skill','command','mcp']` for Tools

**Files Modified**:
- Modify: `skillmeat/web/components/workflow/stage-editor.tsx` (replace 2 picker invocations, add EntityPickerDialog imports)
- Modify: `skillmeat/web/__tests__/components/workflow/stage-editor.test.tsx` (update mocks)

---

### Phase 4: Integrate into Workflow Builder Sidebar

**Duration**: 1 day
**Dependencies**: Phase 1 + Phase 2 complete
**Assigned Subagent(s)**: ui-engineer-enhanced

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| UEPD-4.1 | Replace Global Modules picker | Replace ContextModulePicker (lines ~426-443) with EntityPickerDialog multi-select Context Entities tab showing context modules as MiniContextEntityCard | Dialog opens on trigger click; selecting/deselecting modules updates contextPolicy.modules array; inherited modules handled correctly | 2 pts | ui-engineer-enhanced | UEPD-1.1, UEPD-1.2, UEPD-2.1, UEPD-2.2 |

**Phase 4 Quality Gates:**
- [ ] `pnpm type-check` passes on builder-sidebar.tsx
- [ ] Global Modules picker opens EntityPickerDialog when trigger clicked
- [ ] Context Entities tab shows all context modules as MiniContextEntityCard
- [ ] Multi-select: clicking/deselecting modules toggles selection; "Done" updates form field
- [ ] Form value shape unchanged (contextPolicy.modules: string[])
- [ ] Inherited modules handled correctly (read-only state if applicable; inspect useContextModules to confirm)
- [ ] Existing form save/load behavior works (form state roundtrip verified)
- [ ] Unit tests updated: old ContextModulePicker mocks replaced with EntityPickerDialog mocks
- [ ] Manual QA: builder sidebar form opens and closes correctly; selections persist

**Key Integration Points**:
- `builder-sidebar.tsx` lines ~426-443: Global Modules field
- Preserve `value` and `onChange` prop contracts with parent form
- Reuse `useEntityPickerContextModules` hook from Phase 2
- Display context modules as `MiniContextEntityCard` items

**Files Modified**:
- Modify: `skillmeat/web/components/workflow/builder-sidebar.tsx` (replace 1 picker invocation, add EntityPickerDialog imports)
- Modify: `skillmeat/web/__tests__/components/workflow/builder-sidebar.test.tsx` (update mocks)

---

### Phase 5: Testing & Polish

**Duration**: 1 day
**Dependencies**: Phases 1-4 complete
**Assigned Subagent(s)**: ui-engineer-enhanced, task-completion-validator

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| UEPD-5.1 | Keyboard navigation & accessibility | Implement full keyboard support and ARIA labels | Tab through pills/cards, arrow keys in list, Enter/Space to select, Escape to close; screen reader announces selections; focus trap on open; focus returns to trigger on close | 1 pt | ui-engineer-enhanced | UEPD-1.1 |
| UEPD-5.2 | Visual polish & responsive | Match AddMemberDialog visual scale; responsive grid; empty/loading states; selection feedback | Responsive grid (2 cols md, 3 cols lg); loading skeletons; empty state messaging; checkmark overlay on selected cards; smooth animations | 0.5 pts | ui-engineer-enhanced | UEPD-1.1, UEPD-2.1 |
| UEPD-5.3 | Integration validation | Full end-to-end test of all three integration points | pnpm type-check passes; pnpm lint passes; all unit tests pass (>80% coverage); form state roundtrip works; no regressions in workflow create/edit; keyboard nav verified; a11y audit clean | 0.5 pts | task-completion-validator | UEPD-3.1, UEPD-3.2, UEPD-4.1 |

**Phase 5 Quality Gates:**
- [ ] Full keyboard navigation: Tab key moves focus through tabs/pills/cards; Up/Down arrows navigate list; Enter/Space selects; Escape closes
- [ ] ARIA labels: dialog has role="dialog" aria-modal="true"; pills have role="group"; list items have aria-selected
- [ ] Focus trap: dialog traps focus on open; focus returns to trigger on close
- [ ] Screen reader: selection changes announced (aria-live regions or aria-selected updates)
- [ ] Color + icon: selection state uses both color AND checkmark icon (not color alone)
- [ ] Loading: skeletons shown during initial fetch
- [ ] Empty state: "No results" message when search + filter yield zero items
- [ ] Responsive: grid reflows correctly on mobile/tablet/desktop
- [ ] Visual parity: trigger button size/style matches surrounding form fields
- [ ] `pnpm type-check` passes with zero errors on all modified files
- [ ] `pnpm lint` passes with no new warnings
- [ ] All unit tests pass: `pnpm test -- --testPathPattern="entity-picker|stage-editor|builder-sidebar"`
- [ ] Manual QA: all three workflow picker fields work end-to-end in `skillmeat web dev`
- [ ] Accessibility audit: keyboard-only navigation through each dialog verified manually
- [ ] Form state roundtrip: select → save → reload → correct selection shown

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|:------:|:----------:|-------------------|
| `context-entity-card.tsx` is complex; mini variant requires significant design work | Medium | Low | Phase 2 task includes inspection of source component; if overly complex, scope to name + type chip only for v1 |
| Tab lazy-load flashes empty content on first activate | Low | Medium | Show skeleton immediately on tab activate before first fetch resolves |
| Existing stage-editor/builder-sidebar unit tests break due to ArtifactPicker/ContextModulePicker import mocks | Low | Medium | Task UEPD-3.2 and UEPD-4.1 explicitly include test mock updates |
| EntityPickerDialog trigger button different size than current pickers; visual regression | Low | Low | Match trigger button height and label style to existing `Field` + label pattern in stage-editor.tsx |
| Inherited context modules UX unclear from ContextModulePicker source | Low | Low | Inspect `useContextModules` hook return shape before Phase 4 implementation; defer inherited display to v2 if needed |

---

## Resource Requirements

### Team Composition

**Single dedicated frontend developer** (recommended for efficiency):
- **ui-engineer-enhanced** (Sonnet 4.6): Phases 1-5 (all component + integration work)
- **task-completion-validator** (Sonnet 4.6): Phase 5 (final validation and test pass verification)

**Alternative: Parallel execution** (2 developers):
- Developer A: Phase 1 + Phase 3 (EntityPickerDialog + Stage Editor integration)
- Developer B: Phase 2 + Phase 4 (MiniContextEntityCard + Builder Sidebar integration)
- Both: Phase 5 validation

### Skill Requirements

- React component patterns (`hooks`, component structure, context)
- TypeScript (strict mode, interface composition)
- Radix UI Dialog + Command patterns (already in project)
- React Query / infinite scroll patterns
- Accessibility (ARIA, keyboard navigation, focus management)
- Jest/React Testing Library

### Infrastructure

- Existing: `skillmeat web dev` for local testing
- Existing: `pnpm test`, `pnpm type-check`, `pnpm lint` for validation

---

## Success Metrics

### Delivery Metrics

- [ ] 14 story points completed on time
- [ ] 0 P0/P1 bugs in implementation
- [ ] Code coverage >80% for new components
- [ ] All unit tests passing in CI/CD
- [ ] `pnpm type-check` and `pnpm lint` with zero errors/new warnings

### Feature Metrics

- [ ] All 3 workflow picker integration points functional end-to-end
- [ ] No regressions in workflow create/edit flows
- [ ] Form state roundtrip verified (select → save → reload → correct selection)
- [ ] Infinite scroll tested with 100+ entities in collection
- [ ] Empty state and loading state visible and correct

### Technical Metrics

- [ ] EntityPickerDialog has zero imports from workflow/deployment-set/context domain modules
- [ ] Full keyboard navigation verified (Tab, arrow keys, Enter, Escape)
- [ ] WCAG 2.1 AA accessibility compliance validated
- [ ] JSDoc blocks on all exported types and components

---

## Parallelization Strategy

```
Batch 1: Phases 1 + 2 (can run in parallel; no dependencies)
  ├── UEPD-1.1: EntityPickerDialog component
  ├── UEPD-1.2: EntityPickerTrigger component
  ├── UEPD-1.3: useEntityPickerArtifacts hook
  ├── UEPD-2.1: MiniContextEntityCard component
  └── UEPD-2.2: useEntityPickerContextModules hook

Batch 2: Phases 3 + 4 (can run in parallel; depend on Batch 1)
  ├── UEPD-3.1: Replace Primary Agent picker
  ├── UEPD-3.2: Replace Supporting Tools picker
  └── UEPD-4.1: Replace Global Modules picker

Batch 3: Phase 5 (depends on Batch 2)
  ├── UEPD-5.1: Keyboard navigation & accessibility
  ├── UEPD-5.2: Visual polish & responsive
  └── UEPD-5.3: Integration validation & final test pass
```

**Timeline**:
- Single developer: 5-6 days (sequential phases)
- Parallel execution: 3-4 days (Batch 1: 2d, Batch 2: 1.5d, Batch 3: 1d)

---

## Quality Gates

Each phase must pass before proceeding to next:

### Phase 1 Gate
- `EntityPickerDialog` component renders and accepts all required props
- Tabs render and switch correctly
- Search, filter pills, infinite scroll, and selection state all functional
- Unit test coverage >80%
- `pnpm type-check` passes

### Phase 2 Gate
- `MiniContextEntityCard` renders with correct styling and layout
- Matches visual scale of `MiniArtifactCard`
- Unit tests pass
- `pnpm type-check` passes

### Phase 3 Gate
- Both stage-editor pickers replaced with EntityPickerDialog
- Form state preserved (primaryAgentUuid, toolUuids)
- Stage editor unit tests updated and passing
- Manual QA: both pickers work correctly in dev

### Phase 4 Gate
- Builder sidebar Global Modules picker replaced with EntityPickerDialog
- Form state preserved (contextPolicy.modules)
- Builder sidebar unit tests updated and passing
- Manual QA: Global Modules picker works correctly in dev

### Phase 5 Gate
- `pnpm type-check` passes on all files
- `pnpm lint` passes with no new warnings
- All unit tests passing: `pnpm test -- --testPathPattern="entity-picker|stage-editor|builder-sidebar"`
- Keyboard navigation verified manually (all three dialogs)
- Accessibility audit clean (ARIA labels, focus trap, screen reader)
- Form state roundtrip verified for all three integration points
- No visual regressions in workflow UI

---

## Key Files Reference

**Source Components (read-only reference)**:
- `skillmeat/web/components/deployment-sets/add-member-dialog.tsx` (742 lines; patterns to extract)
- `skillmeat/web/components/collection/mini-artifact-card.tsx` (436 lines; visual pattern reference)
- `skillmeat/web/components/context/context-entity-card.tsx` (429 lines; mini variant source)

**Components Being Replaced** (unchanged in this plan; only call-sites modified):
- `skillmeat/web/components/shared/artifact-picker.tsx` (466 lines; used elsewhere)
- `skillmeat/web/components/shared/context-module-picker.tsx` (530 lines; used elsewhere)

**Integration Points** (modified in Phases 3-4):
- `skillmeat/web/components/workflow/stage-editor.tsx` (lines ~413-432; 2 picker replacements)
- `skillmeat/web/components/workflow/builder-sidebar.tsx` (lines ~426-443; 1 picker replacement)

**Hooks** (reused; no modifications):
- `skillmeat/web/hooks/index.ts` (barrel export; useInfiniteArtifacts, useContextModules, useIntersectionObserver, useDebounce)

**Types** (referenced; no modifications):
- `skillmeat/web/types/workflow.ts` (RoleAssignment, StageRoles, ContextBinding)
- `skillmeat/web/types/index.ts` (Artifact, ContextModuleResponse)
- `skillmeat/web/lib/context-entity-config.ts` (type color mapping)

**New Files Created**:
- `skillmeat/web/components/shared/entity-picker-dialog.tsx` (main component + types + JSDoc)
- `skillmeat/web/components/shared/entity-picker-adapter-hooks.ts` (adapter hooks)
- `skillmeat/web/components/context/mini-context-entity-card.tsx` (mini card component)

---

## Implementation Notes

### Component API Design

```typescript
// EntityPickerTab configuration shape
interface EntityPickerTab<T> {
  id: string;                                           // Unique tab identifier
  label: string;                                         // Visible tab label
  icon: React.ComponentType<{ className?: string }>;    // Lucide icon component
  useData: (params: {                                   // Hook that returns paginated data
    search: string;
    typeFilter?: string[];
  }) => InfiniteDataResult<T>;
  renderCard: (item: T, isSelected: boolean) =>        // Render function for each item
    React.ReactNode;
  getId: (item: T) => string;                          // Extract UUID from item
  typeFilters?: {                                        // Optional type filter pills
    value: string;
    label: string;
    icon?: React.ComponentType;
  }[];
}

// EntityPickerDialog props
interface EntityPickerDialogProps<T = unknown> {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tabs: EntityPickerTab<T>[];
  mode: 'single' | 'multi';
  value: string | string[];
  onChange: (value: string | string[]) => void;
  title?: string;
  description?: string;
}
```

### Adapter Hooks Pattern

Two adapter hooks bridge existing data sources to the EntityPickerTab interface:

```typescript
// Wraps useInfiniteArtifacts
function useEntityPickerArtifacts(params: {
  search: string;
  typeFilter?: string[];
}) {
  // Returns { items, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage }
}

// Wraps useContextModules
function useEntityPickerContextModules(params: {
  search: string;
  typeFilter?: string[];
}) {
  // Returns { items, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage }
}
```

### Selection State Management

- **Single-select**: `value: string` (one UUID); dialog closes on selection
- **Multi-select**: `value: string[]` (UUID array); dialog stays open until explicit confirm

---

## Post-Implementation

### Monitoring & Observability

No new API endpoints, so no telemetry changes needed. Monitor:
- No console errors during dialog interactions
- Form submission succeeds with selected values
- No JavaScript errors in browser console

### Future Enhancements (Out of Scope)

1. **Preview Pane** (v2): Hover/focus on card to see full artifact detail
2. **Refactor AddMemberDialog** (v2): Use EntityPickerDialog as foundation to eliminate duplication
3. **Composite Artifact Type** (v2): Add `composite` to Supporting Tools type filter
4. **Inherited Module Visibility** (v2): If needed, add visual distinction for inherited context modules

---

**Progress Tracking:**

See `.claude/progress/universal-entity-picker-dialog/all-phases-progress.md` (to be created when implementation begins)

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-03-06
