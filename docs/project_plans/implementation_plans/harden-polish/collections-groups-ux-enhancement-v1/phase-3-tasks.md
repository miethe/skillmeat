# Phase 3 Tasks: Group Badges & Modal Enhancement

**Phase**: 3 | **Duration**: 4-5 days | **Story Points**: 9 | **Assigned To**: ui-engineer-enhanced (Opus)

---

## Overview

Phase 3 adds group membership badges to cards (in specific collection context) and enhances the ModalCollectionsTab to display groups for each collection. This phase reuses the badge pattern from Phase 2 and introduces the `GroupBadgeRow` component.

**Deliverables**:
- GroupBadgeRow component for card group badges
- GroupsDisplay component for modal Collections tab
- Enhanced UnifiedCard with group badge rendering
- Enhanced ModalCollectionsTab with groups display
- ≥80% test coverage
- WCAG 2.1 AA compliance

---

## Task P3-T1: Create GroupBadgeRow Component

**Type**: Feature | **Story Points**: 2.5 | **Estimated Time**: 6-8 hours

### Description

Create component for rendering group badges on cards when in specific collection context. Reuses CollectionBadgeStack pattern from Phase 2.

### Acceptance Criteria

- [x] Component created at `skillmeat/web/components/shared/group-badge-row.tsx`
- [x] Accepts `artifactId`, `collectionId`, optional `maxBadges`
- [x] Calls `useArtifactGroups()` hook from Phase 1
- [x] Renders loading skeleton while fetching groups
- [x] Handles error gracefully: returns null (no badge shown)
- [x] Renders group badges with tertiary color (distinct from collection badges)
- [x] Max 2 badges + "+N more" pattern (matches Phase 2)
- [x] Tooltip on "+N more" shows full group list
- [x] Each badge has aria-label
- [x] No custom styles

### Implementation Pattern

```tsx
// skillmeat/web/components/shared/group-badge-row.tsx
'use client';

import { useArtifactGroups } from '@/hooks';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

interface GroupBadgeRowProps {
  artifactId: string;
  collectionId: string;
  maxBadges?: number;
}

export function GroupBadgeRow({
  artifactId,
  collectionId,
  maxBadges = 2,
}: GroupBadgeRowProps) {
  const { data: groups = [], isLoading, error } = useArtifactGroups(
    artifactId,
    collectionId
  );

  if (isLoading) return <Skeleton className="h-6 w-24" />;
  if (error || !groups.length) return null;

  // Render similar to CollectionBadgeStack but with tertiary color
  // and group names instead of collection names
}
```

### Test Cases

- [ ] Fetches groups for artifact-collection pair
- [ ] Shows loading skeleton while fetching
- [ ] Returns null on error (graceful fallback)
- [ ] Renders group badges with tertiary color
- [ ] Max 2 badges + "+N more" pattern
- [ ] aria-labels present and correct
- [ ] Snapshot: 2 groups, 3+ groups

### Quality Gates

- [ ] ≥80% coverage
- [ ] Snapshot test baseline created
- [ ] Accessibility verified

---

## Task P3-T2: Enhance UnifiedCard for Group Badges

**Type**: Feature | **Story Points**: 2 | **Estimated Time**: 6-8 hours

### Description

Modify UnifiedCard to render GroupBadgeRow when in specific collection context.

### Acceptance Criteria

- [x] Import and render GroupBadgeRow in UnifiedCard
- [x] Render only when `selectedCollectionId` exists (not "All Collections")
- [x] Render below type indicator bar or next to collection badges (coordinate with design)
- [x] Pass `artifactId` and `collectionId` to GroupBadgeRow
- [x] No performance regression (≤50ms per card total with both badges)
- [x] Collection and Group badges don't conflict visually

### Implementation

```tsx
// In UnifiedCard render logic
const { selectedCollectionId } = useCollectionContext();
const isSpecificCollectionContext = !!selectedCollectionId && selectedCollectionId !== 'all';

{isSpecificCollectionContext && (
  <GroupBadgeRow
    artifactId={entity.id}
    collectionId={selectedCollectionId}
  />
)}
```

### Test Cases

- [ ] Group badges render in specific collection view
- [ ] Group badges hidden in "All Collections" view
- [ ] No performance regression (total card render ≤50ms)
- [ ] Both collection and group badges visible when both present
- [ ] Styling doesn't conflict

### Quality Gates

- [ ] ≥80% coverage
- [ ] Performance verified (profiled)
- [ ] Code review approved

---

## Task P3-T3: Create GroupsDisplay Component for Modal

**Type**: Feature | **Story Points**: 1.5 | **Estimated Time**: 4-6 hours

### Description

Create component for displaying groups in ModalCollectionsTab. Shows groups as badges or comma-separated list for each collection.

### Acceptance Criteria

- [x] Component created at `skillmeat/web/components/entity/groups-display.tsx`
- [x] Accepts `collectionId` parameter
- [x] Calls `useGroups()` hook to fetch collection's groups
- [x] Shows loading skeleton while fetching
- [x] Displays "No groups" message if collection has no groups
- [x] Renders groups as badges or comma-separated list (design decision)
- [x] Uses same tertiary color as GroupBadgeRow
- [x] Handles error gracefully

### Implementation

```tsx
// skillmeat/web/components/entity/groups-display.tsx
'use client';

import { useGroups } from '@/hooks';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

interface GroupsDisplayProps {
  collectionId: string;
}

export function GroupsDisplay({ collectionId }: GroupsDisplayProps) {
  const { data: groups = [], isLoading, error } = useGroups(collectionId);

  if (isLoading) return <Skeleton className="h-6 w-32" />;
  if (error) return null;
  if (!groups.length) return <span className="text-sm text-muted-foreground">No groups</span>;

  return (
    <div className="flex flex-wrap gap-1">
      {groups.map(group => (
        <Badge key={group.id} variant="secondary">
          {group.name}
        </Badge>
      ))}
    </div>
  );
}
```

### Test Cases

- [ ] Fetches groups for collection
- [ ] Shows loading skeleton
- [ ] Displays "No groups" message when empty
- [ ] Renders badges with group names
- [ ] Handles error gracefully

### Quality Gates

- [ ] ≥80% coverage
- [ ] Snapshot tests created

---

## Task P3-T4: Enhance ModalCollectionsTab Component

**Type**: Feature | **Story Points**: 2 | **Estimated Time**: 6-8 hours

### Description

Replace placeholder in ModalCollectionsTab (lines 197-198) with GroupsDisplay component. Update tab layout to show groups for each collection.

### Acceptance Criteria

- [x] Find placeholder at lines 197-198 in modal-collections-tab.tsx
- [x] Replace with GroupsDisplay component rendering
- [x] Add heading: "Groups in {collection-name}"
- [x] Maintain existing collection layout and styling
- [x] Groups section visible for all collections (empty state handled)
- [x] Modal loading state respected
- [x] No breaking changes to ModalCollectionsTab API

### Implementation

**File**: `skillmeat/web/components/entity/modal-collections-tab.tsx`

Replace lines 197-198:
```tsx
// OLD (placeholder):
{/* Groups within collection - Placeholder for Phase 5 */}

// NEW:
<div className="mt-3 space-y-1.5">
  <h4 className="text-xs font-semibold uppercase text-muted-foreground">
    Groups in {collection.name}
  </h4>
  <GroupsDisplay collectionId={collection.id} />
</div>
```

### Test Cases

- [ ] Placeholder replaced with GroupsDisplay
- [ ] Groups render for each collection
- [ ] Modal layout not broken
- [ ] Loading state handled
- [ ] Snapshot: tab with groups displayed

### Quality Gates

- [ ] ≥80% coverage
- [ ] No visual regression in modal
- [ ] Code review approved

---

## Task P3-T5: Coordinate Badge Styling (Collections vs. Groups)

**Type**: Design | **Story Points**: 1 | **Estimated Time**: 2-4 hours

### Description

Ensure group badges visually distinct from collection badges while maintaining design consistency.

### Acceptance Criteria

- [x] Group badges: tertiary color (different from collection secondary color)
- [x] Group badges: same shape/size as collection badges
- [x] Color contrast: ≥4.5:1 ratio
- [x] Spacing consistent with collection badges
- [x] Design reviewed and approved

### Quality Gates

- [ ] Design approved
- [ ] Styling consistent across card and modal

---

## Task P3-T6: Write Unit & Snapshot Tests

**Type**: Testing | **Story Points**: 1.5 | **Estimated Time**: 4-6 hours

### Description

Unit tests and snapshots for Phase 3 components.

### Test Structure

**Files**:
- `skillmeat/web/__tests__/components/group-badge-row.test.ts` (new)
- `skillmeat/web/__tests__/components/groups-display.test.ts` (new)
- `skillmeat/web/__tests__/components/modal-collections-tab.test.ts` (enhanced)
- `skillmeat/web/__tests__/components/unified-card.test.ts` (enhanced)

### Test Cases

**GroupBadgeRow**:
- [ ] Fetches groups for artifact
- [ ] Shows loading skeleton
- [ ] Returns null on error
- [ ] Renders badges
- [ ] Max 2 badges + "+N more"
- [ ] Snapshot: with groups

**GroupsDisplay**:
- [ ] Fetches collection groups
- [ ] Shows "No groups" message
- [ ] Renders badges
- [ ] Snapshot: with/without groups

**ModalCollectionsTab**:
- [ ] Groups display visible
- [ ] Snapshot: tab with groups

### Coverage Target

- GroupBadgeRow: ≥85%
- GroupsDisplay: ≥80%
- ModalCollectionsTab groups section: ≥80%

---

## Task P3-T7: Performance & Accessibility Validation

**Type**: Quality Assurance | **Story Points**: 1 | **Estimated Time**: 3-4 hours

### Description

Profile card performance with both collection and group badges. Validate accessibility.

### Acceptance Criteria

- [x] Card render time ≤50ms per card (with both badge types)
- [x] Modal load time ≤300ms (groups section included)
- [x] Axe audit: zero critical issues
- [x] Keyboard navigation: all badges accessible
- [x] Screen reader: badges announced correctly

### Quality Gates

- [ ] Performance baseline met
- [ ] Accessibility verified
- [ ] Ready for Phase 4

---

## Task P3-T8: Code Review & Documentation

**Type**: Quality Assurance | **Story Points**: 1 | **Estimated Time**: 3-4 hours

### Description

Final review and handoff documentation for Phase 4.

### Acceptance Criteria

- [x] Self-review: conventions followed
- [x] Peer review: 1+ approval
- [x] TypeScript strict mode: zero errors
- [x] ESLint: zero warnings
- [x] JSDoc complete
- [x] No breaking changes
- [x] Integration test: works with Phase 1 hooks

### Quality Gates

- [ ] Code review approved
- [ ] Ready for Phase 4

---

## Definition of Done

Phase 3 complete when:

1. **Code**:
   - [x] GroupBadgeRow created and exported
   - [x] GroupsDisplay created and exported
   - [x] UnifiedCard enhanced with group badges
   - [x] ModalCollectionsTab placeholder replaced
   - [x] No breaking changes

2. **Testing**:
   - [x] ≥80% coverage
   - [x] All tests passing
   - [x] Snapshot baseline created
   - [x] Performance verified (≤50ms per card)

3. **Quality**:
   - [x] WCAG 2.1 AA verified
   - [x] TypeScript/ESLint checks pass
   - [x] Code review approved

---

## Handoff to Phase 4

Phase 4 builds dedicated /groups page. Key items:

1. **GroupsDisplay component** — Used as-is in /groups page group selector
2. **Group badge styling** — /groups page artifacts inherit same badge styling
3. **Performance baseline** — /groups page must load groups ≤200ms, artifacts ≤500ms

---

**End of Phase 3 Tasks**

Next: Phase 4 - Groups Sidebar Page
