---
type: context
prd: collections-groups-ux-enhancement
title: Collections & Groups UX Enhancement - Development Context
status: active
created: '2026-01-19'
updated: '2026-01-19'
critical_notes_count: 0
implementation_decisions_count: 0
active_gotchas_count: 0
agent_contributors: []
agents: []
schema_version: 2
doc_type: context
feature_slug: collections-groups-ux-enhancement
---

# Collections & Groups UX Enhancement - Development Context

**Status**: Active Development
**Created**: 2026-01-19
**Last Updated**: 2026-01-19

> **Purpose**: This is a shared worknotes file for all AI agents working on the Collections & Groups UX Enhancement PRD. Add brief observations, decisions, gotchas, and implementation notes that future agents should know. Think of this as a sticky-note pad for the development team.

---

## Quick Reference

**PRD**: `docs/project_plans/PRDs/harden-polish/collections-groups-ux-enhancement-v1.md`
**Implementation Plan**: `docs/project_plans/implementation_plans/harden-polish/collections-groups-ux-enhancement-v1.md`

**Progress Tracking**:
- Phase 1: `.claude/progress/collections-groups-ux-enhancement/phase-1-progress.md`
- Phase 2: `.claude/progress/collections-groups-ux-enhancement/phase-2-progress.md`
- Phase 3: `.claude/progress/collections-groups-ux-enhancement/phase-3-progress.md`
- Phase 4: `.claude/progress/collections-groups-ux-enhancement/phase-4-progress.md`
- Phase 5: `.claude/progress/collections-groups-ux-enhancement/phase-5-progress.md`

**Phases**:
1. Data Layer & Hooks (8 SP) - Foundation for efficient group data fetching
2. Collection Badges on Cards (10 SP) - Visual collection membership indicators
3. Group Badges + Modal Enhancement (9 SP) - Group membership display
4. Groups Sidebar Page (12 SP) - Dedicated /groups navigation
5. Group Filter Integration (8 SP) - Filter artifacts by group

**Total Effort**: 47 story points (~3-4 weeks)

---

## Key Architectural Decisions

### 2026-01-19 - Planning - Hook-First Data Access Pattern

**Decision**: All group data access goes through TanStack Query custom hooks (`useGroups`, `useArtifactGroups`). No direct API calls from components.

**Rationale**: Ensures consistent caching strategy, centralized error handling, and automatic request deduplication across all consumers.

**Location**: Phase 1 hooks implementation (`hooks/use-groups.ts`, `hooks/use-artifact-groups.ts`)

**Impact**: All subsequent phases (2-5) depend on Phase 1 hooks. Components simply call hooks and receive cached data.

---

### 2026-01-19 - Planning - Conditional Badge Rendering Strategy

**Decision**: Collection badges shown ONLY in "All Collections" view. Group badges shown ONLY in specific collection context. Never both simultaneously.

**Rationale**: Reduces visual clutter, provides contextually relevant information, avoids badge overflow on cards.

**Location**: `components/shared/unified-card.tsx` (enhanced in Phases 2-3)

**Impact**: Requires `useCollectionContext()` hook to detect current view context. Badge components check `isSpecificCollection` before rendering.

---

### 2026-01-19 - Planning - No Backend Changes Required

**Decision**: Leverage existing Groups API endpoints (`GET /groups`, `GET /groups/{id}`). No new backend development.

**Rationale**: Groups functionality already exists in backend. This PRD focuses on frontend UX improvements only.

**Location**: All phases use existing API contract

**Impact**: Reduces risk, shortens timeline, enables parallel development without backend coordination.

---

### 2026-01-19 - Planning - Consistent Badge Styling with Color Differentiation

**Decision**: Collection badges use `variant="secondary"` (gray/muted), Group badges use `variant="outline"` (border-only).

**Rationale**: Visual distinction helps users understand badge type at a glance. Both use shadcn Badge component for consistency.

**Location**: `components/shared/collection-badge-stack.tsx`, `components/shared/group-badge-row.tsx`

**Impact**: Design review required to verify color contrast meets WCAG 2.1 AA (4.5:1 ratio).

---

## Critical Gotchas & Observations

### 2026-01-19 - Planning - N+1 Query Risk with Badge Rendering

**What**: If `useArtifactGroups` is called for every card in a grid (100+ cards), we risk 100+ API calls.

**Why**: Each card independently fetches its group membership, potentially causing network congestion.

**Solution**: TanStack Query deduplication handles same-key requests. Monitor network tab during Phase 3 development. Consider batching strategy if performance degrades.

**Affects**: Phase 3 (GroupBadgeRow component)

---

### 2026-01-19 - Planning - Next.js 15 Params Must Be Awaited

**What**: Next.js 15 changed `searchParams` to be a Promise. Must use `await searchParams` in server components.

**Why**: Breaking change in Next.js 15 App Router.

**Solution**: Always await params in server components:
```typescript
export default async function Page({ searchParams }: { searchParams: Promise<{...}> }) {
  const params = await searchParams;
}
```

**Affects**: Phase 4 (`app/groups/page.tsx`)

---

### 2026-01-19 - Planning - Modal Placeholder Removal in ModalCollectionsTab

**What**: Lines 197-198 in `components/entity/modal-collections-tab.tsx` are currently commented placeholders for groups display.

**Why**: Groups feature was planned but not implemented in UI.

**Solution**: Verify exact location before replacing in Phase 3. Placeholder may have been moved or removed in recent changes.

**Affects**: Phase 3 (ModalCollectionsTab enhancement)

---

## Integration Notes

### 2026-01-19 - Planning - Phase 1 → Phases 2-5 Hook Dependency

**From**: Phase 1 (Data Layer & Hooks)
**To**: Phases 2-5 (All badge and filter components)
**Method**: Import hooks from `@/hooks` barrel export
**Notes**: Phase 1 must be 100% complete with ≥80% test coverage before starting Phases 2-3. Phases 2-3 can run in parallel after Phase 1.

---

### 2026-01-19 - Planning - Badge Components → UnifiedCard Integration

**From**: CollectionBadgeStack, GroupBadgeRow components
**To**: UnifiedCard component
**Method**: Conditional render sections with `useCollectionContext()` check
**Notes**: UnifiedCard already complex (200+ lines). Keep badge logic in separate components to maintain readability.

---

### 2026-01-19 - Planning - Filters → Artifact Query Hooks

**From**: GroupFilterSelect component (Phase 5)
**To**: useInfiniteCollectionArtifacts hook
**Method**: Pass `filters.groupId` to hook; hook includes in API query params
**Notes**: Existing `ArtifactFilters` interface needs `groupId?: string` field added. Verify backend supports `group_id` filter parameter.

---

## Performance Notes

### 2026-01-19 - Planning - Target Performance Benchmarks

**Groups fetch latency**: ≤200ms (Phase 1)
- TanStack Query caching with 5min stale time reduces repeat fetches
- Profile with Chrome DevTools Network tab

**Card render with badges**: ≤50ms per card (Phases 2-3)
- Use React DevTools Profiler to measure
- Lazy-render badges only if `entity.collections` or `entity.groups` exists

**/groups page load**: ≤500ms (Phase 4)
- Lighthouse audit before rollout
- Infinite scroll pagination reduces initial load

**Modal Collections tab load**: ≤300ms (Phase 3)
- Groups section loads with collection data
- Use skeleton loaders for perceived performance

---

## Agent Handoff Notes

_Agents will add notes here as phases complete_

---

## Related Files

**Progress Tracking**:
- `.claude/progress/collections-groups-ux-enhancement/phase-1-progress.md`
- `.claude/progress/collections-groups-ux-enhancement/phase-2-progress.md`
- `.claude/progress/collections-groups-ux-enhancement/phase-3-progress.md`
- `.claude/progress/collections-groups-ux-enhancement/phase-4-progress.md`
- `.claude/progress/collections-groups-ux-enhancement/phase-5-progress.md`

**Implementation Plan**:
- `docs/project_plans/implementation_plans/harden-polish/collections-groups-ux-enhancement-v1.md`

**PRD**:
- `docs/project_plans/PRDs/harden-polish/collections-groups-ux-enhancement-v1.md`

**Design Specs**: _(to be added)_

**Related Components**:
- `skillmeat/web/components/shared/unified-card.tsx`
- `skillmeat/web/components/collection/filters.tsx`
- `skillmeat/web/components/entity/modal-collections-tab.tsx`
- `skillmeat/web/components/navigation.tsx`

**Related Hooks**:
- `skillmeat/web/hooks/use-collections.ts` (existing pattern reference)
- `skillmeat/web/hooks/use-artifacts.ts` (existing pattern reference)
- `skillmeat/web/hooks/use-groups.ts` (to be enhanced in Phase 1)
- `skillmeat/web/hooks/use-artifact-groups.ts` (to be created in Phase 1)

**Types**:
- `skillmeat/web/types/groups.ts` (verify API contract)
- `skillmeat/web/types/artifact.ts` (verify collections, groups arrays)

**API Endpoints** (existing, no changes):
- `GET /groups` - List groups in collection
- `GET /groups/{id}` - Get group details
- `GET /artifacts?group_id={id}` - Filter artifacts by group (verify backend support)

---

## Development Guidelines

### Testing Requirements

**Every phase must have**:
- ≥80% unit test coverage (statements, branches, lines)
- Integration tests for multi-component workflows
- Accessibility tests (axe audit, WCAG 2.1 AA compliance)

**Phase-specific**:
- Phase 1: Hook tests with mock API responses, error handling
- Phases 2-3: Component snapshot tests, badge rendering tests
- Phase 4: E2E happy path test (navigate, select group, view artifacts)
- Phase 5: Filter application tests, URL state persistence

### Code Quality Standards

- TypeScript strict mode, no `any` types
- ESLint zero errors, zero warnings
- shadcn components only (no custom styling)
- JSDoc comments on all exported functions
- Named exports only (no default exports)

### Accessibility Checklist

- [ ] All badges have `aria-label` attributes
- [ ] Keyboard navigation works for all interactive elements
- [ ] Color contrast ≥4.5:1 (WCAG AA)
- [ ] Screen reader tested (NVDA/JAWS)
- [ ] Focus indicators visible on all focusable elements

### Performance Checklist

- [ ] Card render ≤50ms per card
- [ ] Page load latency ≤200ms added from baseline
- [ ] TanStack Query cache hit rate ≥80% for repeated fetches
- [ ] No unnecessary re-renders (React DevTools Profiler)

---

## Rollout Plan

**Staged Rollout**:
1. **Day 1**: 10% of users via feature flag
2. **Day 2-3**: 50% of users
3. **Day 4-7**: 100% rollout

**Monitoring** (first 2 weeks):
- GA events: `collection_badge_viewed`, `group_badge_viewed`, `groups_page_visited`, `group_filter_applied`
- Error tracking (Sentry): Failed group fetches, badge render errors
- Performance metrics (Web Vitals): Page load latency, card render time

**Rollback Criteria**:
- Error rate >0.5%
- Page load latency >500ms (>200ms increase from baseline)
- WCAG Level A failures
- Critical bugs affecting >5% of users

---

## Template Examples

<details>
<summary>Example: Implementation Decision</summary>

### 2026-01-XX - [agent-name] - [Decision Title]

**Decision**: [What was decided in 1-2 sentences]

**Rationale**: [Why in 1-2 sentences]

**Location**: `path/to/file.ext:line`

**Impact**: [What this affects]

</details>

<details>
<summary>Example: Gotcha/Observation</summary>

### 2026-01-XX - [agent-name] - [Gotcha Title]

**What**: [What happened in 1-2 sentences]

**Why**: [Root cause in 1 sentence]

**Solution**: [How to avoid/fix in 1-2 sentences]

**Affects**: [Which files/components/phases]

</details>

<details>
<summary>Example: Agent Handoff</summary>

### 2026-01-XX - [agent-name] → [next-agent]

**Completed**: [What was just finished]

**Next**: [What should be done next]

**Watch Out For**: [Any gotchas or warnings]

</details>
