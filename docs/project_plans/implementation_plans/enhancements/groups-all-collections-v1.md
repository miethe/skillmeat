---
title: 'Implementation Plan: Groups in All Collections View'
description: Phased implementation for groups functionality in All Collections view
  with group copy feature
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- groups
- collections
created: 2025-01-16
updated: 2025-01-16
category: product-planning
status: inferred_complete
related:
- /docs/project_plans/PRDs/enhancements/groups-all-collections-v1.md
---
# Implementation Plan: Groups in All Collections View

**Plan ID**: `IMPL-2025-01-16-GROUPS-ALL-COLLECTIONS`
**Date**: 2025-01-16
**Author**: Claude (Opus 4.5)
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/enhancements/groups-all-collections-v1.md`

**Complexity**: Medium
**Total Estimated Effort**: 13 story points
**Phases**: 4

---

## Executive Summary

This implementation adds two key capabilities: (1) enabling "Add to Group" functionality from the All Collections view via a two-step collection-then-group selection flow, and (2) a new "Copy Group" feature that duplicates a group with all its artifacts to another collection. The backend is mostly complete; primary work is a new copy endpoint and frontend enhancements.

---

## Implementation Strategy

### Architecture Sequence

This feature follows MeatyPrompts layered architecture with a streamlined path:

1. **Phase 1: Backend** - Add copy group endpoint (Service → API)
2. **Phase 2: Frontend Enhancement** - Collection picker in AddToGroupDialog
3. **Phase 3: Frontend New Feature** - Copy Group Dialog + integration
4. **Phase 4: Testing & Polish** - E2E tests, a11y, documentation

### Parallel Work Opportunities

- Phase 2 (Frontend Enhancement) can start immediately - no backend dependency
- Phase 3 (Copy Group) depends on Phase 1 backend completion
- Testing can begin incrementally as features complete

### Critical Path

```
Phase 1 (Backend) ─────────────────┐
                                   ├──> Phase 3 (Copy Group UI)
Phase 2 (Collection Picker) ───────┘
                                        │
                                        ├──> Phase 4 (Testing/Polish)
```

---

## Phase Breakdown

### Phase 1: Backend - Copy Group Endpoint

**Duration**: 1 day
**Dependencies**: None (groups API already complete)
**Assigned Subagent(s)**: `python-backend-engineer`

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent |
|---------|-----------|-------------|-------------------|-----|----------|
| BE-001 | Copy Endpoint | Add `POST /groups/{id}/copy` endpoint | Returns new group with artifacts | 2 pts | python-backend-engineer |
| BE-002 | Service Logic | Implement atomic copy in GroupsService | Transaction handles all-or-nothing | 1 pt | python-backend-engineer |
| BE-003 | Unit Tests | Tests for copy operation | Edge cases covered | 1 pt | python-backend-engineer |

**Implementation Details:**

```python
# New endpoint: POST /groups/{group_id}/copy
# Request body: { "target_collection_id": "uuid" }
# Response: GroupResponse (the newly created group)

# Service method signature:
async def copy_group(
    self,
    group_id: str,
    target_collection_id: str,
    user_id: str
) -> GroupResponse:
    """
    Copy group to target collection:
    1. Fetch source group with artifacts
    2. Create new group in target collection (name + " (Copy)")
    3. For each artifact in source group:
       a. Add artifact to target collection (if not already)
       b. Add artifact to new group
    4. Return new group
    """
```

**Phase 1 Quality Gates:**
- [ ] Copy endpoint returns 201 with new group
- [ ] Duplicate artifacts handled (skip add to collection)
- [ ] Group name has " (Copy)" suffix
- [ ] Transaction rolls back on any failure
- [ ] Unit tests pass

---

### Phase 2: Frontend - Collection Picker Enhancement

**Duration**: 1 day
**Dependencies**: None (can start immediately)
**Assigned Subagent(s)**: `ui-engineer-enhanced`, `frontend-developer`

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent |
|---------|-----------|-------------|-------------------|-----|----------|
| FE-001 | Collection Picker Step | Add collection selection to AddToGroupDialog | Shows when no collectionId | 2 pts | ui-engineer-enhanced |
| FE-002 | Wire All Collections | Pass undefined collectionId in All Collections view | Dialog shows picker first | 1 pt | frontend-developer |
| FE-003 | Unit Tests | Test collection picker behavior | States and selection work | 1 pt | frontend-developer |

**Implementation Details:**

```tsx
// Enhanced AddToGroupDialog props
interface AddToGroupDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  artifact: Artifact;
  collectionId?: string;  // Now optional
  onSuccess?: () => void;
}

