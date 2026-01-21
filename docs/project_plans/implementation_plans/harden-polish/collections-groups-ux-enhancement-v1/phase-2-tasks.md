# Phase 2 Tasks: Collection Badges on Cards

**Phase**: 2 | **Duration**: 4-5 days | **Story Points**: 10 | **Assigned To**: ui-engineer-enhanced (Opus)

---

## Overview

Phase 2 adds visual collection membership indicators to the UnifiedCard component. When users view "All Collections," cards display which collections contain each artifact (excluding the default collection). This phase establishes the badge rendering pattern reused in Phase 3 (group badges).

**Deliverables**:
- CollectionBadgeStack component for rendering collection badges
- Enhanced UnifiedCard with badge rendering logic
- Hover tooltip with full collection list
- ≥80% test coverage with snapshot tests
- WCAG 2.1 AA accessibility compliance

---

## Task P2-T1: Create CollectionBadgeStack Component

**Type**: Feature | **Story Points**: 2.5 | **Estimated Time**: 6-8 hours

### Description

Create a reusable component for rendering collection membership badges on cards. Handles max 2 badges + "X more..." pattern with hover tooltip.

### Acceptance Criteria

- [x] Component created at `skillmeat/web/components/shared/collection-badge-stack.tsx`
- [x] Accepts `collections: Array<{ id: string; name: string }>` prop
- [x] Accepts optional `maxBadges: number` prop (default: 2)
- [x] Filters out 'default' collection from display
- [x] Renders up to `maxBadges` collection names as Badge components
- [x] If more collections than maxBadges, shows "+N more" badge
- [x] Hover on "+N more" displays tooltip with full list
- [x] Badge styling: secondary color from shadcn palette
- [x] Each badge has aria-label for accessibility
- [x] Keyboard navigable (Tab through badges)
- [x] No custom styles; uses Tailwind + shadcn classes

### Component Structure

```tsx
// skillmeat/web/components/shared/collection-badge-stack.tsx
'use client';

import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface Collection {
  id: string;
  name: string;
}

interface CollectionBadgeStackProps {
  collections: Collection[];
  maxBadges?: number;
}

export function CollectionBadgeStack({
  collections,
  maxBadges = 2,
}: CollectionBadgeStackProps) {
  // Filter out 'default' collection
  // Show max maxBadges names
  // Show "+N more" badge if necessary
  // Tooltip with full list on "+N more" hover
}
```

### Test Cases

- [ ] Filters out 'default' collection
- [ ] Shows first 2 collections by default
- [ ] Shows "+3 more" badge when 5 collections present
- [ ] Tooltip content includes filtered collections
- [ ] Accessibility: each badge has aria-label
- [ ] Keyboard navigation works
- [ ] Empty collections array renders nothing
- [ ] Single collection renders single badge

### Quality Gates

- [ ] Snapshot test baseline created
- [ ] ≥80% coverage
- [ ] Accessibility audit passes
- [ ] No performance regressions

---

## Task P2-T2: Enhance UnifiedCard Component

**Type**: Feature | **Story Points**: 3 | **Estimated Time**: 8-10 hours

### Description

Modify UnifiedCard component to render CollectionBadgeStack when viewing "All Collections." Add conditional logic to detect view mode and only render badges when appropriate.

### Acceptance Criteria

- [x] Import `useCollectionContext()` hook in UnifiedCard
- [x] Check context to determine if in "All Collections" view
- [x] Add CollectionBadgeStack render logic below type indicator bar
- [x] Render only if `entity.collections` array exists and is non-empty
- [x] Don't break existing card layout or styling
- [x] Keep card render time ≤50ms per card (profile with React DevTools)
- [x] Collection badges disappear when selecting specific collection
- [x] No breaking changes to UnifiedCard API

### Implementation Details

**File**: `skillmeat/web/components/shared/unified-card.tsx`

Add near top after imports:
```tsx
import { useCollectionContext } from '@/hooks';
import { CollectionBadgeStack } from './collection-badge-stack';
```

