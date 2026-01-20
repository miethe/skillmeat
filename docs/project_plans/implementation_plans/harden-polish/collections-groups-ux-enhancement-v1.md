# Implementation Plan: Collections & Groups UX Enhancement v1

**Status**: Ready for Implementation
**Created**: 2026-01-19
**Complexity**: Large (L) | **Estimated Effort**: 55 story points | **Timeline**: 4-5 weeks | **Priority**: High

**Related PRD**: `docs/project_plans/PRDs/harden-polish/collections-groups-ux-enhancement-v1.md`

---

## Executive Summary

This implementation plan transforms the Collections & Groups UX from a backend-only feature into a user-facing, discoverable component of SkillMeat's web interface. The enhancement spans five coordinated phases that progressively expose Groups functionality through visual indicators on cards, modal enhancements, dedicated navigation, and filtering capabilities.

### Key Outcomes

1. **Phase 0: API Contract Alignment & Backend Enhancements (8 SP)** — Add missing backend filters/endpoints needed for group membership and group filtering
2. **Phase 1: Data Layer & Hooks (8 SP)** — Establish efficient data fetching and caching for groups at the hook layer
3. **Phase 2: Collection Badges on Cards (10 SP)** — Expose collection membership visually in "All Collections" view
4. **Phase 3: Group Badges & Modal Enhancement (9 SP)** — Show group membership on cards and in modal Collections tab
5. **Phase 4: Groups Sidebar Page (12 SP)** — Create dedicated `/groups` page with group selector and artifact browsing
6. **Phase 5: Group Filter Integration (8 SP)** — Add Group filter dropdown to collection and manage pages

### Success Criteria

- All new code: TypeScript strict mode, ≥80% test coverage, WCAG 2.1 Level AA accessible
- Performance: ≤200ms added latency on /collection page load
- No breaking changes to existing components or APIs
- All acceptance criteria from PRD Section 9 met

---

## Architecture Overview

### MeatyPrompts Layer Alignment

This feature follows the MeatyPrompts architecture layering:

```
┌─────────────────────────────────────────┐
│ UI Layer (Components)                   │
│ - UnifiedCard, Filters, Modal, /groups  │
├─────────────────────────────────────────┤
│ Hook Layer (Data Access)                │
│ - useGroups, useArtifactGroups,         │
│   useGroupFilter                        │
├─────────────────────────────────────────┤
│ API Client Layer                        │
│ - fetchArtifactGroups, existing hooks   │
├─────────────────────────────────────────┤
│ Backend (No changes required)           │
│ - Groups API fully implemented          │
└─────────────────────────────────────────┘
```

### Key Decisions

1. **Hook-First Approach**: All data fetching via custom hooks with TanStack Query caching
2. **Backend Enhancements Required**: Add minimal backend filters/endpoints to support artifact→group membership and group filtering
3. **Conditional Rendering**: Collection badges shown only in "All Collections" view; Group badges only in specific collection context
4. **Consistent Design**: Reuse shadcn Badge components with distinct colors for collections vs. groups
5. **Graceful Degradation**: Missing group/collection data skips badge render; cards still display

### Verified API Contracts (as of 2026-01-20)

- `GET /api/v1/groups?collection_id=...` returns group list (no `artifact_id` filter yet)
- `GET /api/v1/groups/{group_id}` returns group metadata + artifact IDs/positions
- `GET /api/v1/user-collections/{collection_id}/artifacts` supports pagination + `artifact_type` filter only (no `group_id` filter yet)
- `GET /api/v1/groups/{group_id}/artifacts` is **not** implemented (front-end hook currently assumes it exists)

---

## Phase Overview & Dependencies

| Phase | Name | Story Points | Duration | Dependencies | Risk Level |
|-------|------|--------------|----------|--------------|-----------|
| 0 | API Contract Alignment & Backend Enhancements | 8 | 3-4 days | None | Medium |
| 1 | Data Layer & Hooks | 8 | 3-4 days | Phase 0 | Low |
| 2 | Collection Badges on Cards | 10 | 4-5 days | Phase 1 | Medium |
| 3 | Group Badges & Modal | 9 | 4-5 days | Phase 1 | Medium |
| 4 | Groups Sidebar Page | 12 | 5-6 days | Phases 0-3 | Medium-High |
| 5 | Group Filter Integration | 8 | 3-4 days | Phases 0-4 | Medium |
| **Total** | | **55** | **4-5 weeks** | | |

### Sequential Path

```
Phase 0 (API Contract Alignment)
    ↓
Phase 1 (Hooks)
    ↓
Phase 2 (Collection Badges) + Phase 3 (Group Badges) [parallel]
    ↓
Phase 4 (Groups Page)
    ↓
Phase 5 (Group Filter)
    ↓
Integration Testing & Rollout
```

---

## Phase 0: API Contract Alignment & Backend Enhancements

**Duration**: 3-4 days | **Story Points**: 8 | **Assigned to**: python-backend-engineer (Opus)

### Objectives

- Align backend APIs with group membership and filtering requirements
- Avoid N+1 calls by enabling batch-friendly responses for group badges
- Update OpenAPI/SDK models to reflect new query params and optional fields

### Detailed Tasks

- Add optional `artifact_id` filter to `GET /api/v1/groups?collection_id=...` to return only groups that contain a specific artifact
- Add optional `group_id` filter to `GET /api/v1/user-collections/{collection_id}/artifacts` for Group filter and /groups page
- Add optional `include_groups=true` to `GET /api/v1/user-collections/{collection_id}/artifacts` to return each artifact’s groups (id, name, position)
- Resolve `useGroupArtifacts` API mismatch: either implement `GET /api/v1/groups/{group_id}/artifacts` or update hook to use `GET /api/v1/groups/{group_id}`
- Update OpenAPI + web SDK models/types to include new query params and optional fields

### Acceptance Criteria

- [x] `GET /groups` supports `artifact_id` filter (returns only groups containing that artifact within the collection)
- [x] `GET /user-collections/{collection_id}/artifacts` supports `group_id` filter
- [x] `GET /user-collections/{collection_id}/artifacts` supports `include_groups=true` and returns group list per artifact
- [x] `useGroupArtifacts` endpoint mismatch resolved (API or hook update)
- [x] OpenAPI schema + web SDK types updated
- [x] Backend tests cover new filters and response shape

### Testing Strategy

```bash
# Backend tests for new filters
pytest -k "groups and artifact_id"
pytest -k "collection_artifacts and group_id"
```

### Dependencies

- Database tables: Group, GroupArtifact, CollectionArtifact
- Existing collection artifacts pagination

### Risks & Mitigation

| Risk | Likelihood | Mitigation |
|------|------------|-----------|
| Response payload grows with include_groups | Medium | Make groups optional via `include_groups=true` |
| Query performance on large collections | Medium | Add indexes on GroupArtifact(artifact_id, group_id) and GroupArtifact(group_id, artifact_id) |

---

## Phase 1: Data Layer & Hooks

**Duration**: 3-4 days | **Story Points**: 8 | **Assigned to**: backend-typescript-architect (Opus)

### Objectives

- Create reusable hooks for fetching groups and artifact-group relationships
- Extend collection artifacts hooks to support `group_id` filtering and optional `include_groups`
- Implement TanStack Query caching with appropriate stale times
- Add API client function for fetching artifact groups
- Establish error handling patterns for graceful degradation

### Detailed Tasks

See: `collections-groups-ux-enhancement-v1/phase-1-tasks.md`

### Acceptance Criteria

- [x] `useGroups(collectionId)` hook created and exported from `@/hooks`
- [x] `useArtifactGroups(artifactId, collectionId)` hook uses `GET /groups?collection_id=&artifact_id=`
- [x] `fetchArtifactGroups()` API client function implemented
- [x] `useInfiniteCollectionArtifacts` supports optional `group_id` and `include_groups`
- [x] TanStack Query cache keys structured hierarchically
- [x] Stale times configured: groups 5 min, artifact-groups 10 min
- [x] Error handling returns fallback values (empty arrays, null)
- [x] ≥80% test coverage for all hooks
- [x] JSDoc comments document all exported functions

### Testing Strategy

```bash
# Unit tests for hooks
pnpm test -- use-groups.test.ts
pnpm test -- use-artifact-groups.test.ts

# Integration tests with API client
pnpm test -- hooks-integration.test.ts

# Coverage report
pnpm test -- --coverage
```

### Quality Gates

- [ ] All tests pass
- [ ] TypeScript strict mode enabled, no errors
- [ ] ESLint passes with no warnings
- [ ] Code reviewed by senior frontend engineer
- [ ] API contract verified against backend endpoints

### Dependencies

- TanStack React Query v5 (already in project)
- Existing `useCollectionContext()` hook
- Existing `apiRequest` from `@/lib/api`

### Risks & Mitigation

| Risk | Likelihood | Mitigation |
|------|------------|-----------|
| N+1 queries for artifact groups (M cards × 1 fetch each) | Medium | Implement query batching in Phase 2; use TanStack Query deduplication |
| API endpoint contract mismatch | Low | Verify backend `/groups` endpoint response format before implementation |
| Cache invalidation after mutations | Medium | Use `queryClient.invalidateQueries()` with hierarchical cache keys |

---

## Phase 2: Collection Badges on Cards

**Duration**: 4-5 days | **Story Points**: 10 | **Assigned to**: ui-engineer-enhanced (Opus)

### Objectives

- Add visual collection membership indicators to UnifiedCard component
- Implement "+N more" badge pattern for >2 collections
- Ensure accessibility compliance (WCAG 2.1 AA)
- Create reusable badge rendering utility

### Detailed Tasks

See: `collections-groups-ux-enhancement-v1/phase-2-tasks.md`

### Acceptance Criteria

- [x] Collection badges render on UnifiedCard when in "All Collections" view
- [x] Default collection hidden from badge display
- [x] Non-default collections shown with collection name
- [x] Verify All Collections API supplies `entity.collections`; add guard if missing
- [x] Max 2 badges displayed; 3+ collections show "X more..." badge
- [x] Hover on "X more..." shows tooltip with full collection list
- [x] Badges styled with shadcn Badge component (secondary color)
- [x] Badges hidden when viewing specific collection (conditional render)
- [x] Accessibility: each badge has aria-label and is keyboard-navigable
- [x] No performance regression: card render ≤50ms per card
- [x] ≥80% unit test coverage
- [x] Code review approved

### Component Structure

**File**: `skillmeat/web/components/shared/unified-card.tsx` (enhanced)

```tsx
// New section in UnifiedCard component
{!isSpecificCollectionContext && entity.collections && (
  <CollectionBadgeStack collections={entity.collections} />
)}
```

**New Utility Component**: `CollectionBadgeStack`

```tsx
// Location: skillmeat/web/components/shared/collection-badge-stack.tsx
interface CollectionBadgeStackProps {
  collections: Array<{ id: string; name: string }>;
  maxBadges?: number; // Default: 2
}

export function CollectionBadgeStack(props: CollectionBadgeStackProps) {
  // Render max 2 collection badges + "X more..." badge
  // Handle hover tooltip with full list
}
```

### Testing Strategy

```bash
# Unit tests for badge rendering
pnpm test -- unified-card.test.ts
pnpm test -- collection-badge-stack.test.ts

# Snapshot tests for badge layout
pnpm test -- -u # Update snapshots

# Accessibility audit
pnpm test:a11y # Run axe accessibility tests
```

### Quality Gates

- [ ] Component renders correctly in "All Collections" view
- [ ] Badge layout does not break card design
- [ ] Accessibility: WCAG 2.1 AA compliance verified (axe audit)
- [ ] Performance: card render time ≤50ms per card (profiled)
- [ ] ≥80% test coverage (statements, branches, lines)
- [ ] Code review complete
- [ ] Storybook entry created (optional but recommended)

### Dependencies

- Phase 1: Hooks (not used in Phase 2, but framework ready)
- Existing UnifiedCard component
- shadcn Badge component
- useCollectionContext hook

### Risks & Mitigation

| Risk | Likelihood | Mitigation |
|------|------------|-----------|
| Badge visual clutter | Medium | Design review with UI engineer; use max 2 badges + tooltip |
| Performance impact (many cards loaded) | Medium | Lazy-render badges only if entity has collections array |
| Color contrast accessibility failure | Low | shadcn Badge uses tested color system; verify 4.5:1 ratio |

---

## Phase 3: Group Badges & Modal Enhancement

**Duration**: 4-5 days | **Story Points**: 9 | **Assigned to**: ui-engineer-enhanced (Opus)

### Objectives

- Add group membership badges to cards (when in specific collection context) using `include_groups` data
- Enhance ModalCollectionsTab to display groups for each collection using artifact-scoped lookups
- Implement consistent badge styling (distinct from collection badges)
- Ensure no performance regression from group fetching (avoid per-card N+1)

### Detailed Tasks

See: `collections-groups-ux-enhancement-v1/phase-3-tasks.md`

### Acceptance Criteria

- [x] Group badges render on UnifiedCard when in specific collection context
- [x] Group badges styled with tertiary color (distinct from collection badges)
- [x] Max 2 group badges; 3+ groups show "X more..." badge
- [x] Tooltip on "X more..." shows full group list
- [x] Badges hidden when viewing "All Collections" or outside collection context
- [x] Group badges sourced from `include_groups` data on collection artifacts (no per-card fetch)
- [x] Modal groups use `useArtifactGroups(artifactId, collectionId)`
- [x] Loading state: skeleton or placeholder while modal groups fetch
- [x] Error handling: gracefully skip badge render if group data missing
- [x] ModalCollectionsTab placeholder (lines 197-198) replaced with Groups display
- [x] For each collection in modal, groups shown as badges or comma-separated list
- [x] "No groups" message if collection has no groups
- [x] Groups section loads with collection data; respects modal loading state
- [x] ≥80% unit test coverage
- [x] Code review approved

### Component Structure

**File**: `skillmeat/web/components/shared/unified-card.tsx` (enhanced)

```tsx
// New section in UnifiedCard (only when in specific collection context)
{isSpecificCollectionContext && entity.groups?.length ? (
  <GroupBadgeRow groups={entity.groups} />
) : null}
```

**New Component**: `GroupBadgeRow`

```tsx
// Location: skillmeat/web/components/shared/group-badge-row.tsx
interface GroupBadgeRowProps {
  groups: Array<{ id: string; name: string }>;
  maxBadges?: number; // Default: 2
}

export function GroupBadgeRow({ groups, maxBadges = 2 }: GroupBadgeRowProps) {
  // Render group badges with same pattern as CollectionBadgeStack
}
```

**File**: `skillmeat/web/components/entity/modal-collections-tab.tsx` (enhanced)

```tsx
// Replace placeholder at lines 197-198 with:
<div className="mt-3 space-y-2">
  <h4 className="text-sm font-medium">Groups in {collection.name}</h4>
  <GroupsDisplay collectionId={collection.id} artifactId={entity.id} />
</div>
```

**New Component**: `GroupsDisplay`

```tsx
// Location: skillmeat/web/components/entity/groups-display.tsx
interface GroupsDisplayProps {
  collectionId: string;
  artifactId: string;
}

export function GroupsDisplay({ collectionId, artifactId }: GroupsDisplayProps) {
  const { data: groups, isLoading } = useArtifactGroups(artifactId, collectionId);
  // Display groups as badges or comma-separated list
  // Show "No groups" if empty
}
```

### Testing Strategy

```bash
# Unit tests for group badges
pnpm test -- group-badge-row.test.ts
pnpm test -- groups-display.test.ts

# Integration test: modal with groups
pnpm test -- modal-collections-tab.test.ts

# Snapshot tests
pnpm test -- -u

# E2E test (optional): open modal and verify groups display
pnpm test:e2e -- modal-groups.spec.ts
```

### Quality Gates

- [ ] Group badges render correctly in specific collection context
- [ ] Modal Collections tab shows groups for each collection
- [ ] No performance regression from group fetching
- [ ] Loading states handled correctly (skeleton/placeholder)
- [ ] Error handling prevents card crashes
- [ ] Accessibility: WCAG 2.1 AA compliance verified
- [ ] ≥80% test coverage
- [ ] Code review complete

### Dependencies

- Phase 1: useArtifactGroups() hook and useGroups() hook
- Existing ModalCollectionsTab component
- Existing UnifiedCard component
- useCollectionContext hook for detecting collection context

### Risks & Mitigation

| Risk | Likelihood | Mitigation |
|------|------------|-----------|
| N+1 queries (one fetch per card) | Medium | Use `include_groups=true` on collection artifacts to render badges without per-card fetch |
| Modal load latency increases | Medium | Lazy-load groups; use skeleton loaders; profile before/after |
| Modal grows too large | Low | Groups section compact; use "+X more" pattern; scrollable if needed |

---

## Phase 4: Groups Sidebar Page

**Duration**: 5-6 days | **Story Points**: 12 | **Assigned to**: frontend-developer (Opus)

### Objectives

- Create new `/groups` page with group selector and artifact grid
- Add "Groups" navigation item to sidebar
- Implement view mode toggle (Grid/List) and filters (Type, Status, Scope, Sort)
- Reuse existing ArtifactGrid and filter components for consistency

### Detailed Tasks

See: `collections-groups-ux-enhancement-v1/phase-4-tasks.md`

### Acceptance Criteria

- [x] New `/groups` page renders at `/groups` URL
- [x] "Groups" tab appears in sidebar under Collections section
- [x] Group selector dropdown at top of page
- [x] Dropdown populated from `useGroups(selectedCollectionId)`
- [x] Artifact grid/list renders when group is selected
- [x] Artifacts fetched via `/user-collections/{collection_id}/artifacts?group_id=...`
- [x] Same filters (Type, Status, Scope, Sort) available and functional
- [x] View mode toggle (Grid/List) works and persists (localStorage)
- [x] Empty states: "No groups in collection" and "Select a group"
- [x] Infinite scroll or pagination works for group artifacts
- [x] Breadcrumb: Dashboard > Collections > Groups > [Group Name]
- [x] URL query param: `?group=<group-id>`
- [x] Performance: groups load ≤200ms; artifacts ≤500ms
- [x] ≥80% unit test coverage
- [x] E2E happy path test
- [x] Code review approved

### Page Structure

**File**: `skillmeat/web/app/groups/page.tsx` (new)

```tsx
// Server component wrapping client components
export default async function GroupsPage({ searchParams }: {
  searchParams: Promise<{ group?: string }>
}) {
  const params = await searchParams;
  return <GroupsPageClient selectedGroupId={params.group} />;
}
```

**File**: `skillmeat/web/app/groups/layout.tsx` (new, if needed for breadcrumb)

```tsx
// Optional: add breadcrumb to layout
export const metadata = {
  title: 'Groups | SkillMeat',
};

export default function GroupsLayout({ children }: {
  children: React.ReactNode
}) {
  return <>{children}</>;
}
```

**Client Components** (in `/app/groups/components/`):

1. `GroupsPageClient` — Main page controller
2. `GroupSelector` — Dropdown to select group
3. `GroupArtifactGrid` — Reuse ArtifactGrid component
4. `GroupFilters` — Reuse Filters component
5. `ViewModeToggle` — Grid/List toggle

### Component Implementation

**GroupSelector Component**

```tsx
interface GroupSelectorProps {
  collectionId: string;
  selectedGroupId?: string;
  onGroupSelect: (groupId: string) => void;
}

export function GroupSelector({ collectionId, selectedGroupId, onGroupSelect }: GroupSelectorProps) {
  const { data: groups, isLoading } = useGroups(collectionId);
  // Render Select dropdown with groups
  // Trigger onGroupSelect when user selects group
}
```

**GroupArtifactGrid Component**

```tsx
interface GroupArtifactGridProps {
  collectionId: string;
  groupId: string;
  view: 'grid' | 'list';
  filters?: ArtifactFilters;
}

export function GroupArtifactGrid({ collectionId, groupId, view, filters }: GroupArtifactGridProps) {
  const { data, isLoading, hasNextPage, fetchNextPage } = useInfiniteCollectionArtifacts(
    collectionId,
    { ...filters, group_id: groupId }
  );
  // Render artifacts using existing ArtifactGrid or ArtifactList component
  // Implement infinite scroll with fetchNextPage
}
```

### API Integration

- Use existing `useInfiniteCollectionArtifacts(collectionId, { group_id })`
- Requires Phase 0 backend support for `group_id` filter on `/user-collections/{collection_id}/artifacts`

### Testing Strategy

```bash
# Unit tests for page and components
pnpm test -- groups/page.test.ts
pnpm test -- groups/components/*.test.ts

# E2E happy path test
pnpm test:e2e -- groups-page.spec.ts

# Performance test (profile page load)
# Use Lighthouse or similar tool to verify ≤200ms load time

# Coverage
pnpm test -- --coverage
```

### Quality Gates

- [ ] /groups page renders and navigates correctly
- [ ] Group selector dropdown functional with API data
- [ ] Artifact grid displays correct artifacts for selected group
- [ ] Filters and view modes work correctly
- [ ] Empty states render properly
- [ ] Performance: groups load ≤200ms; artifacts ≤500ms
- [ ] ≥80% test coverage
- [ ] E2E test passes
- [ ] Code review complete

### Dependencies

- Phase 1: useGroups(), useInfiniteCollectionArtifacts() hooks (with `group_id` support)
- Existing ArtifactGrid, ArtifactList components
- Existing Filters component
- useCollectionContext() hook
- Navigation component for sidebar update

### Risks & Mitigation

| Risk | Likelihood | Mitigation |
|------|------------|-----------|
| Performance regression (slow artifact fetch) | Medium | Profile before rollout; implement pagination/lazy-loading |
| Navigation sidebar integration breaks | Low | Verify Navigation component structure before Phase 4 |
| Scope creep (drag-drop, bulk ops) | High | Strictly adhere to In-Scope list; defer to Phase 2 |
| Cross-browser Select component issues | Low | shadcn Select well-tested; verify Radix UI browser support |

---

## Phase 5: Group Filter Integration

**Duration**: 3-4 days | **Story Points**: 8 | **Assigned to**: ui-engineer-enhanced (Sonnet)

### Objectives

- Add Group filter dropdown to Filters component (/collection page)
- Add Group filter dropdown to EntityFilters component (/manage page)
- Implement conditional visibility (hidden in "All Collections" view)
- Integrate group filter with artifact query hooks

### Detailed Tasks

See: `collections-groups-ux-enhancement-v1/phase-5-tasks.md`

### Acceptance Criteria

- [x] Group filter dropdown appears on /collection page when in specific collection context
- [x] Group filter dropdown appears on /manage page when in specific collection context
- [x] Filter hidden when viewing "All Collections" or outside collection context
- [x] Filter options populated from `useGroups(collectionId)` API
- [x] Default value: "All Groups" (no filter applied)
- [x] Selecting group filters artifacts; URL updates with `?group=<id>`
- [x] Clearing filter removes `?group=<id>` from URL
- [x] Both Filters and EntityFilters components have identical Group filter UX
- [x] Filter state persists across page navigation (via URL params)
- [x] Tooltip/help text explains filter availability
- [x] ≥80% test coverage
- [x] Code review approved

