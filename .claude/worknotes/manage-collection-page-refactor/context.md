# Context: Manage/Collection Page Architecture Refactor

**PRD**: manage-collection-page-refactor-v1
**Status**: Approved
**Complexity**: Medium (18-26 hours)
**Created**: 2026-02-01

## PRD Summary

Separate and clarify the purpose of `/manage` (Operations Dashboard) and `/collection` (Browse & Discover) pages with distinct card components, modals, and cross-navigation.

**Design Decision**: Option C - Distinct Purpose Pages with Cross-Links

**Key Principle**: Each page uses its optimal backend system while maintaining clear semantic separation:
- `/collection` = Browse & Discover (primary) - "What artifacts do I have?"
- `/manage` = Operations Dashboard (secondary) - "What needs attention?"

## Cross-References

| Document | Location | Purpose |
|----------|----------|---------|
| Implementation Plan | `/docs/project_plans/implementation_plans/features/manage-collection-page-refactor-v1.md` | Full task breakdown |
| UI Component Specs | `/docs/design/ui-component-specs-page-refactor.md` | Component specifications |
| Architecture Analysis | `/docs/project_plans/reports/manage-collection-page-architecture-analysis.md` | Decision rationale |
| Component Patterns | `/.claude/context/key-context/component-patterns.md` | React/shadcn patterns |
| Next.js Patterns | `/.claude/context/key-context/nextjs-patterns.md` | App Router patterns |
| Testing Patterns | `/.claude/context/key-context/testing-patterns.md` | Jest/Playwright templates |

## Technical Constraints

### Must Use
- shadcn/ui primitives (do not modify `ui/` files)
- Tailwind CSS classes (no inline styles)
- Named exports only
- `cn()` for conditional class merging
- Next.js 15 App Router (await params in dynamic routes)
- TanStack Query for client-side data fetching

### Performance Requirements
- No >10% regression in page load times
- Modal open time <200ms
- Filter changes responsive

### Accessibility Requirements
- WCAG AA compliance on all new components
- ARIA labels on icon buttons
- Focus management in modals (trapped focus, ESC to close)
- Keyboard navigation for all interactive elements
- No color-only information

## Key Patterns

### Component Relationships

```
Page Layer
  /manage (page.tsx)
    ManagePageFilters
    ArtifactOperationsCard (repeated)
    ArtifactOperationsModal

  /collection (page.tsx)
    CollectionPageFilters
    ArtifactBrowseCard (repeated)
    ArtifactDetailsModal

Shared Utilities
  StatusBadge
  HealthIndicator
  DeploymentBadgeStack
  CrossNavigationButtons
  PageHeader
```

### Files to Modify

**Pages**:
- `skillmeat/web/app/manage/page.tsx` (296 lines)
- `skillmeat/web/app/collection/page.tsx` (748 lines)

**Existing Components to Update**:
- `skillmeat/web/components/navigation.tsx` (191 lines) - Sidebar labels
- `skillmeat/web/components/entity/unified-entity-modal.tsx` (650+ lines) - Cross-nav buttons

**New Components to Create**:
- `skillmeat/web/components/shared/page-header.tsx`
- `skillmeat/web/components/collection/artifact-browse-card.tsx`
- `skillmeat/web/components/manage/artifact-operations-card.tsx`
- `skillmeat/web/components/shared/status-badge.tsx`
- `skillmeat/web/components/shared/health-indicator.tsx`
- `skillmeat/web/components/shared/deployment-badge-stack.tsx`
- `skillmeat/web/components/collection/artifact-details-modal.tsx`
- `skillmeat/web/components/manage/artifact-operations-modal.tsx`
- `skillmeat/web/components/manage/manage-page-filters.tsx`

### Hooks Reference
- `skillmeat/web/hooks/useArtifacts.ts` (543 lines) - Data fetching
- `skillmeat/web/hooks/use-collections.ts` (463 lines) - Collection data
- `skillmeat/web/hooks/useEntityLifecycle.tsx` (791 lines) - Artifact management

### API Endpoints
- `GET /api/v1/artifacts` - Manage page endpoint
- `GET /api/v1/user-collections/{id}/artifacts` - Collection page endpoint

## Feature Flag

```typescript
// .env.local
NEXT_PUBLIC_NEW_PAGE_UI=true  // Enable new UI
```

Rollout: Staging -> 10% canary -> 50% -> 100%

## Success Criteria

| Criterion | Target |
|-----------|--------|
| User understands page purpose | >85% task completion |
| Cross-navigation works | No user confusion |
| Load performance maintained | <10% regression |
| Accessibility compliant | WCAG AA |
| Code coverage | >80% on new components |

## Risk Mitigations

1. **User Confusion**: Clear page headers, cross-links, in-app messaging
2. **Modal Complexity**: Extract shared components early (Phase 3.3)
3. **Performance**: Baseline measurement, React.memo, lazy loading
4. **State Loss**: URL state management, E2E testing
5. **Accessibility**: Early audit, semantic HTML, screen reader testing

## Agent Assignments

| Role | Hours | Phases |
|------|-------|--------|
| ui-engineer-enhanced | 8-10h | 1, 2, 3, 5 |
| frontend-developer | 8-10h | 1, 2, 3, 4, 5 |
| web-accessibility-checker | 1.5-2h | 5 |
| testing specialist | 2-3h | 5 |
