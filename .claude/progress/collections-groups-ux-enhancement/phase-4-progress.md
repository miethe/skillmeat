---
type: progress
prd: collections-groups-ux-enhancement
phase: 4
title: Groups Sidebar Page
status: completed
started: "2026-01-20T12:10:00Z"
completed: "2026-01-20T12:35:00Z"
overall_progress: 100
completion_estimate: on-track
total_tasks: 6
completed_tasks: 6
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- frontend-developer
contributors: []
tasks:
- id: P4-T1
  description: Add Groups nav item to sidebar Navigation component
  status: completed
  assigned_to:
  - frontend-developer
  dependencies: []
  estimated_effort: 1h
  priority: high
- id: P4-T2
  description: Create /groups/page.tsx with server component wrapper
  status: completed
  assigned_to:
  - frontend-developer
  dependencies: []
  estimated_effort: 2h
  priority: high
- id: P4-T3
  description: Implement GroupSelector dropdown component
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - P4-T2
  estimated_effort: 2.5h
  priority: high
- id: P4-T4
  description: Create GroupArtifactGrid with infinite scroll
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - P4-T2
  estimated_effort: 3h
  priority: high
- id: P4-T5
  description: Add empty states and loading skeletons
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - P4-T3
  - P4-T4
  estimated_effort: 1.5h
  priority: medium
- id: P4-T6
  description: Write unit and integration tests (≥80% coverage)
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - P4-T1
  - P4-T2
  - P4-T3
  - P4-T4
  - P4-T5
  estimated_effort: 4h
  priority: high
parallelization:
  batch_1:
  - P4-T1
  - P4-T2
  batch_2:
  - P4-T3
  - P4-T4
  batch_3:
  - P4-T5
  batch_4:
  - P4-T6
  critical_path:
  - P4-T2
  - P4-T3
  - P4-T5
  - P4-T6
  estimated_total_time: 10h
blockers: []
success_criteria:
- id: SC-1
  description: New /groups page renders at /groups URL
  status: pending
- id: SC-2
  description: Groups tab appears in sidebar under Collections section
  status: pending
- id: SC-3
  description: Group selector dropdown at top of page
  status: pending
- id: SC-4
  description: Dropdown populated from useGroups(selectedCollectionId)
  status: pending
- id: SC-5
  description: Artifact grid/list renders when group is selected
  status: pending
- id: SC-6
  description: Same filters (Type, Status, Scope, Sort) available and functional
  status: pending
- id: SC-7
  description: View mode toggle (Grid/List) works and persists (localStorage)
  status: pending
- id: SC-8
  description: 'Empty states: No groups in collection and Select a group'
  status: pending
- id: SC-9
  description: Infinite scroll or pagination works for group artifacts
  status: pending
- id: SC-10
  description: 'Breadcrumb: Dashboard > Collections > Groups > [Group Name]'
  status: pending
- id: SC-11
  description: 'URL query param: ?group=<group-id>'
  status: pending
- id: SC-12
  description: 'Performance: groups load ≤200ms; artifacts ≤500ms'
  status: pending
- id: SC-13
  description: ≥80% unit test coverage
  status: pending
- id: SC-14
  description: E2E happy path test passes
  status: pending
files_modified:
- skillmeat/web/components/navigation.tsx
- skillmeat/web/app/groups/page.tsx
- skillmeat/web/app/groups/components/groups-page-client.tsx
- skillmeat/web/app/groups/components/group-selector.tsx
- skillmeat/web/app/groups/components/group-artifact-grid.tsx
- skillmeat/web/hooks/use-groups.ts
- skillmeat/web/__tests__/pages/groups.test.ts
- skillmeat/web/__tests__/components/group-selector.test.ts
- skillmeat/web/tests/e2e/groups-page.spec.ts
progress: 100
updated: '2026-01-20'
---

# Collections & Groups UX Enhancement - Phase 4: Groups Sidebar Page

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/collections-groups-ux-enhancement/phase-4-progress.md -t P4-T1 -s completed
```

**Quick Reference for Task Orchestration**:

```python
# Batch 1 (parallel - independent tasks)
Task("frontend-developer", "Add Groups nav item to sidebar. File: components/navigation.tsx. Add Groups link under Collections section, icon, active state.", model="opus")
Task("frontend-developer", "Create /groups page. File: app/groups/page.tsx. Server component with searchParams, await params (Next.js 15), pass to client component.", model="opus")

# Batch 2 (parallel after batch 1)
Task("frontend-developer", "Implement GroupSelector dropdown. File: app/groups/components/group-selector.tsx. Use shadcn Select, populate from useGroups hook, handle selection.", model="opus")
Task("frontend-developer", "Create GroupArtifactGrid. File: app/groups/components/group-artifact-grid.tsx. Reuse ArtifactGrid component, implement infinite scroll with useInfiniteGroupArtifacts hook.", model="opus")

# Batch 3 (sequential after batch 2)
Task("frontend-developer", "Add empty states and loading skeletons. Files: app/groups/components/*.tsx. Create No groups, Select a group, and Loading states with shadcn Skeleton.", model="opus")

