# Phase 4 Tasks: Groups Sidebar Page

**Phase**: 4 | **Duration**: 5-6 days | **Story Points**: 12 | **Assigned To**: frontend-developer (Opus)

---

## Overview

Phase 4 creates a dedicated `/groups` page accessible from the sidebar. Users can select a group and browse its artifacts using familiar grid/list views, filters, and sorting. This phase integrates components from Phases 1-3 and establishes the primary Groups entry point.

**Deliverables**:
- New `/groups` page with group selector
- Sidebar navigation item ("Groups")
- GroupSelector component for dropdown
- GroupArtifactGrid component for artifact display
- View mode toggle (Grid/List)
- ≥80% test coverage
- E2E happy path test

---

## Task P4-T1: Update Navigation Sidebar

**Type**: Feature | **Story Points**: 1 | **Estimated Time**: 2-3 hours

### Description

Add "Groups" tab to sidebar navigation under Collections section.

### Acceptance Criteria

- [x] File: `skillmeat/web/components/navigation.tsx`
- [x] Add Groups nav item under Collections section
- [x] Icon: FolderTree or similar icon (design decision)
- [x] Href: `/groups`
- [x] Navigation item appears in sidebar
- [x] Click navigates to /groups page
- [x] Active state highlights when on /groups

### Implementation

```tsx
// In navigation sidebar, Collections section
{ name: 'Groups', href: '/groups', icon: FolderTree }
```

### Test Cases

- [ ] Groups item visible in sidebar
- [ ] Click navigates to /groups
- [ ] Active state correct

---

## Task P4-T2: Create /groups Page Layout

**Type**: Feature | **Story Points**: 1.5 | **Estimated Time**: 4-5 hours

### Description

Create page structure for /groups at `skillmeat/web/app/groups/page.tsx`.

### Acceptance Criteria

- [x] File: `skillmeat/web/app/groups/page.tsx` (server component)
- [x] File: `skillmeat/web/app/groups/layout.tsx` (optional, for breadcrumb)
- [x] Accepts `searchParams` with optional `group` query param
- [x] Metadata: title "Groups | SkillMeat"
- [x] Server component wraps client components
- [x] Breadcrumb: Dashboard > Collections > Groups > [Group Name]
- [x] Placeholder for GroupsPageClient component

### Implementation

```tsx
// skillmeat/web/app/groups/page.tsx
export const metadata = {
  title: 'Groups | SkillMeat',
};

export default async function GroupsPage({
  searchParams,
}: {
  searchParams: Promise<{ group?: string }>;
}) {
  const params = await searchParams;
  return <GroupsPageClient selectedGroupId={params.group} />;
}
```

### Test Cases

- [ ] Page renders at /groups URL
- [ ] Query param `?group=id` captured
- [ ] Metadata correct
- [ ] No TypeScript errors

---

## Task P4-T3: Create GroupsPageClient Component

**Type**: Feature | **Story Points**: 2.5 | **Estimated Time**: 8-10 hours

### Description

Main client component managing page state: group selection, filters, view mode.

### Acceptance Criteria

- [x] Component: `skillmeat/web/app/groups/components/groups-page-client.tsx`
- [x] Uses `useCollectionContext()` to get selectedCollectionId
- [x] Manages state: selectedGroupId, viewMode, filters
- [x] Renders: GroupSelector, Filters, ViewModeToggle, GroupArtifactGrid
- [x] Syncs selectedGroupId to URL query param
- [x] Breadcrumb component shows full navigation path
- [x] Empty states: "No groups in collection", "Select a group"

### Implementation Pattern

```tsx
'use client';

import { useState } from 'react';
import { useCollectionContext } from '@/hooks';
import { GroupSelector } from './group-selector';
import { GroupArtifactGrid } from './group-artifact-grid';
import { Filters } from '@/components/collection/filters';
import { ViewModeToggle } from './view-mode-toggle';

interface GroupsPageClientProps {
  selectedGroupId?: string;
}

export function GroupsPageClient({ selectedGroupId }: GroupsPageClientProps) {
  const { selectedCollectionId } = useCollectionContext();
  const [groupId, setGroupId] = useState(selectedGroupId);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [filters, setFilters] = useState({});

  // Render page sections
  // Handle empty states
  // Sync groupId to URL
}
```

### Test Cases

- [ ] Component mounts and renders
- [ ] GroupSelector renders
- [ ] Empty states: no groups, no group selected
- [ ] State management: filter/view changes update grid
- [ ] URL sync: groupId in query params
- [ ] Breadcrumb shows correct path

### Quality Gates

- [ ] ≥80% coverage
- [ ] No TypeScript errors

---

## Task P4-T4: Create GroupSelector Component

**Type**: Feature | **Story Points**: 2 | **Estimated Time**: 6-8 hours

### Description

Dropdown component for selecting group from current collection.

### Acceptance Criteria

