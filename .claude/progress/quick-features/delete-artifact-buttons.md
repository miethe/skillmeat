# Quick Feature: Delete Artifact Buttons

**Status**: completed
**Created**: 2026-02-04
**Scope**: 4-5 files, single session

## Description

Add Delete Artifact functionality to both /collection and /manage pages:
- Kebab menus on artifact cards should include Delete option
- Modals should have kebab menu in header with Delete option
- All Delete buttons call existing ArtifactDeletionDialog

## Files to Modify

| File | Change |
|------|--------|
| `web/components/collection/artifact-browse-card.tsx` | Add Delete option to DropdownMenu |
| `web/components/manage/artifact-operations-card.tsx` | Add kebab menu with Delete option |
| `web/components/entity/unified-entity-modal.tsx` | Add kebab menu to header actions |
| `web/components/manage/ManageArtifactModal.tsx` | Add kebab menu to header actions |
| `web/app/manage/page.tsx` | Wire up ArtifactDeletionDialog (replace confirm()) |

## Implementation Tasks

### TASK-1: Add Delete to ArtifactBrowseCard
- Add `onDelete?: (artifact: Artifact) => void` prop
- Add Delete menu item with destructive styling
- Wire up in parent (collection page already has handler)

### TASK-2: Add Kebab Menu to ArtifactOperationsCard
- Add DropdownMenu with MoreHorizontal trigger
- Include Delete option with destructive styling
- Add `onDelete?: (artifact: Artifact) => void` prop

### TASK-3: Add Kebab Menu to UnifiedEntityModal Header
- Use ModalHeader actions slot for kebab menu
- Include Delete option
- Ensure proper spacing from close button (X)
- Pass onDelete prop up from parent

### TASK-4: Add Kebab Menu to ManageArtifactModal Header
- Same pattern as UnifiedEntityModal
- Include Delete option in dropdown

### TASK-5: Wire Up /manage Page with ArtifactDeletionDialog
- Replace confirm() with ArtifactDeletionDialog
- Add state for artifactToDelete and showDeletionDialog
- Add handler for card and modal delete actions

## Quality Gates

- [ ] `pnpm typecheck`
- [ ] `pnpm lint`
- [ ] `pnpm build`
- [ ] Manual test: Delete from /collection card
- [ ] Manual test: Delete from /collection modal
- [ ] Manual test: Delete from /manage card
- [ ] Manual test: Delete from /manage modal
