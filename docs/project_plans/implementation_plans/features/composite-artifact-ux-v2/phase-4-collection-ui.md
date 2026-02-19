---
schema_version: 2
doc_type: phase_plan
title: 'Phase 4: Collection Plugin Management UI'
status: inferred_complete
created: 2026-02-19
updated: 2026-02-19
feature_slug: composite-artifact-ux-v2
feature_version: v2
phase: 4
phase_title: Collection Plugin Management UI
prd_ref: /docs/project_plans/PRDs/features/composite-artifact-ux-v2.md
plan_ref: /docs/project_plans/implementation_plans/features/composite-artifact-ux-v2.md
entry_criteria:
- Phase 1 complete (type system, CRUD API)
- Phase 3 complete (import flow wiring)
- UI specs reviewed and approved
- Design system tokens defined (indigo-500, Blocks icon, spacing, animations)
exit_criteria:
- Plugin cards render in collection grid with correct styling
- Plugin creation form creates composite via API
- Plugin detail page shows members with full management (add/remove/reorder)
- All new UI components pass WCAG 2.1 AA axe checks
- Keyboard navigation works (Tab, Enter, Escape, Arrow keys)
- Collection plugin creation E2E test passes
related_documents:
- /docs/project_plans/implementation_plans/features/composite-artifact-ux-v2.md
- /docs/project_plans/implementation_plans/features/composite-artifact-ux-v2/ui-specs.md
---
# Phase 4: Collection Plugin Management UI

**Duration**: 3-4 days
**Dependencies**: Phase 1 complete, Phase 3 complete
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

## Overview

Build comprehensive collection UI for plugin browsing, creation, and member management. Implements 12 tasks including new components, mutation hooks, accessibility, and E2E testing. This phase is the largest and should be broken into multiple batches for parallel work.

## Task Groups

### Group 1: Foundation Components (2-3 days parallel)

**CUX-P4-01**: `PluginMemberIcons` Component
Small component displaying type icons for plugin members (up to 5, +N overflow). Responsive sizing, accessibility.
**Est**: 1 pt | **Subagent**: ui-engineer-enhanced

**CUX-P4-03**: `MemberSearchInput` Component
Searchable artifact picker with debounced search, result filtering, exclusion of already-added members.
**Est**: 2 pts | **Subagent**: frontend-developer
**Depends on**: CUX-P1-01

**CUX-P4-04**: `MemberList` Component
Sortable member list with drag-to-reorder, keyboard Up/Down arrow support, remove actions, WCAG compliant.
**Est**: 2 pts | **Subagent**: ui-engineer-enhanced
**Depends on**: CUX-P4-03

---

### Group 2: Creation Flow (2 days)

**CUX-P4-05**: `CreatePluginDialog`
Dialog form: name (required), description, tags, pre-populated members (from bulk select or empty). Creates via `POST /api/v1/composites`.
**Est**: 3 pts | **Subagent**: ui-engineer-enhanced
**Depends on**: CUX-P4-03, CUX-P4-04

**CUX-P4-06**: Create Plugin Button
Add "New Plugin" button to collection toolbar and bulk action bar.
**Est**: 1 pt | **Subagent**: ui-engineer-enhanced
**Depends on**: CUX-P4-05

---

### Group 3: Plugin Cards & Display (2 days parallel)

**CUX-P4-02**: Plugin Card Variant
Extend `ArtifactBrowseCard` for plugin display: icon (Blocks, indigo), name, description, member icons, count badge, actions menu.
**Est**: 2 pts | **Subagent**: ui-engineer-enhanced
**Depends on**: CUX-P4-01

---

### Group 4: Detail Page & Member Management (2-3 days)

**CUX-P4-07**: `PluginMembersTab`
Detail page "Members" tab: member table with add/remove/reorder capabilities. Header with "Add Member" button.
**Est**: 2 pts | **Subagent**: ui-engineer-enhanced
**Depends on**: CUX-P4-04

**CUX-P4-08**: Member Actions Menu
Menu for each member: View Details, Deploy, Remove from Plugin. Destructive styling for Remove.
**Est**: 1 pt | **Subagent**: ui-engineer-enhanced
**Depends on**: CUX-P4-07

**CUX-P4-09**: Plugin Detail Modal
Extend `BaseArtifactModal` for plugins with Members tab + existing metadata/sync/deploy tabs.
**Est**: 1 pt | **Subagent**: ui-engineer-enhanced
**Depends on**: CUX-P4-07

---

### Group 5: Hooks & API Integration (1-2 days)

**CUX-P4-10**: Mutation Hooks
Create `useCreateComposite`, `useUpdateComposite`, `useDeleteComposite`, `useManageCompositeMembers`. All use TanStack Query; handle loading/error/success; implement optimistic updates with rollback.
**Est**: 2 pts | **Subagent**: frontend-developer
**Depends on**: CUX-P1-08

---

### Group 6: Polish & Testing (1-2 days)