# Batch 4 (sequential - testing)
Task("frontend-developer", "Write unit and E2E tests. Files: __tests__/pages/groups.test.ts, __tests__/components/group-selector.test.ts, tests/e2e/groups-page.spec.ts. ≥80% coverage, E2E happy path.", model="opus")
```

---

## Objective

Create a dedicated `/groups` page that provides first-class navigation for Groups. Users can browse groups within a collection, select a group from a dropdown, and view all artifacts in that group with the same filtering and view options available on the collection page.

---

## Implementation Notes

### Architectural Decisions

**Page Structure**: Server component wrapper (`page.tsx`) with client components for interactivity:
```typescript
// app/groups/page.tsx (server component)
export default async function GroupsPage({ searchParams }: {
  searchParams: Promise<{ group?: string }>
}) {
  const params = await searchParams; // Next.js 15 requires await
  return <GroupsPageClient selectedGroupId={params.group} />;
}
```

**Component Hierarchy**:
```
GroupsPage (server)
└── GroupsPageClient (client)
    ├── GroupSelector (dropdown)
    ├── Filters (reused component)
    ├── ViewModeToggle (grid/list)
    └── GroupArtifactGrid (infinite scroll)
        └── ArtifactGrid/ArtifactList (reused)
```

**Hook Enhancement**: Add `useInfiniteGroupArtifacts` to Phase 1 hooks:
```typescript
export function useInfiniteGroupArtifacts(
  groupId: string,
  filters?: ArtifactFilters
): UseInfiniteQueryResult<...>
```

**URL State Management**: Store selected group in query param for bookmarkability:
```typescript
const router = useRouter();
const handleGroupSelect = (groupId: string) => {
  router.push(`/groups?group=${groupId}`);
};
```

**View Mode Persistence**: Use localStorage to persist grid/list preference:
```typescript
const [viewMode, setViewMode] = useLocalStorage('groups-view-mode', 'grid');
```

### Patterns and Best Practices

**Reference Patterns**:
- `/collection/page.tsx` structure (similar layout)
- Existing `ArtifactGrid` component (reuse for consistency)
- Existing `Filters` component (reuse entire component)
- Navigation sidebar pattern in `components/navigation.tsx`

**Infinite Scroll Pattern** (reuse from collection page):
```typescript
const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteGroupArtifacts(groupId);

<InfiniteScroll
  loadMore={fetchNextPage}
  hasMore={hasNextPage}
  isLoading={isFetchingNextPage}
>
  <ArtifactGrid artifacts={data?.pages.flatMap(p => p.items)} />
</InfiniteScroll>
```

**Empty States**:
1. No groups in collection: "This collection has no groups yet. Create groups to organize your artifacts."
2. No group selected: "Select a group from the dropdown to view its artifacts."
3. No artifacts in group: "This group has no artifacts. Add artifacts to this group."

**Breadcrumb Navigation** (optional but recommended):
```
Dashboard > Collections > Groups > [Group Name]
```

### Known Gotchas

**Next.js 15 Params Pattern**: `searchParams` is now a Promise and must be awaited:
```typescript
// CORRECT
const params = await searchParams;
const groupId = params.group;

// WRONG (will error in Next.js 15)
const groupId = searchParams.group;
```

**Navigation Sidebar Integration**: Verify `Navigation` component structure before adding Groups link. Current structure may have Collections section as collapsible.

**Scope Creep Risk**: DO NOT implement drag-drop, bulk operations, or group CRUD in this phase. Focus strictly on browsing and viewing.

**Performance**: Groups dropdown population could be slow if collection has 100+ groups. Mitigation:
- Use searchable Select (shadcn Select supports search)
- Lazy-load groups on dropdown open
- Profile with large collections

**Cross-Browser Select Compatibility**: shadcn Select uses Radix UI, which is well-tested. Verify on Safari, Firefox, Chrome.

**Infinite Scroll vs Pagination**: Recommendation: use infinite scroll for consistency with collection page. If performance degrades, switch to pagination.

### Development Setup

**Prerequisites**:
- Phase 1 hooks: `useGroups()`, `useInfiniteGroupArtifacts()` (enhancement needed)
- Existing ArtifactGrid, ArtifactList components
- Existing Filters component
- shadcn Select, Skeleton components

**Testing Setup**:
```bash
# Unit tests
pnpm test -- pages/groups.test.ts
pnpm test -- components/group-selector.test.ts
pnpm test -- components/group-artifact-grid.test.ts

# E2E happy path
pnpm test:e2e -- groups-page.spec.ts

# Performance profile (manual)
# Use Lighthouse or Chrome DevTools to verify ≤500ms load time
```

**Quality Gates**:
- [ ] /groups page renders and navigates correctly
- [ ] Group selector dropdown functional with API data
- [ ] Artifact grid displays correct artifacts for selected group
- [ ] Filters and view modes work correctly
- [ ] Empty states render properly
- [ ] Performance: groups load ≤200ms; artifacts ≤500ms
- [ ] ≥80% test coverage
- [ ] E2E test passes

---

## Completion Notes

_Fill in when phase is complete_

**What was built**:

**Key learnings**:

**Unexpected challenges**:

**Recommendations for next phase**:
