---
title: 'Phases 4-6: Frontend Implementation'
description: Components, pages, and dialogs for marketplace sources enhancement
parent: ../marketplace-sources-enhancement-v1.md
phases:
- 4
- 5
- 6
status: inferred_complete
schema_version: 2
doc_type: phase_plan
feature_slug: marketplace-sources-enhancement
prd_ref: null
plan_ref: null
---
# Phases 4-6: Frontend Implementation

**Parent Plan**: [Marketplace Sources Enhancement v1](../marketplace-sources-enhancement-v1.md)

---

## Phase 4: Frontend Components - Filter UI & Source Card Redesign

**Duration**: 3 days
**Dependencies**: Phase 3 complete (API contract defined)
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer
**Start after**: Phase 3 API contract finalized (can begin design during Phase 3)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| UI-001 | SourceFilterBar Component | Create reusable filter UI component with artifact type, tags, trust level filters | Component accepts current filters; renders dropdowns/chip inputs; emits filter change events; keyboard accessible | 2 pts | ui-engineer-enhanced | API-009 |
| UI-002 | Tag Badge Component | Create tag display component with color coding and overflow handling | Tags render as colored badges; overflow shows "+n more"; hover tooltip reveals all tags; WCAG AA color contrast | 2 pts | ui-engineer-enhanced | UI-001 |
| UI-003 | Count Badge Component | Create artifact count badge with type breakdown tooltip | Badge shows total count; hover reveals breakdown ("Skills: 5, Commands: 3, Agents: 2"); aria-label for a11y | 1 pt | ui-engineer-enhanced | UI-001 |
| UI-004 | SourceCard Redesign | Redesign source card to display tags, count badge, description fallback | Card displays: repo name, branch, tags, count badge, description (fallback to repo_description if user description empty), badges (status, trust level) | 3 pts | frontend-developer | UI-003 |
| UI-005 | RepoDetailsModal Component | Create modal to display repository description and README in ContentPane | Modal layout: description section at top, README in scrollable ContentPane; keyboard navigable (Escape to close); focus management | 2 pts | ui-engineer-enhanced | UI-001 |
| UI-006 | Clickable Tags | Implement tag click handlers to apply filters | Clicking tag on card/detail page applies tag filter to current view; filter UI updates to reflect clicked tag | 1 pt | frontend-developer | UI-004 |
| UI-007 | Component Accessibility | Implement WCAG 2.1 AA accessibility for all components | ARIA labels on all interactive elements; semantic HTML; keyboard navigation; color contrast tested | 1 pt | frontend-developer | UI-006 |

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

**Notes**: These components should be built using shadcn/ui primitives (Button, Badge, Dialog, Tooltip) for consistency with existing UI. No direct DOM manipulation; all state managed via React hooks and context.

---

## Phase 5: Frontend Pages - Marketplace Sources & Source Detail Integration

**Duration**: 2 days
**Dependencies**: Phase 4 complete (components ready)
**Assigned Subagent(s)**: frontend-developer
**Start after**: Phase 4 component implementation complete

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| PAGE-001 | Sources List Page Enhancement | Update /marketplace/sources page to include SourceFilterBar and integrate filtering | Page renders SourceFilterBar; filter changes trigger API calls via TanStack Query; results update in real-time | 2 pts | frontend-developer | UI-007 |
| PAGE-002 | URL State Sync | Sync filter state with URL query parameters | Filter values reflected in URL (?artifact_type=skill&tags=ui); browser back/forward works correctly | 1 pt | frontend-developer | PAGE-001 |
| PAGE-003 | Source Card List Update | Replace old source cards with redesigned cards on sources list | SourceCards display tags, count badges, descriptions; pagination preserved | 1 pt | frontend-developer | PAGE-001 |
| PAGE-004 | Clear Filters Button | Add button to reset all filters to defaults | Clicking "Clear Filters" resets URL and TanStack Query state; filters disappear from UI | 1 pt | frontend-developer | PAGE-002 |
| PAGE-005 | Loading & Error States | Implement loading states and error boundaries for filtered results | Loading spinner shown while fetching; errors displayed in error boundary; retry button available | 1 pt | frontend-developer | PAGE-004 |
| PAGE-006 | Source Detail Page Updates | Update /marketplace/sources/[id] page with artifact filtering and Repo Details button | Page shows "Repo Details" button (only if description/README populated); button opens RepoDetailsModal | 2 pts | frontend-developer | PAGE-005 |
| PAGE-007 | Artifact Filtering on Detail Page | Add type and status filters to source detail page catalog | Detail page filters artifacts by type and status using new query params; list updates on filter change | 2 pts | frontend-developer | PAGE-006 |

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

