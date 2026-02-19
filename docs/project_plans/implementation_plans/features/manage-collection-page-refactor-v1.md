---
title: 'Implementation Plan: /manage vs /collection Page Architecture Refactor'
description: Detailed implementation plan for separating and clarifying the purpose
  of the /manage (Operations Dashboard) and /collection (Browse & Discover) pages
  with distinct card components, modals, and cross-navigation.
status: inferred_complete
complexity: Medium
total_effort: 22-31 hours
phases: 6
related_specs:
- /docs/design/ui-component-specs-page-refactor.md
- /docs/project_plans/reports/manage-collection-page-architecture-analysis.md
- /docs/project_plans/PRDs/tools-api-support-v1.md
created: 2026-02-01
updated: 2026-02-02
category: features
schema_version: 2
doc_type: implementation_plan
feature_slug: manage-collection-page-refactor
prd_ref: null
---
# Implementation Plan: /manage vs /collection Page Architecture Refactor

**Design Foundation**: Option C - Distinct Purpose Pages with Cross-Links (Approved)

**Key Decision**: Each page uses its optimal backend system while maintaining clear semantic separation:
- `/collection` = Browse & Discover (primary page) - "What artifacts do I have?"
- `/manage` = Operations Dashboard (secondary page) - "What needs attention?"
- `/collection` remains the canonical route (collection and group selection via query params and local state)

**Prerequisites** (external dependencies):
- [x] Tools API PRD (`/docs/project_plans/PRDs/tools-api-support-v1.md`) - complete

---

## Table of Contents

1. [Overview & Complexity Assessment](#overview--complexity-assessment)
2. [Phase-by-Phase Implementation](#phase-by-phase-implementation)
3. [Component Specifications Reference](#component-specifications-reference)
4. [Quality Gates & Validation](#quality-gates--validation)
5. [Risk Mitigation](#risk-mitigation)
6. [Timeline & Resource Planning](#timeline--resource-planning)

---

## Overview & Complexity Assessment

### Complexity Determination: Medium (M)

**Criteria Met**:
- Multi-component: 6 new components + 2 page updates + filter enhancements
- Task Count: 29 distinct tasks across 6 phases
- Effort Range: 22-31 hours
- Architecture Impact: High (page-level separation) but low risk (backward compatible)
- Scope: Primarily frontend, contained within web layer

### Workflow Track: Standard Track

Uses Haiku agents for mechanical work + Sonnet agents for component implementation + guidance from Opus for architecture decisions.

### Success Criteria

| Criterion | Measurement |
|-----------|------------|
| User understands page purpose | >85% task completion in usability test |
| Cross-navigation works | Users can switch contexts without confusion |
| Load performance maintained | No >10% regression in page load times |
| Accessibility compliant | WCAG AA on all new components |
| Code coverage | >80% on new components (unit + integration) |

---

## Phase-by-Phase Implementation

### Phase 0: Schema & Cache Extensions (2-3 hours)

**Objective**: Extend ArtifactSummary schema and collection cache to include deployment information, enabling the "Deployed (N)" badge on browse cards.

**Subagent Leads**: python-backend-engineer, data-layer-expert

| Task ID | Task Name | Description | Acceptance Criteria | Est. Hours | Assignee |
|---------|-----------|-------------|-------------------|-----------|----------|
| SCHEMA-0.1 | Add deployments to ArtifactSummary schema | Add `deployments: Optional[List[DeploymentInfo]]` to `ArtifactSummary` in `user_collections.py`. DeploymentInfo includes `project_path`, `project_name`, `deployed_at` | 1. Schema updated with deployments field<br>2. Field is optional (backward compatible)<br>3. OpenAPI spec regenerated<br>4. SDK types updated | 0.5 | python-backend-engineer |
| SCHEMA-0.2 | Add deployments_json to CollectionArtifact cache | Add `deployments_json` column to `CollectionArtifact` model. Create Alembic migration (nullable column) | 1. Migration created and tested<br>2. Column is nullable for backward compat<br>3. Migration reversible | 0.5 | data-layer-expert |
| SCHEMA-0.3 | Populate deployments in cache | Update `populate_collection_artifact_metadata()` to store deployments from file-based CollectionManager. Update refresh-cache endpoints | 1. Deployments populated from metadata<br>2. Refresh endpoints update deployments<br>3. Cache miss fallback includes deployments | 1 | python-backend-engineer |
| SCHEMA-0.4 | Emit deployments in API responses | Update collection artifact endpoints to include deployments from cache. Ensure `/user-collections/{id}/artifacts` returns deployments | 1. Deployments appear in API response<br>2. Count matches actual deployments<br>3. No performance regression | 0.5 | python-backend-engineer |
| SCHEMA-0.5 | Update frontend Artifact type and mapper | Add `deployments` to frontend `Artifact` type. Update `entity-mapper.ts` to map deployments from API response | 1. TypeScript type updated<br>2. Mapper handles deployments<br>3. No type errors in build | 0.5 | frontend-developer |

**Phase 0 Quality Gate**:
- [ ] ArtifactSummary schema includes optional deployments field
- [ ] CollectionArtifact cache stores deployments_json
- [ ] `/user-collections/{id}/artifacts` returns deployments in response
- [ ] Frontend Artifact type includes deployments
- [ ] No migration errors, no type errors

**Phase 0 Output Artifacts**:
- Updated `skillmeat/api/schemas/user_collections.py`
- New Alembic migration for deployments_json column
- Updated `skillmeat/api/managers/collection_cache_manager.py`
- Updated `skillmeat/web/types/artifact.ts`
- Updated `skillmeat/web/lib/api/entity-mapper.ts`
- Regenerated SDK types

---

### Phase 1: Page Structure & Navigation (5-7 hours)

**Objective**: Establish clear page identities through navigation, headers, and deep linking infrastructure.

**Subagent Leads**: ui-engineer-enhanced, frontend-developer

| Task ID | Task Name | Description | Acceptance Criteria | Est. Hours | Assignee |
|---------|-----------|-------------|-------------------|-----------|----------|
| NAV-1.1 | Update sidebar navigation labels | Update sidebar component to show "Health & Sync" (for /manage) and "Collections" (for /collection) with icon changes | 1. Sidebar reflects new labels<br>2. Icons changed appropriately<br>3. Hover states work<br>4. Mobile nav updated | 1 | ui-engineer-enhanced |
| NAV-1.2 | Add page headers with descriptions | Implement PageHeader components with purpose statements: Collection → "Browse & Discover", Manage → "Health & Sync" | 1. Headers render on both pages<br>2. Icons display correctly<br>3. Description text clear and concise<br>4. Responsive on mobile | 1 | frontend-developer |
| NAV-1.3 | Implement deep link + URL state support | **Existing**: `/manage` has `?type=` and `?artifact=`; `/collection` has `?tags=` only with collection selection in React state. **New**: Add `?artifact={id}` to `/collection` for deep linking; add `?collection={id}&group={id}` to move selection from React state to URL; add `?tab=` for modal tab deep linking on both pages | 1. `/collection?artifact={id}` opens modal automatically<br>2. `/collection?collection={id}&group={id}` restores selection<br>3. `?tab=` opens specific modal tab on both pages<br>4. URL updates on modal open/tab change<br>5. Browser back button works<br>6. Bookmarkable links work<br>7. Collection selection migrates from local state to URL | 2.5 | frontend-developer |
| NAV-1.4 | Add cross-navigation buttons to UnifiedEntityModal | Add "Manage Artifact →" (from discovery) and "Collection Details →" (from operations) in modal headers | 1. Buttons appear in correct context<br>2. Navigation preserves artifact + collection context<br>3. Modal closes on navigation<br>4. No console errors on click | 1.5 | frontend-developer |
| NAV-1.5 | Create PageHeader component variant | Create reusable PageHeader component with title, description, icon, and optional action button slots | 1. Component accepts title, description, icon<br>2. Renders correctly on multiple pages<br>3. Accessible with semantic HTML<br>4. Responsive layout | 1 | ui-engineer-enhanced |

**Phase 1 Quality Gate**:
- [ ] Sidebar reflects new navigation labels
- [ ] Page headers display with correct descriptions
- [ ] Deep links (`?artifact={id}`) work on both pages
- [ ] Collection/group selection restores from URL (`?collection=...&group=...`)
- [ ] Modal cross-navigation buttons appear and function
- [ ] No accessibility violations in navigation elements

**Phase 1 Output Artifacts**:
- Updated `skillmeat/web/components/navigation.tsx`
- Updated `skillmeat/web/app/manage/page.tsx` (header added)
- Updated `skillmeat/web/app/collection/page.tsx` (header added)
- Updated `skillmeat/web/components/entity/unified-entity-modal.tsx` (cross-nav buttons)
- New `skillmeat/web/components/shared/page-header.tsx`

---

### Phase 2: Card Components (4-6 hours)

**Objective**: Create distinct card components that reflect each page's purpose and reduce cognitive load.

**Subagent Leads**: ui-engineer-enhanced, frontend-developer

| Task ID | Task Name | Description | Acceptance Criteria | Est. Hours | Assignee |
|---------|-----------|-------------|-------------------|-----------|----------|
| CARD-2.1 | Create ArtifactBrowseCard component | Discovery-focused card: type icon, name, author, description (truncated), tags, tools, score badge, quick actions menu; **"Deployed" badge with project count when applicable** (no sync/drift indicators - those belong on /manage) | 1. All props accepted and rendered<br>2. Description truncates to 2-3 lines<br>3. Quick actions menu functional<br>4. Hover/focus states work<br>5. "Deployed (N)" badge shown when artifact has deployments | 2 | ui-engineer-enhanced |
| CARD-2.2 | Create ArtifactOperationsCard component | Operations-focused card: checkbox, type icon, name, version arrows, deployments, badges (drift/update), sync time, action buttons | 1. Checkbox selection works<br>2. Status badges display correctly<br>3. Deployment badges stack properly<br>4. Health indicator colored correctly<br>5. All action buttons functional | 2 | ui-engineer-enhanced |
| CARD-2.3 | Create shared status utility components | StatusBadge, HealthIndicator, DeploymentBadgeStack components with proper styling and tooltips. **DeploymentBadgeStack behavior**: hover overflow badge shows tooltip with full project list; click overflow badge opens modal on deployments tab | 1. StatusBadge renders all states<br>2. HealthIndicator shows correct health<br>3. DeploymentBadgeStack shows overflow with hover tooltip<br>4. DeploymentBadgeStack overflow click opens deployments tab<br>5. All tooltips functional<br>6. Accessible labels present | 1.5 | ui-engineer-enhanced |
| CARD-2.4 | Integrate ArtifactBrowseCard into collection page | Replace existing card rendering with ArtifactBrowseCard; update prop passing and event handlers | 1. Cards render on collection page<br>2. Quick actions work<br>3. Click opens modal<br>4. No visual regressions<br>5. Performance maintained | 1 | frontend-developer |
| CARD-2.5 | Integrate ArtifactOperationsCard into manage page | Replace existing card rendering with ArtifactOperationsCard; integrate bulk selection, action handlers | 1. Cards render on manage page<br>2. Checkboxes functional<br>3. Action buttons work<br>4. Bulk selection affects button state<br>5. No visual regressions | 1 | frontend-developer |

**Phase 2 Quality Gate**:
- [ ] ArtifactBrowseCard shows "Deployed (N)" badge when applicable; no sync/drift indicators
- [ ] ArtifactOperationsCard shows health and deployment status
- [ ] Shared utilities (StatusBadge, HealthIndicator, DeploymentBadgeStack) exported and working
- [ ] Both cards integrate into pages with no console errors
- [ ] Quick actions on browse card and operation buttons on operations card functional

**Phase 2 Output Artifacts**:
- New `skillmeat/web/components/collection/artifact-browse-card.tsx`
- New `skillmeat/web/components/manage/artifact-operations-card.tsx`
- New `skillmeat/web/components/shared/status-badge.tsx`
- New `skillmeat/web/components/shared/health-indicator.tsx`
- New `skillmeat/web/components/shared/deployment-badge-stack.tsx`
- Updated `skillmeat/web/app/collection/page.tsx` (card integration)
- Updated `skillmeat/web/app/manage/page.tsx` (card integration)

---

### Phase 3: Modal Separation (7-9 hours)

**Objective**: Create purpose-specific modals that reduce feature confusion and improve task completion flows.

**Subagent Leads**: ui-engineer-enhanced, frontend-developer

| Task ID | Task Name | Description | Acceptance Criteria | Est. Hours | Assignee |
|---------|-----------|-------------|-------------------|-----------|----------|
| MODAL-3.1 | Create ArtifactDetailsModal (collection-focused) | Discovery modal reusing existing content: Overview + Contents + Links + Collections + Sources + **history** (general artifact timeline); includes "Manage Artifact" button | 1. All tabs render<br>2. Overview + Contents present<br>3. Overview is default tab<br>4. Cross-navigation button works<br>5. Deploy action available<br>6. Add to Group action available<br>7. Upstream status summary shown (if any)<br>8. No project-level sync details | 2.5 | ui-engineer-enhanced |
| MODAL-3.2 | Create ArtifactOperationsModal (manage-focused) | Operations modal reusing existing content: Overview + Contents + Status + Sync Status + Deployments + **version-history** (version timeline with rollback options) | 1. All tabs render<br>2. Overview + Contents present<br>3. Status tab is default<br>4. Health indicators display<br>5. Sync actions work<br>6. Cross-navigation button present<br>7. Version history shows correctly | 2.5 | ui-engineer-enhanced |
| MODAL-3.3 | Extract shared modal components | Create reusable modal subcomponents: TabNavigation, ModalHeader, TabContent wrapper | 1. Components are reusable<br>2. No duplication between modals<br>3. Props accept customization<br>4. Accessibility preserved | 1 | frontend-developer |
| MODAL-3.4 | Update ModalCollectionsTab component | Add optional "View in Collection" and "Manage Artifact" actions per collection when in operations context | 1. Buttons appear in modal<br>2. Navigation works correctly<br>3. Collection list renders<br>4. Focus management correct | 1 | ui-engineer-enhanced |
| MODAL-3.5 | Implement cross-navigation state preservation | Ensure modal context preserved when navigating between pages. Implement `?returnTo=` query param: serialize origin URL with filters; show "Return to [origin]" button when returnTo present; handle browser back button correctly | 1. `returnTo` query param serialized on cross-navigation<br>2. Return button appears when `returnTo` is present<br>3. Return navigation restores filters and scroll position<br>4. Browser back button works correctly with returnTo<br>5. Modal reopens correctly after return<br>6. No data loss on navigation | 1.5 | frontend-developer |
| MODAL-3.6 | Integrate modals into respective pages | Wire ArtifactDetailsModal to collection page, ArtifactOperationsModal to manage page | 1. Correct modal opens on each page<br>2. Artifact data flows correctly<br>3. Modal close handlers work<br>4. No console errors<br>5. No visual regressions | 1 | frontend-developer |

**Phase 3 Quality Gate**:
- [ ] ArtifactDetailsModal shows discovery-focused content (overview/contents/links/collections/sources/history tab)
- [ ] ArtifactOperationsModal shows operations-focused content (status/sync/deployments/version-history tab)
- [ ] Cross-navigation buttons present in both modals with `returnTo` handling
- [ ] Return button appears when navigated from other page
- [ ] Modals integrate into pages without errors
- [ ] All tabs in both modals render and function correctly

**Phase 3 Output Artifacts**:
- New `skillmeat/web/components/collection/artifact-details-modal.tsx`
- New `skillmeat/web/components/manage/artifact-operations-modal.tsx`
- New `skillmeat/web/components/shared/modal-header.tsx`
- New `skillmeat/web/components/shared/cross-navigation-buttons.tsx`
- Updated `skillmeat/web/components/entity/modal-collections-tab.tsx`
- Updated `skillmeat/web/app/collection/page.tsx` (modal integration)
- Updated `skillmeat/web/app/manage/page.tsx` (modal integration)

---

### Phase 4: Filter Components (2-4 hours)

**Objective**: Implement purpose-specific filters that guide users toward relevant features on each page.

**Subagent Leads**: frontend-developer, ui-engineer-enhanced

| Task ID | Task Name | Description | Acceptance Criteria | Est. Hours | Assignee |
|---------|-----------|-------------|-------------------|-----------|----------|
| FILTER-4.1 | Create ManagePageFilters component | Project dropdown (prominent), Status filter (All, Needs Update, Has Drift, Deployed, Error), Type filter, search input, optional tag filter (retained) | 1. All filters render<br>2. Project dropdown populated<br>3. Status options functional<br>4. Type filtering works<br>5. Search input functional<br>6. Tag filter optional and non-blocking<br>7. Active filters display | 1.5 | frontend-developer |
| FILTER-4.2 | Enhance CollectionPageFilters with tools filter | Add Tools multi-select popover to existing filters (Collection, Group, Type, Tags, Search). **Prerequisite**: Tools API PRD must be complete before this plan begins | 1. Tools filter popover opens<br>2. Tools list populated from API<br>3. Multi-select works<br>4. Selected tools show in active filters<br>5. Clear all works<br>6. Responsive on mobile | 1 | frontend-developer |
| FILTER-4.3 | Add filter state to URL for bookmarkability | Serialize filter state to query params, restore on page load, update on filter change (including collection/group selection) | 1. URL updates on filter change<br>2. Filters restore from URL<br>3. Back button works<br>4. Bookmarkable URLs work<br>5. No race conditions<br>6. Deep links work with artifacts | 1.5 | frontend-developer |

**Phase 4 Quality Gate**:
- [ ] ManagePageFilters component renders with all filter types
- [ ] CollectionPageFilters has Tools filter working
- [ ] Filter state persists in URL
- [ ] Filters can be bookmarked and shared
- [ ] No console errors on filter changes

**Phase 4 Output Artifacts**:
- New `skillmeat/web/components/manage/manage-page-filters.tsx`
- Updated `skillmeat/web/components/collection/collection-page-filters.tsx`
- Updated `skillmeat/web/app/manage/page.tsx` (filter integration)
- Updated `skillmeat/web/app/collection/page.tsx` (filter URL state)

---

### Phase 5: Polish & Testing (2-4 hours)

**Objective**: Ensure production-ready quality with comprehensive testing, accessibility compliance, and documentation.

**Subagent Leads**: frontend-developer, web-accessibility-checker, testing specialist

| Task ID | Task Name | Description | Acceptance Criteria | Est. Hours | Assignee |
|---------|-----------|-------------|-------------------|-----------|----------|
| POLISH-5.1 | Add loading states and skeletons | Skeleton versions of ArtifactBrowseCard, ArtifactOperationsCard, modals for loading states | 1. Skeletons match card dimensions<br>2. Animate properly<br>3. Appear during data fetch<br>4. Smooth transition to content | 1 | ui-engineer-enhanced |
| POLISH-5.2 | Accessibility audit (ARIA, keyboard nav) | Audit all new components for WCAG AA compliance: ARIA labels, focus management, keyboard navigation | 1. All interactive elements keyboard accessible<br>2. ARIA labels present on icon buttons<br>3. Focus visible on all elements<br>4. Modal focus trapped<br>5. ESC closes modals<br>6. No color-only information | 1.5 | web-accessibility-checker |
| POLISH-5.3 | Unit tests for new components | Jest + React Testing Library tests for cards, modals, filters, utilities | 1. >80% statement coverage<br>2. Tests use accessible selectors<br>3. Mock data from Artifact type<br>4. All prop combinations tested<br>5. Error states tested | 1.5 | testing specialist |
| POLISH-5.4 | E2E tests for cross-navigation flows | Playwright tests for key user journeys: browse to manage, manage to collection, deep links | 1. Navigate collection → modal → manage works<br>2. Navigate manage → modal → collection works<br>3. Deep links open correct modals<br>4. URL state preserves<br>5. Mobile navigation works | 1 | testing specialist |
| POLISH-5.5 | Dark mode verification | Verify all new components work in dark mode with proper contrast | 1. All components readable in dark mode<br>2. No color contrast issues<br>3. Icons visible<br>4. Badge colors appropriate<br>5. Focus indicators visible | 0.5 | ui-engineer-enhanced |
| POLISH-5.6 | Performance verification | Measure and verify no >10% regression in page load times, measure modal open times | 1. Page load times stable<br>2. Modal open <200ms<br>3. Filter changes responsive<br>4. No memory leaks<br>5. Network requests batched | 0.5 | frontend-developer |

**Phase 5 Quality Gate**:
- [ ] All new components have loading/skeleton states
- [ ] WCAG AA compliance audit passed
- [ ] Unit test coverage >80%
- [ ] E2E tests cover critical flows
- [ ] Dark mode verified
- [ ] No performance regressions

**Phase 5 Output Artifacts**:
- Skeleton component utilities
- Test files for all new components (`__tests__/`)
- E2E test scenarios (`tests/`)
- Accessibility audit report
- Performance baseline metrics

---

## Component Specifications Reference

All component specifications defined in:

**Full Specification**: `/docs/design/ui-component-specs-page-refactor.md`

### Quick Reference: Key Components

| Component | Purpose | File Location | Dependencies |
|-----------|---------|--------------|--------------|
| ArtifactBrowseCard | Discovery-focused card | `collection/artifact-browse-card.tsx` | Artifact type, quick actions |
| ArtifactOperationsCard | Operations-focused card | `manage/artifact-operations-card.tsx` | Artifact type, health indicator |
| ArtifactDetailsModal | Collection page modal | `collection/artifact-details-modal.tsx` | Tabs, cross-nav buttons |
| ArtifactOperationsModal | Manage page modal | `manage/artifact-operations-modal.tsx` | Tabs, cross-nav buttons |
| StatusBadge | Status display utility | `shared/status-badge.tsx` | Badge component |
| HealthIndicator | Health status display | `shared/health-indicator.tsx` | Tooltip |
| DeploymentBadgeStack | Deployment display | `shared/deployment-badge-stack.tsx` | Badge component |
| ManagePageFilters | Operations filters | `manage/manage-page-filters.tsx` | Existing filter components |
| CollectionPageFilters | Discovery filters | `collection/collection-page-filters.tsx` | Tag filter, tools filter |

### Component Relationships

```
Page Layer
  ├── /manage (page.tsx)
  │   ├── ManagePageFilters
  │   ├── ArtifactOperationsCard (repeated)
  │   └── ArtifactOperationsModal
  │
  └── /collection (page.tsx)
      ├── CollectionPageFilters
      ├── ArtifactBrowseCard (repeated)
      └── ArtifactDetailsModal

Shared Utilities
  ├── StatusBadge
  ├── HealthIndicator
  ├── DeploymentBadgeStack
  └── CrossNavigationButtons
```

---

## Quality Gates & Validation

### Gate 0: Schema & Cache (End of Phase 0)

**Validator**: python-backend-engineer + data-layer-expert

```checklist
- [ ] ArtifactSummary schema includes deployments field
- [ ] Alembic migration runs without errors
- [ ] Cache population includes deployments data
- [ ] API response includes deployments array
- [ ] Frontend Artifact type updated
- [ ] Entity mapper handles deployments
- [ ] No type errors in frontend build
```

### Gate 1: Navigation & Deep Linking (End of Phase 1)

**Validator**: ui-engineer-enhanced + frontend-developer

```checklist
- [ ] Sidebar displays new labels
- [ ] Page headers render with descriptions
- [ ] ?artifact={id} opens correct modal on both pages
- [ ] Browser back button works after navigation
- [ ] Links are bookmarkable
- [ ] No console errors
```

### Gate 2: Card Components (End of Phase 2)

**Validator**: web-accessibility-checker + testing specialist

```checklist
- [ ] ArtifactBrowseCard shows "Deployed (N)" badge when applicable (no sync/drift)
- [ ] ArtifactOperationsCard shows health/sync/deployment data
- [ ] Cards integrate without visual regressions
- [ ] Quick actions functional
- [ ] Accessible keyboard navigation
- [ ] Hover/focus states correct
- [ ] No console errors
```

### Gate 3: Modal Separation (End of Phase 3)

**Validator**: frontend-developer + web-accessibility-checker

```checklist
- [ ] ArtifactDetailsModal focuses on discovery
- [ ] ArtifactOperationsModal focuses on operations
- [ ] Cross-navigation buttons functional
- [ ] All tabs render correctly
- [ ] Modal state preserved across navigations
- [ ] Focus management correct
- [ ] ESC key closes modals
- [ ] No console errors
```

### Gate 4: Filters & URL State (End of Phase 4)

**Validator**: frontend-developer

```checklist
- [ ] ManagePageFilters all functional
- [ ] CollectionPageFilters all functional
- [ ] Filters serialize to URL correctly
- [ ] Filters restore from URL on page load
- [ ] Deep links with filters work
- [ ] Collection/group selection persists via URL without breaking local state
- [ ] No race conditions
- [ ] No console errors
```

### Gate 5: Production Readiness (End of Phase 5)

**Validator**: web-accessibility-checker + testing specialist + DevOps

```checklist
- [ ] All components have loading states
- [ ] WCAG AA compliance verified
- [ ] Unit test coverage >80%
- [ ] E2E tests passing
- [ ] Dark mode verified
- [ ] Performance baseline established
- [ ] No accessibility violations
- [ ] Code reviewed and approved
- [ ] Ready for production deployment
```

---

## Risk Mitigation

### Risk 1: User Confusion During Transition

**Risk Level**: Medium

**Mitigation**:
- Clear page headers explaining purpose
- Cross-links guide users between pages
- Feature indicators show what's available
- In-app messaging on first visit

**Owner**: frontend-developer

---

### Risk 2: Modal Component Complexity

**Risk Level**: Medium

**Mitigation**:
- Extract shared components early (Phase 3.3)
- Keep tab structures similar but distinct
- Write comprehensive component tests
- Document tab content expectations

**Owner**: ui-engineer-enhanced

---

### Risk 3: Performance Regression

**Risk Level**: Low-Medium

**Mitigation**:
- Measure baseline before implementation
- Monitor bundle size growth
- Use React.memo for card components
- Lazy load modal tab content
- Establish performance gates

**Owner**: frontend-developer, react-performance-optimizer

---

### Risk 4: Cross-Navigation State Loss

**Risk Level**: Low

**Mitigation**:
- Implement comprehensive URL state management
- Test all navigation paths in E2E
- Handle browser back/forward
- Preserve scroll position where possible

**Owner**: frontend-developer

---

### Risk 5: Accessibility Gaps

**Risk Level**: Medium

**Mitigation**:
- Early accessibility audit (Phase 5.2)
- Use semantic HTML everywhere
- Test with screen readers
- Keyboard navigation testing
- Color contrast verification

**Owner**: web-accessibility-checker

---

## Timeline & Resource Planning

### Recommended Schedule

| Phase | Duration | Start | End | Primary Resources |
|-------|----------|-------|-----|------------------|
| Phase 0: Schema/Cache | 2-3h | Week 1, Day 1 | Week 1, Day 1 | python-backend-engineer (2h), data-layer-expert (0.5h), frontend-developer (0.5h) |
| Phase 1: Navigation | 5-7h | Week 1, Day 1 | Week 1, Day 2 | ui-engineer-enhanced (3h), frontend-developer (3.5h) |
| Phase 2: Cards | 4-6h | Week 1, Day 2 | Week 1, Day 4 | ui-engineer-enhanced (4h), frontend-developer (2h) |
| Phase 3: Modals | 7-9h | Week 2, Day 1 | Week 2, Day 3 | ui-engineer-enhanced (5h), frontend-developer (3.5h) |
| Phase 4: Filters | 2-4h | Week 2, Day 4 | Week 2, Day 5 | frontend-developer (3h), ui-engineer-enhanced (1h) |
| Phase 5: Polish | 2-4h | Week 3, Day 1 | Week 3, Day 2 | web-accessibility-checker (1.5h), testing specialist (2h), ui-engineer-enhanced (1h) |
| **Total** | **22-31h** | | | |

### Parallelization Opportunities

The following tasks can run in parallel:

- **Phase 2**: ArtifactBrowseCard and ArtifactOperationsCard development (separate subagents)
- **Phase 3**: ArtifactDetailsModal and ArtifactOperationsModal development (separate subagents)
- **Phase 5**: Accessibility audit, unit tests, and dark mode verification (separate subagents)

Estimated time with maximum parallelization: 15-20 hours wall-clock time

Note: Phase 0 must complete before Phase 2 (cards need deployments data), but can run in parallel with Phase 1.

### Resource Requirements

| Role | Hours | Phases | Critical Path |
|------|-------|--------|---------------|
| python-backend-engineer | 2-2.5h | 0 | Yes (enables cards) |
| data-layer-expert | 0.5h | 0 | No |
| ui-engineer-enhanced | 8-10h | 1, 2, 3, 5 | Yes (modals) |
| frontend-developer | 9-11h | 0, 1, 2, 3, 4, 5 | Yes (integration) |
| web-accessibility-checker | 1.5-2h | 5 | No |
| testing specialist | 2-3h | 5 | No |

---

## Success Metrics & Monitoring

### Post-Launch Metrics (Track for 1-2 Weeks)

| Metric | Target | Measurement | Tool |
|--------|--------|-------------|------|
| Page load time regression | <10% | Page load timing | Browser DevTools, Sentry |
| Modal open time | <200ms | Navigation timing | Custom instrumentation |
| Error rate | <0.5% | JavaScript errors | Sentry |
| User task completion | >85% | Usability testing | Manual testing |
| Accessibility violations | 0 | Automated scan | axe DevTools |

### Documentation Requirements

- [ ] Component stories in Storybook (if applicable)
- [ ] Architecture decision in ADR format
- [ ] User-facing changelog entry
- [ ] Developer guide for extending page-specific components
- [ ] Test coverage documentation

---

## Related Documentation

### Source Documents
- [Architecture Analysis Report](/docs/project_plans/reports/manage-collection-page-architecture-analysis.md)
- [UI Component Specifications](/docs/design/ui-component-specs-page-refactor.md)
- [Tools API Support PRD](/docs/project_plans/PRDs/tools-api-support-v1.md)

### Reference Documentation
- [MeatyPrompts Component Patterns](/.claude/context/key-context/component-patterns.md)
- [Next.js Patterns](/.claude/context/key-context/nextjs-patterns.md)
- [Testing Patterns](/.claude/context/key-context/testing-patterns.md)
- [Web Rules - Components](/.claude/rules/web/components.md)
- [Web Rules - Pages](/.claude/rules/web/pages.md)
- [Web Rules - Testing](/.claude/rules/web/testing.md)

### Existing Code References

**Pages**:
- `skillmeat/web/app/manage/page.tsx` (296 lines)
- `skillmeat/web/app/collection/page.tsx` (748 lines)

**Existing Components**:
- `skillmeat/web/components/entity/unified-entity-modal.tsx` (650+ lines) - To be split
- `skillmeat/web/components/navigation.tsx` (191 lines) - To be updated
- `skillmeat/web/components/collection/artifact-grid.tsx` - Reference for existing card usage
- `skillmeat/web/components/shared/unified-card.tsx` - Existing card to be replaced

**Hooks**:
- `skillmeat/web/hooks/useArtifacts.ts` (543 lines) - Data fetching
- `skillmeat/web/hooks/use-collections.ts` (463 lines) - Collection data
- `skillmeat/web/hooks/useEntityLifecycle.tsx` (791 lines) - Artifact management

**API Endpoints**:
- `GET /api/v1/artifacts` - Manage page endpoint
- `GET /api/v1/user-collections/{id}/artifacts` - Collection page endpoint

---

## Appendix: Implementation Checklist

### Pre-Implementation
- [ ] Review component specifications document thoroughly
- [ ] Create branch for feature development
- [ ] Set up local testing environment

### Phase 0: Schema & Cache
- [ ] Add deployments to ArtifactSummary schema
- [ ] Create Alembic migration for deployments_json
- [ ] Update cache population to include deployments
- [ ] Update API responses to emit deployments
- [ ] Update frontend Artifact type and mapper
- [ ] Gate 0: Schema validation

### Phase 1: Navigation
- [ ] Update sidebar navigation
- [ ] Add page headers
- [ ] Implement deep links
- [ ] Add cross-navigation buttons
- [ ] Gate 1: Navigation validation

### Phase 2: Cards
- [ ] Create ArtifactBrowseCard
- [ ] Create ArtifactOperationsCard
- [ ] Create shared utilities
- [ ] Integrate into pages
- [ ] Gate 2: Card validation

### Phase 3: Modals
- [ ] Create ArtifactDetailsModal
- [ ] Create ArtifactOperationsModal
- [ ] Extract shared components
- [ ] Implement cross-navigation
- [ ] Integrate into pages
- [ ] Gate 3: Modal validation

### Phase 4: Filters
- [ ] Create ManagePageFilters
- [ ] Enhance CollectionPageFilters
- [ ] Add URL state persistence
- [ ] Gate 4: Filter validation

### Phase 5: Polish
- [ ] Add loading states
- [ ] Accessibility audit
- [ ] Unit tests
- [ ] E2E tests
- [ ] Dark mode verification
- [ ] Performance verification
- [ ] Gate 5: Production readiness

### Pre-Launch
- [ ] Code review by senior-code-reviewer
- [ ] Architecture review by lead-architect
- [ ] QA testing on staging
- [ ] Performance baseline established
- [ ] Documentation complete

---

**Document Version**: 1.1
**Status**: Ready for Implementation
**Approved By**: Architecture Review (2026-02-01)
**Last Updated**: 2026-02-02
**Review Notes**: Codex review incorporated; clarifications added for card indicators, tab naming, URL state scope, and cross-navigation returnTo handling