- [x] Component: `skillmeat/web/app/groups/components/group-selector.tsx`
- [x] Uses `useGroups(collectionId)` hook to fetch groups
- [x] Shows loading state while fetching
- [x] Shows empty state if no groups
- [x] Select dropdown with group options
- [x] Default label: "Select Group"
- [x] onChange callback fires with selected groupId
- [x] Selected group shows in dropdown
- [x] Accessible: proper Select semantics

### Implementation

```tsx
// skillmeat/web/app/groups/components/group-selector.tsx
'use client';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useGroups } from '@/hooks';
import { Skeleton } from '@/components/ui/skeleton';

interface GroupSelectorProps {
  collectionId: string;
  value?: string;
  onChange: (groupId: string) => void;
}

export function GroupSelector({
  collectionId,
  value,
  onChange,
}: GroupSelectorProps) {
  const { data: groups = [], isLoading, error } = useGroups(collectionId);

  if (isLoading) return <Skeleton className="h-10 w-32" />;
  if (error || !groups.length) return <p>No groups in this collection</p>;

  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger>
        <SelectValue placeholder="Select Group" />
      </SelectTrigger>
      <SelectContent>
        {groups.map(group => (
          <SelectItem key={group.id} value={group.id}>
            {group.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
```

### Test Cases

- [ ] Shows loading skeleton while fetching
- [ ] Displays "No groups" message when empty
- [ ] Renders all groups in dropdown
- [ ] Selection fires onChange callback
- [ ] Selected value displays
- [ ] Accessible

### Quality Gates

- [ ] ≥80% coverage
- [ ] Accessibility verified

---

## Task P4-T5: Create GroupArtifactGrid Component

**Type**: Feature | **Story Points**: 2.5 | **Estimated Time**: 8-10 hours

### Description

Display artifacts for selected group using existing ArtifactGrid/ArtifactList components.

### Acceptance Criteria

- [x] Component: `skillmeat/web/app/groups/components/group-artifact-grid.tsx`
- [x] Accepts `groupId` prop
- [x] Accepts optional `filters` prop
- [x] Accepts `viewMode` ('grid' | 'list')
- [x] Uses `useInfiniteGroupArtifacts()` hook (Phase 1 enhancement)
- [x] Renders ArtifactGrid or ArtifactList based on viewMode
- [x] Infinite scroll: fetchNextPage on scroll to bottom
- [x] Loading state: skeleton while initial fetch
- [x] Empty state: "No artifacts in this group"
- [x] Error state: graceful error message

### Implementation Pattern

```tsx
// skillmeat/web/app/groups/components/group-artifact-grid.tsx
'use client';

import { useInfiniteGroupArtifacts } from '@/hooks'; // Phase 1 enhancement
import { ArtifactGrid } from '@/components/collection/artifact-grid';
import { ArtifactList } from '@/components/collection/artifact-list';

interface GroupArtifactGridProps {
  groupId: string;
  viewMode: 'grid' | 'list';
  filters?: ArtifactFilters;
}

export function GroupArtifactGrid({
  groupId,
  viewMode,
  filters,
}: GroupArtifactGridProps) {
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useInfiniteGroupArtifacts(groupId, filters);

  // Combine pages
  // Handle infinite scroll
  // Render based on viewMode
  // Handle empty/error states
}
```

### Hook Enhancement (Phase 1)

**File**: `skillmeat/web/hooks/use-groups.ts`

Add new hook:
```typescript
export function useInfiniteGroupArtifacts(
  groupId: string,
  filters?: ArtifactFilters
): UseInfiniteQueryResult<...> {
  // Fetch artifacts for group with infinite query
  // Support filtering by type, status, scope
}
```

### Test Cases

- [ ] Fetches and displays artifacts
- [ ] Infinite scroll loads more artifacts
- [ ] Empty state shows correctly
- [ ] Grid/List view toggle works
- [ ] Filters applied correctly
- [ ] Error state handled gracefully

### Quality Gates

- [ ] ≥80% coverage
- [ ] Performance: artifacts load ≤500ms

---

## Task P4-T6: Create ViewModeToggle Component

**Type**: Feature | **Story Points**: 1 | **Estimated Time**: 3-4 hours

### Description

Grid/List view mode toggle, reusing existing pattern from /collection page.

### Acceptance Criteria

- [x] Component: `skillmeat/web/app/groups/components/view-mode-toggle.tsx`
- [x] Two buttons: Grid icon, List icon
- [x] Active state highlights current mode
- [x] onClick fires onChange callback
- [x] State persists in localStorage (key: `groups-view-mode`)
- [x] Accessible: proper button semantics

### Implementation

