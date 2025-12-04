---
type: progress
prd: "discovery-import-enhancement"
phase: 4
title: "Frontend - Discovery Tab & UI Polish"
status: "planning"
started: null
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 12
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["ui-engineer-enhanced"]
contributors: ["frontend-developer", "testing-specialist"]

tasks:
  - id: "DIS-4.1"
    description: "Create DiscoveryTab.tsx component with artifact table/list displaying metadata and status badges"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "1.5d"
    priority: "critical"

  - id: "DIS-4.2"
    description: "Add artifact filtering and sorting controls to Discovery Tab (by status, type, date)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["DIS-4.1"]
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-4.3"
    description: "Integrate DiscoveryTab into Project Detail page with tab switcher (Deployed | Discovery)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["DIS-4.1"]
    estimated_effort: "1d"
    priority: "critical"

  - id: "DIS-4.4"
    description: "Update DiscoveryBanner visibility logic - only show if importable_count > 0"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "0.5d"
    priority: "medium"

  - id: "DIS-4.5"
    description: "Update toast-utils.ts to display detailed breakdown (Imported:N | Skipped:N | Failed:N)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: []
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-4.6"
    description: "Add skip management UI in Discovery Tab - list skipped artifacts with Un-skip buttons"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["DIS-4.1"]
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-4.7"
    description: "Add artifact context menu with Import, Skip, View details, Copy source actions"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["DIS-4.1"]
    estimated_effort: "0.5d"
    priority: "medium"

  - id: "DIS-4.8"
    description: "Unit tests for DiscoveryTab rendering with various artifact lists and filters"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["DIS-4.1", "DIS-4.2"]
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-4.9"
    description: "Unit tests for banner visibility logic - only shown when importable_count > 0"
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: ["DIS-4.4"]
    estimated_effort: "0.5d"
    priority: "medium"

  - id: "DIS-4.10"
    description: "Unit tests for toast utilities - detailed breakdown display"
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: ["DIS-4.5"]
    estimated_effort: "0.5d"
    priority: "medium"

  - id: "DIS-4.11"
    description: "E2E test for Discovery Tab navigation - tab visible, clickable, state persists via URL"
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: ["DIS-4.3"]
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-4.12"
    description: "E2E test for skip management in tab - Un-skip artifact and verify updated in future discovery"
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: ["DIS-4.6"]
    estimated_effort: "1d"
    priority: "high"

parallelization:
  batch_1: ["DIS-4.1", "DIS-4.4", "DIS-4.5"]
  batch_2: ["DIS-4.2", "DIS-4.3", "DIS-4.6", "DIS-4.7"]
  batch_3: ["DIS-4.8", "DIS-4.9", "DIS-4.10"]
  batch_4: ["DIS-4.11", "DIS-4.12"]
  critical_path: ["DIS-4.1", "DIS-4.2", "DIS-4.3", "DIS-4.8"]
  estimated_total_time: "8-10 days"

blockers: []

success_criteria:
  - id: "SC-1"
    description: "DiscoveryTab component renders correctly with various data sets"
    status: "pending"
  - id: "SC-2"
    description: "Artifact filters and sorting functional"
    status: "pending"
  - id: "SC-3"
    description: "Tab switcher integrated into Project Detail, tab state persists"
    status: "pending"
  - id: "SC-4"
    description: "Banner only shows when importable_count > 0"
    status: "pending"
  - id: "SC-5"
    description: "Toast utilities display detailed breakdown with counts"
    status: "pending"
  - id: "SC-6"
    description: "Skip management UI functional (Un-skip, Clear all)"
    status: "pending"
  - id: "SC-7"
    description: "Artifact actions menu keyboard accessible"
    status: "pending"
  - id: "SC-8"
    description: "Unit test coverage >80%"
    status: "pending"
  - id: "SC-9"
    description: "E2E tests pass: tab navigation, skip management"
    status: "pending"
  - id: "SC-10"
    description: "Visual design consistent with existing UI"
    status: "pending"

files_modified:
  - "skillmeat/web/components/discovery/DiscoveryTab.tsx"
  - "skillmeat/web/components/discovery/ArtifactActions.tsx"
  - "skillmeat/web/components/discovery/SkipPreferencesList.tsx"
  - "skillmeat/web/app/projects/[id]/page.tsx"
  - "skillmeat/web/components/discovery/DiscoveryBanner.tsx"
  - "skillmeat/web/lib/toast-utils.ts"
  - "skillmeat/web/__tests__/DiscoveryTab.test.tsx"
  - "skillmeat/web/__tests__/toast-utils.test.ts"
  - "skillmeat/web/tests/e2e/discovery-tab-navigation.spec.ts"
  - "skillmeat/web/tests/e2e/skip-management.spec.ts"
---

# Discovery & Import Enhancement - Phase 4: Frontend - Discovery Tab & UI Polish

**Phase**: 4 of 6
**Status**: 📋 Planning (0% complete)
**Duration**: Estimated 2-3 days
**Owner**: ui-engineer-enhanced
**Contributors**: frontend-developer, testing-specialist
**Dependency**: Phase 3 ✓ Complete

---

## Orchestration Quick Reference

> **For Orchestration Agents**: Launch Phase 4 after Phase 3 completes. This is the primary UI implementation phase.

### Parallelization Strategy

**Batch 1** (Parallel - No Dependencies):
- DIS-4.1 → `ui-engineer-enhanced` (1.5d) - Create DiscoveryTab component
- DIS-4.4 → `ui-engineer-enhanced` (0.5d) - Update banner visibility logic
- DIS-4.5 → `frontend-developer` (1d) - Update toast utilities

**Batch 2** (Parallel - Depends on Batch 1):
- DIS-4.2 → `ui-engineer-enhanced` (1d) - Add filters and sorting (depends on DIS-4.1)
- DIS-4.3 → `ui-engineer-enhanced` (1d) - Integrate into Project Detail (depends on DIS-4.1)
- DIS-4.6 → `ui-engineer-enhanced` (1d) - Skip management UI (depends on DIS-4.1)
- DIS-4.7 → `ui-engineer-enhanced` (0.5d) - Artifact context menu (depends on DIS-4.1)

**Batch 3** (Parallel - Depends on Batch 2):
- DIS-4.8 → `ui-engineer-enhanced` (1d) - DiscoveryTab unit tests (depends on DIS-4.1, DIS-4.2)
- DIS-4.9 → `testing-specialist` (0.5d) - Banner visibility tests (depends on DIS-4.4)
- DIS-4.10 → `testing-specialist` (0.5d) - Toast utilities tests (depends on DIS-4.5)

**Batch 4** (Sequential - Depends on Batch 3):
- DIS-4.11 → `testing-specialist` (1d) - E2E tab navigation (depends on DIS-4.3)
- DIS-4.12 → `testing-specialist` (1d) - E2E skip management (depends on DIS-4.6)

**Critical Path**: DIS-4.1 → DIS-4.2 → DIS-4.3 → DIS-4.8 (8-10 days total)

### Task Delegation Commands

```
# Batch 1 (Launch in parallel)
Task("ui-engineer-enhanced", "DIS-4.1: Create DiscoveryTab.tsx component showing artifacts in table/list format. File: skillmeat/web/components/discovery/DiscoveryTab.tsx (new). Include: name, type, status, size, source columns. Acceptance: (1) Renders artifact list; (2) Shows metadata; (3) Status badges color-coded; (4) Responsive; (5) Handles large lists")

Task("ui-engineer-enhanced", "DIS-4.4: Update DiscoveryBanner visibility - only show if importable_count > 0. File: skillmeat/web/components/discovery/DiscoveryBanner.tsx. Acceptance: (1) Hidden when 0; (2) Visible when >0; (3) Tests validate; (4) No false positives")

Task("frontend-developer", "DIS-4.5: Update toast-utils.ts to display detailed breakdown. File: skillmeat/web/lib/toast-utils.ts. Format: 'Imported to Collection: 3 | Added to Project: 5 | Skipped: 2'. Acceptance: (1) Toast accepts breakdown; (2) Displays multi-line; (3) Clickable link to Notification Center; (4) Responsive")

# Batch 2 (After Batch 1 completes)
Task("ui-engineer-enhanced", "DIS-4.2: Add filtering and sorting to DiscoveryTab. File: skillmeat/web/components/discovery/DiscoveryTab.tsx. Filters: by status (success/skipped/failed), by type (skill/command/etc.), by date range. Sort: name, type, discovered_at. Acceptance: (1) Filters visible; (2) Apply to table; (3) Sort working; (4) Filtered state persists during session")

Task("ui-engineer-enhanced", "DIS-4.3: Integrate DiscoveryTab into Project Detail. File: skillmeat/web/app/projects/[id]/page.tsx. Add tab switcher: 'Deployed' | 'Discovery'; route via URL param (?tab=discovery). Acceptance: (1) Tabs visible; (2) Tab switching works; (3) URL updates; (4) State persists; (5) No layout shift")

Task("ui-engineer-enhanced", "DIS-4.6: Add skip management UI in Discovery Tab. File: skillmeat/web/components/discovery/SkipPreferencesList.tsx (new). Show: list of skipped artifacts with Un-skip buttons, Clear all button with confirmation. Acceptance: (1) Skipped artifacts listed; (2) Un-skip removes skip; (3) Clear all with confirmation; (4) Updates reflected immediately")

Task("ui-engineer-enhanced", "DIS-4.7: Add artifact context menu. File: skillmeat/web/components/discovery/ArtifactActions.tsx (new). Actions: Import, Skip for future, View details, Copy source. Acceptance: (1) Actions visible on hover/click; (2) Import opens confirmation; (3) Skip toggles checkbox; (4) Keyboard accessible")

# Batch 3 (After Batch 2 completes)
Task("ui-engineer-enhanced", "DIS-4.8: Unit tests for DiscoveryTab rendering. File: skillmeat/web/__tests__/DiscoveryTab.test.tsx (new). Test: empty state, single artifact, many artifacts, filters apply, sorts apply. Acceptance: (1) Empty state displays; (2) Artifacts render; (3) Filters apply; (4) Sorts apply; (5) Coverage >80%")

Task("testing-specialist", "DIS-4.9: Unit tests for banner visibility. File: skillmeat/web/__tests__/DiscoveryBanner.test.tsx (update). Test: hidden when 0, visible when >0. Acceptance: (1) Coverage >80%")

Task("testing-specialist", "DIS-4.10: Unit tests for toast utilities. File: skillmeat/web/__tests__/toast-utils.test.ts (update). Test: breakdown parsed, displayed correctly, responsive. Acceptance: (1) Coverage >80%")

# Batch 4 (After Batch 3 completes)
Task("testing-specialist", "DIS-4.11: E2E test for Discovery Tab navigation. File: skillmeat/web/tests/e2e/discovery-tab-navigation.spec.ts (new). Test: tab visible, clickable, shows artifacts, URL updates, reload keeps tab selected. Acceptance: (1) Tab visible; (2) Click navigates; (3) URL updates; (4) Artifacts display; (5) Reload persists")

Task("testing-specialist", "DIS-4.12: E2E test for skip management. File: skillmeat/web/tests/e2e/skip-management.spec.ts (new). Test: click Un-skip → artifact removed from skip list → future discovery includes artifact. Acceptance: (1) Un-skip works; (2) Artifact removed; (3) Future discovery includes")
```

---

## Overview

**Phase 4** creates the permanent Discovery Tab UI component on the Project Detail page, enabling users to view, filter, sort, and manage discovered artifacts alongside their deployed artifacts. This phase includes UI polish, improved toast notifications with detailed breakdowns, and skip preference management UI.

**Why This Phase**: Phases 1-3 established the backend logic and frontend types; Phase 4 materializes the user experience with a permanent, discoverable interface for managing discoveries.

**Scope**:
- **IN**: Discovery Tab component, filters/sorting, tab integration, skip management UI, toast improvements, E2E tests
- **OUT**: Notification System integration (Phase 5), analytics (Phase 6)

---

## Success Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| SC-1 | DiscoveryTab component renders correctly with various data sets | ⏳ Pending |
| SC-2 | Artifact filters and sorting functional | ⏳ Pending |
| SC-3 | Tab switcher integrated into Project Detail, tab state persists | ⏳ Pending |
| SC-4 | Banner only shows when importable_count > 0 | ⏳ Pending |
| SC-5 | Toast utilities display detailed breakdown with counts | ⏳ Pending |
| SC-6 | Skip management UI functional (Un-skip, Clear all) | ⏳ Pending |
| SC-7 | Artifact actions menu keyboard accessible | ⏳ Pending |
| SC-8 | Unit test coverage >80% | ⏳ Pending |
| SC-9 | E2E tests pass: tab navigation, skip management | ⏳ Pending |
| SC-10 | Visual design consistent with existing UI | ⏳ Pending |

---

## Tasks

| ID | Task | Status | Agent | Dependencies | Est | Notes |
|----|------|--------|-------|--------------|-----|-------|
| DIS-4.1 | Create DiscoveryTab component | ⏳ | ui-engineer-enhanced | None | 1.5d | Table/list with metadata |
| DIS-4.2 | Add filters and sorting | ⏳ | ui-engineer-enhanced | DIS-4.1 | 1d | Status, type, date |
| DIS-4.3 | Integrate tab into Project Detail | ⏳ | ui-engineer-enhanced | DIS-4.1 | 1d | Tab switcher + URL param |
| DIS-4.4 | Update banner visibility | ⏳ | ui-engineer-enhanced | None | 0.5d | Only if importable_count > 0 |
| DIS-4.5 | Update toast-utils | ⏳ | frontend-developer | None | 1d | Detailed breakdown |
| DIS-4.6 | Add skip management UI | ⏳ | ui-engineer-enhanced | DIS-4.1 | 1d | List skips, Un-skip |
| DIS-4.7 | Add artifact context menu | ⏳ | ui-engineer-enhanced | DIS-4.1 | 0.5d | Import, Skip, Details |
| DIS-4.8 | Unit tests - DiscoveryTab | ⏳ | ui-engineer-enhanced | DIS-4.1, DIS-4.2 | 1d | Rendering, filters, sorts |
| DIS-4.9 | Unit tests - banner | ⏳ | testing-specialist | DIS-4.4 | 0.5d | Visibility logic |
| DIS-4.10 | Unit tests - toast | ⏳ | testing-specialist | DIS-4.5 | 0.5d | Breakdown display |
| DIS-4.11 | E2E test - tab navigation | ⏳ | testing-specialist | DIS-4.3 | 1d | URL persistence |
| DIS-4.12 | E2E test - skip management | ⏳ | testing-specialist | DIS-4.6 | 1d | Un-skip workflow |

---

## Architecture Context

### Current State

Project Detail page shows only deployed artifacts. DiscoveryBanner appears when discoveries available but lacks permanent UI. BulkImportModal handles import but doesn't persist access to discovered artifacts.

**Key Files**:
- `skillmeat/web/app/projects/[id]/page.tsx` - Project Detail
- `skillmeat/web/components/discovery/DiscoveryBanner.tsx` - Banner component
- `skillmeat/web/lib/toast-utils.ts` - Toast notifications

### Reference Patterns

Tab switcher implementation in codebase:
- Similar tab pattern used in Artifact Detail (Metadata | Versions tabs)
- URL param routing (e.g., `?tab=metadata`)
- Tab state persistence via URL

---

## Implementation Details

### Technical Approach

1. **DiscoveryTab Component (DIS-4.1)**:
   - Table layout with columns: Name, Type, Status (badge), Size, Source, Actions
   - Empty state when no artifacts discovered
   - Loading skeleton states during discovery
   - Responsive (desktop-first, mobile-friendly table or list view)

2. **Filters & Sorting (DIS-4.2)**:
   - Filter buttons: Status (Success/Skipped/Failed), Type (Skill/Command/etc.), Date range
   - Sort dropdown: Name, Type, Discovered date
   - Filtered state stored in component state (persists during session)

3. **Tab Integration (DIS-4.3)**:
   - Add tabs on Project Detail: "Deployed" | "Discovery"
   - Tab switching updates URL param: `?tab=deployed` or `?tab=discovery`
   - Tab state persists on page reload (read from URL)
   - Deployed tab shows existing artifacts, Discovery tab shows discovered

4. **Banner Visibility (DIS-4.4)**:
   - Update DiscoveryBanner to check `importable_count > 0`
   - Hide if all discovered artifacts already exist locally
   - Remove false positives

