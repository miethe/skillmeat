---
type: progress
prd: collections-groups-ux-enhancement
phase: 3
title: Group Badges + Modal Enhancement
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
- id: P3-T1
  description: Create GroupBadgeRow component with useArtifactGroups hook
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 2.5h
  priority: high
- id: P3-T2
  description: Integrate GroupBadgeRow into UnifiedCard for collection view
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P3-T1
  estimated_effort: 1.5h
  priority: high
- id: P3-T3
  description: Update ModalCollectionsTab with Groups section
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 2h
  priority: high
- id: P3-T4
  description: Create GroupsDisplay component for modal
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P3-T3
  estimated_effort: 2h
  priority: medium
- id: P3-T5
  description: "Write unit tests for group badge components (\u226580% coverage)"
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P3-T1
  - P3-T2
  - P3-T3
  - P3-T4
  estimated_effort: 3h
  priority: high
parallelization:
  batch_1:
  - P3-T1
  - P3-T3
  batch_2:
  - P3-T2
  - P3-T4
  batch_3:
  - P3-T5
  critical_path:
  - P3-T1
  - P3-T2
  - P3-T5
  estimated_total_time: 8h
blockers: []
success_criteria:
- id: SC-1
  description: Group badges render on UnifiedCard in specific collection context
  status: pending
- id: SC-2
  description: Group badges styled with tertiary/outline color (distinct from collection
    badges)
  status: pending
- id: SC-3
  description: Max 2 group badges; 3+ groups show X more... badge
  status: pending
- id: SC-4
  description: Tooltip on X more... shows full group list
  status: pending
- id: SC-5
  description: Badges hidden when viewing All Collections
  status: pending
- id: SC-6
  description: Groups fetched via useArtifactGroups() hook from Phase 1
  status: pending
- id: SC-7
  description: 'Loading state: skeleton or placeholder while groups fetch'
  status: pending
- id: SC-8
  description: 'Error handling: gracefully skip badge render if fetch fails'
  status: pending
- id: SC-9
  description: ModalCollectionsTab placeholder (lines 197-198) replaced with Groups
    display
  status: pending
- id: SC-10
  description: For each collection in modal, groups shown as badges or list
  status: pending
- id: SC-11
  description: No groups message if collection has no groups
  status: pending
- id: SC-12
  description: "\u226580% unit test coverage"
  status: pending
files_modified:
- skillmeat/web/components/shared/unified-card.tsx
- skillmeat/web/components/shared/group-badge-row.tsx
- skillmeat/web/components/entity/modal-collections-tab.tsx
- skillmeat/web/components/entity/groups-display.tsx
- skillmeat/web/__tests__/components/group-badge-row.test.ts
- skillmeat/web/__tests__/components/groups-display.test.ts
- skillmeat/web/__tests__/components/modal-collections-tab.test.ts
progress: 100
updated: '2026-01-20'
schema_version: 2
doc_type: progress
feature_slug: collections-groups-ux-enhancement
---

# Collections & Groups UX Enhancement - Phase 3: Group Badges + Modal Enhancement

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/collections-groups-ux-enhancement/phase-3-progress.md -t P3-T1 -s completed
```

**Quick Reference for Task Orchestration**:

```python
# Batch 1 (parallel - independent tasks)
Task("ui-engineer-enhanced", "Create GroupBadgeRow component. File: components/shared/group-badge-row.tsx. Use useArtifactGroups hook, shadcn Badge (outline variant), max 2 badges + overflow.", model="opus")
Task("ui-engineer-enhanced", "Update ModalCollectionsTab with Groups section. File: components/entity/modal-collections-tab.tsx. Replace placeholder at lines 197-198 with groups display area.", model="opus")

# Batch 2 (parallel after batch 1)
Task("ui-engineer-enhanced", "Integrate GroupBadgeRow into UnifiedCard. File: components/shared/unified-card.tsx. Add conditional render for specific collection context.", model="opus")
Task("ui-engineer-enhanced", "Create GroupsDisplay component. File: components/entity/groups-display.tsx. Use useGroups hook, display badges or list, handle empty state.", model="opus")

# Batch 3 (sequential - testing)
Task("ui-engineer-enhanced", "Write unit tests. Files: __tests__/components/group-badge-row.test.ts, __tests__/components/groups-display.test.ts, __tests__/components/modal-collections-tab.test.ts. Test loading states, error handling, accessibility. ≥80% coverage.", model="opus")
```

---

## Objective

Expose group membership on artifact cards (when in specific collection context) and enhance the modal's Collections tab to display groups for each collection. This phase completes the visual badge pattern by adding the group dimension and improves modal information density.

---

## Implementation Notes

### Architectural Decisions

**GroupBadgeRow Component**: Uses `useArtifactGroups(artifactId, collectionId)` from Phase 1 to fetch group membership. Key features:
- Skeleton loader during fetch (avoid layout shift)
- Graceful degradation on error (skip badge render, no crash)
- Max 2 badges + "+N more..." overflow pattern (consistent with collection badges)

**Modal Enhancement Strategy**: Replace placeholder in ModalCollectionsTab (lines 197-198) with `GroupsDisplay` component that:
- Fetches groups per collection using `useGroups(collectionId)`
- Shows "No groups" message if empty
- Uses compact badge layout (not full table)

**Color Differentiation**:
- Collection badges: `variant="secondary"` (gray/muted)
- Group badges: `variant="outline"` (border-only, distinct)

**Conditional Rendering**:
```typescript
// In UnifiedCard
const { selectedCollectionId } = useCollectionContext();
const isSpecificCollection = selectedCollectionId && selectedCollectionId !== 'all';

{isSpecificCollection && (
  <GroupBadgeRow artifactId={entity.id} collectionId={selectedCollectionId} />
)}
```

### Patterns and Best Practices

**Reference Patterns**:
- CollectionBadgeStack component from Phase 2 (reuse badge + tooltip pattern)
- ModalCollectionsTab existing structure in `components/entity/modal-collections-tab.tsx`
- Loading skeleton pattern in `.claude/context/key-context/component-patterns.md`

**Hook Integration**:
```typescript
// In GroupBadgeRow
import { useArtifactGroups } from '@/hooks';

const { data: groups, isLoading, error } = useArtifactGroups(artifactId, collectionId);

if (isLoading) return <Skeleton className="h-6 w-24" />;
if (error || !groups?.length) return null; // Graceful degradation
```

**Error Handling Pattern**:
- Network errors: skip badge render silently (don't crash card)
- Empty groups: skip badge render (no "0 groups" badge)
- Loading state: show skeleton to prevent layout shift

### Known Gotchas

**N+1 Query Problem**: `useArtifactGroups` called for every card in grid = potential 100+ API calls. Mitigation:
- TanStack Query deduplication (same key = single request)
- Monitor performance in development
- Consider batching in Phase 5 if network tab shows excessive requests

**Modal Load Latency**: Adding groups section increases modal content. Mitigation:
- Lazy-load groups (don't fetch until modal opens)
- Use skeleton loaders for perceived performance
- Profile before/after to ensure ≤300ms modal load

**Layout Shift on Badge Load**: If badge appears after skeleton, card height changes. Mitigation:
- Use fixed-height skeleton matching badge height
- Test with slow network throttling

**Group vs Collection Badge Confusion**: Users might not understand difference. Mitigation:
- Use distinct visual styling (outline vs secondary)
- Tooltip explains badge type: "Group: [name]" vs "Collection: [name]"

**Modal Placeholder Removal**: Lines 197-198 in ModalCollectionsTab are currently commented placeholders. Verify exact location before replacing.

### Development Setup

**Prerequisites**:
- Phase 1 hooks: `useArtifactGroups()`, `useGroups()` (must be complete)
- shadcn Badge, Skeleton components
- Radix Tooltip primitive

**Testing Setup**:
```bash
# Run component tests
pnpm test -- components/group-badge-row.test.ts
pnpm test -- components/groups-display.test.ts
pnpm test -- components/modal-collections-tab.test.ts

# Integration test: modal with groups
pnpm test -- modal-groups-integration.test.ts

# E2E (optional)
pnpm test:e2e -- modal-groups.spec.ts
```

**Quality Gates**:
- [ ] Group badges render in specific collection context
- [ ] Modal Collections tab shows groups for each collection
- [ ] No performance regression from group fetching
- [ ] Loading states handled correctly
- [ ] Error handling prevents crashes
- [ ] WCAG 2.1 AA compliance
- [ ] ≥80% test coverage

---

## Completion Notes

_Fill in when phase is complete_

**What was built**:

**Key learnings**:

**Unexpected challenges**:

**Recommendations for next phase**:
