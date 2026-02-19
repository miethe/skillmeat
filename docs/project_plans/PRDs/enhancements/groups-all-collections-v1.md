---
title: 'PRD: Groups in All Collections View'
description: Enable adding artifacts to groups from All Collections view with group
  copy functionality
audience:
- ai-agents
- developers
tags:
- prd
- planning
- groups
- collections
- refactor
created: 2025-01-16
updated: 2025-01-16
category: product-planning
status: inferred_complete
related:
- .claude/progress/quick-features/collection-card-menu-actions.md
schema_version: 2
doc_type: prd
feature_slug: groups-all-collections
---
# Feature Brief & Metadata

**Feature Name:**

> Groups in All Collections View

**Filepath Name:**

> `groups-all-collections-v1`

**Date:**

> 2025-01-16

**Author:**

> Claude (Opus 4.5)

**Related Epic(s)/PRD ID(s):**

> Collection Management Enhancement

**Related Documents:**

> - `.claude/progress/quick-features/collection-card-menu-actions.md` - Initial groups implementation
> - `skillmeat/web/types/groups.ts` - Group type definitions
> - `skillmeat/api/routers/groups.py` - Backend groups API

---

## 1. Executive Summary

This feature enables users to add artifacts to groups when viewing "All Collections", eliminating the current limitation where group functionality is only available within a specific collection view. Additionally, it introduces the ability to copy entire groups (with all contained artifacts) to other collections, enabling efficient organization workflows across collections.

**Priority:** MEDIUM

**Key Outcomes:**
- Outcome 1: Users can organize artifacts into groups from any view, not just specific collections
- Outcome 2: Groups can be replicated across collections for consistent organization
- Outcome 3: Reduced friction in artifact organization workflows

---

## 2. Context & Background

### Current State

- Groups are scoped to individual collections (required `collection_id` field)
- "Add to Group" menu action is disabled when viewing "All Collections"
- No mechanism exists for copying groups between collections
- Users must navigate to a specific collection to use group functionality

### Problem Space

Users frequently work across multiple collections and want to organize artifacts consistently. The current limitation forces users to:
1. Navigate away from "All Collections" view to add artifacts to groups
2. Manually recreate groups in multiple collections
3. Individually add the same artifacts to groups in different collections

### Current Alternatives / Workarounds

**Workaround 1: Navigate to specific collection**
- User must click into a collection, find the artifact, then add to group
- Friction: Multiple navigation steps, loses context of cross-collection view

**Workaround 2: Manually recreate groups**
- Create same-named groups in multiple collections
- Manually add artifacts to each
- Friction: Error-prone, time-consuming, no link between groups

### Architectural Context

- **Routers** - Groups router handles HTTP + validation, returns DTOs
- **Services** - GroupsService handles business logic including copy operations
- **Repositories** - GroupsRepository handles all DB I/O with proper transactions
- **Groups Model** - Groups belong to exactly one collection (collection_id required)
- **GroupArtifact Model** - Many-to-many relationship between groups and artifacts

---

## 3. Problem Statement

**User Story Format:**
> "As a user viewing All Collections, when I want to add an artifact to a group, I have to navigate to a specific collection first instead of being able to do it directly from my current view."

> "As a user who wants the same group structure in multiple collections, when I try to replicate a group, I must manually recreate it and re-add all artifacts instead of copying the entire group."

**Technical Root Cause:**
- `AddToGroupDialog` requires `collectionId` prop which isn't available in All Collections view
- No backend endpoint exists for copying groups between collections
- Frontend lacks collection selection step in add-to-group workflow

**Files Involved:**
- `skillmeat/web/components/collection/add-to-group-dialog.tsx`
- `skillmeat/web/app/collection/page.tsx`
- `skillmeat/api/routers/groups.py`
- `skillmeat/api/services/groups.py`

---

## 4. Goals & Success Metrics

### Primary Goals

**Goal 1: Enable Add to Group from All Collections View**
- Users can add any artifact to a group regardless of current view
- Two-step selection: Choose collection → Choose group(s)
- Seamless UX that doesn't disrupt workflow

**Goal 2: Enable Group Copy to Other Collections**
- Users can copy an entire group to another collection
- All artifacts in the group are copied to target collection
- Copied group maintains same name/description
- Artifacts are automatically added to the new group

**Goal 3: Maintain Data Model Integrity**
- Groups remain scoped to collections (no model changes)
- Artifacts can still belong to multiple groups across collections
- Existing group functionality unchanged

### Success Metrics

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Add to Group available | Specific collection only | All views | Feature flag / UI check |
| Group copy success rate | N/A | >95% | API error monitoring |
| User clicks to organize | 5+ (navigate, find, add) | 2 (select, confirm) | UX analytics |

---

## 5. User Personas & Journeys

### Personas

**Primary Persona: Power User**
- Role: Manages large artifact collections
- Needs: Efficient organization across multiple collections
- Pain Points: Switching contexts to organize, repetitive group creation

**Secondary Persona: Team Lead**
- Role: Maintains shared collection structures
- Needs: Consistent group organization across team collections
- Pain Points: Manual replication of organizational structures

### High-level Flow

```mermaid
graph TD
    A[User in All Collections] --> B{Add to Group clicked}
    B --> C[Select Collection]
    C --> D[Select Group(s)]
    D --> E[Artifact added to group]

    F[User views Group] --> G{Copy Group clicked}
    G --> H[Select Target Collection]
    H --> I[Confirm Copy]
    I --> J[Group + Artifacts copied]
```

---

## 6. Requirements

### 6.1 Functional Requirements

| ID | Requirement | Priority | Notes |
| :-: | ----------- | :------: | ----- |
| FR-1 | Add to Group works from All Collections view | Must | Two-step: collection then group selection |
| FR-2 | Collection picker shows only collections artifact belongs to | Must | Filter based on artifact.collections |
| FR-3 | Copy Group creates group in target collection | Must | Same name, description |
| FR-4 | Copy Group copies all artifacts to target collection | Must | Uses existing add-to-collection logic |
| FR-5 | Copy Group adds artifacts to new group | Must | Maintains positions if possible |
| FR-6 | Copy dialog shows artifact count and confirms action | Should | UX clarity |
| FR-7 | Handle duplicate group names gracefully | Should | Append "(Copy)" or increment |
| FR-8 | Show progress for large group copies | Could | For groups with many artifacts |

### 6.2 Non-Functional Requirements

**Performance:**
- Copy operation completes in <5s for groups with up to 100 artifacts
- No blocking UI during copy operation

**Security:**
- User must have access to both source and target collections
- RLS policies apply to all operations

**Accessibility:**
- All new dialogs meet WCAG 2.1 AA
- Keyboard navigation for collection/group selection

**Reliability:**
- Copy operation is atomic (all or nothing)
- Failed copies don't leave partial state

**Observability:**
- Log all copy operations with source/target IDs
- Track copy success/failure metrics

---

## 7. Scope

### In Scope

- Two-step Add to Group dialog (collection picker + group picker)
- Copy Group to Collection feature (backend + frontend)
- Copy dialog with confirmation
- Cache invalidation for both collections after copy
- Error handling and user feedback

### Out of Scope

- Global groups (groups not tied to collections) - major model change
- Bulk copy multiple groups at once - future enhancement
- Sync groups between collections - different feature
- Move group (copy + delete original) - can be added later
- Group templates/presets - separate feature

---

## 8. Dependencies & Assumptions

### External Dependencies

- None

### Internal Dependencies

- **Groups API**: Fully implemented, needs copy endpoint added
- **Collections API**: Fully implemented, no changes needed
- **AddToGroupDialog**: Exists, needs enhancement
- **Artifact.collections field**: Partially populated (TODO noted in code)

### Assumptions

- Artifacts maintain their `collections` array (needed for collection picker)
- Backend can handle atomic multi-artifact operations
- Copy operation is additive (doesn't affect source)

### Feature Flags

- `GROUPS_ALL_COLLECTIONS`: Enable add to group from All Collections view
- `GROUPS_COPY`: Enable copy group functionality

---

## 9. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
| ----- | :----: | :--------: | ---------- |
| artifact.collections not populated | High | Medium | Verify backend populates field; add fallback query |
| Large group copy timeout | Medium | Low | Implement background job for large copies |
| Duplicate group name confusion | Low | Medium | Clear naming convention with "(Copy)" suffix |
| Cache staleness after copy | Medium | Medium | Aggressive invalidation of both collections |

---

## 10. Target State (Post-Implementation)

**User Experience:**
- "Add to Group" available everywhere, regardless of current view
- Intuitive two-step selection when collection context is ambiguous
- One-click group duplication to other collections
- Clear feedback during and after operations

**Technical Architecture:**
- New `POST /groups/{id}/copy` endpoint with target_collection_id
- Enhanced `AddToGroupDialog` with optional collection picker step
- New `CopyGroupDialog` component
- Proper transaction handling for atomic copy operations

**Observable Outcomes:**
- Users can organize artifacts without navigation friction
- Group structures can be replicated efficiently
- Reduced time spent on repetitive organization tasks

---

## 11. Overall Acceptance Criteria (Definition of Done)

### Functional Acceptance

- [ ] Add to Group works from All Collections view
- [ ] Collection picker appears when collectionId not provided
- [ ] Copy Group creates group in target collection
- [ ] Copy Group copies all artifacts to target
- [ ] Copy Group adds artifacts to new group
- [ ] Error states handled gracefully

### Technical Acceptance

- [ ] Follows MeatyPrompts layered architecture
- [ ] All APIs return DTOs (no ORM models)
- [ ] Copy operation is atomic (transaction)
- [ ] ErrorResponse envelope for all errors
- [ ] Proper cache invalidation

### Quality Acceptance

- [ ] Unit tests for new backend endpoint
- [ ] Integration tests for copy operation
- [ ] E2E tests for user workflows
- [ ] Accessibility compliance for new dialogs

### Documentation Acceptance

- [ ] API documentation for copy endpoint
- [ ] Component documentation for new dialogs
- [ ] Updated user guide for group features

---

## 12. Assumptions & Open Questions

### Assumptions

- artifact.collections is or can be made available in frontend
- Users expect "copy" semantics (not "move")
- Group positions don't need to be preserved exactly in copy

### Open Questions

- [x] **Q1**: Should copied group have same name or indicate it's a copy?
  - **A**: If the group doesn't exist yet, same name. Otherwise,append " (Copy)" to name to avoid collision
- [x] **Q2**: What if artifact already exists in target collection?
  - **A**: Skip adding to collection, just add to group (idempotent)
- [ ] **Q3**: Should we track lineage between original and copied groups?
  - **A**: TBD - Out of scope for v1, consider for future

---

## 13. Appendices & References

### Related Documentation

- **Progress File**: `.claude/progress/quick-features/collection-card-menu-actions.md`

### Symbol References

- **Backend**: `GroupsService`, `GroupsRepository`, `GroupsRouter`
- **Frontend**: `useGroups`, `useAddArtifactToGroup`, `AddToGroupDialog`

### File Locations

| Component | Path |
|-----------|------|
| Add to Group Dialog | `web/components/collection/add-to-group-dialog.tsx` |
| Groups API Client | `web/lib/api/groups.ts` |
| Groups Hooks | `web/hooks/use-groups.ts` |
| Groups Types | `web/types/groups.ts` |
| Groups Router | `api/routers/groups.py` |
| Groups Service | `api/services/groups.py` |
| Groups Repository | `api/repositories/groups.py` |

---

## Implementation

### Phased Approach

**Phase 1: Backend - Copy Group Endpoint**
- Add `POST /groups/{id}/copy` endpoint
- Implement atomic copy in service layer
- Handle duplicate names, existing artifacts
- Add tests

**Phase 2: Frontend - Add to Group Enhancement**
- Add collection picker step to `AddToGroupDialog`
- Conditional rendering based on collectionId prop
- Wire up in collection page for All Collections view
- Add tests

**Phase 3: Frontend - Copy Group Feature**
- Create `CopyGroupDialog` component
- Add `useCopyGroup` hook
- Add `copyGroup` API function
- Integrate into group management UI
- Add tests

**Phase 4: Polish & Documentation**
- E2E tests for full workflows
- Accessibility audit and fixes
- API documentation
- User guide updates

### Epics & User Stories Backlog

| Story ID | Short Name | Description | Acceptance Criteria | Estimate |
|----------|-----------|-------------|-------------------|----------|
| GAC-001 | Copy Group Backend | Add copy endpoint | Endpoint works, tests pass | 3 pts |
| GAC-002 | Collection Picker | Add collection step to dialog | Shows when no collectionId | 2 pts |
| GAC-003 | Wire All Collections | Enable in All Collections view | Menu item works | 1 pt |
| GAC-004 | Copy Group Hook | Frontend hook for copy | Mutation works | 1 pt |
| GAC-005 | Copy Group Dialog | UI for copy operation | Dialog works end-to-end | 2 pts |
| GAC-006 | Integration in UI | Add copy option to group menu | Accessible from group actions | 1 pt |
| GAC-007 | E2E Tests | Full workflow tests | All scenarios covered | 2 pts |
| GAC-008 | Documentation | API + user docs | Docs complete | 1 pt |

**Total Estimate:** 13 points

---

**Progress Tracking:**

See progress tracking: `.claude/progress/groups-all-collections/`
