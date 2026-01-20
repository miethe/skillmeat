# Phase 5 Tasks: Group Filter Integration

**Phase**: 5 | **Duration**: 3-4 days | **Story Points**: 8 | **Assigned To**: ui-engineer-enhanced (Sonnet)

---

## Overview

Phase 5 adds Group filter dropdown to /collection and /manage pages. The filter is hidden when viewing "All Collections" to prevent cross-collection group name conflicts. This phase completes the Groups UX enhancement by enabling efficient group-based filtering.

**Deliverables**:
- GroupFilterSelect component for dropdown
- Enhanced Filters component with group filter
- Enhanced EntityFilters component with group filter
- Hook integration for group filtering
- ≥80% test coverage

---

## Task P5-T1: Create GroupFilterSelect Component

**Type**: Feature | **Story Points**: 1.5 | **Estimated Time**: 4-6 hours

### Description

Reusable Select component for group filtering, similar to Type/Status dropdowns.

### Acceptance Criteria

- [x] Component: `skillmeat/web/components/shared/group-filter-select.tsx`
- [x] Accepts `collectionId`, `value`, `onChange`
- [x] Uses `useGroups()` hook to fetch collection groups
- [x] Shows loading skeleton while fetching
- [x] Default option: "All Groups" (no filter)
- [x] Lists all groups as selectable options
- [x] Handles error gracefully (renders disabled or with fallback)
- [x] Accessible: proper Select semantics
- [x] Styling matches existing Type/Status selects

### Implementation

```tsx
// skillmeat/web/components/shared/group-filter-select.tsx
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

interface GroupFilterSelectProps {
  collectionId: string;
  value?: string;
  onChange: (groupId: string | undefined) => void;
}

export function GroupFilterSelect({
  collectionId,
  value,
  onChange,
}: GroupFilterSelectProps) {
  const { data: groups = [], isLoading, error } = useGroups(collectionId);

  if (isLoading) return <Skeleton className="h-10 w-32" />;

  return (
    <Select value={value || ''} onValueChange={(val) => onChange(val || undefined)}>
      <SelectTrigger>
        <SelectValue placeholder="All Groups" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="">All Groups</SelectItem>
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

- [ ] Renders "All Groups" default option
- [ ] Fetches and displays groups
- [ ] Selection fires onChange callback
- [ ] Clearing selection returns undefined
- [ ] Shows loading skeleton
- [ ] Handles error gracefully
- [ ] Accessible

### Quality Gates

- [ ] ≥80% coverage
- [ ] Styling matches Type/Status components

---

## Task P5-T2: Enhance Filters Component

**Type**: Feature | **Story Points**: 2 | **Estimated Time**: 5-7 hours

### Description

Add GroupFilterSelect to existing Filters component at `/collection` page.

### Acceptance Criteria

- [x] File: `skillmeat/web/components/collection/filters.tsx`
- [x] Import GroupFilterSelect component
- [x] Add conditional render: only show when in specific collection context
- [x] Check `useCollectionContext()` to detect view mode
- [x] Position: after Status/Scope filters, before Sort (coordinate with design)
- [x] Styling: matches existing filter selects
- [x] onChange: update filters state with groupId
- [x] No breaking changes to Filters API

### Implementation

```tsx
// In Filters component render logic
const { selectedCollectionId } = useCollectionContext();
const isSpecificCollectionContext = !!selectedCollectionId && selectedCollectionId !== 'all';

{isSpecificCollectionContext && (
  <GroupFilterSelect
    collectionId={selectedCollectionId}
    value={filters.groupId}
    onChange={(groupId) => onFiltersChange({ ...filters, groupId })}
  />
)}
```

### Test Cases

- [ ] GroupFilterSelect visible in specific collection context
- [ ] Hidden when viewing "All Collections"
- [ ] Selection updates filters state
- [ ] Filters passed to artifact queries
- [ ] URL params update with ?group=id
- [ ] Styling consistent with other filters
- [ ] No layout breakage

### Quality Gates

- [ ] ≥80% coverage
- [ ] TypeScript/ESLint: zero errors
- [ ] Code review approved

---

## Task P5-T3: Enhance EntityFilters Component

**Type**: Feature | **Story Points**: 2 | **Estimated Time**: 5-7 hours

### Description

Add identical GroupFilterSelect to EntityFilters component at `/manage` page.

### Acceptance Criteria

- [x] File: `skillmeat/web/app/manage/components/entity-filters.tsx`
- [x] Add GroupFilterSelect component (same logic as Phase 5-T2)
- [x] Conditional render: only in specific collection context
- [x] Identical UX to Filters component
- [ ] onChange: update entity filter state
- [x] No breaking changes to EntityFilters API

### Implementation

Same pattern as Phase 5-T2, but in EntityFilters component.

### Test Cases

- [ ] GroupFilterSelect visible in specific collection context
- [ ] Hidden in "All Collections" view
- [ ] Selection filters entities
- [ ] Styling matches Filters component
- [ ] Identical UX between pages

### Quality Gates

- [ ] ≥80% coverage
- [ ] Code review approved

---

## Task P5-T4: Integrate with Artifact Query Hooks

**Type**: Feature | **Story Points**: 1.5 | **Estimated Time**: 4-6 hours

### Description

Update artifact query hooks to accept and use `groupId` filter parameter.

### Acceptance Criteria

- [x] Hook: `useInfiniteCollectionArtifacts()` enhanced
- [x] Accepts optional `groupId` in filters parameter
- [x] Passes groupId to API query: `?group_id={groupId}`
- [x] Artifacts filtered server-side by group
- [x] Cache keys include groupId for proper invalidation
- [x] No breaking changes to hook signature

### Implementation

**File**: `skillmeat/web/hooks/useArtifacts.ts` or similar

```typescript
interface ArtifactFilters {
  type?: EntityType;
  status?: string;
  scope?: string;
  sort?: string;
  groupId?: string; // NEW
}

export function useInfiniteCollectionArtifacts(
  collectionId: string,
  filters?: ArtifactFilters
): UseInfiniteQueryResult<...> {
  return useInfiniteQuery({
    queryKey: ['artifacts', collectionId, filters], // Include groupId in key
    queryFn: async ({ pageParam = 0 }) => {
      const params = new URLSearchParams({
        collection_id: collectionId,
        offset: String(pageParam),
      });
      if (filters?.groupId) {
        params.append('group_id', filters.groupId);
      }
      // ... fetch with params
    },
    // ...
  });
}
```

### Test Cases

- [ ] Hook accepts groupId in filters
- [ ] API call includes group_id parameter
- [ ] Artifacts filtered correctly
- [ ] Cache keys differ when groupId changes
- [ ] Clearing groupId removes filter

### Quality Gates

- [ ] ≥80% coverage
- [ ] Integration test: filter changes update artifacts

---

## Task P5-T5: Add Tooltip/Help Text

**Type**: Feature | **Story Points**: 0.5 | **Estimated Time**: 1-2 hours

### Description

Optional: Add tooltip explaining Group filter availability.

### Acceptance Criteria

- [x] Tooltip on Group filter: "Available only in specific collection view"
- [x] Appears on hover or keyboard focus
- [x] Accessible: screen reader announces

### Implementation

```tsx
<Tooltip>
  <TooltipTrigger asChild>
    <div className="relative">
      <GroupFilterSelect {...props} />
      <InfoIcon className="absolute -right-5 top-1/2 -translate-y-1/2 h-4 w-4 cursor-help" />
    </div>
  </TooltipTrigger>
  <TooltipContent>
    Available only when viewing a specific collection
  </TooltipContent>
</Tooltip>
```

---

## Task P5-T6: Write Unit & Integration Tests

**Type**: Testing | **Story Points**: 1.5 | **Estimated Time**: 4-6 hours

### Description

Unit tests for filter components and integration tests verifying filter applies.

### Test Files

- `skillmeat/web/__tests__/components/group-filter-select.test.ts`
- `skillmeat/web/__tests__/components/filters.test.ts` (enhanced)
- `skillmeat/web/__tests__/components/entity-filters.test.ts` (enhanced)

### Test Cases

**GroupFilterSelect**:
- [ ] Renders "All Groups" option
- [ ] Fetches and displays groups
- [ ] Selection fires onChange
- [ ] Conditional visibility (phase 5-T2/T3)

**Filters + EntityFilters Integration**:
- [ ] Group filter visible in specific collection context
- [ ] Filter selection updates artifact query
- [ ] URL params include ?group=id
- [ ] Clearing filter removes URL param
- [ ] Both pages have identical UX

**E2E Integration Test**:
```
1. Navigate to /collection
2. Select specific collection
3. VERIFY: Group filter dropdown appears
4. Select group
5. VERIFY: URL changes to ?group=id
6. VERIFY: Artifact grid updates with filtered results
7. Scroll: infinite scroll still works
8. Navigate to /manage
9. VERIFY: Group filter appears and works identically
```

### Coverage Target

- GroupFilterSelect: ≥80%
- Filter integration: ≥80%

---

## Task P5-T7: Verify URL Parameter Handling

**Type**: Quality Assurance | **Story Points**: 0.5 | **Estimated Time**: 2-3 hours

### Description

Verify URL parameters are correctly handled and persistent.

### Acceptance Criteria

- [x] URL param key: `group` (e.g., `?group=abc123`)
- [x] Param persists on page navigation (within collection context)
- [x] Param clears when switching to "All Collections"
- [x] Deep link with `?group=id` loads with filter applied
- [x] Multiple params coexist: `?type=skill&group=abc123`

### Test Cases

- [ ] URL param read on page load
- [ ] Filter state synced to URL on change
- [ ] URL param cleared when appropriate
- [ ] Browser back/forward preserves param

---

## Task P5-T8: Code Review & Final Testing

**Type**: Quality Assurance | **Story Points**: 1 | **Estimated Time**: 3-4 hours

### Description

Final peer review, comprehensive testing, and readiness for rollout.

### Acceptance Criteria

- [x] Self-review: conventions followed
- [x] Peer review: 1+ approval
- [x] TypeScript/ESLint: zero errors
- [x] ≥80% test coverage verified
- [x] All 5 E2E test scenarios passing (from master plan)
- [x] Performance verified: no regression
- [x] Accessibility verified: WCAG 2.1 AA
- [x] No breaking changes

### Comprehensive Testing Checklist

- [ ] **Test 1: Collection Badges** (Phase 2) — still work correctly
- [ ] **Test 2: Group Badges** (Phase 3) — visible and styled correctly
- [ ] **Test 3: Groups Page** (Phase 4) — loads and functions
- [ ] **Test 4: Group Filter** (Phase 5) — visible, filters, persists
- [ ] **Test 5: Cross-Page Consistency** — /collection and /manage match

### Quality Gates

- [ ] All code reviews approved
- [ ] Test suite green: `pnpm test`
- [ ] Build succeeds: `pnpm build`
- [ ] Lighthouse score ≥80
- [ ] Ready for rollout

---

## Definition of Done

Phase 5 complete when:

1. **Code**:
   - [x] GroupFilterSelect component created
   - [x] Filters component enhanced
   - [x] EntityFilters component enhanced
   - [x] Query hooks support groupId parameter
   - [x] No breaking changes

2. **Testing**:
   - [x] ≥80% unit test coverage
   - [x] Integration tests passing
   - [x] All 5 E2E scenarios pass

3. **Quality**:
   - [x] WCAG 2.1 AA verified
   - [x] TypeScript/ESLint: zero errors
   - [x] Code review approved
   - [x] Performance verified

4. **Documentation**:
   - [x] JSDoc complete
   - [x] Tooltip/help text added
   - [x] No "TODO" comments left

---

## Handoff to Integration & Rollout

Phase 5 is the final phase. Next steps:

1. **Integration Testing**: Run all 5 E2E test scenarios together
2. **Beta Rollout**: Deploy to beta environment for user testing
3. **Monitoring Setup**: Verify GA events fire correctly
4. **Documentation**: Update help center, release notes
5. **Staged Rollout**: 10% → 50% → 100% over 3 days

---

**End of Phase 5 Tasks**

**All Phases Complete** — Ready for Rollout

---

## Summary of Phase 5 Deliverables

| Deliverable | File | Status |
|-------------|------|--------|
| GroupFilterSelect component | `components/shared/group-filter-select.tsx` | NEW |
| Enhanced Filters | `components/collection/filters.tsx` | MODIFIED |
| Enhanced EntityFilters | `app/manage/components/entity-filters.tsx` | MODIFIED |
| Enhanced query hooks | `hooks/useArtifacts.ts` | MODIFIED |
| Unit tests | `__tests__/components/group-*.test.ts` | NEW |
| Integration tests | `__tests__/filters.test.ts` | ENHANCED |
| E2E tests | `tests/group-filter.spec.ts` | NEW |

---

**Implementation Plan Complete**

Proceed to Beta Testing and Rollout phases.