// Internal state machine:
// 1. If collectionId provided → show groups directly
// 2. If no collectionId → show collection picker first
//    - Collections filtered to artifact.collections (where artifact belongs)
//    - After selection, show groups for that collection
```

**Key Files:**
- `components/collection/add-to-group-dialog.tsx` - Add collection step
- `app/collection/page.tsx` - Remove collectionId restriction

**Phase 2 Quality Gates:**
- [ ] Collection picker shows when collectionId not provided
- [ ] Only artifact's collections shown in picker
- [ ] Selecting collection shows that collection's groups
- [ ] Back button returns to collection picker
- [ ] Works end-to-end from All Collections view

---

### Phase 3: Frontend - Copy Group Feature

**Duration**: 1-2 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: `ui-engineer-enhanced`, `frontend-developer`

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent |
|---------|-----------|-------------|-------------------|-----|----------|
| FE-004 | API Client | Add `copyGroup()` function | Calls backend endpoint | 0.5 pt | frontend-developer |
| FE-005 | Hook | Add `useCopyGroup()` mutation hook | Proper cache invalidation | 0.5 pt | frontend-developer |
| FE-006 | Copy Dialog | Create `CopyGroupDialog` component | Select target, confirm, success | 2 pts | ui-engineer-enhanced |
| FE-007 | Integration | Add copy action to group management UI | Accessible from group menu | 1 pt | frontend-developer |

**Implementation Details:**

```typescript
// lib/api/groups.ts
export async function copyGroup(
  groupId: string,
  targetCollectionId: string
): Promise<Group> {
  const response = await fetch(buildUrl(`/groups/${groupId}/copy`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_collection_id: targetCollectionId }),
  });
  if (!response.ok) throw new Error('Failed to copy group');
  return response.json();
}

// hooks/use-groups.ts
export function useCopyGroup() {
  return useMutation({
    mutationFn: ({ groupId, targetCollectionId }) =>
      copyGroup(groupId, targetCollectionId),
    onSuccess: (newGroup) => {
      // Invalidate target collection groups
      queryClient.invalidateQueries({
        queryKey: groupKeys.list(newGroup.collection_id)
      });
    },
  });
}
```

**CopyGroupDialog UI:**
```
┌─────────────────────────────────────────┐
│ Copy Group to Collection                │
├─────────────────────────────────────────┤
│ Copy "My Group" (5 artifacts) to        │
│ another collection.                     │
│                                         │
│ Select target collection:               │
│ ○ Collection A (12 artifacts)           │
│ ○ Collection B (8 artifacts)            │
│ ● Collection C (23 artifacts)           │
│                                         │
│ Note: Artifacts will be added to the    │
│ target collection if not already there. │
├─────────────────────────────────────────┤
│              [Cancel]  [Copy Group]     │
└─────────────────────────────────────────┘
```

**Phase 3 Quality Gates:**
- [ ] Copy creates new group in target collection
- [ ] All artifacts copied to target
- [ ] Success toast with link to new group
- [ ] Error handling for failures
- [ ] Cache invalidation refreshes UI

---

### Phase 4: Testing & Polish

**Duration**: 1 day
**Dependencies**: Phases 1-3 complete
**Assigned Subagent(s)**: `frontend-developer`, `documentation-writer`

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent |
|---------|-----------|-------------|-------------------|-----|----------|
| QA-001 | E2E Tests | Full workflow tests | Add to group, copy group pass | 1 pt | frontend-developer |
| QA-002 | Accessibility | Audit new dialogs | WCAG 2.1 AA compliance | 0.5 pt | ui-engineer-enhanced |
| QA-003 | API Docs | Document copy endpoint | OpenAPI spec updated | 0.5 pt | documentation-writer |
| QA-004 | User Guide | Update groups documentation | Users can follow workflows | 0.5 pt | documentation-writer |

**E2E Test Scenarios:**
1. Add artifact to group from All Collections view
2. Add artifact to group from specific collection view
3. Copy group with artifacts to another collection
4. Copy group when artifacts already exist in target
5. Handle empty group copy

**Phase 4 Quality Gates:**
- [ ] E2E tests pass in CI
- [ ] Accessibility audit passes
- [ ] API documentation complete
- [ ] No P0/P1 bugs

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| artifact.collections not populated | High | Medium | Check backend, add fallback query if needed |
| Large group copy timeout | Medium | Low | Add progress indicator, consider background job |
| Cache staleness | Medium | Medium | Aggressive invalidation of both source/target |

---

## Resource Requirements

### Team
- Backend Developer: 1 day (Phase 1)
- Frontend Developer: 2-3 days (Phases 2-4)

### Skills
- FastAPI, SQLAlchemy (backend)
- React, TanStack Query (frontend)
- Playwright (E2E tests)

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Add to Group from All Collections | Working |
| Copy Group success rate | >95% |
| E2E test coverage | All scenarios |
| Performance (copy <100 artifacts) | <5 seconds |

---

## File Reference

### Backend Files (Phase 1)
| File | Changes |
|------|---------|
| `api/routers/groups.py` | Add copy endpoint |
| `api/services/groups.py` | Add copy_group method |
| `api/schemas/groups.py` | Add CopyGroupRequest schema |
| `tests/api/test_groups.py` | Add copy tests |

### Frontend Files (Phases 2-3)
| File | Changes |
|------|---------|
| `components/collection/add-to-group-dialog.tsx` | Add collection picker step |
| `components/collection/copy-group-dialog.tsx` | New file |
| `lib/api/groups.ts` | Add copyGroup function |
| `hooks/use-groups.ts` | Add useCopyGroup hook |
| `app/collection/page.tsx` | Enable for All Collections |

---

## Progress Tracking

See `.claude/progress/groups-all-collections/`

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2025-01-16
