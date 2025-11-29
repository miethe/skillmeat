# Phase 1 Progress: 3-Panel Sync Status Redesign

**Status:** PENDING
**Last Updated:** 2025-11-29
**Completion:** 0% (0 of 5 tasks)
**Total Effort:** ~530 lines of component code
**Priority:** Medium

**Related Documents:**
- PRD: `/docs/project_plans/PRDs/enhancements/artifact-flow-modal-redesign.md`
- Implementation Plan: `/docs/project_plans/implementation_plans/enhancements/artifact-flow-modal-redesign.md`

**Subagent Assignments:**
- **TASK-1.1:** ui-engineer-enhanced
- **TASK-1.2:** ui-engineer-enhanced
- **TASK-1.3:** ui-engineer-enhanced
- **TASK-1.4:** ui-engineer-enhanced
- **TASK-1.5:** ui-engineer-enhanced

**Dependencies Map:**
- **TASK-1.1-1.5:** No dependencies (can run in parallel)
- **TASK-2.1:** Depends on TASK-1.1, 1.2, 1.3, 1.4, 1.5 (orchestration)
- **TASK-3.1:** Depends on TASK-2.1 (integration)
- **TASK-4.1:** Depends on TASK-3.1 (wiring)
- **TASK-4.2:** Depends on TASK-3.1 (tooltips)

---

## Phase Overview

**Phase Title:** 3-Panel Sync Status Redesign

**Duration:** 2-3 days
**Assigned Subagent(s):** ui-engineer-enhanced
**Code Domains:** Web, Test

**Objective:** Refactor the Sync Status tab in the unified entity modal with five new sub-components that together create a comprehensive 3-panel artifact flow visualization with comparison capabilities.

**Component Architecture:**
```
SyncStatusTab (parent)
├── ArtifactFlowBanner (top-left)
│   └── 3-tier visualization with SVG connectors
├── ComparisonSelector (top-right)
│   └── Dropdown with quick-switch buttons
├── DriftAlertBanner (top alert area)
│   └── Status-specific alert variants
├── FilePreviewPane (center-right)
│   └── Markdown + code preview
└── SyncActionsFooter (bottom)
    └── Action buttons + Coming Soon states
```

---

## Phase 1: Parallel Sub-Components

### Sub-Task Breakdown

- **TASK-1.1:** Create ArtifactFlowBanner component
- **TASK-1.2:** Create ComparisonSelector component
- **TASK-1.3:** Create DriftAlertBanner component
- **TASK-1.4:** Create FilePreviewPane component
- **TASK-1.5:** Create SyncActionsFooter component

### Completion Checklist

- [ ] **TASK-1.1: Create ArtifactFlowBanner component** (Medium priority) ⏳
  - **Assigned To:** ui-engineer-enhanced
  - **Dependencies:** None (parallel)
  - **File:** `skillmeat/web/components/sync-status/artifact-flow-banner.tsx`
  - **Size:** ~150 lines
  - **Acceptance Criteria:**
    - [ ] Component created with TypeScript/TSX
    - [ ] 3-tier visualization layout (Local → Cloud → Upstream)
    - [ ] SVG connectors between tiers with status-based colors
    - [ ] Node rendering with icons (document/code/check/warning)
    - [ ] Version labels for each tier
    - [ ] Responsive sizing (100% width, adaptive height)
    - [ ] Button placement logic (Deploy/Sync/Merge buttons positioned correctly)
    - [ ] Hover states with tooltips
    - [ ] Dark mode support via Tailwind
  - **Dependencies:**
    - Radix UI icons or shadcn icons
    - Tailwind CSS
  - **Key Files:**
    - New: `skillmeat/web/components/sync-status/artifact-flow-banner.tsx`
  - **Notes:**
    - SVG should use inline rendering for better performance
    - Node colors: green (synced), yellow (modified), red (conflict), blue (default)
    - Connector lines use Bezier curves for smooth appearance

- [ ] **TASK-1.2: Create ComparisonSelector component** (Medium priority) ⏳
  - **Assigned To:** ui-engineer-enhanced
  - **Dependencies:** None (parallel)
  - **File:** `skillmeat/web/components/sync-status/comparison-selector.tsx`
  - **Size:** ~80 lines
  - **Acceptance Criteria:**
    - [ ] Component created with shadcn Select
    - [ ] Dropdown shows: Local vs Cloud, Cloud vs Upstream, Local vs Upstream
    - [ ] Quick-switch buttons below dropdown (3 buttons)
    - [ ] Button styling: active state (filled), inactive state (outline)
    - [ ] Selected comparison highlighted
    - [ ] onChange callback fires on selection change
    - [ ] Default selection: Local vs Cloud
    - [ ] Accessible keyboard navigation
  - **Dependencies:**
    - shadcn/ui Select
    - Tailwind CSS
  - **Key Files:**
    - New: `skillmeat/web/components/sync-status/comparison-selector.tsx`
  - **Notes:**
    - Comparison options: "Local vs Cloud", "Cloud vs Upstream", "Local vs Upstream"
    - Visual differentiation with icons or badges

- [ ] **TASK-1.3: Create DriftAlertBanner component** (Medium priority) ⏳
  - **Assigned To:** ui-engineer-enhanced
  - **Dependencies:** None (parallel)
  - **File:** `skillmeat/web/components/sync-status/drift-alert-banner.tsx`
  - **Size:** ~100 lines
  - **Acceptance Criteria:**
    - [ ] Component created with shadcn Alert variants
    - [ ] Renders different alerts based on status prop
    - [ ] Status states: synced, modified, outdated, conflict
    - [ ] Alert variants: success (synced), warning (modified/outdated), danger (conflict)
    - [ ] Title + description text for each status
    - [ ] Action button row (Resolve, Sync, Merge buttons)
    - [ ] Icons for each status
    - [ ] Dismissible variant (optional close button)
    - [ ] Smooth transitions between states
  - **Dependencies:**
    - shadcn/ui Alert
    - shadcn/ui Button
    - Radix UI icons
  - **Key Files:**
    - New: `skillmeat/web/components/sync-status/drift-alert-banner.tsx`
  - **Notes:**
    - Alert messages should be human-readable and actionable
    - Button visibility depends on status (some buttons only show for certain statuses)

- [ ] **TASK-1.4: Create FilePreviewPane component** (Medium priority) ⏳
  - **Assigned To:** ui-engineer-enhanced
  - **Dependencies:** None (parallel)
  - **File:** `skillmeat/web/components/sync-status/file-preview-pane.tsx`
  - **Size:** ~120 lines
  - **Acceptance Criteria:**
    - [ ] Component created with file content display
    - [ ] Markdown rendering via react-markdown
    - [ ] Code highlighting via highlight.js or similar
    - [ ] File type detection (markdown, code, text, binary)
    - [ ] Loading skeleton during fetch
    - [ ] Error state for unsupported file types
    - [ ] Scrollable container for large files
    - [ ] File path breadcrumb at top
    - [ ] Line numbers for code files (optional)
    - [ ] Copy code button for code blocks
    - [ ] Responsive sizing
  - **Dependencies:**
    - react-markdown
    - remark-gfm
    - highlight.js
    - shadcn/ui Skeleton
  - **Key Files:**
    - New: `skillmeat/web/components/sync-status/file-preview-pane.tsx`
  - **Notes:**
    - Should handle large files gracefully (pagination/truncation)
    - Syntax highlighting for common languages: Python, JavaScript, TypeScript, Go, Rust, YAML, JSON

- [ ] **TASK-1.5: Create SyncActionsFooter component** (Medium priority) ⏳
  - **Assigned To:** ui-engineer-enhanced
  - **Dependencies:** None (parallel)
  - **File:** `skillmeat/web/components/sync-status/sync-actions-footer.tsx`
  - **Size:** ~80 lines
  - **Acceptance Criteria:**
    - [ ] Component created with button layout
    - [ ] Button group: Deploy, Sync, Merge, Rollback (if available)
    - [ ] Loading states: spinner + disabled state during operation
    - [ ] Coming Soon tooltips for disabled buttons
    - [ ] Button colors: primary (enabled), ghost (disabled with tooltip)
    - [ ] Responsive layout (stack on mobile, horizontal on desktop)
    - [ ] Click handlers for each button
    - [ ] Visual feedback (hover, active, disabled states)
    - [ ] Success/error state visualization
  - **Dependencies:**
    - shadcn/ui Button
    - shadcn/ui Tooltip
    - Radix UI icons
  - **Key Files:**
    - New: `skillmeat/web/components/sync-status/sync-actions-footer.tsx`
  - **Notes:**
    - Each button should have distinct color: Deploy (green), Sync (blue), Merge (orange), Rollback (red)
    - Tooltips for Coming Soon buttons should show "Coming in next release"
    - Button group should have consistent 8px gap spacing

---

## Task Status Legend

- ⏳ **Pending:** Not started
- 🔄 **In Progress:** Currently being worked on
- ✅ **Completed:** Done and tested
- 🐛 **Blocked:** Waiting on dependencies
- ⚠️  **Needs Review:** Completed but review pending

---

## Component Size Estimates

| Component | Estimated Lines | Agent | Dependencies | Status |
|-----------|-----------------|-------|--------------|--------|
| ArtifactFlowBanner | ~150 | ui-engineer-enhanced | None | ⏳ |
| ComparisonSelector | ~80 | ui-engineer-enhanced | None | ⏳ |
| DriftAlertBanner | ~100 | ui-engineer-enhanced | None | ⏳ |
| FilePreviewPane | ~120 | ui-engineer-enhanced | None | ⏳ |
| SyncActionsFooter | ~80 | ui-engineer-enhanced | None | ⏳ |
| **Phase 1 Total** | **~530** | — | — | **0%** |

---

## Parallelization Strategy

### Execution Plan

**Phase 1 (Parallel Execution):**
All 5 sub-components can be built simultaneously since they have no interdependencies:

```
┌─────────────────────────────────────────────────────────────────┐
│ PARALLEL EXECUTION BATCH 1 (ui-engineer-enhanced)              │
├─────────────────────────────────────────────────────────────────┤
│ TASK-1.1: ArtifactFlowBanner (~150 lines)                      │
│ TASK-1.2: ComparisonSelector (~80 lines)                       │
│ TASK-1.3: DriftAlertBanner (~100 lines)                        │
│ TASK-1.4: FilePreviewPane (~120 lines)                         │
│ TASK-1.5: SyncActionsFooter (~80 lines)                        │
└─────────────────────────────────────────────────────────────────┘
```

**Phase 2 (Sequential - Blocked by Phase 1):**

```
┌─────────────────────────────────────────────────────────────────┐
│ TASK-2.1: SyncStatusTab orchestration                          │
│ Dependencies: TASK-1.1, 1.2, 1.3, 1.4, 1.5                     │
│ Agent: ui-engineer-enhanced                                     │
│ Work: Import all 5 components, add state management, hooks     │
└─────────────────────────────────────────────────────────────────┘
```

**Phase 3 (Sequential - Blocked by Phase 2):**

```
┌─────────────────────────────────────────────────────────────────┐
│ TASK-3.1: Integrate into unified-entity-modal                  │
│ Dependencies: TASK-2.1                                          │
│ Agent: ui-engineer-enhanced                                     │
│ Work: Replace existing tab content, update modal props         │
└─────────────────────────────────────────────────────────────────┘
```

**Phase 4 (Parallel - Both blocked by Phase 3):**

```
┌─────────────────────────────────────────────────────────────────┐
│ PARALLEL EXECUTION BATCH 2                                     │
├─────────────────────────────────────────────────────────────────┤
│ TASK-4.1: Wire all action buttons to hooks                     │
│ TASK-4.2: Add Coming Soon tooltips                             │
│ Dependencies: TASK-3.1                                          │
│ Agent: ui-engineer-enhanced                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Critical Path

```
TASK-1.1 ─┐
TASK-1.2 ─┤
TASK-1.3 ─┼─→ TASK-2.1 ─→ TASK-3.1 ─┬─→ TASK-4.1
TASK-1.4 ─┤                          └─→ TASK-4.2
TASK-1.5 ─┘
```

**Timeline Estimate:**
- Batch 1 (parallel): 2-3 hours (all 5 components simultaneously)
- Task 2.1 (sequential): 1 hour
- Task 3.1 (sequential): 30 minutes
- Batch 2 (parallel): 1 hour

**Total:** 4.5-5.5 hours of development time

### Optimization Notes

1. **Maximum Parallelization**: All Phase 1 tasks can run concurrently on different files
2. **Single Agent**: All work goes to `ui-engineer-enhanced` (UI specialist)
3. **No Handoffs**: Same agent handles entire feature stack, reducing coordination overhead
4. **Clean Interfaces**: Each component accepts props, no shared state until orchestration
5. **Independent Testing**: Each component can be tested in isolation before integration

---

## Design Specifications

### Color Palette (Tailwind)

| Status | Color | Tailwind Class |
|--------|-------|----------------|
| Synced | Green | `bg-green-50`, `text-green-900`, `border-green-200` |
| Modified | Yellow | `bg-yellow-50`, `text-yellow-900`, `border-yellow-200` |
| Outdated | Blue | `bg-blue-50`, `text-blue-900`, `border-blue-200` |
| Conflict | Red | `bg-red-50`, `text-red-900`, `border-red-200` |

### Layout Grid

```
┌─────────────────────────────────────────┐
│ Drift Alert Banner (full width)         │
├──────────────────────┬──────────────────┤
│ ArtifactFlowBanner   │ ComparisonSelector
│ (3-tier visualization)│ + File Preview   │
│ (left panel)         │ (right panel)    │
├──────────────────────┴──────────────────┤
│ Sync Actions Footer (full width)        │
└─────────────────────────────────────────┘
```

### Spacing & Sizing

- Container padding: 16px
- Component gaps: 8px
- Left panel width: 40%
- Right panel width: 60%
- Footer height: 56px

---

## Dependencies & Prerequisites

### External Libraries (verify installed)
- [ ] shadcn/ui (Alert, Button, Select, Tooltip, Skeleton)
- [ ] react-markdown
- [ ] remark-gfm
- [ ] highlight.js

### Internal Dependencies
- [ ] useSync hook (for sync operations)
- [ ] useDeploy hook (for deploy operations)
- [ ] useVersionGraph hook (for version data)

---

## Testing Strategy

### Unit Tests (per component)
- [ ] Component renders without errors
- [ ] Props are correctly passed and used
- [ ] Callbacks fire on user interaction
- [ ] Loading/error states display correctly
- [ ] Responsive behavior works

### Integration Tests
- [ ] All 5 components integrate in SyncStatusTab
- [ ] Data flows correctly between components
- [ ] Button actions trigger parent callbacks

### Manual Testing Checklist
- [ ] Visual appearance matches design
- [ ] Keyboard navigation works (Tab, Enter, Space)
- [ ] Mobile responsive (test at 320px, 768px, 1024px)
- [ ] Dark mode works correctly
- [ ] Tooltips display on hover

---

## Next Steps (Phase 2 & Beyond)

**After Phase 1 completion:**

1. **Phase 2:** Create SyncStatusTab component (orchestration)
   - Imports all 5 Phase 1 components
   - State management for selected comparison
   - API integration via useSync/useDeploy hooks
   - Query/mutation logic

2. **Phase 3:** Integrate into unified-entity-modal.tsx
   - Replace current Sync Status tab content
   - Update modal props/types
   - Wire entity data to components

3. **Phase 4:** Polish & Actions
   - Wire all buttons to real API calls
   - Add Coming Soon states properly
   - Toast notifications for success/error
   - Loading states during operations

---

## Notes & Observations

- All components are presentational (receive data via props)
- State management will be handled by SyncStatusTab parent
- Use Tailwind for all styling (no CSS modules)
- Follow shadcn/ui patterns for consistency
- Each component should be independently testable
