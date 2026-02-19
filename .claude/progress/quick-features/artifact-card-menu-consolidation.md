---
feature: artifact-card-menu-consolidation
status: completed
created: 2026-01-28
priority: high
complexity: medium
files_affected:
- skillmeat/web/components/shared/unified-card-actions.tsx (NEW)
- skillmeat/web/components/collection/artifact-grid.tsx
- skillmeat/web/components/collection/artifact-list.tsx
- skillmeat/web/components/entity/entity-card.tsx
- skillmeat/web/components/entity/entity-row.tsx
- skillmeat/web/components/entity/entity-actions.tsx
schema_version: 2
doc_type: quick_feature
feature_slug: artifact-card-menu-consolidation
---

# Quick Feature: Artifact Card Menu Consolidation

## Problem Statement

The `/collection` and `/manage` pages have inconsistent artifact card menu implementations:

1. **Icon inconsistency**: Collection uses meatballs (`MoreHorizontal`), Manage uses kebab (`MoreVertical`)
2. **Visibility inconsistency**: Collection grid hides menu by default (opacity-0, show on hover), Manage always visible
3. **Broken behavior**: Collection page has a non-functional always-visible kebab menu PLUS a working hover meatballs menu
4. **Duplicated code**: `ArtifactCardActions` (collection) and `EntityActions` (manage) implement similar menus separately

## Solution

Create a single shared `UnifiedCardActions` component that:
- Uses meatballs icon (`MoreHorizontal`)
- Shows on hover (opacity-0 → opacity-100 on hover, always visible on touch)
- Supports all action types from both pages via callback props
- Is used by both `/collection` and `/manage` pages

## Tasks

- [x] TASK-1: Create `UnifiedCardActions` component in `components/shared/`
  - Meatballs icon with hover visibility
  - Props for all action callbacks (deploy, sync, edit, delete, etc.)
  - Conditional menu items based on which callbacks are provided
  - Assigned: ui-engineer-enhanced
  - Completed: 2026-01-28

- [x] TASK-2: Refactor collection page components to use `UnifiedCardActions`
  - Update `artifact-grid.tsx` - remove `ArtifactCardActions`, use shared component
  - Update `artifact-list.tsx` - remove `ArtifactRowActions`, use shared component
  - Assigned: ui-engineer-enhanced
  - Completed: 2026-01-28

- [x] TASK-3: Refactor manage page components to use `UnifiedCardActions`
  - Update `entity-card.tsx` - uses `UnifiedCard` which now uses `UnifiedCardActions`
  - Update `entity-row.tsx` - use shared component
  - Assigned: ui-engineer-enhanced
  - Completed: 2026-01-28

- [x] TASK-4: Remove deprecated action components
  - `entity-actions.tsx` updated to match new patterns (meatballs icon, hover visibility)
  - Marked as deprecated, kept for backward compatibility with existing tests
  - Clean up unused imports
  - Assigned: ui-engineer-enhanced
  - Completed: 2026-01-28

- [x] TASK-5: Verify quality gates
  - pnpm build: PASSED
  - pnpm lint: PASSED (no errors in modified files)
  - pnpm type-check: Pre-existing test file errors only (not related to changes)
  - Assigned: orchestrator
  - Completed: 2026-01-28

## Design Decisions

### Menu Icon: Meatballs (`MoreHorizontal`)
- More common in modern UI (Linear, Notion)
- Horizontal orientation works better in card corners

### Visibility: Hover with touch fallback
```css
opacity-0 transition-opacity group-hover:opacity-100 touch:opacity-100
```
- Clean appearance on desktop
- Always accessible on touch devices

### Props Pattern
```typescript
interface UnifiedCardActionsProps {
  artifact: Artifact;
  // All callbacks optional - menu items shown only if callback provided
  onDeploy?: () => void;
  onSync?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  onViewDiff?: () => void;
  onRollback?: () => void;
  onAddToGroup?: () => void;
  onMoveToCollection?: () => void;
  // Status-based conditional items
  showDiffOption?: boolean;  // Only when status === "modified"
  showRollbackOption?: boolean;  // Only when status === "modified" | "conflict"
}
```

## Success Criteria

1. Both pages use identical menu component
2. Meatballs icon on hover for both pages
3. No broken/non-functional menu buttons
4. All existing functionality preserved
5. Quality gates pass