### Component Modifications

**File**: `skillmeat/web/components/collection/filters.tsx` (enhanced)

```tsx
// Add to existing Filters component
{isSpecificCollectionContext && (
  <GroupFilterSelect
    collectionId={selectedCollectionId}
    value={filters.groupId}
    onChange={(groupId) => onFilterChange({ ...filters, groupId })}
  />
)}
```

**File**: `skillmeat/web/app/manage/components/entity-filters.tsx` (enhanced)

```tsx
// Add to existing EntityFilters component
{isSpecificCollectionContext && (
  <GroupFilterSelect
    collectionId={selectedCollectionId}
    value={filters.groupId}
    onChange={(groupId) => onFilterChange({ ...filters, groupId })}
  />
)}
```

**New Utility Component**: `GroupFilterSelect`

```tsx
// Location: skillmeat/web/components/shared/group-filter-select.tsx
interface GroupFilterSelectProps {
  collectionId: string;
  value?: string;
  onChange: (groupId: string | undefined) => void;
}

export function GroupFilterSelect(props: GroupFilterSelectProps) {
  const { data: groups, isLoading } = useGroups(props.collectionId);
  // Render Select with "All Groups" default option
  // Populate with groups from collection
}
```

### Hook Enhancement

**File**: `skillmeat/web/hooks/use-artifact-filters.ts` (new or enhanced)

```typescript
export interface ArtifactFilters {
  type?: EntityType;
  status?: string;
  scope?: string;
  sort?: string;
  groupId?: string; // NEW
}

export function useInfiniteCollectionArtifacts(
  collectionId: string,
  filters?: ArtifactFilters // Already exists, add groupId support
): UseInfiniteQueryResult<...>
```

- Map `groupId` to `group_id` query param on `/user-collections/{collection_id}/artifacts`

### Testing Strategy

```bash
# Unit tests for filter components
pnpm test -- group-filter-select.test.ts
pnpm test -- filters.test.ts
pnpm test -- entity-filters.test.ts

# Integration tests: filter applied and grid updates
pnpm test -- collection-page.test.ts
pnpm test -- manage-page.test.ts

# E2E test: apply group filter and verify artifacts
pnpm test:e2e -- group-filter.spec.ts

# Coverage
pnpm test -- --coverage
```

### Quality Gates

- [ ] Group filter dropdown visible in correct contexts
- [ ] Filter hidden when viewing "All Collections"
- [ ] Dropdown populated with groups from current collection
- [ ] Selecting group filters artifacts in grid/list
- [ ] URL updates with ?group=<id> parameter
- [ ] Filter state persists across navigation
- [ ] Tooltip/help text explains filter
- [ ] ≥80% test coverage
- [ ] Code review complete

### Dependencies

- Phase 1: useGroups() hook
- Existing Filters component
- Existing EntityFilters component
- Existing artifact query hooks (useInfiniteCollectionArtifacts, etc.)
- useCollectionContext() hook

### Risks & Mitigation

| Risk | Likelihood | Mitigation |
|------|------------|-----------|
| URL param collision (group vs. other params) | Low | Verify URL param naming doesn't conflict; use consistent naming |
| Filter state lost on page refresh | Low | Store in URL query params (already done by framework) |
| Cross-page filter inconsistency | Medium | Ensure identical UX between /collection and /manage pages |

---

## Integration & Testing

### Cross-Phase Integration Points

| Integration | Phase Dependency | Verification |
|-------------|------------------|--------------|
| Card badges + Modal | 2, 3 | Same badge styling; consistent color scheme |
| Card badges + /groups page | 2, 4 | Badge groupId matches group selector on /groups |
| Group filter + /groups page | 4, 5 | Filter groupId matches /groups page group selection |
| All pages + Context | 1-5 | useCollectionContext() provides consistent state across all pages |

### End-to-End Test Scenarios

**Test 1: Collection Badges Visibility**

```
1. Navigate to /collection with "All Collections" view
2. VERIFY: Collection badges appear on cards for non-default collections
3. Select specific collection from dropdown
4. VERIFY: Collection badges disappear; Group badges appear
5. VERIFY: Collection badges reappear when back to "All Collections"
```

**Test 2: Group Badges & Modal**

```
1. Navigate to /collection and select a collection
2. VERIFY: Group badges appear on cards
3. Click card to open modal
4. VERIFY: Collections tab shows groups for each collection
5. VERIFY: Badge styling consistent between card and modal
```

**Test 3: Groups Page Navigation**

```
1. Click "Groups" in sidebar
2. VERIFY: /groups page renders with group selector
3. Select group from dropdown
4. VERIFY: Artifact grid updates with that group's artifacts
5. Verify: Breadcrumb shows: Dashboard > Collections > Groups > [Group Name]
```

**Test 4: Group Filter**

```
1. Navigate to /collection and select a collection
2. VERIFY: Group filter dropdown appears in Filters
3. Select group from filter
4. VERIFY: URL updates with ?group=<id>
5. VERIFY: Artifact grid shows only that group's artifacts
6. Navigate away and return
7. VERIFY: Filter state persists via URL
```

**Test 5: Cross-Page Consistency**

```
1. Apply group filter on /collection page
2. Navigate to /manage page
3. VERIFY: Group filter context is appropriate for /manage
4. Apply same group filter on /manage
5. VERIFY: Artifacts shown match /collection view
```

### Performance Benchmarks

| Metric | Target | Measurement Tool |
|--------|--------|------------------|
| Groups fetch latency (Phase 1) | ≤200ms | Chrome DevTools Network tab |
| Card render with badges | ≤50ms per card | React DevTools Profiler |
| /groups page load | ≤500ms | Lighthouse |
| Modal Collections tab load | ≤300ms | Chrome DevTools Network tab |
| Filter dropdown population | ≤150ms | Chrome DevTools |

### Accessibility Validation

**Tools**: axe DevTools, Lighthouse, NVDA/JAWS screen reader

| Component | Checks |
|-----------|--------|
| Collection badges | aria-labels, color contrast (4.5:1), keyboard navigation |
| Group badges | aria-labels, color contrast, keyboard navigation |
| Group filter | Select semantics, aria-labels, keyboard navigation |
| /groups page | Heading hierarchy, landmark navigation, filter semantics |
| Modal | Groups section heading, aria-labels for badges |

---

## Quality Standards & Gates

### Code Quality Checklist

- [ ] All new code: TypeScript strict mode, no `any` types
- [ ] All new components: use shadcn primitives, no custom styling
- [ ] All new functions: JSDoc comments with examples
- [ ] ESLint: zero errors, zero warnings
- [ ] TypeScript: zero errors (`pnpm type-check`)
- [ ] Tests: ≥80% coverage for new functions and components
- [ ] Tests: all pass (`pnpm test`)

### Accessibility Checklist

- [ ] WCAG 2.1 Level AA: axe audit passes with zero critical issues
- [ ] Color contrast: all text meets 4.5:1 ratio (badges, filters, buttons)
- [ ] Keyboard navigation: all interactive elements reachable via Tab key
- [ ] Screen reader: all badges have aria-labels; filter semantics correct
- [ ] Focus visibility: clear focus indicators on all interactive elements

### Performance Checklist

- [ ] Page load latency: ≤200ms added from baseline
- [ ] Card render: ≤50ms per card with badges
- [ ] Modal load: ≤300ms for Collections tab with groups
- [ ] TanStack Query: cache hit rate ≥80% for repeated group fetches
- [ ] No unnecessary re-renders: profiler shows no excessive renders

### Test Coverage Checklist

- [ ] Unit tests: ≥80% coverage (statements, branches, lines)
- [ ] Integration tests: multi-component workflows pass
- [ ] E2E tests: all 5 test scenarios pass
- [ ] Snapshot tests: baseline snapshots created; all match
- [ ] Accessibility tests: axe audit integrates into test suite

### Code Review Checklist

- [ ] At least one senior engineer review
- [ ] Architecture decisions documented in comments
- [ ] Error handling reviewed and tested
- [ ] Performance considerations addressed
- [ ] No breaking changes to existing APIs

---

## Risk Management

### High-Risk Items

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| **N+1 Query Problem** (fetch groups for each card) | Medium | High (100+ cards = excessive API calls) | Avoid per-card fetch by using `include_groups=true` on collection artifacts; reserve `useArtifactGroups` for modal only |
| **Performance Regression** (badge rendering slows page) | Medium | Medium (bad UX perceived slowness) | Lazy-load badges; profile with React DevTools; implement virtualization if needed |
| **Stale Data After CRUD** (groups list doesn't update after create/update) | Medium | Medium (confusing UX) | Use `queryClient.invalidateQueries()` on mutations; test invalidation in Phase 1 |
| **Accessibility Failure** (badges fail WCAG audit) | Low | High (compliance issue) | Use axe DevTools early; verify color contrast; test keyboard navigation |
| **Scope Creep** (dragging, bulk ops added to Phase 4) | High | High (timeline overrun) | Strictly enforce In-Scope list; create separate PRD for Phase 2 features |

### Medium-Risk Items

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Color scheme conflict | Low | Medium | Verify tertiary color works with design system |
| Cross-browser compatibility | Low | Medium | Test with shadcn components; verify Radix UI browser support |
| Modal size increase | Medium | Low | Use compact badge layout; scrollable if needed |

### Monitoring & Alerting

**Post-Rollout Monitoring** (first 2 weeks):

1. **GA Events Tracking**:
   - `collection_badge_viewed` (track render frequency)
   - `group_badge_viewed`
   - `groups_page_visited`
   - `group_filter_applied`

2. **Error Tracking** (Sentry):
   - Failed group fetches
   - Badge render errors
   - Modal load failures

3. **Performance Metrics** (Web Vitals, RUM):
   - Page load latency (compare baseline vs. post-rollout)
   - Card render time
   - Modal load time

4. **User Feedback**:
   - Support tickets mentioning Groups or badges
   - NPS survey: "Card information is clear"

---

## Rollout Plan

### Pre-Release (Internal Testing)

**Week 1-2**: Development (Phases 1-3)
**Week 3**: Feature completion (Phases 4-5)
**Week 3-4**: Testing & fixes

**Beta Environment Testing**:

- [ ] All 5 acceptance criteria lists complete
- [ ] Code review approved by 2+ engineers
- [ ] ≥80% test coverage verified
- [ ] Performance benchmarks met
- [ ] Accessibility audit passed
- [ ] E2E tests all pass

### Staged Rollout

**Stage 1 (Day 1)**: 10% of users via feature flag
- Monitor: error rate, page load latency, GA events
- Metrics: <0.1% error rate, latency ≤250ms vs. 50ms baseline

**Stage 2 (Day 2-3)**: 50% of users
- Continue monitoring
- Gather initial user feedback

**Stage 3 (Day 4-7)**: 100% rollout
- Monitor for 1 week post-rollout
- Review GA events for adoption metrics

### Rollback Criteria

Immediate rollback if:
- Error rate >0.5%
- Page load latency >500ms (>200ms increase)
- WCAG Level A accessibility failures detected
- Data loss or corruption reported
- Critical bugs affecting >5% of users

### Communication Plan

- [ ] Announce rollout in #engineering Slack channel
- [ ] Link to this Implementation Plan in commit messages
- [ ] Update release notes with feature summary
- [ ] Prepare user documentation (help center article)

---

## Success Metrics

### Product Metrics (Track Post-Rollout)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Groups page adoption** | 60%+ of users visit within 2 weeks | GA: `groups_page_visited` |
| **Group filter usage** | 40%+ of collection sessions use filter | GA: `group_filter_applied` |
| **Modal engagement** | 50%+ of modal opens with groups interact with section | GA: `modal_groups_viewed` |
| **Card usability (NPS)** | +15 point improvement on "Card clarity" survey | Post-launch survey |
| **Performance** | No regression; ≤200ms added latency | RUM/Lighthouse |
| **Accessibility** | Zero WCAG A failures; zero accessibility support tickets | Issue tracker, axe audit |

### Engineering Metrics (Track During Development)

| Metric | Target |
|--------|--------|
| **Test coverage** | ≥80% across all new code |
| **Code review turnaround** | <24 hours |
| **Build/deployment time** | No increase (automated tests <5 min) |
| **Type safety** | Zero TypeScript strict mode errors |

---

## Dependencies & Prerequisites

### External Dependencies

- React 19+ (already in project)
- Next.js 15+ App Router (already in project)
- TanStack Query v5+ (already in project)
- shadcn/ui components (already integrated)
- Radix UI (already in project)

### Internal Dependencies

- `useCollectionContext()` hook (must provide `selectedCollectionId`, `viewMode`)
- `apiRequest()` from `@/lib/api` (existing)
- `useInfiniteCollectionArtifacts()` hook (might need enhancement for groupId filter)
- `UnifiedCard` component (modification target)
- `Filters` component (modification target)
- `EntityFilters` component (modification target)
- `ModalCollectionsTab` component (modification target)

### Backend Readiness

- [ ] Groups API endpoints verified: GET /groups, GET /groups/{id}
- [ ] API response contract matches types in `@/types/groups.ts`
- [ ] Backend supports `artifact_id` filter on `GET /groups` for artifact→group lookups
- [ ] Backend supports `group_id` filter on `/user-collections/{collection_id}/artifacts`
- [ ] Backend supports `include_groups=true` on `/user-collections/{collection_id}/artifacts`
- [ ] No breaking changes to existing endpoints

---

## Documentation & Knowledge Transfer

### Code Documentation

- **JSDoc Comments**: All exported functions documented with:
  - Purpose
  - Parameters with types
  - Return type
  - Usage examples
  - Error handling notes

### Architecture Documentation

- **Decision Record**: Add to `.claude/context/` documenting:
  - Why hooks-first approach
  - Why minimal backend changes were required
  - Why conditional rendering for badges
  - Cache invalidation strategy

### Testing Documentation

- **Test Patterns**: Document badge render test patterns, hook test patterns in `.claude/context/testing-patterns.md`
- **E2E Scenarios**: Link to test specifications in Phase 4 section

### User Documentation

- **Help Article**: "Managing Artifacts with Collections & Groups"
- **Screenshots**: Badge examples, /groups page walkthrough
- **FAQ**: "What's the difference between Collections and Groups?"

---

## Timeline & Resources

### Week-by-Week Breakdown

**Week 1:**
- Phase 0 (3-4 days): Backend API alignment + OpenAPI/SDK updates
- Phase 1 (1-2 days): Hook implementation, testing
- Phase 2 (1-2 days): Start Collection badges

**Week 2:**
- Phase 2 (3-4 days): Complete Collection badges
- Phase 3 (1-2 days): Start Group badges

**Week 3:**
- Phase 3 (3-4 days): Complete Group badges + Modal
- Phase 4 (1-2 days): Start /groups page

**Week 4:**
- Phase 4 (4-5 days): Complete /groups page
- Phase 5 (1-2 days): Start Group filter

**Week 5 (Final Days):**
- Phase 5 (2-3 days): Complete Group filter
- Integration testing, fixes
- Code review, acceptance
- Beta rollout preparation

### Resource Allocation

**Team Size**: 2-3 engineers

| Role | Phases | Total Hours |
|------|--------|-------------|
| Backend Engineer (Python) | 0 | 20-25 hours |
| Backend/TypeScript Architect (Opus) | 1 | 35-40 hours |
| UI Engineer (Opus) | 2, 3 | 40-50 hours |
| Frontend Developer (Opus) | 4 | 50-60 hours |
| UI Engineer (Sonnet) | 5 | 25-35 hours |
| Code Reviewer (Haiku tasks) | All | 10-15 hours |
| QA/Tester (parallel) | All | 30-40 hours |

**Total Estimated Effort**: ~220-260 hours over 4-5 weeks

---

## Appendix A: File Structure

```
skillmeat/web/
├── hooks/
│   ├── use-groups.ts (ENHANCED: add useArtifactGroups)
│   ├── use-collections.ts (ENHANCED: add group_id/include_groups support)
│   ├── use-artifact-groups.ts (NEW)
│   └── index.ts (MODIFIED: export new hooks)
│
├── components/
│   ├── shared/
│   │   ├── unified-card.tsx (ENHANCED: add badge sections)
│   │   ├── collection-badge-stack.tsx (NEW)
│   │   ├── group-badge-row.tsx (NEW)
│   │   └── group-filter-select.tsx (NEW)
│   │
│   ├── collection/
│   │   ├── filters.tsx (ENHANCED: add group filter)
│   │   └── ... (existing components)
│   │
│   ├── entity/
│   │   ├── modal-collections-tab.tsx (ENHANCED: add groups display)
│   │   ├── groups-display.tsx (NEW)
│   │   └── ... (existing components)
│   │
│   └── navigation.tsx (ENHANCED: add Groups tab)
│
├── app/
│   ├── groups/
│   │   ├── page.tsx (NEW)
│   │   ├── layout.tsx (NEW, optional)
│   │   └── components/
│   │       ├── groups-page-client.tsx (NEW)
│   │       ├── group-selector.tsx (NEW)
│   │       ├── group-artifact-grid.tsx (NEW)
│   │       └── ... (other components)
│   │
│   ├── manage/
│   │   └── components/
│   │       └── entity-filters.tsx (ENHANCED: add group filter)
│   │
│   └── ... (existing pages)
│
├── __tests__/
│   ├── hooks/
│   │   ├── use-groups.test.ts (ENHANCED)
│   │   └── use-artifact-groups.test.ts (NEW)
│   │
│   ├── components/
│   │   ├── collection-badge-stack.test.ts (NEW)
│   │   ├── group-badge-row.test.ts (NEW)
│   │   ├── group-filter-select.test.ts (NEW)
│   │   ├── unified-card.test.ts (ENHANCED)
│   │   └── ... (other tests)
│   │
│   └── pages/
│       └── groups.test.ts (NEW)
│
└── types/
    ├── groups.ts (VERIFY: existing types)
    └── artifact.ts (VERIFY: collections, groups arrays)
```

---

## Appendix B: Phase-Specific Task Documents

Detailed task breakdowns for each phase are provided in separate files:

- **Phase 1**: `collections-groups-ux-enhancement-v1/phase-1-tasks.md`
- **Phase 2**: `collections-groups-ux-enhancement-v1/phase-2-tasks.md`
- **Phase 3**: `collections-groups-ux-enhancement-v1/phase-3-tasks.md`
- **Phase 4**: `collections-groups-ux-enhancement-v1/phase-4-tasks.md`
- **Phase 5**: `collections-groups-ux-enhancement-v1/phase-5-tasks.md`

Each document contains:
- Task IDs and names (P#-T#)
- Detailed descriptions and acceptance criteria
- Story point estimates
- Dependency chains
- Quality gates and testing requirements

---

## Appendix C: Linear Board Setup

### Board Configuration

**Project**: Collections & Groups UX Enhancement v1
**Status**: Ready for Planning
**Effort**: 47 story points

### Epic Hierarchy

```
Epic: Collections & Groups UX Enhancement (47 SP)
├── Story: Data Layer & Hooks (8 SP)
│   ├── Task: useGroups hook
│   ├── Task: useArtifactGroups hook
│   └── ...
│
├── Story: Collection Badges on Cards (10 SP)
│   ├── Task: Enhance UnifiedCard component
│   ├── Task: Create CollectionBadgeStack component
│   └── ...
│
├── Story: Group Badges & Modal (9 SP)
├── Story: Groups Sidebar Page (12 SP)
└── Story: Group Filter Integration (8 SP)
```

### Label Strategy

- `collections-groups-ux-v1` — Primary feature label
- `phase-1`, `phase-2`, etc. — Phase identifier
- `frontend` — Component ownership
- `hook` — Hook implementation
- `test` — Testing task
- `a11y` — Accessibility-related
- `perf` — Performance-critical

### Milestone Configuration

- Milestone 1: Phase 1-3 complete (2 weeks)
- Milestone 2: Phase 4-5 complete (2 weeks)
- Milestone 3: Integration & rollout ready (1 week)

---

## Appendix D: Git Branching Strategy

```
main (protected)
├── feat/collections-groups-ux-v1 (main feature branch)
│   ├── feat/collections-groups-ux/phase-1-hooks
│   ├── feat/collections-groups-ux/phase-2-collection-badges
│   ├── feat/collections-groups-ux/phase-3-group-badges
│   ├── feat/collections-groups-ux/phase-4-groups-page
│   └── feat/collections-groups-ux/phase-5-group-filter
│
└── (after phases complete, squash merge to main)
```

### Commit Message Convention

```
feat(collections-groups): [Phase N] [Component] - [Brief description]

- Detailed explanation of change
- Reference to acceptance criteria
- Link to related tasks

Related: feat/collections-groups-ux-v1
Co-Authored-By: [Engineer Name]
```

---

## References & Links

### Related Documents

- **PRD**: `/docs/project_plans/PRDs/harden-polish/collections-groups-ux-enhancement-v1.md`
- **Web CLAUDE.md**: `/skillmeat/web/CLAUDE.md`
- **Rules**: `//.claude/rules/web/`
- **Context**: `//.claude/context/key-context/`

### Code References

- **Groups Types**: `/skillmeat/web/types/groups.ts`
- **Groups API Client**: `/skillmeat/web/lib/api/groups.ts`
- **UnifiedCard Component**: `/skillmeat/web/components/shared/unified-card.tsx`
- **Filters Component**: `/skillmeat/web/components/collection/filters.tsx`
- **ModalCollectionsTab**: `/skillmeat/web/components/entity/modal-collections-tab.tsx`
- **Navigation**: `/skillmeat/web/components/navigation.tsx`

### External Resources

- **TanStack Query**: https://tanstack.com/query/latest
- **shadcn/ui**: https://ui.shadcn.com/
- **Radix UI**: https://radix-ui.com/
- **WCAG 2.1**: https://www.w3.org/WAI/WCAG21/quickref/
- **axe DevTools**: https://www.deque.com/axe/devtools/

---

## Sign-Off

**Implementation Plan Status**: READY FOR DEVELOPMENT

- [x] All phases defined with clear acceptance criteria
- [x] Task breakdown complete with story point estimates
- [x] Risk assessment complete with mitigation strategies
- [x] Quality standards and test strategies defined
- [x] Resource allocation calculated
- [x] Timeline established (3-4 weeks)
- [x] Success metrics defined
- [x] Rollout and monitoring plan documented

**Next Steps**:

1. Create Linear board with phase-specific stories
2. Assign engineers to phases (Opus for Phases 1-4, Sonnet for Phase 5)
3. Begin Phase 1 development
4. Daily standups during development weeks
5. Code review gates before each phase merge

**Document Prepared By**: Claude Code (AI Agent)
**Date Prepared**: 2026-01-19
**Last Updated**: 2026-01-19

---

**End of Master Implementation Plan**

For detailed task breakdowns, see phase-specific task documents in the `collections-groups-ux-enhancement-v1/` subdirectory.