**CUX-P4-11**: Accessibility Audit
WCAG 2.1 AA compliance for all plugin UI components: axe checks pass, keyboard nav works, screen reader support.
**Est**: 2 pts | **Subagent**: ui-engineer-enhanced
**Depends on**: CUX-P4-10

**CUX-P4-12**: Collection Plugin E2E
Playwright E2E test: create plugin from selection → add member → remove member → verify in collection.
**Est**: 2 pts | **Subagent**: frontend-developer
**Depends on**: CUX-P4-10

---

## Quality Gates

- [ ] Plugin card renders in collection grid with correct icon, colors, member info
- [ ] Plugin creation form creates composite via API; updates collection immediately
- [ ] Member add/remove/reorder calls correct endpoints; updates persist
- [ ] Plugin detail view shows all members with full management
- [ ] Keyboard navigation works: Tab focuses elements, Enter activates, Escape closes
- [ ] Screen readers announce plugin info, member counts, form labels
- [ ] Drag-to-reorder provides visual feedback; accessible via keyboard arrows
- [ ] All axe accessibility checks pass
- [ ] E2E test passes: create → add → remove → verify in collection
- [ ] No regression in existing collection or artifact detail views

---

## Files Modified/Created

### Frontend Components
- **Created**: `skillmeat/web/components/collection/plugin-member-icons.tsx`
- **Created**: `skillmeat/web/components/shared/member-search-input.tsx`
- **Created**: `skillmeat/web/components/shared/member-list.tsx`
- **Modified**: `skillmeat/web/components/collection/artifact-browse-card.tsx` (extend for plugin)
- **Created**: `skillmeat/web/components/collection/create-plugin-dialog.tsx`
- **Created**: `skillmeat/web/components/entity/plugin-members-tab.tsx`
- **Created**: `skillmeat/web/components/entity/plugin-detail-modal.tsx` (or extend unified modal)

### Frontend Hooks
- **Created**: `skillmeat/web/hooks/useCreateComposite.ts`
- **Created**: `skillmeat/web/hooks/useUpdateComposite.ts`
- **Created**: `skillmeat/web/hooks/useDeleteComposite.ts`
- **Created**: `skillmeat/web/hooks/useManageCompositeMembers.ts`

### Tests
- **Created**: `skillmeat/web/__tests__/components/collection/plugin-member-icons.test.tsx`
- **Created**: `skillmeat/web/__tests__/components/shared/member-search-input.test.tsx`
- **Created**: `skillmeat/web/__tests__/components/shared/member-list.test.tsx`
- **Created**: `skillmeat/web/__tests__/components/collection/create-plugin-dialog.test.tsx`
- **Created**: `skillmeat/web/__tests__/hooks/useCreateComposite.test.ts`
- **Created**: `skillmeat/web/tests/e2e/collection-plugin-management.spec.ts`

---

## Implementation Notes

1. **UI Specs Reference**: Follow `/docs/project_plans/implementation_plans/features/composite-artifact-ux-v2/ui-specs.md` exactly for component designs and behavior.
2. **Color Token**: Use `text-indigo-500` for plugin type throughout (icon, badges, accents).
3. **Icon**: Use Lucide `Blocks` icon for plugin type.
4. **Spacing**: Follow existing 4px/8px grid (p-4, space-y-4, gap-2, gap-3).
5. **Drag Library**: Use `@dnd-kit/sortable` if available; otherwise native HTML drag-and-drop with Up/Down buttons.
6. **Animations**: Follow existing animation patterns (fade-in for add, fade-out for remove, 150ms default).
7. **Error Handling**: Display errors as toast notifications; inline errors under form fields.
8. **Loading States**: Show spinners in buttons, skeleton loaders for lists.
9. **Empty States**: Show helpful empty state illustrations (e.g., "No members yet", "Add artifacts to this plugin").
10. **Responsive**: All components should work on mobile (< 640px), tablet (640-1024px), and desktop (> 1024px).

---

## Parallelization Strategy

- **Batch 1 (Group 1)**: CUX-P4-01, CUX-P4-03, CUX-P4-04 run in parallel (foundation components). Estimated 2-3 days.
- **Batch 2 (Group 2)**: CUX-P4-05, CUX-P4-06 can start once CUX-P4-03 and CUX-P4-04 are done. Estimated 2 days.
- **Batch 3 (Group 3)**: CUX-P4-02 depends on CUX-P4-01; can run in parallel with Batch 2. Estimated 2 days.
- **Batch 4 (Group 4)**: CUX-P4-07, CUX-P4-08, CUX-P4-09 depend on earlier groups. Estimated 2-3 days.
- **Batch 5 (Group 5)**: CUX-P4-10 can start early (depends on Phase 1 API). Estimated 1-2 days.
- **Batch 6 (Group 6)**: CUX-P4-11, CUX-P4-12 run last. Estimated 1-2 days.

Total: 3-4 weeks for the full phase with 1 FTE frontend engineer.

---

**Phase 4 Version**: 1.0
**Last Updated**: 2026-02-19
