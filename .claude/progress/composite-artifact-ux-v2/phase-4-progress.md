---
type: progress
schema_version: 2
doc_type: progress
prd: composite-artifact-ux-v2
feature_slug: composite-artifact-ux-v2
phase: 4
title: Collection Plugin Management UI
status: pending
created: '2026-02-19'
updated: '2026-02-19'
prd_ref: docs/project_plans/PRDs/features/composite-artifact-ux-v2.md
plan_ref: docs/project_plans/implementation_plans/features/composite-artifact-ux-v2.md
overall_progress: 0
completion_estimate: on-track
total_tasks: 12
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- ui-engineer-enhanced
- frontend-developer
contributors: []
tasks:
- id: CUX-P4-01
  description: PluginMemberIcons component — type icons for members (up to 5, +N overflow),
    responsive sizing, accessible
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 1pt
  priority: medium
- id: CUX-P4-02
  description: Plugin Card Variant — extend ArtifactBrowseCard for plugin display
    with icon, name, description, member icons, count badge, actions menu
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - CUX-P4-01
  estimated_effort: 2pt
  priority: high
- id: CUX-P4-03
  description: MemberSearchInput component — searchable artifact picker with debounced
    search, result filtering, exclusion of already-added members
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - CUX-P1-01
  estimated_effort: 2pt
  priority: high
- id: CUX-P4-04
  description: MemberList component — sortable list with drag-to-reorder, keyboard
    Up/Down support, remove actions, WCAG compliant
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - CUX-P4-03
  estimated_effort: 2pt
  priority: high
- id: CUX-P4-05
  description: CreatePluginDialog — dialog form with name, description, tags, pre-populated
    members; creates via POST /api/v1/composites
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - CUX-P4-03
  - CUX-P4-04
  estimated_effort: 3pt
  priority: high
- id: CUX-P4-06
  description: Create Plugin Button — add 'New Plugin' button to collection toolbar
    and bulk action bar
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - CUX-P4-05
  estimated_effort: 1pt
  priority: medium
- id: CUX-P4-07
  description: PluginMembersTab — detail page 'Members' tab with member table, add/remove/reorder,
    'Add Member' button
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - CUX-P4-04
  estimated_effort: 2pt
  priority: high
- id: CUX-P4-08
  description: Member Actions Menu — View Details, Deploy, Remove from Plugin; destructive
    styling for Remove
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - CUX-P4-07
  estimated_effort: 1pt
  priority: medium
- id: CUX-P4-09
  description: Plugin Detail Modal — extend BaseArtifactModal for plugins with Members
    tab + existing metadata/sync/deploy tabs
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - CUX-P4-07
  estimated_effort: 1pt
  priority: medium
- id: CUX-P4-10
  description: 'Mutation hooks: useCreateComposite, useUpdateComposite, useDeleteComposite,
    useManageCompositeMembers with optimistic updates'
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - CUX-P1-08
  estimated_effort: 2pt
  priority: high
- id: CUX-P4-11
  description: 'Accessibility audit — WCAG 2.1 AA compliance for all plugin UI components:
    axe checks, keyboard nav, screen reader support'
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - CUX-P4-10
  estimated_effort: 2pt
  priority: high
- id: CUX-P4-12
  description: Playwright E2E test — create plugin from selection, add member, remove
    member, verify in collection
  status: pending
  assigned_to:
  - frontend-developer
  dependencies:
  - CUX-P4-10
  estimated_effort: 2pt
  priority: high
parallelization:
  batch_1:
  - CUX-P4-01
  - CUX-P4-03
  - CUX-P4-10
  batch_2:
  - CUX-P4-02
  - CUX-P4-04
  batch_3:
  - CUX-P4-05
  - CUX-P4-07
  batch_4:
  - CUX-P4-06
  - CUX-P4-08
  - CUX-P4-09
  batch_5:
  - CUX-P4-11
  - CUX-P4-12
  critical_path:
  - CUX-P4-03
  - CUX-P4-04
  - CUX-P4-05
  - CUX-P4-06
  estimated_total_time: 3-4 days
blockers: []
success_criteria:
- id: SC-P4-1
  description: Plugin card renders in collection grid with correct icon, colors, member
    info
  status: pending
- id: SC-P4-2
  description: Plugin creation form creates composite via API; updates collection
    immediately
  status: pending
- id: SC-P4-3
  description: Member add/remove/reorder calls correct endpoints; updates persist
  status: pending
- id: SC-P4-4
  description: Plugin detail view shows all members with full management
  status: pending
- id: SC-P4-5
  description: 'Keyboard navigation works: Tab, Enter, Escape, Arrow keys'
  status: pending
- id: SC-P4-6
  description: Screen readers announce plugin info, member counts, form labels
  status: pending
- id: SC-P4-7
  description: Drag-to-reorder provides visual feedback; accessible via keyboard arrows
  status: pending
- id: SC-P4-8
  description: All axe accessibility checks pass
  status: pending
- id: SC-P4-9
  description: 'E2E test passes: create -> add -> remove -> verify in collection'
  status: pending
- id: SC-P4-10
  description: No regression in existing collection or artifact detail views
  status: pending
files_modified: []
progress: 41
---
# Phase 4: Collection Plugin Management UI

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/composite-artifact-ux-v2/phase-4-progress.md -t CUX-P4-01 -s completed

python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/composite-artifact-ux-v2/phase-4-progress.md \
  --updates "CUX-P4-01:completed,CUX-P4-03:completed,CUX-P4-10:completed"
```

---

## Objective

Build comprehensive collection UI for plugin browsing, creation, and member management. Implements 12 tasks including new components, mutation hooks, accessibility audit, and E2E testing. Largest phase -- broken into 5 batches for parallel work.

---

## Orchestration Quick Reference

### Batch 1 (Foundation — launch immediately)

```
Task("ui-engineer-enhanced", "CUX-P4-01: Create PluginMemberIcons component.
  File: skillmeat/web/components/collection/plugin-member-icons.tsx
  Display type icons for members (up to 5, +N overflow). Responsive sizing. Accessible.")

Task("frontend-developer", "CUX-P4-03: Create MemberSearchInput component.
  File: skillmeat/web/components/shared/member-search-input.tsx
  Searchable artifact picker, debounced search, result filtering, exclude already-added.")

Task("frontend-developer", "CUX-P4-10: Create mutation hooks for composite CRUD.
  Files: skillmeat/web/hooks/useCreateComposite.ts, useUpdateComposite.ts, useDeleteComposite.ts, useManageCompositeMembers.ts
  TanStack Query mutations with optimistic updates and rollback.")
```

### Batch 2 (After Batch 1 foundations)

```
Task("ui-engineer-enhanced", "CUX-P4-02: Plugin Card Variant for ArtifactBrowseCard.
  File: skillmeat/web/components/collection/artifact-browse-card.tsx
  Extend for plugin: Blocks icon (indigo), name, description, member icons, count badge, actions.")

Task("ui-engineer-enhanced", "CUX-P4-04: Create MemberList component.
  File: skillmeat/web/components/shared/member-list.tsx
  Sortable with drag-to-reorder, keyboard Up/Down, remove actions, WCAG compliant.")
```

### Batch 3 (After Batch 2)

```
Task("ui-engineer-enhanced", "CUX-P4-05: Create CreatePluginDialog.
  File: skillmeat/web/components/collection/create-plugin-dialog.tsx
  Form: name (required), description, tags, pre-populated members. Creates via POST /api/v1/composites.")

Task("ui-engineer-enhanced", "CUX-P4-07: Create PluginMembersTab.
  File: skillmeat/web/components/entity/plugin-members-tab.tsx
  Detail page Members tab with member table, add/remove/reorder, 'Add Member' button.")
```

### Batch 4 (After Batch 3)

```
Task("ui-engineer-enhanced", "CUX-P4-06: Create Plugin Button in toolbar.
  Add 'New Plugin' button to collection toolbar and bulk action bar. Opens CreatePluginDialog.")

Task("ui-engineer-enhanced", "CUX-P4-08 + CUX-P4-09: Member Actions Menu + Plugin Detail Modal.
  Files: skillmeat/web/components/entity/plugin-detail-modal.tsx
  Menu: View Details, Deploy, Remove. Modal: extend BaseArtifactModal with Members tab.")
```

### Batch 5 (Polish — after Batch 4)

```
Task("ui-engineer-enhanced", "CUX-P4-11: Accessibility audit for all plugin UI components.
  WCAG 2.1 AA: axe checks, keyboard nav, screen reader support for all new components.")

Task("frontend-developer", "CUX-P4-12: Playwright E2E for collection plugin management.
  File: skillmeat/web/tests/e2e/collection-plugin-management.spec.ts
  Create plugin -> add member -> remove member -> verify in collection.")
```

---

## Known Gotchas

- Phase 1 (type system, CRUD API) and Phase 3 (import flow) must be complete.
- Follow UI specs in `docs/project_plans/implementation_plans/features/composite-artifact-ux-v2/ui-specs.md` exactly.
- Use `text-indigo-500` color token and Lucide `Blocks` icon throughout.
- Use `@dnd-kit/sortable` for drag-reorder if available; otherwise native HTML drag + Up/Down buttons.
- All components must work on mobile (<640px), tablet (640-1024px), and desktop (>1024px).
- CUX-P4-10 (mutation hooks) can start early since it depends only on Phase 1 API, not Phase 3/4 UI.
