---
title: "Collections Remediation - Implementation Plan"
description: "Fix collection filtering and artifact-collection display in modal"
audience: [ai-agents, developers]
tags: [implementation, remediation, collections, frontend, bugfix]
created: 2025-12-21
updated: 2025-12-21
category: "remediation"
status: ready
complexity: Small
effort: 8 story points
related:
  - /docs/project_plans/ideas/collections-remediate-12-18.md
  - /docs/project_plans/PRDs/enhancements/collections-navigation-v1.md
---

# Collections Remediation - Implementation Plan

**Feature Name**: Collections Remediation
**Date**: 2025-12-21
**Author**: Claude (Opus 4.5)
**Status**: Ready for Implementation
**Complexity**: Small | **Effort**: 8 story points | **Timeline**: 1-2 days

---

## Executive Summary

Two focused bug fixes to complete the Collections feature:

1. **Issue 1**: Collection dropdown selection doesn't filter artifacts - page still shows ALL artifacts
2. **Issue 2**: Artifact modal Collections tab always empty - never shows which collections an artifact belongs to

Both issues are **frontend-only** fixes. The backend API endpoints already work correctly.

---

## Root Cause Analysis

### Issue 1: Collection Filtering Not Applied

**File**: `skillmeat/web/app/collection/page.tsx`

**Current Flow**:
```
CollectionSwitcher → selectedCollectionId (stored in context)
                   → useArtifacts() called (ignores selection)
                   → Shows ALL artifacts
```

**Problem**: The page uses `useArtifacts()` which calls `GET /artifacts` with no collection filter.

**Solution**: Use `useCollectionArtifacts(selectedCollectionId)` when a collection is selected (hook already exists and works).

### Issue 2: Collections Tab Always Empty

**File**: `skillmeat/web/components/entity/modal-collections-tab.tsx`

**Current Flow**:
```
Artifact → artifactToEntity() hardcodes collection: 'default'
        → Modal Collections Tab filters collections.filter(c => c.id === 'default')
        → Always returns empty array
```

**Problem**: Two-part issue:
1. `artifactToEntity()` in `page.tsx` hardcodes `collection: 'default'` instead of preserving actual data
2. Tab component filters for matching collection ID which never matches real collections

**Solution**:
1. Add `collections` array to Entity type
2. Preserve artifact's collection memberships in conversion
3. Display actual collections in the tab

---

## Implementation Strategy

### Phase Overview

| Phase | Title | Effort | Assignee |
|-------|-------|--------|----------|
| 1 | Collection Filtering Fix | 3 pts | ui-engineer-enhanced |
| 2 | Modal Collections Tab Fix | 3 pts | ui-engineer-enhanced |
| 3 | Testing & Polish | 2 pts | ui-engineer-enhanced |

**Total**: 8 story points (~1-2 days)

### Critical Path

```
Phase 1 (Filtering) ──┬──> Phase 3 (Testing)
Phase 2 (Modal Tab) ──┘
```

Phases 1 and 2 are independent and can be done in parallel.

---

## Phase 1: Collection Filtering Fix

**Goal**: When user selects a collection, show only artifacts from that collection.

### Task Breakdown

| ID | Task | Description | Acceptance Criteria | Est |
|----|------|-------------|---------------------|-----|
| 1.1 | Update page.tsx to use conditional hook | Use `useArtifacts()` for "All Collections", `useCollectionArtifacts(id)` when specific collection selected | Selecting a collection filters the artifact grid | 2h |
| 1.2 | Handle loading states | Show loading indicator when switching collections | Smooth transition between collections | 30m |
| 1.3 | Handle empty state | Show appropriate message when collection has no artifacts | "No artifacts in this collection" message displayed | 30m |

### Implementation Details

**File**: `skillmeat/web/app/collection/page.tsx`

**Current Code** (around line 70):
```tsx
const { data: artifacts = [], isLoading } = useArtifacts();
```

**Fixed Code**:
```tsx
const { selectedCollectionId } = useCollectionContext();

// Use collection-specific hook when collection selected, otherwise all artifacts
const {
  data: collectionArtifacts,
  isLoading: isLoadingCollection
} = useCollectionArtifacts(selectedCollectionId || '', {
  enabled: !!selectedCollectionId && selectedCollectionId !== 'all',
});

const {
  data: allArtifacts,
  isLoading: isLoadingAll
} = useArtifacts({
  enabled: !selectedCollectionId || selectedCollectionId === 'all',
});

const artifacts = selectedCollectionId && selectedCollectionId !== 'all'
  ? collectionArtifacts
  : allArtifacts;
const isLoading = selectedCollectionId && selectedCollectionId !== 'all'
  ? isLoadingCollection
  : isLoadingAll;
```

### API Endpoint (Already Working)

```
GET /api/v1/user-collections/{id}/artifacts
Response: { items: Artifact[], page_info: PageInfo }
```

### Quality Gate

- [ ] Selecting "All Collections" shows all artifacts
- [ ] Selecting a specific collection shows only its artifacts
- [ ] Artifact count in dropdown matches displayed artifacts
- [ ] Loading state shown during collection switch
- [ ] Empty collection shows appropriate message

---

## Phase 2: Modal Collections Tab Fix

**Goal**: Show which collections an artifact belongs to in the modal's Collections tab.

### Task Breakdown

| ID | Task | Description | Acceptance Criteria | Est |
|----|------|-------------|---------------------|-----|
| 2.1 | Update Entity type | Add `collections?: Collection[]` field to Entity type | Type includes collections array | 15m |
| 2.2 | Fix artifactToEntity conversion | Preserve artifact's collection data instead of hardcoding | Collections data passed through | 30m |
| 2.3 | Update modal Collections tab | Display entity's collections instead of filtering | Collections shown in tab | 1h |
| 2.4 | Add/remove collection from tab | Wire up add/remove buttons to work | Changes reflected immediately | 1h |

### Implementation Details

#### 2.1 Update Entity Type

**File**: `skillmeat/web/types/entity.ts`

```tsx
// Add to Entity interface
export interface Entity {
  // ... existing fields
  collections?: Collection[];  // Add this
}
```

#### 2.2 Fix artifactToEntity Conversion

**File**: `skillmeat/web/app/collection/page.tsx`

**Current Code** (lines 24-47):
```tsx
function artifactToEntity(artifact: Artifact): Entity {
  return {
    // ...
    collection: 'default',  // HARDCODED - this is the bug
  };
}
```

**Fixed Code**:
```tsx
function artifactToEntity(artifact: Artifact): Entity {
  return {
    // ...
    collection: artifact.collection_id || 'default',
    collections: artifact.collections || [],  // Preserve actual collections
  };
}
```

#### 2.3 Update Modal Collections Tab

**File**: `skillmeat/web/components/entity/modal-collections-tab.tsx`

**Current Code** (lines 88-91):
```tsx
// Filtering against hardcoded 'default' - always returns empty
const entityCollections = collections.filter(c => c.id === entity.collection);
```

**Fixed Code**:
```tsx
// Use the entity's actual collections array
const entityCollections = entity.collections || [];
```

#### 2.4 Wire Add/Remove Actions

The tab already has UI for add/remove. Need to:
1. Call `useAddArtifactToCollection` mutation on add
2. Call `useRemoveArtifactFromCollection` mutation on remove
3. Invalidate queries to refresh the display

### Quality Gate

- [ ] Collections tab shows artifact's actual collections
- [ ] Empty state shown if artifact not in any collections
- [ ] Add artifact to collection works and updates display
- [ ] Remove artifact from collection works and updates display
- [ ] Changes persist after modal close/reopen

---

## Phase 3: Testing & Polish

**Goal**: Verify both fixes work correctly and handle edge cases.

### Task Breakdown

| ID | Task | Description | Acceptance Criteria | Est |
|----|------|-------------|---------------------|-----|
| 3.1 | Manual E2E testing | Test full flows for both fixes | All scenarios pass | 1h |
| 3.2 | Edge case handling | Test empty states, rapid switching, etc. | No errors or glitches | 30m |
| 3.3 | Update unit tests | Add/update tests for changed hooks | Tests pass | 30m |

### Test Scenarios

**Collection Filtering**:
1. Select collection → verify only its artifacts shown
2. Switch between collections → verify correct filtering
3. Select "All Collections" → verify all artifacts shown
4. Select empty collection → verify empty state
5. Create new artifact in collection → verify it appears

**Modal Collections Tab**:
1. Open artifact in collection → verify collection shown in tab
2. Open artifact in multiple collections → verify all shown
3. Open artifact not in any collection → verify empty state
4. Add artifact to collection → verify immediate update
5. Remove artifact from collection → verify immediate update
6. Close and reopen modal → verify changes persisted

### Quality Gate

- [ ] All manual test scenarios pass
- [ ] No console errors during operations
- [ ] Unit tests pass
- [ ] TypeScript compilation succeeds
- [ ] Build completes without errors

---

## Files to Modify

| File | Changes |
|------|---------|
| `skillmeat/web/app/collection/page.tsx` | Use conditional hooks for filtering, fix artifactToEntity |
| `skillmeat/web/types/entity.ts` | Add collections field |
| `skillmeat/web/components/entity/modal-collections-tab.tsx` | Use entity.collections instead of filtering |
| `skillmeat/web/hooks/use-collections.ts` | Verify useCollectionArtifacts works (likely no changes) |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Hook causes extra API calls | Low | Low | Use `enabled` flag properly |
| Type mismatch with backend | Low | Medium | Verify Artifact type has collections |
| Cache invalidation issues | Medium | Low | Invalidate relevant queries on mutation |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Collection filtering works | 100% | Manual testing |
| Modal displays collections | 100% | Manual testing |
| No regressions | 0 bugs | Existing tests pass |
| Build succeeds | Yes | CI pipeline |

---

## Orchestration Quick Reference

**Phase 1** (Filtering):
```
Task("ui-engineer-enhanced", "TASK-1.1: Update collection page to use conditional artifact fetching.
     File: skillmeat/web/app/collection/page.tsx
     Change: Use useCollectionArtifacts(id) when collection selected, useArtifacts() for 'All Collections'
     Reference: useCollectionArtifacts hook already exists in hooks/use-collections.ts:178-218")
```

**Phase 2** (Modal):
```
Task("ui-engineer-enhanced", "TASK-2.1-2.4: Fix modal Collections tab to display artifact's collections.
     Files:
       - skillmeat/web/types/entity.ts (add collections field)
       - skillmeat/web/app/collection/page.tsx (fix artifactToEntity conversion)
       - skillmeat/web/components/entity/modal-collections-tab.tsx (use entity.collections)
     Issue: Currently hardcodes 'default' and filters against it, always empty")
```

**Phase 3** (Testing):
```
Task("ui-engineer-enhanced", "TASK-3.1-3.3: Test collection filtering and modal collections tab fixes.
     Test scenarios:
       - Select collection → only its artifacts shown
       - Modal shows artifact's actual collections
       - Add/remove from collection updates immediately
     Verify no console errors, build succeeds")
```

---

## Document Status

**Status**: Ready for implementation
**Next Steps**:
1. Create progress tracking with artifact-tracking skill
2. Execute Phase 1 and Phase 2 in parallel
3. Execute Phase 3 after both complete
4. Commit after each phase