**Notes**: Use TanStack Query for managing filter state and API calls. Leverage useSearchParams/useRouter from next/navigation for URL state synchronization.

---

## Phase 6: Frontend Dialogs - Import & Edit Updates

**Duration**: 2 days
**Dependencies**: Phase 5 complete (core pages functional)
**Assigned Subagent(s)**: frontend-developer, ui-engineer-enhanced
**Start after**: Phase 5 page integration complete

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DIALOG-001 | CreateSourceDialog Enhancement | Update import dialog to include import_repo_description and import_repo_readme toggles | Dialog includes two toggles: "Include Repository Description" and "Include Repository README"; default to false | 1 pt | ui-engineer-enhanced | PAGE-007 |
| DIALOG-002 | CreateSourceDialog Tags Input | Add tags field to import dialog with input and chip display | Tags input field accepts comma-separated or chip-entry; validates tag format; displays chips for each tag; max 20 tags | 2 pts | frontend-developer | DIALOG-001 |
| DIALOG-003 | EditSourceDialog Enhancement | Update edit dialog to include toggles and tags management | Edit dialog mirrors create dialog toggles and tags field; allows modifying existing tags | 1 pt | frontend-developer | DIALOG-002 |
| DIALOG-004 | Toggle Help Text | Add explanatory text for toggles and tags field | Tooltips explain: "Repository Description will be fetched from GitHub", "Tags help organize sources for discovery" | 1 pt | ui-engineer-enhanced | DIALOG-003 |
| DIALOG-005 | Dialog Validation | Implement validation for tags and dialog submission | Tags validated before submission; invalid tags show error; submit button disabled if validation fails | 1 pt | frontend-developer | DIALOG-004 |
| DIALOG-006 | API Integration | Integrate dialogs with backend endpoints (POST/PUT) | Dialog submission calls create/update API with toggles and tags; loading state shown; success/error feedback | 1 pt | frontend-developer | DIALOG-005 |

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

**Notes**: Keep toggles unchecked by default to be conservative about fetching external resources. User can explicitly enable if desired.

---

## Key Frontend Files

| File | Phase | Changes |
|------|-------|---------|
| `skillmeat/web/types/marketplace.ts` | 4 | Update GitHubSource type with new fields |
| `skillmeat/web/components/marketplace/source-card.tsx` | 4 | Redesign to show tags, count badges, description fallback |
| `skillmeat/web/components/marketplace/source-filter-bar.tsx` | 4 | New component for filter UI |
| `skillmeat/web/components/marketplace/repo-details-modal.tsx` | 4 | New component for repo details |
| `skillmeat/web/components/marketplace/tag-badge.tsx` | 4 | New component for tag display |
| `skillmeat/web/components/marketplace/count-badge.tsx` | 4 | New component for artifact count |
| `skillmeat/web/app/marketplace/sources/page.tsx` | 5 | Add SourceFilterBar, integrate filters with API |
| `skillmeat/web/app/marketplace/sources/[id]/page.tsx` | 5-6 | Add Repo Details button, artifact filtering |
| `skillmeat/web/components/dialogs/create-source-dialog.tsx` | 6 | Add toggles and tags input |
| `skillmeat/web/components/dialogs/edit-source-dialog.tsx` | 6 | Add toggles and tags input |

---

## Frontend Testing Files

| File | Phase | Purpose |
|------|-------|---------|
| `tests/unit/frontend/source-filter-bar.test.tsx` | 7 | Component tests |
| `tests/e2e/marketplace/source-import.spec.ts` | 7 | E2E test for import workflow |
| `tests/e2e/marketplace/source-filtering.spec.ts` | 7 | E2E test for filtering |
| `tests/a11y/marketplace-components.test.ts` | 7 | Accessibility tests |

---

## Component Interface Examples

```typescript
// SourceFilterBar.tsx
interface SourceFilterBarProps {
  currentFilters: FilterState;
  onFilterChange: (filters: FilterState) => void;
  availableTags?: string[];
  trustLevels?: string[];
}

interface FilterState {
  artifact_type?: string;
  tags?: string[];
  trust_level?: string;
}

// SourceCard.tsx
interface SourceCardProps {
  source: GitHubSource;
  onTagClick?: (tag: string) => void;
}

// RepoDetailsModal.tsx
interface RepoDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  source: GitHubSource;
}

// TagBadge.tsx
interface TagBadgeProps {
  tags: string[];
  maxDisplay?: number;
  onTagClick?: (tag: string) => void;
}

// CountBadge.tsx
interface CountBadgeProps {
  countsByType: Record<string, number>;
}
```
