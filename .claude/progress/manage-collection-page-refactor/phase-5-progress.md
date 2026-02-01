---
type: progress
prd: "manage-collection-page-refactor"
phase: 5
title: "Polish & Testing"
status: "pending"
started: null
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 6
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["frontend-developer", "ui-engineer-enhanced"]
contributors: ["web-accessibility-checker", "testing-specialist"]

tasks:
  - id: "POLISH-5.1"
    description: "Add loading states and skeletons for ArtifactBrowseCard, ArtifactOperationsCard, and modals."
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "1h"
    priority: "medium"
    model: "sonnet"

  - id: "POLISH-5.2"
    description: "Accessibility audit (WCAG AA): ARIA labels, focus management, keyboard navigation on all new components."
    status: "pending"
    assigned_to: ["web-accessibility-checker"]
    dependencies: []
    estimated_effort: "1.5h"
    priority: "high"
    model: "opus"

  - id: "POLISH-5.3"
    description: "Unit tests for new components (Jest + RTL): cards, modals, filters, utilities. Target >80% coverage."
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: []
    estimated_effort: "1.5h"
    priority: "high"
    model: "opus"

  - id: "POLISH-5.4"
    description: "E2E tests for cross-navigation flows (Playwright): browse to manage, manage to collection, deep links."
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: []
    estimated_effort: "1h"
    priority: "high"
    model: "opus"

  - id: "POLISH-5.5"
    description: "Dark mode verification: all new components readable, proper contrast, icons visible, badge colors appropriate."
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "0.5h"
    priority: "medium"
    model: "haiku"

  - id: "POLISH-5.6"
    description: "Performance verification: page load times stable, modal open <200ms, filter changes responsive, no memory leaks."
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: []
    estimated_effort: "0.5h"
    priority: "medium"
    model: "sonnet"

parallelization:
  batch_1: ["POLISH-5.1", "POLISH-5.2", "POLISH-5.3", "POLISH-5.4", "POLISH-5.5", "POLISH-5.6"]
  critical_path: ["POLISH-5.2"]
  estimated_total_time: "2-4h"

blockers: []

success_criteria:
  - { id: "SC-5.1", description: "All new components have loading/skeleton states", status: "pending" }
  - { id: "SC-5.2", description: "WCAG AA compliance audit passed", status: "pending" }
  - { id: "SC-5.3", description: "Unit test coverage >80%", status: "pending" }
  - { id: "SC-5.4", description: "E2E tests cover critical flows", status: "pending" }
  - { id: "SC-5.5", description: "Dark mode verified", status: "pending" }
  - { id: "SC-5.6", description: "No performance regressions", status: "pending" }

files_modified:
  - "skillmeat/web/components/collection/artifact-browse-card-skeleton.tsx"
  - "skillmeat/web/components/manage/artifact-operations-card-skeleton.tsx"
  - "skillmeat/web/__tests__/components/collection/"
  - "skillmeat/web/__tests__/components/manage/"
  - "skillmeat/web/__tests__/components/shared/"
  - "skillmeat/web/tests/cross-navigation.spec.ts"
---

# manage-collection-page-refactor - Phase 5: Polish & Testing

**YAML frontmatter is the source of truth for tasks, status, and assignments.**

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/manage-collection-page-refactor/phase-5-progress.md -t POLISH-5.1 -s completed
```

---

## Objective

Ensure production-ready quality with comprehensive testing, accessibility compliance, and documentation. All components must meet performance and accessibility standards.

---

## Orchestration Quick Reference

### Batch 1 (All tasks can run in parallel)

```
Task("ui-engineer-enhanced", "POLISH-5.1: Add loading states and skeletons. Create skeleton versions of ArtifactBrowseCard, ArtifactOperationsCard, and modal loading states. Skeletons must match card dimensions, animate properly, appear during data fetch, smooth transition to content. Files: skillmeat/web/components/collection/artifact-browse-card-skeleton.tsx, skillmeat/web/components/manage/artifact-operations-card-skeleton.tsx", model="sonnet")

