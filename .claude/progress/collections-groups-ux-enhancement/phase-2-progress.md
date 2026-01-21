---
type: progress
prd: collections-groups-ux-enhancement
phase: 2
title: Collection Badges on Cards
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
- id: P2-T1
  description: Create CollectionBadgeStack component with shadcn Badge
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 2h
  priority: high
- id: P2-T2
  description: Integrate CollectionBadgeStack into UnifiedCard component
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P2-T1
  estimated_effort: 1.5h
  priority: high
- id: P2-T3
  description: Add conditional rendering logic (All Collections view only)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P2-T2
  estimated_effort: 1h
  priority: high
- id: P2-T4
  description: Handle overflow with +N more badge and tooltip
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P2-T1
  estimated_effort: 2h
  priority: medium
- id: P2-T5
  description: Write unit tests for badge components (≥80% coverage)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P2-T1
  - P2-T2
  - P2-T3
  - P2-T4
  estimated_effort: 3h
  priority: high
parallelization:
  batch_1:
  - P2-T1
  batch_2:
  - P2-T2
  - P2-T4
  batch_3:
  - P2-T3
  batch_4:
  - P2-T5
  critical_path:
  - P2-T1
  - P2-T2
  - P2-T3
  - P2-T5
  estimated_total_time: 7.5h
blockers: []
success_criteria:
- id: SC-1
  description: Collection badges render on UnifiedCard in All Collections view
  status: pending
- id: SC-2
  description: Default collection hidden from badge display
  status: pending
- id: SC-3
  description: Non-default collections shown with collection name
  status: pending
- id: SC-4
  description: Max 2 badges displayed; 3+ collections show X more... badge
  status: pending
- id: SC-5
  description: Hover on X more... shows tooltip with full collection list
  status: pending
- id: SC-6
  description: Badges styled with shadcn Badge component (secondary color)
  status: pending
- id: SC-7
  description: Badges hidden when viewing specific collection
  status: pending
- id: SC-8
  description: 'Accessibility: each badge has aria-label, keyboard-navigable'
  status: pending
- id: SC-9
  description: 'No performance regression: card render ≤50ms per card'
  status: pending
- id: SC-10
  description: ≥80% unit test coverage
  status: pending
files_modified:
- skillmeat/web/components/shared/unified-card.tsx
- skillmeat/web/components/shared/collection-badge-stack.tsx
- skillmeat/web/__tests__/components/unified-card.test.ts
- skillmeat/web/__tests__/components/collection-badge-stack.test.ts
progress: 100
updated: '2026-01-20'
---

# Collections & Groups UX Enhancement - Phase 2: Collection Badges on Cards

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/collections-groups-ux-enhancement/phase-2-progress.md -t P2-T1 -s completed
```

**Quick Reference for Task Orchestration**:

```python
# Batch 1
Task("ui-engineer-enhanced", "Create CollectionBadgeStack component. File: components/shared/collection-badge-stack.tsx. Use shadcn Badge (secondary), max 2 badges + overflow tooltip.", model="opus")

# Batch 2 (parallel after batch 1)
Task("ui-engineer-enhanced", "Integrate CollectionBadgeStack into UnifiedCard. File: components/shared/unified-card.tsx. Add conditional render section for All Collections view.", model="opus")
Task("ui-engineer-enhanced", "Implement +N more badge with tooltip. File: components/shared/collection-badge-stack.tsx. Use Radix Tooltip, show full list on hover.", model="opus")

# Batch 3 (sequential after batch 2)
Task("ui-engineer-enhanced", "Add conditional rendering logic. File: components/shared/unified-card.tsx. Use useCollectionContext to detect All Collections view vs specific collection.", model="opus")

# Batch 4 (sequential - testing)
Task("ui-engineer-enhanced", "Write unit tests. Files: __tests__/components/collection-badge-stack.test.ts, __tests__/components/unified-card.test.ts. Test badge rendering, overflow, accessibility. ≥80% coverage.", model="opus")
```

---

## Objective

Add visual collection membership indicators to artifact cards in the "All Collections" view. Users will immediately see which collections contain each artifact without opening the modal. This phase implements the badge display pattern, overflow handling, and accessibility requirements.

---

## Implementation Notes

### Architectural Decisions

**Badge Component Pattern**: Create a dedicated `CollectionBadgeStack` component rather than inline rendering in UnifiedCard. This:
- Enables reuse in other contexts (future phases)
- Simplifies testing with isolated unit tests
- Keeps UnifiedCard component lean

**Conditional Rendering Strategy**:
```typescript
// In UnifiedCard component
const { selectedCollectionId } = useCollectionContext();
const isAllCollections = !selectedCollectionId || selectedCollectionId === 'all';

{isAllCollections && entity.collections && (
  <CollectionBadgeStack collections={entity.collections} />
)}
```

**Overflow Pattern**: Show max 2 collection badges, then "+N more..." badge with tooltip:
```typescript
const visibleCollections = collections.slice(0, 2);
const overflowCount = collections.length - 2;
```

**Color Scheme**:
- Collection badges: `variant="secondary"` (shadcn Badge)
- Future group badges: `variant="outline"` (distinct from collections)

### Patterns and Best Practices

**Reference Patterns**:
- Existing badge usage in `components/shared/entity-type-badge.tsx`
- Tooltip patterns in `.claude/context/key-context/component-patterns.md`
- UnifiedCard structure in `components/shared/unified-card.tsx`

**Accessibility Requirements**:
```typescript
<Badge variant="secondary" aria-label={`In collection: ${collection.name}`}>
  {collection.name}
</Badge>
```

**Integration with useCollectionContext**:
```typescript
import { useCollectionContext } from '@/hooks';

const { selectedCollectionId } = useCollectionContext();
const isSpecificCollection = selectedCollectionId && selectedCollectionId !== 'all';
```

### Known Gotchas

**Badge Visual Clutter**: Too many badges overwhelm the card. Mitigation:
- Strict max of 2 visible badges
- Use "+N more..." pattern with tooltip for overflow
- Design review before merge

**Default Collection Filtering**: The "default" collection should never show a badge. Filter logic:
```typescript
const nonDefaultCollections = collections.filter(c => !c.is_default);
```

**Performance with Many Cards**: Badge rendering on 100+ cards could slow initial render. Mitigation:
- Profile with React DevTools Profiler
- Lazy-render badges only if `entity.collections` exists
- Target: ≤50ms per card render

**Color Contrast**: Ensure secondary badge meets WCAG 4.5:1 ratio. shadcn Badge component already tested, but verify in context.

**Tooltip Positioning**: Tooltip may overflow viewport on cards near edge. Use Radix Tooltip `side="top"` and `align="center"` with collision detection.

### Development Setup

**Prerequisites**:
- shadcn Badge component (already installed)
- Radix Tooltip primitive (already installed)
- useCollectionContext hook (already exists)

**Testing Setup**:
```bash
# Run component tests
pnpm test -- components/collection-badge-stack.test.ts
pnpm test -- components/unified-card.test.ts

# Snapshot tests
pnpm test -- -u

# Accessibility audit
pnpm test:a11y
```

**Quality Gates**:
- [ ] Component renders in "All Collections" view
- [ ] Badge layout does not break card design
- [ ] WCAG 2.1 AA compliance (axe audit)
- [ ] Performance: ≤50ms per card (profiled)
- [ ] ≥80% test coverage
- [ ] Code review complete

---

## Completion Notes

_Fill in when phase is complete_

**What was built**:

**Key learnings**:

**Unexpected challenges**:

**Recommendations for next phase**:
