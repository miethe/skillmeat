---
title: "Execution Summary: /manage vs /collection Page Refactor"
description: "Quick reference guide for executing the page refactor implementation plan"
status: active
type: execution-guide
created: 2026-02-01
---

# Execution Summary: Page Refactor

**Full Plan**: `manage-collection-page-refactor-v1.md`

---

## Quick Stats

| Metric | Value |
|--------|-------|
| Total Effort | 18-26 hours |
| Phases | 5 |
| New Components | 10 |
| Updated Components | 5 |
| Complexity | Medium |
| Track | Standard (Haiku + Sonnet) |

---

## Phase Roadmap

### Phase 1: Navigation (4-6h)
Update sidebar labels, add page headers, implement `?artifact={id}` deep links, add modal cross-nav buttons.

**Lead**: ui-engineer-enhanced, frontend-developer
**Deliverables**: PageHeader component, updated navigation, deep link support

### Phase 2: Cards (4-6h)
Create ArtifactBrowseCard (discovery) and ArtifactOperationsCard (operations) with shared utilities.

**Lead**: ui-engineer-enhanced, frontend-developer
**Deliverables**: Two distinct card components, status/health/deployment utilities, page integration

### Phase 3: Modals (6-8h)
Create ArtifactDetailsModal (collection-focused) and ArtifactOperationsModal (manage-focused) with cross-navigation.

**Lead**: ui-engineer-enhanced, frontend-developer
**Deliverables**: Two purpose-specific modals, modal subcomponents, page integration

### Phase 4: Filters (2-4h)
Create ManagePageFilters, enhance CollectionPageFilters with tools filter, add URL state persistence.

**Lead**: frontend-developer
**Deliverables**: Filter components, URL-based state management, bookmarkable filters

### Phase 5: Polish (2-4h)
Loading states, accessibility audit, unit tests, E2E tests, dark mode, performance verification.

**Lead**: web-accessibility-checker, testing specialist, frontend-developer
**Deliverables**: Production-ready components, test coverage >80%, WCAG AA compliance

---

## Component Structure

### New Components Created

```
skillmeat/web/components/
├── collection/
│   ├── artifact-browse-card.tsx          (discovery card)
│   └── artifact-details-modal.tsx        (discovery modal)
├── manage/
│   ├── artifact-operations-card.tsx      (operations card)
│   ├── artifact-operations-modal.tsx     (operations modal)
│   └── manage-page-filters.tsx           (operations filters)
└── shared/
    ├── page-header.tsx                   (page title component)
    ├── status-badge.tsx                  (status display utility)
    ├── health-indicator.tsx              (health status display)
    ├── deployment-badge-stack.tsx        (deployment display)
    ├── cross-navigation-buttons.tsx      (modal navigation)
    └── modal-header.tsx                  (shared modal header)
```

### Updated Components

- `skillmeat/web/components/navigation.tsx` - New sidebar labels
- `skillmeat/web/components/entity/unified-entity-modal.tsx` - Add cross-nav buttons
- `skillmeat/web/components/collection/collection-page-filters.tsx` - Add tools filter
- `skillmeat/web/app/manage/page.tsx` - Headers, filters, new cards
- `skillmeat/web/app/collection/page.tsx` - Headers, filters, new cards

---

## Key Design Decisions

### Page Purposes (Clear Mental Models)

**`/collection` → Browse & Discover**
- What artifacts do I have?
- What do they do?
- How do I organize them?
- Features: Full metadata, tags, tools, groups, descriptions

**`/manage` → Operations Dashboard**
- What needs attention?
- Is it up to date?
- Where is it deployed?
- Features: Health status, sync actions, deployments, version tracking

### Modal Purposes (Distinct Content)

**ArtifactDetailsModal** (Collection page):
- Overview tab (default): Full description, metadata, author, license, tags, upstream summary
- Contents tab: File tree + content pane (existing data)
- Links tab: Linked artifacts + unlinked references
- Collections tab: Membership + group actions
- Sources tab: Repository/source details
- History tab: General artifact history
- Action: "Manage Artifact" button in header

**ArtifactOperationsModal** (Manage page):
- Overview tab: Metadata + operational highlights
- Contents tab: File tree + content pane (existing data)
- Status tab (default): Detailed operational status
- Sync Status tab: Drift + sync actions (existing data)
- Deployments tab: Where deployed, deployment actions
- Version History tab: Timeline of versions, rollback options
- Action: "Collection Details" button in header

**Dependency Note**: Tools badges and the tools filter rely on Tools API support
(`/docs/project_plans/PRDs/tools-api-support-v1.md`).

### Cross-Navigation Patterns

```
/collection → Click card → ArtifactDetailsModal
           ↓ "Manage Artifact" button
         /manage → ArtifactOperationsModal

/manage → Click card → ArtifactOperationsModal
        ↓ "Collection Details" button
      /collection → ArtifactDetailsModal
```

---

## Critical Success Factors

| Factor | How to Verify |
|--------|---------------|
| **Page purpose clarity** | Users can explain difference between pages >85% |
| **Cross-navigation** | Users successfully switch contexts without confusion |
| **Performance** | No >10% regression in load times |
| **Accessibility** | WCAG AA compliance on all new components |
| **Code quality** | Unit test coverage >80%, E2E tests passing |

---

## Testing Strategy

### Unit Tests (Phase 5.3)
- Component render tests (all props)
- Event handler tests
- State management tests
- Accessible selectors (RTL queries)

**Coverage Target**: >80% statements

### E2E Tests (Phase 5.4)
- Navigate collection → modal → manage
- Navigate manage → modal → collection
- Deep links work (`?artifact={id}`)
- Filter state preserved in URL
- Dark mode works

**Tools**: Playwright, standard Next.js patterns

### Accessibility Tests (Phase 5.2)
- ARIA labels on all icon buttons
- Focus management in modals
- Keyboard navigation (Tab, Enter, Escape)
- Color contrast (WCAG AA minimum)
- Screen reader annotations

**Tool**: axe DevTools

---

## Subagent Assignments

| Phase | Primary | Secondary | Hours |
|-------|---------|-----------|-------|
| 1 | ui-engineer-enhanced | frontend-developer | 4-6 |
| 2 | ui-engineer-enhanced | frontend-developer | 4-6 |
| 3 | ui-engineer-enhanced | frontend-developer | 6-8 |
| 4 | frontend-developer | ui-engineer-enhanced | 2-4 |
| 5 | web-accessibility-checker, testing specialist | frontend-developer | 2-4 |

**Parallel Opportunities**:
- Phase 2: Two different card components (parallel development)
- Phase 3: Two different modals (parallel development)
- Phase 5: Accessibility, tests, dark mode (parallel execution)

---

## Risk Mitigation Quick Guide

| Risk | Mitigation | Owner |
|------|-----------|-------|
| User confusion | Clear headers, cross-links, messaging | frontend-developer |
| Modal complexity | Extract shared components early | ui-engineer-enhanced |
| Performance regression | Baseline measurements, monitoring | react-performance-optimizer |
| State loss on navigation | Comprehensive URL state, E2E testing | frontend-developer |
| Accessibility gaps | Early audit, semantic HTML, keyboard nav | web-accessibility-checker |

---

## Go/No-Go Gate Checklist

### Before Phase 1 Start
- [ ] Feature flag configured
- [ ] Branch created
- [ ] Components specs reviewed
- [ ] Team aligned on design

### After Phase 1 (Gate 1: Navigation)
- [ ] Sidebar shows new labels
- [ ] Deep links work (`?artifact={id}`)
- [ ] Cross-nav buttons appear
- [ ] No console errors

### After Phase 2 (Gate 2: Cards)
- [ ] ArtifactBrowseCard renders without drift indicators
- [ ] ArtifactOperationsCard shows health/sync/deployment
- [ ] Cards integrate on pages
- [ ] No visual regressions

### After Phase 3 (Gate 3: Modals)
- [ ] ArtifactDetailsModal focuses on discovery
- [ ] ArtifactOperationsModal focuses on operations
- [ ] Cross-navigation functional
- [ ] Modal close works correctly

### After Phase 4 (Gate 4: Filters)
- [ ] All filters functional
- [ ] URL state persistence working
- [ ] Bookmarkable filter URLs work

### After Phase 5 (Gate 5: Production Ready)
- [ ] WCAG AA compliance verified
- [ ] Unit test coverage >80%
- [ ] E2E tests passing
- [ ] Dark mode verified
- [ ] No performance regressions
- [ ] Code reviewed and approved
- [ ] Ready for production deployment

---

## Quick Reference: Files to Create/Update

### Create (10 files)
1. `components/collection/artifact-browse-card.tsx`
2. `components/collection/artifact-details-modal.tsx`
3. `components/manage/artifact-operations-card.tsx`
4. `components/manage/artifact-operations-modal.tsx`
5. `components/manage/manage-page-filters.tsx`
6. `components/shared/page-header.tsx`
7. `components/shared/status-badge.tsx`
8. `components/shared/health-indicator.tsx`
9. `components/shared/deployment-badge-stack.tsx`
10. `components/shared/cross-navigation-buttons.tsx`

### Update (5 files)
1. `components/navigation.tsx`
2. `components/entity/unified-entity-modal.tsx`
3. `components/collection/collection-page-filters.tsx`
4. `app/manage/page.tsx`
5. `app/collection/page.tsx`

### Test Files (Phase 5)
- `__tests__/components/collection/artifact-browse-card.test.tsx`
- `__tests__/components/manage/artifact-operations-card.test.tsx`
- `__tests__/components/collection/artifact-details-modal.test.tsx`
- `__tests__/components/manage/artifact-operations-modal.test.tsx`
- `tests/e2e/page-navigation.spec.ts`
- And others for filters, utilities

---

## Timeline Estimate

| Phase | Days | Start | End |
|-------|------|-------|-----|
| 1 | 1-2 | Day 1 | Day 2 |
| 2 | 1-2 | Day 2 | Day 4 |
| 3 | 2 | Day 4 | Day 6 |
| 4 | 1 | Day 6 | Day 7 |
| 5 | 1-2 | Day 7 | Day 8 |
| **Total** | **7-9 days** | | |

With maximum parallelization: 5-7 days wall-clock time

---

## Success Metrics (Track Post-Launch)

Monitor for 1-2 weeks after release:

| Metric | Target | Method |
|--------|--------|--------|
| Page load time | <10% regression | Browser DevTools, Sentry |
| Modal open time | <200ms | Custom instrumentation |
| Error rate | <0.5% | Sentry |
| Task completion | >85% | Usability testing |
| A11y violations | 0 | axe DevTools |

---

## Approval & Sign-Off

- **Architecture Review**: Approved (2026-02-01)
- **Design Review**: See component specs document
- **PM Review**: Pending
- **QA Review**: Pending
- **Launch Authorization**: Pending

---

**This is a high-level execution summary. Refer to `manage-collection-page-refactor-v1.md` for detailed task specifications, acceptance criteria, and risk mitigation strategies.**