5. **Toast Breakdown (DIS-4.5)**:
   - Update toast to accept breakdown object
   - Display: "Imported to Collection: 3 | Added to Project: 5 | Skipped: 2"
   - Add link to Notification Center for details

6. **Skip Management UI (DIS-4.6)**:
   - Section in Discovery Tab showing skipped artifacts
   - List with artifact names and skip reasons
   - "Un-skip" button removes skip preference
   - "Clear all" button with confirmation modal

7. **Context Menu (DIS-4.7)**:
   - Right-click or icon menu on each artifact
   - Actions: Import, Skip for future, View details, Copy source
   - Keyboard accessible (Tab + Enter)

### Known Gotchas

- **Large Lists**: 500+ artifacts → use virtualization or pagination
- **Tab State**: Browser back/forward navigation → update URL handling
- **Responsive Design**: Table → card list on mobile
- **Accessibility**: Tab order, ARIA labels on badges and menus

### Development Setup

- Test project with 100+ discovered artifacts
- Test skip preferences with various states
- Responsive testing on mobile devices

---

## Blockers

### Active Blockers

- **Phase 3 Dependency**: Awaiting Phase 3 completion (skip checkbox UI, types)

---

## Dependencies

### External Dependencies

- **Phase 3 Complete**: Skip checkbox UI, LocalStorage persistence, types
- **Phase 1-2 Complete**: Backend endpoints, status enum, pre-scan logic

### Internal Integration Points

- **Project Detail Page** - Tab switcher integration
- **BulkImportModal** - Artifact import actions
- **useProjectDiscovery Hook** - Discovery and skip state
- **Toast Utils** - Detailed breakdown display
- **Notification System** - Detail breakdown consumption (Phase 5)

---

## Testing Strategy

| Test Type | Scope | Coverage | Status |
|-----------|-------|----------|--------|
| Unit - DiscoveryTab | Rendering, filters, sorting, empty/loaded states | 80%+ | ⏳ |
| Unit - Banner | Visibility logic with various importable_count values | 80%+ | ⏳ |
| Unit - Toast | Breakdown parsing and display | 80%+ | ⏳ |
| Unit - Skip Management | Un-skip, Clear all operations | 80%+ | ⏳ |
| E2E - Tab Navigation | Tab click, URL update, reload persistence | Happy path | ⏳ |
| E2E - Skip Management | Un-skip artifact, verify in future discovery | Happy path | ⏳ |
| Accessibility | Tab navigation (Tab key), Menu keyboard access, ARIA labels | WCAG AA | ⏳ |
| Responsive | Table → list on mobile, touch-friendly interactions | Mobile + desktop | ⏳ |

---

## Next Session Agenda

### Immediate Actions (Next Session - After Phase 3 Complete)
1. [ ] Launch Batch 1: Start DIS-4.1 and DIS-4.4 and DIS-4.5
2. [ ] Setup test fixtures for discovery artifacts (100+ artifacts)
3. [ ] Review design system for table, tabs, badges, menu components
4. [ ] Coordinate with Phase 5 on Notification System integration

### Upcoming Critical Items

- **Day 1-2**: Batch 2 completion (tab integration, filters, skip management)
- **Day 3-4**: Batch 3 starts (unit tests)
- **Day 5**: Quality gate check - all tests passing, responsive design verified

### Context for Continuing Agent

Phase 4 is highly visual and interactive. Focus on:
1. DiscoveryTab rendering performance (virtualization if >500 artifacts)
2. Tab state persistence via URL (critical for UX)
3. Accessibility: tab navigation, ARIA labels, keyboard shortcuts
4. Responsive design: table → list on mobile
5. Visual consistency with existing Skillmeat UI (colors, spacing, typography)

---

## Session Notes

*None yet - Phase 4 not started*

---

## Additional Resources

- **Design Reference**: Existing tab patterns in Project Detail or Artifact Detail
- **Component Library**: Radix UI + shadcn components (table, tabs, dialog, menu)
- **Phase 3 Results**: Skip checkbox UI, LocalStorage persistence, types
- **Phase 1-2 Results**: Backend endpoints, status enum, skip preference API
- **UI Consistency**: Skillmeat design system colors, spacing, typography
