---
type: progress
prd: "collections-remediate"
phase: "all"
status: pending
progress: 0
total_tasks: 10
completed_tasks: 0
effort_points: 8
created: 2025-12-21
updated: 2025-12-21

tasks:
  # Phase 1: Collection Filtering Fix (3 pts)
  - id: "TASK-1.1"
    title: "Update page.tsx to use conditional hook"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    effort: "2h"
    phase: 1
  - id: "TASK-1.2"
    title: "Handle loading states"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-1.1"]
    effort: "30m"
    phase: 1
  - id: "TASK-1.3"
    title: "Handle empty state"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-1.1"]
    effort: "30m"
    phase: 1

  # Phase 2: Modal Collections Tab Fix (3 pts)
  - id: "TASK-2.1"
    title: "Update Entity type"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    effort: "15m"
    phase: 2
  - id: "TASK-2.2"
    title: "Fix artifactToEntity conversion"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-2.1"]
    effort: "30m"
    phase: 2
  - id: "TASK-2.3"
    title: "Update modal Collections tab"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-2.2"]
    effort: "1h"
    phase: 2
  - id: "TASK-2.4"
    title: "Add/remove collection from tab"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-2.3"]
    effort: "1h"
    phase: 2

  # Phase 3: Testing & Polish (2 pts)
  - id: "TASK-3.1"
    title: "Manual E2E testing"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-1.3", "TASK-2.4"]
    effort: "1h"
    phase: 3
  - id: "TASK-3.2"
    title: "Edge case handling"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.1"]
    effort: "30m"
    phase: 3
  - id: "TASK-3.3"
    title: "Update unit tests"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.1"]
    effort: "30m"
    phase: 3

parallelization:
  batch_1: ["TASK-1.1", "TASK-2.1"]  # Phase 1 & 2 starts (independent)
  batch_2: ["TASK-1.2", "TASK-1.3", "TASK-2.2"]  # After batch_1
  batch_3: ["TASK-2.3"]  # After TASK-2.2
  batch_4: ["TASK-2.4"]  # After TASK-2.3
  batch_5: ["TASK-3.1"]  # After Phase 1 & 2 complete
  batch_6: ["TASK-3.2", "TASK-3.3"]  # After TASK-3.1

blockers: []
---

# Collections Remediation - Progress Tracking

**PRD**: `docs/project_plans/implementation_plans/remediations/collections-remediate-v1.md`
**Complexity**: Small | **Effort**: 8 story points | **Timeline**: 1-2 days

## Summary

Two focused frontend bug fixes:
1. **Issue 1**: Collection dropdown selection doesn't filter artifacts
2. **Issue 2**: Artifact modal Collections tab always empty

## Phase Overview

| Phase | Title | Effort | Status | Tasks |
|-------|-------|--------|--------|-------|
| 1 | Collection Filtering Fix | 3 pts | pending | 3 |
| 2 | Modal Collections Tab Fix | 3 pts | pending | 4 |
| 3 | Testing & Polish | 2 pts | pending | 3 |

---

## Orchestration Quick Reference

### Batch 1 (Parallel - Phase 1 & 2 Starts)

```
Task("ui-engineer-enhanced", "TASK-1.1: Update collection page to use conditional artifact fetching.
     File: skillmeat/web/app/collection/page.tsx
     Change: Use useCollectionArtifacts(id) when collection selected, useArtifacts() for 'All Collections'
     Reference: useCollectionArtifacts hook already exists in hooks/use-collections.ts:178-218

     Implementation:
     - Get selectedCollectionId from useCollectionContext()
     - Use useCollectionArtifacts with enabled flag when collection selected
     - Use useArtifacts with enabled flag when 'all' or no selection
     - Merge results into single artifacts variable")
```

```
Task("ui-engineer-enhanced", "TASK-2.1: Update Entity type to include collections array.
     File: skillmeat/web/types/entity.ts
     Change: Add 'collections?: Collection[]' field to Entity interface
     Purpose: Allow artifacts to carry their collection memberships to modal")
```

### Batch 2 (After Batch 1)

```
Task("ui-engineer-enhanced", "TASK-1.2 + TASK-1.3: Handle loading and empty states for collection filtering.
     File: skillmeat/web/app/collection/page.tsx
     Changes:
     - Show loading indicator when switching collections (isLoading state)
     - Show 'No artifacts in this collection' when collection is empty
     - Ensure smooth transition between collection selections")
```

```
Task("ui-engineer-enhanced", "TASK-2.2: Fix artifactToEntity conversion to preserve collection data.
     File: skillmeat/web/app/collection/page.tsx
     Current: hardcodes collection: 'default'
     Fix:
     - Set collection: artifact.collection_id || 'default'
     - Add collections: artifact.collections || []")
```

### Batch 3 (After Batch 2)

```
Task("ui-engineer-enhanced", "TASK-2.3: Update modal Collections tab to display actual collections.
     File: skillmeat/web/components/entity/modal-collections-tab.tsx
     Current: filters collections.filter(c => c.id === entity.collection) → always empty
     Fix: Use entity.collections directly instead of filtering
     - const entityCollections = entity.collections || []
     - Show empty state if no collections")
```

### Batch 4 (After Batch 3)

```
Task("ui-engineer-enhanced", "TASK-2.4: Wire add/remove collection actions in modal tab.
     File: skillmeat/web/components/entity/modal-collections-tab.tsx
     Changes:
     - Connect add button to useAddArtifactToCollection mutation
     - Connect remove button to useRemoveArtifactFromCollection mutation
     - Invalidate queries to refresh display after mutation
     - Ensure optimistic UI updates")
```

### Batch 5 (After Phase 1 & 2 Complete)

```
Task("ui-engineer-enhanced", "TASK-3.1: Manual E2E testing of collection filtering and modal fixes.
     Test scenarios:
     Collection Filtering:
       1. Select collection → verify only its artifacts shown
       2. Switch between collections → verify correct filtering
       3. Select 'All Collections' → verify all artifacts shown
       4. Select empty collection → verify empty state message
     Modal Collections Tab:
       1. Open artifact in collection → verify collection shown
       2. Open artifact in multiple collections → verify all shown
       3. Open artifact not in any collection → verify empty state
       4. Add artifact to collection → verify immediate update
       5. Remove artifact from collection → verify immediate update")
```

### Batch 6 (After Batch 5)

```
Task("ui-engineer-enhanced", "TASK-3.2 + TASK-3.3: Edge case handling and unit test updates.
     Edge cases:
     - Rapid collection switching
     - Add/remove same collection quickly
     - Network errors during mutation
     Tests:
     - Update/add tests for useCollectionArtifacts hook usage
     - Update/add tests for entity conversion
     Verify: No console errors, TypeScript compiles, build succeeds")
```

---

## Key Files

| File | Purpose | Changes |
|------|---------|---------|
| `skillmeat/web/app/collection/page.tsx` | Collection page | Conditional hooks, fix conversion |
| `skillmeat/web/types/entity.ts` | Entity type | Add collections field |
| `skillmeat/web/components/entity/modal-collections-tab.tsx` | Modal tab | Use entity.collections |
| `skillmeat/web/hooks/use-collections.ts` | Collection hooks | Verify (likely no changes) |

---

## Quality Gates

### Phase 1 Complete When:
- [ ] Selecting "All Collections" shows all artifacts
- [ ] Selecting specific collection shows only its artifacts
- [ ] Artifact count in dropdown matches displayed count
- [ ] Loading state shown during collection switch
- [ ] Empty collection shows appropriate message

### Phase 2 Complete When:
- [ ] Collections tab shows artifact's actual collections
- [ ] Empty state shown if artifact not in any collections
- [ ] Add artifact to collection works and updates display
- [ ] Remove artifact from collection works and updates display
- [ ] Changes persist after modal close/reopen

### Phase 3 Complete When:
- [ ] All manual test scenarios pass
- [ ] No console errors during operations
- [ ] Unit tests pass
- [ ] TypeScript compilation succeeds
- [ ] Build completes without errors

---

## Notes

_Session notes and decisions will be added here during implementation._
