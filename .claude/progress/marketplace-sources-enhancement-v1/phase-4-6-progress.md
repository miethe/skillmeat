---
type: progress
prd: marketplace-sources-enhancement-v1
phase: 4-6
status: completed
progress: 0
created: 2026-01-18
updated: 2026-01-18
source: docs/project_plans/implementation_plans/enhancements/marketplace-sources-enhancement-v1/phase-4-6-frontend.md
---
# Phase 4-6 Progress: Frontend Implementation

**Phases**: 4 (Components), 5 (Pages), 6 (Dialogs)
**Duration**: 7 days total (3 + 2 + 2)
**Status**: Not Started

---

## Phase 4: Frontend Components - Filter UI & Source Card Redesign

**Duration**: 3 days
**Completion Target**: 7 tasks (UI-001 through UI-007)

### Batch 1: Independent Component Creation

| Task ID | Status | Assigned To | Task | Estimate | Notes |
|---------|--------|-------------|------|----------|-------|
| UI-001 | pending | ui-engineer-enhanced | SourceFilterBar Component | 2 pts | Create reusable filter UI component with artifact type, tags, trust level filters |
| UI-002 | pending | ui-engineer-enhanced | Tag Badge Component | 2 pts | Create tag display component with color coding and overflow handling |
| UI-003 | pending | ui-engineer-enhanced | Count Badge Component | 1 pt | Create artifact count badge with type breakdown tooltip |

### Batch 2: Card Redesign

| Task ID | Status | Assigned To | Task | Estimate | Notes |
|---------|--------|-------------|------|----------|-------|
| UI-004 | pending | frontend-developer | SourceCard Redesign | 3 pts | Redesign to display tags, count badge, description fallback |
| UI-005 | pending | ui-engineer-enhanced | RepoDetailsModal Component | 2 pts | Create modal for repository description and README display |

### Batch 3: Final Component Polish

| Task ID | Status | Assigned To | Task | Estimate | Notes |
|---------|--------|-------------|------|----------|-------|
| UI-006 | pending | frontend-developer | Clickable Tags | 1 pt | Implement tag click handlers to apply filters |
| UI-007 | pending | frontend-developer | Component Accessibility | 1 pt | Implement WCAG 2.1 AA accessibility for all components |

### Phase 4 Quality Gates

- [ ] SourceFilterBar renders correctly with all filter options
- [ ] Tag badges display with proper overflow handling
- [ ] Count badge shows total and type breakdown on hover
- [ ] SourceCard redesign matches artifact card visual patterns
- [ ] RepoDetailsModal accessible and navigable
- [ ] Clickable tags apply filters correctly
- [ ] All components meet WCAG 2.1 AA standards
- [ ] Component tests >80% coverage
- [ ] Components work on desktop, tablet, mobile

---

## Phase 5: Frontend Pages - Marketplace Sources & Source Detail Integration

**Duration**: 2 days
**Completion Target**: 7 tasks (PAGE-001 through PAGE-007)

### Batch 4: Page Integration & Filter Sync

| Task ID | Status | Assigned To | Task | Estimate | Notes |
|---------|--------|-------------|------|----------|-------|
| PAGE-001 | pending | frontend-developer | Sources List Page Enhancement | 2 pts | Update /marketplace/sources page to include SourceFilterBar and integrate filtering |
| PAGE-002 | pending | frontend-developer | URL State Sync | 1 pt | Sync filter state with URL query parameters |
| PAGE-003 | pending | frontend-developer | Source Card List Update | 1 pt | Replace old source cards with redesigned cards on sources list |

### Batch 5: Filters & States

| Task ID | Status | Assigned To | Task | Estimate | Notes |
|---------|--------|-------------|------|----------|-------|
| PAGE-004 | pending | frontend-developer | Clear Filters Button | 1 pt | Add button to reset all filters to defaults |
| PAGE-005 | pending | frontend-developer | Loading & Error States | 1 pt | Implement loading states and error boundaries for filtered results |

### Batch 6: Source Detail Page

| Task ID | Status | Assigned To | Task | Estimate | Notes |
|---------|--------|-------------|------|----------|-------|
| PAGE-006 | pending | frontend-developer | Source Detail Page Updates | 2 pts | Update /marketplace/sources/[id] page with artifact filtering and Repo Details button |
| PAGE-007 | pending | frontend-developer | Artifact Filtering on Detail Page | 2 pts | Add type and status filters to source detail page catalog |

### Phase 5 Quality Gates

- [ ] SourceFilterBar appears on marketplace sources list
- [ ] Filters apply via API and results update
- [ ] Filter state synced with URL
- [ ] Clear Filters button resets all state
- [ ] Loading and error states display correctly
- [ ] Source cards display new design elements
- [ ] Source detail page shows Repo Details button (conditional)
- [ ] Repo Details modal displays description and README
- [ ] Artifact filtering on detail page works correctly
- [ ] Page tests >80% coverage
- [ ] All interactions responsive (<100ms feedback)

---

## Phase 6: Frontend Dialogs - Import & Edit Updates

**Duration**: 2 days
**Completion Target**: 6 tasks (DIALOG-001 through DIALOG-006)

### Batch 7: Dialog Enhancements

| Task ID | Status | Assigned To | Task | Estimate | Notes |
|---------|--------|-------------|------|----------|-------|
| DIALOG-001 | pending | ui-engineer-enhanced | CreateSourceDialog Enhancement | 1 pt | Update import dialog to include import_repo_description and import_repo_readme toggles |
| DIALOG-002 | pending | frontend-developer | CreateSourceDialog Tags Input | 2 pts | Add tags field to import dialog with input and chip display |
| DIALOG-003 | pending | frontend-developer | EditSourceDialog Enhancement | 1 pt | Update edit dialog to include toggles and tags management |

### Batch 8: Final Dialog Work

| Task ID | Status | Assigned To | Task | Estimate | Notes |
|---------|--------|-------------|------|----------|-------|
| DIALOG-004 | pending | ui-engineer-enhanced | Toggle Help Text | 1 pt | Add explanatory text for toggles and tags field |
| DIALOG-005 | pending | frontend-developer | Dialog Validation | 1 pt | Implement validation for tags and dialog submission |
| DIALOG-006 | pending | frontend-developer | API Integration | 1 pt | Integrate dialogs with backend endpoints (POST/PUT) |

### Phase 6 Quality Gates

- [ ] CreateSourceDialog shows import toggles and tags field
- [ ] EditSourceDialog allows modifying tags and toggles
- [ ] Toggles default to false (conservative default)
- [ ] Tags input validates format and enforces limits
- [ ] Help text explains toggle and tag purposes
- [ ] Validation prevents invalid submissions
- [ ] API integration working (POST/PUT calls)
- [ ] Success/error feedback displayed
- [ ] Dialog tests >80% coverage
- [ ] Keyboard navigation and focus management working

---

## Execution Batches

### Parallelization Strategy

**Batch 1** (Phase 4 Components - Independent)
- UI-001: SourceFilterBar Component
- UI-002: Tag Badge Component
- UI-003: Count Badge Component

**Batch 2** (Phase 4 Components - Depend on Batch 1)
- UI-004: SourceCard Redesign
- UI-005: RepoDetailsModal Component

**Batch 3** (Phase 4 Components - Final)
- UI-006: Clickable Tags
- UI-007: Component Accessibility

**Batch 4** (Phase 5 Pages - Initial)
- PAGE-001: Sources List Page Enhancement
- PAGE-002: URL State Sync
- PAGE-003: Source Card List Update

**Batch 5** (Phase 5 Pages - Filter Controls)
- PAGE-004: Clear Filters Button
- PAGE-005: Loading & Error States

**Batch 6** (Phase 5 Pages - Detail Page)
- PAGE-006: Source Detail Page Updates
- PAGE-007: Artifact Filtering on Detail Page

**Batch 7** (Phase 6 Dialogs - Initial)
- DIALOG-001: CreateSourceDialog Enhancement
- DIALOG-002: CreateSourceDialog Tags Input
- DIALOG-003: EditSourceDialog Enhancement

**Batch 8** (Phase 6 Dialogs - Final)
- DIALOG-004: Toggle Help Text
- DIALOG-005: Dialog Validation
- DIALOG-006: API Integration

---

## Key Files to Modify

### Components (Phase 4)
- `skillmeat/web/types/marketplace.ts` - Update GitHubSource type
- `skillmeat/web/components/marketplace/source-filter-bar.tsx` - New
- `skillmeat/web/components/marketplace/tag-badge.tsx` - New
- `skillmeat/web/components/marketplace/count-badge.tsx` - New
- `skillmeat/web/components/marketplace/source-card.tsx` - Redesign
- `skillmeat/web/components/marketplace/repo-details-modal.tsx` - New

### Pages (Phase 5)
- `skillmeat/web/app/marketplace/sources/page.tsx` - Add filtering
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx` - Add details modal & filtering

### Dialogs (Phase 6)
- `skillmeat/web/components/dialogs/create-source-dialog.tsx` - Add toggles & tags
- `skillmeat/web/components/dialogs/edit-source-dialog.tsx` - Add toggles & tags

---

## Notes

- Components should use shadcn/ui primitives (Button, Badge, Dialog, Tooltip)
- No direct DOM manipulation; all state managed via React hooks
- Use TanStack Query for API calls and state management
- Leverage useSearchParams/useRouter from next/navigation for URL sync
- Toggles default to false for conservative resource fetching
- All components must meet WCAG 2.1 AA accessibility standards
- Target >80% test coverage for all components and pages
