---
type: progress
prd: collections-groups-ux-enhancement
phase: 5
title: Group Filter Integration
status: completed
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 5
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- ui-engineer-enhanced
contributors: []
tasks:
- id: P5-T1
  description: Create GroupFilterSelect component with shadcn Select
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 2h
  priority: high
  model: sonnet
- id: P5-T2
  description: Integrate GroupFilterSelect into Filters component (collection page)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P5-T1
  estimated_effort: 1.5h
  priority: high
  model: sonnet
- id: P5-T3
  description: Integrate GroupFilterSelect into EntityFilters component (manage page)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P5-T1
  estimated_effort: 1.5h
  priority: high
  model: sonnet
- id: P5-T4
  description: Add conditional visibility logic (hide in All Collections view)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P5-T2
  - P5-T3
  estimated_effort: 1h
  priority: medium
  model: sonnet
- id: P5-T5
  description: Write unit tests for filter component (≥80% coverage)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P5-T1
  - P5-T2
  - P5-T3
  - P5-T4
  estimated_effort: 2h
  priority: high
  model: sonnet
parallelization:
  batch_1:
  - P5-T1
  batch_2:
  - P5-T2
  - P5-T3
  batch_3:
  - P5-T4
  batch_4:
  - P5-T5
  critical_path:
  - P5-T1
  - P5-T2
  - P5-T4
  - P5-T5
  estimated_total_time: 6.5h
blockers: []
success_criteria:
- id: SC-1
  description: Group filter dropdown appears on /collection page in specific collection
    context
  status: pending
- id: SC-2
  description: Group filter dropdown appears on /manage page in specific collection
    context
  status: pending
- id: SC-3
  description: Filter hidden when viewing All Collections or outside collection context
  status: pending
- id: SC-4
  description: Filter options populated from useGroups(collectionId) API
  status: pending
- id: SC-5
  description: 'Default value: All Groups (no filter applied)'
  status: pending
- id: SC-6
  description: Selecting group filters artifacts; URL updates with ?group=<id>
  status: pending
- id: SC-7
  description: Clearing filter removes ?group=<id> from URL
  status: pending
- id: SC-8
  description: Both Filters and EntityFilters have identical Group filter UX
  status: pending
- id: SC-9
  description: Filter state persists across page navigation (via URL params)
  status: pending
- id: SC-10
  description: Tooltip/help text explains filter availability
  status: pending
- id: SC-11
  description: ≥80% test coverage
  status: pending
files_modified:
- skillmeat/web/components/shared/group-filter-select.tsx
- skillmeat/web/components/collection/filters.tsx
- skillmeat/web/app/manage/components/entity-filters.tsx
- skillmeat/web/hooks/use-artifact-filters.ts
- skillmeat/web/__tests__/components/group-filter-select.test.ts
- skillmeat/web/__tests__/components/filters.test.ts
- skillmeat/web/__tests__/integration/collection-page.test.ts
progress: 100
updated: '2026-01-20'
---

# Collections & Groups UX Enhancement - Phase 5: Group Filter Integration

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/collections-groups-ux-enhancement/phase-5-progress.md -t P5-T1 -s completed
```

**Quick Reference for Task Orchestration**:

```python
# Batch 1
Task("ui-engineer-enhanced", "Create GroupFilterSelect component. File: components/shared/group-filter-select.tsx. Use shadcn Select, populate from useGroups hook, All Groups default.", model="sonnet")

# Batch 2 (parallel after batch 1)
Task("ui-engineer-enhanced", "Integrate into Filters component. File: components/collection/filters.tsx. Add GroupFilterSelect with conditional render for specific collection context.", model="sonnet")
Task("ui-engineer-enhanced", "Integrate into EntityFilters component. File: app/manage/components/entity-filters.tsx. Add GroupFilterSelect with same conditional logic.", model="sonnet")

# Batch 3 (sequential after batch 2)
Task("ui-engineer-enhanced", "Add conditional visibility logic. Files: components/collection/filters.tsx, app/manage/components/entity-filters.tsx. Use useCollectionContext to hide in All Collections view.", model="sonnet")

# Batch 4 (sequential - testing)
Task("ui-engineer-enhanced", "Write unit tests. Files: __tests__/components/group-filter-select.test.ts, __tests__/components/filters.test.ts, __tests__/integration/collection-page.test.ts. Test visibility, URL updates, filter application. ≥80% coverage.", model="sonnet")
```

---

## Objective

Add Group filter dropdown to existing filter bars on `/collection` and `/manage` pages. Users can filter artifacts by group membership when viewing a specific collection. The filter integrates seamlessly with existing filters (Type, Status, Scope, Sort) and respects URL state for bookmarkability.

---

## Implementation Notes

### Architectural Decisions

**Component Reuse**: Create a single `GroupFilterSelect` component used by both `Filters` and `EntityFilters`. This ensures:
- Consistent UX across pages
- Single source of truth for filter logic
- Easier testing and maintenance

**Conditional Visibility Pattern**:
```typescript
// In Filters and EntityFilters components
const { selectedCollectionId } = useCollectionContext();
const isSpecificCollection = selectedCollectionId && selectedCollectionId !== 'all';

{isSpecificCollection && (
  <GroupFilterSelect
    collectionId={selectedCollectionId}
    value={filters.groupId}
    onChange={(groupId) => onFilterChange({ ...filters, groupId })}
  />
)}
```

**URL State Management**: Filter value stored in URL query param `?group=<id>`:
```typescript
const router = useRouter();
const searchParams = useSearchParams();

const handleGroupChange = (groupId: string | undefined) => {
  const params = new URLSearchParams(searchParams);
  if (groupId) {
    params.set('group', groupId);
  } else {
    params.delete('group');
  }
  router.push(`?${params.toString()}`);
};
```

**Filter Interface Enhancement**:
```typescript
// In hooks/use-artifact-filters.ts or similar
export interface ArtifactFilters {
  type?: EntityType;
  status?: string;
  scope?: string;
  sort?: string;
  groupId?: string; // NEW
}
```

**Default Value**: "All Groups" option (value: `undefined` or `null`) clears filter.

### Patterns and Best Practices

**Reference Patterns**:
- Existing Filters component in `components/collection/filters.tsx`
- Existing EntityFilters component in `app/manage/components/entity-filters.tsx`
- Select usage patterns in `.claude/context/key-context/component-patterns.md`

**shadcn Select Pattern**:
```typescript
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

<Select value={value} onValueChange={onChange}>
  <SelectTrigger className="w-[180px]">
    <SelectValue placeholder="All Groups" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="">All Groups</SelectItem>
    {groups?.map(group => (
      <SelectItem key={group.id} value={group.id}>
        {group.name}
      </SelectItem>
    ))}
  </SelectContent>
</Select>
```

**Integration with Artifact Hooks**: Ensure `useInfiniteCollectionArtifacts` hook supports `groupId` filter parameter:
```typescript
export function useInfiniteCollectionArtifacts(
  collectionId: string,
  filters?: ArtifactFilters // Already includes groupId from interface enhancement
): UseInfiniteQueryResult<...>
```

### Known Gotchas

**URL Param Collision**: Ensure `group` param name doesn't conflict with other query params. Verify existing URL structure on `/collection` and `/manage` pages.

**Filter State Lost on Page Refresh**: URL query params persist state automatically. No additional localStorage needed.

**Cross-Page Filter Inconsistency**: Filters and EntityFilters must have identical UX. Use shared `GroupFilterSelect` component to enforce consistency.

**Empty Group List**: If collection has no groups, dropdown should show "No groups available" message. Disable Select or show placeholder.

**Tooltip/Help Text**: Add tooltip explaining filter: "Filter artifacts by group membership. Only available when viewing a specific collection."

**Performance**: Fetching groups for filter dropdown adds latency. Mitigation:
- Use `useGroups()` hook from Phase 1 (cached with 5min stale time)
- Lazy-load groups on filter dropdown open (Radix Select supports this)

### Development Setup

**Prerequisites**:
- Phase 1 hooks: `useGroups()` (must be complete)
- Existing Filters and EntityFilters components
- Existing artifact query hooks
- shadcn Select component

**Testing Setup**:
```bash
# Unit tests
pnpm test -- components/group-filter-select.test.ts
pnpm test -- components/filters.test.ts
pnpm test -- components/entity-filters.test.ts

# Integration tests
pnpm test -- integration/collection-page.test.ts
pnpm test -- integration/manage-page.test.ts

# E2E (optional)
pnpm test:e2e -- group-filter.spec.ts
```

**Quality Gates**:
- [ ] Group filter dropdown visible in correct contexts
- [ ] Filter hidden when viewing "All Collections"
- [ ] Dropdown populated with groups from current collection
- [ ] Selecting group filters artifacts in grid/list
- [ ] URL updates with ?group=<id> parameter
- [ ] Filter state persists across navigation
- [ ] Tooltip/help text explains filter
- [ ] ≥80% test coverage

---

## Completion Notes

_Fill in when phase is complete_

**What was built**:

**Key learnings**:

**Unexpected challenges**:

**Recommendations for next phase**:
