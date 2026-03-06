---
type: progress
schema_version: 2
doc_type: progress
prd: "universal-entity-picker-dialog"
feature_slug: "universal-entity-picker-dialog"
prd_ref: "docs/project_plans/PRDs/enhancements/universal-entity-picker-dialog-v1.md"
plan_ref: "docs/project_plans/implementation_plans/enhancements/universal-entity-picker-dialog-v1.md"
phase: 3
title: "Testing, Accessibility & Polish"
status: "planning"
started: null
completed: null
commit_refs: []
pr_refs: []

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 3
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["ui-engineer-enhanced"]
contributors: ["task-completion-validator"]

tasks:
  - id: "UEPD-5.1"
    description: "Full keyboard navigation and accessibility audit (focus trap, ARIA labels, screen reader)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["UEPD-3.1", "UEPD-3.2", "UEPD-4.1"]
    estimated_effort: "2h"
    priority: "high"

  - id: "UEPD-5.2"
    description: "Visual polish - responsive grid, loading skeletons, empty states, selection animations"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["UEPD-3.1", "UEPD-3.2", "UEPD-4.1"]
    estimated_effort: "2h"
    priority: "medium"

  - id: "UEPD-5.3"
    description: "Integration validation - form state roundtrip, no regressions in workflow flows"
    status: "pending"
    assigned_to: ["task-completion-validator"]
    dependencies: ["UEPD-5.1", "UEPD-5.2"]
    estimated_effort: "1h"
    priority: "high"

parallelization:
  batch_1: ["UEPD-5.1", "UEPD-5.2"]
  batch_2: ["UEPD-5.3"]
  critical_path: ["UEPD-5.1", "UEPD-5.3"]
  estimated_total_time: "3h"

blockers: []

success_criteria:
  - { id: "SC-1", description: "Full keyboard navigation works (Tab, arrows, Enter, Escape)", status: "pending" }
  - { id: "SC-2", description: "All ARIA labels present and correct", status: "pending" }
  - { id: "SC-3", description: "pnpm type-check && pnpm lint passes", status: "pending" }
  - { id: "SC-4", description: "All 3 integration points verified end-to-end", status: "pending" }

files_modified:
  - "skillmeat/web/components/shared/entity-picker-dialog.tsx"
  - "skillmeat/web/components/shared/entity-picker-adapter-hooks.ts"
  - "skillmeat/web/components/context/mini-context-entity-card.tsx"
  - "skillmeat/web/components/workflow/stage-editor.tsx"
  - "skillmeat/web/components/workflow/builder-sidebar.tsx"
---

# Universal Entity Picker Dialog - Phase 3: Testing, Accessibility & Polish

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/universal-entity-picker-dialog/phase-3-progress.md \
  -t TASK-ID -s completed
```

Batch update when phase complete:

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/universal-entity-picker-dialog/phase-3-progress.md \
  --updates "UEPD-5.1:completed,UEPD-5.2:completed,UEPD-5.3:completed"
```

---

## Objective

Harden the feature for production through comprehensive keyboard navigation, accessibility (WCAG 2.1 AA), visual polish (responsive grid, loading and empty states, selection feedback), and integration validation across all three workflow UI locations. This phase gates feature completion and depends on successful implementation of Phases 1-2.

---

## Implementation Notes

### Architectural Decisions

- **Accessibility First**: Keyboard navigation and ARIA labels are not optional polish—they are core requirements. Focus trap and screen reader support must be fully functional before feature release.
- **Visual Consistency**: Selection feedback uses both color AND icon (checkmark), not color alone, to meet WCAG color-not-alone requirement.
- **Responsive Design**: Grid should reflow seamlessly on mobile (2 columns), tablet (3 columns), and desktop (4+ columns) to match AddMemberDialog patterns.

### Patterns and Best Practices

- **Focus Management**: Dialog must trap focus on open (prevent tabbing outside) and return focus to trigger on close.
- **Keyboard Navigation**: Tab moves focus through elements, arrow keys navigate list items, Enter/Space selects item, Escape closes dialog.
- **ARIA Semantics**: Dialog has `role="dialog"` and `aria-modal="true"`; list items have `aria-selected` state; filter pills have accessible roles.
- **Loading & Empty States**: Show skeleton loaders immediately on first tab activation; show "No results" message when search + filter yields zero items.
- **Selection Animation**: Brief highlight animation on card selection (200ms fade/scale) provides visual feedback.

### Known Gotchas

- **Color + Icon Contrast**: Ensure checkmark icon has sufficient contrast against card background in both light and dark modes. Do not rely on color alone.
- **Screen Reader Announcements**: Selection changes must be announced to screen reader users. Use `aria-live` region or ensure `aria-selected` changes are detected by screen reader.
- **Focus Visible Outline**: Ensure focus outline is visible on all keyboard-navigable elements (tabs, filter pills, cards) and not hidden by CSS.
- **Responsive Breakpoints**: Verify grid reflows correctly at sm/md/lg Tailwind breakpoints; test on actual mobile/tablet devices if possible.

### Development Setup

1. Run dev server: `skillmeat web dev`
2. Type-check frequently: `pnpm type-check`
3. Lint validation: `pnpm lint`
4. Manual accessibility testing: Keyboard-only navigation through each dialog
5. Screen reader testing (if available): VoiceOver (macOS), NVDA (Windows), Orca (Linux)

---

## Quality Gates

**Phase 3 is complete when ALL of the following pass:**

- [ ] Full keyboard navigation verified manually (Tab, arrows, Enter, Escape)
- [ ] ARIA labels and roles present on all interactive elements
- [ ] Focus trap functional: Dialog traps focus on open, returns to trigger on close
- [ ] Screen reader announces selection changes and dialog state
- [ ] Selection feedback uses both color and icon (checkmark), never color alone
- [ ] Loading skeletons display on tab activate and during fetch
- [ ] Empty state message visible when search/filter yields zero results
- [ ] Responsive grid reflows correctly at all Tailwind breakpoints (sm/md/lg/xl/2xl)
- [ ] Selection animation smooth and non-distracting (200ms duration)
- [ ] `pnpm type-check` passes with zero errors on all modified files
- [ ] `pnpm lint` passes with no new warnings
- [ ] All unit tests pass: `pnpm test -- --testPathPattern="entity-picker|stage-editor|builder-sidebar"`
- [ ] Manual QA: All three workflow picker fields work end-to-end in `skillmeat web dev`
- [ ] Form state roundtrip verified: select → save → reload → correct selection shown
- [ ] No visual regressions in surrounding workflow UI

---

## Completion Notes

*Fill in when phase is complete:*

- [ ] What was built
- [ ] Key learnings
- [ ] Unexpected challenges
- [ ] Recommendations for next phase
