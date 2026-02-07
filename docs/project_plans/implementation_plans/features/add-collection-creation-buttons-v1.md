---
title: Add Collection Creation Buttons - Implementation Plan
description: Add buttons to create new collections from the /collection page and artifact
  Collections tab
audience:
- ai-agents
- developers
tags:
- implementation
- collections
- ui
- frontend
created: 2025-12-13
updated: '2026-02-07'
category: product-planning
status: completed
---

# Implementation Plan: Add Collection Creation Buttons

## Executive Summary

**Goal**: Enable users to create new collections from two key locations:
1. The `/collection` page header
2. The Collections tab in the unified entity modal (artifact detail view)

**Scope**: Frontend-only changes. The `CreateCollectionDialog` component already exists and is fully functional.

**Effort**: ~2 story points (1-2 hours)

**Risk**: Low - reusing existing dialog component

---

## Current State Analysis

### Existing Components

| Component | Location | Status |
|-----------|----------|--------|
| `CreateCollectionDialog` | `components/collection/create-collection-dialog.tsx` | ✅ Complete |
| `CollectionHeader` | `components/collection/collection-header.tsx` | Missing create button |
| `ModalCollectionsTab` | `components/entity/modal-collections-tab.tsx` | Missing create option |
| `MoveCopyDialog` | `components/collection/move-copy-dialog.tsx` | Optional enhancement |

### User Flow Gaps

1. **Collection Page**: User visits `/collection`, sees "All Collections" header but no way to create a new collection
2. **Artifact Modal**: User opens artifact → Collections tab → sees "Add to Collection" but if no collections exist or they want a new one, they can't create one from here

---

## Implementation Strategy

### Phase 1: Collection Page Header Button

**Location**: `CollectionHeader` component

**Approach**: Add a "New Collection" button that appears in "All Collections" mode (when no specific collection is selected). This button opens the existing `CreateCollectionDialog`.

**Files to Modify**:
- `skillmeat/web/components/collection/collection-header.tsx`
- `skillmeat/web/app/collection/page.tsx` (wire up dialog state)

### Phase 2: Modal Collections Tab Enhancement

**Location**: `ModalCollectionsTab` component

**Approach**: Add a "Create New Collection" button/link next to or below the "Add to Collection" button. When clicked, it opens `CreateCollectionDialog`. After successful creation, optionally auto-add the artifact to the new collection.

**Files to Modify**:
- `skillmeat/web/components/entity/modal-collections-tab.tsx`

### Phase 3: MoveCopyDialog Enhancement (Optional)

**Location**: `MoveCopyDialog` component

**Approach**: When no collections are available, show a "Create Collection" link in the empty state.

**Files to Modify**:
- `skillmeat/web/components/collection/move-copy-dialog.tsx`

---

## Task Breakdown

### Phase 1: Collection Page Header Button

| ID | Task | Description | Acceptance Criteria | Estimate |
|----|------|-------------|---------------------|----------|
| TASK-1.1 | Add onCreate prop to CollectionHeader | Add optional `onCreate` callback prop to CollectionHeader component | Prop typed, passed through | 10m |
| TASK-1.2 | Add "New Collection" button to header | Display button in header when `isAllCollections` is true and `onCreate` is provided | Button visible in All Collections mode | 15m |
| TASK-1.3 | Wire up dialog in collection page | Add dialog state and pass `onCreate` to header, render `CreateCollectionDialog` | Dialog opens on button click | 15m |

**Assigned Subagent(s)**: `ui-engineer-enhanced`

**Quality Gates**:
- [ ] Button only appears in "All Collections" mode
- [ ] Dialog opens correctly
- [ ] Collection created and list refreshes
- [ ] New collection auto-selected after creation

### Phase 2: Modal Collections Tab Enhancement

| ID | Task | Description | Acceptance Criteria | Estimate |
|----|------|-------------|---------------------|----------|
| TASK-2.1 | Add CreateCollectionDialog to tab | Import and render `CreateCollectionDialog` with state management | Dialog integrated | 10m |
| TASK-2.2 | Add "Create New" button to header row | Add button next to "Add to Collection" that opens create dialog | Button visible and functional | 10m |
| TASK-2.3 | Add "Create New" link to empty state | In empty state, add link to create collection | Link visible when no collections | 10m |
| TASK-2.4 | Auto-add artifact after creation (optional) | After collection created, optionally add current artifact to it | Artifact added to new collection | 15m |

**Assigned Subagent(s)**: `ui-engineer-enhanced`

**Quality Gates**:
- [ ] "Create New Collection" button visible in header
- [ ] Empty state shows create link
- [ ] Dialog opens and creates collection
- [ ] Collections list refreshes after creation
- [ ] (Optional) Artifact auto-added to new collection

### Phase 3: MoveCopyDialog Enhancement (Optional)

| ID | Task | Description | Acceptance Criteria | Estimate |
|----|------|-------------|---------------------|----------|
| TASK-3.1 | Add create link to empty state | In "No other collections available" state, add "Create Collection" link | Link visible in empty state | 15m |
| TASK-3.2 | Handle nested dialog | Open CreateCollectionDialog from within MoveCopyDialog | Nested dialog works correctly | 10m |

**Assigned Subagent(s)**: `ui-engineer-enhanced`

**Quality Gates**:
- [ ] Create link appears when no collections available
- [ ] Dialog opens correctly (nested dialog handling)
- [ ] New collection appears in list after creation

---

## File Changes Summary

| File | Changes |
|------|---------|
| `components/collection/collection-header.tsx` | Add `onCreate` prop, render "New Collection" button |
| `app/collection/page.tsx` | Add dialog state, wire up `CreateCollectionDialog` |
| `components/entity/modal-collections-tab.tsx` | Add create button, create link in empty state, integrate dialog |
| `components/collection/move-copy-dialog.tsx` | (Optional) Add create link in empty state |

---

## UI Specifications

### Collection Page Header Button

```
┌─────────────────────────────────────────────────────────────────┐
│ All Collections  [12 artifacts]                    [+ New Collection] │
│ Browse artifacts across all collections                          │
└─────────────────────────────────────────────────────────────────┘
```

- Button style: `variant="default"` or `variant="outline"` with `FolderPlus` icon
- Position: Right side of header, aligned with artifact count badge
- Only visible in "All Collections" mode (not when viewing a specific collection)

### Modal Collections Tab

```
┌─────────────────────────────────────────────────────────────────┐
│ Collections & Groups              [+ Add to Collection] [+ New] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                   (collection list or empty state)              │
│                                                                 │
│     Empty state includes: "Create New Collection" link          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

- "New" button: Compact, next to "Add to Collection"
- Empty state: Include "Create New Collection" as clickable link

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Collection creation accessible from page | ✅ Yes |
| Collection creation accessible from modal | ✅ Yes |
| No breaking changes to existing functionality | ✅ Yes |
| TypeScript compiles without errors | ✅ Yes |

---

## Orchestration Quick Reference

### Batch 1 (Sequential - Phase 1 then Phase 2)

**Phase 1** - Collection Header:
```
Task("ui-engineer-enhanced", "TASK-1.1-1.3: Add 'New Collection' button to collection page header

Files:
- skillmeat/web/components/collection/collection-header.tsx
- skillmeat/web/app/collection/page.tsx

Requirements:
1. Add `onCreate?: () => void` prop to CollectionHeader
2. When `isAllCollections` is true AND `onCreate` is provided, show 'New Collection' button
3. Button should use FolderPlus icon, variant='outline', positioned right of artifact count badge
4. In page.tsx, add state for dialog: `const [showCreateDialog, setShowCreateDialog] = useState(false)`
5. Pass `onCreate={() => setShowCreateDialog(true)}` to CollectionHeader
6. Render CreateCollectionDialog with open/onOpenChange props

Existing pattern reference: EditCollectionDialog is already integrated in page.tsx (lines 302-310)
CreateCollectionDialog is at components/collection/create-collection-dialog.tsx")
```

**Phase 2** - Modal Collections Tab:
```
Task("ui-engineer-enhanced", "TASK-2.1-2.3: Add 'Create New Collection' option to ModalCollectionsTab

File: skillmeat/web/components/entity/modal-collections-tab.tsx

Requirements:
1. Import CreateCollectionDialog from '@/components/collection/create-collection-dialog'
2. Add state: `const [showCreateDialog, setShowCreateDialog] = useState(false)`
3. Add 'New' button next to 'Add to Collection' button in header row (line 122-125)
   - Use Button variant='ghost' size='sm' with FolderPlus icon
   - Text: 'New' (keep it short to fit next to existing button)
4. In empty state (lines 131-145), add 'or create a new collection' link after the existing 'Add to Collection' button
5. Render CreateCollectionDialog at end of component

Pattern: Follow existing dialog integration pattern from MoveCopyDialog (lines 186-199)")
```

### Batch 2 (Optional - Phase 3)

```
Task("ui-engineer-enhanced", "TASK-3.1-3.2: Add 'Create Collection' link to MoveCopyDialog empty state

File: skillmeat/web/components/collection/move-copy-dialog.tsx

Requirements:
1. Import CreateCollectionDialog
2. Add state for create dialog
3. In empty state (lines 178-181), add 'Create one now' link
4. Render CreateCollectionDialog
5. After creation, new collection should appear in list (automatic via useCollectionContext refresh)

Note: Handle nested dialog UX - create dialog should close before user returns to move/copy dialog")
```

---

## Dependencies

- None - all required components exist

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Dialog state conflicts | Low | Low | Use separate state variables |
| Nested dialog UX issues | Low | Medium | Test dialog close/open sequence |

---

## Post-Implementation

- [ ] Manual testing of both button locations
- [ ] Verify collection list refreshes after creation
- [ ] Check TypeScript compilation
- [ ] Visual review of button placement