```tsx
'use client';

import { Button } from '@/components/ui/button';
import { Grid, List } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ViewModeToggleProps {
  value: 'grid' | 'list';
  onChange: (mode: 'grid' | 'list') => void;
}

export function ViewModeToggle({ value, onChange }: ViewModeToggleProps) {
  return (
    <div className="flex gap-1 border rounded-md p-1">
      <Button
        variant={value === 'grid' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => onChange('grid')}
        aria-label="Grid view"
      >
        <Grid className="h-4 w-4" />
      </Button>
      <Button
        variant={value === 'list' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => onChange('list')}
        aria-label="List view"
      >
        <List className="h-4 w-4" />
      </Button>
    </div>
  );
}
```

### Test Cases

- [ ] Toggle buttons render
- [ ] Click changes mode
- [ ] Active state highlights
- [ ] localStorage persists selection
- [ ] Accessible

---

## Task P4-T7: Integrate Filters Component

**Type**: Feature | **Story Points**: 1 | **Estimated Time**: 3-4 hours

### Description

Reuse existing Filters component on /groups page (Type, Status, Scope, Sort). No Group filter on /groups (only for /collection and /manage).

### Acceptance Criteria

- [x] Import `Filters` component from `@/components/collection/filters.tsx`
- [x] Render in GroupsPageClient
- [x] Filters: Type, Status, Scope, Sort
- [x] No Group filter (redundant on /groups page)
- [x] onChange callback updates filters state
- [x] Filters passed to GroupArtifactGrid

### Implementation

```tsx
// In GroupsPageClient render
<Filters
  value={filters}
  onChange={setFilters}
/>
```

### Test Cases

- [ ] Filters render correctly
- [ ] Selection updates grid
- [ ] URL params sync with filters

---

## Task P4-T8: Write Unit & E2E Tests

**Type**: Testing | **Story Points**: 2 | **Estimated Time**: 6-8 hours

### Description

Unit tests for page components and E2E happy path test.

### Test Files

- `skillmeat/web/__tests__/app/groups/page.test.ts`
- `skillmeat/web/__tests__/app/groups/components/*.test.ts`
- `skillmeat/web/tests/groups-page.spec.ts` (E2E)

### Test Cases

**Unit Tests**:
- [ ] Page renders with searchParams
- [ ] GroupSelector renders and selections work
- [ ] GroupArtifactGrid displays artifacts
- [ ] ViewModeToggle works
- [ ] Filters integrate correctly
- [ ] Empty states show properly
- [ ] Error states handled

**E2E Test (Happy Path)**:
```
1. Navigate to /groups
2. VERIFY: page loads, sidebar item highlighted
3. VERIFY: collection context available (show groups from current collection)
4. Select group from dropdown
5. VERIFY: artifact grid updates with group's artifacts
6. Toggle view mode to List
7. VERIFY: list view displays
8. Apply Type filter
9. VERIFY: grid shows only filtered artifacts
10. Scroll to bottom
11. VERIFY: infinite scroll loads more artifacts
```

### Coverage Target

- Components: ≥80%
- Page logic: ≥80%

---

## Task P4-T9: Performance Profiling

**Type**: Quality Assurance | **Story Points**: 1 | **Estimated Time**: 3-4 hours

### Description

Profile page load and artifact rendering performance.

### Acceptance Criteria

- [x] Groups list fetch: ≤200ms
- [x] Artifact initial load: ≤500ms
- [x] Infinite scroll: no jank (60 fps)
- [x] Memory usage: no leaks on scroll
- [x] Lighthouse score: ≥80

### Quality Gates

- [ ] Performance targets met
- [ ] Ready for Phase 5

---

## Task P4-T10: Code Review & Documentation

**Type**: Quality Assurance | **Story Points**: 1 | **Estimated Time**: 3-4 hours

### Description

Final review and handoff for Phase 5.

### Acceptance Criteria

- [x] Self-review: conventions followed
- [x] Peer review: 1+ approval
- [x] TypeScript/ESLint: zero errors
- [ ] JSDoc complete
- [ ] No breaking changes
- [ ] Integration test: works with all previous phases

---

## Definition of Done

Phase 4 complete when:

1. **Code**:
   - [x] /groups page created and routable
   - [x] GroupSelector component created
   - [x] GroupArtifactGrid component created
   - [x] ViewModeToggle component created
   - [x] Filters integrated
   - [x] Sidebar item added

2. **Testing**:
   - [x] ≥80% unit test coverage
   - [x] E2E happy path test passing
   - [x] Performance verified

3. **Quality**:
   - [x] WCAG 2.1 AA verified
   - [x] TypeScript/ESLint checks pass
   - [x] Code review approved

---

## Handoff to Phase 5

Phase 5 implements Group filter on /collection and /manage pages. Key items:

1. **GroupSelector pattern** — Can be reused in Filters for phase 5
2. **Group fetch performance** — Phase 5 filter should match /groups page load time
3. **Integration test** — Phase 5 must verify filter/page consistency

---

**End of Phase 4 Tasks**

Next: Phase 5 - Group Filter Integration