Add in card render (coordinate position with UI engineer):
```tsx
// In UnifiedCard render, after type indicator:
const { selectedCollectionId } = useCollectionContext();
const isAllCollectionsView = !selectedCollectionId || selectedCollectionId === 'all';

{isAllCollectionsView && entity.collections && entity.collections.length > 0 && (
  <div className="mt-2 mb-2">
    <CollectionBadgeStack collections={entity.collections} />
  </div>
)}
```

### Test Cases

- [ ] Badges render in "All Collections" view
- [ ] Badges hidden in specific collection view
- [ ] Badges hidden when entity has no collections array
- [ ] Badges hidden when all collections are 'default'
- [ ] Card layout not broken by badge addition
- [ ] No performance regression (≤50ms per card)

### Quality Gates

- [ ] ≥80% coverage
- [ ] TypeScript strict mode
- [ ] ESLint passes
- [ ] No visual regression

---

## Task P2-T3: Implement Badge Positioning & Styling

**Type**: Design Coordination | **Story Points**: 1.5 | **Estimated Time**: 4-6 hours

### Description

Coordinate with UI engineer on badge placement and styling. Ensure badges fit naturally in card layout and follow design system.

### Acceptance Criteria

- [x] Badge position decided: top-right corner OR below type indicator
- [x] Badge background color: secondary (or design system variant)
- [x] Badge text color: contrasts with background (≥4.5:1)
- [x] Badge spacing: consistent with card padding
- [x] Badge max-width: doesn't cause text overflow
- [x] Design reviewed and approved by UI team

### Implementation Details

**Decision Points**:
1. Where on card? (top-right corner vs. below type indicator)
2. What color? (secondary, tertiary, or custom variant)
3. How much vertical space? (one line, two lines, wrapping)

Coordinate with UI engineer BEFORE final implementation.

### Quality Gates

- [ ] Design approved by UI engineer
- [ ] Styling consistent with design system
- [ ] No visual conflicts with existing card elements

---

## Task P2-T4: Add Accessibility Features

**Type**: Quality Assurance | **Story Points**: 1.5 | **Estimated Time**: 4-6 hours

### Description

Ensure WCAG 2.1 Level AA accessibility compliance for badges.

### Acceptance Criteria

- [x] Each badge has aria-label: "in {collection-name} collection"
- [x] "+N more" badge has aria-label: "in {count} more collections"
- [x] Color contrast: badges meet 4.5:1 ratio
- [x] Keyboard navigation: Tab through all badges
- [x] Focus visible: clear focus outline on tabbing
- [x] Tooltip accessible: visible on keyboard focus, not just hover
- [x] Screen reader test: NVDA/JAWS reads badges correctly

### Testing Tools

- axe DevTools browser extension
- Lighthouse accessibility audit
- Keyboard-only navigation test
- NVDA or JAWS screen reader

### Quality Gates

- [ ] Axe audit: zero critical issues
- [ ] Lighthouse: ≥90 accessibility score
- [ ] Keyboard navigation: all badges reachable and identifiable

---

## Task P2-T5: Write Unit & Snapshot Tests

**Type**: Testing | **Story Points**: 2 | **Estimated Time**: 6-8 hours

### Description

Comprehensive unit tests including snapshot tests for badge rendering at different states.

### Test Structure

**Files**:
- `skillmeat/web/__tests__/components/collection-badge-stack.test.ts` (new)
- `skillmeat/web/__tests__/components/unified-card.test.ts` (enhanced)

### Test Cases

**CollectionBadgeStack**:
- [ ] Renders first 2 collections
- [ ] Shows "+N more" badge when necessary
- [ ] Filters out 'default' collection
- [ ] Tooltip shows full list
- [ ] aria-labels are present and correct
- [ ] Snapshot: 2 collections
- [ ] Snapshot: 3+ collections with "+N more"

**UnifiedCard with Badges**:
- [ ] Badges render in "All Collections" view
- [ ] Badges hidden in specific collection view
- [ ] Snapshot: card with collection badges

### Coverage Target

- CollectionBadgeStack: ≥85%
- UnifiedCard badge section: ≥80%

### Quality Gates

- [ ] All tests pass
- [ ] Coverage ≥80%
- [ ] Snapshots reviewed and approved

---

## Task P2-T6: Performance Profiling & Optimization

**Type**: Quality Assurance | **Story Points**: 1 | **Estimated Time**: 3-4 hours

### Description

Profile card render performance to ensure no regression. Optimize if badges cause slowdown.

### Acceptance Criteria

- [x] Profile with React DevTools: card render ≤50ms per card
- [x] Profile with 100+ cards: total render ≤5 seconds
- [x] No memory leaks when mounting/unmounting badges
- [x] Badges don't trigger unnecessary re-renders of parent card

### Profiling Steps

1. Open component in browser
2. React DevTools Profiler tab
3. Record: render 100+ cards
4. Check: individual card render times
5. Identify: any components rendering unnecessarily
6. Optimize: if render time > 50ms per card

### Quality Gates

- [ ] Card render time ≤50ms
- [ ] No unexpected re-renders
- [ ] Ready for Phase 3

---

## Task P2-T7: Code Review & Documentation

**Type**: Quality Assurance | **Story Points**: 1 | **Estimated Time**: 3-4 hours

### Description

Final code review, JSDoc documentation, and integration test with Phase 1 hooks (dry run for Phase 3).

### Acceptance Criteria

- [x] Self-review: follows project conventions
- [x] Peer review: approved by 1+ senior engineer
- [x] TypeScript strict mode: zero errors
- [x] ESLint: zero warnings
- [x] JSDoc: CollectionBadgeStack documented
- [x] Integration test: badges work with useCollectionContext
- [x] No breaking changes to UnifiedCard API

### Quality Gates

- [ ] Code review approved
- [ ] Ready for Phase 3 (group badges depend on Phase 2)
- [ ] Handoff documentation complete

---

## Task P2-T8: Storybook Entry (Optional)

**Type**: Documentation | **Story Points**: 0.5 | **Estimated Time**: 1-2 hours

### Description

Optional: Create Storybook story for CollectionBadgeStack component to aid future developers.

### Acceptance Criteria

- [x] Story file created: `CollectionBadgeStack.stories.tsx`
- [x] Story shows: 1-2 collections, 3+ collections, empty state
- [x] Story shows: light/dark mode if applicable
- [x] Story runnable and accurate

---

## Definition of Done

Phase 2 is complete when:

1. **Code**:
   - [x] CollectionBadgeStack component created and exported
   - [x] UnifiedCard enhanced with badge rendering logic
   - [x] Conditional rendering based on collection context
   - [x] No breaking changes to existing components

2. **Testing**:
   - [x] ≥80% test coverage
   - [x] All unit tests passing
   - [x] Snapshot tests baseline created
   - [x] Performance profiling completed (≤50ms per card)

3. **Quality**:
   - [x] WCAG 2.1 AA accessibility verified
   - [x] TypeScript strict mode: zero errors
   - [x] ESLint: zero warnings
   - [x] Code review approved

4. **Documentation**:
   - [x] JSDoc complete
   - [x] Design decisions documented
   - [x] Performance benchmark recorded

---

## Handoff to Phase 3

Phase 3 builds on Phase 2's badge rendering pattern. Key handoff items:

1. **CollectionBadgeStack pattern** — Phase 3 creates `GroupBadgeRow` using same structure
2. **Conditional rendering logic** — Phase 3 reuses context-based visibility pattern
3. **Tooltip + overflow pattern** — Phase 3 applies same "+N more" badge approach for groups
4. **Performance baseline** — Phase 3 must not exceed Phase 2's 50ms per card target

---

**End of Phase 2 Tasks**

Next: Phase 3 - Group Badges & Modal Enhancement