Task("web-accessibility-checker", "POLISH-5.2: Accessibility audit (WCAG AA). Audit all new components: ARIA labels on icon buttons, focus management correct, keyboard navigation works, modal focus trapped, ESC closes modals, no color-only information. Generate accessibility audit report with any violations and fixes needed.")

Task("testing-specialist", "POLISH-5.3: Unit tests for new components. Write Jest + RTL tests for: ArtifactBrowseCard, ArtifactOperationsCard, StatusBadge, HealthIndicator, DeploymentBadgeStack, ManagePageFilters, CollectionPageFilters enhancements, modals. Target >80% statement coverage. Use accessible selectors (getByRole, getByLabelText). Directory: skillmeat/web/__tests__/")

Task("testing-specialist", "POLISH-5.4: E2E tests for cross-navigation flows. Write Playwright tests for: navigate collection -> modal -> manage, navigate manage -> modal -> collection, deep links open correct modals, URL state preserves, mobile navigation works. File: skillmeat/web/tests/cross-navigation.spec.ts")

Task("ui-engineer-enhanced", "POLISH-5.5: Dark mode verification. Verify all new components in dark mode: readable text, proper contrast, visible icons, appropriate badge colors, visible focus indicators. Document any issues found.", model="haiku")

Task("frontend-developer", "POLISH-5.6: Performance verification. Measure and document: page load times (compare to baseline), modal open times (target <200ms), filter change responsiveness, check for memory leaks with React DevTools. Document performance metrics.", model="sonnet")
```

---

## Tasks Reference

| Task ID | Description | Assignee | Est. | Dependencies |
|---------|-------------|----------|------|--------------|
| POLISH-5.1 | Add loading states and skeletons | ui-engineer-enhanced | 1h | - |
| POLISH-5.2 | Accessibility audit (WCAG AA) | web-accessibility-checker | 1.5h | - |
| POLISH-5.3 | Unit tests for components | testing-specialist | 1.5h | - |
| POLISH-5.4 | E2E tests for cross-navigation | testing-specialist | 1h | - |
| POLISH-5.5 | Dark mode verification | ui-engineer-enhanced | 0.5h | - |
| POLISH-5.6 | Performance verification | frontend-developer | 0.5h | - |

---

## Quality Gate

- [ ] All new components have loading/skeleton states
- [ ] WCAG AA compliance audit passed
- [ ] Unit test coverage >80%
- [ ] E2E tests cover critical flows
- [ ] Dark mode verified
- [ ] No performance regressions

---

## Implementation Notes

### Testing Requirements

**Unit Tests (Jest + RTL)**:
- Use `getByRole`, `getByLabelText`, `getByText` (avoid `getByTestId`)
- Fresh `QueryClient` per test with `retry: false`
- Use `userEvent.setup()` over `fireEvent`
- Test all prop combinations and error states

**E2E Tests (Playwright)**:
- Test complete user journeys
- Verify URL state at each step
- Test mobile viewport
- Test keyboard-only navigation

### Accessibility Checklist

- [ ] All interactive elements keyboard accessible
- [ ] ARIA labels on icon buttons
- [ ] Focus visible on all elements
- [ ] Modal focus trapped
- [ ] ESC closes modals
- [ ] No color-only information
- [ ] Sufficient color contrast (4.5:1 for text)

### Performance Targets

| Metric | Target |
|--------|--------|
| Page load regression | <10% |
| Modal open time | <200ms |
| Filter change response | <100ms |
| Memory leaks | None |

### Skeleton Component Pattern

```typescript
export function ArtifactBrowseCardSkeleton() {
  return (
    <Card className="animate-pulse">
      <div className="h-4 bg-muted rounded w-3/4 mb-2" />
      <div className="h-3 bg-muted rounded w-1/2 mb-4" />
      <div className="h-16 bg-muted rounded" />
    </Card>
  );
}
```

---

## Completion Notes

(Fill in when phase is complete)

---

## Pre-Launch Checklist

After Phase 5 completes:

- [ ] Code review by senior-code-reviewer
- [ ] Architecture review by lead-architect
- [ ] QA testing on staging
- [ ] Performance baseline established
- [ ] Documentation complete
- [ ] Feature flag prepared for rollout
